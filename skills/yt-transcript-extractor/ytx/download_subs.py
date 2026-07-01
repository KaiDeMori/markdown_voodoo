"""Stage 2 - download chosen subtitle tracks into raw/ (kept pristine).

Reuses the cached meta/<id>.info.json from Stage 1, so NO re-extraction is
needed: we fetch the exact lang x format files directly (same auth/cookies),
one polite request each. Raw files are the download-once source of truth and
are never edited - cleaning happens later on copies.

    python -m ytx.download_subs <id-or-url> [--langs en-orig,de] [--formats json3,vtt] \
        [--client web,mweb,tv] [--cookies FILE] [--use-cookies]
"""
from __future__ import annotations

import sys
import time

import yt_dlp

from . import config
from .list_subs import _take_opt, video_id

DEFAULT_LANGS = ("en-orig",)
DEFAULT_FORMATS = ("json3", "vtt")  # the two worth comparing (clean vs rolling)


def load_info(vid: str) -> dict:
    import json

    p = config.META_DIR / f"{vid}.info.json"
    if not p.is_file():
        raise SystemExit(
            f"No cached info for {vid} at {p}. Run `python -m ytx.list_subs` first."
        )
    return json.loads(p.read_text(encoding="utf-8"))


def find_entry(info: dict, lang: str, fmt: str, kind: str | None = None):
    """Return (kind, entry) with kind in {'manual','auto'}, or (None, None).

    If kind is given, only that track type is searched.
    """
    pairs = (("manual", "subtitles"), ("auto", "automatic_captions"))
    if kind:
        pairs = tuple(p for p in pairs if p[0] == kind)
    for k, key in pairs:
        for e in (info.get(key) or {}).get(lang, []):
            if e.get("ext") == fmt:
                return k, e
    return None, None


def download_pairs(vid, pairs, cookies_file=None, force=False,
                   player_clients=config.DEFAULT_PLAYER_CLIENTS) -> list:
    """Download explicit (lang, kind|None, fmt) tuples into raw/.

    Already-present raw files are reused (download-once) unless force=True.
    Progress goes to stderr so callers' stdout stays clean.
    """
    info = load_info(vid)
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    opts = config.base_ydl_opts(cookies_file=cookies_file, player_clients=player_clients)
    saved, hits = [], 0
    with yt_dlp.YoutubeDL(opts) as ydl:  # carries the cookie jar for urlopen
        for lang, kind, fmt in pairs:
            k, entry = find_entry(info, lang, fmt, kind=kind)
            if not entry:
                print(f"  [skip ] {lang}.{fmt}: not offered by this video", file=sys.stderr)
                continue
            out = config.RAW_DIR / f"{vid}.{lang}.{k}.{fmt}"
            if out.exists() and not force:
                print(f"  [have ] {out.name} (already downloaded)", file=sys.stderr)
                saved.append(out)
                continue
            if hits:
                time.sleep(config.SLEEP_REQUESTS)  # be polite between real hits
            hits += 1
            data = ydl.urlopen(entry["url"]).read()
            out.write_bytes(data)
            saved.append(out)
            print(f"  [saved] {out.name}  ({len(data):,} bytes)", file=sys.stderr)
    return saved


def download(vid, langs, formats, cookies_file=None, force=False,
             player_clients=config.DEFAULT_PLAYER_CLIENTS) -> list:
    pairs = [(lang, None, fmt) for lang in langs for fmt in formats]
    return download_pairs(vid, pairs, cookies_file=cookies_file, force=force,
                          player_clients=player_clients)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    config.use_utf8_io()
    config.configure(_take_opt(argv, "--out-dir"))  # where the raw/ cache lands

    langs_arg = _take_opt(argv, "--langs")
    formats_arg = _take_opt(argv, "--formats")
    use_cookies_flag = "--use-cookies" in argv
    if use_cookies_flag:
        argv.remove("--use-cookies")
    cookies_file = config.resolve_cookies(
        _take_opt(argv, "--cookies"),
        use_cookies=True if use_cookies_flag else None)
    # --client web,mweb,tv  (comma-separated; "default"/omitted = let yt-dlp pick)
    client_arg = _take_opt(argv, "--client")
    if not client_arg or client_arg.lower() == "default":
        player_clients = config.DEFAULT_PLAYER_CLIENTS
    else:
        player_clients = tuple(c.strip() for c in client_arg.split(",") if c.strip())
    langs = tuple(langs_arg.split(",")) if langs_arg else DEFAULT_LANGS
    formats = tuple(formats_arg.split(",")) if formats_arg else DEFAULT_FORMATS

    if not argv:
        print(__doc__)
        return 2
    for target in argv:
        vid = video_id(target)
        print(f"\n=== downloading subs for {vid} : {list(langs)} x {list(formats)} ===")
        download(vid, langs, formats, cookies_file=cookies_file, player_clients=player_clients)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

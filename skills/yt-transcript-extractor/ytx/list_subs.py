"""Stage 1 - discover which subtitle tracks/formats a video offers.

Network stage. Fetches metadata only (no media, no subtitle files) and caches
the full info-json plus a compact human summary into meta/. Run once per video;
later stages work off the cached files.

    python -m ytx.list_subs "https://www.youtube.com/watch?v=VIDEOID" [more urls]
"""
from __future__ import annotations

import json
import re
import sys

import yt_dlp

from . import config

# langs we usually care about; anything matching these is highlighted.
INTERESTING_PREFIXES = ("en", "de")


def video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else re.sub(r"[^A-Za-z0-9_-]", "_", url)[:32]


def fetch_info(
    url: str,
    verbose: bool = False,
    player_clients=config.DEFAULT_PLAYER_CLIENTS,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> dict:
    opts = config.base_ydl_opts(
        verbose=verbose,
        player_clients=player_clients,
        cookies_from_browser=cookies_from_browser,
        cookies_file=cookies_file,
    )
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return ydl.sanitize_info(info)


def _formats_by_lang(tracks: dict) -> dict[str, list[str]]:
    return {
        lang: sorted({t.get("ext") for t in entries if t.get("ext")})
        for lang, entries in tracks.items()
    }


def _interesting(langs) -> list[str]:
    return sorted(
        l for l in langs
        if l.lower().startswith(INTERESTING_PREFIXES) or l.lower().endswith("-orig")
    )


def original_lang(info: dict) -> str | None:
    """Best guess at the video's original spoken language.

    Strongest signal is an auto-caption track tagged '-orig'; else yt-dlp's
    detected `language` (only if a track for it actually exists).
    """
    auto = info.get("automatic_captions") or {}
    manual = info.get("subtitles") or {}
    orig = sorted(l for l in auto if l.endswith("-orig"))
    if orig:
        return orig[0]
    lang = info.get("language")
    if lang and (lang in auto or lang in manual):
        return lang
    return None


def summarize(info: dict) -> dict:
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    manual_fmts = _formats_by_lang(manual)
    auto_fmts = _formats_by_lang(auto)
    # auto tracks usually all share the same format set -> sample one.
    sample_fmt = next(iter(auto_fmts.values()), [])
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "duration_s": info.get("duration"),
        "original_lang": original_lang(info),
        "formats_available": sample_fmt or sorted({f for fs in manual_fmts.values() for f in fs}),
        "manual": {
            "langs": sorted(manual.keys()),
            "formats_by_lang": manual_fmts,
        },
        "auto": {
            "total_langs": len(auto),
            "formats_available": sample_fmt,
            "interesting_langs": _interesting(auto.keys()),
            "interesting_formats": {
                l: auto_fmts[l] for l in _interesting(auto.keys())
            },
        },
    }


def fetch_and_cache(
    url: str,
    verbose: bool = False,
    player_clients=config.DEFAULT_PLAYER_CLIENTS,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> tuple[str, dict, dict]:
    """Stage 1 core: fetch info, cache info.json + subs.json, return (vid, info, summary)."""
    config.META_DIR.mkdir(parents=True, exist_ok=True)
    info = fetch_info(
        url,
        verbose=verbose,
        player_clients=player_clients,
        cookies_from_browser=cookies_from_browser,
        cookies_file=cookies_file,
    )
    vid = info.get("id") or video_id(url)
    (config.META_DIR / f"{vid}.info.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    summary = summarize(info)
    (config.META_DIR / f"{vid}.subs.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return vid, info, summary


def run(
    urls: list[str],
    verbose: bool = False,
    player_clients=config.DEFAULT_PLAYER_CLIENTS,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> int:
    summaries = []
    for url in urls:
        print(f"[list] {video_id(url)} : {url}", file=sys.stderr, flush=True)
        vid, _info, summary = fetch_and_cache(
            url,
            verbose=verbose,
            player_clients=player_clients,
            cookies_from_browser=cookies_from_browser,
            cookies_file=cookies_file,
        )
        print(f"[cached] meta/{vid}.info.json", file=sys.stderr, flush=True)
        summaries.append(summary)
    # stdout = clean, parseable JSON (single object for one url, else an array)
    out = summaries[0] if len(summaries) == 1 else summaries
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def _take_opt(argv: list[str], name: str) -> str | None:
    """Pop `--name value` from argv, returning the value (or None)."""
    if name in argv:
        i = argv.index(name)
        value = argv[i + 1]
        del argv[i:i + 2]
        return value
    return None


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    config.use_utf8_io()
    config.configure(_take_opt(argv, "--out-dir"))  # where the meta/ cache lands
    verbose = False
    if "-v" in argv:
        verbose = True
        argv.remove("-v")

    # --client web,mweb,tv   (comma-separated; "default" = let yt-dlp decide)
    client_arg = _take_opt(argv, "--client")
    if client_arg is None:
        player_clients = config.DEFAULT_PLAYER_CLIENTS
    elif client_arg.lower() == "default":
        player_clients = None
    else:
        player_clients = tuple(c.strip() for c in client_arg.split(",") if c.strip())

    # --cookies-from-browser firefox   (or firefox:profilename for an alt)
    cookies_from_browser = _take_opt(argv, "--cookies-from-browser")
    # --cookies path/to/cookies.txt   (Netscape export)
    cookies_file = _take_opt(argv, "--cookies")

    if not argv:
        print(__doc__)
        return 2
    return run(
        argv,
        verbose=verbose,
        player_clients=player_clients,
        cookies_from_browser=cookies_from_browser,
        cookies_file=cookies_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())

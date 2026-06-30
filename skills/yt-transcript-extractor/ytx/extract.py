"""One-shot transcript extraction: give a URL, get a clean transcript.

Runs the whole pipeline and DECIDES which tracks to use itself:
  Stage 1 list -> auto-select best track(s) -> Stage 2 download json3 -> Stage 3 clean.

NETWORK: stages 1 and 2 contact YouTube. Per this project's hard rule, an agent
MUST ask the user's permission (AskUserQuestion) BEFORE running this. See README.

Track-selection rules (best first):
  1. manual subtitles beat auto-captions      (human > ASR)
  2. original language beats translations      ('-orig' marker or detected language)
  3. json3 beats other formats                 (cleanest; falls back to srv3/vtt/ttml/srt)

    python -m ytx.extract <url> [--prefer en,de] [--also-translation]
                                [--flow sentences|paragraphs|wrapped|oneline|lines]
                                [--cookies FILE] [--refresh] [--verbose]
"""
from __future__ import annotations

import json
import sys

from . import clean as clean_mod
from . import config, download_subs
from .list_subs import _take_opt, fetch_and_cache, video_id

FORMAT_PREFERENCE = ("json3", "srv3", "vtt", "ttml", "srt")


def _formats_for(info, lang, kind):
    key = "subtitles" if kind == "manual" else "automatic_captions"
    return [e.get("ext") for e in (info.get(key) or {}).get(lang, []) if e.get("ext")]


def _best_format(available):
    return next((f for f in FORMAT_PREFERENCE if f in available),
                available[0] if available else None)


def _first_present(mapping, candidates):
    return next((c for c in candidates if c and c in mapping), None)


def choose_tracks(info, prefer_langs=("en", "de"), also_translation=False):
    """Decide which subtitle tracks to download.

    Returns a list of {lang, kind, fmt, reason}; the first item is the primary
    (most faithful) transcript.
    """
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}

    # Identify the original language: prefer the '-orig' ASR marker, else yt-dlp's
    # detected video language (only if a track for it actually exists).
    orig_lang = None
    orig_auto = sorted(l for l in auto if l.endswith("-orig"))
    if orig_auto:
        orig_lang = orig_auto[0]
    elif info.get("language") and (info["language"] in manual or info["language"] in auto):
        orig_lang = info["language"]

    picks: list[tuple[str, str, str]] = []  # (lang, kind, reason)

    # Primary: the most faithful transcript available.
    if manual:
        lang = _first_present(manual, [orig_lang, *prefer_langs]) or sorted(manual)[0]
        picks.append((lang, "manual", "human-made subtitles (highest quality)"))
    elif orig_lang:
        picks.append((orig_lang, "auto", "original-language auto-captions (best fidelity)"))
    elif auto:
        lang = _first_present(auto, prefer_langs) or sorted(auto)[0]
        picks.append((lang, "auto", "auto-captions (no original marker; preferred/first language)"))

    # Optional: also fetch a translation into a preferred reading language.
    if also_translation and picks:
        primary_base = picks[0][0].replace("-orig", "")
        for pl in prefer_langs:
            if pl == primary_base:
                continue
            if pl in manual:
                picks.append((pl, "manual", f"human translation into preferred '{pl}'"))
                break
            if pl in auto:
                picks.append((pl, "auto", f"auto-translation into preferred '{pl}'"))
                break

    chosen = []
    for lang, kind, reason in picks:
        fmt = _best_format(_formats_for(info, lang, kind))
        if fmt:
            chosen.append({"lang": lang, "kind": kind, "fmt": fmt, "reason": reason})
    return chosen


def _load_or_fetch(url, cookies, verbose, refresh):
    """Stage 1, reusing the cached listing when present (no network re-extraction)."""
    vid = video_id(url)
    cached = config.META_DIR / f"{vid}.info.json"
    if cached.is_file() and not refresh:
        print(f"[1/3] using cached listing meta/{vid}.info.json (no network)", file=sys.stderr)
        info = json.loads(cached.read_text(encoding="utf-8"))
        return info.get("id") or vid, info
    print(f"[1/3] listing tracks for {vid} (network) ...", file=sys.stderr)
    vid, info, _summary = fetch_and_cache(url, verbose=verbose, cookies_file=cookies)
    return vid, info


def _write_transcript_md(info, vid, lang, kind, fmt, lines, flow):
    words = sum(len(l.split()) for l in lines)
    out = config.CLEAN_DIR / config.safe_filename(info, suffix=f".{lang}.md", max_len=200)
    header = (
        f"# {info.get('title') or vid}\n\n"
        f"- **Channel:** {info.get('channel') or info.get('uploader') or ''}\n"
        f"- **URL:** https://www.youtube.com/watch?v={vid}\n"
        f"- **Track:** {lang} · {kind} · {fmt} · flow={flow}\n"
        f"- **Words:** {words}\n\n"
        "---\n\n"
    )
    out.write_text(header + clean_mod.reflow(lines, flow), encoding="utf-8")
    return out, words


def extract(url, prefer_langs=("en", "de"), also_translation=False,
            cookies_file=None, verbose=False, refresh=False, flow=None):
    flow = flow or config.DEFAULT_FLOW
    cookies = config.resolve_cookies(cookies_file)
    print(f"[cookies] {cookies or 'NONE - YouTube will likely return LOGIN_REQUIRED'}",
          file=sys.stderr)

    # Stage 1 - list (network, or cache)
    vid, info = _load_or_fetch(url, cookies, verbose, refresh)
    print(f"      title: {info.get('title')!r}  channel: "
          f"{(info.get('channel') or info.get('uploader'))!r}", file=sys.stderr)

    # Decide
    picks = choose_tracks(info, prefer_langs=prefer_langs, also_translation=also_translation)
    if not picks:
        raise SystemExit("No subtitle tracks available for this video.")
    print("[decision] chosen track(s):", file=sys.stderr)
    for p in picks:
        print(f"      - {p['lang']} ({p['kind']}, {p['fmt']}) : {p['reason']}", file=sys.stderr)

    # Stage 2 - download (network; reuses already-downloaded raw files)
    print(f"[2/3] downloading {len(picks)} track(s) -> {config.RAW_DIR} ...", file=sys.stderr)
    config.CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    download_subs.download_pairs(
        vid, [(p["lang"], p["kind"], p["fmt"]) for p in picks], cookies_file=cookies)

    # Stage 3 - clean (local) -> nicely-named .md deliverables
    print(f"[3/3] cleaning -> {config.OUTPUT_BASE} ...", file=sys.stderr)
    transcripts = []
    for i, p in enumerate(picks):
        raw = config.RAW_DIR / f"{vid}.{p['lang']}.{p['kind']}.{p['fmt']}"
        lines = clean_mod.clean_file(raw) or []
        md, words = _write_transcript_md(info, vid, p["lang"], p["kind"], p["fmt"], lines, flow)
        transcripts.append({
            "primary": i == 0,
            "lang": p["lang"], "kind": p["kind"], "format": p["fmt"],
            "lines": len(lines), "words": words, "path": str(md),
        })
        print(f"      [md] {md.name}", file=sys.stderr)

    result = {
        "id": vid,
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "url": f"https://www.youtube.com/watch?v={vid}",
        "out_dir": str(config.OUTPUT_BASE),
        "transcripts": transcripts,
    }
    # stdout = the single machine-readable result: where the finished files are.
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    config.use_utf8_io()
    config.configure(_take_opt(argv, "--out-dir"))  # where outputs land (the workspace)
    verbose = "--verbose" in argv
    if verbose:
        argv.remove("--verbose")
    also_translation = "--also-translation" in argv
    if also_translation:
        argv.remove("--also-translation")
    refresh = "--refresh" in argv          # force a fresh listing (ignore cache)
    if refresh:
        argv.remove("--refresh")
    prefer = _take_opt(argv, "--prefer")
    cookies_file = _take_opt(argv, "--cookies")
    flow = _take_opt(argv, "--flow")       # sentences|paragraphs|wrapped|oneline|lines
    prefer_langs = tuple(prefer.split(",")) if prefer else ("en", "de")

    if not argv:
        print(__doc__)
        return 2
    for url in argv:
        extract(url, prefer_langs=prefer_langs, also_translation=also_translation,
                cookies_file=cookies_file, verbose=verbose, refresh=refresh, flow=flow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

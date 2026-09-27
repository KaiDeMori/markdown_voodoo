"""Stage 2b - probe: download chosen tracks and show what they actually contain.

YouTube's track labels are unreliable; the text is not. The probe downloads up
to MAX_PROBE_TRACKS tracks of one video from the cached listing into raw/ and
prints a short sample of each, so the reader can judge language and quality
before extracting. raw/ is download-once, so the probe is also the final
download: the extract run afterwards is local.

NETWORK: one caption request per track not yet in raw/. Every YouTube request
counts toward the bot wall - hence the cap per call. With --offline nothing is
fetched: the tracks must already be in raw/ (e.g. from an imported relay bundle).

    python -m ytx.probe <id-or-url> --tracks en-orig.auto[,en.manual] [--offline]
        [--client web,mweb,tv] [--cookies FILE] [--use-cookies]
"""
from __future__ import annotations

import json
import sys

from . import clean as clean_mod
from . import config, download_subs
from .extract import _best_format, _formats_for
from .list_subs import _take_opt, parse_track_id, source_tracks, track_id, video_id

MAX_PROBE_TRACKS = 2
SAMPLE_LINES = 5


def sample_from(lines: list[str], start: int) -> str:
    return " ".join(lines[start:start + SAMPLE_LINES])


def probe(vid, tracks, cookies_file=None,
          player_clients=config.DEFAULT_PLAYER_CLIENTS, offline=False) -> dict:
    tracks = list(dict.fromkeys(tracks))
    if len(tracks) > MAX_PROBE_TRACKS:
        raise SystemExit(
            f"At most {MAX_PROBE_TRACKS} tracks per probe; got {len(tracks)}. "
            "Probing more needs the user's OK first.")
    info = download_subs.load_info(vid)

    pairs = []
    for track in tracks:
        lang, kind = parse_track_id(track)
        fmt = _best_format(_formats_for(info, lang, kind))
        if not fmt:
            available = ", ".join(t["track"] for t in source_tracks(info)) or "none"
            raise SystemExit(f"Track {track} is not offered by this video. Source tracks: {available}.")
        pairs.append((lang, kind, fmt))

    print(f"[probe] {vid} : {', '.join(tracks)}", file=sys.stderr)
    download_subs.download_pairs(vid, pairs, cookies_file=cookies_file,
                                 player_clients=player_clients, offline=offline)

    duration = info.get("duration")
    probes = []
    for lang, kind, fmt in pairs:
        raw = config.RAW_DIR / f"{vid}.{lang}.{kind}.{fmt}"
        lines = clean_mod.clean_file(raw) or []
        words = sum(len(line.split()) for line in lines)
        middle = max(0, len(lines) // 2 - SAMPLE_LINES // 2)
        probes.append({
            "track": track_id(lang, kind),
            "format": fmt,
            "path": str(raw),
            "lines": len(lines),
            "words": words,
            "words_per_minute": round(words / (duration / 60)) if duration else None,
            "sample_start": sample_from(lines, 0),
            "sample_middle": sample_from(lines, middle),
        })
    return {
        "id": vid,
        "title": info.get("title"),
        "duration_s": duration,
        "probes": probes,
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    config.use_utf8_io()
    config.configure(_take_opt(argv, "--out-dir"))  # where the meta/ and raw/ caches live

    tracks_arg = _take_opt(argv, "--tracks")
    offline = "--offline" in argv
    if offline:
        argv.remove("--offline")
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

    if len(argv) != 1 or not tracks_arg:
        print(__doc__)
        return 2
    tracks = [t.strip() for t in tracks_arg.split(",") if t.strip()]
    result = probe(video_id(argv[0]), tracks, cookies_file=cookies_file,
                   player_clients=player_clients, offline=offline)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

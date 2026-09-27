"""Stage 1 - discover which subtitle tracks a video offers, and recommend one.

Network stage. Fetches metadata only (no media, no subtitle files) and caches
the full info-json plus the track report into meta/. Run once per video; later
stages work off the cached files.

YouTube's track labels are unreliable, so the report is built from evidence:
each track's own URL says which language it was made in (`lang`) and whether it
is a machine translation (`tlang`). The report lists only source tracks - manual
uploads and ASR tracks - and leaves the final choice to the reader.

    python -m ytx.list_subs "https://www.youtube.com/watch?v=VIDEOID" [more urls]
        [--client web,mweb,tv] [--cookies FILE] [--use-cookies] [-v]
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse

import yt_dlp

from . import config

TRACK_KINDS = ("manual", "auto")

# yt-dlp files the chat replay of a past livestream under subtitles; it is not a transcript.
LIVE_CHAT_KEY = "live_chat"

# yt-dlp's language_preference for the audio track YouTube names "original".
ORIGINAL_AUDIO_LANGUAGE_PREFERENCE = 10

DESCRIPTION_HEAD_CHARS = 300


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


def url_query(entry: dict) -> dict[str, str]:
    return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(entry.get("url") or "").query))


def source_lang_of(entry: dict) -> str | None:
    """The language a track was made in: the ASR language, or the uploader's declaration."""
    return url_query(entry).get("lang")


def translated_to_of(entry: dict) -> str | None:
    """The target language of a machine translation; None for a source track."""
    return url_query(entry).get("tlang")


def base_lang(lang: str | None) -> str:
    """'en-GB' and 'en-orig' -> 'en'."""
    return (lang or "").split("-")[0].lower()


def track_id(lang: str, kind: str) -> str:
    """'<lang>.<kind>' - the same pair that names the raw file <id>.<lang>.<kind>.<fmt>."""
    return f"{lang}.{kind}"


def parse_track_id(track: str) -> tuple[str, str]:
    lang, separator, kind = track.rpartition(".")
    if not separator or not lang or kind not in TRACK_KINDS:
        raise SystemExit(
            f"Invalid track id {track!r}: expected <lang>.<kind> with kind "
            f"{' or '.join(TRACK_KINDS)}, e.g. en-orig.auto or en.manual.")
    return lang, kind


def make_track(lang: str, kind: str, entry: dict) -> dict:
    return {
        "track": track_id(lang, kind),
        "kind": kind,
        "lang": lang,
        "name": entry.get("name"),
        "source_lang": source_lang_of(entry),
    }


def source_tracks(info: dict) -> list[dict]:
    """Every track YouTube produced directly: manual uploads, then ASR tracks.

    Machine translations and the live-chat replay are left out. yt-dlp files one ASR track under several
    keys (its '-orig' key, its plain key, and as the source of translations), so
    ASR entries are identified by the language the ASR ran in and listed once,
    under the '-orig' key when yt-dlp created one. The '-orig' keys keep
    YouTube's track order; an ASR track without one (a language YouTube does not
    translate into) follows under its plain key.
    """
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    tracks = [make_track(lang, "manual", entries[0])
              for lang, entries in manual.items() if entries and lang != LIVE_CHAT_KEY]

    covered_source_langs = set()
    for lang, entries in auto.items():
        if lang.endswith("-orig") and entries:
            tracks.append(make_track(lang, "auto", entries[0]))
            covered_source_langs.add(source_lang_of(entries[0]))
    for lang, entries in auto.items():
        if lang.endswith("-orig"):
            continue
        for entry in entries:
            source_lang = source_lang_of(entry)
            if translated_to_of(entry) or not source_lang or source_lang in covered_source_langs:
                continue
            covered_source_langs.add(source_lang)
            tracks.append(make_track(lang, "auto", entry))
    return tracks


def machine_translation_count(info: dict) -> int:
    auto = info.get("automatic_captions") or {}
    return sum(1 for entries in auto.values()
               if entries and all(translated_to_of(e) for e in entries))


def original_audio_lang(info: dict) -> str | None:
    """Language of the audio track YouTube flags as original.

    Present only on multi-audio videos (e.g. auto-dubbed ones) whose formats were
    extracted - exactly the case where several ASR tracks compete.
    """
    for fmt in info.get("formats") or []:
        if (fmt.get("language_preference") == ORIGINAL_AUDIO_LANGUAGE_PREFERENCE
                and fmt.get("language")):
            return fmt["language"]
    return None


def first_track_in_langs(tracks: list[dict], langs: list[str]) -> dict | None:
    for lang in langs:
        for track in tracks:
            if base_lang(track["source_lang"] or track["lang"]) == base_lang(lang):
                return track
    return None


def recommend_track(info: dict, spoken_langs=None) -> dict | None:
    """Pick the most faithful source track; None when the video has none.

    Human subtitles beat ASR; within a kind, the spoken language wins. The
    spoken language comes from, best first: explicit spoken_langs (--prefer),
    the audio track YouTube flags as original, the only ASR track. Several ASR
    tracks without further evidence (an auto-dubbed video) leave only YouTube's
    track order to go on. `ambiguous` marks every pick that is not backed by
    spoken-language evidence - those need a human or Claude to confirm.
    """
    tracks = source_tracks(info)
    manual = [t for t in tracks if t["kind"] == "manual"]
    asr = [t for t in tracks if t["kind"] == "auto"]
    audio_lang = original_audio_lang(info)

    ambiguous = False
    if spoken_langs:
        spoken, evidence = list(spoken_langs), "--prefer"
    elif audio_lang:
        spoken, evidence = [audio_lang], "original audio track"
    elif len(asr) == 1:
        spoken, evidence = [asr[0]["source_lang"]], "the only ASR track"
    elif asr:
        spoken, evidence = [asr[0]["source_lang"]], "first of several ASR tracks"
        ambiguous = True
    else:
        spoken, evidence = [], "no evidence"
    spoken_claim = "the likely spoken language" if ambiguous else "the spoken language"

    if manual:
        pick = first_track_in_langs(manual, spoken)
        if pick:
            reason = f"human subtitles in {spoken_claim} ({evidence})"
        else:
            ambiguous = True
            pick = first_track_in_langs(manual, list(config.DEFAULT_READING_LANGS))
            if pick:
                reason = "human subtitles in a reading language; none in the spoken language"
            else:
                pick = manual[0]
                reason = "human subtitles; none in the spoken or a reading language"
    elif asr:
        pick = first_track_in_langs(asr, spoken)
        if pick:
            reason = f"ASR in {spoken_claim} ({evidence})"
        else:
            ambiguous = True
            pick = asr[0]
            reason = "ASR; none in the preferred languages"
    else:
        return None
    return {"track": pick["track"], "reason": reason, "ambiguous": ambiguous}


def summarize(info: dict) -> dict:
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "duration_s": info.get("duration"),
        "description_head": (info.get("description") or "")[:DESCRIPTION_HEAD_CHARS],
        "original_audio_lang": original_audio_lang(info),
        "source_tracks": source_tracks(info),
        "machine_translations": machine_translation_count(info),
        "recommended": recommend_track(info),
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

    # --client web,mweb,tv   (comma-separated; "default"/omitted = let yt-dlp decide)
    client_arg = _take_opt(argv, "--client")
    if not client_arg or client_arg.lower() == "default":
        player_clients = config.DEFAULT_PLAYER_CLIENTS
    else:
        player_clients = tuple(c.strip() for c in client_arg.split(",") if c.strip())

    # --cookies-from-browser firefox   (or firefox:profilename for an alt)
    cookies_from_browser = _take_opt(argv, "--cookies-from-browser")
    # --cookies FILE (explicit) wins; --use-cookies opts in to the default cookies
    # file. Off unless enabled (settings.local.json or the flag).
    use_cookies_flag = "--use-cookies" in argv
    if use_cookies_flag:
        argv.remove("--use-cookies")
    cookies_file = config.resolve_cookies(
        _take_opt(argv, "--cookies"),
        use_cookies=True if use_cookies_flag else None)

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

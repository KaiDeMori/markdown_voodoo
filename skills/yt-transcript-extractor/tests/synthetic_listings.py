"""Small listings shaped like yt-dlp's, for rule tests that must stay readable.

`listing` mimics how yt-dlp files ASR tracks: per ASR track it walks the
translation languages; at the track's own language it adds the '-orig' key and
the untranslated entry, everywhere else a machine translation (tlang). Keys are
created in that order, which is what the recommendation's "YouTube order" sees.
"""
from __future__ import annotations

SYNTHETIC_VIDEO_ID = "SYNTHETIC00"
TRANSLATION_LANGS = ("ar", "de", "en", "fr")
NEVER_EXPIRES = 4102444800

ORIGINAL_AUDIO_EN = [
    {"format_id": "251-0", "acodec": "opus", "language": "en", "language_preference": 10},
    {"format_id": "251-1", "acodec": "opus", "language": "ar", "language_preference": -1},
]

LIVE_CHAT = {
    "live_chat": [{
        "ext": "json",
        "url": "https://www.youtube.com/live_chat_replay?continuation=synthetic",
        "protocol": "youtube_live_chat_replay",
    }],
}


def entry(source_lang, name, tlang=None, asr=True, expire=NEVER_EXPIRES) -> list[dict]:
    url = (f"https://www.youtube.com/api/timedtext?v={SYNTHETIC_VIDEO_ID}"
           f"&lang={source_lang}&fmt=json3&expire={expire}")
    if asr:
        url += "&kind=asr"
    if tlang:
        url += f"&tlang={tlang}"
    return [{"ext": "json3", "name": name, "url": url}]


def manual_track(lang, name) -> list[dict]:
    return entry(lang, name, asr=False)


def listing(asr_order=(), manual=None, formats=None) -> dict:
    automatic_captions: dict[str, list[dict]] = {}
    for asr_lang in asr_order:
        for target in TRANSLATION_LANGS:
            if target == asr_lang:
                automatic_captions.setdefault(f"{target}-orig", []).extend(
                    entry(asr_lang, f"{target} (Original)"))
                automatic_captions.setdefault(target, []).extend(entry(asr_lang, target))
            else:
                automatic_captions.setdefault(target, []).extend(
                    entry(asr_lang, target, tlang=target))
    return {
        "id": SYNTHETIC_VIDEO_ID,
        "title": "Synthetic video",
        "channel": "Synthetic channel",
        "duration": 600,
        "automatic_captions": automatic_captions,
        "subtitles": manual or {},
        "formats": formats or [],
    }

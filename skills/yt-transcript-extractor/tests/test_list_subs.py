"""Track knowledge: URL decoding, track ids, source tracks and the recommendation."""
from __future__ import annotations

import pytest

from synthetic_listings import (
    LIVE_CHAT,
    ORIGINAL_AUDIO_EN,
    entry,
    listing,
    manual_track,
)
from ytx.list_subs import (
    base_lang,
    machine_translation_count,
    original_audio_lang,
    parse_track_id,
    recommend_track,
    relay_command,
    source_lang_of,
    source_tracks,
    summarize,
    track_id,
    translated_to_of,
)


# --- helpers ---------------------------------------------------------------

def test_url_decoding_separates_source_and_translation():
    translation = entry("en", "German", tlang="de")[0]
    source = entry("en", "English (Original)")[0]
    assert (source_lang_of(translation), translated_to_of(translation)) == ("en", "de")
    assert (source_lang_of(source), translated_to_of(source)) == ("en", None)


@pytest.mark.parametrize("lang, expected", [
    ("en", "en"), ("en-GB", "en"), ("en-orig", "en"), ("EN", "en"), (None, ""),
])
def test_base_lang(lang, expected):
    assert base_lang(lang) == expected


@pytest.mark.parametrize("track, expected", [
    ("en.manual", ("en", "manual")),
    ("en-orig.auto", ("en-orig", "auto")),
    ("zh-Hans.manual", ("zh-Hans", "manual")),
])
def test_parse_track_id_round_trips(track, expected):
    assert parse_track_id(track) == expected
    assert track_id(*expected) == track


@pytest.mark.parametrize("track", ["en-orig", "en.foo", ".manual", "en.", ""])
def test_parse_track_id_rejects_malformed_ids(track):
    with pytest.raises(SystemExit, match="Invalid track id"):
        parse_track_id(track)


def test_relay_command():
    assert relay_command("abc123XYZ_-", ["en.manual", "fr-orig.auto"]) == \
        "ytx_relay.bat abc123XYZ_- en.manual fr-orig.auto"


# --- the real listing ------------------------------------------------------

def test_real_listing_source_tracks(fixture_listing):
    assert [t["track"] for t in source_tracks(fixture_listing)] == ["en.manual", "en-orig.auto"]
    assert source_tracks(fixture_listing)[1] == {
        "track": "en-orig.auto", "kind": "auto", "lang": "en-orig",
        "name": "English (Original)", "source_lang": "en",
    }


def test_real_listing_counts_machine_translations(fixture_listing):
    assert machine_translation_count(fixture_listing) == 155


def test_real_listing_report(fixture_listing):
    report = summarize(fixture_listing)
    assert report["id"] == "iyJj9RxSsBY"
    assert report["duration_s"] == 2261
    assert report["original_audio_lang"] is None
    assert report["description_head"].startswith("How do you imbue character")
    assert report["recommended"] == {
        "track": "en.manual",
        "reason": "human subtitles in the spoken language (the only ASR track)",
        "ambiguous": False,
    }


# --- the real auto-dubbed listing ------------------------------------------

DUBBED_SOURCE_TRACKS = [
    "en.manual", "en-orig.auto", "fr-FR-orig.auto", "de-DE-orig.auto", "hi-orig.auto",
    "id-orig.auto", "it-orig.auto", "pt-BR-orig.auto", "es-US-orig.auto",
]


def test_real_dubbed_listing_source_tracks(dubbed_listing):
    assert [t["track"] for t in source_tracks(dubbed_listing)] == DUBBED_SOURCE_TRACKS
    assert machine_translation_count(dubbed_listing) == 152
    assert original_audio_lang(dubbed_listing) == "en-US"


def test_real_dubbed_listing_recommends_the_human_track(dubbed_listing):
    assert recommend_track(dubbed_listing) == {
        "track": "en.manual",
        "reason": "human subtitles in the spoken language (original audio track)",
        "ambiguous": False,
    }


def test_regression_real_dubbed_video_without_human_subtitles(dubbed_listing):
    """The real case behind the alphabetical-pick bug: without human subtitles, the
    alphabetically first '-orig' track of this video is the German dub."""
    info = {**dubbed_listing, "subtitles": {}}
    assert sorted(t["track"] for t in source_tracks(info))[0] == "de-DE-orig.auto"
    assert recommend_track(info) == {
        "track": "en-orig.auto",
        "reason": "ASR in the spoken language (original audio track)",
        "ambiguous": False,
    }


def test_real_dubbed_video_without_the_audio_flag_is_ambiguous(dubbed_listing):
    """Without the original-audio evidence, only YouTube's track order is left."""
    info = {**dubbed_listing, "subtitles": {}, "formats": []}
    recommended = recommend_track(info)
    assert recommended["track"] == "en-orig.auto"
    assert recommended["ambiguous"] is True


# --- the recommendation ----------------------------------------------------

RECOMMENDATION_CASES = [
    pytest.param(listing(["en", "ar"], formats=ORIGINAL_AUDIO_EN), None,
                 "en-orig.auto", False, id="auto-dub, original first, audio flag"),
    pytest.param(listing(["ar", "en"], formats=ORIGINAL_AUDIO_EN), None,
                 "en-orig.auto", False, id="auto-dub, dub first, audio flag"),
    pytest.param(listing(["en", "ar"]), None,
                 "en-orig.auto", True, id="auto-dub, original first, no audio flag"),
    pytest.param(listing(["ar", "en"]), None,
                 "ar-orig.auto", True, id="auto-dub, dub first, no audio flag"),
    pytest.param(listing(["ar", "en"]), ["en"],
                 "en-orig.auto", False, id="auto-dub, --prefer en"),
    pytest.param(listing(["en"], manual={"de": manual_track("de", "German"),
                                         "en-GB": manual_track("en-GB", "English (UK)")}), None,
                 "en-GB.manual", False, id="manual de + en-GB, ASR en"),
    pytest.param(listing(["en"], manual={"fr": manual_track("fr", "French")}), None,
                 "fr.manual", True, id="manual fr only, ASR en (human beats ASR)"),
    pytest.param(listing(["ar"]), None,
                 "ar-orig.auto", False, id="wrong-language ASR only (undetectable)"),
    pytest.param(listing(["en"], manual=LIVE_CHAT), None,
                 "en-orig.auto", False, id="live chat is not a track"),
]


@pytest.mark.parametrize("info, spoken_langs, expected_track, expected_ambiguous",
                         RECOMMENDATION_CASES)
def test_recommendation(info, spoken_langs, expected_track, expected_ambiguous):
    recommended = recommend_track(info, spoken_langs=spoken_langs)
    assert recommended["track"] == expected_track
    assert recommended["ambiguous"] is expected_ambiguous


def test_ambiguous_reason_does_not_claim_the_spoken_language():
    reason = recommend_track(listing(["ar", "en"]))["reason"]
    assert "likely spoken language" in reason


def test_no_captions_means_no_recommendation():
    assert recommend_track({"automatic_captions": {}, "subtitles": {}}) is None


def test_asr_track_without_orig_key_is_listed_under_its_plain_key():
    info = {"automatic_captions": {"yue": entry("yue", "Cantonese")}, "subtitles": {}}
    assert [t["track"] for t in source_tracks(info)] == ["yue.auto"]
    assert recommend_track(info)["track"] == "yue.auto"


def test_original_audio_lang():
    assert original_audio_lang(listing(["en"], formats=ORIGINAL_AUDIO_EN)) == "en"
    assert original_audio_lang(listing(["en"])) is None


def test_regression_alphabetical_orig_pick():
    """An auto-dubbed video once yielded its Arabic dub: '-orig' tracks were picked
    alphabetically. The pick follows evidence, then YouTube's order - never the alphabet."""
    with_audio_flag = listing(["en", "ar"], formats=ORIGINAL_AUDIO_EN)
    without_audio_flag = listing(["en", "ar"])
    assert recommend_track(with_audio_flag)["track"] == "en-orig.auto"
    assert recommend_track(without_audio_flag)["track"] == "en-orig.auto"

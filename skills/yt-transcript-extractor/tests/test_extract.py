"""The extract stage, run in-process and offline against the seeded caches."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from synthetic_listings import listing
from ytx import extract

VIDEO = "iyJj9RxSsBY"


def transcript_header(result: dict) -> str:
    path = Path(result["transcripts"][0]["path"])
    return path.read_text(encoding="utf-8").split("---", 1)[0]


def test_explicit_track_offline(seeded_out_dir, run_cli):
    exit_code, stdout = run_cli(extract.main, "--offline", "--track", "en.manual", VIDEO)
    result = json.loads(stdout)
    transcript = result["transcripts"][0]
    assert exit_code == 0
    assert transcript["track"] == "en.manual"
    assert transcript["words"] == 8100
    assert transcript["source_lang"] == "en"
    assert transcript["translated_to"] is None
    header = transcript_header(result)
    assert '- **Source:** "English" · source_lang=en · translated_to=none' in header
    assert "- **Selection:** explicit · recommended=en.manual · match=yes" in header


def test_one_shot_offline_takes_the_recommendation(seeded_out_dir, run_cli):
    _exit_code, stdout = run_cli(extract.main, "--offline", VIDEO)
    result = json.loads(stdout)
    assert result["transcripts"][0]["selection"] == "recommended"
    assert "- **Selection:** recommended\n" in transcript_header(result)


def test_offline_missing_track_names_the_relay_command(seeded_out_dir, run_cli):
    with pytest.raises(SystemExit, match="ytx_relay.bat iyJj9RxSsBY en-orig.auto"):
        run_cli(extract.main, "--offline", "--track", "en-orig.auto", VIDEO)


def test_offline_without_listing_is_refused(run_cli):
    with pytest.raises(SystemExit, match="no cached listing"):
        run_cli(extract.main, "--offline", VIDEO)


def test_offline_and_refresh_contradict(seeded_out_dir, run_cli):
    with pytest.raises(SystemExit, match="contradict"):
        run_cli(extract.main, "--offline", "--refresh", VIDEO)


def test_malformed_track_id_is_refused(seeded_out_dir, run_cli):
    with pytest.raises(SystemExit, match="Invalid track id"):
        run_cli(extract.main, "--offline", "--track", "en-orig", VIDEO)


def test_unknown_track_lists_the_source_tracks(seeded_out_dir, run_cli):
    with pytest.raises(SystemExit, match="Source tracks: en.manual, en-orig.auto"):
        run_cli(extract.main, "--offline", "--track", "xx.manual", VIDEO)


def test_expired_urls_stop_before_any_request(seeded_out_dir, run_cli):
    """Not offline, raw file missing, URLs expired: the expiry guard must stop the
    run. Reaching the network guard instead would mean a request was attempted."""
    with pytest.raises(SystemExit, match="expired"):
        run_cli(extract.main, "--track", "en-orig.auto", VIDEO)


def test_also_translation_adds_a_reading_language():
    picks = extract.choose_tracks(listing(["en"]), also_translation=True)
    assert [(p["lang"], p["kind"], p["selection"]) for p in picks] == [
        ("en-orig", "auto", "recommended"),
        ("de", "auto", "translation"),
    ]

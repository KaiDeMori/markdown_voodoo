"""The probe stage, run in-process and offline against the seeded caches."""
from __future__ import annotations

import json

import pytest

from ytx import probe

VIDEO = "iyJj9RxSsBY"


def test_offline_probe_reports_samples_and_rates(seeded_out_dir, run_cli):
    exit_code, stdout = run_cli(probe.main, VIDEO, "--tracks", "en.manual", "--offline")
    (result,) = json.loads(stdout)["probes"]
    assert exit_code == 0
    assert result["track"] == "en.manual"
    assert result["words"] == 8100
    assert result["words_per_minute"] == 215
    assert result["sample_start"].startswith("- [Stuart] Hello")
    assert result["sample_middle"]


def test_more_tracks_than_the_cap_are_refused(seeded_out_dir, run_cli):
    with pytest.raises(SystemExit, match="At most 2 tracks"):
        run_cli(probe.main, VIDEO, "--tracks", "en.manual,en-orig.auto,de.auto", "--offline")


def test_duplicate_track_ids_count_once(seeded_out_dir, run_cli):
    _exit_code, stdout = run_cli(probe.main, VIDEO, "--tracks", "en.manual,en.manual", "--offline")
    assert len(json.loads(stdout)["probes"]) == 1


def test_unknown_track_is_refused(seeded_out_dir, run_cli):
    with pytest.raises(SystemExit, match="not offered"):
        run_cli(probe.main, VIDEO, "--tracks", "xx.manual", "--offline")


def test_one_video_per_call(seeded_out_dir, run_cli):
    exit_code, stdout = run_cli(probe.main, VIDEO, "abcdefghijk", "--tracks", "en.manual")
    assert exit_code == 2
    assert stdout.startswith("Stage 2b - probe")


def test_offline_missing_track_names_the_relay_command(seeded_out_dir, run_cli):
    with pytest.raises(SystemExit, match="ytx_relay.bat iyJj9RxSsBY en-orig.auto"):
        run_cli(probe.main, VIDEO, "--tracks", "en-orig.auto", "--offline")

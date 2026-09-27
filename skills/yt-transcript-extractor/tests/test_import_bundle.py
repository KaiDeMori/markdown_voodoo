"""Importing relay bundles: the documented layout passes, anything else is rejected."""
from __future__ import annotations

import json
import zipfile

import pytest

from conftest import FIXTURE_CAPTION, FIXTURE_LISTING
from ytx import extract, import_bundle

VIDEO = "iyJj9RxSsBY"
OTHER_VIDEO = "OTHERVIDEO1"


def valid_members() -> dict[str, bytes]:
    return {
        f"{VIDEO}.info.json": FIXTURE_LISTING.read_bytes(),
        f"manual/{VIDEO}.en.json3": FIXTURE_CAPTION.read_bytes(),
    }


def write_bundle(path, members: dict[str, bytes]):
    """A zip laid out like the one ytx_relay.bat writes, 7-Zip's folder entries included."""
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("auto/", b"")
        bundle.writestr("manual/", b"")
        for name, data in members.items():
            bundle.writestr(name, data)
    return path


def test_import_fills_meta_and_raw(tmp_path, isolated_output, run_cli):
    bundle = write_bundle(tmp_path / f"{VIDEO}.ytx.zip", valid_members())
    exit_code, stdout = run_cli(import_bundle.main, str(bundle))
    report = json.loads(stdout)
    assert exit_code == 0
    assert (isolated_output / "meta" / f"{VIDEO}.info.json").is_file()
    assert (isolated_output / "meta" / f"{VIDEO}.subs.json").is_file()
    assert (isolated_output / "raw" / f"{VIDEO}.en.manual.json3").read_bytes() == \
        FIXTURE_CAPTION.read_bytes()
    assert report["recommended"]["track"] == "en.manual"
    assert report["bundle"]["tracks_in_raw"] == ["en.manual"]
    assert report["bundle"]["source_tracks_missing"] == ["en-orig.auto"]
    assert report["bundle"]["relay_command"] == f"ytx_relay.bat {VIDEO} <track> [<track> ...]"
    assert report["bundle"]["yt_dlp_version"] == "2026.06.09"


def test_reimport_keeps_existing_raw_files(tmp_path, isolated_output, run_cli):
    bundle = write_bundle(tmp_path / f"{VIDEO}.ytx.zip", valid_members())
    run_cli(import_bundle.main, str(bundle))
    raw = isolated_output / "raw" / f"{VIDEO}.en.manual.json3"
    raw.write_bytes(b"already here")
    run_cli(import_bundle.main, str(bundle))
    assert raw.read_bytes() == b"already here"


def test_import_then_extract_offline(tmp_path, run_cli):
    bundle = write_bundle(tmp_path / f"{VIDEO}.ytx.zip", valid_members())
    run_cli(import_bundle.main, str(bundle))
    _exit_code, stdout = run_cli(extract.main, "--offline", "--track", "en.manual", VIDEO)
    assert json.loads(stdout)["transcripts"][0]["words"] == 8100


def with_member(name, data=b"x"):
    return {**valid_members(), name: data}


REJECTED_BUNDLES = [
    pytest.param(with_member("../evil.txt"), "unexpected member", id="parent path"),
    pytest.param(with_member("manual/../evil.json3"), "unexpected member", id="parent inside folder"),
    pytest.param(with_member("notes.txt"), "unexpected member", id="stray file"),
    pytest.param(with_member(f"manual/{OTHER_VIDEO}.en.json3"), "another video", id="caption of another video"),
    pytest.param(with_member(f"{OTHER_VIDEO}.info.json", b"{}"), "exactly one", id="two listings"),
    pytest.param({f"manual/{VIDEO}.en.json3": b"x"}, "found 0", id="no listing"),
    pytest.param({f"{OTHER_VIDEO}.info.json": FIXTURE_LISTING.read_bytes()},
                 "the listing is for", id="listing id differs from its name"),
]


@pytest.mark.parametrize("members, reason", REJECTED_BUNDLES)
def test_malformed_bundles_are_rejected(tmp_path, isolated_output, run_cli, members, reason):
    bundle = write_bundle(tmp_path / "bundle.ytx.zip", members)
    with pytest.raises(SystemExit, match=reason):
        run_cli(import_bundle.main, str(bundle))
    assert not (isolated_output / "raw").exists() or not any((isolated_output / "raw").iterdir())


def test_a_file_that_is_not_a_zip_is_rejected(tmp_path, run_cli):
    not_a_zip = tmp_path / "bundle.ytx.zip"
    not_a_zip.write_text("not a zip", encoding="utf-8")
    with pytest.raises(SystemExit, match="Cannot open bundle"):
        run_cli(import_bundle.main, str(not_a_zip))

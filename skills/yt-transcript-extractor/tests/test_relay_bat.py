"""The relay batch file, run for real through cmd.exe behind a dead proxy.

yt-dlp runs as a separate process, which the in-process socket guard cannot reach.
Instead every run gets HTTP(S)_PROXY pointing at a closed local port, and its config,
home and temp folders point into the test folder - so no config on this machine can
bring its own proxy. The session starts with a canary request that must be refused;
otherwise no batch test runs.

Round-1 listings come from fixtures: a test variant of the batch copies a listing
where the production script asks yt-dlp for one. Everything after that - the id
check, counting, fetching, bundling - is the production code.

Slow, so excluded by default:  "$PY" -m pytest -m relay_bat
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from conftest import (
    FIXTURE_DUBBED_LISTING,
    FIXTURE_DUBBED_VIDEO_ID,
    FIXTURE_LISTING,
    FIXTURE_VIDEO_ID,
    PROJECT_DIR,
)
from ytx import import_bundle

pytestmark = [
    pytest.mark.relay_bat,
    pytest.mark.skipif(sys.platform != "win32", reason="batch files need cmd.exe"),
    pytest.mark.skipif(shutil.which("7z") is None, reason="the bundle needs 7-Zip on PATH"),
]

RELAY_BAT = PROJECT_DIR / "relay" / "ytx_relay.bat"
VENV_YTDLP = PROJECT_DIR / ".venv" / "Scripts" / "yt-dlp.exe"
DEAD_PROXY = "http://127.0.0.1:9"
CONNECTION_REFUSED = "10061"
# Loaded the way a user's own yt-dlp.conf is; keeps refused requests fast.
TEST_YTDLP_CONFIG = "--retries 0\n--extractor-retries 0\n--no-cache-dir\n"

LISTING_CALL_START = '"%YTDLP%" %SHARED% --no-simulate --sleep-requests 2'
LISTING_CALL_END = '"%URL%"'
EXPLORER_CALL = 'explorer /select,"%SCRIPT_DIR%%BUNDLE%"'

VIDEO_URL = f"https://www.youtube.com/watch?v={FIXTURE_VIDEO_ID}&t=10s"
DUBBED_VIDEO_URL = f"https://www.youtube.com/watch?v={FIXTURE_DUBBED_VIDEO_ID}"
LISTING_ONLY = ["auto/", f"{FIXTURE_VIDEO_ID}.info.json", "manual/"]


def isolated_environment(root: Path) -> dict[str, str]:
    for name in ("config", "appdata", "home", "temp"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "config" / "yt-dlp.conf").write_text(TEST_YTDLP_CONFIG, encoding="utf-8")
    environment = {name: value for name, value in os.environ.items()
                   if not name.lower().endswith("_proxy")}
    environment.update({
        "HTTP_PROXY": DEAD_PROXY,
        "HTTPS_PROXY": DEAD_PROXY,
        "XDG_CONFIG_HOME": str(root / "config"),
        "APPDATA": str(root / "appdata"),
        "LOCALAPPDATA": str(root / "appdata"),
        "USERPROFILE": str(root / "home"),
        "HOME": str(root / "home"),
        "TEMP": str(root / "temp"),
        "TMP": str(root / "temp"),
    })
    return environment


@pytest.fixture(scope="session")
def dead_proxy_verified(tmp_path_factory):
    environment = isolated_environment(tmp_path_factory.mktemp("canary"))
    result = subprocess.run(
        [str(VENV_YTDLP), "--skip-download", "https://example.com"],
        env=environment, capture_output=True, encoding="utf-8", errors="replace", timeout=120)
    output = result.stdout + result.stderr
    if result.returncode == 0 or CONNECTION_REFUSED not in output:
        pytest.exit("The dead proxy did not stop yt-dlp - no batch test runs.\n" + output,
                    returncode=3)


class Relay_folder:
    """A test copy of the batch next to yt-dlp.exe, in a folder whose name has a space."""

    def __init__(self, root: Path):
        self.root = root
        self.folder = root / "tools folder"
        self.folder.mkdir()
        shutil.copy(VENV_YTDLP, self.folder)
        self.relay_dir = self.folder / "ytx_relay"
        self.script = self.folder / RELAY_BAT.name
        self.environment = isolated_environment(root / "environment")
        self.write_script(replace_once(self.production_text(), EXPLORER_CALL,
                                       "rem Explorer is not opened in tests."))

    @staticmethod
    def production_text() -> str:
        return RELAY_BAT.read_bytes().decode("ascii")

    def write_script(self, text: str):
        self.script.write_bytes(text.encode("ascii"))

    def use_listing_from(self, listing: Path, file_name: str | None = None):
        """Round 1 copies this listing instead of asking yt-dlp for it."""
        text = self.script.read_bytes().decode("ascii")
        assert text.count(LISTING_CALL_START) == 1, "the listing call changed; update the test"
        start = text.index(LISTING_CALL_START)
        end = text.index(LISTING_CALL_END, start) + len(LISTING_CALL_END)
        copy_command = f'copy "{listing}" "%INCOMING%\\{file_name or listing.name}" >nul'
        self.write_script(text[:start] + copy_command + text[end:])

    def seed_work_folder(self, listing: Path, video_id: str):
        work = self.relay_dir / video_id
        work.mkdir(parents=True)
        shutil.copy(listing, work / f"{video_id}.info.json")

    def run(self, *arguments: str) -> tuple[int, str]:
        """Runs the script from another folder, as a user would; returns (exit code, output)."""
        quoted = " ".join(f'"{argument}"' for argument in arguments)
        result = subprocess.run(
            f'cmd.exe /d /s /c ""{self.script}" {quoted}"',
            cwd=self.root, env=self.environment, capture_output=True,
            encoding="utf-8", errors="replace", timeout=300)
        output = result.stdout + result.stderr
        assert str(self.root).lower() not in output.lower(), "the output shows an absolute path"
        return result.returncode, output


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"{old!r} changed in the batch; update the test"
    return text.replace(old, new)


def bundle_members(bundle: Path) -> list[str]:
    with zipfile.ZipFile(bundle) as archive:
        return sorted(archive.namelist())


def assert_no_extraction(output: str):
    assert "Extracting URL" not in output
    assert "trying with URL" not in output


@pytest.fixture
def relay(tmp_path, dead_proxy_verified) -> Relay_folder:
    return Relay_folder(tmp_path)


# --- usage -----------------------------------------------------------------

def test_usage_names_the_script(relay):
    exit_code, output = relay.run()
    assert exit_code == 2
    assert 'ytx_relay.bat "URL"' in output


# --- round 1 ---------------------------------------------------------------

def test_round_1_listing_failure_stops_cleanly(relay):
    exit_code, output = relay.run(VIDEO_URL)
    assert exit_code == 1
    assert CONNECTION_REFUSED in output
    assert "No listing was written" in output
    assert not list(relay.relay_dir.glob("*.ytx.zip"))


def test_round_1_fetches_the_source_tracks_and_bundles(relay, run_cli):
    relay.use_listing_from(FIXTURE_LISTING)
    exit_code, output = relay.run(VIDEO_URL)
    assert exit_code == 0
    assert "selected 2 tracks - ASR: [en-orig]  manual: [en]" in output
    assert "fetching auto captions: en-orig" in output
    assert "fetching manual captions: en" in output
    assert f"Writing video subtitles to: ytx_relay\\{FIXTURE_VIDEO_ID}\\auto\\" in output
    assert_no_extraction(output)

    bundle = relay.relay_dir / f"{FIXTURE_VIDEO_ID}.ytx.zip"
    assert bundle_members(bundle) == LISTING_ONLY
    _exit_code, stdout = run_cli(import_bundle.main, str(bundle))
    assert json.loads(stdout)["bundle"]["source_tracks_missing"] == ["en.manual", "en-orig.auto"]


def test_round_1_matches_manual_tracks_on_the_base_language(relay, tmp_path):
    """fr-FR-orig must also find a manual track tagged plain fr."""
    listing = json.loads(FIXTURE_DUBBED_LISTING.read_text(encoding="utf-8"))
    listing["subtitles"]["fr"] = [{**entry, "name": "French"} for entry in listing["subtitles"]["en"]]
    variant = tmp_path / FIXTURE_DUBBED_LISTING.name
    variant.write_text(json.dumps(listing), encoding="utf-8")
    relay.use_listing_from(variant)

    exit_code, output = relay.run(DUBBED_VIDEO_URL)
    assert exit_code == 0
    assert ("selected 10 tracks - ASR: [en-orig,fr-FR-orig,de-DE-orig,hi-orig,id-orig,"
            "it-orig,pt-BR-orig,es-US-orig]  manual: [en,fr]") in output
    assert "More than 8 tracks - bundling the listing only." in output
    assert "fetching" not in output
    assert bundle_members(relay.relay_dir / f"{FIXTURE_DUBBED_VIDEO_ID}.ytx.zip") == \
        ["auto/", f"{FIXTURE_DUBBED_VIDEO_ID}.info.json", "manual/"]


def test_round_1_refuses_a_listing_with_an_invalid_id(relay):
    relay.use_listing_from(FIXTURE_LISTING, file_name="bad.id.info.json")
    exit_code, output = relay.run(VIDEO_URL)
    assert exit_code == 1
    assert 'Refusing video id "bad.id"' in output
    assert not (relay.relay_dir / "bad.id").exists()


# --- round 2 ---------------------------------------------------------------

def test_round_2_fetches_named_tracks_without_extraction(relay):
    relay.seed_work_folder(FIXTURE_DUBBED_LISTING, FIXTURE_DUBBED_VIDEO_ID)
    exit_code, output = relay.run(FIXTURE_DUBBED_VIDEO_ID, "en.manual", "fr-FR-orig.auto")
    assert exit_code == 0
    assert f"round 2 for {FIXTURE_DUBBED_VIDEO_ID} - ASR: [fr-FR-orig]  manual: [en]" in output
    assert CONNECTION_REFUSED in output
    assert_no_extraction(output)
    assert (relay.relay_dir / f"{FIXTURE_DUBBED_VIDEO_ID}.ytx.zip").is_file()


@pytest.mark.parametrize("tracks, message", [
    (["en.foo"], "Invalid track id"),
    ([f"l{number}.auto" for number in range(9)], "More than 8 tracks requested"),
], ids=["unknown kind", "nine tracks"])
def test_round_2_refuses_bad_track_lists(relay, tracks, message):
    relay.seed_work_folder(FIXTURE_LISTING, FIXTURE_VIDEO_ID)
    exit_code, output = relay.run(FIXTURE_VIDEO_ID, *tracks)
    assert exit_code == 1
    assert message in output


def test_round_2_needs_the_round_1_listing(relay):
    exit_code, output = relay.run("NOLISTING01", "en.manual")
    assert exit_code == 1
    assert "run round 1 first" in output


@pytest.mark.parametrize("video_id", ["..", ".", "a\\b", "x.y", "C:", "a&b", "a b"])
def test_invalid_video_ids_are_refused_before_any_file_operation(relay, video_id):
    relay.relay_dir.mkdir()
    sentinels = [relay.folder / "sentinel.txt", relay.relay_dir / "sentinel.txt"]
    for sentinel in sentinels:
        sentinel.write_text("still here", encoding="utf-8")
    exit_code, output = relay.run(video_id, "en.manual")
    assert exit_code == 1
    assert "Refusing video id" in output
    assert all(sentinel.is_file() for sentinel in sentinels)


def test_an_empty_video_id_shows_the_usage(relay):
    exit_code, output = relay.run("", "en.manual")
    assert exit_code == 2
    assert "Usage:" in output

"""Shared test setup: no network, no writes outside the project, seeded caches.

Every test runs with all socket operations refused, so no test can reach
YouTube - or resolve its name - even by mistake. Every test also points the
output base at its own tmp_path, and every tmp_path lives inside the project
(pytest.ini sets --basetemp), never in the system temp folder.
"""
from __future__ import annotations

import json
import shutil
import socket
from pathlib import Path

import pytest

from ytx import config

PROJECT_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_VIDEO_ID = "iyJj9RxSsBY"
FIXTURE_LISTING = FIXTURES_DIR / f"{FIXTURE_VIDEO_ID}.info.json"
FIXTURE_CAPTION = FIXTURES_DIR / f"{FIXTURE_VIDEO_ID}.en.manual.json3"
# An auto-dubbed video from a relay fetch: eight ASR tracks, one per dub, and the
# audio track YouTube flags as original.
FIXTURE_DUBBED_VIDEO_ID = "hBB__YXYpOc"
FIXTURE_DUBBED_LISTING = FIXTURES_DIR / f"{FIXTURE_DUBBED_VIDEO_ID}.info.json"
# Japanese ASR carries no sentence punctuation at all.
UNPUNCTUATED_CAPTION_LINES = [f"今日は{number}番目の話題について少し詳しく説明していきます"
                              for number in range(300)]


class Network_blocked(RuntimeError):
    pass


def refuse_network(*args, **kwargs):
    raise Network_blocked("tests never touch the network")


@pytest.fixture(scope="session", autouse=True)
def temp_stays_in_project(request):
    """Stop before the first tmp_path is created if it would land outside the project -
    e.g. when pytest runs from another folder and the relative --basetemp moves along."""
    basetemp = request.config.option.basetemp
    if not basetemp or PROJECT_DIR not in Path(basetemp).resolve().parents:
        pytest.exit(f"tmp_path would leave the project ({basetemp!r}); "
                    f"run pytest from {PROJECT_DIR}", returncode=4)


@pytest.fixture(autouse=True)
def network_guard(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", refuse_network)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse_network)
    monkeypatch.setattr(socket, "create_connection", refuse_network)
    monkeypatch.setattr(socket, "getaddrinfo", refuse_network)


@pytest.fixture(autouse=True)
def isolated_output(tmp_path) -> Path:
    out_dir = tmp_path / "out"
    config.configure(out_dir)
    return out_dir


@pytest.fixture
def seeded_out_dir(isolated_output) -> Path:
    """An out-dir holding the real listing in meta/ and its manual caption in raw/."""
    (isolated_output / "meta").mkdir(parents=True)
    (isolated_output / "raw").mkdir()
    shutil.copy(FIXTURE_LISTING, isolated_output / "meta")
    shutil.copy(FIXTURE_CAPTION, isolated_output / "raw")
    return isolated_output


@pytest.fixture
def unpunctuated_asr_track(seeded_out_dir) -> Path:
    """UNPUNCTUATED_CAPTION_LINES as the json3 of the ASR track the fixture listing offers.

    The failure needs only length, not a real quirk, so the caption file is synthetic.
    """
    events = [{"tStartMs": number * 3000, "dDurationMs": 3000, "segs": [{"utf8": line}]}
              for number, line in enumerate(UNPUNCTUATED_CAPTION_LINES)]
    raw_file = seeded_out_dir / "raw" / f"{FIXTURE_VIDEO_ID}.en-orig.auto.json3"
    raw_file.write_text(json.dumps({"events": events}, ensure_ascii=False), encoding="utf-8")
    return raw_file


@pytest.fixture(scope="session")
def fixture_listing() -> dict:
    """The real listing, shared read-only across tests."""
    return json.loads(FIXTURE_LISTING.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def dubbed_listing() -> dict:
    """The real auto-dubbed listing, shared read-only: derive variants with {**listing, ...}."""
    return json.loads(FIXTURE_DUBBED_LISTING.read_text(encoding="utf-8"))


@pytest.fixture
def run_cli(capsys, isolated_output):
    """Run a stage's main() in-process against the isolated out-dir.

    Returns (exit code, stdout). Errors surface as SystemExit, for pytest.raises.
    """
    def run(stage_main, *args: str) -> tuple[int, str]:
        exit_code = stage_main(["--out-dir", str(isolated_output), *args])
        return exit_code, capsys.readouterr().out
    return run

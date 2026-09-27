"""Shared test setup: no network, no writes outside tmp_path, seeded caches.

Every test runs with all socket operations refused, so no test can reach
YouTube - or resolve its name - even by mistake. Every test also points the
output base at its own tmp_path, so nothing lands in the repo.
"""
from __future__ import annotations

import json
import shutil
import socket
from pathlib import Path

import pytest

from ytx import config

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURE_VIDEO_ID = "iyJj9RxSsBY"
FIXTURE_LISTING = FIXTURES_DIR / f"{FIXTURE_VIDEO_ID}.info.json"
FIXTURE_CAPTION = FIXTURES_DIR / f"{FIXTURE_VIDEO_ID}.en.manual.json3"


class Network_blocked(RuntimeError):
    pass


def refuse_network(*args, **kwargs):
    raise Network_blocked("tests never touch the network")


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


@pytest.fixture(scope="session")
def fixture_listing() -> dict:
    """The real listing, shared read-only across tests."""
    return json.loads(FIXTURE_LISTING.read_text(encoding="utf-8"))


@pytest.fixture
def run_cli(capsys, isolated_output):
    """Run a stage's main() in-process against the isolated out-dir.

    Returns (exit code, stdout). Errors surface as SystemExit, for pytest.raises.
    """
    def run(stage_main, *args: str) -> tuple[int, str]:
        exit_code = stage_main(["--out-dir", str(isolated_output), *args])
        return exit_code, capsys.readouterr().out
    return run

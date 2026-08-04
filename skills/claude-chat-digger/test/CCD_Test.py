"""Minimal isolated round-trip test for CCD's index/search — see Test_idea.md.

Uses a scratch corpus and scratch index under this directory; never touches the real
~/.claude corpus or index.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIRECTORY.parent
sys.path.insert(0, str(SKILL_ROOT))

from CCD_engine import Chat_digger

EXAMPLE_CHAT_DIRECTORY = SCRIPT_DIRECTORY / "example_chat"
SCRATCH_DIRECTORY = SCRIPT_DIRECTORY / "scratch"
SCRATCH_CORPUS_ROOT = SCRATCH_DIRECTORY / "corpus"
SCRATCH_INDEX_PATH = SCRATCH_DIRECTORY / "CCD_index.db"

UNIQUE_STRING = "hyednesenc"
EXPECTED_SESSION_ID = "a90d5763-7f6a-4139-9226-d4684f23f3e3"


def reset_scratch_directory() -> None:
    if SCRATCH_DIRECTORY.exists():
        shutil.rmtree(SCRATCH_DIRECTORY)
    SCRATCH_CORPUS_ROOT.mkdir(parents=True)


def inject_example_chat() -> None:
    shutil.copytree(EXAMPLE_CHAT_DIRECTORY, SCRATCH_CORPUS_ROOT, dirs_exist_ok=True)


def main() -> None:
    reset_scratch_directory()
    digger = Chat_digger(index_path=str(SCRATCH_INDEX_PATH), corpus_root=str(SCRATCH_CORPUS_ROOT))

    empty_stats = digger.build_index()
    assert empty_stats.conversation_count == 0, "scratch corpus should start empty"

    before = digger.search_all(UNIQUE_STRING)
    assert before.total_matches == 0, "unique string must not be found before injection"
    print("ok: '%s' not found before injection" % UNIQUE_STRING)

    inject_example_chat()
    after_stats = digger.build_index()
    assert after_stats.conversation_count == 1, "expected exactly one indexed conversation after injection"

    after = digger.search_all(UNIQUE_STRING)
    assert after.total_matches > 0, "unique string must be found after injection"
    session_ids = [conversation.session_id for conversation in after.conversations]
    assert EXPECTED_SESSION_ID in session_ids, "expected session %s in results, got %s" % (
        EXPECTED_SESSION_ID,
        session_ids,
    )
    print("ok: '%s' found in session %s after injection" % (UNIQUE_STRING, EXPECTED_SESSION_ID))

    shutil.rmtree(SCRATCH_DIRECTORY)
    print("PASS")


if __name__ == "__main__":
    main()

"""Minimal isolated tests for CCD's index/search - see Test_idea.md.

Uses a scratch corpus and scratch index under this directory; never touches the real
~/.claude corpus or index. One test function per search mode, run against a single
index build of the injected example chat.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIRECTORY.parent
sys.path.insert(0, str(SKILL_ROOT))

from CCD_api import Match_mode, Search_options
from CCD_engine import Chat_digger

EXAMPLE_CHAT_DIRECTORY = SCRIPT_DIRECTORY / "example_chat"
SCRATCH_DIRECTORY = SCRIPT_DIRECTORY / "scratch"
SCRATCH_CORPUS_ROOT = SCRATCH_DIRECTORY / "corpus"
SCRATCH_INDEX_PATH = SCRATCH_DIRECTORY / "CCD_index.db"

UNIQUE_STRING = "hyednesenc"
EXPECTED_SESSION_ID = "a90d5763-7f6a-4139-9226-d4684f23f3e3"
FIZOTONITU_ANSWER_UUID = "ebc2f46e-58b5-423c-a85f-c5be094fef56"
HYEDNESENC_ANSWER_UUID = "3b5ccc09-fca3-4924-8428-bbf0576e7fda"


def reset_scratch_directory() -> None:
    if SCRATCH_DIRECTORY.exists():
        shutil.rmtree(SCRATCH_DIRECTORY)
    SCRATCH_CORPUS_ROOT.mkdir(parents=True)


def inject_example_chat() -> None:
    shutil.copytree(EXAMPLE_CHAT_DIRECTORY, SCRATCH_CORPUS_ROOT, dirs_exist_ok=True)


def test_substring_mode_round_trip(digger: Chat_digger) -> None:
    before = digger.search_all(UNIQUE_STRING)
    assert before.total_matches == 0, "unique string must not be found before injection"

    inject_example_chat()
    stats = digger.build_index()
    assert stats.conversation_count == 1, "expected exactly one indexed conversation after injection"

    after = digger.search_all(UNIQUE_STRING)
    assert after.total_matches > 0, "unique string must be found after injection"
    session_ids = [conversation.session_id for conversation in after.conversations]
    assert EXPECTED_SESSION_ID in session_ids, "expected session %s in results, got %s" % (
        EXPECTED_SESSION_ID,
        session_ids,
    )
    print("ok: substring - '%s' not found before injection, found in %s after" % (UNIQUE_STRING, EXPECTED_SESSION_ID))


def test_all_terms_mode(digger: Chat_digger) -> None:
    options = Search_options(match_mode=Match_mode.all_terms)

    positive = digger.search_all("drawer motivation", options)
    assert positive.total_conversations == 1, "both terms appear together only in the fizotonitu answer"
    matched_uuids = {entry.uuid for entry in positive.conversations[0].matched_chat_entries}
    assert matched_uuids == {FIZOTONITU_ANSWER_UUID}, "expected only the fizotonitu answer, got %s" % matched_uuids

    negative = digger.search_all("drawer hyednesenc", options)
    assert negative.total_matches == 0, "terms from different entries must not match under all_terms"
    print("ok: all_terms - requires every term in the same entry, not a union across entries")


def test_wildcard_mode(digger: Chat_digger) -> None:
    options = Search_options(match_mode=Match_mode.wildcard)
    result = digger.search_in_conversation(EXPECTED_SESSION_ID, "hyednesenc*", options)
    entry = next(item for item in result.chat_entries if item.uuid == HYEDNESENC_ANSWER_UUID)
    assert len(entry.snippets) > 1, "'hyednesenc*' must find hyednesenc/hyednesencing/hyednesencic as separate matches"
    assert all(len(snippet.match) < 20 for snippet in entry.snippets), "a greedy '*' would swallow everything up to the last match"
    print("ok: wildcard - '*' is non-greedy, occurrences stay separate")


def test_regex_mode_is_reserved(digger: Chat_digger) -> None:
    options = Search_options(match_mode=Match_mode.regex)
    try:
        digger.search_all(UNIQUE_STRING, options)
    except NotImplementedError:
        print("ok: regex - reserved, raises NotImplementedError")
    else:
        raise AssertionError("regex mode should raise NotImplementedError")


def main() -> None:
    reset_scratch_directory()
    digger = Chat_digger(index_path=str(SCRATCH_INDEX_PATH), corpus_root=str(SCRATCH_CORPUS_ROOT))

    empty_stats = digger.build_index()
    assert empty_stats.conversation_count == 0, "scratch corpus should start empty"

    test_substring_mode_round_trip(digger)
    test_all_terms_mode(digger)
    test_wildcard_mode(digger)
    test_regex_mode_is_reserved(digger)

    shutil.rmtree(SCRATCH_DIRECTORY)
    print("PASS")


if __name__ == "__main__":
    main()

"""Minimal isolated tests for CCD's index/search - see Test_idea.md.

Uses a scratch corpus and scratch index under this directory; never touches the real
~/.claude corpus or index. One test function per search mode, plus a few checks on
indexing behaviour deliberately baked into the example chat, all run against a single
index build of the injected example chat.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIRECTORY.parent
sys.path.insert(0, str(SKILL_ROOT))

from CCD_api import Match_mode, Search_options, Search_role
from CCD_engine import Chat_digger

EXAMPLE_CHAT_DIRECTORY = SCRIPT_DIRECTORY / "example_chat"
SCRATCH_DIRECTORY = SCRIPT_DIRECTORY / "scratch"
SCRATCH_CORPUS_ROOT = SCRATCH_DIRECTORY / "corpus"
SCRATCH_INDEX_PATH = SCRATCH_DIRECTORY / "CCD_index.db"

UNIQUE_STRING = "hyednesenc"
EXPECTED_SESSION_ID = "a90d5763-7f6a-4139-9226-d4684f23f3e3"
EXPECTED_MODEL = "claude-sonnet-5"
FIZOTONITU_QUESTION_UUID = "31af7b9a-30a9-4e07-a364-6c49cbddb08f"
FIZOTONITU_ANSWER_UUID = "ebc2f46e-58b5-423c-a85f-c5be094fef56"
HYEDNESENC_QUESTION_UUID = "59813b71-984a-4e58-acdf-57381e0853c2"
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


def test_machine_wrapper_is_not_indexed(digger: Chat_digger) -> None:
    result = digger.search_all("Test_idea.md")
    assert result.total_matches == 0, "an <ide_opened_file> wrapper block must never be indexed as user content"
    print("ok: machine wrapper - <ide_opened_file> block is excluded from the index")


def test_streamed_duplicate_dedup(digger: Chat_digger) -> None:
    conversations = digger.list_conversations()
    conversation = next(item for item in conversations if item.session_id == EXPECTED_SESSION_ID)
    assert conversation.chat_entry_count == 4, (
        "expected 4 entries (2 user, 2 assistant) once the streamed thinking-stub duplicate collapses "
        "into its final copy, got %d" % conversation.chat_entry_count
    )
    print("ok: dedup - streamed thinking-stub duplicate collapses into its final message.id copy")


def test_role_filter(digger: Chat_digger) -> None:
    user_only = digger.search_all("fizotonitu", Search_options(roles=Search_role.user))
    user_uuids = {entry.uuid for conversation in user_only.conversations for entry in conversation.matched_chat_entries}
    assert user_uuids == {FIZOTONITU_QUESTION_UUID}, "role=user must find only the question, got %s" % user_uuids

    assistant_only = digger.search_all("fizotonitu", Search_options(roles=Search_role.assistant))
    assistant_uuids = {
        entry.uuid for conversation in assistant_only.conversations for entry in conversation.matched_chat_entries
    }
    assert assistant_uuids == {FIZOTONITU_ANSWER_UUID}, "role=assistant must find only the answer, got %s" % assistant_uuids
    print("ok: role filter - user/assistant each restrict to their own side")


def test_case_sensitivity(digger: Chat_digger) -> None:
    exact = digger.search_all("Hyednesenc", Search_options(case_sensitive=True))
    exact_uuids = {entry.uuid for conversation in exact.conversations for entry in conversation.matched_chat_entries}
    assert exact_uuids == {HYEDNESENC_ANSWER_UUID}, (
        "case-sensitive 'Hyednesenc' must miss the lowercase question, got %s" % exact_uuids
    )

    insensitive = digger.search_all("Hyednesenc")
    insensitive_uuids = {
        entry.uuid for conversation in insensitive.conversations for entry in conversation.matched_chat_entries
    }
    assert HYEDNESENC_QUESTION_UUID in insensitive_uuids, "case-insensitive search must also find the lowercase question"
    print("ok: case sensitivity - --case-sensitive distinguishes 'Hyednesenc' from 'hyednesenc'")


def test_model_is_indexed(digger: Chat_digger) -> None:
    connection = digger._open_for_read()
    models_by_role = {
        row["role"]: set(row["models"].split(",")) if row["models"] else set()
        for row in connection.execute(
            "SELECT role, GROUP_CONCAT(DISTINCT model) AS models FROM blocks WHERE session_id = ? GROUP BY role",
            (EXPECTED_SESSION_ID,),
        ).fetchall()
    }
    model_counts = [
        (row["model"], row["message_count"])
        for row in connection.execute(
            "SELECT model, message_count FROM conversation_models WHERE session_id = ?", (EXPECTED_SESSION_ID,)
        ).fetchall()
    ]
    connection.close()
    assert models_by_role.get("assistant") == {EXPECTED_MODEL}, (
        "every assistant block must carry the message's model, got %s" % models_by_role.get("assistant")
    )
    assert models_by_role.get("user") == set(), "user blocks carry no model, got %s" % models_by_role.get("user")
    assert model_counts == [(EXPECTED_MODEL, 2)], (
        "expected one model row counting the 2 deduplicated assistant entries, got %s" % model_counts
    )
    print("ok: model - assistant blocks carry '%s', user blocks none, conversation_models counts 2 entries" % EXPECTED_MODEL)


def test_model_filter(digger: Chat_digger) -> None:
    matching = digger.search_all("fizotonitu", Search_options(model=EXPECTED_MODEL))
    matching_uuids = {entry.uuid for conversation in matching.conversations for entry in conversation.matched_chat_entries}
    assert matching_uuids == {FIZOTONITU_ANSWER_UUID}, "model filter must keep only the assistant answer, got %s" % matching_uuids

    other = digger.search_all("fizotonitu", Search_options(model="claude-opus-5"))
    assert other.total_matches == 0, "a model that never answered must match nothing"
    print("ok: model filter - restricts to assistant entries answered by the given model")


def test_list_models(digger: Chat_digger) -> None:
    result = digger.list_models(EXPECTED_SESSION_ID)
    usages = [(usage.model, usage.message_count) for usage in result.models]
    assert usages == [(EXPECTED_MODEL, 2)], "expected the one model with 2 deduplicated answers, got %s" % usages
    try:
        digger.list_models("no-such-session")
    except ValueError:
        pass
    else:
        raise AssertionError("an unknown session_id must raise ValueError")
    print("ok: models - lists '%s' with 2 messages, unknown session raises" % EXPECTED_MODEL)


def main() -> None:
    reset_scratch_directory()
    digger = Chat_digger(index_path=str(SCRATCH_INDEX_PATH), corpus_root=str(SCRATCH_CORPUS_ROOT))

    empty_stats = digger.build_index()
    assert empty_stats.conversation_count == 0, "scratch corpus should start empty"

    test_substring_mode_round_trip(digger)
    test_all_terms_mode(digger)
    test_wildcard_mode(digger)
    test_regex_mode_is_reserved(digger)
    test_machine_wrapper_is_not_indexed(digger)
    test_streamed_duplicate_dedup(digger)
    test_role_filter(digger)
    test_case_sensitivity(digger)
    test_model_is_indexed(digger)
    test_model_filter(digger)
    test_list_models(digger)

    shutil.rmtree(SCRATCH_DIRECTORY)
    print("PASS")


if __name__ == "__main__":
    main()

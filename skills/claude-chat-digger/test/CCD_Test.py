"""Minimal isolated tests for CCD's index/search - see Test_idea.md.

Uses a scratch corpus and scratch index under this directory; never touches the real ~/.claude corpus or index.
One test function per search mode, plus checks on indexing and output behaviour deliberately baked into the example chat, all run against a single index build of the injected example chat.
The last test adds a synthetic session for what the recorded chat lacks, and rebuilds.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIRECTORY.parent
sys.path.insert(0, str(SKILL_ROOT))

from CCD import parse_command, render_excerpt
from CCD_api import Context_unit, Context_window, Match_mode, Search_options, Search_role
from CCD_engine import Chat_digger
from CCD_normalise import local_time_text
from CCD_search import iter_excerpts

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
FIZOTONITU_ANSWER_TIMESTAMP = "2026-08-04T14:50:56.251Z"
STREAMED_STUB_UUID = "196017b2-aa79-454f-95a8-56968ea89e71"
LOCAL_TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}[+-]\d{2}:\d{2}$")
CCD_CALL_SESSION_ID = "0ccd0ccd-0000-4000-8000-000000000001"
CCD_CALL_WORD = "zibberquak"


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


def test_local_time_display(digger: Chat_digger) -> None:
    text = local_time_text(FIZOTONITU_ANSWER_TIMESTAMP)
    assert LOCAL_TIME_PATTERN.match(text), "expected ISO 8601 local time with offset, got %r" % text
    assert datetime.fromisoformat(text) == datetime(2026, 8, 4, 14, 50, tzinfo=timezone.utc), (
        "%s must name the same minute as %s" % (text, FIZOTONITU_ANSWER_TIMESTAMP)
    )
    print("ok: time display - %s shows as %s" % (FIZOTONITU_ANSWER_TIMESTAMP, text))


def test_date_filters(digger: Chat_digger) -> None:
    answer_day = datetime.fromisoformat(FIZOTONITU_ANSWER_TIMESTAMP.replace("Z", "+00:00")).astimezone().date()

    same_day = digger.search_all("fizotonitu", Search_options(date_from=answer_day.isoformat(), date_to=answer_day.isoformat()))
    assert same_day.total_matches > 0, "--date-from D --date-to D must include the whole local day D"

    day_before = digger.search_all("fizotonitu", Search_options(date_to=(answer_day - timedelta(days=1)).isoformat()))
    assert day_before.total_matches == 0, "--date-to the day before must exclude the chat"

    answer_minute = local_time_text(FIZOTONITU_ANSWER_TIMESTAMP)
    minute = digger.search_all(
        "fizotonitu", Search_options(roles=Search_role.assistant, date_from=answer_minute, date_to=answer_minute)
    )
    minute_uuids = {entry.uuid for conversation in minute.conversations for entry in conversation.matched_chat_entries}
    assert minute_uuids == {FIZOTONITU_ANSWER_UUID}, "a minute bound must cover its whole minute, got %s" % minute_uuids

    try:
        digger.search_all("fizotonitu", Search_options(date_to="yesterday"))
    except ValueError:
        pass
    else:
        raise AssertionError("an unreadable date bound must raise ValueError")
    print("ok: date filters - a local day or minute is an inclusive bound")


def test_path_spellings(digger: Chat_digger) -> None:
    conversation = next(item for item in digger.list_conversations() if item.session_id == EXPECTED_SESSION_ID)
    stored = conversation.project_path
    assert stored[:1].isupper() and stored[1:2] == ":", "the drive letter must show upper-cased, got %r" % stored

    spellings = [stored, stored.lower(), stored.replace("\\", "/"), stored[0].lower() + stored[1:] + "\\"]
    for spelling in spellings:
        exact = digger.search_all("fizotonitu", Search_options(projects=[spelling]))
        assert exact.total_matches > 0, "--project must accept the spelling %r" % spelling
        within = digger.search_all("fizotonitu", Search_options(workspace=spelling))
        assert within.total_matches > 0, "--workspace must accept the spelling %r" % spelling

    folder = stored.replace("\\", "/").rsplit("/", 1)[-1]
    named = digger.search_all("fizotonitu", Search_options(workspace=folder))
    assert named.total_matches > 0, "--workspace must match a whole folder name"
    partial = digger.search_all("fizotonitu", Search_options(workspace=folder[:-1]))
    assert partial.total_matches == 0, "--workspace must not match part of a folder name"

    assert len(digger.list_families(workspace=folder)) == 1, "families --workspace must match a whole folder name"
    assert digger.list_families(workspace=folder[:-1]) == [], "families --workspace must not match part of a folder name"
    print("ok: paths - drive letter upper-cased; --project and --workspace take any spelling, whole folder names only")


def test_in_merges_excerpts(digger: Chat_digger) -> None:
    result = digger.search_in_conversation(EXPECTED_SESSION_ID, "hyednesenc")
    assert result.match_count == 5, "in must count every match, 1 in the question and 4 in the answer, got %d" % result.match_count
    answer = next(item for item in result.chat_entries if item.uuid == HYEDNESENC_ANSWER_UUID)
    excerpts = list(iter_excerpts(answer.snippets, Context_unit.lines))
    assert len(answer.snippets) == 4 and len(excerpts) == 1, "the answer's 4 nearby matches must form one excerpt"
    assert render_excerpt(excerpts[0]).count(">>>") == 4, "the excerpt must mark all 4 matches"

    arguments = parse_command(["in", EXPECTED_SESSION_ID, "hyednesenc"])
    output = arguments.handler(digger, arguments)
    assert output.body.count("[block 0/text]") == 2, "the CLI must print each block once, not once per match"
    assert output.body.count(">>>") == 5, "the CLI must mark every match"
    print("ok: in - nearby matches merge into one excerpt per block, every match marked and counted")


def test_context_zero(digger: Chat_digger) -> None:
    result = digger.search_in_conversation(EXPECTED_SESSION_ID, "hyednesencic", context=Context_window(before=0, after=0))
    snippet = result.chat_entries[0].snippets[0]
    assert "\n" not in snippet.before + snippet.after, "--context 0 must show the match line only, got %r" % snippet.before
    print("ok: context 0 - the match line only")


def test_search_reports_totals(digger: Chat_digger) -> None:
    result = digger.search_all("fizotonitu", Search_options(limit=0))
    assert result.total_conversations == 1 and result.conversations == [], (
        "total_conversations must count every matching conversation, before --limit cuts the list"
    )
    arguments = parse_command(["search", "fizotonitu", "--limit", "0"])
    output = arguments.handler(digger, arguments)
    assert any("showing the first 0 of 1" in note for note in output.notes), "a cut must be reported, got %s" % output.notes
    print("ok: search totals - --limit cuts the list, not the totals, and the cut is reported")


def test_show_requested_thinking_block(digger: Chat_digger) -> None:
    entry = digger.get_chat_entry(STREAMED_STUB_UUID, EXPECTED_SESSION_ID, block_index=0)
    kinds = [block.block_type for block in entry.blocks]
    assert kinds == ["thinking"], "show --block must return the requested block whatever its kind, got %s" % kinds
    print("ok: show --block - a requested thinking block comes back without --thinking")


def ccd_call_session_records() -> list[dict]:
    """A synthetic session: a CCD search, its result, and an unrelated shell call, all naming one made-up word."""
    ccd_command = 'python ~/markdown_voodoo/skills/claude-chat-digger/CCD.py search "%s"' % CCD_CALL_WORD
    contents = [
        ("user", None, "Did %s come up before?" % CCD_CALL_WORD),
        (
            "assistant",
            "msg_ccd_call",
            [{"type": "tool_use", "id": "toolu_ccd", "name": "Bash", "input": {"command": ccd_command, "description": "Search for %s" % CCD_CALL_WORD}}],
        ),
        (
            "user",
            None,
            [{"type": "tool_result", "tool_use_id": "toolu_ccd", "content": "'%s' - 0 matches across 0 conversations" % CCD_CALL_WORD}],
        ),
        (
            "assistant",
            "msg_echo_call",
            [{"type": "tool_use", "id": "toolu_echo", "name": "Bash", "input": {"command": "echo %s" % CCD_CALL_WORD, "description": "Print it"}}],
        ),
    ]
    records = []
    for index, (role, message_id, content) in enumerate(contents):
        message = {"role": role, "content": content}
        if message_id:
            message["id"] = message_id
        records.append(
            {
                "type": role,
                "uuid": "ccd-call-%d" % index,
                "parentUuid": "ccd-call-%d" % (index - 1) if index else None,
                "timestamp": "2026-08-05T10:00:%02d.000Z" % index,
                "cwd": "/work/ccd",
                "message": message,
            }
        )
    return records


def test_ccd_calls_are_not_indexed(digger: Chat_digger) -> None:
    """Runs last: it adds a synthetic second session to the scratch corpus and rebuilds the index."""
    session_path = SCRATCH_CORPUS_ROOT / "synthetic" / ("%s.jsonl" % CCD_CALL_SESSION_ID)
    session_path.parent.mkdir(parents=True)
    with open(session_path, "w", encoding="utf-8", newline="\n") as handle:
        for record in ccd_call_session_records():
            handle.write(json.dumps(record) + "\n")
    digger.build_index()

    result = digger.search_all(CCD_CALL_WORD, Search_options(include_tool_result=True))
    uuids = {entry.uuid for conversation in result.conversations for entry in conversation.matched_chat_entries}
    assert uuids == {"ccd-call-0", "ccd-call-3"}, (
        "a CCD call and its result must stay out of the index, other shell calls must not; got %s" % uuids
    )
    print("ok: CCD calls - a CCD call and its result stay out of the index, other shell calls stay in")


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
    test_local_time_display(digger)
    test_date_filters(digger)
    test_path_spellings(digger)
    test_in_merges_excerpts(digger)
    test_context_zero(digger)
    test_search_reports_totals(digger)
    test_show_requested_thinking_block(digger)
    test_ccd_calls_are_not_indexed(digger)

    shutil.rmtree(SCRATCH_DIRECTORY)
    print("PASS")


if __name__ == "__main__":
    main()

# Findings

Open findings on CCD, ordered by impact.
`Status` stays `code reading only` until a run reproduces the finding.
Delete an entry once it is fixed.

## Path filters compare raw strings

- **Where:** `Search_mixin._filter_clauses` (`--workspace`, `--project` on `search` and `in`) and `Tree_mixin.list_families` (`families`).
- **Cause:** both compare the stored `project_path` with the argument as a plain string.
  The stored value is the record's raw `cwd`, e.g. `c:\Users\devboese\markdown_voodoo` in the fixture (`test/example_chat/`).
  `--workspace` lower-cases both sides and tests "contains"; `--project` tests exact, case-sensitive equality.
- **Symptom:** on Windows, no forward-slash spelling matches: `C:/Users/...`, `/c/Users/...`, `~/...`.
  Claudes on this machine call CCD from Git Bash, where these spellings are the natural ones; `Examples.md` itself shows `--workspace ~/projects/todo-app`.
  `--project C:\...` misses a `cwd` recorded as `c:\...`, and the drive-letter case differs between entrypoints (see `Storage_format.md`).
  Only a backslash path or a bare folder name matches.
- **Second issue:** "contains" is not the documented "a folder and everything under it": `--workspace C:\dev\app` also matches `C:\dev\app_old` and `C:\dev\apple`.
- **Fix idea:** one shared path normaliser for both sides (expand `~`, map `/c/` to `c:/` and `\` to `/`, lower-case, strip a trailing `/`), then match "equal, or starts with the folder plus `/`".
- **Check:** with the fixture, `Search_options(workspace="C:/Users/devboese/markdown_voodoo")` finds nothing, `workspace="markdown_voodoo"` finds the conversation.
- **Status:** code reading only.

## Earlier CCD calls match their own query

- **Where:** `TOOL_INPUT_TEXT_KEYS` and `iter_searchable_blocks` in `CCD_parsing.py`; `_allowed_block_kinds` in `CCD_search.py`.
- **Cause:** the `command` and `description` of every shell call (`Bash`, `PowerShell`) are indexed as a `tool_input` block, and `tool_input` is searched by default.
- **Symptom:** the call `CCD.py search "foo"` matches `foo` as soon as its conversation is indexed.
  Every search adds a match for its own query, so the noise grows with use.
  Repeated `search` and `in` calls for one term also raise that conversation's rank, since `search` ranks by match count.
  With `--tool-result` it gets worse: the output of `in` and `show` copies text of other conversations into the calling one.
- **Fix idea:** recognise CCD's own calls during indexing (a shell `tool_use` whose `command` runs `CCD.py`), then skip them or give them a block kind that is excluded by default.
- **Check:** on the real index, `in` on any conversation that ran CCD shows `tool_input` snippets of the CCD command line.
- **Status:** code reading only.

## Truncation is silent

- **Where:** `Search_mixin._assemble_search_result`, `Search_mixin.search_in_conversation` and `_iter_match_positions` in `CCD_search.py`; `command_list` and `command_families` in `CCD.py`; `Tree_mixin.list_families`.
- **Symptom:**
  - `search` sums `total_matches` over all conversations but counts `total_conversations` after `--limit`.
    The header can read "312 matches across 20 conversations" while 50 conversations matched.
  - `list` and `families` stop at `--limit` (default 40), and their counts cover only the shown rows.
  - `in` shows at most 3 snippets per block and counts only those, so it reports fewer matches than `search` for the same conversation.
  - `in` accepts `--limit` and ignores it.
  - The CLI has no `--offset`, although `Search_options.offset` exists.
- **Fix idea:** report each cut as a note on stderr ("showing 20 of 50 conversations; raise --limit"), as `tree` already does for folded entries.
  Keep the true totals in the JSON; `Search_all_result` in `CCD_api.py` then needs a shown/total split.
- **Check:** with the fixture, `search_all("hyednesenc")` counts 5 matches and `search_in_conversation` on the same conversation counts 4, because the answer block holds 4 and is capped at 3.
- **Status:** code reading only.

## `in --context 0` prints every preceding line

- **Where:** `_build_snippet` in `CCD_search.py`.
- **Cause:** the preceding lines are sliced with `[-context.before:]`, and `[-0:]` is the whole list.
- **Symptom:** `in --context 0` prints the whole block up to each match, and no line after it.
  The option meant to shrink the output can inflate it to the size of the block.
- **Fix idea:** take no preceding lines when `context.before` is 0, or slice with an explicit start index.
- **Check:** with the fixture, `search_in_conversation` for `hyednesencic` with `Context_window(before=0, after=0)` returns a `before` that starts with the answer's first line.
- **Status:** code reading only.

## `--date-to` excludes its own day

- **Where:** `Search_mixin._filter_clauses`.
- **Cause:** `timestamp <= ?` compares text, and `2026-08-04T14:50:52.679Z` sorts after `2026-08-04`.
- **Symptom:** `--date-to 2026-08-04` drops every entry of August 4.
  `--date-from 2026-08-04 --date-to 2026-08-04` finds nothing.
- **Second issue:** timestamps are UTC (`Z`), so a bare date bounds the UTC day, not the user's local day.
- **Fix idea:** read a bare `YYYY-MM-DD` upper bound as "before the next day": `timestamp < date(?, '+1 day')`.
- **Check:** with the fixture, `Search_options(date_from="2026-08-04", date_to="2026-08-04")` finds nothing.
- **Status:** code reading only.

## Case-insensitive matching folds ASCII only

- **Where:** `Search_mixin._content_predicate` and `Search_mixin._all_terms_rows`.
- **Cause:** the SQL predicates use SQLite's built-in `lower()`, which converts only ASCII letters unless SQLite is built with ICU.
- **Symptom:** `search "über"` misses `Über`.
  The Python side (`count_occurrences`, `_iter_match_positions`, `_wildcard_pattern`) folds Unicode, but it only sees the rows the SQL predicate lets through.
- **Fix idea:** register a Unicode-aware lower function with `sqlite3.Connection.create_function` and use it in the predicates.
  It runs once per block and search, so measure its cost on the real index.
- **Pitfall:** `_iter_match_positions` finds positions in the lower-cased text, and `_build_snippet` applies them to the original text.
  A folding that changes the length (`casefold` turns `ß` into `ss`) shifts every snippet after that character.
- **Check:** `SELECT lower('Ü')` through Python's `sqlite3` returns `Ü`.
- **Status:** code reading only.

## `origin` merges the backups of same-named files

- **Where:** `_collect_backups` and the file-event loop of `parse_session_file` in `CCD_parsing.py`.
- **Cause:** file-history versions are keyed per conversation by the lower-cased basename, not by the path.
- **Symptom:** a conversation that writes `skills/a/SKILL.md` and `skills/b/SKILL.md` keeps one version map for both.
  `origin` can then report the other file's version and backup, and `created` instead of `edited` or the reverse.
  Every skill folder in this repo has a `SKILL.md`, so such conversations are common here.
- **Fix idea:** key by the full path, normalised as in *Path filters compare raw strings*.
- **Open:** whether the `trackedFileBackups` keys spell paths like the tools' `file_path`; the fixture's snapshots are empty.
- **Check:** needs a fixture conversation that writes two files with the same basename.
- **Status:** code reading only.

## Small items

- `command_index` prints "Indexing …" to stdout, so `index --format json` without `--out` is not valid JSON; `SKILL.md` promises that a piped stdout carries the payload only.
- `show --block N` on a thinking block without `--thinking` prints an empty result and no note, although `in --thinking` hands out exactly such block indices.
- The `CCD_api.py` module docstring cites `api_design.md`, which is not in the skill folder.
- The `CCD.py` module docstring lists only some commands; `origin`, `tree`, `family` and `families` are missing.
- `docs/AGENTS.md` and `docs/Usage.md` say to run from the folder that contains `CCD.py`; `SKILL.md` rightly says any working directory works.
- The "Out of scope" section of `test/Test_idea.md` is outdated: `CCD_Test.py` now also exercises `in` and `list` through their engine methods, streamed duplicates, and the role, case and model filters.

## Open questions

Each one needs a look at real transcripts under `~/.claude/projects`.

- **Subagent transcripts:** `Storage_format.md` says they are interleaved into the session file and marks that as unconfirmed.
  If current Claude Code writes them to separate `.jsonl` files below the project folder, `iter_session_files` (`**/*.jsonl`) indexes each one as its own conversation, with the file stem as `session_id`.
- **Loaded skill text:** the text of a loaded skill may be stored as a `user` record flagged `isMeta: true`.
  `parse_session_file` ignores `isMeta`, so that text would count as typed user text.
  Every conversation that loaded a skill would then match the skill's whole text, an echo like *Earlier CCD calls match their own query*.
- **Backup key spelling:** see *`origin` merges the backups of same-named files*.

## Index version

Fixes that change what the index stores need a `CCD_INDEX_VERSION` bump, and every bump makes all searches fail until the next `index` run.
That applies to *Earlier CCD calls match their own query*, to *`origin` merges the backups of same-named files*, and to *Path filters compare raw strings* if the stored side gets normalised.
Done together, they cost one rebuild.

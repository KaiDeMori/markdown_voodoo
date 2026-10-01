# Findings

Open findings on CCD, ordered by impact.
`Status` stays `code reading only` until a run reproduces the finding.
Delete an entry once it is fixed.

## Case-insensitive matching folds ASCII only

- **Where:** `Search_mixin._content_predicate` and `Search_mixin._all_terms_rows`.
- **Cause:** the SQL predicates use SQLite's built-in `lower()`, which converts only ASCII letters unless SQLite is built with ICU.
- **Symptom:** `search "über"` misses `Über`.
  The Python side (`count_occurrences`, `_iter_match_positions`, `_wildcard_pattern`) folds Unicode, but it only sees the rows the SQL predicate lets through.
- **Fix idea:** register a Unicode-aware lower function with `sqlite3.Connection.create_function`, as `in_workspace` already is, and use it in the predicates.
  It runs once per block and search, so measure its cost on the real index.
  A stored folded copy of the content would avoid that cost, at the price of a larger index and a `CCD_INDEX_VERSION` bump.
- **Pitfall:** `_iter_match_positions` finds positions in the lower-cased text, and `_build_snippet` applies them to the original text.
  A folding that changes the length (`casefold` turns `ß` into `ss`) shifts every snippet after that character.
- **Status:** reproduced in SQLite 3.43.1: `lower('Über')` returns `Über`, and `instr(lower('Über'), lower('über'))` is 0.

## `origin` merges the backups of same-named files

- **Where:** `_collect_backups` and the file-event loop of `parse_session_file` in `CCD_parsing.py`.
- **Cause:** file-history versions are keyed per conversation by the lower-cased basename, not by the path.
- **Symptom:** a conversation that writes `skills/a/SKILL.md` and `skills/b/SKILL.md` keeps one version map for both.
  `origin` can then report the other file's version and backup, and `created` instead of `edited` or the reverse.
  Every skill folder in this repo has a `SKILL.md`, so such conversations are common here.
- **Fix idea:** key by the full path's `path_key` (`CCD_normalise.py`).
- **Open:** whether the `trackedFileBackups` keys spell paths like the tools' `file_path`; the fixture's snapshots are empty.
- **Check:** needs a fixture conversation that writes two files with the same basename.
- **Status:** code reading only.

## Small items

- `in` accepts `--limit` and ignores it; `docs/Usage.md` says so.
- The CLI has no `--offset`, although `Search_options.offset` exists; the cut notes point to `--limit` instead.
- An `in` excerpt keeps a blank context line at its start or end, so `[block N/text]` can stand alone on its line.
- `search` labels a conversation's last activity `when`, which a reader can take for the time of the match.

## Open questions

Each one needs a look at real transcripts under `~/.claude/projects`.

- **Subagent transcripts:** `Storage_format.md` says they are interleaved into the session file and marks that as unconfirmed.
  If current Claude Code writes them to separate `.jsonl` files below the project folder, `iter_session_files` (`**/*.jsonl`) indexes each one as its own conversation, with the file stem as `session_id`.
- **Loaded skill text:** the text of a loaded skill may be stored as a `user` record flagged `isMeta: true`.
  `parse_session_file` ignores `isMeta`, so that text would count as typed user text.
  Every conversation that loaded a skill would then match the skill's whole text, the kind of echo `is_ccd_call` prevents for CCD's own calls.
- **Backup key spelling:** see *`origin` merges the backups of same-named files*.

## Index version

Fixes that change what the index stores need a `CCD_INDEX_VERSION` bump, and every bump makes all searches fail until the next `index` run.
Of the open findings, the `origin` fix changes the index, and so would a stored folded copy of the content.
Done together, they cost one rebuild.

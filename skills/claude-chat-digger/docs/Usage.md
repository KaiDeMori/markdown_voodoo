# Usage

```
python CCD.py [global-options] <command> [arguments] [options]
```

Give Python the path to `CCD.py`; the working directory does not matter.
Pure Python 3 standard library; no install.
Build the index once with `index` before any search.

## Argument order

- Positionals first, in the order shown for the command, then options.
- A positional value may start with a dash (e.g. `-X`).
  It is read literally; no `--` escape needed.
- Options follow the positionals, in any order.
- Exception: `--help`/`-h` given alone directly after the command name (e.g. `CCD search --help`) shows that command's options, not read as a positional.
- `CCD -h` shows global help and the full command list.

## Global options (before the command)

| Option | Default |
|---|---|
| `--index-path <file>` | `~/.claude/CCD_index.db` |
| `--corpus-root <dir>` | `~/.claude/projects` |

## Commands

| Command | Arguments | Purpose |
|---|---|---|
| `index` | — | Full rebuild of the search index (the only writer). |
| `status` | — | Index counts, staleness, and format version. |
| `search` | `<query>` + search filters | Find matching conversations (tier 1). |
| `in` | `<session_id> <query> [--context N]` + search filters | Matches within one conversation, with context (tier 2). |
| `show` | `<session_id> <uuid> [--block N] [--thinking] [--meta]` | Full content of one message (tier 3). |
| `models` | `<session_id>` | The models that answered in one conversation, with a message count each. |
| `origin` | `<filename> [--mode all\|created\|edited\|read] [--tool T,T]` | Where a file was created/edited/read. |
| `tree` | `<session_id>` + tree options | Render a fork family as a diagram. |
| `family` | `<session_id>` | List the sessions in this conversation's fork family. |
| `families` | `[--workspace W] [--project P] [--limit N]` | Overview of fork families. |
| `list` | `[--limit N]` | Browse indexed conversations. |

## Output (every command)

| Option | Default | Effect |
|---|---|---|
| `--out <file>`, `-o` | — | Write the full result to a UTF-8 file (`\n` line endings) and print a one-line receipt to stderr. Without it, the result goes to stdout. |
| `--format text\|json` | `text` | Human-readable text, or the full structured result as JSON. |

`--format json` emits the complete structured result — richer than the text (e.g. snippet offsets, roles, per-entry match counts).
For `tree` it is the render-neutral graph (`directed`, `nodes`, `edges`, `notes`); `--diagram-format` is ignored.

Prefer `--out` over shell redirection: PowerShell `>` writes UTF-16 with a BOM and CRLF, which corrupts JSON and diagram source.
The receipt and any notes are diagnostics on stderr, so the saved file — or a piped stdout — carries the payload only, valid JSON included.
Every cut is reported as a note: `--limit` on `search`, `list`, and `families`, and the excerpt cap of `in`.

## Times

- Text output shows every time in local time, ISO 8601 to the minute with its offset: `2026-10-01T15:51+02:00`.
- JSON keeps the stored UTC timestamps: `2026-10-01T13:51:30.123Z`.

## Search filters (`search`, `in`)

| Option | Default | Effect |
|---|---|---|
| `--mode substring\|all_terms\|wildcard\|regex` | `substring` | Match mode. `wildcard` = glob `*` `?`, see below; `regex` is reserved and errors if used. |
| `--all` | off | Shorthand for `--mode all_terms`: every whitespace-separated term must appear in the same message. |
| `--case-sensitive` | off | Case-sensitive matching. |
| `--role user\|assistant\|both` | `both` | Restrict by speaker. |
| `--model <model_id>` | — | Restrict to assistant messages answered by this exact model id (e.g. `claude-opus-5`). User messages carry no model, so they never match. `models <session_id>` lists the ids present. |
| `--project <path>` | — | One exact project folder, in any spelling (see Paths). |
| `--workspace <folder>` | — | Whole folder names: a full path matches that folder and everything under it; a relative one (`app`, `dev/app`) matches those folder names anywhere in the path. `app` never matches `apple`. |
| `--date-from <date>` | — | Earliest time, inclusive: a local date `YYYY-MM-DD` or an ISO 8601 date-time, local if it has no offset. |
| `--date-to <date>` | — | Latest time, inclusive through the bound's own precision: a date covers the whole local day, `2026-10-01T15:51` the whole minute. |
| `--thinking` | off | Also search assistant thinking blocks. |
| `--tool-result` | off | Also search tool-result bodies. |
| `--no-tool-input` | off | Do not search tool inputs (searched by default). |
| `--limit N` | `20` | Cap the number of conversations `search` lists; `in` ignores it. |

### Paths (`--project`, `--workspace`)

- Any spelling names the same folder: `\` or `/`, any letter case, a trailing slash, `~`, and Git Bash's `/c/...`.
- CCD shows a path with its drive letter upper-cased, whatever case Claude Code recorded.

### Excerpts (`in`)

- Matches in one block whose context lines overlap or touch merge into one excerpt, each match marked `>>>…<<<`.
- At most 3 excerpts and 100 matches per block are shown; a note counts the matches left out, and `show --block N` prints the whole block.
- The header counts every match.
- `--format json` keeps one snippet per shown match, with its offset.

### Wildcard matching (`--mode wildcard`)

- `*` matches zero or more characters.
- `?` matches exactly one character.
- `[...]` character classes pass through unmodified.
- Tier 1 (`search`): SQL `GLOB`, a whole-string test.
  Greediness does not apply.
- Tier 2/3 (`in`): non-greedy regex translation.
  Each `*` matches the shortest possible span, so multiple occurrences in one block stay separate.
- Example: pattern `fix*bug` on text containing both `fix-the-bug` and `fix-the-other-bug` produces two matches, not one match spanning both.

## `tree` options

| Option | Default | Choices / effect |
|---|---|---|
| `--diagram-format` | `mermaid` | Diagram drawing language: `mermaid` or `dot`. Used when `--format text`; for JSON output use the universal `--format json`. |
| `--detail` | `forks_only` | `short`, `forks_only`, `turns`, `full`. |
| `--max-nodes N` | `200` | Coarsen beyond this; the reduction is noted, not silent. |
| `--single` | off | This session only, not its whole fork family. |

## Other defaults

- `show --meta` prints model, token usage, git branch, Claude Code version, and the rest of the message envelope, read from the source `.jsonl` file (never the index) — off by default.
- `show --block N` returns that block whatever its kind; `--thinking` matters only for a whole message.
- `models` counts deduplicated assistant messages per model, read from the index; the order is most-used first.
- `in --context` (lines of context per side): `2`; `0` shows the match line only.
- `families --limit`: `40`.
  `list --limit`: `40`.
- `origin --mode`: `all`.
  Recognised tools: `Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`.
- Index format version: `5`.
  A search refuses to run against an index built by a different version — rebuild with `index`.
- Output is always UTF-8.

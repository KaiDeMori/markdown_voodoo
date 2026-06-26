# Usage

```
python CCD.py [global-options] <command> [arguments] [options]
```

Run from the directory containing `CCD.py`. Pure Python 3 standard library; no install. Build the index once with `index` before any search.

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
| `show` | `<session_id> <uuid> [--block N] [--thinking]` | Full content of one message (tier 3). |
| `origin` | `<filename> [--mode all\|created\|edited\|read] [--tool T,T]` | Where a file was created/edited/read. |
| `tree` | `<session_id>` + tree options | Render a fork family as a diagram. |
| `family` | `<session_id>` | List the sessions in this conversation's fork family. |
| `families` | `[--workspace W] [--project P] [--limit N]` | Overview of fork families. |
| `list` | `[--limit N]` | Browse indexed conversations. |

## Search filters (`search`, `in`)

| Option | Default | Effect |
|---|---|---|
| `--mode substring\|all_terms\|wildcard\|phrase\|regex` | `substring` | Match mode. `wildcard` = glob `*` `?`; `regex` is reserved and errors if used. |
| `--all` | off | Shorthand for `--mode all_terms`: every whitespace-separated term must appear in the same message. |
| `--case-sensitive` | off | Case-sensitive matching. |
| `--role user\|assistant\|both` | `both` | Restrict by speaker. |
| `--project <path>` | — | One exact project path. |
| `--workspace <folder>` | — | A project folder and everything under it (case-insensitive). |
| `--date-from <YYYY-MM-DD>` | — | Lower time bound. |
| `--date-to <YYYY-MM-DD>` | — | Upper time bound. |
| `--thinking` | off | Also search assistant thinking blocks. |
| `--tool-result` | off | Also search tool-result bodies. |
| `--no-tool-input` | off | Do not search tool inputs (searched by default). |
| `--limit N` | `20` | Cap the number of results. |

## `tree` options

| Option | Default | Choices / effect |
|---|---|---|
| `--format` | `mermaid` | `mermaid`, `dot`, `graph_json`. |
| `--detail` | `forks_only` | `short`, `forks_only`, `turns`, `full`. |
| `--max-nodes N` | `200` | Coarsen beyond this; the reduction is noted, not silent. |
| `--single` | off | This session only, not its whole fork family. |
| `--out FILE`, `-o` | — | Write diagram source to a file; print a one-line summary. |

## Other defaults

- `in --context` (lines of context per side): `2`.
- `families --limit`: `40`. `list --limit`: `40`.
- `origin --mode`: `all`. Recognised tools: `Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`.
- Index format version: `3`. A search refuses to run against an index built by a different version — rebuild with `index`.
- Output is always UTF-8.

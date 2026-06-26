---
name: claude-chat-digger
description: Search, recall, and trace past Claude Code conversations. Use when the user wants to find whether a topic, decision, error, or code snippet came up in an earlier Claude Code session; recall what an earlier chat said; find which past conversation created, edited, or read a given file; browse or list prior conversations; or visualize a conversation's fork tree. Wraps the CCD command-line tool over the local ~/.claude/projects conversation logs.
---

# Claude Chat Digger (CCD)

CCD indexes every past Claude Code conversation — the JSON-Lines logs under `~/.claude/projects` — into a local SQLite index, then lets you search them, read messages in full, trace where a file was created or edited, and draw a conversation's fork tree. It is pure Python 3 standard library: no dependencies, nothing to install.

## Where it lives

The code and its reference docs live at one single home:

```
C:/Users/devboese/markdown_voodoo/skills/claude-chat-digger/
```

Run the tool from anywhere by giving Python the absolute path — the working directory does not matter, and the default `--corpus-root` (`~/.claude/projects`) and `--index-path` (`~/.claude/CCD_index.db`) are already correct, so no paths need to be passed:

```bash
python "C:/Users/devboese/markdown_voodoo/skills/claude-chat-digger/CCD.py" <command> [options]
```

## Always check the index first

Search only ever reads the SQLite index, and it goes stale as new conversations accrue. Before searching:

1. Run `status`. If it reports the index is stale, missing, or built by a different format version, run `index` to rebuild it.
2. `index` is the only command that writes; everything else only reads.

```bash
python "C:/Users/devboese/markdown_voodoo/skills/claude-chat-digger/CCD.py" status
python "C:/Users/devboese/markdown_voodoo/skills/claude-chat-digger/CCD.py" index
```

## Command map

Search is tiered — find the conversation, narrow to the matches, then read one in full:

| Step | Command | Use |
|---|---|---|
| 1 | `search "<query>"` | Which conversations match, across everything. |
| 2 | `in <session_id> "<query>" [--context N]` | The matches inside one conversation, with surrounding lines. |
| 3 | `show <session_id> <uuid> [--block N] [--thinking]` | One message printed in full. |

Beyond search:

- `origin <filename> [--mode all|created|edited|read] [--tool Write,Edit]` — every event where a file was created, edited, or read.
- `tree <session_id> [--format mermaid|dot|graph_json]` — render a conversation's fork family as a diagram.
- `family <session_id>` — the sessions in one conversation's fork family.
- `families [--workspace W] [--project P]` — an overview of all fork families.
- `list [--limit N]` — browse indexed conversations, newest first.

Common filters on `search` and `in`: `--project`, `--workspace` (a folder and everything under it), `--date-from` / `--date-to`, `--role user|assistant|both`, `--thinking` (also search thinking blocks), `--mode substring|all_terms|wildcard|phrase`, and `--all` (every term in the same message).

## Writing results to a file

Every command takes `--out FILE` (`-o`) to write its full result to a file and print a one-line receipt instead. Prefer it over shell redirection: it always writes UTF-8 with `\n` line endings, where a PowerShell `>` would write UTF-16 with a BOM and CRLF and corrupt diagram source or JSON. Diagnostics — the receipt and any notes — go to stderr, so the saved file (or a piped stdout) carries the payload only. This is what you want for large results: keep the bulk on disk instead of in the terminal.

## Full reference

The bundled docs under the skill's home carry the complete detail — read them on demand rather than guessing:

- `docs/Usage.md` — every command, option, and default, as a terse reference.
- `docs/Examples.md` — worked examples for each command.
- `docs/CCD_architecture.md` — where each part of the code lives and why; read before changing CCD.
- `docs/Storage_format.md` — how Claude Code stores conversations on disk and how CCD parses them.

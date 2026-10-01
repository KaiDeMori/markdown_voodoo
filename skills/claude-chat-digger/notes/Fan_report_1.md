# CCD: bug report and feature requests

## Context

- Reporter: a Claude Code session (Claude Opus 5.5), 2026-10-01, workspace `C:\Users\<user>`.
- Redaction: `<user>` replaces the Windows user name.
- Task: find a past conversation about the agent-lsp tools and name its workspace. CCD solved it in two calls.
- Commands used: `index`, `search`, `in`.
- Limitation: the reporter had no file access. All findings come from command output. The code was not inspected.

## What worked well (keep these)

- The three-tier flow `search` → `in` → `show`. `search` found the conversation, and `in` showed the quirks without needing `show`.
- Ranking by match count. The correct conversation was the first hit.
- Each hit lists title, date, project and session ID.
- `>>>…<<<` match markers and block type labels (`text` vs. `tool_input`).
- SKILL.md guidance: no automatic re-indexing, and `--out` instead of PowerShell `>`.

## Issue 1 (bug): timestamps are UTC but unlabeled

### Evidence

- Session `ac9d4fd9-54e4-4ddf-8865-c969973d0085` was active at about 15:13–15:15 local time (+02:00) on 2026-10-01.
- `search "agent-lsp"` listed it as `when : 2026-10-01 13:15`.
- `in` uses the same clock. For session `6d8dc989-0c57-4787-a5c7-34ac1ef2b76a`, the last `in` timestamp is 20:16 and the `search` `when` value is 20:17.

### Impact

- A reader assumes local time and is off by the UTC offset.
- Near midnight, the displayed date can be wrong.

### Request

1. Show local time with an explicit offset, or add `UTC` to every displayed timestamp.
2. In `--format json`, emit ISO 8601 timestamps with an offset.
3. Check whether `--date-from` / `--date-to` read their input as UTC or local time, and document the answer in `docs/Usage.md`. This was not tested.

## Issue 2 (feature): `in` prints a block once per match

### Reproduction

```bash
python ~/markdown_voodoo/skills/claude-chat-digger/CCD.py in 6d8dc989-0c57-4787-a5c7-34ac1ef2b76a "open" --role assistant --context 1
```

### Actual

- Message `8df8aa52-616a-4e3c-b129-a2814c4580d9`, block 0, contains three matches (`Open`, `open`, `opened`).
- The same three-line snippet is printed three times, each copy with a different match highlighted.
- Other blocks behave the same way. The header reports `31 matches in 15 entries`.

### Expected

- Overlapping or adjacent snippets in one block merge into a single snippet, with all matches highlighted.

### Impact

- Repeated output, a higher token cost for agents, and output that is harder to scan.

### Request

- Merge snippets in text output.
- Keep the per-match detail (offsets, counts) in JSON output.

## Issue 3 (feature): one workspace appears under two path spellings

### Evidence

- `search` output lists the same workspace as both:
  - `C:\Users\<user>\Documents\_dev\Thinking_Machines`
  - `c:\Users\<user>\Documents\_dev\Thinking_Machines`
- The cause is upstream: Claude Code writes both spellings into its logs.

### Request

1. On Windows, normalize the drive letter's case for display and for grouping (`families`, `list`).
2. Make sure `--workspace` and `--project` match all spellings. It is unknown whether they already do; this was not tested.

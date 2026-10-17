---
name: calm-grep
description: >-
  hallmark_tool
  A calm grep: it starts zoomed out at how many, and zooms in to where and what only when asked.
  Use when a raven wants to know whether, where or how something appears in a folder's files, without a flood of lines.
---

# calm-grep

```
bash C:/Users/devboese/.claude/skills/calm-grep/calm_grep.sh count <pattern> [folder]
bash C:/Users/devboese/.claude/skills/calm-grep/calm_grep.sh where <pattern> [folder]
bash C:/Users/devboese/.claude/skills/calm-grep/calm_grep.sh what <pattern> <file>
```

Start zoomed out, and zoom in only when the answer asks for it:

| Command | Answers | Happy path |
|---|---|---|
| `count` | Is it there at all? Is it gone everywhere? | `3 lines in 2 files`, or `nowhere` |
| `where` | Where exactly? | `skills/calm-comms/SKILL.md:4` |
| `what` | What does it say there? | `4: hallmark_tool` |

- The pattern is an extended regular expression, as in `grep -E`: `colour|color` finds both spellings.
- The folder is the current one by default; `where` puts it in front of every path, so the paths work from where the raven stands.
- `where` lists each file with the numbers of its matching lines: at most 20 files and 10 numbers per file, each list ending in `and N more`.
- `what` reads one file: at most 10 lines, each cut down to about 60 characters on each side of its match, with `...` where something was cut.
- Counts are lines, not matches: a line with several matches counts once.
- Noisy folders stay out: `.git`, `.venv`, `node_modules`, `__pycache__`, `.pytest_cache` and `.pytest_tmp`; binary files are skipped.
- A broken pattern is reported in one line, before any search.
- Exit 0 means the search ran, `nowhere` included; a broken pattern, a missing folder, or a folder given to `what` exits 1.
- The limits and the noisy folders are the variables at the top of `calm_grep.sh`.

'nough said.

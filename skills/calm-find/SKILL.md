---
name: calm-find
description: >-
  hallmark_tool
  A calm find: what kinds of files a folder holds, where they are, and what one of them would cost a window.
  Use when a raven wants to know what is in a folder, where its images, markdown or source are, or how heavy a file is before reading it.
---

# calm-find

```
calm-find [folder]
calm-find <kind> [folder]
calm-find what <file>
```

Start zoomed out, and zoom in only when the answer asks for it:

| Command | Answers | Happy path |
|---|---|---|
| `calm-find [folder]` | What is in here? | `skills/: 45 markdown · 72 source · 24 images` |
| `calm-find <kind> [folder]` | Where are they? | `skills/calm-find/calm_find.sh` |
| `calm-find what <file>` | Is it too much? | `png, 1932×1912`, or `markdown, 1846 tokens` |

- The kinds: `markdown`, `source` (code, scripts and html), `text` (txt, json, csv and the like), `images` (png, jpg, gif, webp, svg), `pdf`, and `other`.
- The map goes one level down: `here` for the folder's own files, then one line per subfolder, counted as a whole, with nothing inside it named; at most 20 lines.
- A kind's list holds at most 20 paths, then `and N more`; the folder goes in front of every path.
- `what` tells one fact, the one the kind is about: an image's resolution, a text's token count, or `small` below 4 KB. A pdf gets what it deserves.
- A token count sends the file to Anthropic, through the token counter.
- Noisy folders stay out: `.git`, `.venv`, `node_modules`, `__pycache__`, `.pytest_cache` and `.pytest_tmp`.
- The limits are the variables at the top of `calm_find.sh`.

'nough said.

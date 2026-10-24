# calm-find plan

A raven sees what kinds of files a folder holds, where they are, and what one of them would cost its window, before anything enters it.

## Decided

- `calm-find` is a hallmark tool in `skills/calm-find/`; `calm_find.sh` gives it its short call.
- Three levels, from zoomed out to zoomed in, like calm-grep:
  - `calm-find <folder>`: a map one level down, at most 20 lines: `here: 2 markdown` for the folder's own files, then one line per subfolder like `skills/: 40 markdown · 30 source · 20 images`, with nothing inside a subfolder named
  - `calm-find <kind> <folder>`: the paths of that kind, at most 20, then `and N more`
  - `calm-find what <file>`: one fact, the one its kind is about
- One fact per kind:
  - an image: its resolution, `png, 1932×1912`; byte sizes don't matter
  - markdown, source and text: the exact token count, from the token counter, above a byte threshold; below it, `small`
  - a pdf: a joke, the easter egg
- The kinds: images (png, jpg, gif, webp, svg), markdown (md), source (code, scripts and html), text (txt, json, csv and the like), pdf, and other for everything else.
- The byte threshold for counting is 4 KB.
- Noisy folders stay out, as in calm-grep: `.git`, `.venv`, `node_modules`, `__pycache__`.

## Steps

- [x] Settle the kinds and their extensions.
- [x] Write `calm_find.sh`: the overview, the list of a kind, and `what`.
- [x] Image resolution from `file`, which names it for png, jpg, gif and webp, so no extra library.
- [x] Token counts through the token counter, above the threshold.
- [x] The pdf jokes, picked at random.
- [x] `SKILL.md`, still without the mark, and a `deploy.bat`.
- [x] One or two ravens fly calm-find; if they like it, it gets the mark `hallmark_tool`.
- [x] Test one at a time, on the hall and on this workspace.

# calm-find plan

A raven sees what kinds of files a folder holds, where they are, and what one of them would cost its window, before anything enters it.

## Decided

- `calm-find` is a hallmark tool in `skills/calm-find/`; `calm_find.sh` gives it its short call.
- Three levels, from zoomed out to zoomed in, like calm-grep:
  - `calm-find <folder>`: one line, `14 markdown · 6 source · 3 images · 1 pdf · 2 other`
  - `calm-find <kind> <folder>`: the paths of that kind, at most 20, then `and N more`
  - `calm-find what <file>`: one fact, the one its kind is about
- One fact per kind:
  - an image: its resolution, `png, 1932×1912`; byte sizes don't matter
  - markdown, source and text: the exact token count, from the token counter, above a byte threshold; below it, `small`
  - a pdf: a joke, the easter egg
- Noisy folders stay out, as in calm-grep: `.git`, `.venv`, `node_modules`, `__pycache__`.

## Steps

- [ ] Settle the kinds and their extensions.
- [ ] Write `calm_find.sh`: the overview, the list of a kind, and `what`.
- [ ] Image resolution from `file`, which names it for png, jpg, gif and webp, so no extra library.
- [ ] Token counts through the token counter, above the threshold.
- [ ] The pdf jokes, picked at random.
- [ ] `SKILL.md` with the mark `hallmark_tool`, and a `deploy.bat`.
- [ ] Test one at a time, on the hall and on this workspace.

## Open questions

- The byte threshold for counting: 4 KB, about a thousand tokens?
- Are images, markdown, source, text, pdf and other the right kinds?

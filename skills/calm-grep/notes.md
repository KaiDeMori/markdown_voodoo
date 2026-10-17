# calm-grep: loose notes

## The idea

Grep is sometimes fine-ish and sometimes really loud: nobody knows how much comes back.
calm-grep starts zoomed out, and zooms in only when the answer asks for it.

## Real uses

- A grep for `json3` returned 87.8 KB from a handful of matches, because caption data lives in very long lines.
- A Glob returned 886 files, because a `.venv` was in the way.

## The questions

Ravens grep with one of four questions:

1. Is it there at all?
2. Where exactly?
3. Is it gone everywhere?
4. What does it say there?

Three of the four are answered with names and numbers; only the fourth needs the lines.

## Three zoom levels

```
how many   2 files                         or: nowhere
where      skills/calm-comms/SKILL.md:17
what       skills/calm-comms/SKILL.md:17  .../calm-comms/calm_comms.sh <verb>...
```

- The search term stays out of the answer; the raven just typed it.
- `nowhere` is grep's `main: clear`.

## The noise, and its calm answer

- Too many matches: counts per file first, and the lines only for the file the raven picks.
- Endless lines, such as minified code, JSON and captions: each line is cut to the part around the match.
- Noisy folders, such as `.venv`, `node_modules` and `.git`: they stay out unless asked for.

## Decided

- `count`, `where` and `what`, verb first, like calm-comms.
- grep counts inside itself, and only the files that get shown are searched again; `where e` over the whole repo takes about a second and a half.
- The pytest leftovers joined the noisy folders after a real use: they held 19 of the first 20 files for `json3`.

## Later

- In the hall: a search that honors `hall_overview_visibility.txt` and looks only into the open rooms.

# calm-md plan

A raven sees a markdown file's chapters, reads one, or writes one, without the whole file entering its window.

## Decided

- calm-md lives in `skills/calm-md/`, without the mark `hallmark_tool` until ravens have flown it; `calm_md.sh` gives it its short call.
- markdown-it-py, with the `front_matter_plugin` of mdit-py-plugins, finds the structure, in the skill's own venv, like the token counter's.
- The parser only finds the headings; `read` and `write` cut and splice the original lines.
  Nothing is ever re-rendered, so everything outside a chapter stays byte for byte, line endings included.
- A chapter runs from its heading to the line before the next heading of the same or a higher level, or to the end of the file, so it holds its subchapters.
- Headings of every level make chapters, except a heading nested inside a list item or a quote, which stays text.
- Front matter and the lines before the first heading belong to no chapter.
- A heading's title is its plain text: inline markup joined into text.
- A chapter path is a list of titles ending with the chapter's own, with only as many parents as it takes, like `"Attachments" "Steps"`; a path that fits more than one chapter is refused, with the candidates.
- A written chapter followed by more ends with a blank line, so an underlined heading below never swallows its last line.
- Three verbs to start:
  - `calm-md toc <file> [title ...]`: one line per chapter, indented by level, at most 40 lines, then `and N more`; a title path shows one chapter's part.
    A title longer than 60 characters is cut, with the count of omitted characters, like `… (+23)`.
    Each line ends with its chapter's weight in words, subchapters included, like `## Attachments (520 words)`.
  - `calm-md read <file> <title> ...`: the chapter's original lines, its heading line included.
  - `calm-md write <file> <title> ...`: replaces the chapter's lines with what comes on stdin, in the same shape, so a chapter can be read, changed and written back.
    Empty input is refused, and so is input that does not start with a heading line.
  - `calm-md replace <file> <title> ...`: the old text on stdin's first line, the new text after it; the old text occurs exactly once in the chapter, and the chapter keeps its heading line.
    The Packorator's flight log asked for it: a one-word fix should not send a whole chapter back.
- Later: an override that turns every cap off, and maybe a verb that removes a chapter.

## Linting

### Decided

- calm-md works only on piko bello markdown: before `toc`, `read` or `write`, pymarkdownlnt checks the whole file.
  With issues, calm-md does nothing but list them, like `3 issues, fix them and call again`, then one line per issue, so the raven fixes the doc and calls again.
- pymarkdownlnt runs in calm-md's venv, through its API, so the issues come back as data; one stack, one venv, one deploy.
- One central config, `piko_bello.json`, lives next to the tool and is deployed with it; it is tuned by feedback.
- It starts quiet, with the heading rules only: MD001, MD003 with `atx`, MD022, MD024 among siblings, and MD025.
  A rule joins when a real doc runs into a real problem.
- The linter knows front matter through its `front-matter` extension.
- The linter reads \r\n as two line breaks, so it gets every line ending as \n; the line numbers stay the same.
- A pragma comment cannot silence a rule: calm-md leaves pragma lines out of the scan and reports every issue with its line number in the original.
- The front matter's `title` never counts as a heading; `piko_bello.json` names a field no doc uses, since an empty name is not allowed.
- `write` checks the doc it would leave behind, and refuses if that doc has issues.
- `--as-is` turns the linter off for one call: calm-md works as before, and still says in one line how many issues wait.

### Steps

- [x] Pin pymarkdownlnt in `requirements.txt`.
- [x] `piko_bello.json` with the five heading rules.
- [x] The check in `toc`, `read` and `write`, and `--as-is`.
- [x] Test a doc with each of the five issues, a pragma trying to silence one, front matter, and `--as-is`.
- [x] `SKILL.md`, and `deploy.bat` copying `piko_bello.json`.
- [ ] A raven flies it.

## Zoom, numbers and find

### Decided

- The examples are in `calm_md_syntax_sketch.md`.
- `toc` shows the whole tree while it fits on a page of 100 lines; a bigger doc shows one level, says so in its first line, and zooms in by title or by number.
- A chapter's weight is its word count, split on whitespace; the skill says once: "All word counts are estimates!"
- A chapter with chapters inside says how many, like `(2300 words, 30 inside)`.
- A level with more than 100 chapters comes in pages: `--page 2`, and the last line says `page 2 of 3`.
- Every chapter has a number, its place in reading order, written `@3`; the next chapter is one higher.
- Numbers are for looking, in `toc`, `read` and `find`; `write` and `replace` take titles, so a number that shifted never changes the wrong chapter.
- Line numbers stay written out, like `line 4`, and are only shown.
- `find <file> <word> [title ...]`: one line per hit, with its number, its title path and five words on each side; word starts, case-insensitive.
  More than 10 hits give only the count, like `23 hits, more than 10: try a longer word, or a title path.`

### Steps

- [x] Numbers in `toc`, and `@3` in `toc` and `read`.
- [x] Word weights instead of line weights, and the one sentence in the skill.
- [ ] The zoom: one level for a doc bigger than a page, the inside counts, and pages.
- [ ] `find`.
- [ ] Test each on a big flat doc and a deep one, with LF and CRLF.
- [ ] `SKILL.md`, and a raven flies it.

## Steps

- [x] Settle the open questions with Wally.
- [x] Set up `skills/calm-md/.venv` with markdown-it-py and mdit-py-plugins from a `requirements.txt`.
- [x] Write `calm_md.py`, the parser and the three verbs, and `calm_md.sh`, the short call into the venv.
- [x] Test on one file with `#` and underlined headings, front matter, a `#` in a code fence and in a list, CRLF line endings, and two chapters with the same title under different parents.
- [x] `SKILL.md`, a `deploy.bat` that creates the venv like the token counter's, and a line in `INDEX.md`; the meta-deploy finds it by its `calm-` name.
- [ ] A raven flies it.

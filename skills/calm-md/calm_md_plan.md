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
    Each line ends with its chapter's weight in lines, subchapters included, like `## Attachments (42 lines)`.
  - `calm-md read <file> <title> ...`: the chapter's original lines, its heading line included.
  - `calm-md write <file> <title> ...`: replaces the chapter's lines with what comes on stdin, in the same shape, so a chapter can be read, changed and written back.
    Empty input is refused, and so is input that does not start with a heading line.
- Later: an override that turns every cap off, and maybe a verb that removes a chapter.

## Steps

- [x] Settle the open questions with Wally.
- [x] Set up `skills/calm-md/.venv` with markdown-it-py and mdit-py-plugins from a `requirements.txt`.
- [x] Write `calm_md.py`, the parser and the three verbs, and `calm_md.sh`, the short call into the venv.
- [x] Test on one file with `#` and underlined headings, front matter, a `#` in a code fence and in a list, CRLF line endings, and two chapters with the same title under different parents.
- [x] `SKILL.md`, a `deploy.bat` that creates the venv like the token counter's, and a line in `INDEX.md`; the meta-deploy finds it by its `calm-` name.
- [ ] A raven flies it.

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
- A chapter path is a list of titles from the top, like `"Attachments" "Steps"`; a path that fits more than one chapter is refused, with the candidates.
- Three verbs to start:
  - `calm-md toc <file>`: one line per chapter, indented by level; a long title is cut, with the count of omitted characters.
  - `calm-md read <file> <title> ...`: the chapter's original lines.
  - `calm-md write <file> <title> ...`: replaces the chapter's lines with what comes on stdin.

## Open questions

- The caps of `toc`: how long may a title be, and how many lines may the toc have?
- Does `toc` show each chapter's weight, like its number of lines, so a raven knows the size before it reads?
- Do `read` and `write` include the chapter's heading line, so a chapter can be read, changed and written back as it is?
- Is an empty stdin for `write` refused, so a chapter is never emptied by accident?

## Steps

- [ ] Settle the open questions with Wally.
- [ ] Set up `skills/calm-md/.venv` with markdown-it-py and mdit-py-plugins from a `requirements.txt`.
- [ ] Write `calm_md.py`, the parser and the three verbs, and `calm_md.sh`, the short call into the venv.
- [ ] Test on one file with `#` and underlined headings, front matter, a `#` in a code fence and in a list, CRLF line endings, and two chapters with the same title under different parents.
- [ ] `SKILL.md`, a `deploy.bat` that creates the venv like the token counter's, and a line in `INDEX.md`; the meta-deploy finds it by its `calm-` name.
- [ ] A raven flies it.

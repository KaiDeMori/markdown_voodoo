---
name: calm-md
description: >-
  A calm markdown file: its chapters at a glance, one chapter to read, one chapter to write.
  Use when a raven wants to see how a markdown file is built, read one chapter of it, or rewrite one chapter, without the whole file entering its window.
---

# calm-md

```
calm-md toc <file> [title ...]
calm-md read <file> <title> ...
calm-md write <file> <title> ... < chapter
```

Start zoomed out, and zoom in only when the answer asks for it:

| Command | Answers | Happy path |
|---|---|---|
| `toc <file> [title ...]` | How is it built, and how heavy is each part? | `  ## Attachments (10 lines)` |
| `read <file> <title> ...` | What does one chapter say? | the chapter's original lines, heading line included |
| `write <file> <title> ... < chapter` | Change one chapter, and nothing else | `Sample > Receiving: 4 lines became 5 lines.` |

- A chapter runs from its heading to the next heading of the same or a higher level, so it holds its subchapters, and its weight counts them too.
- Headings of every level make chapters; a heading inside a list item, a quote, a code block or front matter does not.
- A title is the heading's plain text: `## Setext *Chapter*` reads as `Setext Chapter`.
- A title path ends with the chapter's own title and needs only as many parents as it takes: `read notes.md Attachments Steps`. A path that fits more than one chapter is refused, with the candidates.
- `toc` shows at most 40 lines, then how many more; a title path after the file shows one chapter's part. A title longer than 60 characters is cut, with the count of what was cut.
- `write` takes the chapter in the shape `read` gives it, heading line first, on stdin; empty input, and input that does not start with a heading line, are refused.
- `write` changes only the chapter's lines, and the rest of the file stays byte for byte. The new lines take the file's own line endings, and a chapter followed by more ends with a blank line.
- A chapter with backticks, `$` or apostrophes goes in through a quoted heredoc, as in calm-comms.
- Files are read and written as UTF-8.
- The limits are the variables at the top of `calm_md.py`.

'nough said.

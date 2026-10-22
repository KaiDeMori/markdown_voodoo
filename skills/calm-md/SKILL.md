---
name: calm-md
description: >-
  A calm markdown file: its chapters at a glance, one chapter to read, one chapter to write.
  Use when a raven wants to see how a markdown file is built, read one chapter of it, rewrite one chapter, or fix one piece of text in it, without the whole file entering its window.
---

# calm-md

```
calm-md toc [--as-is] <file> [title ...]
calm-md read [--as-is] <file> <title> ...
calm-md write [--as-is] <file> <title> ... < chapter
calm-md replace [--as-is] <file> <title> ... < old line, new text
```

calm-md works only on piko bello markdown.
Before anything else, a linter checks the whole file by `piko_bello.json`; with issues, calm-md only lists them, like `3 issues, fix them and call again:`, one line each.
Fix the doc, then call again: file by file, the hall's markdown gets cleaner.

Start zoomed out, and zoom in only when the answer asks for it:

| Command | Answers | Happy path |
|---|---|---|
| `toc <file> [title ...]` | How is it built, and how heavy is each part? | `@2    ## Attachments (10 lines)` |
| `read <file> <title> ...` | What does one chapter say? | the chapter's original lines, heading line included |
| `write <file> <title> ... < chapter` | Change one chapter, and nothing else | `Sample > Receiving: 4 lines became 5 lines.` |
| `replace <file> <title> ... < old line, new text` | Fix one piece, and send only that | `Doc > Alpha: replaced on line 7.` |

- A chapter runs from its heading to the next heading of the same or a higher level, so it holds its subchapters, and its weight counts them too.
- Headings of every level make chapters; a heading inside a list item, a quote, a code block or front matter does not.
- A title is the heading's plain text: `## Setext *Chapter*` reads as `Setext Chapter`.
- A title path ends with the chapter's own title and needs only as many parents as it takes: `read notes.md Attachments Steps`. A path that fits more than one chapter is refused, with the candidates.
- Every chapter in the toc has a number, its place in reading order, like `@3`; `toc` and `read` take it instead of a title path, and the next chapter is `@4`.
  `write` and `replace` take titles only, so a number that shifted never changes the wrong chapter.
- `toc` shows at most 40 lines, then how many more; a title path after the file shows one chapter's part. A title longer than 60 characters is cut, with the count of what was cut.
- `write` takes the chapter in the shape `read` gives it, heading line first, on stdin; empty input, and input that does not start with a heading line, are refused.
- `write` changes only the chapter's lines, and the rest of the file stays byte for byte. The new lines take the file's own line endings, and a chapter followed by more ends with a blank line.
- `write` checks the doc it would leave behind, and refuses if that doc would have issues, so a clean doc stays clean.
- `--as-is` skips the check for one call: calm-md works anyway, and says on stderr how many issues wait.
- A pragma comment cannot silence a rule; calm-md leaves it out of the check.
- `piko_bello.json` starts quiet, with the heading rules only: one level at a time, `#` headings only, blank lines around headings, no title twice among siblings, one `#` title.
- `replace` takes the old text on stdin's first line and the new text after it, which may span lines; an empty second line deletes the old text.
  The old text has to occur exactly once in the chapter; otherwise calm-md names where it occurs, and nothing changes.
  The chapter keeps its heading line, and the doc it leaves behind is checked like after `write`.
- A chapter or a fix with backticks, `$` or apostrophes goes in through a quoted heredoc, as in calm-comms:

  ```
  calm-md replace notes.md Steps <<'EOF'
  teh quick
  the quick
  EOF
  ```
- Files are read and written as UTF-8.
- The limits are the variables at the top of `calm_md.py`.

'nough said.

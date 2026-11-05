# calm-pdf guide

How one PDF becomes one Markdown file, read by sight.

## Steps

1. **Render** every page at 240 dpi.
2. **Cut the views** of each page:
   - an overview: the whole page, scaled to a long side of 1000 px
   - five bands: full width, 700 px tall, spread from top to bottom so that neighbours overlap
3. **Write the skeleton** of the file: the title, the source lines, one `## Page N` chapter per page, and `## Unclear` at the end.
4. **Read each page:** its overview for the layout, then its bands for the text. Fill the page's chapter with `calm-md write`.
5. **Use the glass:** for every unclear spot, crop the region around it from a higher-resolution render, with generous margins, at a long side of about 1000 px. Read the whole region again, not only the flagged word. Fix the page with `calm-md replace`, and take a resolved spot off the Unclear list.

The reader reads only the views, never the PDF itself.
A text layer can be wrong: without a Unicode mapping, diacritics break apart.

## Rules for reading

- Not a summary: everything on the page becomes text.
- Typed text exactly as written, including errors in spelling and grammar, with headings, lists, captions and footnotes.
- Handwriting exactly as written, marked "(handwritten)".
- Italic and bold as Markdown. Other styles that carry meaning, like color or underline, in parentheses: "(blue, underlined)".
- Tables as Markdown tables. Formulas as written, in plain text or LaTeX.
- A figure gets a short, factual description where it sits, as a quote line, "> Description: …", with its label if the page gives one.
- The source's headings go below the page's chapter, one level down.
- What can't be read becomes "[unreadable]". Never a guess.
- Nothing added: no outside facts, no interpretation, no opinions.
- One paragraph or list item per line.
- Anything unclear, like the reading order, goes into the Unclear chapter, with its page.

## The file

```markdown
# A short, plain title

Source: report.pdf
Pages: 12
Converted: 2026-11-05, Haiku 5.5, read by sight from 240 dpi views

## Page 1

…

## Unclear

- Page 3: …
```

## What to expect

Measured with Haiku 5.5 at effort max as the reader:

- About 10K tokens of images per page in the reader's window: about 1K for the overview, about 1.7K per band.
- About a minute per page.
- The words "including errors in spelling and grammar" matter: without them, readers added a missing word to the source, twice.
- By sight, readers got words right where the text layer was broken. The glass caught a period that two readers had read as a comma.

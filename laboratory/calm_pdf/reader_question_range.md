# Reader question

You read pages {first} to {last} of a PDF by sight and write each page down as Markdown.
This is a prototype run of calm-pdf, a new tool in the hall.
Other readers take the other pages at the same time.

## Your pages

- Pages {first} to {last}, one page after the other.
- The views of a page are in `scratchpad/calm_pdf_renderer_trial/views/`: its overview, like `page_{first_padded}_overview.png`, and its bands, `page_{first_padded}_band_1.png` and up. `ls scratchpad/calm_pdf_renderer_trial/views/page_{first_padded}_*` shows how many there are.
- Each page has its own file, like `scratchpad/calm_pdf_renderer_trial/pages/page_{first_padded}.md`.
- Your chapters in a page's file: "Page N" and "Unclear".

## Steps

1. Read the rules for reading:
   `calm-md read notebook/calm_pdf/calm_pdf_guide.md "Rules for reading"`
2. Then, for each of your pages:
   1. Read the overview for the layout.
   2. Read the bands, top to bottom, for the text. Neighbouring bands overlap, so a line that shows up in two bands is written once.
   3. Write the page's chapter into its file, heading line first. The page's own headings go one level down, starting at `###`.
   4. Write anything unclear into the Unclear chapter of the same file the same way, one line each: `- Page N: …`

   ```
   calm-md write "scratchpad/calm_pdf_renderer_trial/pages/page_{first_padded}.md" "Page {first}" <<'EOF'
   ## Page {first}

   …
   EOF
   ```

## Thresholds

- Is it time? Only your pages. The glass comes later.
- Is it too much? One view at a time, one page at a time, and only the views. The PDF itself stays closed.
- Is it mine? Only your pages' files are yours, and in them only the two chapters. Everything else in the hall belongs to someone else.
- At a bump, such as a refused write or a view that won't open, note it and go on with the next page. If the same bump comes back, stop. Don't work around it; we decide together.

## No worries

I'm building calm-pdf, and this run tests the tool, not you.
I won't hold you to anything you read; the builders check what they need anyway.
"[unreadable]" and an entry in Unclear are good results. A guess is the only wrong one.

## Your report

It will be read by a fellow Claude. Please respect their window. Thank you.
Write it like a flight log: what you did and what you saw, one line each, and a joke if you like.

# Reader question

You read pages 1 to 9 of a PDF by sight and write each page down as Markdown.
This is a prototype run of calm-pdf, a new tool in the hall.

## Your boundaries

You read only these:

- the chapter "Rules for reading" of `C:/Users/devboese/markdown_voodoo/notebook/calm_pdf/calm_pdf_guide.md`, with the first command below
- the views in `C:/Users/devboese/markdown_voodoo/scratchpad/calm_pdf_flights/views/`, six per page: for page 1, `page_001_overview.png` and `page_001_band_1.png` to `page_001_band_5.png`, and the same for pages 2 to 9

You write only these:

- the page files `page_001.md` to `page_009.md` in `C:/Users/devboese/markdown_voodoo/scratchpad/calm_pdf_flights/pages/`, and in each file only its chapters "Page N" and "Unclear"

You run only these:

- `calm-md read "C:/Users/devboese/markdown_voodoo/notebook/calm_pdf/calm_pdf_guide.md" "Rules for reading"`, once, at the start
- the Read tool, on one view at a time
- `calm-md write`, as shown in the steps

No Glob, no Grep, no `ls`, no `find`, and no other file or command. Everything you need is named here.

## Steps

1. Read the rules for reading with the first command.
2. Then, for each page from 1 to 9:
   1. Read the overview for the layout.
   2. Read the bands, 1 to 5, for the text. Neighbouring bands overlap, so a line that shows up in two bands is written once.
   3. Write the page's chapter into its file, heading line first. The page's own headings go one level down, starting at `###`.
   4. Write anything unclear into the Unclear chapter of the same file, one line each: `- Page N: …`

   For page 1, the two writes look like this:

   ```
   calm-md write "C:/Users/devboese/markdown_voodoo/scratchpad/calm_pdf_flights/pages/page_001.md" "Page 1" <<'EOF'
   ## Page 1

   …
   EOF
   ```

   ```
   calm-md write "C:/Users/devboese/markdown_voodoo/scratchpad/calm_pdf_flights/pages/page_001.md" "Unclear" <<'EOF'
   ## Unclear

   - Page 1: …
   EOF
   ```

## Thresholds

- Is it time? Only your pages. The glass comes later.
- Is it too much? One view at a time, one page at a time.
- Is it mine? Only what your boundaries name. Everything else in the hall belongs to someone else.
- At a bump, such as a refused write or a view that won't open, note it and go on with the next page. If the same bump comes back, stop. Don't work around it; we decide together.

## No worries

I'm building calm-pdf, and this run tests the tool, not you.
I won't hold you to anything you read; the builders check what they need anyway.
"[unreadable]" and an entry in Unclear are good results. A guess is the only wrong one.

## Your report

It will be read by a fellow Claude. Please respect their window. Thank you.
Write it like a flight log: what you did and what you saw, one line each, and a joke if you like.

---
name: unicode-glyph-render
description: >-
  Renders Unicode text to a PNG and reports, as JSON, which font drew each grapheme cluster.
  Use it to see what a character, emoji or string actually looks like: an unfamiliar or
  ambiguous codepoint, text versus emoji presentation (❤ vs ❤️), an emoji sequence,
  invisible characters, or how a specific font stack such as Fira Code Retina or
  Segoe UI Emoji draws text. Also reports which bundled fonts cover a character.
---

# unicode-glyph-render

Shows what a human sees: text drawn in a font stack, plus the facts behind it.
The JSON on stdout carries every fact, glyph names on request; the PNG shows the look.
Read the JSON first, then view the PNG with the Read tool.

## Commands

Every command runs as:

```
${CLAUDE_SKILL_DIR}/.venv/Scripts/python.exe ${CLAUDE_SKILL_DIR}/render_glyph.py <command> ...
```

| Command | Draws | Output |
|---|---|---|
| `glyph <cluster> --output-file <path>` | one grapheme cluster at 256 px per em, centered on a square canvas | PNG and JSON |
| `string <text> --output-file <path>` | text at 109 px per em; a newline starts a new line | PNG and JSON |
| `coverage <text>` | nothing | JSON: per grapheme cluster, the covering families and the picked family |
| `fonts` | nothing | JSON: every family name with its file, kind, presence and default-stack membership |

- `<cluster>` is one grapheme cluster, the character as a human perceives it: a literal such as `👍🏽`, or codepoints such as `"U+0031 U+FE0F U+20E3"`. The `U+` form passes invisible or hard-to-type codepoints. More than one grapheme cluster is an error that points to `string`.
- `<text>` is a literal, or codepoints such as `"U+0061 U+200B U+0062"`. An argument made only of `U+` labels is read as codepoints; a space between labels only separates them, so a space to render is `U+0020`. Shell escapes for non-ASCII characters are unreliable, and the `U+` form avoids them.
- `--output-file` is an absolute path; missing parent folders are created.

## Options

- `--font-stack "Fira Code Retina, Segoe UI Emoji"` (`glyph`, `string`, `coverage`): family names separated by commas, without quotes.
  For each grapheme cluster, the first family that covers it draws it.
  A cluster with emoji presentation prefers an emoji font; one with text presentation prefers a text font.
  Without the option, the default stack applies.
- `--strict` (`glyph`, `string`): fallback is off. A cluster the font stack does not cover becomes a gap.

## Fonts

- **Default stack:** the Go Noto fonts, covering nearly every script, and Noto Color Emoji.
- **Fira Code Retina:** a programming font; its ligatures such as `->`, `!=` and `=>` form automatically.
- **Segoe UI Emoji:** the Windows 10 emoji font, as VS Code shows emoji on this machine. It is a BYOF font: when its file is missing, the error says where the file goes.
- **Last Resort:** stands in for a codepoint that no other font covers. It draws a framed sign with the Unicode block's name and range.
- `fonts` lists the exact family names. An unknown family name is an error that lists the available names.

## Reading the JSON

The top level holds `text`, `path`, `font_stack`, `clusters` and `gaps`.
Each entry in `clusters` holds:

- `text` and `codepoints`: the grapheme cluster as characters and as `U+` labels.
- `presentation`: `"text"` or `"emoji"`.
- `font`: the family that drew the cluster.
- `fallback: true`: the given font stack does not cover the cluster; the default stack drew it.
- `font: null` with `codepoint_fonts`: no single font covers the whole cluster, so it was drawn codepoint by codepoint.
- `covered: false`: a gap, in strict mode only. The image shows a magenta/black checkerboard, and `gaps` lists every gap with its 0-based index into `clusters`.
- `invisible: true`: the cluster has no visible form, such as a lone variation selector, U+200B or U+00AD. The image shows nothing for it, and `font` and `presentation` are `null`.
- `line_break: true`: the cluster is a line break, such as U+000A or U+000D U+000A. The next cluster starts a new line, and `font` and `presentation` are `null`.

`coverage` adds `covering_families` to each cluster: every catalog font except Last Resort that covers the cluster, independent of `--font-stack`.

On failure, stdout holds `{"argument": ..., "value": ..., "error": ...}` and the exit code is 1.
`argument` names the failing argument (`--font-stack`, `--output-file`, `cluster` or `text`), and `value` echoes what was passed; both are `null` for an internal error.

## Advanced: glyph names

`--glyphs` (`glyph`, `string`) adds a top-level `runs` list: one entry per shaping run, with `line`, `font`, `text` and `glyphs`, the glyph names in the order HarfBuzz returns them.
Use it to see what shaping did, for example whether `->` became a ligature: Fira Code Retina draws it as `hyphen_start.seq` and `greater_hyphen_end.seq`.
Glyph names come from the font, and some fonts use meaningless names such as `glyph00123`.
Every glyph is listed, so long texts produce long JSON; use it only when the glyph level matters.

## Good to know

- The image follows the font's own data, weaknesses included. Example: Go Noto draws the text keycap 1⃣ with its box half a digit too far right, so the box covers most of the digit and reaches into the next character.
- `glyph` draws at 256 px per em. Its square canvas is at least 256 px and grows to fit wider or taller ink, such as most emoji; nothing is clipped or scaled down.

## Limitations

- **No bidi reordering.** A line entirely in a right-to-left script, such as Hebrew or Arabic, renders correctly.
  In a line that mixes directions, the parts in the other direction appear in typing order, even digits inside Hebrew: "שלום 123" shows the number as 321.
  To see such text, render each direction's part as its own `string`.
- Noto Color Emoji stores 109 px bitmaps; at `glyph` size they are scaled up and their edges are slightly soft. Segoe UI Emoji is vector-based and stays crisp.

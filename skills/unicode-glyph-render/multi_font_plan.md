# Multi-font plan

Font selection and proper emoji support for the `unicode-glyph-render` noema.

Status: direction and implementation decisions locked; implementation not started.

## Audience

Claude implements this plan, and Claude is the noema's user.
Every output is designed for that user: Claude reads the JSON on stdout and views the PNG with the Read tool.

## Goal

The noema shows Claude what a human sees: text, drawn in a given font stack.
The leading use case is fidelity: rendering text the way a specific environment shows it.

## Principles

- **The JSON carries every fact; the image shows the look.** Claude reads the JSON exactly but sees images approximately, so nothing important may exist only in the image.
- **Input errors fail; coverage falls back.** A wrong argument is the caller's mistake and fails immediately. A missing glyph is nobody's mistake; the noema falls back and reports it.

## Terms

- **Grapheme cluster:** a user-perceived character, as defined by Unicode (UAX #29). 👨‍👩‍👧, 🇩🇪 and 1️⃣ are one grapheme cluster each.
- **Family name:** the font's family name from nameID 1, as classic Windows apps show it in their font menus. Example: "Fira Code Retina".
- **Font catalog:** the dict in `render_glyph.py` that maps each family name to its file, relative to `fonts/`.
- **BYOF font:** a font the repo never ships and never fetches. Everyone brings their own copy into `fonts/BYOF/`, which is git-ignored.
- **Text font / emoji font:** a font with color glyph tables (CBDT, COLR, SVG, sbix) is an emoji font; every other font is a text font.
- **Font stack:** an ordered list of family names.
- **Default stack:** the font stack used when none is given, and the fallback for every given font stack.
- **Cover:** a font covers a grapheme cluster when HarfBuzz shapes it without a `.notdef` glyph.
- **Presentation:** whether a grapheme cluster shows as text or as emoji.
- **Fallback:** drawing a grapheme cluster with the default stack, because the given font stack does not cover it.
- **Strict mode:** rendering without fallback.
- **Gap:** in strict mode, a grapheme cluster that the given font stack does not cover.
- **Stand-in:** a Last Resort glyph, drawn for a single codepoint that no other font covers.

## Direction decisions

1. **The unit is the grapheme cluster.**
   Font selection happens per grapheme cluster, never per codepoint.
   `glyph` renders exactly one grapheme cluster; `string` renders any number.
   Why: emoji sequences must reach the shaper as a whole.
2. **Fonts are addressed by family name.**
   The font catalog lists every usable font; its files live in `fonts/`.
3. **A font stack works like CSS `font-family`.**
   For each grapheme cluster, the first family that covers it draws it.
4. **The default stack is ordered deliberately.**
   It replaces the alphabetical file order.
5. **Presentation is a preference inside the font stack.**
   A grapheme cluster with emoji presentation prefers emoji fonts; one with text presentation prefers text fonts.
   If no font of the preferred kind covers it, the first covering font draws it.
6. **Fallback is visible.**
   The JSON result reports which font drew which grapheme cluster.
   Strict mode disables fallback.
7. **Discovery.**
   A list of the usable family names, and a coverage report: which fonts cover each grapheme cluster.

## Implementation decisions

Letters match the decision tour.

- **H. Family names are nameID 1 names.**
  The font catalog maps each family name to exactly one file.
  Why: every style is reachable by name alone, without a weight option. It is the name Notepad++ shows.
- **J. The default stack is an explicit list of family names in `render_glyph.py`.**
  A font in `fonts/` that is not on the list is used only when `--font-stack` names it.
  BYOF fonts are never on the list.
  Why: adding a font never changes existing renders, and a fresh clone without BYOF fonts has a complete default stack.
- **L. A gap is drawn as a magenta/black checkerboard.**
  The JSON lists every gap under `gaps`.
  Why: the checkerboard is unmistakable in the image, and the facts are in the JSON.
- **M1. `--font-stack` takes one argument: family names separated by commas.**
  Whitespace around each name is trimmed. Quotes are not part of the syntax.
  Every family name in the font catalog is comma-free.
- **M2. An unknown family name in `--font-stack` is an error.**
  The error lists the available family names.
  A catalog entry whose file is missing is an error that names the file; for a BYOF font, it says where the file goes.
  Why: input errors fail; coverage falls back.
- **P. The fonts to bring: Fira Code first, then Segoe UI Emoji.**
  Fira Code tests font stacks and ligatures.
  Segoe UI Emoji is what VS Code shows on Windows 10; it is COLRv0, so it needs no new drawing engine.
  Segoe UI Emoji is a BYOF font: its license permits use, not redistribution.
  Nothing is ever taken out of the Windows folder.
  Proprietary material we deliberately redistribute, such as a future Apple emoji set, lives in `fonts/proprietary/`, with a note that the repo's MIT license does not cover it.

## Implementation notes

These follow from the decisions and have no viable alternative.

- **Grapheme clusters:** the `regex` module's `\X`.
- **Presentation rule:** U+FE0F means emoji, U+FE0E means text. Skin tone modifiers, flags and tag sequences mean emoji. Otherwise the first codepoint's `Emoji_Presentation` property decides. The property data comes from `regex`.
- **Font catalog:** adding a font means adding one line. The kind (text or emoji) is read from the file.
  Why a catalog instead of scanning `fonts/`: fonts change only here, in the workshop, by our own hands.
- **Coverage:** if no font covers the whole grapheme cluster, the cluster is split per codepoint.
- **Last Resort:** never covers a whole grapheme cluster; it only provides stand-ins.
- **Rendering:** one pipeline for `glyph` and `string`: HarfBuzz shaping, FreeType rasterization. The Pillow `ImageFont` path goes away.
  - Consecutive grapheme clusters drawn by the same font form one shaping run, so ligatures across clusters, such as Fira Code's `->`, still form.
  - CBDT glyphs are decoded from the font's PNG data with fontTools, because the bundled FreeType has no PNG support.
  - Bitmap fonts use the nearest strike, scaled to the target size.
  - Target sizes stay 256 px (`glyph`) and 109 px (`string`), no longer tied to a strike.
  - COLRv0 through FreeType's `FT_LOAD_COLOR`. COLRv1 and SVG are not supported.
- **CLI:**
  - `glyph` takes exactly one grapheme cluster: literal, or codepoints like `"U+0031 U+FE0F U+20E3"`. More than one grapheme cluster is an error that points to `string`.
  - `glyph` and `string` take `--font-stack` and `--strict`.
  - New subcommands: `fonts` (family names, files, kinds) and `coverage <text>` (per grapheme cluster: codepoints, presentation, covering families, and the family the font stack picks). `coverage` takes `--font-stack` as well.
- **JSON:** per grapheme cluster `text`, `codepoints`, `presentation`, `font`, `fallback`, `covered`. Top level `path`, `font_stack`, `clusters`, `gaps`.
- **Dev test cases:** `render_test_glyphs.py` gains 👨‍👩‍👧, 🇩🇪, 🏴󠁧󠁢󠁳󠁣󠁴󠁿, 1⃣ vs 1️⃣, ❤ vs ❤️, ☺︎ vs ☺️ and 👍🏽, plus Fira Code ligatures.
- **`platform_notes.md`:** verified library and font facts, one per entry: the claim in bold, the explanation, the primary source in brackets.
- **SKILL.md:** rewritten for the new options. Its description says when to use the noema, not only what the commands do.
- **`deploy.bat`:** following the repo's convention, for the end-to-end test loop.

## Not now

- Comparison of several font stacks in one image. Claude composes comparisons from separate renders.
- System fonts.
- Size, weight, colors, themes.
- Profiles: a name, a font stack and rendering options such as ligatures on or off. Examples: "VS Code editor", "Wally's Notepad++" (Fira Code Retina, ligatures on). The font stack is their foundation.
- Emoji image sets (emoji-datasource): one mechanism would bring four vendor looks, Apple (what Signal shows), Google, Twitter and Facebook. They are bitmaps of 64 px, not fonts, so they need an extension of decision 2 and a second drawing path.
- COLRv1 and SVG fonts.
- Unicode names in the JSON.

## Verified facts

Current implementation:

- The font catalog lists 12 families; every key matches its file's nameID 1. GoNotoCurrent's family name is "Go Noto Current-Regular".
- `pick_font_for_codepoint` takes the first family of the provisional `DEFAULT_STACK` whose cmap covers the codepoint.
  Last Resort is used only when no family of the default stack covers the codepoint.
- The default stack lists the Go Notos before Noto Color Emoji, so characters with both a text and an emoji form (1, ©, ❤) get a Go Noto text glyph.
- U+200D (ZWJ) and U+20E3 (keycap) resolve to Go Noto Current-Regular.
  U+FE0E and U+FE0F are covered only by Last Resort.
- `split_into_font_runs` starts a new run at every font change, so ZWJ sequences, keycaps and VS16 sequences reach HarfBuzz in pieces.
- `glyph` accepts exactly one codepoint. No CLI option selects a font; Fira Code Retina and Segoe UI Emoji sit outside the default stack and wait for `--font-stack`.
- The bundled FreeType (freetype-py's `libfreetype.dll`) has no PNG support: loading a Noto Color Emoji glyph fails with "unimplemented feature", and the DLL contains no libpng.
  `string` therefore fails on every emoji drawn from Noto Color Emoji. `glyph` decodes CBDT glyphs with fontTools and works.
- No catalog font is variable. Only Fira Code Retina carries nameID 16.
- Noto Color Emoji is CBDT with a single strike at 109 ppem.
- Go Noto Current's `.notdef` is a plain rectangle. Noto Color Emoji's `.notdef` is empty.
- Libraries: FreeType 2.13.2, HarfBuzz 14.2.1 (uharfbuzz 0.55.0), fontTools 4.63.0, Pillow 12.3.0 without raqm, regex 2026.9.29.
- `regex`'s `\X` keeps ZWJ sequences, flags, tag flags, keycaps, presentation sequences, skin tones and Indic conjuncts whole.
  `regex` offers `Emoji_Presentation`, `Emoji_Modifier`, `Regional_Indicator` and `Extended_Pictographic`.
- HarfBuzz hides variation selectors a font lacks (U+FE0F, U+FE0E, U+E0100), so a cluster containing one counts as covered.
- The `coverage` subcommand picks, with the default stack: ❤ → Go Noto Current-Regular, ❤️ → Noto Color Emoji; 1⃣ → Go Noto, 1️⃣ → Noto Color Emoji; 👍🏽, 🇩🇪, 👨‍👩‍👧 and 🏴󠁧󠁢󠁳󠁣󠁴󠁿 → Noto Color Emoji as one cluster each.
  With `--font-stack "Fira Code Retina, Segoe UI Emoji"`: text → Fira Code Retina, 😀 and ❤️ → Segoe UI Emoji, ꙮ → Go Noto Current-Regular as fallback.
  😀 followed by U+0301 has no single covering font and is split: Noto Color Emoji, then Go Noto Current-Regular.

Fira Code:

- The source is tonsky's release 6.2 (2021), `Fira_Code_v6.2.zip`; `font_installer.py` extracts `ttf/FiraCode-Retina.ttf` from it.
- Only the static TTFs contain Retina. `woff/` and `woff2/` have no Retina file.
- The variable font has no Retina instance (Light, Regular, Medium, SemiBold, Bold), and its nameID 1 is "Fira Code Light".
- `FiraCode-Retina.ttf` carries nameID 1 "Fira Code Retina", nameID 16 "Fira Code", nameID 17 "Retina", weight class 450, license OFL 1.1 in nameID 13 and 14.
- Its ligatures live in `calt`; there is no `liga` feature.
- `shape_run` passes no features to HarfBuzz, and the default `calt` draws the ligatures: `->`, `!=`, `=>`, `===`, `<=`, `www` render as ligatures.

Segoe UI Emoji:

- `fonts/BYOF/seguiemj.ttf`: nameID 1 "Segoe UI Emoji", version 1.29, COLR version 0 with CPAL, 12189 glyphs.
- Its license string (nameID 13) permits creating, displaying and printing content; it says nothing about redistribution.

## To confirm

- FreeType renders COLRv0 glyphs in color with `FT_LOAD_COLOR`.

## Testing

- Dev checks run against the repo code: import `render_glyph.py` or run it directly. Never through the Skill tool.
- Ad-hoc dev renders go to the session scratchpad.
- End-to-end tests of the deployed noema run in another workspace, in a fresh session.

## Next

Proposed implementation order:

1. Bring the fonts: done. Fira Code Retina via `font_installer.py`; Segoe UI Emoji as a BYOF font in `fonts/BYOF/`.
2. Font catalog, kinds and a provisional default stack; the `fonts` subcommand: done.
3. Grapheme clusters, presentation and coverage; the `coverage` subcommand: done.
4. The unified rendering pipeline: font stack, fallback, strict mode, gaps, JSON.
5. Dev test cases, `platform_notes.md`, SKILL.md, `deploy.bat`.

Details whose behavior only shows in practice get settled by trying them on tricky test cases.

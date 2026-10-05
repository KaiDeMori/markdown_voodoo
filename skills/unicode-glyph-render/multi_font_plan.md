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
   The only font source is the bundled `fonts/` folder (BYOF: bring your own font).
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

- **H. Family names come from nameID 1.**
  Among several files with the same family name, the Regular one is used.
  Why: every style is reachable by name alone, without a weight option. It is the name Notepad++ shows.
- **J. The default stack is an explicit list of family names in `render_glyph.py`.**
  A font in `fonts/` that is not on the list is used only when `--font-stack` names it.
  Why: adding a font never changes existing renders.
- **L. A gap is drawn as a magenta/black checkerboard.**
  The JSON lists every gap under `gaps`.
  Why: the checkerboard is unmistakable in the image, and the facts are in the JSON.
- **M1. `--font-stack` takes one argument: family names separated by commas.**
  Whitespace around each name is trimmed. Quotes are not part of the syntax.
  The registry rejects a font whose family name contains a comma, at load time.
- **M2. An unknown family name in `--font-stack` is an error.**
  The error lists the available family names.
  Why: input errors fail; coverage falls back.
- **P. The fonts to bring: Fira Code first, then Segoe UI Emoji.**
  Fira Code tests font stacks and ligatures.
  Segoe UI Emoji is what VS Code shows on Windows 10; it is COLRv0, so it needs no new drawing engine.
  Proprietary fonts live in `fonts/proprietary/`, with a note that the repo's MIT license does not cover them.

## Implementation notes

These follow from the decisions and have no viable alternative.

- **Grapheme clusters:** the `regex` module's `\X`. New dependency; verify its behavior once installed.
- **Presentation rule:** U+FE0F means emoji, U+FE0E means text. Skin tone modifiers, flags and tag sequences mean emoji. Otherwise the first codepoint's `Emoji_Presentation` property decides. The property data comes from `regex` if it has it, otherwise from Unicode's `emoji-data.txt`, bundled.
- **Registry:** scans `fonts/`, including `fonts/proprietary/`.
- **Coverage:** if no font covers the whole grapheme cluster, the cluster is split per codepoint.
- **Last Resort:** never covers a whole grapheme cluster; it only provides stand-ins.
- **Rendering:** one pipeline for `glyph` and `string`: HarfBuzz shaping, FreeType rasterization. The Pillow `ImageFont` path and the CBDT special case go away.
  - Bitmap fonts use the nearest strike, scaled to the target size.
  - Target sizes stay 256 px (`glyph`) and 109 px (`string`), no longer tied to a strike.
  - COLRv0 through FreeType's `FT_LOAD_COLOR`. COLRv1 and SVG are not supported.
- **CLI:**
  - `glyph` takes exactly one grapheme cluster: literal, or codepoints like `"U+0031 U+FE0F U+20E3"`. More than one grapheme cluster is an error that points to `string`.
  - `glyph` and `string` take `--font-stack` and `--strict`.
  - New subcommands: `fonts` (family names, files, kinds) and `coverage <text>` (per grapheme cluster: codepoints, presentation, covering families, and the family the font stack picks).
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

- `pick_font_for_codepoint` takes the first font in alphabetical file order whose cmap covers the codepoint.
  `LastResort-Regular` is used only when no other font covers the codepoint.
- All GoNoto fonts sort before `NotoColorEmoji`, so characters with both a text and an emoji form (1, ©, ☀, ☺, ❤) always get a GoNoto text glyph.
- U+200D (ZWJ) and U+20E3 (keycap) resolve to `GoNotoAfricaMiddleEast`.
  U+FE0E and U+FE0F are covered only by `LastResort-Regular`.
- `split_into_font_runs` starts a new run at every font change, so ZWJ sequences, keycaps and VS16 sequences reach HarfBuzz in pieces.
- `glyph` accepts exactly one codepoint. No CLI option selects a font.
- All 10 bundled fonts have distinct family names (nameID 1). GoNotoCurrent's family name is "Go Noto Current-Regular". None has nameID 16.
- No bundled font is variable, and none has COLR, SVG or sbix.
  The only emoji font is `NotoColorEmoji`: CBDT with a single strike at 109 ppem.
- Go Noto Current's `.notdef` is a plain rectangle. Noto Color Emoji's `.notdef` is empty.
- Libraries: FreeType 2.13.2, HarfBuzz 14.2.1 (uharfbuzz 0.55.0), fontTools 4.63.0, Pillow 12.3.0 without raqm. `regex` is not installed.
- Until decision J is implemented, the alphabetical file order puts `FiraCode-Retina.ttf` first, so the repo copy draws Latin text in Fira Code Retina.

Fira Code:

- The source is tonsky's release 6.2 (2021), `Fira_Code_v6.2.zip`; `font_installer.py` extracts `ttf/FiraCode-Retina.ttf` from it.
- Only the static TTFs contain Retina. `woff/` and `woff2/` have no Retina file.
- The variable font has no Retina instance (Light, Regular, Medium, SemiBold, Bold), and its nameID 1 is "Fira Code Light".
- `FiraCode-Retina.ttf` carries nameID 1 "Fira Code Retina", nameID 16 "Fira Code", nameID 17 "Retina", weight class 450, license OFL 1.1 in nameID 13 and 14.
- Its ligatures live in `calt`; there is no `liga` feature.
- `shape_run` passes no features to HarfBuzz, and the default `calt` draws the ligatures: `->`, `!=`, `=>`, `===`, `<=`, `www` render as ligatures.

## To confirm

- FreeType renders COLRv0 glyphs in color with `FT_LOAD_COLOR`.
- `regex`'s `\X` handles ZWJ sequences, flags and tag sequences; `regex` offers the `Emoji_Presentation` property.

## Testing

- Dev checks run against the repo code: import `render_glyph.py` or run it directly. Never through the Skill tool.
- Ad-hoc dev renders go to the session scratchpad.
- End-to-end tests of the deployed noema run in another workspace, in a fresh session.

## Next

Proposed implementation order:

1. Bring the fonts: Fira Code Retina is done. Segoe UI Emoji needs a source; nothing is ever taken out of the Windows folder.
2. Registry: family names, kinds, the comma rule; the `fonts` subcommand.
3. Grapheme clusters, presentation and coverage; the `coverage` subcommand.
4. The unified rendering pipeline: font stack, fallback, strict mode, gaps, JSON.
5. Dev test cases, `platform_notes.md`, SKILL.md, `deploy.bat`.

Details whose behavior only shows in practice get settled by trying them on tricky test cases.

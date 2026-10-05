# Multi-font plan

Font selection and proper emoji support for the `unicode-glyph-render` noema.

Status: direction agreed; implementation not designed yet.

## Audience

Claude implements this plan, and Claude is the noema's user.
Every output is designed for that user: Claude reads the JSON on stdout and views the PNG with the Read tool.

## Goal

The noema shows Claude what a human sees: text, drawn in a given font stack.
The leading use case is fidelity: rendering text the way a specific environment shows it.

## Terms

- **Grapheme cluster:** a user-perceived character, as defined by Unicode (UAX #29). 👨‍👩‍👧, 🇩🇪 and 1️⃣ are one grapheme cluster each.
- **Font stack:** an ordered list of font family names.
- **Default stack:** the font stack used when none is given, and the fallback for every given font stack.
- **Presentation:** whether a grapheme cluster shows as text or as emoji. Unicode's defaults (the `Emoji_Presentation` property) and the variation selectors VS15 (U+FE0E) and VS16 (U+FE0F) decide it.
- **Fallback:** drawing a grapheme cluster with the default stack, because the given font stack does not cover it.
- **Strict mode:** rendering without fallback.

## Decisions

1. **The unit is the grapheme cluster.**
   Font selection happens per grapheme cluster, never per codepoint.
   `glyph` renders exactly one grapheme cluster; `string` renders any number.
   Why: emoji sequences must reach the shaper as a whole.
2. **Fonts are addressed by family name.**
   The only font source is the bundled `fonts/` folder (BYOF: bring your own font).
3. **A font stack works like CSS `font-family`.**
   For each grapheme cluster, the first family that covers the whole grapheme cluster draws it.
4. **The default stack is ordered deliberately.**
   It replaces the alphabetical file order.
5. **Presentation is a preference inside the font stack.**
   A grapheme cluster with emoji presentation prefers emoji fonts; one with text presentation prefers text fonts.
   If no font of the preferred kind covers it, the first covering font draws it.
6. **Fallback is visible.**
   The JSON result reports which font drew which grapheme cluster.
   Strict mode disables fallback and leaves uncovered grapheme clusters visible as gaps.
7. **Discovery.**
   A list of the usable family names, and a coverage report: which fonts cover each grapheme cluster.

## Not now

- Comparison of several font stacks in one image. Claude composes comparisons from separate renders.
- System fonts.
- Size, weight, colors, themes.
- Profiles: a name, a font stack and rendering options such as ligatures on or off. Examples: "VS Code editor", "Wally's Notepad++" (Fira Code Retina, ligatures on). The font stack is their foundation.

## Current implementation

Verified facts that motivate the decisions:

- `pick_font_for_codepoint` takes the first font in alphabetical file order whose cmap covers the codepoint.
  `LastResort-Regular` is used only when no other font covers the codepoint.
- All GoNoto fonts sort before `NotoColorEmoji`, so characters with both a text and an emoji form (1, ©, ☀, ☺, ❤) always get a GoNoto text glyph.
- U+200D (ZWJ) and U+20E3 (keycap) resolve to `GoNotoAfricaMiddleEast`.
  U+FE0E and U+FE0F are covered only by `LastResort-Regular`.
- `split_into_font_runs` starts a new run at every font change, so ZWJ sequences, keycaps and VS16 sequences reach HarfBuzz in pieces.
- `glyph` accepts exactly one codepoint.
- No CLI option selects a font.

## To confirm

- `shape_run` passes no features to HarfBuzz, so HarfBuzz's default features apply, including `liga` and `calt`.
  Fira Code's ligatures should therefore show up without extra work.

## Testing

- Dev checks run against the repo code: import `render_glyph.py` or run it directly. Never through the Skill tool.
- End-to-end tests of the deployed noema run in another workspace, in a fresh session.

## Next

Work through the implementation questions one at a time.
Details whose behavior only shows in practice get settled by trying them on tricky test cases.

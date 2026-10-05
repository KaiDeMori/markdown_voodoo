# Platform notes

Library and font behavior the implementation depends on.
Every entry was verified, and its source is named in brackets.
Treat each entry as a claim to re-check when a package version or a font file changes.

## Versions

- **FreeType 2.13.2 (freetype-py's bundled `libfreetype.dll`), HarfBuzz 14.2.1 (uharfbuzz 0.55.0), fontTools 4.63.0, Pillow 12.3.0, regex 2026.9.29.** The entries below were verified against exactly these versions. [`freetype.version()`, `uharfbuzz.version_string()`, package versions]

## FreeType

- **The bundled FreeType has no PNG support.** Loading a glyph from a PNG-based bitmap font such as Noto Color Emoji (CBDT) fails with "unimplemented feature", and the DLL contains no libpng. CBDT glyphs are therefore decoded with fontTools. [reproduced directly; DLL string search]
- **`FT_LOAD_COLOR | FT_LOAD_RENDER` renders COLRv0 glyphs as BGRA bitmaps.** Segoe UI Emoji's 😀 comes out as `FT_PIXEL_MODE_BGRA`. [reproduced directly]
- **FreeType's BGRA bitmaps are premultiplied.** Across 2227 semi-transparent pixels of five Segoe UI Emoji glyphs, no color channel exceeds alpha. Pillow reads them with the raw mode `BGRa`. [verified by test]

## HarfBuzz

- **Default features apply when `shape` gets no feature list.** Fira Code's ligatures (`->`, `!=`, `=>`, `===`, `<=`, `www`) form through its default `calt` feature. [verified by test]
- **HarfBuzz hides default-ignorable codepoints a font lacks.** A cluster containing U+FE0F, U+FE0E or U+E0100 shapes without a `.notdef` glyph even in a font without those codepoints. A cluster made only of such codepoints therefore looks covered by any font. [verified by test]
- **Glyph positions follow the font's own data, including its weaknesses.** In Go Noto Current, the text keycap 1⃣ is shaped as `one.deva` plus U+20E3 (advance 0, left side bearing −422/1000) without mark attachment, so the keycap box sits half a digit too far right. [verified by test; font file]

## regex

- **`\X` keeps every emoji sequence whole.** ZWJ sequences, flags, tag flags, keycaps, presentation sequences and skin tones form one cluster each, and so do Indic conjuncts. [verified by test]
- **The emoji properties are available.** `Emoji_Presentation`, `Emoji_Modifier`, `Regional_Indicator`, `Extended_Pictographic` and `Default_Ignorable_Code_Point` match as Unicode defines them; ❤ has no `Emoji_Presentation`, 😀 has it. [verified by test]

## Pillow

- **Pillow is built without raqm.** It cannot shape complex text, which is why shaping runs through HarfBuzz directly. [`PIL.features.check("raqm")`]
- **The raw modes `BGRA` and `BGRa` both exist.** `BGRa` is the premultiplied one. [verified by test]

## Fonts

- **Noto Color Emoji is CBDT with a single strike at 109 ppem.** Its glyphs use format 17 with small metrics; 😀 has BearingY 101 and advance 136, matching HarfBuzz's 2550/2048 em. Its `.notdef` is empty. [font file: CBLC, CBDT, hmtx]
- **The Go Notos carry their family name in nameID 1 only.** Go Noto Current's family name is "Go Noto Current-Regular". Its `.notdef` is a plain rectangle. [font file: name table]
- **Six Go Notos cover all 70646 codepoints of the eight.** Current, CJKCore, Ancient, Europe Americas, East Asia and Asia Historical, in falling order of what each adds. Go Noto South Asia's 12491 codepoints all lie in Go Noto Current; Go Noto Africa Middle East has no codepoint the others lack. [font files: cmap; verified by test]
- **Overlapping Go Notos draw identical glyphs, with one exception.** Of 15594 codepoints compared across fonts, 15582 have identical outlines and advances. The Ideographic Description Characters U+2FF0–U+2FFB differ: Go Noto East Asia draws fewer, heavier dashes; Go Noto CJKCore draws fine dashes that match its ideographs. [font files: glyf, hmtx; verified by test]
- **Fira Code 6.2 ships Retina only as a static TTF.** In `Fira_Code_v6.2.zip`, only `ttf/FiraCode-Retina.ttf` exists; `woff/` and `woff2/` have none, and the variable font has no Retina instance while its nameID 1 reads "Fira Code Light". [release asset]
- **`FiraCode-Retina.ttf` is named "Fira Code Retina" in nameID 1.** nameID 16 is "Fira Code", nameID 17 "Retina", weight class 450; Regular and Bold share nameID 1 "Fira Code". License: OFL 1.1. [font file: name table, OS/2]
- **Fira Code's ligatures live in `calt`.** The font has no `liga` feature. [font file: GSUB]
- **Segoe UI Emoji 1.29 is COLRv0 with CPAL.** 12189 glyphs, nameID 1 "Segoe UI Emoji". [font file]
- **Segoe UI Emoji's license string permits use, not redistribution.** nameID 13 permits creating, displaying and printing content and says nothing about redistribution. [font file: name table]

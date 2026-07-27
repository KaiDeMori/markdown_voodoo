import argparse
import sys
from collections import Counter
from pathlib import Path

from fontTools.ttLib import TTFont

FONT_DIRECTORY = Path(__file__).parent / "fonts"
DEFAULT_FONT_NAME = "NotoColorEmoji.ttf"

# PNG files start with an 8-byte signature followed by the IHDR chunk:
# 4-byte length, 4-byte "IHDR" tag, then big-endian uint32 width and height.
PNG_IHDR_WIDTH_OFFSET = 16
PNG_IHDR_HEIGHT_OFFSET = 20


def read_png_dimensions(png_bytes):
    width = int.from_bytes(
        png_bytes[PNG_IHDR_WIDTH_OFFSET : PNG_IHDR_WIDTH_OFFSET + 4], "big"
    )
    height = int.from_bytes(
        png_bytes[PNG_IHDR_HEIGHT_OFFSET : PNG_IHDR_HEIGHT_OFFSET + 4], "big"
    )
    return width, height


def iter_glyph_png_dimensions(ttfont):
    for strike in ttfont["CBDT"].strikeData:
        for glyph_name, bitmap_glyph in strike.items():
            yield glyph_name, read_png_dimensions(bitmap_glyph.imageData)


def summarize_strike_ppem(ttfont):
    return sorted({strike.bitmapSizeTable.ppemY for strike in ttfont["CBLC"].strikes})


def main():
    parser = argparse.ArgumentParser(
        description="Report CBLC strike ppem sizes and the actual embedded PNG "
        "pixel dimensions of glyphs in a CBDT/CBLC color bitmap font."
    )
    parser.add_argument(
        "font_path",
        nargs="?",
        type=Path,
        default=FONT_DIRECTORY / DEFAULT_FONT_NAME,
    )
    arguments = parser.parse_args()

    ttfont = TTFont(arguments.font_path)

    print(f"strike ppem sizes: {summarize_strike_ppem(ttfont)}")

    dimension_counts = Counter(
        dimensions for _, dimensions in iter_glyph_png_dimensions(ttfont)
    )
    for (width, height), count in sorted(dimension_counts.items()):
        print(f"{width}x{height} px: {count} glyphs")


if __name__ == "__main__":
    sys.exit(main())

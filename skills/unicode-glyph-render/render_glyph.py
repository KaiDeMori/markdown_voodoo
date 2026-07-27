import argparse
import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

FONT_DIRECTORY = Path(__file__).parent / "fonts"
SURROGATE_RANGE = range(0xD800, 0xE000)
CANVAS_SIZE_PIXELS = 109


@dataclass(frozen=True)
class Font_spec:
    filename: str
    variation_instance_name: Optional[str] = None
    has_color: bool = False


# Ordered by specificity, not coverage size — Last Resort is last because it
# only ever draws a generic per-block placeholder, never the real glyph.
FALLBACK_FONTS = (
    Font_spec("NotoSans[wdth,wght].ttf", variation_instance_name="Regular"),
    Font_spec("NotoSansSymbols[wght].ttf", variation_instance_name="Regular"),
    Font_spec("NotoSansSymbols2-Regular.ttf"),
    Font_spec("NotoSansMath-Regular.ttf"),
    Font_spec("NotoSansCJK-Regular.ttc"),
    Font_spec("NotoColorEmoji.ttf", has_color=True),
    Font_spec("LastResort-Regular.ttf"),
)


def open_font(filename):
    path = FONT_DIRECTORY / filename
    if path.suffix.lower() == ".ttc":
        return TTFont(path, fontNumber=0)
    return TTFont(path)


@lru_cache(maxsize=None)
def load_cmap(filename):
    return open_font(filename).getBestCmap()


def pick_font_for_codepoint(codepoint):
    for spec in FALLBACK_FONTS:
        if codepoint in load_cmap(spec.filename):
            return spec
    return FALLBACK_FONTS[-1]


@lru_cache(maxsize=None)
def bitmap_strike_sizes(filename):
    ttfont = open_font(filename)
    if "CBLC" not in ttfont:
        return ()
    return tuple(sorted({strike.bitmapSizeTable.ppemY for strike in ttfont["CBLC"].strikes}))


def resolve_font_size(spec, requested_size):
    available_sizes = bitmap_strike_sizes(spec.filename)
    if not available_sizes:
        return requested_size
    return min(available_sizes, key=lambda size: abs(size - requested_size))


def render_codepoint(codepoint):
    spec = pick_font_for_codepoint(codepoint)
    character = chr(codepoint)

    font_size = resolve_font_size(spec, round(CANVAS_SIZE_PIXELS * 0.78))
    font = ImageFont.truetype(
        str(FONT_DIRECTORY / spec.filename), size=font_size, index=0
    )
    if spec.variation_instance_name is not None:
        font.set_variation_by_name(spec.variation_instance_name)

    measuring_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    left, top, right, bottom = measuring_draw.textbbox(
        (0, 0), character, font=font, embedded_color=spec.has_color
    )

    # A fixed-size bitmap glyph (e.g. color emoji) can be larger than the
    # canvas — render at whatever size actually fits, then resize.
    working_size = max(CANVAS_SIZE_PIXELS, right - left, bottom - top)
    image = Image.new("RGB", (working_size, working_size), "white")
    draw = ImageDraw.Draw(image)
    horizontal_offset = (working_size - (right - left)) / 2 - left
    vertical_offset = (working_size - (bottom - top)) / 2 - top
    draw.text(
        (horizontal_offset, vertical_offset),
        character,
        font=font,
        fill=(0, 0, 0),
        embedded_color=spec.has_color,
    )

    if working_size != CANVAS_SIZE_PIXELS:
        image = image.resize((CANVAS_SIZE_PIXELS, CANVAS_SIZE_PIXELS), Image.LANCZOS)
    return image, spec


def parse_codepoint_argument(argument):
    if argument.lower().startswith("u+"):
        codepoint = int(argument[2:], 16)
    elif len(argument) == 1:
        codepoint = ord(argument)
    else:
        raise ValueError(
            f"'{argument}' is ambiguous — pass a single character or U+<HEX>"
        )

    if codepoint > 0x10FFFF or codepoint in SURROGATE_RANGE:
        raise ValueError(f"'{argument}' is not a valid Unicode scalar value")
    return codepoint


def format_codepoint_label(codepoint):
    return f"U+{codepoint:04X}"


def main():
    parser = argparse.ArgumentParser(
        description="Render Unicode codepoints to small PNG images for visual inspection."
    )
    parser.add_argument(
        "codepoints", nargs="+", help="e.g. U+1F600, or a single literal character"
    )
    parser.add_argument("--out-dir", required=True, type=Path)
    arguments = parser.parse_args()

    arguments.out_dir.mkdir(parents=True, exist_ok=True)

    images = []
    errors = []
    for argument in arguments.codepoints:
        try:
            codepoint = parse_codepoint_argument(argument)
            image, spec = render_codepoint(codepoint)
            label = format_codepoint_label(codepoint)
            output_path = arguments.out_dir / f"{label}.png"
            image.save(output_path)
            images.append(
                {"codepoint": label, "font": spec.filename, "path": str(output_path)}
            )
            print(f"{label} -> {spec.filename}", file=sys.stderr)
        except Exception as error:
            errors.append({"argument": argument, "error": str(error)})
            print(f"{argument}: {error}", file=sys.stderr)

    print(json.dumps({"images": images, "errors": errors}))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

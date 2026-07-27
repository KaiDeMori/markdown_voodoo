import argparse
import io
import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

FONT_DIRECTORY = Path(__file__).parent / "fonts"
FONT_FILE_EXTENSIONS = (".ttf", ".otf", ".ttc")
COLOR_TABLE_TAGS = ("CBDT", "COLR", "SVG ")
SURROGATE_RANGE = range(0xD800, 0xE000)
CANVAS_SIZE_PIXELS = 109

LAST_RESORT_FONT_STEM = "lastresort-regular"


@dataclass(frozen=True)
class Font_spec:
    path: Path
    variation_instance_name: Optional[str] = None
    has_color: bool = False
    has_bitmap: bool = False


def open_font(path):
    if path.suffix.lower() == ".ttc":
        return TTFont(path, fontNumber=0)
    return TTFont(path)


def find_regular_variation_instance_name(ttfont):
    if "fvar" not in ttfont:
        return None
    instances = ttfont["fvar"].instances
    if not instances:
        return None
    name_table = ttfont["name"]
    instance_names = [
        name_table.getDebugName(instance.subfamilyNameID) for instance in instances
    ]
    for instance_name in instance_names:
        if instance_name and instance_name.lower() == "regular":
            return instance_name
    return instance_names[0]


def has_color_glyphs(ttfont):
    return any(tag in ttfont for tag in COLOR_TABLE_TAGS)


def has_bitmap_glyphs(ttfont):
    return "CBDT" in ttfont


@lru_cache(maxsize=None)
def load_font_specs():
    specs = []
    for path in sorted(FONT_DIRECTORY.iterdir()):
        if path.suffix.lower() not in FONT_FILE_EXTENSIONS:
            continue
        ttfont = open_font(path)
        specs.append(
            Font_spec(
                path=path,
                variation_instance_name=find_regular_variation_instance_name(ttfont),
                has_color=has_color_glyphs(ttfont),
                has_bitmap=has_bitmap_glyphs(ttfont),
            )
        )
    if not specs:
        raise RuntimeError(f"no fonts found in {FONT_DIRECTORY}")
    return tuple(specs)


@lru_cache(maxsize=None)
def load_cmap(path):
    return open_font(path).getBestCmap()


def pick_font_for_codepoint(codepoint):
    fallback_spec = None
    for spec in load_font_specs():
        if spec.path.stem.lower() == LAST_RESORT_FONT_STEM:
            fallback_spec = spec
            continue
        if codepoint in load_cmap(spec.path):
            return spec
    if fallback_spec is not None:
        return fallback_spec
    raise RuntimeError(
        f"no installed font covers U+{codepoint:04X} and no "
        f"{LAST_RESORT_FONT_STEM} fallback is present in {FONT_DIRECTORY}"
    )


@lru_cache(maxsize=None)
def bitmap_strike_ppems(path):
    return tuple(
        strike.bitmapSizeTable.ppemY for strike in open_font(path)["CBLC"].strikes
    )


def resolve_bitmap_strike_index(path, requested_size):
    ppems = bitmap_strike_ppems(path)
    return min(range(len(ppems)), key=lambda index: abs(ppems[index] - requested_size))


@lru_cache(maxsize=None)
def load_cbdt_strikes(path):
    return open_font(path)["CBDT"].strikeData


def load_bitmap_glyph_image(spec, codepoint):
    glyph_name = load_cmap(spec.path)[codepoint]
    strike_index = resolve_bitmap_strike_index(spec.path, CANVAS_SIZE_PIXELS)
    png_bytes = load_cbdt_strikes(spec.path)[strike_index][glyph_name].imageData
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def render_codepoint(codepoint):
    spec = pick_font_for_codepoint(codepoint)
    if spec.has_bitmap:
        image = render_bitmap_codepoint(spec, codepoint)
    else:
        image = render_vector_codepoint(spec, codepoint)
    return image, spec


def render_bitmap_codepoint(spec, codepoint):
    glyph_image = load_bitmap_glyph_image(spec, codepoint)
    working_size = max(CANVAS_SIZE_PIXELS, glyph_image.width, glyph_image.height)
    image = Image.new("RGB", (working_size, working_size), "white")
    offset = (
        (working_size - glyph_image.width) // 2,
        (working_size - glyph_image.height) // 2,
    )
    image.paste(glyph_image, offset, glyph_image)
    return image


def render_vector_codepoint(spec, codepoint):
    character = chr(codepoint)
    font = ImageFont.truetype(str(spec.path), size=CANVAS_SIZE_PIXELS, index=0)
    if spec.variation_instance_name is not None:
        font.set_variation_by_name(spec.variation_instance_name)

    measuring_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    left, top, right, bottom = measuring_draw.textbbox(
        (0, 0), character, font=font, embedded_color=spec.has_color
    )

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

    return image


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
                {"codepoint": label, "font": spec.path.name, "path": str(output_path)}
            )
            print(f"{label} -> {spec.path.name}", file=sys.stderr)
        except Exception as error:
            errors.append({"argument": argument, "error": str(error)})
            print(f"{argument}: {error}", file=sys.stderr)

    print(json.dumps({"images": images, "errors": errors}))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

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
def bitmap_strike_sizes(path):
    ttfont = open_font(path)
    if "CBLC" not in ttfont:
        return ()
    return tuple(sorted({strike.bitmapSizeTable.ppemY for strike in ttfont["CBLC"].strikes}))


def resolve_font_size(spec, requested_size):
    available_sizes = bitmap_strike_sizes(spec.path)
    if not available_sizes:
        return requested_size
    return min(available_sizes, key=lambda size: abs(size - requested_size))


def render_codepoint(codepoint):
    spec = pick_font_for_codepoint(codepoint)
    character = chr(codepoint)

    font_size = resolve_font_size(spec, CANVAS_SIZE_PIXELS)
    font = ImageFont.truetype(str(spec.path), size=font_size, index=0)
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

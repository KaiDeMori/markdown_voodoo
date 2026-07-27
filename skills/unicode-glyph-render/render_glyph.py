import argparse
import io
import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import freetype
import uharfbuzz as harfbuzz
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
    canvas_width = max(CANVAS_SIZE_PIXELS, glyph_image.width)
    canvas_height = max(CANVAS_SIZE_PIXELS, glyph_image.height)
    image = Image.new("RGB", (canvas_width, canvas_height), "white")
    offset = (
        (canvas_width - glyph_image.width) // 2,
        (canvas_height - glyph_image.height) // 2,
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


@lru_cache(maxsize=None)
def load_hb_font(path):
    with open(path, "rb") as file:
        face = harfbuzz.Face(file.read())
    font = harfbuzz.Font(face)
    font.scale = (face.upem, face.upem)
    harfbuzz.ot_font_set_funcs(font)
    return font, face.upem


@lru_cache(maxsize=None)
def load_freetype_face(path):
    return freetype.Face(str(path))


def split_into_font_runs(text):
    runs = []
    current_spec = None
    current_characters = []
    for character in text:
        spec = pick_font_for_codepoint(ord(character))
        if spec != current_spec and current_characters:
            runs.append((current_spec, "".join(current_characters)))
            current_characters = []
        current_spec = spec
        current_characters.append(character)
    if current_characters:
        runs.append((current_spec, "".join(current_characters)))
    return runs


def shape_run(spec, text, pixel_size):
    hb_font, units_per_em = load_hb_font(spec.path)
    scale = pixel_size / units_per_em
    buffer = harfbuzz.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    harfbuzz.shape(hb_font, buffer)
    return [
        (
            info.codepoint,
            position.x_advance * scale,
            position.y_advance * scale,
            position.x_offset * scale,
            position.y_offset * scale,
        )
        for info, position in zip(buffer.glyph_infos, buffer.glyph_positions)
    ]


def convert_bitmap_to_image(bitmap):
    buffer = bytes(bitmap.buffer)
    if bitmap.pixel_mode == freetype.FT_PIXEL_MODE_BGRA:
        return Image.frombytes(
            "RGBA", (bitmap.width, bitmap.rows), buffer, "raw", ("BGRA", bitmap.pitch, 1)
        )
    return Image.frombytes(
        "L", (bitmap.width, bitmap.rows), buffer, "raw", ("L", bitmap.pitch, 1)
    )


def rasterize_glyph(spec, glyph_index, pixel_size):
    face = load_freetype_face(spec.path)
    face.set_pixel_sizes(0, pixel_size)
    face.load_glyph(glyph_index, freetype.FT_LOAD_COLOR | freetype.FT_LOAD_RENDER)
    bitmap = face.glyph.bitmap
    if bitmap.width == 0 or bitmap.rows == 0:
        return None, 0, 0
    return convert_bitmap_to_image(bitmap), face.glyph.bitmap_left, face.glyph.bitmap_top


def render_string(text):
    pixel_size = CANVAS_SIZE_PIXELS
    shaped_runs = [
        (spec, shape_run(spec, run_text, pixel_size))
        for spec, run_text in split_into_font_runs(text)
    ]

    ascenders = []
    descenders = []
    for spec, _ in shaped_runs:
        face = load_freetype_face(spec.path)
        face.set_pixel_sizes(0, pixel_size)
        ascenders.append(face.size.ascender / 64)
        descenders.append(face.size.descender / 64)
    max_ascender = max(ascenders, default=pixel_size)
    min_descender = min(descenders, default=0)

    total_advance = sum(glyph[1] for _, glyphs in shaped_runs for glyph in glyphs)

    margin = pixel_size // 8
    canvas_width = max(pixel_size, round(total_advance)) + margin * 2
    canvas_height = round(max_ascender - min_descender) + margin * 2
    image = Image.new("RGB", (canvas_width, canvas_height), "white")

    pen_x = float(margin)
    baseline_y = margin + max_ascender

    for spec, glyphs in shaped_runs:
        for glyph_index, x_advance, y_advance, x_offset, y_offset in glyphs:
            glyph_image, bitmap_left, bitmap_top = rasterize_glyph(spec, glyph_index, pixel_size)
            if glyph_image is not None:
                draw_x = round(pen_x + x_offset + bitmap_left)
                draw_y = round(baseline_y - y_offset - bitmap_top)
                if glyph_image.mode == "RGBA":
                    image.paste(glyph_image, (draw_x, draw_y), glyph_image)
                else:
                    black_fill = Image.new("RGB", glyph_image.size, (0, 0, 0))
                    image.paste(black_fill, (draw_x, draw_y), glyph_image)
            pen_x += x_advance
            baseline_y -= y_advance

    return image, [spec for spec, _ in shaped_runs]


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

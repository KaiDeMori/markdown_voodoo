import argparse
import io
import json
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

import freetype
import regex
import uharfbuzz as harfbuzz
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

FONT_DIRECTORY = Path(__file__).parent / "fonts"
BYOF_DIRECTORY_NAME = "BYOF"
COLOR_TABLE_TAGS = ("CBDT", "COLR", "SVG ", "sbix")
SURROGATE_RANGE = range(0xD800, 0xE000)
DEFAULT_SINGLE_GLYPH_SIZE = 256
DEFAULT_STRING_GLYPH_SIZE = 109

FONT_CATALOG = {
    "Go Noto Current-Regular": "GoNotoCurrent-Regular.ttf",
    "Go Noto Europe Americas": "GoNotoEuropeAmericas.ttf",
    "Go Noto Africa Middle East": "GoNotoAfricaMiddleEast.ttf",
    "Go Noto South Asia": "GoNotoSouthAsia.ttf",
    "Go Noto East Asia": "GoNotoEastAsia.ttf",
    "Go Noto CJKCore": "GoNotoCJKCore.ttf",
    "Go Noto Asia Historical": "GoNotoAsiaHistorical.ttf",
    "Go Noto Ancient": "GoNotoAncient.ttf",
    "Noto Color Emoji": "NotoColorEmoji.ttf",
    "Last Resort": "LastResort-Regular.ttf",
    "Fira Code Retina": "FiraCode-Retina.ttf",
    "Segoe UI Emoji": "BYOF/seguiemj.ttf",
}

DEFAULT_STACK = (
    "Go Noto Current-Regular",
    "Go Noto Europe Americas",
    "Go Noto Africa Middle East",
    "Go Noto South Asia",
    "Go Noto East Asia",
    "Go Noto CJKCore",
    "Go Noto Asia Historical",
    "Go Noto Ancient",
    "Noto Color Emoji",
)

LAST_RESORT_FAMILY = "Last Resort"

TEXT_PRESENTATION_SELECTOR = "︎"
EMOJI_PRESENTATION_SELECTOR = "️"
GRAPHEME_CLUSTER_PATTERN = regex.compile(r"\X")
EMOJI_PRESENTATION_PATTERN = regex.compile(r"\p{Emoji_Presentation}")
EMOJI_SEQUENCE_COMPONENT_PATTERN = regex.compile(
    r"[\p{Emoji_Modifier}\p{Regional_Indicator}\U000E0020-\U000E007F]"
)


@dataclass(frozen=True)
class Font_spec:
    family_name: str
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


def describe_missing_font_file(family_name, relative_path):
    if Path(relative_path).parts[0] == BYOF_DIRECTORY_NAME:
        return (
            f"'{family_name}' is a BYOF font: put {Path(relative_path).name} "
            f"into {FONT_DIRECTORY / BYOF_DIRECTORY_NAME}"
        )
    return (
        f"'{family_name}' needs {FONT_DIRECTORY / relative_path}; "
        f"font_installer.py downloads it"
    )


@lru_cache(maxsize=None)
def load_font_spec(family_name):
    if family_name not in FONT_CATALOG:
        raise ValueError(
            f"unknown family name '{family_name}'; "
            f"available: {', '.join(FONT_CATALOG)}"
        )
    path = FONT_DIRECTORY / FONT_CATALOG[family_name]
    if not path.exists():
        raise FileNotFoundError(
            describe_missing_font_file(family_name, FONT_CATALOG[family_name])
        )
    ttfont = open_font(path)
    return Font_spec(
        family_name=family_name,
        path=path,
        variation_instance_name=find_regular_variation_instance_name(ttfont),
        has_color=has_color_glyphs(ttfont),
        has_bitmap=has_bitmap_glyphs(ttfont),
    )


def font_file_is_present(family_name):
    return (FONT_DIRECTORY / FONT_CATALOG[family_name]).exists()


def font_kind(spec):
    return "emoji" if spec.has_color else "text"


def parse_font_stack(argument):
    family_names = tuple(name.strip() for name in argument.split(","))
    if "" in family_names:
        raise ValueError(f"--font-stack '{argument}' contains an empty family name")
    for family_name in family_names:
        load_font_spec(family_name)
    return family_names


@lru_cache(maxsize=None)
def load_cmap(path):
    return open_font(path).getBestCmap()


def pick_font_for_codepoint(codepoint, font_stack=DEFAULT_STACK):
    for family_name in dict.fromkeys(font_stack + DEFAULT_STACK):
        spec = load_font_spec(family_name)
        if codepoint in load_cmap(spec.path):
            return spec
    return load_font_spec(LAST_RESORT_FAMILY)


def split_into_grapheme_clusters(text):
    return GRAPHEME_CLUSTER_PATTERN.findall(text)


def determine_presentation(cluster):
    if EMOJI_PRESENTATION_SELECTOR in cluster:
        return "emoji"
    if TEXT_PRESENTATION_SELECTOR in cluster:
        return "text"
    if EMOJI_SEQUENCE_COMPONENT_PATTERN.search(cluster):
        return "emoji"
    if EMOJI_PRESENTATION_PATTERN.match(cluster):
        return "emoji"
    return "text"


@lru_cache(maxsize=None)
def font_covers_cluster(family_name, cluster):
    hb_font, _ = load_hb_font(load_font_spec(family_name).path)
    buffer = harfbuzz.Buffer()
    buffer.add_str(cluster)
    buffer.guess_segment_properties()
    harfbuzz.shape(hb_font, buffer)
    return all(info.codepoint != 0 for info in buffer.glyph_infos)


def pick_family_for_cluster(cluster, font_stack):
    covering_families = [
        family_name
        for family_name in font_stack
        if font_covers_cluster(family_name, cluster)
    ]
    presentation = determine_presentation(cluster)
    for family_name in covering_families:
        if font_kind(load_font_spec(family_name)) == presentation:
            return family_name
    return covering_families[0] if covering_families else None


def select_family_for_cluster(cluster, font_stack):
    family_name = pick_family_for_cluster(cluster, font_stack)
    if family_name is not None or font_stack == DEFAULT_STACK:
        return family_name, False
    family_name = pick_family_for_cluster(cluster, DEFAULT_STACK)
    return family_name, family_name is not None


def describe_cluster_coverage(cluster, font_stack):
    family_name, fallback = select_family_for_cluster(cluster, font_stack)
    description = {
        "text": cluster,
        "codepoints": [format_codepoint_label(ord(character)) for character in cluster],
        "presentation": determine_presentation(cluster),
        "covering_families": [
            covering_family_name
            for covering_family_name in FONT_CATALOG
            if covering_family_name != LAST_RESORT_FAMILY
            and font_file_is_present(covering_family_name)
            and font_covers_cluster(covering_family_name, cluster)
        ],
        "font": family_name,
        "fallback": fallback,
    }
    if family_name is None:
        description["codepoint_fonts"] = [
            pick_font_for_codepoint(ord(character), font_stack).family_name
            for character in cluster
        ]
    return description


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
    strike_index = resolve_bitmap_strike_index(spec.path, DEFAULT_SINGLE_GLYPH_SIZE)
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
    image = Image.new("RGB", glyph_image.size, "white")
    image.paste(glyph_image, (0, 0), glyph_image)
    return image


def render_vector_codepoint(spec, codepoint):
    character = chr(codepoint)
    font = ImageFont.truetype(str(spec.path), size=DEFAULT_SINGLE_GLYPH_SIZE, index=0)
    if spec.variation_instance_name is not None:
        font.set_variation_by_name(spec.variation_instance_name)

    measuring_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    left, top, right, bottom = measuring_draw.textbbox(
        (0, 0), character, font=font, embedded_color=spec.has_color
    )

    working_size = max(DEFAULT_SINGLE_GLYPH_SIZE, right - left, bottom - top)
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
    pixel_size = DEFAULT_STRING_GLYPH_SIZE
    shaped_runs = [
        (spec, shape_run(spec, run_text, pixel_size))
        for spec, run_text in split_into_font_runs(text)
    ]

    placements = []
    pen_x = 0.0
    pen_y = 0.0
    for spec, glyphs in shaped_runs:
        for glyph_index, x_advance, y_advance, x_offset, y_offset in glyphs:
            glyph_image, bitmap_left, bitmap_top = rasterize_glyph(spec, glyph_index, pixel_size)
            if glyph_image is not None:
                origin_x = pen_x + x_offset + bitmap_left
                origin_y = pen_y - y_offset - bitmap_top
                placements.append((glyph_image, origin_x, origin_y))
            pen_x += x_advance
            pen_y -= y_advance

    margin = pixel_size // 8
    if placements:
        ink_left = min(origin_x for _, origin_x, _ in placements)
        ink_top = min(origin_y for _, _, origin_y in placements)
        ink_right = max(origin_x + glyph_image.width for glyph_image, origin_x, _ in placements)
        ink_bottom = max(origin_y + glyph_image.height for glyph_image, _, origin_y in placements)
    else:
        ink_left = ink_top = 0.0
        ink_right = ink_bottom = 0.0

    canvas_width = max(pixel_size, round(ink_right - ink_left)) + margin * 2
    canvas_height = max(pixel_size, round(ink_bottom - ink_top)) + margin * 2
    image = Image.new("RGB", (canvas_width, canvas_height), "white")

    shift_x = margin - ink_left
    shift_y = margin - ink_top
    for glyph_image, origin_x, origin_y in placements:
        draw_x = round(origin_x + shift_x)
        draw_y = round(origin_y + shift_y)
        if glyph_image.mode == "RGBA":
            image.paste(glyph_image, (draw_x, draw_y), glyph_image)
        else:
            black_fill = Image.new("RGB", glyph_image.size, (0, 0, 0))
            image.paste(black_fill, (draw_x, draw_y), glyph_image)

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


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Render Unicode text to a small PNG image for visual inspection."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    glyph_parser = subparsers.add_parser("glyph", help="render a single codepoint")
    glyph_parser.add_argument(
        "codepoint", help="e.g. U+1F600, or a single literal character"
    )
    glyph_parser.add_argument(
        "--output-file",
        required=True,
        type=Path,
        help="absolute path of the PNG file to write",
    )

    string_parser = subparsers.add_parser("string", help="render a shaped run of text")
    string_parser.add_argument("text", help="the text to render")
    string_parser.add_argument(
        "--output-file",
        required=True,
        type=Path,
        help="absolute path of the PNG file to write",
    )

    subparsers.add_parser("fonts", help="list the fonts of the font catalog")

    coverage_parser = subparsers.add_parser(
        "coverage", help="report which fonts cover each grapheme cluster"
    )
    coverage_parser.add_argument("text", help="the text to analyze")
    coverage_parser.add_argument(
        "--font-stack", help="family names separated by commas"
    )

    return parser


def require_absolute_output_file(output_file):
    if not output_file.is_absolute():
        raise ValueError(
            f"--output-file must be an absolute path, got '{output_file}'"
        )
    output_file.parent.mkdir(parents=True, exist_ok=True)


def run_glyph_command(arguments):
    require_absolute_output_file(arguments.output_file)
    codepoint = parse_codepoint_argument(arguments.codepoint)
    image, spec = render_codepoint(codepoint)
    label = format_codepoint_label(codepoint)
    image.save(arguments.output_file)
    print(f"{label} -> {spec.family_name}", file=sys.stderr)
    return {"codepoint": label, "fonts": [spec.family_name], "path": str(arguments.output_file)}


def run_string_command(arguments):
    require_absolute_output_file(arguments.output_file)
    image, specs = render_string(arguments.text)
    font_names = [spec.family_name for spec in specs]
    image.save(arguments.output_file)
    print(f"{arguments.text} -> {', '.join(font_names)}", file=sys.stderr)
    return {"text": arguments.text, "fonts": font_names, "path": str(arguments.output_file)}


def describe_font(family_name):
    relative_path = FONT_CATALOG[family_name]
    description = {
        "family": family_name,
        "file": relative_path,
        "present": font_file_is_present(family_name),
        "in_default_stack": family_name in DEFAULT_STACK,
        "kind": None,
    }
    if description["present"]:
        description["kind"] = font_kind(load_font_spec(family_name))
    return description


def run_fonts_command(arguments):
    return {"fonts": [describe_font(family_name) for family_name in FONT_CATALOG]}


def run_coverage_command(arguments):
    font_stack = DEFAULT_STACK
    if arguments.font_stack is not None:
        font_stack = parse_font_stack(arguments.font_stack)
    return {
        "text": arguments.text,
        "font_stack": list(font_stack),
        "clusters": [
            describe_cluster_coverage(cluster, font_stack)
            for cluster in split_into_grapheme_clusters(arguments.text)
        ],
    }


def describe_command_argument(arguments):
    if arguments.command == "glyph":
        return arguments.codepoint
    if arguments.command in ("string", "coverage"):
        return arguments.text
    return arguments.command


def main():
    arguments = build_argument_parser().parse_args()
    command_argument = describe_command_argument(arguments)
    command_runners = {
        "glyph": run_glyph_command,
        "string": run_string_command,
        "fonts": run_fonts_command,
        "coverage": run_coverage_command,
    }

    try:
        result = command_runners[arguments.command](arguments)
        print(json.dumps(result))
        return 0
    except Exception as error:
        print(f"{command_argument}: {error}", file=sys.stderr)
        print(json.dumps({"argument": command_argument, "error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())

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
from PIL import Image, ImageDraw

FONT_DIRECTORY = Path(__file__).parent / "fonts"
BYOF_DIRECTORY_NAME = "BYOF"
COLOR_TABLE_TAGS = ("CBDT", "COLR", "SVG ", "sbix")
SURROGATE_RANGE = range(0xD800, 0xE000)
DEFAULT_SINGLE_GLYPH_SIZE = 256
DEFAULT_STRING_GLYPH_SIZE = 109

GAP_WIDTH_PER_EM = 0.6
GAP_HEIGHT_PER_EM = 0.8
GAP_CELLS_PER_EM = 8
GAP_MAGENTA = (255, 0, 255, 255)
GAP_BLACK = (0, 0, 0, 255)

FONT_CATALOG = {
    "Go Noto Current-Regular": "GoNotoCurrent-Regular.ttf",
    "Go Noto Europe Americas": "GoNotoEuropeAmericas.ttf",
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
    "Go Noto CJKCore",
    "Go Noto Ancient",
    "Go Noto Europe Americas",
    "Go Noto East Asia",
    "Go Noto Asia Historical",
    "Noto Color Emoji",
)

LAST_RESORT_FAMILY = "Last Resort"

TEXT_PRESENTATION_SELECTOR = "\U0000FE0E"
EMOJI_PRESENTATION_SELECTOR = "\U0000FE0F"
GRAPHEME_CLUSTER_PATTERN = regex.compile(r"\X")
INVISIBLE_CLUSTER_PATTERN = regex.compile(r"\p{Default_Ignorable_Code_Point}+")
EMOJI_PRESENTATION_PATTERN = regex.compile(r"\p{Emoji_Presentation}")
EMOJI_SEQUENCE_COMPONENT_PATTERN = regex.compile(
    r"[\p{Emoji_Modifier}\p{Regional_Indicator}\U000E0020-\U000E007F]"
)
CODEPOINT_SEQUENCE_PATTERN = regex.compile(
    r"[uU]\+[0-9a-fA-F]{1,6}(?:\s+[uU]\+[0-9a-fA-F]{1,6})*"
)
LINE_BREAK_PATTERN = regex.compile(r"\r\n|[\n\v\f\r\x85\U00002028\U00002029]")
LINE_HEIGHT_PER_EM = 1.25


@dataclass(frozen=True)
class Font_spec:
    family_name: str
    path: Path
    has_color: bool = False
    has_bitmap: bool = False


@dataclass(frozen=True)
class Cluster_assignment:
    cluster: str
    family_name: Optional[str]
    codepoint_families: tuple = ()
    fallback: bool = False
    is_gap: bool = False
    is_invisible: bool = False
    is_line_break: bool = False


class Argument_error(ValueError):
    def __init__(self, argument, value, message):
        super().__init__(message)
        self.argument = argument
        self.value = value


def open_font(path):
    if path.suffix.lower() == ".ttc":
        return TTFont(path, fontNumber=0)
    return TTFont(path)


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
        raise Argument_error(
            "--font-stack", argument, f"--font-stack '{argument}' contains an empty family name"
        )
    for family_name in family_names:
        try:
            load_font_spec(family_name)
        except (ValueError, FileNotFoundError) as error:
            raise Argument_error("--font-stack", argument, str(error)) from error
    return family_names


def resolve_font_stack(argument):
    if argument is None:
        return DEFAULT_STACK
    return parse_font_stack(argument)


@lru_cache(maxsize=None)
def load_cmap(path):
    return open_font(path).getBestCmap()


@lru_cache(maxsize=None)
def load_glyph_order(path):
    return open_font(path).getGlyphOrder()


def pick_font_for_codepoint(codepoint, font_stack=DEFAULT_STACK):
    for family_name in dict.fromkeys(font_stack + DEFAULT_STACK):
        spec = load_font_spec(family_name)
        if codepoint in load_cmap(spec.path):
            return spec
    return load_font_spec(LAST_RESORT_FAMILY)


def split_into_grapheme_clusters(text):
    return GRAPHEME_CLUSTER_PATTERN.findall(text)


def is_invisible_cluster(cluster):
    return INVISIBLE_CLUSTER_PATTERN.fullmatch(cluster) is not None


def is_line_break_cluster(cluster):
    return LINE_BREAK_PATTERN.fullmatch(cluster) is not None


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
def load_hb_font(path):
    with open(path, "rb") as file:
        face = harfbuzz.Face(file.read())
    font = harfbuzz.Font(face)
    font.scale = (face.upem, face.upem)
    harfbuzz.ot_font_set_funcs(font)
    return font, face.upem


@lru_cache(maxsize=None)
def font_covers_cluster(family_name, cluster):
    hb_font, _ = load_hb_font(load_font_spec(family_name).path)
    buffer = harfbuzz.Buffer()
    buffer.add_str(cluster)
    buffer.guess_segment_properties()
    harfbuzz.shape(hb_font, buffer)
    return all(info.codepoint != 0 for info in buffer.glyph_infos)


def list_covering_families(cluster):
    return [
        family_name
        for family_name in FONT_CATALOG
        if family_name != LAST_RESORT_FAMILY
        and font_file_is_present(family_name)
        and font_covers_cluster(family_name, cluster)
    ]


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


def assign_cluster(cluster, font_stack, strict):
    if is_line_break_cluster(cluster):
        return Cluster_assignment(cluster, None, is_line_break=True)
    if is_invisible_cluster(cluster):
        return Cluster_assignment(cluster, None, is_invisible=True)
    if strict:
        family_name = pick_family_for_cluster(cluster, font_stack)
        return Cluster_assignment(cluster, family_name, is_gap=family_name is None)
    family_name, fallback = select_family_for_cluster(cluster, font_stack)
    if family_name is not None:
        return Cluster_assignment(cluster, family_name, fallback=fallback)
    codepoint_families = tuple(
        pick_font_for_codepoint(ord(character), font_stack).family_name
        for character in cluster
    )
    return Cluster_assignment(
        cluster,
        None,
        codepoint_families=codepoint_families,
        fallback=any(
            codepoint_family not in font_stack for codepoint_family in codepoint_families
        ),
    )


def split_into_runs(assignments):
    runs = []
    for assignment in assignments:
        if assignment.is_invisible:
            continue
        if assignment.is_gap:
            runs.append((None, assignment.cluster))
            continue
        if assignment.family_name is not None:
            pieces = [(assignment.family_name, assignment.cluster)]
        else:
            pieces = list(zip(assignment.codepoint_families, assignment.cluster))
        for family_name, text in pieces:
            if runs and runs[-1][0] == family_name:
                runs[-1] = (family_name, runs[-1][1] + text)
            else:
                runs.append((family_name, text))
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


@lru_cache(maxsize=None)
def load_freetype_face(path):
    return freetype.Face(str(path))


def rasterize_bitmap_glyph(spec, glyph_index, pixel_size):
    strike_index = resolve_bitmap_strike_index(spec.path, pixel_size)
    strike = load_cbdt_strikes(spec.path)[strike_index]
    glyph_name = load_glyph_order(spec.path)[glyph_index]
    if glyph_name not in strike:
        return None, 0, 0
    bitmap_glyph = strike[glyph_name]
    scale = pixel_size / bitmap_strike_ppems(spec.path)[strike_index]
    image = Image.open(io.BytesIO(bitmap_glyph.imageData)).convert("RGBA")
    if scale != 1:
        scaled_size = (
            max(1, round(image.width * scale)),
            max(1, round(image.height * scale)),
        )
        image = image.resize(scaled_size, Image.LANCZOS)
    metrics = bitmap_glyph.metrics
    return image, metrics.BearingX * scale, metrics.BearingY * scale


def convert_bitmap_to_image(bitmap):
    buffer = bytes(bitmap.buffer)
    if bitmap.pixel_mode == freetype.FT_PIXEL_MODE_BGRA:
        return Image.frombytes(
            "RGBA", (bitmap.width, bitmap.rows), buffer, "raw", ("BGRa", bitmap.pitch, 1)
        )
    return Image.frombytes(
        "L", (bitmap.width, bitmap.rows), buffer, "raw", ("L", bitmap.pitch, 1)
    )


def rasterize_glyph(spec, glyph_index, pixel_size):
    if spec.has_bitmap:
        return rasterize_bitmap_glyph(spec, glyph_index, pixel_size)
    face = load_freetype_face(spec.path)
    face.set_pixel_sizes(0, pixel_size)
    face.load_glyph(glyph_index, freetype.FT_LOAD_COLOR | freetype.FT_LOAD_RENDER)
    bitmap = face.glyph.bitmap
    if bitmap.width == 0 or bitmap.rows == 0:
        return None, 0, 0
    return convert_bitmap_to_image(bitmap), face.glyph.bitmap_left, face.glyph.bitmap_top


def draw_gap_image(pixel_size):
    width = round(pixel_size * GAP_WIDTH_PER_EM)
    height = round(pixel_size * GAP_HEIGHT_PER_EM)
    cell_size = max(2, pixel_size // GAP_CELLS_PER_EM)
    image = Image.new("RGBA", (width, height), GAP_BLACK)
    draw = ImageDraw.Draw(image)
    for top in range(0, height, cell_size):
        for left in range(0, width, cell_size):
            if (top // cell_size + left // cell_size) % 2 == 0:
                draw.rectangle(
                    [left, top, left + cell_size - 1, top + cell_size - 1], fill=GAP_MAGENTA
                )
    return image


def split_into_lines(assignments):
    lines = [[]]
    for assignment in assignments:
        if assignment.is_line_break:
            lines.append([])
        else:
            lines[-1].append(assignment)
    return lines


def lay_out_lines(assignments, pixel_size):
    placements = []
    line_height = pixel_size * LINE_HEIGHT_PER_EM
    for line_index, line_assignments in enumerate(split_into_lines(assignments)):
        placements.extend(
            lay_out_runs(split_into_runs(line_assignments), pixel_size, line_index * line_height)
        )
    return placements


def lay_out_runs(runs, pixel_size, baseline_y=0.0):
    placements = []
    pen_x = 0.0
    pen_y = baseline_y
    for family_name, run_text in runs:
        if family_name is None:
            gap_image = draw_gap_image(pixel_size)
            placements.append((gap_image, pen_x, pen_y - gap_image.height))
            pen_x += gap_image.width
            continue
        spec = load_font_spec(family_name)
        for glyph_index, x_advance, y_advance, x_offset, y_offset in shape_run(
            spec, run_text, pixel_size
        ):
            glyph_image, bitmap_left, bitmap_top = rasterize_glyph(spec, glyph_index, pixel_size)
            if glyph_image is not None:
                origin_x = pen_x + x_offset + bitmap_left
                origin_y = pen_y - y_offset - bitmap_top
                placements.append((glyph_image, origin_x, origin_y))
            pen_x += x_advance
            pen_y -= y_advance
    return placements


def measure_ink(placements):
    if not placements:
        return 0.0, 0.0, 0.0, 0.0
    ink_left = min(origin_x for _, origin_x, _ in placements)
    ink_top = min(origin_y for _, _, origin_y in placements)
    ink_right = max(origin_x + glyph_image.width for glyph_image, origin_x, _ in placements)
    ink_bottom = max(origin_y + glyph_image.height for glyph_image, _, origin_y in placements)
    return ink_left, ink_top, ink_right, ink_bottom


def compose_image(placements, canvas_size, shift_x, shift_y):
    image = Image.new("RGB", canvas_size, "white")
    for glyph_image, origin_x, origin_y in placements:
        position = (round(origin_x + shift_x), round(origin_y + shift_y))
        if glyph_image.mode == "RGBA":
            image.paste(glyph_image, position, glyph_image)
        else:
            black_fill = Image.new("RGB", glyph_image.size, (0, 0, 0))
            image.paste(black_fill, position, glyph_image)
    return image


def compose_line_image(placements, pixel_size):
    margin = pixel_size // 8
    ink_left, ink_top, ink_right, ink_bottom = measure_ink(placements)
    canvas_width = max(pixel_size, round(ink_right - ink_left)) + margin * 2
    canvas_height = max(pixel_size, round(ink_bottom - ink_top)) + margin * 2
    return compose_image(
        placements, (canvas_width, canvas_height), margin - ink_left, margin - ink_top
    )


def compose_centered_image(placements, pixel_size):
    ink_left, ink_top, ink_right, ink_bottom = measure_ink(placements)
    ink_width = ink_right - ink_left
    ink_height = ink_bottom - ink_top
    side = max(pixel_size, round(ink_width), round(ink_height))
    return compose_image(
        placements,
        (side, side),
        (side - ink_width) / 2 - ink_left,
        (side - ink_height) / 2 - ink_top,
    )


def render_cluster_image(cluster, font_stack=DEFAULT_STACK, strict=False):
    assignments = [assign_cluster(cluster, font_stack, strict)]
    placements = lay_out_lines(assignments, DEFAULT_SINGLE_GLYPH_SIZE)
    return compose_centered_image(placements, DEFAULT_SINGLE_GLYPH_SIZE), assignments


def render_text_image(text, font_stack=DEFAULT_STACK, strict=False):
    assignments = [
        assign_cluster(cluster, font_stack, strict)
        for cluster in split_into_grapheme_clusters(text)
    ]
    placements = lay_out_lines(assignments, DEFAULT_STRING_GLYPH_SIZE)
    return compose_line_image(placements, DEFAULT_STRING_GLYPH_SIZE), assignments


def format_codepoint_label(codepoint):
    return f"U+{codepoint:04X}"


def parse_codepoint_label(label):
    codepoint = int(label[2:], 16)
    if codepoint > 0x10FFFF or codepoint in SURROGATE_RANGE:
        raise ValueError(f"'{label}' is not a valid Unicode scalar value")
    return codepoint


def parse_text_argument(argument_name, argument):
    if not CODEPOINT_SEQUENCE_PATTERN.fullmatch(argument.strip()):
        return argument
    try:
        return "".join(chr(parse_codepoint_label(label)) for label in argument.split())
    except ValueError as error:
        raise Argument_error(argument_name, argument, str(error)) from error


def parse_cluster_argument(argument):
    cluster = parse_text_argument("cluster", argument)
    clusters = split_into_grapheme_clusters(cluster)
    if len(clusters) != 1:
        raise Argument_error(
            "cluster",
            argument,
            f"'{argument}' is {len(clusters)} grapheme clusters; "
            f"glyph takes exactly one, string takes any number",
        )
    return cluster


def describe_cluster_assignment(assignment):
    draws_nothing = assignment.is_invisible or assignment.is_line_break
    description = {
        "text": assignment.cluster,
        "codepoints": [format_codepoint_label(ord(character)) for character in assignment.cluster],
        "presentation": None if draws_nothing else determine_presentation(assignment.cluster),
        "font": assignment.family_name,
        "fallback": assignment.fallback,
        "covered": not assignment.is_gap,
        "invisible": assignment.is_invisible,
        "line_break": assignment.is_line_break,
    }
    if assignment.codepoint_families:
        description["codepoint_fonts"] = list(assignment.codepoint_families)
    return description


def describe_cluster_coverage(cluster, font_stack):
    assignment = assign_cluster(cluster, font_stack, strict=False)
    description = describe_cluster_assignment(assignment)
    description["covering_families"] = (
        []
        if assignment.is_invisible or assignment.is_line_break
        else list_covering_families(cluster)
    )
    return description


def describe_runs(assignments):
    runs = []
    for line_index, line_assignments in enumerate(split_into_lines(assignments)):
        for family_name, text in split_into_runs(line_assignments):
            if family_name is None:
                continue
            spec = load_font_spec(family_name)
            glyph_order = load_glyph_order(spec.path)
            shaped_glyphs = shape_run(spec, text, DEFAULT_STRING_GLYPH_SIZE)
            runs.append(
                {
                    "line": line_index,
                    "font": family_name,
                    "text": text,
                    "glyphs": [glyph_order[glyph_index] for glyph_index, *_ in shaped_glyphs],
                }
            )
    return runs


def describe_render_result(text, font_stack, assignments, output_file, include_glyphs=False):
    clusters = [describe_cluster_assignment(assignment) for assignment in assignments]
    result = {
        "text": text,
        "path": str(output_file),
        "font_stack": list(font_stack),
        "clusters": clusters,
        "gaps": [
            {"index": index, "text": cluster["text"], "codepoints": cluster["codepoints"]}
            for index, cluster in enumerate(clusters)
            if not cluster["covered"]
        ],
    }
    if include_glyphs:
        result["runs"] = describe_runs(assignments)
    return result


def add_rendering_arguments(parser):
    parser.add_argument(
        "--output-file",
        required=True,
        type=Path,
        help="absolute path of the PNG file to write",
    )
    parser.add_argument("--font-stack", help="family names separated by commas")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="draw gaps instead of falling back to the default stack",
    )
    parser.add_argument(
        "--glyphs",
        action="store_true",
        help="also report the glyph names of every shaping run (verbose)",
    )


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Render Unicode text to a small PNG image for visual inspection."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    glyph_parser = subparsers.add_parser("glyph", help="render a single grapheme cluster")
    glyph_parser.add_argument(
        "cluster",
        help='one grapheme cluster: a literal, or codepoints like "U+0031 U+FE0F U+20E3"',
    )
    add_rendering_arguments(glyph_parser)

    string_parser = subparsers.add_parser(
        "string", help="render shaped text; a newline starts a new line"
    )
    string_parser.add_argument(
        "text", help='the text to render: a literal, or codepoints like "U+0061 U+200B U+0062"'
    )
    add_rendering_arguments(string_parser)

    subparsers.add_parser("fonts", help="list the fonts of the font catalog")

    coverage_parser = subparsers.add_parser(
        "coverage", help="report which fonts cover each grapheme cluster"
    )
    coverage_parser.add_argument(
        "text", help='the text to analyze: a literal, or codepoints like "U+0061 U+200B U+0062"'
    )
    coverage_parser.add_argument("--font-stack", help="family names separated by commas")

    return parser


def require_absolute_output_file(output_file):
    if not output_file.is_absolute():
        raise Argument_error(
            "--output-file",
            str(output_file),
            f"--output-file must be an absolute path, got '{output_file}'",
        )
    output_file.parent.mkdir(parents=True, exist_ok=True)


def run_glyph_command(arguments):
    require_absolute_output_file(arguments.output_file)
    cluster = parse_cluster_argument(arguments.cluster)
    font_stack = resolve_font_stack(arguments.font_stack)
    image, assignments = render_cluster_image(cluster, font_stack, arguments.strict)
    image.save(arguments.output_file)
    return describe_render_result(
        cluster, font_stack, assignments, arguments.output_file, arguments.glyphs
    )


def run_string_command(arguments):
    require_absolute_output_file(arguments.output_file)
    text = parse_text_argument("text", arguments.text)
    font_stack = resolve_font_stack(arguments.font_stack)
    image, assignments = render_text_image(text, font_stack, arguments.strict)
    image.save(arguments.output_file)
    return describe_render_result(
        text, font_stack, assignments, arguments.output_file, arguments.glyphs
    )


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
    text = parse_text_argument("text", arguments.text)
    font_stack = resolve_font_stack(arguments.font_stack)
    return {
        "text": text,
        "font_stack": list(font_stack),
        "clusters": [
            describe_cluster_coverage(cluster, font_stack)
            for cluster in split_into_grapheme_clusters(text)
        ],
    }


def report_error(argument, value, message):
    print(f"{argument or 'error'}: {message}", file=sys.stderr)
    print(json.dumps({"argument": argument, "value": value, "error": message}, ensure_ascii=False))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    arguments = build_argument_parser().parse_args()
    command_runners = {
        "glyph": run_glyph_command,
        "string": run_string_command,
        "fonts": run_fonts_command,
        "coverage": run_coverage_command,
    }

    try:
        result = command_runners[arguments.command](arguments)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Argument_error as error:
        report_error(error.argument, error.value, str(error))
        return 1
    except Exception as error:
        report_error(None, None, str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())

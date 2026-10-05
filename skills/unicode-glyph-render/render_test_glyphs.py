import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).parent / "render_glyph.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "render_glyph", MODULE_PATH)
render_glyph = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(render_glyph)

TEST_GLYPHS = ("U+0041", "U+2211", "U+6F22", "U+1F600", "U+1227C", "U+E0100", "U+a9c2", "𒉼", "𒀱")


TEST_STRINGS = ("A⃕᷋͡⃣̸︭᪶", "f̡̬̻̯̠̩̮͙̓᷀̇᷄ͤ̒̄̈́͢ò͈͓̙̙᷿̘᷂̮͇ͣ̑͒͒ͯ̄͘ó̫̳͙̩͎̩̻̀᷉͒᷉͢͢͞͝͝",

                "⃣︭b̅̆⃠᪶ᷓa̳̲ŕ⃔͡")



LABELED_TEST_GLYPHS = (
    ("glyph_ZWJ_family", "U+1F468 U+200D U+1F469 U+200D U+1F467", None, False),
    ("glyph_segoe_thumbs_up", "U+1F44D U+1F3FD", "Segoe UI Emoji", False),
    ("glyph_multiocular_o", "U+A66E", None, False),
)

LABELED_TEST_STRINGS = (
    (
        "emoji_sequences",
        "\U0001F468\U0000200D\U0001F469\U0000200D\U0001F467 \U0001F1E9\U0001F1EA "
        "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F "
        "\U0001F44D\U0001F3FD",
        None,
        False,
    ),
    (
        "presentation_pairs",
        "\U00002764\U00002764\U0000FE0F 1\U000020E31\U0000FE0F\U000020E3 "
        "\U0000263A\U0000FE0E\U0000263A\U0000FE0F",
        None,
        False,
    ),
    ("fira_ligatures", "a -> b != c => d === e <= f www", "Fira Code Retina", False),
    (
        "fira_segoe_fallback",
        "a -> b \U0001F600\U00002764\U0000FE0F\U0000A66E",
        "Fira Code Retina, Segoe UI Emoji",
        False,
    ),
    (
        "fira_segoe_strict_gap",
        "a -> b \U0001F600\U00002764\U0000FE0F\U0000A66E",
        "Fira Code Retina, Segoe UI Emoji",
        True,
    ),
    ("split_cluster", "x\U0001F600\U00000301y", None, False),
    ("invisible_ZWSP", "a\U0000200Bb", None, False),
    ("U_plus_string", "U+0061 U+200B U+0062", None, False),
    ("line_breaks", "line one\nline two\r\nline three", None, False),
)

OUTPUT_DIRECTORY = Path(__file__).parent / "test_images"


def describe_fonts(assignments):
    family_names = []
    for assignment in assignments:
        if assignment.is_line_break:
            family_names.append("line break")
        elif assignment.is_invisible:
            family_names.append("invisible")
        elif assignment.is_gap:
            family_names.append("gap")
        elif assignment.family_name is not None:
            family_names.append(assignment.family_name)
        else:
            family_names.extend(assignment.codepoint_families)
    return ", ".join(dict.fromkeys(family_names))


def render_labeled_glyph(glyph, font_stack, strict):
    cluster = render_glyph.parse_cluster_argument(glyph)
    return render_glyph.render_cluster_image(cluster, font_stack, strict)


def render_labeled_text(text, font_stack, strict):
    parsed_text = render_glyph.parse_text_argument("text", text)
    return render_glyph.render_text_image(parsed_text, font_stack, strict)


def render_labeled_case(label, render, text, font_stack_argument, strict):
    try:
        font_stack = render_glyph.resolve_font_stack(font_stack_argument)
        image, assignments = render(text, font_stack, strict)
    except Exception as error:
        print(f"{label}: FAILED ({error})")
        return
    image.save(OUTPUT_DIRECTORY / f"{label}.png")
    print(f"{label} -> {describe_fonts(assignments)}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for glyph in TEST_GLYPHS:
        cluster = render_glyph.parse_cluster_argument(glyph)
        image, assignments = render_glyph.render_cluster_image(cluster)
        image.save(OUTPUT_DIRECTORY / f"{glyph}.png")
        print(f"{glyph} -> {describe_fonts(assignments)}")
    for text in TEST_STRINGS:
        image, assignments = render_glyph.render_text_image(text)
        image.save(OUTPUT_DIRECTORY / f"{text}.png")
        print(f"{text} -> {describe_fonts(assignments)}")
    for label, glyph, font_stack_argument, strict in LABELED_TEST_GLYPHS:
        render_labeled_case(label, render_labeled_glyph, glyph, font_stack_argument, strict)
    for label, text, font_stack_argument, strict in LABELED_TEST_STRINGS:
        render_labeled_case(label, render_labeled_text, text, font_stack_argument, strict)


if __name__ == "__main__":
    main()

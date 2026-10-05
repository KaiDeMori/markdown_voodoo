import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parent / "render_glyph.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "render_glyph", MODULE_PATH)
render_glyph = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(render_glyph)

TEST_GLYPHS = ("U+0041", "U+2211", "U+6F22", "U+1F600", "U+1227C", "U+E0100", "U+a9c2", "𒉼", "𒀱")


TEST_STRINGS = ("A⃕᷋͡⃣̸︭᪶", "f̡̬̻̯̠̩̮͙̓᷀̇᷄ͤ̒̄̈́͢ò͈͓̙̙᷿̘᷂̮͇ͣ̑͒͒ͯ̄͘ó̫̳͙̩͎̩̻̀᷉͒᷉͢͢͞͝͝",

                "⃣︭b̅̆⃠᪶ᷓa̳̲ŕ⃔͡")



OUTPUT_DIRECTORY = Path(__file__).parent / "test_images"


def describe_fonts(assignments):
    family_names = []
    for assignment in assignments:
        if assignment.is_invisible:
            family_names.append("invisible")
        elif assignment.is_gap:
            family_names.append("gap")
        elif assignment.family_name is not None:
            family_names.append(assignment.family_name)
        else:
            family_names.extend(assignment.codepoint_families)
    return ", ".join(dict.fromkeys(family_names))


def main():
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


if __name__ == "__main__":
    main()

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parent / "render_glyph.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "render_glyph", MODULE_PATH)
render_glyph = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(render_glyph)

TEST_GLYPHS = ("U+0041", "U+2211", "U+6F22", "U+1F600", "U+1227C", "U+E0100")
OUTPUT_DIRECTORY = Path(__file__).parent / "test_images"


def main():
    for argument in TEST_GLYPHS:
        codepoint = render_glyph.parse_codepoint_argument(argument)
        image, spec = render_glyph.render_codepoint(codepoint)
        label = render_glyph.format_codepoint_label(codepoint)
        image.save(OUTPUT_DIRECTORY / f"{label}.png")
        print(f"{label} -> {spec.filename}")


if __name__ == "__main__":
    main()

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parent / "render_glyph.py"
MODULE_SPEC = importlib.util.spec_from_file_location(
    "render_glyph", MODULE_PATH)
render_glyph = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(render_glyph)

TEST_GLYPHS = ("U+0041", "U+2211", "U+6F22", "U+1F600", "U+1227C", "U+E0100", "U+a9c2")
TEST_STRINGS = ("foo", "bar")
OUTPUT_DIRECTORY = Path(__file__).parent / "test_images"


def main():
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for argument in TEST_GLYPHS:
        codepoint = render_glyph.parse_codepoint_argument(argument)
        image, spec = render_glyph.render_codepoint(codepoint)
        label = render_glyph.format_codepoint_label(codepoint)
        image.save(OUTPUT_DIRECTORY / f"{label}.png")
        print(f"{label} -> {spec.path.name}")
    for text in TEST_STRINGS:
        image, specs = render_glyph.render_string(text)
        image.save(OUTPUT_DIRECTORY / f"{text}.png")
        print(f"{text} -> {', '.join(spec.path.name for spec in specs)}")


if __name__ == "__main__":
    main()

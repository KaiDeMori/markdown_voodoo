"""fernschreiber's color themes: a TOML file with a Textual base theme and five colors."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from textual.color import Color
from textual.theme import BUILTIN_THEMES


@dataclass
class Color_theme:
    base: str
    background: str
    text: str
    dim: str
    frame: str
    focus: str


def load_color_theme(file_location: Path) -> Color_theme:
    """Reads a theme file, and stops fernschreiber before its window opens when the file, the TOML, a key, a color or the base theme is wrong."""
    with file_location.open("rb") as file:
        color_theme = Color_theme(**tomllib.load(file))
    for color in (color_theme.background, color_theme.text, color_theme.dim, color_theme.frame, color_theme.focus):
        Color.parse(color)
    if color_theme.base not in BUILTIN_THEMES:
        raise ValueError(f"{file_location}: unknown base theme {color_theme.base!r}; Textual knows {', '.join(sorted(BUILTIN_THEMES))}")
    return color_theme

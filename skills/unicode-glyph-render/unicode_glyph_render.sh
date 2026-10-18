#!/usr/bin/env bash
# unicode_glyph_render: renders Unicode text to a PNG and reports, as JSON, which font drew each grapheme cluster.
# It runs render_glyph.py with the skill's own venv, so the glyph renderer gets the short call unicode-glyph-render.
# Usage: unicode_glyph_render.sh <command> ...

set -e

skill_folder=$(dirname "${BASH_SOURCE[0]}")
exec "$skill_folder/.venv/Scripts/python.exe" "$skill_folder/render_glyph.py" "$@"

#!/usr/bin/env bash
# calm_md: a markdown file by chapter: its table of contents, one chapter to read, one chapter to write.
# It runs calm_md.py with the skill's own venv, isolated from the folder a raven stands in, so calm-md is a short call.
# Usage: calm_md.sh toc <file> [title ...]
#        calm_md.sh read <file> <title> ...
#        calm_md.sh write <file> <title> ... < chapter
#        calm_md.sh replace <file> <title> ... < old line, new text
#        calm_md.sh find <file> <word> [title ...]

set -e

skill_folder=$(dirname "${BASH_SOURCE[0]}")
exec "$skill_folder/.venv/Scripts/python.exe" -I "$skill_folder/calm_md.py" "$@"

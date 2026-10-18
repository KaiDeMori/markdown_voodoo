#!/usr/bin/env bash
# token_counter: counts how many tokens files take up for a Claude model.
# It runs token_counter.py with the skill's own venv, so the token counter gets the short call token-counter.
# Usage: token_counter.sh <file> [<file> ...]

set -e

skill_folder=$(dirname "${BASH_SOURCE[0]}")
exec "$skill_folder/.venv/Scripts/python.exe" "$skill_folder/token_counter.py" "$@"

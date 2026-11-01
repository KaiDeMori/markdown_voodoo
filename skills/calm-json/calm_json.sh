#!/usr/bin/env bash
# calm_json: runs calm-json.exe beside this script, so the deployed skill gets its short call, calm-json, like every hall tool.
# Git Bash's path conversion stays on: it turns /c/... into C:/..., which the exe needs.
exec "$(dirname "${BASH_SOURCE[0]}")/calm-json.exe" "$@"

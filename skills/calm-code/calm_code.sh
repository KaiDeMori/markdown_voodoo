#!/usr/bin/env bash
# calm_code: runs calm-code.exe beside this script, so the deployed skill gets its short call, calm-code, like every hall tool.
# Git Bash's path conversion stays on: it turns /c/... into C:/..., which the exe needs.
exec "$(dirname "${BASH_SOURCE[0]}")/calm-code.exe" "$@"

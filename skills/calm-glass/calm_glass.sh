#!/usr/bin/env bash
# calm_glass: runs calm_glass.py beside it with the system's Python, so calm-glass gets its short call; ImageMagick 7 does the pixel work.
exec /c/Users/devboese/AppData/Local/Programs/Python/Python312/python "$(dirname "${BASH_SOURCE[0]}")/calm_glass.py" "$@"

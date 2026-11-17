#!/usr/bin/env bash
MSYS_NO_PATHCONV=1 exec "$(dirname "${BASH_SOURCE[0]}")/calm_comms.exe" "$@"

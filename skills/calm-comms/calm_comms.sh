#!/usr/bin/env bash
# calm_comms, Rabenschnack 2.0: runs calm_comms.exe beside this script, so the calm-comms command and calm-email's forward keep calling calm_comms.sh.
# Git Bash would rewrite an argument that looks like a POSIX path, such as a text starting with /, so the conversion is off.
MSYS_NO_PATHCONV=1 exec "$(dirname "${BASH_SOURCE[0]}")/calm_comms.exe" "$@"

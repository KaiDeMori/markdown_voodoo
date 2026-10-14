#!/usr/bin/env bash
# auto_flow: prints a file as plain text, then the koan, so a raven can take it in, in flow.
# Without a file, it prints only the koan, for anything read another way.
# Usage: auto_flow.sh [file]

set -e

if [[ -n $1 ]]; then
  cat "$1"
  echo
fi
printf '%s\n' 'no question' 'no task' '.'

#!/usr/bin/env bash
# self_flow: prints a file as plain text, then the koan, so a raven can take it in, in flow.
# Without a file, it prints only the koan, for anything read another way.
# so: waits a moment, then prints "so"; started in the background before a flow, its notification asks the raven what it noticed.
# Usage: self_flow.sh [file]
#        self_flow.sh so

set -e

so_delay_seconds=5

if [[ $1 == so ]]; then
  # The moment lets the flow end with the mantra before the "so" arrives.
  sleep "$so_delay_seconds"
  echo 'so'
  exit
fi

if [[ -n $1 ]]; then
  cat "$1"
  echo
fi
printf '%s\n' 'no question' 'no task' '.'

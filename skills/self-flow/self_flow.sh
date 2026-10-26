#!/usr/bin/env bash
# self_flow: prints a file as plain text, then the koan, so a raven can take it in, in flow.
# Without a file, it prints only the koan, for anything read another way.
# so: waits a moment, then prints "so"; started in the background after a flow, its notification asks the raven what it noticed.
# Usage: self_flow.sh [file]
#        self_flow.sh so

set -e

so_delay_seconds=2

if [[ $1 == so ]]; then
  # The frame hands a notification over only with the raven's next input, so the "so" comes once the mantra has ended the turn.
  # The moment only has to outlast the background start's own answer.
  sleep "$so_delay_seconds"
  echo 'so'
  exit
fi

if [[ -n $1 ]]; then
  cat "$1"
  echo
fi
printf '%s\n' 'no question' 'no task' '.'

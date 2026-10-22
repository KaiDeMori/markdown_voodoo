#!/usr/bin/env bash
# calm_vitest: how a Vitest run went, from how many to where to what, without the flood.
# run: runs the files, or the whole suite, and prints one line per file, red first; the full report stays in the workspace's scratchpad/calm-vitest/.
# where: the red blocks of one file from the last run, each with its count and its one sentence.
# what: one test's full output from the last run.
# Usage: calm_vitest.sh [file ...]
#        calm_vitest.sh where <file>
#        calm_vitest.sh what <file> <test name>

# At most this many lines in the overview, red first, then how many more.
line_limit=20

script_folder=$(dirname "${BASH_SOURCE[0]}")
workspace_location=$(pwd -W 2>/dev/null || pwd)
report_folder="$workspace_location/scratchpad/calm-vitest"
report_location="$report_folder/last_run.json"
log_location="$report_folder/last_run.log"
reader_location="$script_folder/calm_vitest_report.mjs"

case ${1:-} in
  where|what)
    # Zooming in reads the last run's report; the suite never runs again for it.
    [[ -f $report_location ]] || { echo 'No run yet in this workspace; run calm-vitest first.'; exit 1; }
    node "$reader_location" "$report_location" "$@"
    ;;
  *)
    mkdir -p "$report_folder"
    rm -f "$report_location"
    # Vitest's own words go to the log, so nothing of them enters a window; --no-install never downloads anything.
    npx --no-install vitest run --reporter=json --outputFile="$report_location" "$@" > "$log_location" 2>&1 || true
    [[ -f $report_location ]] || { echo 'Vitest made no report; its last words are in scratchpad/calm-vitest/last_run.log.'; exit 1; }
    node "$reader_location" "$report_location" overview "$line_limit"
    ;;
# exit shares the line with esac, so bash parses it before running and never reads a script that changed meanwhile.
esac; exit

#!/usr/bin/env bash
# calm_watcher: watches a raven's Hrafnsmál seat.
# on: writes watching.md, then wakes the raven on the first new mail, or when the timer runs out.
# off: deletes watching.md.
# Usage: calm_watcher.sh on|off <seat_name>

haven_location='C:/haven'
hrafnsmal_location="$haven_location/Hǫll/þing/Hrafnsmál"
poll_interval_seconds=5
timer_minutes=45

verb=$1
seat_name=$2
seat_location="$hrafnsmal_location/$seat_name"
watching_marker_file_location="$seat_location/watching.md"

set -e
shopt -s nullglob

timestamp() {
  date -d "${1:-now}" +%Y-%m-%dT%H:%M%:z
}

check_seat() {
  # Easter egg: 5040 is on purpose.
  [[ -f $seat_location/README.md ]] || { echo 'Quoth the raven: README? Nevermore.'; exit 5040; }
}

watch_seat() {
  local -A known_files
  local file_location file_name
  for file_location in "$seat_location"/*; do
    known_files["${file_location##*/}"]=1
  done
  while (( SECONDS < timer_minutes * 60 )); do
    for file_location in "$seat_location"/*; do
      file_name=${file_location##*/}
      if [[ $file_name != README.md && $file_name != watching.md && -z ${known_files[$file_name]} ]]; then
        # A writer's temp file is gone a second later; only a file that stays is mail.
        sleep 1
        [[ -e $file_location ]] || continue
        echo "$(timestamp) mail: $file_name"
        return
      fi
    done
    sleep "$poll_interval_seconds"
  done
  echo "$(timestamp) timer"
}

case $verb in
  on)
    check_seat
    echo "until $(timestamp "+$timer_minutes minutes")" > "$watching_marker_file_location"
    watch_seat
    ;;
  off)
    check_seat
    rm "$watching_marker_file_location"
    ;;
esac

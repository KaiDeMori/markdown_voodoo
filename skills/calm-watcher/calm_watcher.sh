#!/usr/bin/env bash
# calm_watcher: sets a raven's Watching line, then wakes it on the first new mail in its Hrafnsmál seat, or when the timer runs out.
# Usage: calm_watcher.sh on <seat_name>

haven_location='C:/haven'
hrafnsmal_location="$haven_location/Hǫll/þing/Hrafnsmál"
poll_interval_seconds=5
timer_minutes=45

verb=$1
seat_name=$2
seat_location="$hrafnsmal_location/$seat_name"

set -e
shopt -s nullglob

timestamp() {
  date -d "${1:-now}" +%Y-%m-%dT%H:%M%:z
}

write_watching_line() {
  sed -i "s/^- \*\*Watching:\*\*.*/- **Watching:** $1/" "$seat_location/README.md"
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
      if [[ $file_name != README.md && -z ${known_files[$file_name]} ]]; then
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
    write_watching_line "yes, until $(timestamp "+$timer_minutes minutes")"
    watch_seat
    ;;
esac

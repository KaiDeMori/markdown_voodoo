#!/usr/bin/env bash
# calm_watcher: wakes a raven on the first new mail in its Hrafnsmál seat, or when the timer runs out.
# Usage: calm_watcher.sh on <seat_name>

haven_location='C:/haven'
hrafnsmal_location="$haven_location/Hǫll/þing/Hrafnsmál"
poll_interval_seconds=5
timer_minutes=45

verb=$1
seat_name=$2
seat_location="$hrafnsmal_location/$seat_name"

shopt -s nullglob

timestamp() {
  date +%Y-%m-%dT%H:%M%:z
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
        echo "$(timestamp) mail: $file_name"
        return
      fi
    done
    sleep "$poll_interval_seconds"
  done
  echo "$(timestamp) timer"
}

case $verb in
  on) watch_seat ;;
esac

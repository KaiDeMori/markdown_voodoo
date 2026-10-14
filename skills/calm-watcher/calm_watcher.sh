#!/usr/bin/env bash
# calm_watcher: watches a raven's Hrafnsmal seat.
# on: keeps watching.md while it watches, and wakes the raven on the first new mail, or when the long or short timer runs out.
# off: deletes watching.md.
# overview: lists every seat with its watching.md, or - without one.
# inbox: prints every waiting mail, oldest first, and moves it into already_read.
# Usage: calm_watcher.sh on <seat_name> [long|short]
#        calm_watcher.sh off <seat_name>
#        calm_watcher.sh overview
#        calm_watcher.sh inbox <seat_name>

haven_location='C:/haven'
hrafnsmal_location="$haven_location/Hall/thing/Hrafnsmal"
poll_interval_seconds=10
long_watcher_minutes=45
short_watcher_minutes=4

verb=$1
seat_name=$2
watcher_length=${3:-long}
seat_location="$hrafnsmal_location/$seat_name"
watching_marker_file_location="$seat_location/watching.md"
already_read_location="$seat_location/already_read"

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
      if [[ -f $file_location && $file_name != README.md && $file_name != watching.md && -z ${known_files[$file_name]} ]]; then
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

show_overview() {
  local seat_location watching_status
  for seat_location in "$hrafnsmal_location"/*/; do
    seat_location=${seat_location%/}
    if [[ -f $seat_location/watching.md ]]; then
      watching_status=$(<"$seat_location/watching.md")
    else
      watching_status=-
    fi
    printf '%-24s %s\n' "${seat_location##*/}" "$watching_status"
  done
}

show_inbox() {
  local file_name mail_count=0
  mkdir -p "$already_read_location"
  while IFS= read -r file_name; do
    if [[ -e $already_read_location/$file_name ]]; then echo "Deja lu: $file_name"; exit 1; fi
    echo "--- $file_name"
    cat "$seat_location/$file_name"
    echo
    mv "$seat_location/$file_name" "$already_read_location/"
    mail_count=$((mail_count + 1))
  # Every file at the top of the seat is mail, oldest first, except README.md and watching.md.
  done < <(find "$seat_location" -maxdepth 1 -type f ! -name README.md ! -name watching.md -printf '%T@ %f\n' | sort -n | cut -d' ' -f2-)
  if (( mail_count == 0 )); then echo 'no mail'; fi
}

case $verb in
  on)
    check_seat
    case $watcher_length in
      long) timer_minutes=$long_watcher_minutes ;;
      short) timer_minutes=$short_watcher_minutes ;;
      *) echo 'Long or short?'; exit 1 ;;
    esac
    echo "until $(timestamp "+$timer_minutes minutes")" > "$watching_marker_file_location"
    # watching.md lives exactly as long as this watcher.
    trap 'rm -f "$watching_marker_file_location"' EXIT
    trap exit INT TERM
    watch_seat
    # The bell is for humans in a terminal; ravens in the background never hear it.
    if [[ -t 1 ]]; then printf '\a'; fi
    ;;
  off)
    check_seat
    rm "$watching_marker_file_location"
    ;;
  overview)
    show_overview
    ;;
  inbox)
    check_seat
    show_inbox
    ;;
esac

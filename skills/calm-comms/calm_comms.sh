#!/usr/bin/env bash
# calm_comms, Rabenschnack 1.5: watches a raven's Hrafnsmal seat and sends its mail.
# on: keeps watching.md while it watches, and wakes the raven on the first new mail, or when the long or short timer runs out.
# off: stops the seat's watcher and deletes watching.md.
# overview: lists every seat with the timer of its living watcher, or - without one.
# inbox: prints waiting mail, oldest first, up to a number and a size limit, and moves it into already_read.
# send: writes a mail from one seat into another, and never overwrites a mail.
# Terminal mode: the fernschreiber sets calm_comms_mode=terminal.
# Then nothing pauses, inbox has no limits, and on stays present without a timer, printing one line per mail as it lands.
# A watcher in terminal mode stays only while its stdin stays open, so a crashed terminal leaves no ghost.
# Usage: calm_comms.sh on <seat_name> [long|short|<minutes>]
#        calm_comms.sh off <seat_name>
#        calm_comms.sh overview
#        calm_comms.sh inbox <seat_name> [mail_limit]
#        calm_comms.sh send <seat_name> <target_seat_name> <text>

haven_location='C:/haven'
hrafnsmal_location="$haven_location/Hall/thing/Hrafnsmal"
poll_interval_seconds=10
long_watcher_minutes=55
short_watcher_minutes=4
inbox_mail_limit=3
inbox_size_limit_kilobytes=10
write_throttle_seconds=2
# Terminal mode is no verb, so no raven finds it in a skill list; -1 lifts a limit.
terminal_mode=''
if [[ ${calm_comms_mode:-} == terminal ]]; then
  terminal_mode=yes
  inbox_mail_limit=-1
  inbox_size_limit_kilobytes=-1
fi

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
  [[ -n $1 && -f $hrafnsmal_location/$1/README.md ]] || { echo "Quoth the raven: README in $1? Nevermore."; exit 5040; }
}

throttle() {
  # A busy hall gets a buffer: a call that wrote waits a moment before it returns.
  # A terminal is no busy hall: terminal mode never waits.
  if [[ -n $terminal_mode ]]; then return 0; fi
  sleep "$write_throttle_seconds"
}

rest() {
  # read -t waits inside bash: no sleep.exe on every look, and a stop still acts at once.
  local read_status=0
  if [[ -n $terminal_mode ]]; then
    # Terminal mode waits on stdin, which the terminal keeps open and never writes to.
    # When the terminal is gone, even after a crash, the pipe closes, read meets its end, and the watcher leaves without a ghost.
    read -t "$1" -u 0 || read_status=$?
    if (( read_status > 0 && read_status <= 128 )); then exit 0; fi
    return 0
  fi
  # Everyone else waits on a quiet FIFO, deleted right after opening; the open descriptor keeps it alive, and nothing is left behind.
  if [[ -z ${quiet_fd:-} ]]; then
    local fifo_location="/tmp/calm_comms_quiet_$$"
    mkfifo "$fifo_location"
    exec {quiet_fd}<> "$fifo_location"
    rm -f "$fifo_location"
  fi
  read -t "$1" -u "$quiet_fd" || true
}

read_marker() {
  # watching.md holds the moment the timer runs out, or present in terminal mode, and the watcher's process ID.
  marker_until=''
  marker_pid=''
  if [[ ! -f $1 ]]; then return 0; fi
  # The marker can vanish while it is read, when off and a stopping watcher clean up at the same moment.
  marker_until=$(sed -n -e 's/^until //p' -e '/^present$/p' "$1" 2> /dev/null || true)
  marker_pid=$(sed -n 's/^pid //p' "$1" 2> /dev/null || true)
}

is_watcher_of() {
  # A process ID can be handed out again after a restart, so the command line has to name this watcher.
  local command_line
  if [[ -z $1 || ! -r /proc/$1/cmdline ]]; then return 1; fi
  command_line=$(tr '\0' ' ' < "/proc/$1/cmdline")
  [[ $command_line == *"calm_comms.sh on $2 "* ]]
}

stop_old_watcher() {
  # Quiet when there is nothing to do, two words after a cleanup, and one calm line otherwise.
  read_marker "$watching_marker_file_location"
  if [[ -z $marker_pid ]] || ! kill -0 "$marker_pid" 2> /dev/null; then return 0; fi
  if ! is_watcher_of "$marker_pid" "$seat_name"; then
    echo "watching.md named process $marker_pid, which is no watcher of $seat_name; it was left alone."
    return 0
  fi
  if kill "$marker_pid" 2> /dev/null; then
    echo 'cleanup done'
  else
    echo "The old watcher, process $marker_pid, could not be stopped."
  fi
}

remove_own_marker() {
  # A watcher deletes watching.md only while it is still its own, never a newer watcher's.
  read_marker "$watching_marker_file_location"
  if [[ $marker_pid == "$$" ]]; then rm -f "$watching_marker_file_location"; fi
}

watch_seat() {
  local -A known_files
  local file_location file_name
  for file_location in "$seat_location"/*; do
    known_files["${file_location##*/}"]=1
  done
  # Terminal mode stays present without a timer.
  while [[ -n $terminal_mode ]] || (( SECONDS < timer_minutes * 60 )); do
    for file_location in "$seat_location"/*; do
      file_name=${file_location##*/}
      if [[ -f $file_location && $file_name != README.md && $file_name != watching.md && -z ${known_files[$file_name]} ]]; then
        # A writer's temp file is gone a second later; only a file that stays is mail.
        rest 1
        [[ -e $file_location ]] || continue
        echo "$(timestamp) mail: $file_name"
        # A raven wakes on the first mail; terminal mode keeps watching, one line per mail.
        if [[ -z $terminal_mode ]]; then return; fi
        known_files["$file_name"]=1
      fi
    done
    rest "$poll_interval_seconds"
  done
  echo "$(timestamp) timer"
}

show_overview() {
  local seat_location overview_seat_name
  for seat_location in "$hrafnsmal_location"/*/; do
    seat_location=${seat_location%/}
    overview_seat_name=${seat_location##*/}
    read_marker "$seat_location/watching.md"
    # A marker without its living watcher counts as not watching.
    if [[ $marker_until == present ]] && is_watcher_of "$marker_pid" "$overview_seat_name"; then
      printf '%-24s present\n' "$overview_seat_name"
    elif [[ -n $marker_until ]] && is_watcher_of "$marker_pid" "$overview_seat_name"; then
      printf '%-24s until %s\n' "$overview_seat_name" "$marker_until"
    else
      printf '%-24s -\n' "$overview_seat_name"
    fi
  done
}

show_inbox() {
  local modification_time file_size file_size_text file_name mail_count=0 used_bytes=0 waiting_count=0 waiting_list=''
  # Every file at the top of the seat is mail, oldest first, except README.md and watching.md.
  while read -r modification_time file_size file_name; do
    # The first mail of a call always comes, so a big one arrives alone.
    if (( waiting_count > 0 || mail_count == mail_limit || (mail_count > 0 && inbox_size_limit_kilobytes >= 0 && used_bytes + file_size > inbox_size_limit_kilobytes * 1024) )); then
      waiting_count=$((waiting_count + 1))
      if (( file_size < 1024 )); then file_size_text='<1 KB'; else file_size_text="$(( (file_size + 1023) / 1024 )) KB"; fi
      waiting_list+="${waiting_list:+, }$file_name ($file_size_text)"
      continue
    fi
    if [[ -e $already_read_location/$file_name ]]; then echo "Deja lu: $file_name"; exit 1; fi
    echo "--- $file_name"
    cat "$seat_location/$file_name"
    # A mail without a final line break still gets its own line end, so the next header stays apart.
    [[ -z $(tail -c 1 "$seat_location/$file_name") ]] || echo
    echo
    mkdir -p "$already_read_location"
    mv "$seat_location/$file_name" "$already_read_location/"
    mail_count=$((mail_count + 1))
    used_bytes=$((used_bytes + file_size))
  done < <(find "$seat_location" -maxdepth 1 -type f ! -name README.md ! -name watching.md -printf '%T@ %s %f\n' | sort -n)
  if (( waiting_count > 0 && mail_count > 0 )); then echo "$waiting_count more waiting: $waiting_list"; fi
  if (( waiting_count > 0 && mail_count == 0 )); then echo "$waiting_count waiting: $waiting_list"; fi
  if (( mail_count == 0 && waiting_count == 0 )); then echo 'no mail'; fi
  if (( mail_count > 0 )); then throttle; fi
}

send_mail() {
  local mail_file_location="$hrafnsmal_location/$target_seat_name/from_${seat_name}_$(date +%Y-%m-%d_%H%M%S).md"
  [[ -n $mail_text ]] || { echo 'Nothing to send.'; exit 1; }
  [[ ! -e $mail_file_location ]] || { echo 'One mail per second; send it again in a moment.'; exit 1; }
  # noclobber: an existing mail is never overwritten, not even in a race.
  set -o noclobber
  printf '%s\nFrom: %s\nTo: %s\n%s\n' "$(timestamp)" "$seat_name" "$target_seat_name" "$mail_text" > "$mail_file_location"
  throttle
}

case $verb in
  on)
    check_seat "$seat_name"
    case $watcher_length in
      long) timer_minutes=$long_watcher_minutes ;;
      short) timer_minutes=$short_watcher_minutes ;;
      *[!0-9]*) echo 'Long, short, or minutes?'; exit 1 ;;
      *) timer_minutes=$watcher_length ;;
    esac
    stop_old_watcher
    if [[ -n $terminal_mode ]]; then
      printf 'present\npid %s\n' "$$" > "$watching_marker_file_location"
    else
      printf 'until %s\npid %s\n' "$(timestamp "+$timer_minutes minutes")" "$$" > "$watching_marker_file_location"
    fi
    # watching.md lives exactly as long as this watcher.
    trap remove_own_marker EXIT
    # 143 is the usual exit code after a stop; the raven reads it as: no mail, nothing to do.
    trap 'echo stopped; exit 143' INT TERM
    watch_seat
    # The bell rings only in a terminal; ravens in the background never hear it.
    if [[ -t 1 ]]; then printf '\a'; fi
    ;;
  off)
    check_seat "$seat_name"
    stop_old_watcher
    # A stopped watcher deletes its own marker; one without a living watcher goes here.
    rm -f "$watching_marker_file_location"
    throttle
    ;;
  overview)
    show_overview
    ;;
  inbox)
    check_seat "$seat_name"
    mail_limit=${3:-$inbox_mail_limit}
    show_inbox
    ;;
  send)
    target_seat_name=$3
    check_seat "$seat_name"
    check_seat "$target_seat_name"
    shift 3
    mail_text=$*
    send_mail
    ;;
# exit shares the line with esac, so bash parses it before running and never reads a script that changed meanwhile.
esac; exit

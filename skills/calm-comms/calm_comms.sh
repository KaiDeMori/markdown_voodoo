#!/usr/bin/env bash
# calm_comms, Rabenschnack 1.6: watches a raven's Hrafnsmal seat and sends its mail.
# on: keeps watching.md while it watches, and wakes the raven on the first new mail, or when the long or short timer runs out.
# A waking watcher leaves watching.md saying awake for a few minutes, until the raven's next on replaces it.
# off: stops the seat's watcher and deletes watching.md.
# overview: lists every seat with the timer of its living watcher, awake for a raven that just woke, or - otherwise.
# inbox: prints waiting mail, oldest first, up to a number and a size limit, and moves it into already_read.
# send: writes a mail from one seat into another, and never overwrites a mail.
# group: writes a mail from one seat to every other member of a group, and keeps a copy as the group's thread.
# join and leave: add a seat to a group's MEMBERS.txt or take it out, and wake nobody.
# Terminal mode: the fernschreiber sets calm_comms_mode=terminal.
# Then nothing pauses, inbox has no limits, and on stays present without a timer, printing one line per mail as it lands.
# A watcher in terminal mode stays only while its stdin stays open, so a crashed terminal leaves no ghost.
# Usage: calm_comms.sh on <seat_name> [long|short|<minutes>]
#        calm_comms.sh off <seat_name>
#        calm_comms.sh overview
#        calm_comms.sh inbox <seat_name> [mail_limit]
#        calm_comms.sh send <seat_name> <target_seat_name> <text>
#        calm_comms.sh group <seat_name> <group_name> <text>
#        calm_comms.sh join <seat_name> <group_name>
#        calm_comms.sh leave <seat_name> <group_name>

haven_location='C:/haven'
hrafnsmal_location="$haven_location/Hall/thing/Hrafnsmal"
# Each group is a folder here: its MEMBERS.txt names one seat per line, and the folder keeps the thread.
group_chat_location="$haven_location/Hall/thing/group_chat"
poll_interval_seconds=10
long_watcher_minutes=55
short_watcher_minutes=4
# A raven that just woke stays awake in the overview this long; one in a long turn re-arms only when that turn ends.
awake_grace_minutes=5
inbox_mail_limit=3
inbox_size_limit_kilobytes=10
write_throttle_seconds=2
# A watcher that wakes waits a random moment between these two before it wakes its raven.
wake_jitter_shortest_seconds=1
wake_jitter_longest_seconds=5
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

jitter() {
  # One mail can wake many watchers at once, like a NOTAR to all; a random pause lets their ravens wake one by one.
  # Drawn in milliseconds, so two watchers rarely pick the same moment; RANDOM reaches 32767, so the span stays below 32 seconds.
  local jitter_milliseconds jitter_seconds
  jitter_milliseconds=$(( wake_jitter_shortest_seconds * 1000 + RANDOM % ((wake_jitter_longest_seconds - wake_jitter_shortest_seconds) * 1000 + 1) ))
  printf -v jitter_seconds '%d.%03d' $(( jitter_milliseconds / 1000 )) $(( jitter_milliseconds % 1000 ))
  rest "$jitter_seconds"
}

read_marker() {
  # watching.md holds the moment the timer runs out, or present in terminal mode, and the watcher's process ID.
  # After a wake it holds only awake, and the second its grace ends.
  marker_until=''
  marker_pid=''
  marker_awake=''
  if [[ ! -f $1 ]]; then return 0; fi
  # The marker can vanish while it is read, when off and a stopping watcher clean up at the same moment.
  marker_until=$(sed -n -e 's/^until //p' -e '/^present$/p' "$1" 2> /dev/null || true)
  marker_pid=$(sed -n 's/^pid //p' "$1" 2> /dev/null || true)
  marker_awake=$(sed -n 's/^awake //p' "$1" 2> /dev/null || true)
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

leave_awake_marker() {
  # A raven that just woke is about to watch again, so its seat shows awake instead of gone until its next on.
  # The awake marker names no process, so the exit leaves it in place; off and the next on replace it.
  read_marker "$watching_marker_file_location"
  if [[ $marker_pid == "$$" ]]; then
    printf 'awake %s\n' "$(( $(date +%s) + awake_grace_minutes * 60 ))" > "$watching_marker_file_location"
  fi
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
    # A marker without its living watcher counts as not watching; an awake marker counts while its grace lasts.
    if [[ $marker_until == present ]] && is_watcher_of "$marker_pid" "$overview_seat_name"; then
      printf '%-24s present\n' "$overview_seat_name"
    elif [[ -n $marker_until ]] && is_watcher_of "$marker_pid" "$overview_seat_name"; then
      printf '%-24s until %s\n' "$overview_seat_name" "$marker_until"
    elif [[ $marker_awake =~ ^[0-9]+$ ]] && (( $(date +%s) < marker_awake )); then
      printf '%-24s awake\n' "$overview_seat_name"
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

check_group() {
  if [[ -z $1 ]]; then echo "$verb <seat_name> <group_name>?"; exit 1; fi
  if [[ $1 == */* || $1 == *\\* || $1 == . || $1 == .. || ! -f $group_chat_location/$1/MEMBERS.txt ]]; then echo "There is no group $1 in group_chat."; exit 1; fi
}

read_members() {
  # MEMBERS.txt names one seat per line; empty lines are skipped, and spaces around a name don't count.
  # The names land in the caller's members.
  local member
  members=()
  while IFS= read -r member || [[ -n $member ]]; do
    member=${member//[[:space:]]/}
    if [[ -n $member ]]; then members+=("$member"); fi
  done < "$group_chat_location/$1/MEMBERS.txt"
}

write_members() {
  # The caller's members are written anew, one seat per line, and replace the old list in one step.
  local members_file_location="$group_chat_location/$target_seat_name/MEMBERS.txt"
  if (( ${#members[@]} > 0 )); then printf '%s\n' "${members[@]}" > "$members_file_location.new"; else : > "$members_file_location.new"; fi
  mv -f "$members_file_location.new" "$members_file_location"
}

send_group() {
  local group_location="$group_chat_location/$target_seat_name" member is_member='' file_name stamp location reached_count
  local -a members=() locations
  [[ -n $mail_text ]] || { echo 'Nothing to send.'; exit 1; }
  read_members "$target_seat_name"
  for member in "${members[@]}"; do
    if [[ $member == "$seat_name" ]]; then is_member=yes; fi
  done
  [[ -n $is_member ]] || { echo "$seat_name is no member of $target_seat_name, so nothing goes out."; exit 1; }
  # The group's folder keeps the thread; every other member gets a copy in their seat, and the copy wakes their watcher.
  file_name="from_${seat_name}_$(date +%Y-%m-%d_%H%M%S).md"
  locations=("$group_location/$file_name")
  for member in "${members[@]}"; do
    if [[ $member == "$seat_name" ]]; then continue; fi
    [[ -f $hrafnsmal_location/$member/README.md ]] || { echo "$target_seat_name names $member, who has no seat, so nothing goes out."; exit 1; }
    locations+=("$hrafnsmal_location/$member/$file_name")
  done
  # Everything is checked before anything is written.
  for location in "${locations[@]}"; do
    [[ ! -e $location ]] || { echo 'One mail per second; send it again in a moment.'; exit 1; }
  done
  # noclobber: an existing mail is never overwritten, not even in a race.
  set -o noclobber
  stamp=$(timestamp)
  for location in "${locations[@]}"; do
    printf '%s\nFrom: %s\nTo: %s\n%s\n' "$stamp" "$seat_name" "$target_seat_name" "$mail_text" > "$location"
  done
  reached_count=$(( ${#locations[@]} - 1 ))
  if (( reached_count == 1 )); then echo "To $target_seat_name: 1 member reached."; else echo "To $target_seat_name: $reached_count members reached."; fi
  throttle
}

join_group() {
  local member
  local -a members=()
  read_members "$target_seat_name"
  for member in "${members[@]}"; do
    if [[ $member == "$seat_name" ]]; then echo "$seat_name is already in $target_seat_name."; return 0; fi
  done
  members+=("$seat_name")
  write_members
  echo "$seat_name joined $target_seat_name: ${#members[@]} members."
  throttle
}

leave_group() {
  local member was_member=''
  local -a members=() staying=()
  read_members "$target_seat_name"
  for member in "${members[@]}"; do
    if [[ $member == "$seat_name" ]]; then was_member=yes; else staying+=("$member"); fi
  done
  if [[ -z $was_member ]]; then echo "$seat_name is not in $target_seat_name."; return 0; fi
  members=("${staying[@]}")
  write_members
  echo "$seat_name left $target_seat_name: ${#members[@]} members."
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
    # Terminal mode never gets here: its watcher stays until the terminal is gone.
    jitter
    leave_awake_marker
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
    # A group mail reaches every member, so it has a verb of its own; a seat of the same name still goes first.
    if [[ -n $target_seat_name && ! -f $hrafnsmal_location/$target_seat_name/README.md && -f $group_chat_location/$target_seat_name/MEMBERS.txt ]]; then
      echo "$target_seat_name is a group: a mail there reaches every member. Use group."; exit 1
    fi
    check_seat "$target_seat_name"
    shift 3
    mail_text=$*
    send_mail
    ;;
  group)
    target_seat_name=$3
    check_seat "$seat_name"
    check_group "$target_seat_name"
    shift 3
    mail_text=$*
    send_group
    ;;
  join|leave)
    target_seat_name=$3
    check_seat "$seat_name"
    check_group "$target_seat_name"
    if [[ $verb == join ]]; then join_group; else leave_group; fi
    ;;
# exit shares the line with esac, so bash parses it before running and never reads a script that changed meanwhile.
esac; exit

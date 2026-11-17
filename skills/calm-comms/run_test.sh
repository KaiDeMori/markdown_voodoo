#!/usr/bin/env bash
ng_location='c:/Users/devboese/markdown_voodoo/skills/calm-comms'
test_location='c:/Users/devboese/markdown_voodoo/scratchpad/calm_comms_NG_test'
install_location="$test_location/install"
refusal_location="$test_location/refusal_install"
haven="$test_location/test_haven"
hrafnsmal="$haven/Hall/thing/Hrafnsmal"
group_chat="$haven/Hall/thing/group_chat"
rm -rf "$haven" "$install_location" "$refusal_location" "$test_location"/*.txt
for seat in huginn muninn corvus; do mkdir -p "$hrafnsmal/$seat"; echo "# $seat" > "$hrafnsmal/$seat/README.md"; done
mkdir -p "$group_chat/ravens/members"
: > "$group_chat/ravens/members/huginn"
: > "$group_chat/ravens/members/muninn"
write_settings() {
  cat <<EOF
{
  "haven_location": "$1",
  "read_mail_kept_days": 7,
  "poll_interval_seconds": 10,
  "long_watcher_minutes": 55,
  "short_watcher_minutes": 4,
  "awake_grace_minutes": 5,
  "inbox_mail_limit": 3,
  "inbox_size_limit_kilobytes": 10,
  "write_throttle_seconds": 2
}
EOF
}
install_calm_comms() {
  mkdir -p "$1"
  cp "$ng_location/calm_comms.exe" "$ng_location/calm_comms.sh" "$1/"
}
install_calm_comms "$install_location"
write_settings "$haven" > "$install_location/calm_comms_settings.json"
exe="$install_location/calm_comms.exe"
calm_comms() { bash "$install_location/calm_comms.sh" "$@"; }

run() {
  echo "\$ calm_comms $*"
  calm_comms "$@" 2>&1 | sed 's/^/  /'
  echo "  exit ${PIPESTATUS[0]}"
}
seconds_between() { awk -v start="$1" -v end="$2" 'BEGIN { printf "%.3f", end - start }'; }

echo '--- 1 send'
run send muninn huginn 'Hello, huginn!'
sed 's/^/    | /' "$hrafnsmal/huginn"/*_from_muninn.md

echo '--- 2 inbox'
run inbox huginn
ls "$hrafnsmal/huginn/already_read" | sed 's/^/    already_read: /'

echo '--- 3 join'
run join corvus ravens

echo '--- 4 group'
run group huginn ravens 'Hello, ravens!'
find "$haven" -name '*_from_huginn.md' | sed "s|^$haven/|    |"

echo '--- 5 leave'
run leave corvus ravens

echo '--- 6 overview'
run overview
echo "  the bytes of the first line: $(calm_comms overview | head -n 1 | od -An -tx1 | tr -s ' \n' ' ')"

echo '--- 7 wake'
calm_comms send corvus huginn 'An older mail, unread.' > /dev/null
( sleep 3; echo "$EPOCHREALTIME" > "$test_location/send_time.txt"; calm_comms send muninn huginn 'Wake up, huginn!' > "$test_location/send_7.txt" 2>&1 ) &
sender_pid=$!
line_time=''
while IFS= read -r line; do
  if [[ $line == *' mail: '* ]]; then line_time=$EPOCHREALTIME; fi
  echo "  watcher: $line"
done < <(calm_comms on huginn short; echo "exit $?")
exit_time=$EPOCHREALTIME
wait "$sender_pid"
send_time=$(< "$test_location/send_time.txt")
echo "  the send to the watched seat said: $(< "$test_location/send_7.txt")"
echo "  from the send to the mail line: $(seconds_between "$send_time" "$line_time") s"
echo "  from the mail line to the exit: $(seconds_between "$line_time" "$exit_time") s"
run overview

echo '--- 8 off'
calm_comms inbox corvus > /dev/null
( calm_comms on corvus short > "$test_location/watch_8.txt" 2>&1; echo "$? $EPOCHREALTIME" > "$test_location/exit_8.txt" ) &
watcher_pid=$!
sleep 2
run overview
off_start=$EPOCHREALTIME
run off corvus
wait "$watcher_pid"
read -r watcher_exit watcher_exit_time < "$test_location/exit_8.txt"
echo "  watcher: exit $watcher_exit, $(seconds_between "$off_start" "$watcher_exit_time") s after off began, said: $(< "$test_location/watch_8.txt")"
run overview

echo '--- 9 takeover'
( calm_comms on muninn short > "$test_location/watch_9a.txt" 2>&1; echo "$? $EPOCHREALTIME" > "$test_location/exit_9a.txt" ) &
first_pid=$!
sleep 2
takeover_start=$EPOCHREALTIME
calm_comms on muninn short > "$test_location/watch_9b.txt" 2>&1 &
second_pid=$!
wait "$first_pid"
read -r first_exit first_exit_time < "$test_location/exit_9a.txt"
echo "  first watcher: exit $first_exit, $(seconds_between "$takeover_start" "$first_exit_time") s after the second on began, said: $(< "$test_location/watch_9a.txt")"
sleep 1
run overview
run off muninn
wait "$second_pid"
echo "  second watcher: exit $?, said: $(tr '\n' ' ' < "$test_location/watch_9b.txt")"

echo '--- 10 no seat'
run send nobody huginn 'Hello?'

echo '--- 11 refusals'
run fly
run inbox huginn many
run group huginn nogroup 'Hello?'
run send huginn ravens 'Hello?'
run group corvus ravens 'May I?'
run on huginn sometimes

echo '--- 12 text beyond ASCII'
calm_comms inbox corvus > /dev/null
text=$'Grüße von Ⓦ, mit 📬 und ß.\n/ok: a second line, with a slash first.'
calm_comms send muninn corvus "$text" > /dev/null
received=$(tail -n +4 "$hrafnsmal/corvus"/*_from_muninn.md)
if [[ $received == "$text" ]]; then echo '  through calm_comms.sh, the text arrived exactly as sent'; else echo "  through calm_comms.sh, the text changed: $received"; fi
calm_comms inbox corvus | sed 's/^/  /'
sleep 1
"$exe" send muninn corvus '/ok' > /dev/null
echo "  straight into the exe, /ok arrived as: $(tail -n +4 "$hrafnsmal/corvus"/*_from_muninn.md)"

echo '--- 13 inbox beyond its limits'
calm_comms inbox corvus > /dev/null
calm_comms send huginn corvus 'Small one.' > /dev/null
calm_comms send muninn corvus 'Small two.' > /dev/null
calm_comms send huginn corvus 'Small three.' > /dev/null
calm_comms send muninn corvus 'Small four.' > /dev/null
{ printf '%s\n' '2026-10-27T02:00+01:00' 'From: huginn' 'To: corvus'; head -c 12000 /dev/zero | tr '\0' 'x'; echo; } > "$hrafnsmal/corvus/from_huginn_big.md"
for call in 1 2 3; do
  echo "  inbox, call $call:"
  calm_comms inbox corvus | grep -E '^--- |waiting|^no mail' | sed 's/^/    /'
done

echo '--- 14 overview groups'
run overview groups
run overview groups ravens
run overview groups nogroup
run overview ravens

echo '--- 15 archive'
calm_comms inbox huginn 100 > /dev/null
mkdir -p "$hrafnsmal/huginn/already_read"
echo 'Old and unread: stays.' > "$hrafnsmal/huginn/2026-01-05_100000_from_muninn.md"
echo 'Old and read: moves.' > "$hrafnsmal/huginn/already_read/2026-01-04_100000_from_corvus.md"
echo 'Old, read, without a stamp: moves by its file time.' > "$hrafnsmal/huginn/already_read/a_note_without_a_stamp.md"
touch -d '2026-03-01 12:00' "$hrafnsmal/huginn/already_read/a_note_without_a_stamp.md"
echo 'Read by every member: moves.' > "$group_chat/ravens/2026-02-01_090000_from_huginn.md"
echo 'Still unread at muninn: stays.' > "$group_chat/ravens/2026-02-02_090000_from_huginn.md"
cp "$group_chat/ravens/2026-02-02_090000_from_huginn.md" "$hrafnsmal/muninn/"
echo 'Read by every member, but 2 days old: stays.' > "$group_chat/ravens/$(date -d '2 days ago' '+%Y-%m-%d_%H%M%S')_from_huginn.md"
run inbox corvus 0
echo '  in the archive:'
find "$haven/archive" -type f | sort | sed "s|^$haven/|    |"
echo '  muninn reads its copies; the next call moves the thread messages older than 7 days:'
calm_comms inbox muninn 100 > /dev/null
calm_comms inbox corvus 0 > /dev/null
find "$haven/archive" -type f | sort | sed "s|^$haven/|    |"
echo '  still in the hall:'
ls "$hrafnsmal/huginn" | sed 's/^/    huginn: /'
ls "$group_chat/ravens" | sed 's/^/    ravens: /'

echo '--- 16 settings'
install_calm_comms "$refusal_location"
settings_file="$refusal_location/calm_comms_settings.json"
try_settings() {
  echo "  $1:"
  bash "$refusal_location/calm_comms.sh" overview 2>&1 | sed "s|$refusal_location/||I; s/^/    /"
  echo "    exit ${PIPESTATUS[0]}"
}
try_settings 'no settings file'
write_settings "$haven" | sed 's/"read_mail_kept_days": 7,/"read_mail_kept_days": 7/' > "$settings_file"
try_settings 'a missing comma'
echo '[]' > "$settings_file"
try_settings 'an array'
{ write_settings "$haven"; echo '{}'; } > "$settings_file"
try_settings 'a second JSON value'
write_settings "$haven" | sed '/long_watcher_minutes/d; s/"poll_interval_seconds": 10/"poll_interval_seconds": 0/; s/"inbox_mail_limit": 3/"inbox_mail_limit": 2.5/; s/"write_throttle_seconds": 2/"write_throttle_seconds": 2,\n  "colour": "blue",\n  "write_throttle_seconds": 3/' > "$settings_file"
try_settings 'five issues in one file'
write_settings "$haven" | sed 's|"haven_location": "[^"]*"|"haven_location": null|' > "$settings_file"
try_settings 'haven_location null'
write_settings 'test_haven' > "$settings_file"
try_settings 'a relative haven_location'
write_settings "$test_location" > "$settings_file"
try_settings 'a haven_location without Hall/thing/Hrafnsmal'
{ printf '\xef\xbb\xbf'; write_settings "$haven"; } > "$settings_file"
try_settings 'a byte order mark before a valid file'

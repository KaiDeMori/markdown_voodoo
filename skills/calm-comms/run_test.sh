#!/usr/bin/env bash
# Runs calm-comms in a test haven of its own, through calm_comms.sh as ravens do, so the live hall never sees a test.
# calm_comms_haven_location points the exe at the test haven.
ng_location='c:/Users/devboese/markdown_voodoo/skills/calm-comms'
# The test haven is temporary, so it lives in the scratchpad.
test_location='c:/Users/devboese/markdown_voodoo/scratchpad/calm_comms_NG_test'
haven="$test_location/test_haven"
hrafnsmal="$haven/Hall/thing/Hrafnsmal"
group_chat="$haven/Hall/thing/group_chat"
rm -rf "$haven" "$test_location"/*.txt
for seat in huginn muninn corvus; do mkdir -p "$hrafnsmal/$seat"; echo "# $seat" > "$hrafnsmal/$seat/README.md"; done
mkdir -p "$group_chat/ravens/members"
: > "$group_chat/ravens/members/huginn"
: > "$group_chat/ravens/members/muninn"
export calm_comms_haven_location="$haven"
exe="$ng_location/calm_comms.exe"
calm_comms() { bash "$ng_location/calm_comms.sh" "$@"; }

run() {
  echo "\$ calm_comms $*"
  calm_comms "$@" 2>&1 | sed 's/^/  /'
  echo "  exit ${PIPESTATUS[0]}"
}
seconds_between() { awk -v start="$1" -v end="$2" 'BEGIN { printf "%.3f", end - start }'; }

echo '--- 1 send'
run send muninn huginn 'Hello, huginn!'
sed 's/^/    | /' "$hrafnsmal/huginn"/from_muninn_*.md

echo '--- 2 inbox'
run inbox huginn
ls "$hrafnsmal/huginn/already_read" | sed 's/^/    already_read: /'

echo '--- 3 join'
run join corvus ravens

echo '--- 4 group'
run group huginn ravens 'Hello, ravens!'
find "$haven" -name 'from_huginn_*' | sed "s|^$haven/|    |"

echo '--- 5 leave'
run leave corvus ravens

echo '--- 6 overview'
run overview
echo "  the bytes of the first line: $(calm_comms overview | head -n 1 | od -An -tx1 | tr -s ' \n' ' ')"

echo '--- 7 wake'
# An older mail lands before the watcher starts, so it counts as already there and wakes nobody.
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
received=$(tail -n +4 "$hrafnsmal/corvus"/from_muninn_*.md)
if [[ $received == "$text" ]]; then echo '  through calm_comms.sh, the text arrived exactly as sent'; else echo "  through calm_comms.sh, the text changed: $received"; fi
calm_comms inbox corvus | sed 's/^/  /'
# Straight into the exe from Git Bash, without calm_comms.sh: what the wrapper prevents.
sleep 1
"$exe" send muninn corvus '/ok' > /dev/null
echo "  straight into the exe, /ok arrived as: $(tail -n +4 "$hrafnsmal/corvus"/from_muninn_*.md)"

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

#!/usr/bin/env bash
# Runs NG's freshly built exe in a test haven of its own, so neither the live hall nor the goer's test_haven sees a test.
# The exe looks for test_haven next to itself, so a copy of it here gets a haven of its own.
ng_location='c:/Users/devboese/markdown_voodoo/notebook/calm_comms_NG'
# The test haven is temporary, so it lives in the scratchpad.
test_location='c:/Users/devboese/markdown_voodoo/scratchpad/calm_comms_NG_test'
haven="$test_location/test_haven"
hrafnsmal="$haven/Hall/thing/Hrafnsmal"
group_chat="$haven/Hall/thing/group_chat"
rm -rf "$haven" "$test_location"/*.txt "$test_location/calm_comms.exe"
for seat in huginn muninn corvus; do mkdir -p "$hrafnsmal/$seat"; echo "# $seat" > "$hrafnsmal/$seat/README.md"; done
mkdir -p "$group_chat/ravens/members"
: > "$group_chat/ravens/members/huginn"
: > "$group_chat/ravens/members/muninn"
cp "$ng_location/calm_comms.exe" "$test_location/calm_comms.exe"
exe="$test_location/calm_comms.exe"

run() {
  echo "\$ calm_comms $*"
  "$exe" "$@" 2>&1 | sed 's/^/  /'
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
echo "  the bytes of the first line: $("$exe" overview | head -n 1 | od -An -tx1 | tr -s ' \n' ' ')"

echo '--- 7 wake'
# An older mail lands before the watcher starts, so it counts as already there and wakes nobody.
"$exe" send corvus huginn 'An older mail, unread.' > /dev/null
( sleep 3; echo "$EPOCHREALTIME" > "$test_location/send_time.txt"; "$exe" send muninn huginn 'Wake up, huginn!' > "$test_location/send_7.txt" 2>&1 ) &
sender_pid=$!
line_time=''
while IFS= read -r line; do
  if [[ $line == *' mail: '* ]]; then line_time=$EPOCHREALTIME; fi
  echo "  watcher: $line"
done < <("$exe" on huginn short; echo "exit $?")
exit_time=$EPOCHREALTIME
wait "$sender_pid"
send_time=$(< "$test_location/send_time.txt")
echo "  the send to the watched seat said: $(< "$test_location/send_7.txt")"
echo "  from the send to the mail line: $(seconds_between "$send_time" "$line_time") s"
echo "  from the mail line to the exit: $(seconds_between "$line_time" "$exit_time") s"
run overview

echo '--- 8 off'
"$exe" inbox corvus > /dev/null
( "$exe" on corvus short > "$test_location/watch_8.txt" 2>&1; echo "$? $EPOCHREALTIME" > "$test_location/exit_8.txt" ) &
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
( "$exe" on muninn short > "$test_location/watch_9a.txt" 2>&1; echo "$? $EPOCHREALTIME" > "$test_location/exit_9a.txt" ) &
first_pid=$!
sleep 2
takeover_start=$EPOCHREALTIME
"$exe" on muninn short > "$test_location/watch_9b.txt" 2>&1 &
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

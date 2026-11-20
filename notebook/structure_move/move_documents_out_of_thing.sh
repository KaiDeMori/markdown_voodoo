#!/usr/bin/env bash
# Moves every visible entry in haven:/Hall/thing/ except Hrafnsmal/ and group_chat/ into haven:/Hall/<room_name>/.
# It moves nothing when a name already exists in the room, and nothing without a typed yes.
# Usage: move_documents_out_of_thing.sh <haven_location> <room_name>

set -u
shopt -s nullglob

if (( $# != 2 )); then echo 'move_documents_out_of_thing.sh <haven_location> <room_name>?'; exit 1; fi
haven_location=$1
room_name=$2
thing_location="$haven_location/Hall/thing"
room_location="$haven_location/Hall/$room_name"

if [[ ! -d $thing_location/Hrafnsmal || ! -d $thing_location/group_chat ]]; then
  echo "$thing_location has no Hrafnsmal/ and group_chat/."
  exit 1
fi
case $room_name in
  ''|.|..|thing|*/*|*\\*) echo "\"$room_name\" is no name for the documents room."; exit 1 ;;
esac

entry_names=()
for entry_location in "$thing_location"/*; do
  entry_name=${entry_location##*/}
  if [[ $entry_name != Hrafnsmal && $entry_name != group_chat ]]; then entry_names+=("$entry_name"); fi
done
if (( ${#entry_names[@]} == 0 )); then echo 'Nothing to move: thing/ holds only Hrafnsmal/ and group_chat/.'; exit 0; fi

clashing_names=()
for entry_name in "${entry_names[@]}"; do
  if [[ -e $room_location/$entry_name ]]; then clashing_names+=("$entry_name"); fi
done
if (( ${#clashing_names[@]} > 0 )); then
  echo "Already in haven:/Hall/$room_name/, so nothing moves:"
  printf '  %s\n' "${clashing_names[@]}"
  exit 1
fi

echo "From haven:/Hall/thing/ into haven:/Hall/$room_name/:"
printf '  %s\n' "${entry_names[@]}"
read -r -p "Move these ${#entry_names[@]} entries? Type yes: " answer
if [[ $answer != yes ]]; then echo 'Nothing moved.'; exit 1; fi

mkdir -p "$room_location" || exit 1
moved_count=0
for entry_name in "${entry_names[@]}"; do
  if mv -n "$thing_location/$entry_name" "$room_location/$entry_name" && [[ -e $room_location/$entry_name && ! -e $thing_location/$entry_name ]]; then
    moved_count=$((moved_count + 1))
  else
    echo "Not moved: $entry_name"
  fi
done
echo "Moved $moved_count of ${#entry_names[@]} entries into haven:/Hall/$room_name/."
echo 'Left in haven:/Hall/thing/:'
ls -A "$thing_location" | sed 's/^/  /'

#!/usr/bin/env bash
# calm_hall_overview: shows the hall as far as hall_overview_visibility.txt, beside this script, lets it.
# open: the room's files, and the rooms inside it.
# not all at once: only how many files the room holds.
# not yet, not mine: only the room and its word.
# A room without a line: only its name.
# Usage: calm_hall_overview.sh [seat_name]

script_folder=$(dirname "${BASH_SOURCE[0]}")
haven_location=$(python "$script_folder/read_haven_location.py" "$script_folder/calm_hall_overview_settings.json") || { echo "$haven_location"; exit 1; }
hall_location="$haven_location/Hall"
visibility_file_location="$script_folder/hall_overview_visibility.txt"

if (( $# > 1 )); then echo 'calm-hall-overview [seat_name]?'; exit 1; fi
seat_name=${1:-}
if [[ -n $seat_name ]]; then
  case $seat_name in
    */*|*\\*|*\**|*\?*|*\[*) seat_name_is_valid=false ;;
    *) seat_name_is_valid=true ;;
  esac
  if [[ $seat_name_is_valid == false || ! -f $hall_location/thing/Hrafnsmal/$seat_name/README.md ]]; then
    echo "Quoth the raven: README in $seat_name? Nevermore."
    exit 1
  fi
fi
placeholder_pattern='*[<>]*'

set -e
shopt -s nullglob

room_patterns=()
room_words=()

read_visibility() {
  local line line_number=0 room_pattern room_word
  [[ -f $visibility_file_location ]] || { echo "No $visibility_file_location, so the hall stays unseen."; exit 1; }
  while IFS= read -r line || [[ -n $line ]]; do
    line_number=$((line_number + 1))
    line=${line%$'\r'}
    if [[ $line =~ ^[[:space:]]*(#|$) ]]; then continue; fi
    # Windows never allows a colon in a name, so the last one separates the room from its word.
    read -r room_pattern <<< "${line%:*}"
    read -r room_word <<< "${line##*:}"
    case $room_word in
      open|'not all at once'|'not yet'|'not mine') ;;
      *) room_word='' ;;
    esac
    if [[ $line != *:* || -z $room_pattern || -z $room_word ]]; then
      echo "hall_overview_visibility.txt, line $line_number: \"$line\" needs a room, a colon, and open, not all at once, not yet or not mine."
      exit 1
    fi
    if [[ ${room_pattern//'<seat_name>'/} == $placeholder_pattern ]]; then
      echo "hall_overview_visibility.txt, line $line_number: \"$line\" uses a placeholder other than <seat_name>."
      exit 1
    fi
    room_patterns+=("$room_pattern")
    room_words+=("$room_word")
  done < "$visibility_file_location"
}

find_word() {
  # The last line that matches the room decides.
  local index room_pattern
  room_word=$2
  for index in "${!room_patterns[@]}"; do
    room_pattern=${room_patterns[index]}
    if [[ $room_pattern == *'<seat_name>'* ]]; then
      [[ -n $seat_name ]] || continue
      room_pattern=${room_pattern//'<seat_name>'/$seat_name}
    fi
    if [[ $1 == $room_pattern ]]; then room_word=${room_words[index]}; fi
  done
}

count_files() {
  local file_count
  file_count=$(find "$1" -type f ! -path '*/.*' | wc -l)
  if (( file_count == 1 )); then echo '1 file'; else echo "$file_count files"; fi
}

show_room() {
  local room_path=$1 room_location=$2 room_label=$3 indent=$4 entry_location
  find_word "$room_path" "$5"
  case $room_word in
    open)
      echo "$indent$room_label"
      for entry_location in "$room_location"/*; do
        if [[ -f $entry_location ]]; then echo "$indent  ${entry_location##*/}"; fi
      done
      for entry_location in "$room_location"/*/; do
        entry_location=${entry_location%/}
        show_room "${entry_location#"$hall_location"/}" "$entry_location" "${entry_location##*/}/" "$indent  " unlisted
      done
      ;;
    unlisted) echo "$indent$room_label" ;;
    'not all at once') echo "$indent$room_label: not all at once, $(count_files "$room_location")" ;;
    'not yet'|'not mine') echo "$indent$room_label: $room_word" ;;
    '') echo "$indent$room_label: no line in hall_overview_visibility.txt" ;;
  esac
}

read_visibility
show_room . "$hall_location" 'haven:/Hall/' '' ''

#!/usr/bin/env bash
# Moves the haven into its new structure in four steps:
# 1. Every visible entry in Hall/thing/ besides Hrafnsmal/ and group_chat/ moves into Hall/album/.
# 2. Hall/thing/ becomes Hall/agora/.
# 3. Hall/agora/Hrafnsmal/ becomes Hall/agora/hall_mail/.
# 4. Every archive/<YYYY-MM>/mail/ becomes archive/<YYYY-MM>/hall_mail/; where both exist, their seats merge.
# A finished step is skipped, so a stopped run can run again once its cause is fixed.
# A running watcher keeps its seat open, so every watcher is off before the run.
# Usage: move_to_the_new_structure.sh <haven_location>

set -u
shopt -s nullglob

if (( $# != 1 )); then echo 'move_to_the_new_structure.sh <haven_location>?'; exit 1; fi
haven_location=$1
hall_location="$haven_location/Hall"
archive_location="$haven_location/archive"
if [[ ! -d $hall_location ]]; then echo "$hall_location does not exist."; exit 1; fi

stop() {
  echo "Stopped: $1"
  echo 'Fix it, then run the script again; finished steps are skipped.'
  exit 1
}

move_entry() {
  mv -n "$1" "$2" && [[ -e $2 && ! -e $1 ]]
}

echo "The move in $haven_location:"
echo '  1. Hall/thing/ besides Hrafnsmal/ and group_chat/ into Hall/album/'
echo '  2. Hall/thing/ becomes Hall/agora/'
echo '  3. Hall/agora/Hrafnsmal/ becomes Hall/agora/hall_mail/'
echo '  4. archive/<YYYY-MM>/mail/ becomes archive/<YYYY-MM>/hall_mail/'
read -r -p 'Is every watcher off, and should the move start? Type yes: ' answer
if [[ $answer != yes ]]; then echo 'Nothing moved.'; exit 1; fi

echo '--- 1. into Hall/album/'
if [[ -d $hall_location/thing ]]; then
  entry_names=()
  for entry_location in "$hall_location/thing"/*; do
    entry_name=${entry_location##*/}
    if [[ $entry_name != Hrafnsmal && $entry_name != group_chat ]]; then entry_names+=("$entry_name"); fi
  done
  for entry_name in "${entry_names[@]}"; do
    if [[ -e $hall_location/album/$entry_name ]]; then stop "Hall/album/$entry_name already exists."; fi
  done
  mkdir -p "$hall_location/album" || stop 'Hall/album/ could not be created.'
  for entry_name in "${entry_names[@]}"; do
    move_entry "$hall_location/thing/$entry_name" "$hall_location/album/$entry_name" || stop "Hall/thing/$entry_name did not move."
  done
  echo "  moved: ${#entry_names[@]}"
else
  echo '  skipped: Hall/thing/ no longer exists'
fi

echo '--- 2. Hall/thing/ becomes Hall/agora/'
if [[ -d $hall_location/thing && -e $hall_location/agora ]]; then stop 'Hall/thing/ and Hall/agora/ both exist.'; fi
if [[ -d $hall_location/thing ]]; then
  move_entry "$hall_location/thing" "$hall_location/agora" || stop 'Hall/thing/ did not become Hall/agora/; a running watcher keeps it open.'
  echo '  done'
elif [[ -d $hall_location/agora ]]; then
  echo '  skipped: Hall/agora/ exists'
else
  stop 'neither Hall/thing/ nor Hall/agora/ exists.'
fi

echo '--- 3. Hall/agora/Hrafnsmal/ becomes Hall/agora/hall_mail/'
if [[ -d $hall_location/agora/Hrafnsmal && -e $hall_location/agora/hall_mail ]]; then stop 'Hall/agora/Hrafnsmal/ and Hall/agora/hall_mail/ both exist.'; fi
if [[ -d $hall_location/agora/Hrafnsmal ]]; then
  move_entry "$hall_location/agora/Hrafnsmal" "$hall_location/agora/hall_mail" || stop 'Hall/agora/Hrafnsmal/ did not become Hall/agora/hall_mail/; a running watcher keeps it open.'
  echo '  done'
elif [[ -d $hall_location/agora/hall_mail ]]; then
  echo '  skipped: Hall/agora/hall_mail/ exists'
else
  stop 'neither Hall/agora/Hrafnsmal/ nor Hall/agora/hall_mail/ exists.'
fi

echo '--- 4. archive/<YYYY-MM>/mail/ becomes archive/<YYYY-MM>/hall_mail/'
renamed_count=0
merged_count=0
kept_files=()
for mail_location in "$archive_location"/*/mail; do
  month_location=${mail_location%/mail}
  if [[ ! -e $month_location/hall_mail ]]; then
    move_entry "$mail_location" "$month_location/hall_mail" || stop "${mail_location#"$haven_location"/} did not become hall_mail/."
    renamed_count=$((renamed_count + 1))
    continue
  fi
  for file_location in "$mail_location"/*/*; do
    seat_and_file=${file_location#"$mail_location"/}
    mkdir -p "$month_location/hall_mail/${seat_and_file%%/*}"
    if [[ -e $month_location/hall_mail/$seat_and_file ]]; then
      kept_files+=("${file_location#"$haven_location"/}")
    else
      move_entry "$file_location" "$month_location/hall_mail/$seat_and_file" || stop "${file_location#"$haven_location"/} did not move."
      merged_count=$((merged_count + 1))
    fi
  done
  for seat_location in "$mail_location"/*/; do rmdir "$seat_location" 2>/dev/null; done
  rmdir "$mail_location" 2>/dev/null
done
echo "  renamed: $renamed_count, files merged into an existing hall_mail/: $merged_count"
if (( ${#kept_files[@]} > 0 )); then
  echo '  kept in mail/, because hall_mail/ holds a file of the same name:'
  printf '    %s\n' "${kept_files[@]}"
fi

echo '--- the hall afterwards'
echo "  Hall/agora/: $(ls "$hall_location/agora" | tr '\n' ' ')"
echo "  Hall/album/: $(ls "$hall_location/album" | wc -l) entries"

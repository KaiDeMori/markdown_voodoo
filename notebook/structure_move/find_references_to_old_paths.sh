#!/usr/bin/env bash
# Lists every line that names an old path: Hrafnsmal, Hall/thing, thing/group_chat, or thing/<name> for an entry of thing/ that moves into album/.
# It searches the haven and every further folder given; Hrafnsmal counts in three spellings, so code names such as hrafnsmal_location and HRAFNSMAL count too.
# Git Bash's grep crashes when -i and -F meet, hence the spellings instead of -i.
# Mail stays as it was written: mail files, already_read/ and archive/ are not searched, and neither is scratchpad/; the READMEs of seats and groups are.
# Usage: find_references_to_old_paths.sh <haven_location> [folder ...]

set -u
shopt -s nullglob

if (( $# < 1 )); then echo 'find_references_to_old_paths.sh <haven_location> [folder ...]?'; exit 1; fi
haven_location=$1
hall_location="$haven_location/Hall"
if [[ ! -d $hall_location ]]; then echo "$hall_location does not exist."; exit 1; fi

searched_texts=(-e 'Hrafnsmal' -e 'hrafnsmal' -e 'HRAFNSMAL' -e 'Hall/thing' -e 'thing/group_chat')
for entry_location in "$hall_location/thing"/* "$hall_location/album"/*; do
  entry_name=${entry_location##*/}
  case $entry_name in Hrafnsmal|group_chat|hall_mail) continue ;; esac
  searched_texts+=(-e "thing/$entry_name")
  if [[ $entry_name == *' '* ]]; then searched_texts+=(-e "thing/${entry_name// /%20}"); fi
done

mail_name_patterns=(--exclude='[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]_from_*' --exclude='from_*')
references=$(grep -rnIF "${searched_texts[@]}" --exclude-dir=.git --exclude-dir=already_read --exclude-dir=archive --exclude-dir=scratchpad "${mail_name_patterns[@]}" "$@")
grep_status=$?
if (( grep_status > 1 )); then echo "grep failed with exit code $grep_status, so the search is incomplete."; exit 1; fi
if [[ -z $references ]]; then echo 'No references to old paths.'; exit 0; fi
printf '%s\n' "$references" | sed "s|^$haven_location/|haven:/|"

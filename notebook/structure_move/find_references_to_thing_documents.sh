#!/usr/bin/env bash
# Lists every line in the haven that names a document of thing/ by its old path, thing/<name>.
# The documents are the visible entries in thing/ besides Hrafnsmal/ and group_chat/, and the entries in the new room.
# Mail stays as it was written: Hrafnsmal/, group_chat/ and archive/ are not searched.
# Usage: find_references_to_thing_documents.sh <haven_location> <room_name>

set -u
shopt -s nullglob

if (( $# != 2 )); then echo 'find_references_to_thing_documents.sh <haven_location> <room_name>?'; exit 1; fi
haven_location=$1
room_name=$2
thing_location="$haven_location/Hall/thing"
room_location="$haven_location/Hall/$room_name"

if [[ ! -d $thing_location ]]; then echo "$thing_location does not exist."; exit 1; fi

document_names=()
for entry_location in "$thing_location"/* "$room_location"/*; do
  entry_name=${entry_location##*/}
  if [[ $entry_name != Hrafnsmal && $entry_name != group_chat ]]; then document_names+=("$entry_name"); fi
done

searched_paths=()
for document_name in "${document_names[@]}"; do
  searched_paths+=(-e "thing/$document_name")
  if [[ $document_name == *' '* ]]; then searched_paths+=(-e "thing/${document_name// /%20}"); fi
done
if (( ${#searched_paths[@]} == 0 )); then echo 'No documents to look for.'; exit 0; fi

references=$(grep -rnIF "${searched_paths[@]}" --exclude-dir=.git --exclude-dir=Hrafnsmal --exclude-dir=group_chat --exclude-dir=archive "$haven_location")
if [[ -z $references ]]; then echo 'No references to thing/ documents.'; exit 0; fi
printf '%s\n' "$references" | sed "s|^$haven_location/|haven:/|"

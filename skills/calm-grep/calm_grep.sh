#!/usr/bin/env bash
# calm_grep: searches a folder's files, starting zoomed out: how many, then where, then what.
# count: how many lines match, in how many files; or nowhere.
# Usage: calm_grep.sh count <pattern> [folder]

noisy_folders=(.git .venv node_modules __pycache__)

verb=$1
pattern=$2
folder=${3:-.}

set -e

exclude_arguments=()
for noisy_folder in "${noisy_folders[@]}"; do exclude_arguments+=("--exclude-dir=$noisy_folder"); done

describe_number() {
  if (( $1 == 1 )); then echo "1 $2"; else echo "$1 ${2}s"; fi
}

count_matches() {
  local line count line_count=0 file_count=0
  # grep -c lists every file with its number of matching lines, 0 included.
  while IFS= read -r line; do
    count=${line##*:}
    if (( count > 0 )); then
      file_count=$((file_count + 1))
      line_count=$((line_count + count))
    fi
  done < <(grep -r -I -s -c -E "${exclude_arguments[@]}" -e "$pattern" -- "$folder" || true)
  if (( file_count == 0 )); then
    echo 'nowhere'
  else
    echo "$(describe_number "$line_count" line) in $(describe_number "$file_count" file)"
  fi
}

if [[ -z $pattern ]]; then echo 'A search needs a pattern.'; exit 1; fi
if [[ ! -e $folder ]]; then echo "No folder or file: $folder"; exit 1; fi
# A broken pattern shows itself on an empty file, before any real search.
pattern_status=0
grep -E -e "$pattern" /dev/null 2> /dev/null || pattern_status=$?
if (( pattern_status == 2 )); then
  grep -E -e "$pattern" /dev/null 2>&1 | head -n 1
  exit 1
fi

case $verb in
  count) count_matches ;;
  *) echo 'count, where or what?'; exit 1 ;;
esac

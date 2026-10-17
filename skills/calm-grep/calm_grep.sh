#!/usr/bin/env bash
# calm_grep: searches a folder's files, starting zoomed out: how many, then where, then what.
# count: how many lines match, in how many files; or nowhere.
# where: each file with the numbers of its matching lines; or nowhere.
# Usage: calm_grep.sh count <pattern> [folder]
#        calm_grep.sh where <pattern> [folder]

noisy_folders=(.git .venv node_modules __pycache__)
where_file_limit=20
where_line_number_limit=10

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

search_matches() {
  # Inside the folder, grep's paths are relative, so no drive letter brings its own colon.
  # -o hands over only the matches, never a whole line, however long it is.
  local target=.
  (
    if [[ -d $folder ]]; then cd "$folder"; else cd "$(dirname "$folder")"; target=$(basename "$folder"); fi
    grep -r -I -s -H -n -o -E "${exclude_arguments[@]}" -e "$pattern" -- "$target" || true
  )
}

show_locations() {
  local line path rest line_number index path_prefix=''
  local -A index_of=()
  local -a paths=() counts=() numbers=() last_numbers=()
  # The folder goes back in front of grep's relative paths, so they work from where the raven stands.
  if [[ -d $folder ]]; then
    if [[ $folder != . ]]; then path_prefix=${folder%/}/; fi
  elif [[ $(dirname "$folder") != . ]]; then
    path_prefix=$(dirname "$folder")/
  fi
  while IFS= read -r line; do
    path=${line%%:*}
    rest=${line#*:}
    line_number=${rest%%:*}
    path=${path#./}
    if [[ -z ${index_of["$path"]} ]]; then
      index_of["$path"]=${#paths[@]}
      paths+=("$path"); counts+=(0); numbers+=(''); last_numbers+=('')
    fi
    index=${index_of["$path"]}
    # A line with several matches is listed once.
    if [[ ${last_numbers[index]} == "$line_number" ]]; then continue; fi
    last_numbers[index]=$line_number
    counts[index]=$(( counts[index] + 1 ))
    if (( counts[index] <= where_line_number_limit )); then
      numbers[index]+=${numbers[index]:+,}$line_number
    fi
  done < <(search_matches)
  if (( ${#paths[@]} == 0 )); then echo 'nowhere'; return; fi
  for index in "${!paths[@]}"; do
    if (( index == where_file_limit )); then
      echo "and $(describe_number $(( ${#paths[@]} - where_file_limit )) 'more file')"
      break
    fi
    line="$path_prefix${paths[index]}:${numbers[index]}"
    if (( counts[index] > where_line_number_limit )); then
      line+=" and $(describe_number $(( counts[index] - where_line_number_limit )) 'more line')"
    fi
    echo "$line"
  done
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
  where) show_locations ;;
  *) echo 'count, where or what?'; exit 1 ;;
esac

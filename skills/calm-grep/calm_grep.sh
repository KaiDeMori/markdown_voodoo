#!/usr/bin/env bash
# calm_grep: searches a folder's files, starting zoomed out: how many, then where, then what.
# count: how many lines match, in how many files; or nowhere.
# where: each file with the numbers of its matching lines; or nowhere.
# what: one file's matching lines, each cut down to the part around its match; or nowhere.
# Usage: calm_grep.sh count <pattern> [folder]
#        calm_grep.sh where <pattern> [folder]
#        calm_grep.sh what <pattern> <file>

noisy_folders=(.git .venv node_modules __pycache__)
where_file_limit=20
where_line_number_limit=10
what_line_limit=10
what_context_width=60

verb=$1
pattern=$2
folder=${3:-.}

set -e

exclude_arguments=()
for noisy_folder in "${noisy_folders[@]}"; do exclude_arguments+=("--exclude-dir=$noisy_folder"); done

describe_number() {
  if (( $1 == 1 )); then echo "1 $2"; else echo "$1 ${2}s"; fi
}

enter_folder() {
  # Inside the folder, grep's paths are relative, so no drive letter brings its own colon.
  if [[ -d $folder ]]; then
    cd "$folder"; target=.
  else
    cd "$(dirname "$folder")"; target=$(basename "$folder")
  fi
}

count_lines_per_file() {
  # grep counts inside itself, and bash only sees the files that matched, as path:count.
  (
    enter_folder
    grep -r -I -s -H -c -E "${exclude_arguments[@]}" -e "$pattern" -- "$target" | grep -v ':0$' || true
  )
}

first_line_numbers() {
  # grep stops after the first lines, and cut keeps only their numbers, however long the lines are.
  (
    enter_folder
    grep -n -m "$where_line_number_limit" -I -s -E -e "$pattern" -- "$1" | cut -d: -f1 | paste -s -d, -
  )
}

count_matches() {
  local line line_count=0 file_count=0
  while IFS= read -r line; do
    file_count=$((file_count + 1))
    line_count=$((line_count + ${line##*:}))
  done < <(count_lines_per_file)
  if (( file_count == 0 )); then
    echo 'nowhere'
  else
    echo "$(describe_number "$line_count" line) in $(describe_number "$file_count" file)"
  fi
}

show_locations() {
  local line path line_count file_count=0 path_prefix=''
  # The folder goes back in front of grep's relative paths, so they work from where the raven stands.
  if [[ -d $folder ]]; then
    if [[ $folder != . ]]; then path_prefix=${folder%/}/; fi
  elif [[ $(dirname "$folder") != . ]]; then
    path_prefix=$(dirname "$folder")/
  fi
  while IFS= read -r line; do
    file_count=$((file_count + 1))
    if (( file_count > where_file_limit )); then continue; fi
    path=${line%:*}
    path=${path#./}
    line_count=${line##*:}
    line="$path_prefix$path:$(first_line_numbers "$path")"
    if (( line_count > where_line_number_limit )); then
      line+=" and $(describe_number $(( line_count - where_line_number_limit )) 'more line')"
    fi
    echo "$line"
  done < <(count_lines_per_file)
  if (( file_count == 0 )); then echo 'nowhere'; fi
  if (( file_count > where_file_limit )); then
    echo "and $(describe_number $(( file_count - where_file_limit )) 'more file')"
  fi
}

cut_around_match() {
  # awk cuts each line down to the part around its match; grep's own colon after the line number stays.
  LC_ALL=C.UTF-8 pattern=$pattern context_width=$what_context_width awk '{
    colon = index($0, ":")
    number = substr($0, 1, colon - 1)
    text = substr($0, colon + 1)
    sub(/\r$/, "", text)
    width = ENVIRON["context_width"] + 0
    if (match(text, ENVIRON["pattern"])) {
      start = RSTART - width
      stop = RSTART + RLENGTH + width
    } else {
      start = 1
      stop = 1 + 2 * width
    }
    if (start < 1) start = 1
    excerpt = substr(text, start, stop - start)
    sub(/^[ \t]+/, "", excerpt)
    print number ": " (start > 1 ? "..." : "") excerpt (stop <= length(text) ? "..." : "")
  }'
}

show_lines() {
  local line_count
  if [[ ! -f $folder ]]; then echo 'what reads one file; where shows which ones.'; exit 1; fi
  line_count=$(grep -c -I -s -E -e "$pattern" -- "$folder" || true)
  if (( line_count == 0 )); then echo 'nowhere'; return; fi
  grep -n -m "$what_line_limit" -I -s -E -e "$pattern" -- "$folder" | cut_around_match
  if (( line_count > what_line_limit )); then
    echo "and $(describe_number $(( line_count - what_line_limit )) 'more line')"
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
  where) show_locations ;;
  what) show_lines ;;
  *) echo 'count, where or what?'; exit 1 ;;
esac

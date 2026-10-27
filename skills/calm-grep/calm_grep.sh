#!/usr/bin/env bash
# calm_grep: searches a folder's files, starting zoomed out: how many, then where, then what.
# count: how many lines match, in how many files; or nowhere.
# where: each file with the numbers of its matching lines; or nowhere.
# what: one file's matching lines, each cut down to the part around its match; or nowhere.
# --lines keeps a search to one line or a span of lines in every file, like 1 or 123-454.
# Usage: calm_grep.sh count [--lines <line|span>] <pattern> [folder]
#        calm_grep.sh where [--lines <line|span>] <pattern> [folder]
#        calm_grep.sh what [--lines <line|span>] <pattern> <file>

noisy_folders=(.git .venv node_modules __pycache__ .pytest_cache .pytest_tmp)
where_file_limit=20
where_line_number_limit=10
what_line_limit=10
what_context_width=60

verb=$1
# --lines comes right after the verb; without it, last_line stays empty, and every line counts.
line_span=''
first_line=''
last_line=''
if [[ ${2:-} == --lines ]]; then
  line_span=${3:-}
  pattern=${4:-}
  folder=${5:-.}
else
  pattern=${2:-}
  folder=${3:-.}
fi

set -e

exclude_arguments=()
for noisy_folder in "${noisy_folders[@]}"; do exclude_arguments+=("--exclude-dir=$noisy_folder"); done

describe_number() {
  if (( $1 == 1 )); then echo "1 $2"; else echo "$1 ${2}s"; fi
}

in_span() {
  # Keeps the lines of grep -n whose line number, in the given field, lies inside the span.
  awk -F: -v field="$1" -v first="$first_line" -v last="$last_line" '$field + 0 >= first + 0 && $field + 0 <= last + 0'
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
  # Within a span, awk counts instead, from grep's numbered lines, in the order grep found the files.
  (
    enter_folder
    if [[ -n $last_line ]]; then
      grep -r -n -I -s -H -E "${exclude_arguments[@]}" -e "$pattern" -- "$target" | in_span 2 | awk -F: '
        !($1 in count) { order[++files] = $1 }
        { count[$1]++ }
        END { for (file_number = 1; file_number <= files; file_number++) print order[file_number] ":" count[order[file_number]] }' || true
    else
      grep -r -I -s -H -c -E "${exclude_arguments[@]}" -e "$pattern" -- "$target" | grep -v ':0$' || true
    fi
  )
}

first_line_numbers() {
  # grep stops after the first lines, and cut keeps only their numbers, however long the lines are.
  # Within a span, grep reads the whole file, and the first lines inside the span are kept.
  (
    enter_folder
    if [[ -n $last_line ]]; then
      grep -n -I -s -E -e "$pattern" -- "$1" | in_span 1 | cut -d: -f1 | head -n "$where_line_number_limit" | paste -s -d, -
    else
      grep -n -m "$where_line_number_limit" -I -s -E -e "$pattern" -- "$1" | cut -d: -f1 | paste -s -d, -
    fi
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
  if [[ -n $last_line ]]; then
    line_count=$(grep -n -I -s -E -e "$pattern" -- "$folder" | in_span 1 | wc -l)
  else
    line_count=$(grep -c -I -s -E -e "$pattern" -- "$folder" || true)
  fi
  if (( line_count == 0 )); then echo 'nowhere'; return; fi
  if [[ -n $last_line ]]; then
    grep -n -I -s -E -e "$pattern" -- "$folder" | in_span 1 | head -n "$what_line_limit" | cut_around_match
  else
    grep -n -m "$what_line_limit" -I -s -E -e "$pattern" -- "$folder" | cut_around_match
  fi
  if (( line_count > what_line_limit )); then
    echo "and $(describe_number $(( line_count - what_line_limit )) 'more line')"
  fi
}

if [[ ${2:-} == --lines ]]; then
  if [[ ! $line_span =~ ^([0-9]+)(-([0-9]+))?$ ]]; then echo '--lines takes one line or a span, like 1 or 123-454.'; exit 1; fi
  first_line=$((10#${BASH_REMATCH[1]}))
  last_line=$((10#${BASH_REMATCH[3]:-${BASH_REMATCH[1]}}))
  if (( first_line > last_line )); then echo "A span runs from its first line to its last, like $last_line-$first_line."; exit 1; fi
fi
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

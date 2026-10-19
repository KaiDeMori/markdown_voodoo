#!/usr/bin/env bash
# calm_find: what kinds of files a folder holds, where they are, and what one of them would cost a window.
# overview: one line with the count of each kind.
# <kind>: the paths of one kind, up to a limit, then how many more.
# what: one fact about one file, the one its kind is about.
# Usage: calm_find.sh [folder]
#        calm_find.sh <kind> [folder]
#        calm_find.sh what <file>
# Kinds: markdown, source, text, images, pdf, other.

list_limit=20
# Below this many bytes a text file is small, and nothing needs counting.
small_bytes=4096
token_counter_location="$HOME/.claude/skills/token-counter/token_counter.sh"
noisy_folders=(.git .venv node_modules __pycache__ .pytest_cache .pytest_tmp)
pdf_jokes=(
  'a photograph of a thought. Ask for the thought.'
  'wonderful, on paper.'
  'Turing-complete. Markdown is not.'
  "Don't panic. Ask for the text instead."
  'a picture of text, wearing a tie.'
  'paper, pretending to be digital, pretending to be paper.'
)

set -e

# A file's kind comes from its extension alone, so nothing is opened to sort it.
classify='
  function kind(path,    name, extension) {
    name = path
    sub(/.*\//, "", name)
    extension = (name ~ /\./) ? tolower(name) : ""
    sub(/.*\./, "", extension)
    if (extension ~ /^(png|jpe?g|gif|webp|svg)$/) return "images"
    if (extension ~ /^(md|markdown)$/) return "markdown"
    if (extension == "pdf") return "pdf"
    if (extension ~ /^(sh|bash|py|js|mjs|cjs|ts|tsx|jsx|cs|java|kt|c|h|cpp|hpp|go|rs|rb|php|ps1|psm1|bat|cmd|html|htm|css|scss|sql|lua)$/) return "source"
    if (extension ~ /^(txt|json|jsonl|csv|tsv|yaml|yml|toml|ini|cfg|conf|log|xml)$/) return "text"
    return "other"
  }'

list_files() {
  # One find for the whole folder; the noisy folders are pruned, never entered.
  local prune=() folder_name
  for folder_name in "${noisy_folders[@]}"; do prune+=(-name "$folder_name" -o); done
  find "$1" \( "${prune[@]:0:${#prune[@]}-1}" \) -prune -o -type f -print
}

show_overview() {
  list_files "$1" | awk "$classify"'
    { counts[kind($0)]++ }
    END {
      split("markdown source text images pdf other", order, " ")
      line = ""
      for (i = 1; i <= 6; i++) {
        count = counts[order[i]]
        if (!count) continue
        label = (order[i] == "images" && count == 1) ? "image" : order[i]
        line = line (line ? " · " : "") count " " label
      }
      print line ? line : "nothing here"
    }'
}

show_kind() {
  list_files "$2" | awk -v wanted="$1" -v limit="$list_limit" "$classify"'
    kind($0) == wanted { if (++count <= limit) print }
    END {
      if (count > limit) print "and " (count - limit) " more"
      if (!count) print "no " wanted
    }'
}

show_what() {
  local file_location=$1 kind extension file_size resolution token_line
  [[ -f $file_location ]] || { echo "what takes one file, and $file_location is none."; exit 1; }
  kind=$(printf '%s\n' "$file_location" | awk "$classify"' { print kind($0) }')
  extension=${file_location##*.}
  extension=${extension,,}
  case $kind in
    images)
      # file names the resolution of png, jpg, gif and webp; the last width x height in its line is the image's own.
      resolution=$(file -b "$file_location" | grep -oE '[0-9]+ ?x ?[0-9]+' | tail -n 1 | tr -d ' ' || true)
      if [[ -n $resolution ]]; then echo "$extension, ${resolution/x/×}"
      elif [[ $extension == svg ]]; then echo 'svg, vector'
      else echo "$extension, resolution unknown"
      fi
      ;;
    markdown|source|text)
      file_size=$(wc -c < "$file_location")
      if (( file_size < small_bytes )); then echo "$kind, small"; return; fi
      # The token counter sends the file to Anthropic and answers with an exact count.
      token_line=$(bash "$token_counter_location" "$file_location" 2> /dev/null || true)
      if [[ $token_line == *' tokens' ]]; then echo "$kind, ${token_line##*: }"; else echo "$kind, tokens unknown"; fi
      ;;
    pdf)
      # Bash is Turing-complete, so the picker is too.
      echo "pdf: ${pdf_jokes[RANDOM % ${#pdf_jokes[@]}]}"
      ;;
    *)
      echo "other, $(file -b "$file_location" | cut -d, -f1)"
      ;;
  esac
}

case ${1:-} in
  what)
    [[ -n ${2:-} ]] || { echo 'what <file>?'; exit 1; }
    show_what "$2"
    ;;
  markdown|source|text|images|pdf|other)
    [[ -d ${2:-.} ]] || { echo "No folder ${2:-.}."; exit 1; }
    show_kind "$1" "${2:-.}"
    ;;
  *)
    [[ -d ${1:-.} ]] || { echo "No folder $1; a kind is markdown, source, text, images, pdf or other."; exit 1; }
    show_overview "${1:-.}"
    ;;
# exit shares the line with esac, so bash parses it before running and never reads a script that changed meanwhile.
esac; exit

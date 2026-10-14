#!/usr/bin/env bash
# calm_git: one calm, read-only look at a repository.
# status: the branch, then clear, or what is changed, new or not pushed.
# Usage: calm_git.sh status [repository_folder]

set -e

verb=$1
repository_location=${2:-.}

show_status() {
  local branch_line status_line status_code branch_name summary ahead_count=0 changed_count=0 new_count=0
  local -a summary_parts=() file_lines=()
  {
    IFS= read -r branch_line
    while IFS= read -r status_line; do
      if [[ $status_line == '?? '* ]]; then
        new_count=$((new_count + 1))
        file_lines+=("  ? ${status_line:3}")
      else
        changed_count=$((changed_count + 1))
        status_code=${status_line:0:2}
        file_lines+=("  ${status_code// /} ${status_line:3}")
      fi
    done
  } < <(git -C "$repository_location" status --porcelain --branch)
  branch_name=${branch_line#'## '}
  branch_name=${branch_name%%...*}
  if [[ $branch_line =~ ahead\ ([0-9]+) ]]; then ahead_count=${BASH_REMATCH[1]}; fi
  if (( changed_count > 0 )); then summary_parts+=("$changed_count changed"); fi
  if (( new_count > 0 )); then summary_parts+=("$new_count new"); fi
  if (( ahead_count == 1 )); then summary_parts+=('1 commit not pushed'); fi
  if (( ahead_count > 1 )); then summary_parts+=("$ahead_count commits not pushed"); fi
  if (( ${#summary_parts[@]} == 0 )); then
    echo "$branch_name: clear"
  else
    summary=$(printf '%s, ' "${summary_parts[@]}")
    echo "$branch_name: ${summary%, }"
    if (( ${#file_lines[@]} > 0 )); then printf '%s\n' "${file_lines[@]}"; fi
  fi
}

case $verb in
  status) show_status ;;
esac

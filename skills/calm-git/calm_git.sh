#!/usr/bin/env bash
# calm_git: one calm, read-only look at the repository of the current folder.
# status: the branch, then clear, or what is changed, new or not pushed.
# recent: the last few commits, each with its timestamp and first line.
# Usage: calm_git.sh status
#        calm_git.sh recent [count]

set -e

recent_commit_count=3

verb=$1

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
  } < <(git status --porcelain --branch)
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

show_recent() {
  local commit_date commit_subject
  git log -"$recent_commit_count" --date=iso-strict --format='%cd%x09%s' | while IFS=$'\t' read -r commit_date commit_subject; do
    # The hall's timestamp: to the minute, with its offset.
    printf '%s   %s\n' "${commit_date:0:16}${commit_date:19}" "$commit_subject"
  done
}

case $verb in
  status) show_status ;;
  recent)
    recent_commit_count=${2:-$recent_commit_count}
    show_recent
    ;;
esac

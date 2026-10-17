#!/usr/bin/env bash
# calm_email: the postmaster's door between the hall and the world, through the haven's mailbox.
# setup: asks for the mailbox password in a real terminal, and writes scratchpad/pwd.txt next to the script.
# list: one line per mail in the mailbox, without marking anything as read.
# Usage: calm_email.sh setup
#        calm_email.sh list

mailbox_address='haven@peopleoftheprompt.org'
imap_location='imaps://mail.manitu.de:993/INBOX'
# A seed of random bytes.
rng_seed='dcbcd6d35fc50d46c27fc8c32356c0d2ec3b2cd55f51416139278b84b3d844093cc6d35ff6b273ba719316078b38af0f11e8192232d5aefff83f148c81c868b6'

verb=$1
script_folder=$(cd "$(dirname "${BASH_SOURCE[0]}")" && { pwd -W 2>/dev/null || pwd; })
# Every folder named scratchpad stays out of git.
pwd_file="$script_folder/scratchpad/pwd.txt"

set -e

setup_password() {
  local password password_hex half='' index
  # Only a real terminal: no raven can start this through a tool, so the password passes through no window.
  if [[ ! -t 0 ]]; then echo 'setup runs only in a real terminal.'; exit 1; fi
  read -r -s -p 'Mailbox password: ' password
  echo
  if [[ -z $password ]]; then echo 'No password, nothing written.'; exit 1; fi
  password_hex=$(printf '%s' "$password" | od -An -tx1 | tr -d ' \n')
  if (( ${#password_hex} > ${#rng_seed} )); then echo 'The password is longer than 64 bytes.'; exit 1; fi
  for (( index = 0; index < ${#password_hex}; index += 2 )); do
    half+=$(printf '%02x' $(( 0x${password_hex:index:2} ^ 0x${rng_seed:index:2} )))
  done
  mkdir -p "${pwd_file%/*}"
  printf '%s\n' "$half" > "$pwd_file"
  echo "pwd.txt is written: $pwd_file"
}

read_password() {
  # The two halves meet only here, in memory.
  local half index hex=''
  if [[ ! -f $pwd_file ]]; then echo 'No scratchpad/pwd.txt yet; Wally runs setup first.'; exit 1; fi
  half=$(<"$pwd_file")
  half=${half//[^0-9a-f]/}
  for (( index = 0; index < ${#half}; index += 2 )); do
    hex+='\x'$(printf '%02x' $(( 0x${half:index:2} ^ 0x${rng_seed:index:2} )))
  done
  printf -v password '%b' "$hex"
}

ask_mailbox() {
  # curl reads the login from stdin, so the password never appears on a command line.
  local quoted=${password//\\/\\\\}
  quoted=${quoted//\"/\\\"}
  printf 'user = "%s:%s"\n' "$mailbox_address" "$quoted" | curl --silent --show-error --config - "$@"
}

list_mails() {
  local mail_lines
  read_password
  # One login and one request: ENVELOPE answers on a single line, and reading it marks nothing as read.
  # Only the sender's domain is shown, so no address enters a window.
  mail_lines=$(ask_mailbox "$imap_location" --request 'FETCH 1:* (RFC822.SIZE ENVELOPE)' | tr -d '\r' | awk '
    function tokenize(line,    i, c, n, token) {
      n = 0; i = 1
      while (i <= length(line)) {
        c = substr(line, i, 1)
        if (c == "(" || c == ")") { tokens[++n] = c; i++ }
        else if (c == " ") { i++ }
        else if (c == "\"") {
          token = "\""; i++
          while (i <= length(line)) {
            c = substr(line, i, 1)
            if (c == "\\") { token = token substr(line, i + 1, 1); i += 2; continue }
            if (c == "\"") { i++; break }
            token = token c; i++
          }
          tokens[++n] = token
        } else {
          token = ""
          while (i <= length(line)) { c = substr(line, i, 1); if (c == " " || c == "(" || c == ")") break; token = token c; i++ }
          tokens[++n] = token
        }
      }
      return n
    }
    function text(token) { return (substr(token, 1, 1) == "\"") ? substr(token, 2) : "" }
    /^\* [0-9]+ FETCH/ {
      delete tokens
      count = tokenize($0)
      size = 0; date = ""; subject = ""; domain = "?"
      for (k = 1; k <= count; k++) {
        if (tokens[k] == "RFC822.SIZE") size = tokens[k + 1] + 0
        if (tokens[k] == "ENVELOPE") {
          date = text(tokens[k + 2]); subject = text(tokens[k + 3])
          # From is a list of addresses (name route mailbox host); only the host is kept.
          if (tokens[k + 4] == "(" && tokens[k + 5] == "(") domain = "@" text(tokens[k + 9])
        }
      }
      size_text = (size < 1024) ? "<1 KB" : int((size + 1023) / 1024) " KB"
      print $2 "  " date "  " domain "  " subject "  (" size_text ")"
    }
  ')
  if [[ -z $mail_lines ]]; then echo 'no mail'; else echo "$mail_lines"; fi
}

case $verb in
  setup) setup_password ;;
  list) list_mails ;;
  *) echo 'setup or list?'; exit 1 ;;
esac

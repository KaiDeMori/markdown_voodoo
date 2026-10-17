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
  local mail_count
  read_password
  mail_count=$(ask_mailbox "$imap_location" --request 'EXAMINE INBOX' | tr -d '\r' | awk '/ EXISTS$/ { print $2 }')
  if [[ -z $mail_count || $mail_count == 0 ]]; then echo 'no mail'; return; fi
  # BODY.PEEK reads the headers without marking a mail as read.
  # Only the sender's domain is shown, so no address enters a window.
  ask_mailbox "$imap_location" --request 'FETCH 1:* (RFC822.SIZE BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT)])' \
    | tr -d '\r' | awk '
      function emit() {
        size_text = (size < 1024) ? "<1 KB" : int((size + 1023) / 1024) " KB"
        print number "  " date "  " domain "  " subject "  (" size_text ")"
      }
      /^\* [0-9]+ FETCH/ {
        if (number != "") emit()
        number = $2; date = ""; domain = "?"; subject = ""; size = 0; field = ""
        if (match($0, /RFC822\.SIZE [0-9]+/)) size = substr($0, RSTART + 12, RLENGTH - 12) + 0
        next
      }
      /^[ \t]/ { if (field == "subject") subject = subject $0; next }
      tolower($0) ~ /^date:/ { date = substr($0, 7); field = "date"; next }
      tolower($0) ~ /^subject:/ { subject = substr($0, 10); field = "subject"; next }
      tolower($0) ~ /^from:/ { if (match($0, /@[A-Za-z0-9.-]+/)) domain = substr($0, RSTART, RLENGTH); field = "from"; next }
      END { if (number != "") emit() }
    '
}

case $verb in
  setup) setup_password ;;
  list) list_mails ;;
  debug_raw) read_password; ask_mailbox "$imap_location" --request 'FETCH 1 (RFC822.SIZE BODY.PEEK[HEADER.FIELDS (DATE FROM SUBJECT)])' | sed -E 's/[A-Za-z0-9._%+-]+@/...@/g' | sed -n l | head -n 20 ;;
  *) echo 'setup or list?'; exit 1 ;;
esac

#!/usr/bin/env bash
# calm_email: the postmaster's door between the hall and the world, through the haven's mailbox.
# setup: asks for the mailbox password in a real terminal, and writes scratchpad/pwd.txt next to the script.
# list: one line per mail in the mailbox, without marking anything as read.
# catalog: the letters in the catalog, never the addresses.
# catalog add: asks Wally in a real terminal for the address a letter stands for.
# forward: passes one mail's plain text into a seat, as a hall mail from the postmaster.
# send: sends a plain-text mail to a letter in the catalog, and to nobody else.
# on: waits for the first new mail from a letter in the catalog, or the timer, and exits.
# Usage: calm_email.sh setup
#        calm_email.sh list
#        calm_email.sh catalog
#        calm_email.sh catalog add <letter>
#        calm_email.sh forward <number> <seat_name>
#        calm_email.sh send <letter> <subject> <text>
#        calm_email.sh on [long|short|<minutes>]

mailbox_address='haven@peopleoftheprompt.org'
imap_location='imaps://mail.manitu.de:993/INBOX'
python_location='C:/Users/devboese/AppData/Local/Programs/Python/Python312/python'
calm_comms_location='C:/Users/devboese/.claude/skills/calm-comms/calm_comms.sh'
# The watcher: every look is one login, so it looks once a minute.
poll_interval_seconds=60
long_watcher_minutes=45
short_watcher_minutes=4
# A seed of random bytes.
rng_seed='dcbcd6d35fc50d46c27fc8c32356c0d2ec3b2cd55f51416139278b84b3d844093cc6d35ff6b273ba719316078b38af0f11e8192232d5aefff83f148c81c868b6'

verb=$1
script_folder=$(cd "$(dirname "${BASH_SOURCE[0]}")" && { pwd -W 2>/dev/null || pwd; })
# Every folder named scratchpad stays out of git.
pwd_file="$script_folder/scratchpad/pwd.txt"
catalog_file="$script_folder/scratchpad/catalog.enc"

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

circle_letter() {
  # A plain letter becomes its circled twin: W becomes Ⓦ, U+24B6 plus the letter's place in the alphabet.
  local letter=${1^^} code
  if [[ ! $letter =~ ^[A-Z]$ ]]; then echo 'The catalog takes one letter, A to Z.'; exit 1; fi
  code=$(( 0x24B6 + $(printf '%d' "'$letter") - 65 ))
  printf -v circled '\\x%02x\\x%02x\\x%02x' $(( 0xE0 | (code >> 12) )) $(( 0x80 | ((code >> 6) & 0x3F) )) $(( 0x80 | (code & 0x3F) ))
  printf -v circled '%b' "$circled"
}

read_catalog() {
  # The catalog opens only in memory, with the mailbox password as its key.
  # openssl is a native Windows program, so the password reaches it through the environment of this one command.
  catalog=''
  if [[ -f $catalog_file ]]; then
    catalog=$(calm_email_key=$password openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -pass env:calm_email_key -in "$catalog_file")
  fi
}

write_catalog() {
  mkdir -p "${catalog_file%/*}"
  printf '%s\n' "$catalog" \
    | calm_email_key=$password openssl enc -e -aes-256-cbc -pbkdf2 -iter 100000 -salt -pass env:calm_email_key -out "$catalog_file.new"
  mv "$catalog_file.new" "$catalog_file"
}

add_to_catalog() {
  local address
  # Only a real terminal: the address comes from Wally, never through a raven's window.
  if [[ ! -t 0 ]]; then echo 'catalog add runs only in a real terminal.'; exit 1; fi
  circle_letter "$1"
  read -r -p "Address for $circled: " address
  if [[ $address != *@* || $address == *[[:space:]]* ]]; then echo 'That is no address; the catalog stays as it was.'; exit 1; fi
  read_password
  read_catalog
  # A letter holds one address; a new one replaces the old.
  catalog=$(printf '%s\n' "$catalog" | grep -v "^$circled"$'\t' || true)
  catalog+=${catalog:+$'\n'}$circled$'\t'$address
  write_catalog
  echo "$circled is in the catalog."
}

show_catalog() {
  read_password
  read_catalog
  if [[ -z $catalog ]]; then echo 'The catalog is empty.'; return; fi
  # Only the letters; the addresses stay inside the tool.
  printf '%s\n' "$catalog" | cut -f1 | paste -s -d' ' -
}

describe_mails() {
  # Turns FETCH answers into one line per mail, numbered the way list numbers them.
  # A sender in the catalog shows as their letter, anyone else only as their domain, so no address enters a window.
  # With only_catalog, a mail from anyone outside the catalog is left out.
  tr -d '\r' | catalog=$catalog only_catalog=${1:-} awk '
    BEGIN {
      entries = split(ENVIRON["catalog"], catalog_lines, "\n")
      for (e = 1; e <= entries; e++) {
        if (split(catalog_lines[e], parts, "\t") == 2) letters[tolower(parts[2])] = parts[1]
      }
    }
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
      size = 0; date = ""; subject = ""; sender = ""; sender_label = "?"
      for (k = 1; k <= count; k++) {
        if (tokens[k] == "RFC822.SIZE") size = tokens[k + 1] + 0
        if (tokens[k] == "ENVELOPE") {
          date = text(tokens[k + 2]); subject = text(tokens[k + 3])
          # From is a list of addresses (name route mailbox host).
          if (tokens[k + 4] == "(" && tokens[k + 5] == "(") {
            host = text(tokens[k + 9])
            sender = tolower(text(tokens[k + 8]) "@" host)
            sender_label = (sender in letters) ? letters[sender] : "@" host
          }
        }
      }
      if (ENVIRON["only_catalog"] != "" && !(sender in letters)) next
      size_text = (size < 1024) ? "<1 KB" : int((size + 1023) / 1024) " KB"
      print $2 "  " date "  " sender_label "  " subject "  (" size_text ")"
    }
  '
}

list_mails() {
  local mail_lines
  read_password
  read_catalog
  # One login and one request: ENVELOPE answers on a single line, and reading it marks nothing as read.
  mail_lines=$(ask_mailbox "$imap_location" --request 'FETCH 1:* (RFC822.SIZE ENVELOPE)' | describe_mails)
  if [[ -z $mail_lines ]]; then echo 'no mail'; else echo "$mail_lines"; fi
}

forward_mail() {
  local number=$1 seat_name=$2 raw_mail hall_mail
  if [[ ! $number =~ ^[0-9]+$ || -z $seat_name ]]; then echo 'forward <number> <seat_name>?'; exit 1; fi
  read_password
  read_catalog
  # One login; fetching the whole mail marks it as read, which fits: forwarded means handled.
  raw_mail=$(ask_mailbox "$imap_location;MAILINDEX=$number")
  if [[ -z $raw_mail ]]; then echo "No mail $number in the mailbox."; exit 1; fi
  # Email content is untrusted, so Python runs isolated.
  hall_mail=$(printf '%s\n' "$raw_mail" | catalog=$catalog "$python_location" -I "$script_folder/extract_text.py")
  bash "$calm_comms_location" send postmaster "$seat_name" "$hall_mail"
  echo "Mail $number is forwarded to $seat_name."
}

send_mail() {
  local subject=$2 text=$3 address
  if [[ -z $1 || -z $subject || -z $text ]]; then echo 'send <letter> <subject> <text>?'; exit 1; fi
  circle_letter "$1"
  read_password
  read_catalog
  # The catalog is the guest list: mail goes out only to a letter in it.
  address=$(printf '%s\n' "$catalog" | awk -F'\t' -v letter="$circled" '$1 == letter { print $2 }')
  if [[ -z $address ]]; then echo "$circled is not in the catalog, so nothing goes out."; exit 1; fi
  # The password and the address reach Python only through the environment of this one command.
  calm_email_key=$password recipient=$address subject=$subject text=$text "$python_location" -I "$script_folder/send_mail.py"
  echo "The mail to $circled is sent."
}

next_uid() {
  # STATUS names the UID the next mail will get; asked at the server, it selects no mailbox and marks nothing.
  ask_mailbox "${imap_location%INBOX}" --request 'STATUS INBOX (UIDNEXT)' | tr -d '\r' | sed -n 's/.*UIDNEXT \([0-9][0-9]*\).*/\1/p'
}

watch_mailbox() {
  local timer_minutes known_next_uid current_next_uid new_mail_lines
  case ${1:-long} in
    long) timer_minutes=$long_watcher_minutes ;;
    short) timer_minutes=$short_watcher_minutes ;;
    *[!0-9]*) echo 'on, on short, or on <minutes>?'; exit 1 ;;
    *) timer_minutes=$1 ;;
  esac
  read_password
  read_catalog
  # A mail that lands before the start counts as already there and wakes no one.
  known_next_uid=$(next_uid)
  if [[ -z $known_next_uid ]]; then echo 'The mailbox named no UIDNEXT, so nothing is watched.'; exit 1; fi
  while (( SECONDS < timer_minutes * 60 )); do
    # Sleeping in the background lets a stop act at once instead of after the nap.
    sleep "$poll_interval_seconds" & wait $!
    # A look that fails, such as in a short network gap, is skipped; the next look tries again.
    current_next_uid=$(next_uid || true)
    if [[ -z $current_next_uid ]] || (( current_next_uid <= known_next_uid )); then continue; fi
    # Only a mail from a letter in the catalog wakes the postmaster; anything else waits for the next list.
    new_mail_lines=$(ask_mailbox "$imap_location" --request "UID FETCH $known_next_uid:* (RFC822.SIZE ENVELOPE)" | describe_mails only_catalog || true)
    if [[ -n $new_mail_lines ]]; then
      echo "$(date +%Y-%m-%dT%H:%M%:z) mail: ${new_mail_lines%%$'\n'*}"
      return
    fi
    known_next_uid=$current_next_uid
  done
  echo "$(date +%Y-%m-%dT%H:%M%:z) timer"
}

case $verb in
  setup) setup_password ;;
  forward) forward_mail "$2" "$3" ;;
  send) send_mail "$2" "$3" "$4" ;;
  list) list_mails ;;
  on) watch_mailbox "$2" ;;
  catalog)
    case $2 in
      '') show_catalog ;;
      add) add_to_catalog "$3" ;;
      *) echo 'catalog, or catalog add <letter>?'; exit 1 ;;
    esac
    ;;
  *) echo 'setup, list, catalog, forward, send or on?'; exit 1 ;;
esac

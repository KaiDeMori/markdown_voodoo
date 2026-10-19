#!/usr/bin/env bash
# calm_email: the postmaster's door between the hall and the world, through the haven's mailbox.
# setup: asks for the mailbox password in a real terminal, and writes scratchpad/pwd.txt next to the script.
# list: one line per mail, with the token count of its plain text, without marking anything as read.
# catalog: the letters in the catalog, never the addresses.
# catalog add: asks Wally in a real terminal for the address a letter stands for; the fernschreiber brings the catalog key and the address on stdin instead.
# catalog remove: asks Wally in a real terminal before a letter leaves the catalog; the fernschreiber brings the catalog key on stdin instead.
# catalog key: makes the key for catalog addresses, shows it to Wally once in a real terminal, and keeps only its hash.
# catalog addresses: with the catalog key on stdin, each letter with its address, for the fernschreiber.
# forward: passes one mail's plain text into a seat, as a hall mail from the postmaster.
# send: sends a plain-text mail to a letter in the catalog, and to nobody else.
# on: waits for the first new mail from a letter in the catalog, or the timer, and exits.
# Usage: calm_email.sh setup
#        calm_email.sh list
#        calm_email.sh catalog
#        calm_email.sh catalog add <letter> [< key, address]
#        calm_email.sh catalog remove <letter> [< key]
#        calm_email.sh catalog key
#        calm_email.sh catalog addresses < key
#        calm_email.sh forward <number> <seat_name>
#        calm_email.sh send <letter> <subject> <text>
#        calm_email.sh on [long|short|<minutes>]

mailbox_address='haven@peopleoftheprompt.org'
imap_location='imaps://mail.manitu.de:993/INBOX'
python_location='C:/Users/devboese/AppData/Local/Programs/Python/Python312/python'
calm_comms_location='C:/Users/devboese/.claude/skills/calm-comms/calm_comms.sh'
# The watcher's timers; the server announces new mail, so nothing polls.
long_watcher_minutes=45
short_watcher_minutes=4
# A seed of random bytes.
rng_seed='dcbcd6d35fc50d46c27fc8c32356c0d2ec3b2cd55f51416139278b84b3d844093cc6d35ff6b273ba719316078b38af0f11e8192232d5aefff83f148c81c868b6'

verb=$1
script_folder=$(cd "$(dirname "${BASH_SOURCE[0]}")" && { pwd -W 2>/dev/null || pwd; })
# Every folder named scratchpad stays out of git.
pwd_file="$script_folder/scratchpad/pwd.txt"
catalog_file="$script_folder/scratchpad/catalog.enc"
catalog_key_hash_file="$script_folder/scratchpad/catalog_key.sha256"

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

check_catalog_key() {
  local key
  # The key comes on the first line of stdin, never on a command line, and only its hash is kept.
  IFS= read -r key || true
  key=${key%$'\r'}
  if [[ ! -f $catalog_key_hash_file || $(printf '%s' "$key" | sha256sum | cut -d' ' -f1) != "$(<"$catalog_key_hash_file")" ]]; then
    echo 'That key opens nothing.'
    exit 1
  fi
}

add_to_catalog() {
  local address
  circle_letter "$1"
  if [[ -t 0 ]]; then
    # Wally in a real terminal: the address comes from Wally's keyboard, never through a raven's window.
    read -r -p "Address for $circled: " address
  else
    # The fernschreiber: the catalog key on the first line, the address on the second, and no questions.
    check_catalog_key
    IFS= read -r address || true
    address=${address%$'\r'}
  fi
  if [[ $address != *@* || $address == *[[:space:]]* ]]; then echo 'That is no address; the catalog stays as it was.'; exit 1; fi
  read_password
  read_catalog
  # In a real terminal a new address replaces the old; the fernschreiber asks before it removes, so a taken letter stays taken.
  if [[ ! -t 0 ]] && printf '%s\n' "$catalog" | grep -q "^$circled"$'\t'; then echo "$circled is taken; the catalog stays as it was."; exit 1; fi
  catalog=$(printf '%s\n' "$catalog" | grep -v "^$circled"$'\t' || true)
  catalog+=${catalog:+$'\n'}$circled$'\t'$address
  write_catalog
  echo "$circled is in the catalog."
}

remove_from_catalog() {
  local answer
  circle_letter "$1"
  # The catalog changes only by Wally's hand: in a real terminal, or through the fernschreiber with the catalog key.
  if [[ ! -t 0 ]]; then check_catalog_key; fi
  read_password
  read_catalog
  if ! printf '%s\n' "$catalog" | grep -q "^$circled"$'\t'; then echo "$circled is not in the catalog."; exit 1; fi
  # The fernschreiber does its own asking.
  if [[ -t 0 ]]; then
    read -r -p "Remove $circled from the catalog? (y/n) " answer
    if [[ $answer != y ]]; then echo 'The catalog stays as it was.'; return; fi
  fi
  catalog=$(printf '%s\n' "$catalog" | grep -v "^$circled"$'\t' || true)
  write_catalog
  echo "$circled is no longer in the catalog."
}

make_catalog_key() {
  local key
  # Only a real terminal: the key goes straight to Wally's eyes, through no window.
  if [[ ! -t 0 ]]; then echo 'catalog key runs only in a real terminal.'; exit 1; fi
  # 32 random bytes as hex: nobody guesses it, and it is pasted, never typed.
  key=$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')
  mkdir -p "${catalog_key_hash_file%/*}"
  printf '%s' "$key" | sha256sum | cut -d' ' -f1 > "$catalog_key_hash_file"
  echo "The catalog key, shown only this once: $key"
  echo 'Paste it into the fernschreiber. Only its hash stays here, and a new key replaces the old one.'
}

show_catalog_addresses() {
  check_catalog_key
  read_password
  read_catalog
  if [[ -z $catalog ]]; then echo 'The catalog is empty.'; return; fi
  # One line per letter: the letter, a tab, the address.
  printf '%s\n' "$catalog"
}

show_catalog() {
  read_password
  read_catalog
  if [[ -z $catalog ]]; then echo 'The catalog is empty.'; return; fi
  # Only the letters; the addresses stay inside the tool.
  printf '%s\n' "$catalog" | cut -f1 | paste -s -d' ' -
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

watch_mailbox() {
  local timer_minutes
  case ${1:-long} in
    long) timer_minutes=$long_watcher_minutes ;;
    short) timer_minutes=$short_watcher_minutes ;;
    *[!0-9]*) echo 'on, on short, or on <minutes>?'; exit 1 ;;
    *) timer_minutes=$1 ;;
  esac
  run_mailbox on "$timer_minutes"
}

run_mailbox() {
  local imap_host=${imap_location#imaps://}
  read_password
  read_catalog
  # The password, the address and the catalog reach mailbox.py only through the environment of this one command.
  # Mail content is untrusted, so Python runs isolated.
  calm_email_key=$password mailbox_address=$mailbox_address imap_host=${imap_host%%[:/]*} catalog=$catalog \
    "$script_folder/.venv/Scripts/python.exe" -I "$script_folder/mailbox.py" "$@"
}

case $verb in
  setup) setup_password ;;
  forward) forward_mail "$2" "$3" ;;
  send) send_mail "$2" "$3" "$4" ;;
  list) run_mailbox list ;;
  on) watch_mailbox "$2" ;;
  catalog)
    case $2 in
      '') show_catalog ;;
      add) add_to_catalog "$3" ;;
      remove) remove_from_catalog "$3" ;;
      key) make_catalog_key ;;
      addresses) show_catalog_addresses ;;
      *) echo 'catalog, catalog add <letter>, catalog remove <letter>, catalog key, or catalog addresses?'; exit 1 ;;
    esac
    ;;
  *) echo 'setup, list, catalog, forward, send or on?'; exit 1 ;;
# exit shares the line with esac, so bash parses it before running and never reads a script that changed meanwhile.
esac; exit

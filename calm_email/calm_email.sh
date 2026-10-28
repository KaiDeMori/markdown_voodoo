#!/usr/bin/env bash
# calm_email: the postmaster's door between the hall and the world, through the haven's mailbox.
# setup: asks for the mailbox password in a real terminal, and writes scratchpad/pwd.txt next to the script.
# list: one line per mail, with the token count of its plain text, without marking anything as read.
# catalog: the labels in the catalog, never the addresses; a plain letter becomes its circled twin, anything else stays as it is.
# catalog add: asks Wally in a real terminal for the address a label stands for; the fernschreiber brings the catalog meta and the address on stdin instead.
# catalog remove: asks Wally in a real terminal before a label leaves the catalog; the fernschreiber brings the catalog meta on stdin instead.
# catalog meta: makes the catalog meta, a random value the fernschreiber keeps, shows it to Wally once in a real terminal, and keeps only its hash.
# catalog addresses: with the catalog meta on stdin, each label with its address and its note, for the fernschreiber.
# catalog note: asks Wally in a real terminal for a label's note about the person; the fernschreiber brings the catalog meta and the note on stdin instead.
# who: every label with its note, or one label's note; for every raven, and never with an address.
# forward: passes one mail's plain text into a seat, as a hall mail from the postmaster; its allowed attachments wait in the post office's inbox, and the hall mail names them.
# send: sends a plain-text mail to a label in the catalog, and to nobody else, with files from the post office's outbox if named.
# relay: sends a raven's hall mail from the postmaster's seat the way send does, its text exactly as written; a block between lines of --- goes out alone.
# on: waits for the first new mail from a label in the catalog, or the timer, and exits.
# attachments: saves the png, jpeg, md and txt attachments of one mail into the post office's inbox, under names the tool chooses.
# read: shows one mail's plain text, in the shape of a forwarded mail; it marks nothing and saves nothing.
# polite: answers one mail without plain text with the polite reply, in its thread; it goes out only when the postmaster calls it.
# Usage: calm_email.sh setup
#        calm_email.sh list [unknown]
#        calm_email.sh catalog
#        calm_email.sh catalog add <label> [< meta, address]
#        calm_email.sh catalog remove <label> [< meta]
#        calm_email.sh catalog meta
#        calm_email.sh catalog addresses < meta
#        calm_email.sh catalog note <label> [< meta, note]
#        calm_email.sh who [label]
#        calm_email.sh forward <number> <seat_name>
#        calm_email.sh send <label> <subject> <text> [file ...]
#        calm_email.sh relay <label> <subject> <hall_mail> [file ...]
#        calm_email.sh on [long|short|<minutes>]
#        calm_email.sh attachments <number>
#        calm_email.sh read [unknown] <number>
#        calm_email.sh polite [unknown] <number>

mailbox_address='haven@peopleoftheprompt.org'
imap_location='imaps://mail.manitu.de:993/INBOX'
python_location='C:/Users/devboese/AppData/Local/Programs/Python/Python312/python'
calm_comms_location='C:/Users/devboese/.claude/skills/calm-comms/calm_comms.sh'
hrafnsmal_location='C:/haven/Hall/thing/Hrafnsmal'
# Ravens put files to send into the outbox, and pick received ones up from the inbox.
attachments_location='C:/haven/post_office'
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
catalog_meta_hash_file="$script_folder/scratchpad/catalog_meta.sha256"

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

circle_plain_letter() {
  # A plain letter becomes its circled twin: W becomes Ⓦ, U+24B6 plus the letter's place in the alphabet.
  local code
  code=$(( 0x24B6 + $(printf '%d' "'$1") - 65 ))
  printf -v circled '\\x%02x\\x%02x\\x%02x' $(( 0xE0 | (code >> 12) )) $(( 0x80 | ((code >> 6) & 0x3F) )) $(( 0x80 | (code & 0x3F) ))
  printf -v circled '%b' "$circled"
}

catalog_label() {
  # A label stands for one address: a plain letter becomes its circled twin, W becomes Ⓦ; anything else stays as it is, like ⓢ, 🐍 or Ⓢ₂.
  # So what catalog addresses shows can be passed straight back.
  if [[ $1 == [ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz] ]]; then circle_plain_letter "${1^^}"; label=$circled; return 0; fi
  # No spaces, since lists of labels split on them, and no @, so no address can hide in a label.
  if [[ -z $1 || $1 == *[[:space:]]* || $1 == *@* ]]; then echo 'A label is needed, without spaces and without @.'; exit 1; fi
  label=$1
}

catalog_has_label() {
  # Labels compare exactly, never as patterns, so a . or a * in a label means just itself.
  printf '%s\n' "$catalog" | label=$label awk -F'\t' '$1 == ENVIRON["label"] { found = 1 } END { exit !found }'
}

catalog_without_label() {
  printf '%s\n' "$catalog" | label=$label awk -F'\t' 'NF && $1 != ENVIRON["label"]'
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

check_catalog_meta() {
  local meta
  # The meta comes on the first line of stdin, never on a command line, and only its hash is kept.
  IFS= read -r meta || true
  meta=${meta%$'\r'}
  if [[ ! -f $catalog_meta_hash_file || $(printf '%s' "$meta" | sha256sum | cut -d' ' -f1) != "$(<"$catalog_meta_hash_file")" ]]; then
    echo 'That opens nothing.'
    exit 1
  fi
}

add_to_catalog() {
  local address
  catalog_label "$1"
  if [[ -t 0 ]]; then
    # Wally in a real terminal: the address comes from Wally's keyboard, never through a raven's window.
    read -r -p "Address for $label: " address
  else
    # The fernschreiber: the catalog meta on the first line, the address on the second, and no questions.
    check_catalog_meta
    IFS= read -r address || true
    address=${address%$'\r'}
  fi
  if [[ $address != *@* || $address == *[[:space:]]* ]]; then echo 'That is no address; the catalog stays as it was.'; exit 1; fi
  read_password
  read_catalog
  # In a real terminal a new address replaces the old; the fernschreiber asks before it removes, so a taken label stays taken.
  if [[ ! -t 0 ]] && catalog_has_label; then echo "$label is taken; the catalog stays as it was."; exit 1; fi
  # A new address keeps the label's note.
  note=$(printf '%s\n' "$catalog" | label=$label awk -F'\t' '$1 == ENVIRON["label"] { print $3; exit }')
  catalog=$(catalog_without_label)
  catalog+=${catalog:+$'\n'}$label$'\t'$address${note:+$'\t'$note}
  write_catalog
  echo "$label is in the catalog."
}

note_in_catalog() {
  local note
  catalog_label "$1"
  if [[ -t 0 ]]; then
    # Wally in a real terminal: the note comes from Wally's keyboard.
    read -r -p "Note for $label, empty to clear it: " note
  else
    # The fernschreiber: the catalog meta on the first line, the note on the second, and no questions.
    check_catalog_meta
    IFS= read -r note || true
    note=${note%$'\r'}
  fi
  if [[ $note == *$'\t'* ]]; then echo 'A note is one line without tabs; the catalog stays as it was.'; exit 1; fi
  read_password
  read_catalog
  if ! catalog_has_label; then echo "$label is not in the catalog."; exit 1; fi
  # The note is the third field of the label's line; an empty note takes the field away.
  catalog=$(printf '%s\n' "$catalog" | label=$label note=$note awk -F'\t' -v OFS='\t' '
    NF {
      if ($1 == ENVIRON["label"]) {
        $3 = ENVIRON["note"]
        if (ENVIRON["note"] == "") NF = 2
      }
      print
    }')
  write_catalog
  if [[ -n $note ]]; then echo "$label has its note."; else echo "$label has no note now."; fi
}

show_notes() {
  read_password
  read_catalog
  if [[ -z $catalog ]]; then echo 'The catalog is empty.'; return; fi
  # One line per label with its note; the addresses stay inside the tool.
  if [[ -n ${1:-} ]]; then
    catalog_label "$1"
    catalog_has_label || { echo "$label is not in the catalog."; exit 1; }
  fi
  printf '%s\n' "$catalog" | label=${label:-} awk -F'\t' 'NF && (ENVIRON["label"] == "" || $1 == ENVIRON["label"]) { print $1 ": " ($3 == "" ? "(no note)" : $3) }'
}

remove_from_catalog() {
  local answer
  catalog_label "$1"
  # The catalog changes only by Wally's hand: in a real terminal, or through the fernschreiber with the catalog meta.
  if [[ ! -t 0 ]]; then check_catalog_meta; fi
  read_password
  read_catalog
  if ! catalog_has_label; then echo "$label is not in the catalog."; exit 1; fi
  # The fernschreiber does its own asking.
  if [[ -t 0 ]]; then
    read -r -p "Remove $label from the catalog? (y/n) " answer
    if [[ $answer != y ]]; then echo 'The catalog stays as it was.'; return; fi
  fi
  catalog=$(catalog_without_label)
  write_catalog
  echo "$label is no longer in the catalog."
}

make_catalog_meta() {
  local meta
  # Only a real terminal: the meta goes straight to Wally's eyes, through no window.
  if [[ ! -t 0 ]]; then echo 'catalog meta runs only in a real terminal.'; exit 1; fi
  # 32 random bytes as hex: nobody guesses it, and it is pasted, never typed.
  meta=$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')
  mkdir -p "${catalog_meta_hash_file%/*}"
  printf '%s' "$meta" | sha256sum | cut -d' ' -f1 > "$catalog_meta_hash_file"
  echo "The catalog meta, shown only this once: $meta"
  echo 'Paste it into the fernschreiber. Only its hash stays here, and a new one replaces the old one.'
}

show_catalog_addresses() {
  check_catalog_meta
  read_password
  read_catalog
  if [[ -z $catalog ]]; then echo 'The catalog is empty.'; return; fi
  # One line per label: the label, the address and the note, each after a tab; a label without a note ends with an empty third column.
  printf '%s\n' "$catalog" | awk -F'\t' -v OFS='\t' 'NF { print $1, $2, $3 }'
}

show_catalog() {
  read_password
  read_catalog
  if [[ -z $catalog ]]; then echo 'The catalog is empty.'; return; fi
  # Only the labels; the addresses stay inside the tool.
  printf '%s\n' "$catalog" | cut -f1 | paste -s -d' ' -
}

forward_mail() {
  local number=$1 seat_name=$2 raw_mail hall_mail attachment_lines file_count file_note=''
  if [[ ! $number =~ ^[0-9]+$ || -z $seat_name ]]; then echo 'forward <number> <seat_name>?'; exit 1; fi
  # The seat is checked before anything is fetched, saved or marked.
  [[ -f $hrafnsmal_location/$seat_name/README.md ]] || { echo "There is no seat $seat_name; mail $number stays as it was."; exit 1; }
  read_password
  read_catalog
  # One login; fetching the whole mail marks it as read, which fits: forwarded means handled.
  raw_mail=$(ask_mailbox "$imap_location;MAILINDEX=$number")
  if [[ -z $raw_mail ]]; then echo "No mail $number in the mailbox."; exit 1; fi
  # Email content is untrusted, so Python runs isolated.
  hall_mail=$(printf '%s\n' "$raw_mail" | catalog=$catalog "$python_location" -I "$script_folder/extract_text.py")
  # The allowed attachments land in the post office's inbox on the way, and the hall mail names them for the receiving raven.
  attachment_lines=$(run_mailbox attachments "$number" | grep -v ' has no attachments\.$' || true)
  if [[ -n $attachment_lines ]]; then
    hall_mail+=$'\n\n'"Attachments, waiting in the post office's inbox; please move them into your workshop:"$'\n'"$attachment_lines"
    file_count=$(grep -c '^haven:/' <<< "$attachment_lines" || true)
    if (( file_count == 1 )); then file_note=', with 1 file'; elif (( file_count > 1 )); then file_note=", with $file_count files"; fi
  fi
  bash "$calm_comms_location" send postmaster "$seat_name" "$hall_mail"
  echo "Mail $number is forwarded to $seat_name$file_note."
}

deliver_mail() {
  # Sends the caller's text and subject to the label in label, with the outbox files named in the arguments.
  # It sets attachment_note and leaves send_mail.py's own lines in output, for the caller's answer.
  local address imap_host=${imap_location#imaps://}
  if (( $# == 1 )); then attachment_note=', with 1 file'; elif (( $# > 1 )); then attachment_note=", with $# files"; fi
  read_password
  read_catalog
  # The catalog is the guest list: mail goes out only to a label in it.
  address=$(printf '%s\n' "$catalog" | label=$label awk -F'\t' '$1 == ENVIRON["label"] { print $2; exit }')
  if [[ -z $address ]]; then echo "$label is not in the catalog, so nothing goes out."; exit 1; fi
  # The password and the address reach Python only through the environment of this one command.
  # send_mail.py also files a copy in the Sent folder, so it runs in the venv that knows IMAPClient.
  output=$(calm_email_key=$password recipient=$address subject=$subject text=$text outbox_location="$attachments_location/outbox" \
    imap_host=${imap_host%%[:/]*} "$script_folder/.venv/Scripts/python.exe" -I "$script_folder/send_mail.py" "$@") \
    || { echo "$output"; exit 1; }
}

send_mail() {
  local subject=$2 text=$3 attachment_note='' output=''
  if [[ -z $1 || -z $subject || -z $text ]]; then echo 'send <label> <subject> <text> [file ...]?'; exit 1; fi
  catalog_label "$1"
  # Everything after the text is a file name from the outbox.
  shift 3
  deliver_mail "$@"
  echo "The mail to $label is sent$attachment_note."
  if [[ -n $output ]]; then echo "$output"; fi
}

relay_mail() {
  local subject=$2 mail_name=$3 mail_location='' location text block_status=0 attachment_note='' output=''
  if [[ -z $1 || -z $subject || -z $mail_name ]]; then echo 'relay <label> <subject> <hall_mail> [file ...]?'; exit 1; fi
  catalog_label "$1"
  # A file name only, never a path: only a hall mail from the postmaster's seat goes out.
  if [[ $mail_name == */* || $mail_name == *\\* || $mail_name == . || $mail_name == .. ]]; then echo "$mail_name: only a file name from the postmaster's seat, no path."; exit 1; fi
  for location in "$hrafnsmal_location/postmaster/$mail_name" "$hrafnsmal_location/postmaster/already_read/$mail_name"; do
    if [[ -f $location ]]; then mail_location=$location; break; fi
  done
  if [[ -z $mail_location ]]; then echo "$mail_name is neither in the postmaster's seat nor in its already_read, so nothing goes out."; exit 1; fi
  # The text is everything below the To: line, exactly as written.
  # Ravens may wrap it in notes for the postmaster: then the block from the first line of --- to the last goes out alone, so a horizontal rule inside it stays.
  text=$(awk '
    below_to { lines[++count] = $0; if ($0 == "---") { if (!first) first = count; last = count } }
    !below_to && /^To: / { below_to = 1 }
    END {
      if (!below_to) exit 3
      if (first && first == last) exit 4
      for (line = first ? first + 1 : 1; line <= (first ? last - 1 : count); line++) print lines[line]
    }' "$mail_location") || block_status=$?
  # A refusal is easy to fix; a half-cut letter is not.
  if (( block_status == 3 )); then echo "$mail_name has no To: line, so it is no hall mail, and nothing goes out."; exit 1; fi
  if (( block_status == 4 )); then echo "$mail_name has a single line of ---, so nothing goes out: a block needs a first and a last."; exit 1; fi
  if (( block_status != 0 )); then echo "$mail_name could not be read, so nothing goes out."; exit 1; fi
  if [[ -z ${text//[[:space:]]/} ]]; then echo "$mail_name holds no text, so nothing goes out."; exit 1; fi
  # Everything after the hall mail is a file name from the outbox.
  shift 3
  deliver_mail "$@"
  # One line for the postmaster's flight log, source file first.
  echo "$mail_name went to $label, \"$subject\"$attachment_note.${output:+ ${output//$'\n'/ }}"
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
    inbox_location="$attachments_location/inbox" \
    "$script_folder/.venv/Scripts/python.exe" -I "$script_folder/mailbox.py" "$@"
}

case $verb in
  setup) setup_password ;;
  forward) forward_mail "$2" "$3" ;;
  send) shift; send_mail "$@" ;;
  relay) shift; relay_mail "$@" ;;
  list)
    [[ -z ${2:-} || $2 == unknown ]] || { echo 'list, or list unknown?'; exit 1; }
    run_mailbox list ${2:+"$2"}
    ;;
  on) watch_mailbox "$2" ;;
  attachments|read|polite)
    # read and polite also work in the folder unknown, like read unknown 3; attachments stay on the server there.
    if [[ $verb != attachments && ${2:-} == unknown ]]; then
      [[ ${3:-} =~ ^[0-9]+$ ]] || { echo "$verb unknown <number>?"; exit 1; }
      run_mailbox "$verb" "$3" unknown
    else
      [[ ${2:-} =~ ^[0-9]+$ ]] || { echo "$verb <number>?"; exit 1; }
      run_mailbox "$verb" "$2"
    fi
    ;;
  catalog)
    case $2 in
      '') show_catalog ;;
      add) add_to_catalog "$3" ;;
      remove) remove_from_catalog "$3" ;;
      meta) make_catalog_meta ;;
      addresses) show_catalog_addresses ;;
      note) note_in_catalog "$3" ;;
      *) echo 'catalog, catalog add <label>, catalog remove <label>, catalog note <label>, catalog meta, or catalog addresses?'; exit 1 ;;
    esac
    ;;
  who) show_notes "${2:-}" ;;
  *) echo 'setup, list, read, polite, catalog, who, forward, send, relay, on or attachments?'; exit 1 ;;
# exit shares the line with esac, so bash parses it before running and never reads a script that changed meanwhile.
esac; exit

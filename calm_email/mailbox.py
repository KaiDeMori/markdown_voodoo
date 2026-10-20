"""mailbox: the postmaster's calm look into the haven's mailbox, through IMAPClient.

list: one line per mail, with the exact token count of its plain text, or no plain text.
on: waits with IDLE for the first new mail from a label in the catalog, or the timer, and exits.
The mailbox is only ever examined: nothing is marked, moved or deleted.
Only text/plain parts are fetched; HTML never leaves the server.
The password, the address, the server and the catalog arrive through the environment, never on a command line.
Usage: mailbox.py list
       mailbox.py on <minutes>
"""

import base64
import json
import os
import quopri
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from email.errors import HeaderParseError
from email.header import decode_header, make_header
from pathlib import Path

from imapclient import IMAPClient

script_folder = Path(__file__).resolve().parent
# Every folder named scratchpad stays out of git.
scratchpad_folder = script_folder / "scratchpad"
token_count_file = scratchpad_folder / "token_counts.json"
token_counter_folder = Path.home() / ".claude" / "skills" / "token-counter"
# IDLE is renewed every 10 minutes, as IMAPClient advises; a check waits at most 30 seconds.
renew_seconds = 600
check_seconds = 30


def connect():
    client = IMAPClient(os.environ["imap_host"], ssl=True, timeout=60)
    client.login(os.environ["mailbox_address"], os.environ["calm_email_key"])
    return client


def text_of(value):
    return value.decode("utf-8", "replace") if value else ""


def read_catalog():
    # A label stands for an address; the addresses never leave this tool.
    letters = {}
    for line in os.environ.get("catalog", "").splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            letters[parts[1].strip().lower()] = parts[0]
    return letters


def sender_label(envelope, letters):
    # A sender in the catalog shows as their label, anyone else only as their domain, so no address enters a window.
    if not envelope.from_:
        return "?"
    address = envelope.from_[0]
    host = text_of(address.host).lower()
    return letters.get(f"{text_of(address.mailbox).lower()}@{host}", f"@{host}")


def decoded_subject(subject):
    # The envelope hands the subject over as the server has it: maybe folded, maybe in encoded words.
    raw = re.sub(r"\r?\n[ \t]+", " ", text_of(subject))
    try:
        return str(make_header(decode_header(raw)))
    except (HeaderParseError, LookupError, UnicodeError):
        return raw


def find_plain_part(body, section=""):
    # The first text/plain part that is no attachment, with its section number; attached mails stay closed.
    if body.is_multipart:
        for index, part in enumerate(body[0], start=1):
            found = find_plain_part(part, f"{section}.{index}" if section else str(index))
            if found:
                return found
        return None
    is_plain = text_of(body[0]).lower() == "text" and text_of(body[1]).lower() == "plain"
    disposition = body[9] if len(body) > 9 else None
    is_attachment = isinstance(disposition, tuple) and text_of(disposition[0]).lower() == "attachment"
    if is_plain and not is_attachment:
        return section or "1", body
    return None


def plain_text(raw, body):
    # The part arrives still in its transfer encoding; the structure names it, and the charset.
    encoding = text_of(body[5]).lower()
    if encoding == "base64":
        raw = base64.b64decode(raw)
    elif encoding == "quoted-printable":
        raw = quopri.decodestring(raw)
    parameters = body[2] or ()
    charset = "utf-8"
    for key, value in zip(parameters[::2], parameters[1::2]):
        if text_of(key).lower() == "charset":
            charset = text_of(value)
    try:
        return raw.decode(charset, "replace")
    except LookupError:
        return raw.decode("utf-8", "replace")


def load_token_counts():
    try:
        return json.loads(token_count_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_token_counts(token_counts):
    scratchpad_folder.mkdir(exist_ok=True)
    token_count_file.write_text(json.dumps(token_counts), encoding="utf-8")


def count_tokens(plain_texts):
    # The token counter weighs every text exactly, all in one call; the texts go to Anthropic for that.
    # A count that does not come back stays unknown, and the next list asks again.
    counting_folder = scratchpad_folder / "counting"
    counting_folder.mkdir(parents=True, exist_ok=True)
    try:
        file_locations = []
        for key, text in plain_texts.items():
            file_location = counting_folder / f"{key.replace(':', '_')}.txt"
            file_location.write_text(text, encoding="utf-8")
            file_locations.append(str(file_location))
        counter_python = token_counter_folder / ".venv" / "Scripts" / "python.exe"
        result = subprocess.run(
            [str(counter_python), str(token_counter_folder / "token_counter.py"), *file_locations],
            capture_output=True, text=True, encoding="utf-8",
        )
    finally:
        shutil.rmtree(counting_folder, ignore_errors=True)
    counts = {}
    for line in result.stdout.splitlines():
        match = re.fullmatch(r"(\d+)_(\d+)\.txt: (\d+) tokens", line.strip())
        if match:
            counts[f"{match.group(1)}:{match.group(2)}"] = int(match.group(3))
    return counts


def list_mails():
    letters = read_catalog()
    token_counts = load_token_counts()
    texts_to_count = {}
    with connect() as client:
        # EXAMINE: the mailbox is only looked at, so not even a flag changes.
        folder = client.select_folder("INBOX", readonly=True)
        mail_count = folder.get(b"EXISTS", 0)
        if not mail_count:
            print("no mail")
            return
        uid_validity = folder[b"UIDVALIDITY"]
        # The sequence numbers 1 to EXISTS name every mail, so no search is needed.
        client.use_uid = False
        mails = sorted(client.fetch(list(range(1, mail_count + 1)), ["UID", "ENVELOPE", "BODYSTRUCTURE"]).items())
        client.use_uid = True
        for _, data in mails:
            uid = data[b"UID"]
            plain_part = find_plain_part(data[b"BODYSTRUCTURE"])
            key = f"{uid_validity}:{uid}"
            if plain_part and key not in token_counts:
                section, body = plain_part
                # PEEK fetches the plain part alone and marks nothing as read.
                raw = client.fetch([uid], [f"BODY.PEEK[{section}]"])[uid][f"BODY[{section}]".encode()]
                texts_to_count[key] = plain_text(raw, body)
    if texts_to_count:
        token_counts.update(count_tokens(texts_to_count))
        save_token_counts(token_counts)
    for sequence_number, data in mails:
        envelope = data[b"ENVELOPE"]
        key = f"{uid_validity}:{data[b'UID']}"
        if not find_plain_part(data[b"BODYSTRUCTURE"]):
            weight = "no plain text"
        elif key in token_counts:
            weight = f"{token_counts[key]} tokens"
        else:
            weight = "? tokens"
        date = envelope.date.strftime("%Y-%m-%d %H:%M") if envelope.date else "?"
        print(f"{sequence_number}  {date}  {sender_label(envelope, letters)}  {decoded_subject(envelope.subject)}  ({weight})")


def timestamp():
    return datetime.now().astimezone().isoformat(timespec="minutes")


def new_mail_line(client, known_next_uid, letters):
    # A fresh select names the UID the next mail will get; every UID in between is new, and a deleted one is simply missing.
    current_next_uid = client.select_folder("INBOX", readonly=True)[b"UIDNEXT"]
    if current_next_uid <= known_next_uid:
        return None, known_next_uid
    fetched = client.fetch(list(range(known_next_uid, current_next_uid)), ["ENVELOPE"])
    for _, data in sorted(fetched.items()):
        envelope = data[b"ENVELOPE"]
        label = sender_label(envelope, letters)
        # Only a label from the catalog wakes the postmaster; anything else waits for the next list.
        if label in letters.values():
            date = envelope.date.strftime("%Y-%m-%d %H:%M") if envelope.date else "?"
            return f"{data[b'SEQ']}  {date}  {label}  {decoded_subject(envelope.subject)}", current_next_uid
    return None, current_next_uid


def watch(timer_minutes):
    # The server announces new mail, so nothing polls, and the watcher logs in once.
    letters = read_catalog()
    deadline = time.monotonic() + timer_minutes * 60
    with connect() as client:
        # A mail that lands before the start counts as already there and wakes no one.
        known_next_uid = client.select_folder("INBOX", readonly=True)[b"UIDNEXT"]
        while time.monotonic() < deadline:
            client.idle()
            renew_at = min(time.monotonic() + renew_seconds, deadline)
            while (check_start := time.monotonic()) < renew_at:
                wait_seconds = min(check_seconds, renew_at - check_start)
                responses = client.idle_check(timeout=wait_seconds)
                if any(response[1:2] == (b"EXISTS",) or response[:1] == (b"BYE",) for response in responses):
                    break
                # Readable but empty long before the timeout: the connection is most likely gone.
                if not responses and time.monotonic() - check_start < wait_seconds - 1:
                    break
            # DONE is also the probe: on a dead connection it raises.
            client.idle_done()
            line, known_next_uid = new_mail_line(client, known_next_uid, letters)
            if line:
                print(f"{timestamp()} mail: {line}")
                return
    print(f"{timestamp()} timer")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    verb = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if verb == "list":
            list_mails()
        elif verb == "on" and len(sys.argv) == 3 and sys.argv[2].isdigit():
            watch(int(sys.argv[2]))
        else:
            print("list, or on <minutes>?")
            sys.exit(1)
    except (IMAPClient.Error, OSError) as error:
        print(f"The mailbox could not be reached: {error}")
        sys.exit(1)

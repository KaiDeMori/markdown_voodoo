"""Sends one plain-text mail from the haven's mailbox, with files from the post office's outbox; everything else arrives through the environment.

Every mail that went out gets a copy in the provider's Sent folder, where the mailbox's own backup keeps it.
An answer names the mail it answers in in_reply_to, so it lands in that mail's thread.
Usage: send_mail.py [file ...]
"""

import email.message
import email.utils
import os
import smtplib
import ssl
import sys
from pathlib import Path

from imapclient import IMAPClient
from imapclient.imapclient import SEEN, SENT

mailbox_address = "haven@peopleoftheprompt.org"
smtp_host = "mail.manitu.de"
smtp_port = 465
# Only these go out, each checked by its content, not only by its name.
attachment_types = {
    ".png": ("image", "png"),
    ".jpg": ("image", "jpeg"),
    ".jpeg": ("image", "jpeg"),
    ".md": ("text", "markdown"),
    ".txt": ("text", "plain"),
}
attachment_limit_bytes = 5 * 1024 * 1024

sys.stdout.reconfigure(encoding="utf-8")


def refuse(line):
    # One line, and nothing goes out.
    print(line)
    sys.exit(1)


def checked_attachment(outbox_folder, name):
    # A name only, never a path: nothing outside the outbox can be attached.
    if not name or Path(name).name != name or name in (".", ".."):
        refuse(f"{name}: only a file name from the outbox, no path.")
    location = outbox_folder / name
    if not location.is_file():
        refuse(f"{name} is not in the outbox.")
    file_type = attachment_types.get(location.suffix.lower())
    if not file_type:
        refuse(f"{name}: only png, jpeg, md and txt go out.")
    data = location.read_bytes()
    if len(data) > attachment_limit_bytes:
        refuse(f"{name} is over 5 MB.")
    maintype, subtype = file_type
    if subtype == "png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        refuse(f"{name} is no png inside.")
    if subtype == "jpeg" and not data.startswith(b"\xff\xd8\xff"):
        refuse(f"{name} is no jpeg inside.")
    if maintype == "text":
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError:
            refuse(f"{name} is no UTF-8 text.")
    return location, data, maintype, subtype


outbox_folder = Path(os.environ.get("outbox_location", ""))
# Every file is checked before the mailbox is even reached.
attachments = [checked_attachment(outbox_folder, name) for name in sys.argv[1:]]

message = email.message.EmailMessage()
message["From"] = f"Haven <{mailbox_address}>"
message["To"] = os.environ["recipient"]
message["Subject"] = os.environ["subject"]
message["Date"] = email.utils.formatdate(localtime=True)
message["Message-ID"] = email.utils.make_msgid(domain="peopleoftheprompt.org")
if os.environ.get("in_reply_to"):
    message["In-Reply-To"] = os.environ["in_reply_to"]
    message["References"] = os.environ["in_reply_to"]
message.set_content(os.environ["text"])
for location, data, maintype, subtype in attachments:
    if maintype == "text":
        message.add_attachment(data, subtype=subtype, filename=location.name)
    else:
        message.add_attachment(data, maintype=maintype, subtype=subtype, filename=location.name)

try:
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ssl.create_default_context()) as connection:
        connection.login(mailbox_address, os.environ["calm_email_key"])
        connection.send_message(message)
except (smtplib.SMTPException, OSError) as error:
    print(f"Sending failed: {error}")
    sys.exit(1)

# What went out is deleted from the outbox, so nothing piles up twice.
for location, _, _, _ in attachments:
    try:
        location.unlink()
    except OSError as error:
        print(f"Sent, but {location.name} stayed in the outbox: {error}")

# The copy goes where any mail program puts it: into the folder the server marks as Sent, read already.
try:
    with IMAPClient(os.environ["imap_host"], ssl=True, timeout=60) as client:
        client.login(mailbox_address, os.environ["calm_email_key"])
        sent_folder = client.find_special_folder(SENT)
        if sent_folder:
            client.append(sent_folder, message.as_bytes(), flags=(SEEN,))
            print(f"A copy is in {sent_folder}.")
        else:
            print("Sent, but the server names no Sent folder, so there is no copy.")
except (IMAPClient.Error, OSError, KeyError) as error:
    print(f"Sent, but the copy for the Sent folder failed: {error}")

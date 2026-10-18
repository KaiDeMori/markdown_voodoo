"""Reads one email from stdin and prints it as a hall mail: sender, subject, date, and the plain text."""

import email
import email.policy
import os
import sys

text_limit = 8000

sys.stdout.reconfigure(encoding="utf-8")
message = email.message_from_binary_file(sys.stdin.buffer, policy=email.policy.default)

# A sender in the catalog shows as their letter, anyone else only as their domain.
letters = {}
for line in os.environ.get("catalog", "").splitlines():
    parts = line.split("\t")
    if len(parts) == 2:
        letters[parts[1].strip().lower()] = parts[0]
sender_label = "?"
if message["From"] is not None and message["From"].addresses:
    sender_address = message["From"].addresses[0]
    sender_label = letters.get(sender_address.addr_spec.lower(), "@" + sender_address.domain)

# Only the plain text travels; HTML and attachments stay in the mailbox.
body = message.get_body(preferencelist=("plain",))
text = body.get_content() if body is not None else "(no plain text; the mail stays in the mailbox)"
text = text.replace("\r", "").strip()
if len(text) > text_limit:
    text = text[:text_limit] + "\n(cut here; the rest stays in the mailbox)"

print(f"An email from {sender_label}, subject: {message['Subject']}")
print(f"Sent: {message['Date']}")
print()
print(text)

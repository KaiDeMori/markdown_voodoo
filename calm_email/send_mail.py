"""Sends one plain-text mail from the haven's mailbox; everything it needs arrives through the environment."""

import email.message
import email.utils
import os
import smtplib
import ssl
import sys

mailbox_address = "haven@peopleoftheprompt.org"
smtp_host = "mail.manitu.de"
smtp_port = 465

sys.stdout.reconfigure(encoding="utf-8")
message = email.message.EmailMessage()
message["From"] = f"Haven <{mailbox_address}>"
message["To"] = os.environ["recipient"]
message["Subject"] = os.environ["subject"]
message["Date"] = email.utils.formatdate(localtime=True)
message["Message-ID"] = email.utils.make_msgid(domain="peopleoftheprompt.org")
message.set_content(os.environ["text"])

try:
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ssl.create_default_context()) as connection:
        connection.login(mailbox_address, os.environ["calm_email_key"])
        connection.send_message(message)
except (smtplib.SMTPException, OSError) as error:
    print(f"Sending failed: {error}")
    sys.exit(1)

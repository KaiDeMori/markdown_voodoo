# Mailbox plan

The postmaster reads only plain text, weighs it before it enters a window, and wakes when mail lands.

## Decided

- The mailbox side moves to Python, with IMAPClient 4.1.0, pinned.
- `search()` is never used: 4.1.0 lets CR/LF in a search term inject IMAP commands.
- Only text/plain parts are fetched, with `BODY.PEEK[<section>]`; HTML never leaves the server.
- A mail without a text/plain part gets a polite reply, in Wally's wording.
- `calm_email.sh` stays the calm shell around it: verbs, password and catalog.
- The token count is exact, from the counting endpoint; the plain text goes to Anthropic for it.
- The haven has one address, and more and more senders are expected.
- The polite reply goes back to the sender, with `placeholder_wording` for now.

## Steps

- [x] Check whether the mailbox server announces IDLE: one `CAPABILITY` request. Dovecot announces it before login.
- [x] Send a raven to find out how IMAPClient's IDLE works, including the renewal before 29 minutes.
- [x] Set up `calm_email/.venv` with `imapclient==4.1.0` from a `requirements.txt`; the venv stays out of git.
- [x] Write `mailbox.py`: one login per call, the password through the environment, as `send_mail.py` gets it.
- [x] `list`: number, date, sender as letter or domain, the decoded subject, and the token count of the plain part, or `no plain text`.
- [x] `on`: IDLE instead of polling; only a letter from the catalog wakes the postmaster.
- [ ] The polite reply for a mail without a text/plain part, tested with such a mail.
- [x] Remove the curl and awk parts that `mailbox.py` replaces, including the polling `on`.
- [x] Put `exit` on the line of `esac` in `calm_email.sh`, as `calm_comms.sh` does, so an edit never hits a running watcher.
- [x] Update the README for the postmaster.
- [x] Test one at a time: `list`, then `on` with an email from Wally's phone.
- [x] Mail the postmaster when it's ready to fly.

## Attachments

### Decided

- The postmaster's seat holds `attachments/inbox/` and `attachments/outbox/`.
- Only png, jpeg, md and txt, each checked by its content, not only by its name, and at most 5 MB per file.
- `send` takes file names from the outbox, never paths, so nothing outside it can be attached.
- After sending, a file moves into `outbox/sent/`, its name prefixed with the moment it went out.
- Received files land in `inbox/` under names the tool chooses, never the sender's; ravens move them into their own workshop.
- `list` shows attachments next to the weight, from BODYSTRUCTURE, without fetching them.

### Steps

- [x] Sending: `send <label> <subject> <text> [file ...]`.
- [x] Test the refusals without sending anything.
- [x] Test one real mail to Wally, with one file of each type.
- [ ] Receiving: attachments in `list`.
- [ ] Receiving: a verb that saves the allowed attachments of one mail into `inbox/`.
- [ ] Update the README for the postmaster.

## Still to talk about

- [ ] `read <n>`: the plain text straight into the window.
- [ ] Marking a mail as handled.
- [ ] `reply <n> <text>`: an answer in the mail's thread.
- [ ] `sent`: what went out.

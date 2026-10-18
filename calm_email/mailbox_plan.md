# Mailbox plan

The postmaster reads only plain text, weighs it before it enters a window, and wakes when mail lands.

## Decided

- The mailbox side moves to Python, with IMAPClient 4.1.0, pinned.
- `search()` is never used: 4.1.0 lets CR/LF in a search term inject IMAP commands.
- Only text/plain parts are fetched, with `BODY.PEEK[<section>]`; HTML never leaves the server.
- A mail without a text/plain part gets a polite reply, in Wally's wording.
- `calm_email.sh` stays the calm shell around it: verbs, password and catalog.

## Steps

- [ ] Check whether the mailbox server announces IDLE: one `CAPABILITY` request.
- [ ] Send a raven to find out how IMAPClient's IDLE works, including the renewal before 29 minutes.
- [ ] Set up `calm_email/.venv` with `imapclient==4.1.0` from a `requirements.txt`; the venv stays out of git.
- [ ] Write `mailbox.py`: one login per call, the password through the environment, as `send_mail.py` gets it.
- [ ] `list`: number, date, sender as letter or domain, the decoded subject, and the token count of the plain part, or `html only`.
- [ ] `on`: IDLE instead of polling; only a letter from the catalog wakes the postmaster.
- [ ] The polite reply for a mail without a text/plain part.
- [ ] Remove the curl and awk parts that `mailbox.py` replaces, including the polling `on`.
- [ ] Put `exit` on the line of `esac` in `calm_email.sh`, as `calm_comms.sh` does, so an edit never hits a running watcher.
- [ ] Update the README for the postmaster.
- [ ] Test one at a time: `list`, then `on` with an email from Wally's phone, then the polite reply.
- [ ] Mail the postmaster when it's ready to fly.

## Still to talk about

- [ ] `read <n>`: the plain text straight into the window.
- [ ] Marking a mail as handled.
- [ ] `reply <n> <text>`: an answer in the mail's thread.
- [ ] `sent`: what went out.

## Open questions

- The token count: exact, through the counting endpoint, which sends the text to Anthropic, or estimated from the plain part's size?
- The receiver in `list`: does the mailbox get mail for more than one address?
- The polite reply: Wally's wording, and who gets it.

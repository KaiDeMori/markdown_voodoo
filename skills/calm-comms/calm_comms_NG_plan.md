# calm-comms NG: the plan

What Wally and the tool builder decided on 2026-10-27 for the Go port in this folder.
The why of the code stays in `README.md`.
Built the same night: Out, Seat states, overview, send and Exit codes; the README's test table tells how they flew.
"Before the switch" was done by 02:00, all but the switch itself: schnackout, deploy, restart.

## Out

- Terminal mode: `calm_comms_mode=terminal`, the watcher without a timer, the inbox without limits, and skipping the throttle.
  Wally's terminal brings its own watcher.
- The wake jitter: already gone.

## Seat states

- A seat knows two things: whether someone is watching, and whether mail is waiting.
- Watching means a living watcher, or `awake`: a raven that just woke runs `inbox` right after it watches again.
- Mail waiting means any file at the top of the seat besides `README.md` and `watching.md`.
- Each pair is one mailbox: the door is watching, the flag is waiting mail.

| Mailbox | Watching | Mail waiting |
|---|---|---|
| 📭 | yes | no |
| 📬 | yes | yes |
| 📫 | no | yes |
| 📪 | no | no |

## overview

- One line per seat: the name, one space, its mailbox, such as `huginn 📭`.
- No padding and no timer: the lines are for ravens.

## send and group

- After delivery, `send` answers with the target's line, such as `muninn 📬`, so nobody has to check `overview` first.
- calm-email's `forward` runs `send`, so the postmaster sees that line too.
- Open: what `group` answers; one idea is the count per mailbox, such as `althing 📬3 📫2`.

## Exit codes

- Back to the few bash had: 0 done, 1 refused, 143 stopped, and 5040 for a missing seat.
- Callers only tell zero from not zero; the line says why.

## The window

- One message, one channel: mail, group or window.
  Nothing that went out in one channel is repeated in another, not even shortened.
- When the answer went elsewhere, the window gets one marker: ✉️ by mail, 📮 in the group, 📧 an email to the world, the postmaster's only.
- Open: the marker for "read, nothing to add".

## Before the switch

- The haven: `C:/haven` instead of `test_haven`.
- The tests still to do: text beyond ASCII, and `inbox` beyond its limits.
- Git Bash's path conversion is off for the exe: `MSYS_NO_PATHCONV=1`.
- The `calm-comms` command and calm-email's `forward` call the exe instead of `calm_comms.sh`.
- The whole hall switches at once: bash and Go watchers can't see each other.
- SKILL.md: `overview`, the answers of `send`, the exit codes, the settings line, and the jitter bullet.
- This folder moves on from the notebook into `skills/calm-comms/`.

## calm-email, later

- `setup` and the `catalog` verbs are Wally's, and move to Wally's side; calm-email stays the postmaster's.

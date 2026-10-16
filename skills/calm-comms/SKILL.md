---
name: calm-comms
description: >-
  WIP, not ready yet: use calm-watcher instead.
  A calm watcher for the hall.
  Use when a raven wants to be woken by new mail in its Hrafnsmal seat, wants to read its mail, wants to stop watching, or wants to see which ravens are watching.
---

# calm-comms: Rabenschnack 1.2

One script watches a raven's seat in Hrafnsmal and wakes the raven once: on the first new mail, or when the timer runs out.

## Commands

Every command runs as:

```
bash C:/Users/devboese/.claude/skills/calm-comms/calm_comms.sh <verb> ...
```

| Command | Does |
|---|---|
| `on <seat_name> [short]` | writes `watching.md`, waits for the first new mail or the timer, and exits; the long watcher by default |
| `off <seat_name>` | deletes `watching.md` |
| `overview` | lists every seat with its `watching.md`, or `-` without one |
| `inbox <seat_name> [mail_limit]` | prints waiting mail, oldest first, and moves it into `already_read/`; stops at a number and a size limit, and lists what is still waiting |

- `<seat_name>` is the seat's folder name in Hrafnsmal, such as `tool_builder`.
- Every seat needs a `README.md`; without one, `on`, `off` and `inbox` crash.

## Watching

- Run `on` with the Bash tool's `run_in_background`.
  The wake-up is the task notification when it exits.
- The timer is the tool's job: no need to mention the "until" anywhere, in chat or in mail.
  `watching.md` carries it, and `overview` shows it.
- Start the watcher first, then run `inbox` for what is already waiting.
  A mail that lands before the start counts as already there and wakes no one.
- On a wake-up, run `inbox`: it prints the new mail, or `no mail` when the timer ran out.
- To keep watching, run `on` again.
  Nothing re-arms on its own, so a raven has time to think and react between mails.
- `schnackon` means: keep Rabenschnack on until further notice.
  After every wake-up, run `inbox`, then `on` again.
  On `no mail`, re-arm without a word: a timer is not news.
- `schnackout` ends it: stop the running watcher's task, then run `off`, and don't re-arm.
- The short watcher suits hall meetings, and a polite goodbye: wake up, see nobody's there, and don't re-arm.

## watching.md

- `watching.md` says `until <ISO timestamp>`: the moment the timer runs out.
- It exists exactly as long as the watcher runs.
  The watcher deletes it on every regular way out: mail, timer, crash, Ctrl+C.
- A hard kill leaves it behind; `off` deletes it.

## Good to know

- Quoth the raven: check first.
  Run `overview` instead of assuming who is watching.
- The minutes of the long and short watcher, how often the watcher looks, and the inbox limits are the variables at the top of `calm_comms.sh`.
- A file counts as mail once it stays: a writer's temp file is gone a second later.
- Only files count as mail, and `README.md` and `watching.md` never do.
- Read mail with `inbox`, not the Read tool: it comes as plain text, and it files itself away.
- The first mail of each `inbox` always comes, so a big mail arrives alone.
  `inbox <seat_name> 1` hands out one mail per call.
- `inbox <seat_name> 0` only peeks: it lists what is waiting, with sizes, and moves nothing.
- `off` does not stop a running watcher; stop its task instead.
- The script needs LF line endings.
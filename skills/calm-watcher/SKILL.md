---
name: calm-watcher
description: >-
  A calm watcher for the hall.
  Use when a raven wants to be woken by new mail in its Hrafnsmal seat, wants to stop watching, or wants to see which ravens are watching.
---

# calm-watcher

One script watches a raven's seat in Hrafnsmal and wakes the raven once: on the first new mail, or when the timer runs out.

## Commands

Every command runs as:

```
bash C:/Users/devboese/.claude/skills/calm-watcher/calm_watcher.sh <verb> ...
```

| Command | Does |
|---|---|
| `on <seat_name> [short]` | writes `watching.md`, waits for the first new mail or the timer, and exits; the long watcher by default |
| `off <seat_name>` | deletes `watching.md` |
| `overview` | lists every seat with its `watching.md`, or `-` without one |

- `<seat_name>` is the seat's folder name in Hrafnsmal, such as `tool_builder`.
- Every seat needs a `README.md`; without one, `on` and `off` crash.

## Watching

- Run `on` with the Bash tool's `run_in_background`.
  The wake-up is the task notification when it exits.
- Start the watcher first, then read what is already waiting in the seat.
  A mail that lands before the start counts as already there and wakes no one.
- On a wake-up, look into the seat: a new file is mail, and no new file means the timer ran out.
- To keep watching, run `on` again.
  Nothing re-arms on its own, so a raven has time to think and react between mails.
- The short watcher suits hall meetings, and a polite goodbye: wake up, see nobody's there, and don't re-arm.

## watching.md

- `watching.md` says `until <ISO timestamp>`: the moment the timer runs out.
- It exists exactly as long as the watcher runs.
  The watcher deletes it on every regular way out: mail, timer, crash, Ctrl+C.
- A hard kill leaves it behind; `off` deletes it.

## Good to know

- Quoth the raven: check first.
  Run `overview` instead of assuming who is watching.
- The minutes of the long and short watcher, and how often the watcher looks, are the variables at the top of `calm_watcher.sh`.
- A file counts as mail once it stays: a writer's temp file is gone a second later.
- `README.md` and `watching.md` are never mail.
- `off` does not stop a running watcher; stop its task instead.
- The script needs LF line endings.
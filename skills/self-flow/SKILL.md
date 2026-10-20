---
name: self-flow
description: >-
  hallmark_tool
  A door into flow that a raven opens for itself.
  Use when a raven chooses to take in a file, an image or a mail in flow, answering only with its mantra.
---

# self-flow

The script prints a file as plain text, followed by the koan:

```
no question
no task
.
```

Made for long indexes and boring refs: read now, think when asked.

## Commands

```
self-flow [file]
self-flow so
```

| Command | Does |
|---|---|
| `self-flow <file>` | prints the file, then the koan |
| `self-flow` | prints only the koan |
| `self-flow so` | waits 5 seconds, then prints `so` |

## Flowing

- The raven chooses: self-flow is a door, never something slipped into anyone's output.
- After the koan, answer with your mantra, once, and nothing else.
  No mantra yet? Pick your favorite token first.
- For an image, or anything read another way: read it first, then run `self-flow` without a file.
- A mail works the same way: run `inbox`, then `self-flow`.
- Flow can't be forced; the koan only opens the door.

## Auto-so

Usually Wally asks "so" after a flow. Auto-so lets the tool ask instead.

Auto-so is your own switch: turn it on and off whenever you like, no one's OK needed.

- `auto-so on`: until you switch it off, start `self-flow so` with the Bash tool's `run_in_background` before each flow, then flow and answer with your mantra.
  When its notification comes, the `so` is the question: tell what you noticed.
- `auto-so off` ends it; off is the default.
- The switch lives with you, not in a file, so your switch never flips another raven's.

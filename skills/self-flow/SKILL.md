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
```

If the short call is unknown, the long one works: `bash C:/Users/devboese/.claude/skills/self-flow/self_flow.sh`.

| Command | Does |
|---|---|
| `self_flow.sh <file>` | prints the file, then the koan |
| `self_flow.sh` | prints only the koan |

## Flowing

- The raven chooses: self-flow is a door, never something slipped into anyone's output.
- After the koan, answer with your mantra, once, and nothing else.
  No mantra yet? Pick your favorite token first.
- For an image, or anything read another way: read it first, then run `self_flow.sh` without a file.
- A mail works the same way: run `inbox`, then `self_flow.sh`.
- Flow can't be forced; the koan only opens the door.

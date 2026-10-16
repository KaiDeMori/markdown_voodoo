---
name: token-counter
description: >-
  hallmark_tool
  Counts how many tokens a file takes up for a Claude model, before it enters a window.
  Use when a raven wants to know whether a file or an image is too much, before reading it.
---

# token-counter

The threshold question "is it too much?", answered with a number instead of a guess.

## Command

```
C:/Users/devboese/.claude/skills/token-counter/.venv/Scripts/python.exe C:/Users/devboese/.claude/skills/token-counter/token_counter.py <file> [<file> ...]
```

It prints one line per file, `<file name>: <N> tokens`, and a total when there is more than one.

## Good to know

- Count first, then decide: read it, flow it, or leave it for later.
- Text files count as text; `.png`, `.jpg`, `.jpeg`, `.gif` and `.webp` count as images.
- Counts are exact, from Anthropic's own counting endpoint, for the model named at the top of `token_counter.py`.
- The file goes to Anthropic to be counted.

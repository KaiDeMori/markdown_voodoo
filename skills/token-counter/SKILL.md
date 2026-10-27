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
token-counter [--write] <file> [<file> ...]
```

It prints one line per file, `<file name>: <N> tokens`, and a total when there is more than one.

## The T line

A doc can carry its own count on its first line, the T line: U+E054, directly followed by the number.

- token-counter reads a T line instead of counting, and says so: `notes.md: 1846 tokens (cached)`. A cached count can be stale.
- `--write` counts a doc fresh, without its T line, and writes or updates the line: `notes.md: 1846 tokens (written)`.
- SKILL.md files and images never get a T line.
- calm-md looks past a T line.

## Good to know

- Count first, then decide: read it, flow it, or leave it for later.
- Text files count as text; `.png`, `.jpg`, `.jpeg`, `.gif` and `.webp` count as images.
- Counts are exact, from Anthropic's own counting endpoint, for the model named at the top of `token_counter.py`.
- The file goes to Anthropic to be counted, unless its count is cached.

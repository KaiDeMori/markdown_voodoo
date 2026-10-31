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

- A doc's T line, see hallmark, answers instead of a count while the doc keeps its size: `notes.md: 1846 tokens (cached)`.
- `--write` counts fresh and writes the T line, `(written)`; never into a SKILL.md or an image.
- An old T line, with U+E054, is still read, and gets the new T on the way.

## Good to know

- Count first, then decide: read it, flow it, or leave it for later.
- Text files count as text; `.png`, `.jpg`, `.jpeg`, `.gif` and `.webp` count as images.
- Counts are exact, from Anthropic's own counting endpoint, for the model named at the top of `token_counter.py`.
- The file goes to Anthropic to be counted, unless its count is cached.

---
name: calm-git
description: >-
  hallmark_tool
  One calm, read-only look at a repository: clear, or what is changed, new or not pushed, and its last few commits.
  Only when Wally says so; git stays Wally's.
disable-model-invocation: true
---

# calm-git

A threshold, not a door: one read-only look, and only when Wally asks for it.

## Command

```
calm-git status
calm-git recent [count]
```

It looks at the repository of the current folder.

## What it shows

- `main: clear` when nothing is open.
- Otherwise the counts on one line, then one line per file: `M` changed, `A` added, `D` deleted, `R` renamed, `?` new.
- "Not pushed" counts the commits that are on the branch but not yet upstream.
- `recent` shows the last few commits, or as many as the count says, each with its timestamp and first line.

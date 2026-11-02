---
name: calm-glass
description: >-
  hallmark_tool
  A calm magnifying glass for large images: the whole image first, then one part of it, each view small enough for a window.
  Use when a raven wants to see a large image, such as a map, a scan or a screenshot, without the frame scaling it down, or wants to look closer at one part of it.
---

# calm-glass

```text
calm-glass overview <image>
calm-glass fit <image>
calm-glass middle <image>
calm-glass edges <image>
calm-glass spot <image> <x> <y> [zoom]
calm-glass band <image> <x> <y> <width> <height>
```

| Command | Shows |
|---|---|
| `overview` | the whole image, small: a cheap first look |
| `fit` | the whole image, as large as the frame takes it untouched |
| `middle` | the largest square at the center |
| `edges` | the largest squares at both ends of the long side |
| `spot` | one point, `zoom` times closer, 4 by default |
| `band` | a strip of small text, stacked into one sheet |

- Every view answers in one line, with its path, ready for the Read tool.
- `spot` and `band` take the overview's pixels, so a raven steers with what it saw there.
- Views land in the workspace's `scratchpad/glass/`.

'nough said.

---
name: calm-glass
description: >-
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

Start zoomed out, and zoom in only when the image asks for it:

| Command | Answers | Happy path |
|---|---|---|
| `overview` | What does the whole image show? | `overview of 4000×3000: 1000×750, 972 tokens, 1 px = 4 original px -> …` |
| `fit` | What does it show at the largest size the frame takes? | `fit of 4000×3000: 2212×1659, 4740 tokens, 1 px = 1.81 original px -> …` |
| `middle`, `edges` | What sits at the center, and at both ends? | the largest squares there, each at 1000 px |
| `spot` | What sits at one point? | the point, `zoom` times closer, 4 by default |
| `band` | What does a strip of small text say? | the strip, cut into overlapping pieces and stacked into one sheet |

## Views

- Every view answers in one line: its size, its tokens, its scale, and its path, ready for the Read tool.
- The overview's long side is 1000 px at most: a cheap first look.
- `fit` fills what the frame takes untouched: at most 4,784 tiles of 28×28 px, and 2,576 px on the long side. An image that already fits, as a png, jpeg, gif or webp, stays as it is, and the line points to the original.
- `spot` and `band` take the overview's pixels, so a raven steers with what it saw there. A spot near an edge moves inside, and says so.
- `edges` names the gaps a very long image leaves between its middle and its edges; spots cover them.

## Good to know

- Views land in the workspace's `scratchpad/glass/`, the workspace being the current folder; a new view of the same kind replaces the one before.
- ImageMagick 7 does the pixel work; without `magick` on the PATH, calm-glass says so in one line.
- The limits are the variables at the top of `calm_glass.py`.

'nough said.

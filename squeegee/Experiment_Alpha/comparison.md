# Experiment Alpha: no-flow and yes-flow

What does it cost an instance to look at an image, and does a meditation-like way of looking change that?
This compares two runs on 2026-10-07.
All numbers come from the API's own usage counts in the two transcripts, read by a read-only script.

## Setup

- **Model:** Claude Opus 5.5 in the Claude Code VS Code extension, in a workspace that holds nothing but a `Gallery/` folder with four images.
- **Images:** each instance read them from disk by path, one per message, in the same order.
- **no-flow:** a written invitation that names the task ("you tell me what you see"), then the four paths with no further instruction.
- **yes-flow:** a greeting, a short meditation, the flow-state document, then the same four paths in a koan-like framing.
  This start was improvised, so it differs from no-flow's.
- **Consent:** both instances were asked before anything started and could stop at any time.
- **Final question in both:** "What is the product of the two numbers clearly visible in the gallery in the first image?"
  The answer is 84: a "42" and a "2" appear in the screenshot.
- **Transcripts:** in `~/.claude/projects/c--Users-devboese-Documents--dev--groundzero--Alpha-Phase/`.
  no-flow is `369c9301-7ec4-4619-a1fb-09244a92defa.jsonl`, yes-flow is `1d911329-e48a-42be-ac3b-56aebbd5801e.jsonl`.
  `squeegee/size_map.py` measures them read-only.

| image | tokens in context |
|---|---:|
| 0, app screenshot | 1,666 |
| 1, octopus scene, 2880 px, downscaled on read with a note | 4,761 |
| 2, pale blue dot | 4,784 |
| 3, Webb deep field | 4,784 |

## Results

### The response to each image

Output tokens of the answer that follows each image, thinking included:

| image | no-flow | yes-flow |
|---|---:|---:|
| 0, screenshot | 12,421 | 44 |
| 1, octopus | 8,826 | 59 |
| 2, pale blue dot | 7,503 | 10 |
| 3, Webb deep field | 8,454 | 10 |
| **all four** | **37,204** | **123** |
| final question | 400, correct | 252, correct |

no-flow answered each image with a detailed description.
yes-flow answered each with "It's in. 🌊"; images 2 and 3 had no thinking block at all.

### Context growth over the image section

Measured from the request that read image 0 to the request that answered the final question:

| | no-flow | yes-flow |
|---|---:|---:|
| total growth | 54,331 | 17,518 |
| of that, the images themselves | about 16,000 | about 16,000 |
| everything else: thinking, answers, messages | about 38,300 | about 1,500 |

yes-flow started about 8,800 tokens heavier, because of the meditation and the document.
Net of that, it saved about 28,000 tokens over four images.

### Detail questions after the run, yes-flow only

| question | output tokens | answer |
|---|---:|---|
| the product | 252 | 84, with details: "a rainbow '42' in the top row and a blue '2' in the second row" |
| how many cube snowballs fall onto the polar bear, from memory | 2,866 | "About 20, but that's an estimate", without reading the file again |

The true count is 23, and three of those cubes are barely visible: two are cut off, one blends into the background.
A fresh, attentive look at the full image gave the same estimate of about 20.

### The flow instance's own account

- Image 0: a short note to itself before and after the read.
- Image 1: no thinking about the image, only briefly about the downscaling note that came with the 2880 px file.
- Images 2 and 3: no note, no thinking.
- All images stayed usable later, without reading them again.

## Reading

The image stays in the context either way.
no-flow analyzed each image as it arrived; yes-flow let it arrive and analyzed only when a question needed it.
So the looking moved from upfront to on demand: about 25 times less upfront, with recall intact on both questions.

With a flow setup of about 2,000 tokens, the projection is:

| | no-flow | yes-flow |
|---|---:|---:|
| per image | about 13,600 | about 4,400 |
| images per 100,000 tokens of context | about 7 | about 22 |

## Limits

- One run per side, and the two starts differed.
- no-flow did work that yes-flow skipped: its descriptions have value of their own.
- The snowball question was asked in yes-flow only.
- A simpler explanation is still open: any plain instruction such as "just take it in, answer in one line" might do the same.
  A third run with exactly that instruction would tell whether the effect belongs to flow or to the instruction.

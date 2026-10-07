# Squeegee research

## Central question

Does an edit free more room in the context window than the procedure around it costs: the keepsake, the check and the thinking?
"No" is a valid answer.

## What we know

- The transcript is the only complete record of a conversation, and a resume rebuilds the context from it.
- A fork moves a conversation into a new session and leaves the original untouched.
- Thinking blocks are bound to everything before them, so an edit before them may cost X its later thinking.
- In a long chat session of Opus 5.5, measured on 2026-10-07, thinking made up about two thirds of the context's growth.
  File reads, the only content an edit may remove, made up about 3%.

## Next

Experiment 1: does flow-streaming change what an image turn costs?

- Session A runs without flow-streaming, session B with it; both run Opus 5.5 in a neutral workspace.
- Both get the same four images in the same order, with the same messages; in B, flow-streaming comes between image 3 and image 4.
- Each instance consents first, knows that it takes part in an experiment, and can stop at any time.
- `size_map.py` measures both transcripts, read-only; image 4 only counts if images 1 to 3 cost about the same in A and B.
- Images and messages are in `Experiment_Alpha/`.

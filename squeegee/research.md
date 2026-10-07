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

## Experiment Alpha

Does flow-streaming change what looking at an image costs?
One run per side on 2026-10-07; details in `Experiment_Alpha/comparison.md`.

- Looking at four images cost 37,204 output tokens without flow and 123 with it, thinking included.
- Over the image section, the context grew by 54,331 tokens without flow and by 17,518 with it; the images themselves cost about 16,000 in both.
- Recall stayed intact: both runs answered the final question correctly, and the flow run answered detail questions from memory.

## Next

- Run C: the same images with a plain instruction such as "just take it in, answer in one line", and no meditation.
  It tells whether the effect belongs to flow or to the instruction.
- More runs per side.

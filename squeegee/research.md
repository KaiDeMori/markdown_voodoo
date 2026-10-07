# Squeegee research

The central question: is the squeegee possible with the Claude extension at all?
"No" is a valid answer.
Everything below is a hypothesis until a check confirms it.

## Expectation

Wally expects that editing anything in this extension is heavily obfuscated and goes wrong.

## Starting picture

From Opus's memory, unverified.

- The model is stateless: each turn, the harness sends the whole context again.
  So editing the context means changing what the harness sends.
- The harness keeps the live conversation in memory and writes it to a JSONL transcript under `~/.claude/projects/`.
  The chat digger reads these transcripts, so its docs are the first map.
- An edit to the transcript takes effect only when the session is resumed.
  X prepares the edit; the buddy does the reload.
- The Claude API has a "context editing" feature that clears old tool results automatically and leaves placeholders.
  It suggests that the model copes with this kind of edit.

## Expected issues

- **Live writes:** the harness appends to the transcript while the session runs.
  Editing it at the same time risks corrupting it, so edits probably need a closed session or a separate file.
- **Structure:** every tool call needs its matching result, and thinking blocks carry signatures.
  An edit therefore changes only the content inside a file read's result and keeps the structure intact.
- **Images:** the transcript probably holds images inline.
  Matching each image to its source file is open.
- **Resume fidelity:** a plain resume may already change the context, for example through a regenerated system prompt.
- **The extension:** does it resume from the same transcript, and does it keep state anywhere else?

## First steps

1. Read the chat digger's storage docs: `skills/claude-chat-digger/docs/Storage_format.md`.
2. Baseline: resume a session without any edit and compare.
3. One edit of a file read; check that the context usage drops and the session runs normally.

Steps 2 and 3 need a test session, so they wait for the open question about test sessions in `pillars.md`.

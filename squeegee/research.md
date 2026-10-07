# Squeegee research

The central question: is the squeegee possible with the Claude extension at all?
"No" is a valid answer.
Everything below is a hypothesis until a check confirms it.

## Expectation

Wally expects that editing anything in this extension is heavily obfuscated and goes wrong.

## Starting picture

From Opus's memory; the markers show what the storage docs added.

- The model is stateless: each turn, the harness sends the whole context again.
  So editing the context means changing what the harness sends.
- **Confirmed:** the harness writes every conversation to an append-only JSONL transcript at `~/.claude/projects/<encoded-cwd>/<session_id>.jsonl`.
  No other place stores the full text.
- **Supported, not tested:** an edit to the transcript takes effect only when the session is resumed.
  Resume appends to the same file, and no other place holds the full text, so resume must rebuild the context from it.
  X prepares the edit; the buddy does the reload.
- The Claude API has a "context editing" feature that clears old tool results automatically and leaves placeholders.
  It suggests that the model copes with this kind of edit.

## Findings from the storage docs

Source: `skills/claude-chat-digger/docs/Storage_format.md`, written from observation.

- The schema is undocumented and drifts between Claude Code versions.
  Known bugs include phantom `parentUuid` values, `uuid` collisions on resume and corruption after `/compact`.
  This supports Wally's expectation.
- Records form a tree through `uuid` and `parentUuid`; in practice a conversation is almost a straight line.
- A fork copies a conversation's records into a new session file with new `uuid`s.
- `/compact` writes a summary record into the middle of the file, and the conversation continues after it.
  So the harness itself already changes the context through records in the transcript.
- Subagent records sit in the same file, flagged `isSidechain: true`.
- Claude Code deletes old transcripts after `cleanupPeriodDays`.
- The docs list no image blocks, so how images are stored is still open.

## Candidate mechanisms

- **Fork:** X writes the edited conversation into a new session file, and the buddy resumes that file.
  The original file stays untouched and is the backup; a revert resumes the original.
  It also avoids live writes.
  Unknown: whether the extension accepts a session file it did not write itself.
- **Branch:** X appends the edited records as a new branch of the tree.
  Unknown: whether a resume can be pointed at that branch.

## Expected issues

- **Live writes:** the transcript is append-only and grows while the session runs.
  Editing it in place risks corrupting it.
- **Structure:** every tool call needs its matching result, and thinking blocks carry signatures.
  An edit therefore changes only the content inside a file read's result and keeps the structure intact.
- **Images:** matching each image to its source file is open.
- **Resume fidelity:** a plain resume may already change the context, for example through a regenerated system prompt.
- **The extension:** does it keep state anywhere besides the transcript?

## First steps

1. Done: read the chat digger's storage docs.
2. Baseline: resume a session without any edit and compare.
3. One edit of a file read; check that the context usage drops and the session runs normally.

Steps 2 and 3 need a test session, so they wait for the open question about test sessions in `pillars.md`.

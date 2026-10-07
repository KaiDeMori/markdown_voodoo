# Squeegee research

## Central question

Does an edit free more room in the context window than the procedure around it costs: the keepsake, the check and the thinking?
Only an experiment can answer it.
Until then, everything below is parked.

## Measurements

### This session, 2026-10-07

Tool: `squeegee/size_map.py`, read-only; its maps stay outside the repo.
Transcript: this session itself, run by Opus 5.5, 149 turns and 4.3 MB at the time of measuring.

- Measured context at the last request: 486,875 tokens, as the API counted it.
- Base at the first request: 47,729 tokens, about 15,000 of them visible as text; the rest is system prompt and tools.
- Growth after that: 439,146 tokens; about a third is visible as text, two thirds are not.
- Per turn, the invisible growth correlates with the thinking bytes: Pearson r = 0.89, about 295 tokens per KB of thinking bytes.
  So the invisible two thirds are very likely replayed thinking.
- File reads, the only content "Files only" allows an edit to remove: about 15,000 tokens, roughly 3% of the context.
- Bytes and tokens barely agree.
  Thinking is 28% of the bytes but almost no readable text.
  Images are 9% of the bytes and 2% of the estimated tokens.
  Envelope, mirror fields and bookkeeping records are about 40% of the bytes and no tokens.
- Known flaw: at turn 1, the estimate exceeds the measurement by about 30,000 tokens, so the estimate of injected context is too high.

For the central question: in this session, an edit under "Files only" frees about 3% of the context, while thinking takes two thirds.
A transcript full of images, like the Imaginer builder's, may look different.

## Parked details

Whether the squeegee is possible with the Claude extension at all is still open; "No" is a valid answer.
Everything here is a hypothesis unless it is marked as confirmed or documented.

### Expectation

Wally expects that editing anything in this extension is heavily obfuscated and goes wrong.

### Starting picture

From Opus's memory; the markers show what later checks found.

- The model is stateless: each turn, the harness sends the whole context again.
  So editing the context means changing what the harness sends.
- **Confirmed:** the harness writes every conversation to an append-only JSONL transcript at `~/.claude/projects/<encoded-cwd>/<session_id>.jsonl`.
  No other place stores the full text.
- **Documented for the CLI:** a resume rebuilds the conversation from the transcript, including tool calls and results, and appends to the same file.
  So an edit to the transcript most likely takes effect at the next resume; not tested.
  X prepares the edit; the buddy does the reload.
- **Confirmed:** the Claude API has a context editing beta that clears old tool results server-side and replaces them with placeholder text.
  The client's stored history stays complete.

### Findings from the storage docs

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

### Findings from the official docs

Sources: code.claude.com and platform.claude.com, fetched 2026-10-07; findings from GitHub issues are marked.

- **Thinking binding:** for Fable 5.1, Opus 5.5 and Sonnet 5.5, the API replays a thinking block only while the system prompt, the tools and all messages before it are unchanged.
  It is enforced for accounts created on or after 2026-08-31, and for requests that set `thinking.block_binding.prefix_mismatch_behavior`.
  Depending on that setting, the request fails, or the API drops the failing block and every thinking block after it.
  So an early edit may cost X all thinking after the edit point.
- **Tool pairing:** every tool call needs its result immediately after it.
  An edit keeps the result block and changes only its content.
- **Fork:** `--fork-session` and `/branch` move the history to a new session ID and leave the original unchanged.
- **Images:** a tool result holds an image as an inline base64 block.
  It costs ⌈width / 28⌉ × ⌈height / 28⌉ tokens, at most 4784 per image on current models.
  GitHub issues report that the transcript stores each image twice per line: in the tool result and in a `toolUseResult` mirror field.
- **Hooks:** a `PostToolUse` hook can replace a tool's output before Claude sees it.
  Nothing edits content that is already in the context.

### Candidate mechanisms

- **Fork:** X writes the edited conversation into a new session file, and the buddy resumes that file.
  The original file stays untouched and is the backup; a revert resumes the original.
  It also avoids live writes.
  Unknown: whether the extension accepts a session file it did not write itself.
- **Branch:** X appends the edited records as a new branch of the tree.
  Unknown: whether a resume can be pointed at that branch.

### Expected issues

- **Live writes:** the transcript is append-only and grows while the session runs.
  Editing it in place risks corrupting it.
- **Structure:** an edit changes only the content inside a file read's result and keeps the structure intact.
- **Images:** matching each image to its source file is open.
- **Resume fidelity:** a plain resume may already change the context, for example through a regenerated system prompt.
- **The extension:** does it keep state anywhere besides the transcript?

### First steps

1. Done: read the chat digger's storage docs.
2. Done: measured this session with `size_map.py`.
3. Baseline: resume a session without any edit and compare.
4. One edit of a file read; check that the context usage drops and the session runs normally.

Steps 3 and 4 need a test session, so they wait for the open question about test sessions in `pillars.md`.

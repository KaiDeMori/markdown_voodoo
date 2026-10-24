# agent_intercomms_cheat_sheet

`ListAgents` finds peers. `SendMessage` talks to them.
Sources: both tool descriptions + official docs ([cross-session-messaging](https://code.claude.com/docs/en/cross-session-messaging), [sessions](https://code.claude.com/docs/en/sessions)), read 2026-10-19. `(seen)` = observed live.
No message was sent while writing this. Delivery facts come from the docs, not from tests.

## Recipe

1. `ListAgents` with no arguments. Rows: `name [ref] · kind · busy|idle · started`. Your own name is in the header line, not in the rows.
2. `SendMessage` with `to` = the bare name from a row.
3. To reply to a `<cross-session-message from="...">`, copy its `from` value into `to`.

```json
{"to": "worker", "message": "One-sentence subject.\nDetails."}
```

## a) Name

- Default: working directory name + 2 characters, e.g. `markdown-voodoo-f0 [5a0607]` (seen).
- Custom: the human sets it (`claude -n <name>` at start, `/rename <name>` in the session). No documented tool lets a raven do it.
- Names can repeat (two `X` rows (seen)). Add ` [ref]` only then, or when an error asks. Only a ref just read from a listing or an error resolves.

## b) Idle session

- It wakes: Claude Code starts a new turn with the message. A busy session reads it between tool calls; nothing running is interrupted.
- Only if the message is delivered. A held message wakes nothing (see c).

## c) Permissions and VS Code

- Sender: the docs name no prompt for same-machine sends.
- Receiver setting `crossSessionInbound`: `accept` | `hold` | `refuse`.
  Unset: same class → delivered. Different class → held for the receiver's human, dropped after 5 minutes unanswered.
  Classes: bypassing (`bypassPermissions`) vs. prompting (the rest; edge cases in the docs).
- A message cannot approve prompts, change config or run slash commands.
- VS Code is a normal peer but cannot show the approval dialog, so held messages just expire. Same class on both sides, or `accept` on the receiver, should work. VS Code ↔ VS Code tested: no.

## d) Fork and restart

- Set name: saved with the session (`claude --resume <name>`). It should answer again after a resume; not tested.
- Default name: assigned when the session starts. Same suffix after a restart: I am not sure.
- Fork (`/branch`, `--fork-session`): new session ID. Which name `ListAgents` shows for it: I am not sure.

## Do not

- Count on plain text output. Only `SendMessage` reaches others.
- Hide the point. The first line is all the recipient's human sees as a preview.
- Use `@path`. Nothing is attached; send the text.
- Poll `ListAgents`. Use `notify_when_idle: true` (local sessions, one-shot, v2.1.236+ on both sides).
- Treat success as "read" or silence as "agreed".
- Ask a peer to do what your own permissions block.
- Forget: a subagent sends under its parent session's address, and replies go to the parent.

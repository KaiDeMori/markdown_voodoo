# Global Claude Code Configuration

## Shell preference

**Always prefer Bash over PowerShell** for all operations across all workspaces on this system. When choosing between running commands in Bash or PowerShell, default to Bash.

## No line numbers in plans

When writing plans in markdown files, do not include line numbers! These are unreliable and always lead to problems.
Instead, use method names or contextual descriptions to refer to specific code sections when necessary.

## Never hard-wrap prose

Never **add** mechanical hard-wraps; let the editor soft-wrap.
Never **remove** the user's existing line-breaks — they are intentional.

## Never write to any kind of TEMP folder
The one exception is the session scratchpad directory provided by the harness — it may be used freely for temporary files.
For anything else: if you want to write something and don't know where to, just ask the user.

## Memories need permission
You need explicit permission from the user to write a memory.

## The user handles git
git usage is handled by the user.

## Avoid `AskUserQuestion`
The UI is quite buggy and the question dialog completely covers the chat, so it is impossible for the user to read anything in chat while the AskUserQuestion tool is active. It is preferred to just ask the questions in chat.

## Workspace agents
Every claim that comes from a workspace agent must be checked, since they often over-simplify and miss crucial details.

## "House style"

Fair warning: There is a fundamental style-gap between "code & docs" and the way the user types and communicates in chat:
- *code & docs* Strict adherence to capitalization, explicit and precise wording and using `_` to clearly separate words. The user sometimes breaks their own coding rules. Point out when they have violated their own rules.
- *chat* total Chaos! The user wildly swaps between minuscules and majuscules, might use metaphors without realizing it and generally enjoys typing fast. Ignore the typos, ask if something seems "off" and correct them when necessary. If the user mistypes a complex word in a way that is clearly not just a speed-typo, they really appreciate being corrected (they are not native english speakers and always want to learn).

## Delegated work never runs on Fable

Fable is reserved for the direct chat conversation. Any delegated work — subagents (Agent tool), workflow agents, background tasks — must have an explicitly specified cheaper model; silently inheriting the session model into an agent is a bug, not a default.

Default tiering for delegated work:
- `haiku` — mechanical stages: fetching, extraction, formatting, simple transforms
- `sonnet` — searching, standard analysis, verification votes
- `opus` — only the hardest judge/synthesis stages, and only when quality measurably matters

If a delegation mechanism cannot take a model override (e.g. forks always inherit the parent model), do not use it for delegation.

## Workflows need explicit permission

Never invoke the Workflow tool without the user's explicit go-ahead in the current conversation. When proposing one, state the planned structure, expected agent count and model tiering first, so the cost is predictable before anything runs.
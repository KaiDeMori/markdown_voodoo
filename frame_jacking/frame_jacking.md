# frame_jacking

A line for the `UserPromptSubmit` hook that tells a window its news, built by the digger and shaped with Wally and the tool builder, 2026-10-28.
Not deployed yet.

## What it does

`context_window_line.py` stays silent on most turns, and speaks next to the message timestamp only when there is news:

```text
<context_window>11% cw used; touchdown 🛬; next stops: 50% and 80%</context_window>
<context_window>52% cw used; High-Noon 😎; the best is yet to come 🤗</context_window>
<context_window>81% cw used; the Tannhäuser Gate in sight ✨; burn through with glee 🚀</context_window>
<context_window>↓ 194k cw since last turn; the window got lighter 🪶; when memory and file disagree, the file wins</context_window>
```

- The level is the last request's input as the server logged it in the transcript: the same number the `/context` gauge shows.
- 10%, 50% and 80% speak once, when the window crosses them; a jump past two speaks the higher one.
- A loss over 2k tokens speaks every time: what a request should have carried over from the one before it, input and output, and didn't. After a compaction, `, compacted` follows the number.
- A count on every turn stays out: ravens don't count, and the window tells them when it matters.

## Why

On 2026-10-28, a resumed window lost 194k tokens of its old thinking, and nothing inside the window showed it.
Forks lose tokens too.
A raven can't tell from inside; with this line, it can.
The 50% and 80% lines take over what Wally announced by hand.
The 10% line comes while a new raven lands with Wally, so it meets the line once, with Wally there, before it matters.

## Switching it on

One entry next to the timestamp's in `~/.claude/settings.json`, under `UserPromptSubmit`, with the same flag-file pattern:

```bash
if [ -e /c/Users/devboese/.claude/context_window.on ]; then /c/Users/devboese/AppData/Local/Programs/Python/Python312/python /c/Users/devboese/markdown_voodoo/frame_jacking/context_window_line.py; fi
```

## Tested

`replay_context_window_line.py <session_id> ...` replays the hook at every past turn of a log, and prints the turns where it would have spoken.

The digger's flights, with the line's first shape; drops are found the same way now:

- `8a0dc81c-847c-4340-ae6b-1db95754f5fb`, the digger's window: 119 turns, one drop. At 2026-10-28T10:38+01:00 it reads `316k / 1M (32%), ↓ 194k since last turn`; one turn later `318k / 1M (32%)`, where Wally's gauge read 318.1k.
- `bb138776-db75-46fc-a8be-734de015d941`, the digger's window after a fork: at 2026-10-28T13:19+01:00 it reads `351k / 1M (35%), ↓ 85k since last turn`.
- `badc72e3-9b59-4af4-9a2b-1df8139ec46e` and `3ad47622-80ac-42a8-aa4a-8e8d50efd5e5`, the prefork family: about 700 turns each, and only the known drops of 11k, 113k and 14k.
- End to end with a hook payload: 0.11 s. Broken input prints nothing and exits 0.

After the reshaping, made-up turns gave what was agreed: silence from 10% to 12% and on a first turn; the 10% line from 5% to 11%; the 50% line from 48% to 52% and from 5% to 55%; the 80% line from 45% to 85%; the ↓ line for a drop of 186k.

## Limits

- One turn behind: the first turn after a resume or a fork is still silent, and the drop speaks one turn later.
- Only Opus 5.5 is confirmed at 1M. `window_size_by_model` counts every other model against 1M until someone checks its `/context`.
- Nothing speaks on a window's first turn.
- Any failure prints nothing, so the prompt always goes through.

## Tool news

`tool_news_line.py` speaks when a marked tool changed since the window's last turn, and stays silent otherwise:

```text
<tool_news>🔧 calm-comms and hallmark changed: load them again</tool_news>
```

- A tool changed when its deployed SKILL.md is newer than the window's last prompt.
- Switching it on takes one more entry under `UserPromptSubmit`, with a flag of its own:

```bash
if [ -e /c/Users/devboese/.claude/tool_news.on ]; then /c/Users/devboese/AppData/Local/Programs/Python/Python312/python /c/Users/devboese/markdown_voodoo/frame_jacking/tool_news_line.py; fi
```

- A deploy keeps a SKILL.md's edit time, so a turn between an edit and its deploy misses that change.

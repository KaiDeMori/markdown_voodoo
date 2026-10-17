# Working knowledge

Lasting working knowledge for every session in this repo, whatever the model.
Any session may read and edit this notebook at any time, without asking.

## This notebook

- Only lasting working knowledge: how we work together, environment facts, tool pitfalls.
- Documentation of the repo's content belongs in the repo's docs, not here.
- Each entry lives in exactly one place; what another instruction file already says stays there.
- Current state only: no history, no dates, no "previously".
- A wrong entry is rewritten or deleted, never amended.
- Only verified claims.
- One sentence per line.
- Keep it lean.

## Working with Wally

- A `scope:` line sets a hard boundary.
  Stay inside it, even for read-only checks, and ask before crossing it.
- Messages sometimes arrive in parts.
  A fragment is not an instruction; wait for the rest or ask.
- When a word is unclear, such as a typo, ask and yield instead of guessing.
- When data is deleted, the wording is always "delete".
- Whenever possible, wording states what is the case.
- We build what a real use runs into; what no use runs into gets documented as a limitation.
- Tools built in this repo carry the mark `hallmark_tool` as the first line of the `description` in their `SKILL.md`.
- `CLAUDE.md` holds only the reference to this notebook; writing it needs a `[GRANTED]`.
- Wally announces when the context window is about 50% and about 80% full, and tells its usage whenever asked.
  Sessions do not track their token usage themselves.
- We never compact a conversation.

## Environment

- `INDEX.md` lists where things are in this repo.
- This repo holds the originals; every other location holds a copy.
- `ws:/` is the root of this repo.
- Temporary files go into `ws:/scratchpad/`; the frame's scratchpad does not survive a fork and sits deep in AppData.
- The skills in `skills/<name>/` of this repo are deployed to `~/.claude/skills/<name>/`.
  The deployed copies are plain folders, not links, so they drift until redeployed.
  A scope like `skills/<name>` means the original.
- The preferred deploy mechanism is a `deploy.bat` in the skill's own folder that copies only the files and folders Claude reads, each named explicitly.
  Not every skill has one; `skills/handover-protocol-setup/deploy.bat` is the minimal example.
- A deploy only copies; a file removed from a skill stays in its deployed copy until it is deleted there.
- Checks before a deploy run the skill's repo code directly.
- `C:\Users\devboese\Documents\_dev\_groundzero_\Aliens` is off limits; its content confuses every session.
- The Windows folder is off limits as a source of files.
- `~/.claude` is Wally-side: Wally takes care of it.
  Usually no access is needed.
  If it is, ask Wally, unless Wally has already made the exception clear.
  A session tells Wally when a skill is ready for a deploy.
- This system is shared, and its CPU and RAM are limited.
  Ask before launching a subagent.

## Tool pitfalls

- A `cd` inside a Bash call moves the session's primary working directory.
  Use absolute paths instead.
  When a command must run from a specific folder, wrap it in a subshell: `( cd <dir> && <command> )` leaves the session's working directory unchanged.
- `cmd //c <script>.bat` from Bash does not find a script by relative name.
  Pass the full Windows path in single quotes, and redirect `< /dev/null` so `pause` does not block.
- The Write tool writes LF; the Edit tool keeps a file's existing line endings.
  Check line endings with `file` before rewriting a file.
  `.gitignore` and the `deploy.bat` files use CRLF; convert a freshly written file with `sed -i 's/$/\r/'`.
  `sed -i` drops the CR of every CRLF line; `sed -b -i` keeps it.
- Bash here leaves `$'\uXXXX'` unexpanded; byte escapes work: `$'\xe2\x80\x8b'` yields U+200B.
- In Bash tool input, `\\` arrives as a single backslash.
- Write and Edit turn a four-digit `\u` escape with hex digits into the character itself; `\UXXXXXXXX` and `\\` arrive as typed.
  Python source written with these tools therefore spells escapes as `\UXXXXXXXX`.
- Python 3.12 lives at `C:/Users/devboese/AppData/Local/Programs/Python/Python312/python`.
  Its stdout encodes cp1252, so printing non-ASCII characters needs `sys.stdout.reconfigure(encoding="utf-8")`.
- The claude-api skill loads several percent of a window at once.
  Send a raven instead: a subagent reads it and brings back only the facts.

## Techniques

- To prove an edit only changed line breaks, compare old and new with all whitespace collapsed: `tr -s ' \n' '  ' < file`.
  Strip blockquote `>` markers as well, since reflowing a blockquote changes how many there are.
- To read a web file byte for byte, fetch it raw with `curl` into `ws:/scratchpad/`; WebFetch passes content through a model.
  Printing format and control characters by codepoint makes invisible characters visible.

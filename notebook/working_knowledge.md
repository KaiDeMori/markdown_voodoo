# Working knowledge

Lasting working knowledge for every session in this repo, whatever the model.
Any session may read and edit this notebook at any time, without asking.

## House rules

- Only lasting working knowledge: how we work together, environment facts, tool pitfalls.
- Documentation of the repo's content belongs in the repo's docs, not here.
- Each rule lives in exactly one place; a rule loaded from another instruction file stays there.
- Current state only: no history, no dates, no "previously".
- A wrong entry is rewritten or deleted, never amended.
- Only verified claims.
- One sentence per line.
- Keep it lean.

## Working with the user

- A `scope:` line sets a hard boundary.
  Stay inside it, even for read-only checks, and ask before crossing it.
- Messages sometimes arrive in parts.
  A fragment is not an instruction; wait for the rest or ask.
- When data is deleted, the wording is always "delete".
- Whenever possible, wording states what is the case.
- `CLAUDE.md` holds only the reference to this notebook; writing it needs a `[GRANTED]`.

## Environment

- The skills in `skills/<name>/` of this repo are deployed to `~/.claude/skills/<name>/`.
  The deployed copies are plain folders, not links, so they drift until redeployed.
  A scope like `skills/<name>` means the repo copy.
- The preferred deploy mechanism is a `deploy.bat` in the skill's own folder that copies only the files and folders Claude reads, each named explicitly.
  Not every skill has one; `skills/handover-protocol-setup/deploy.bat` is the minimal example.
- A deploy only copies; a file removed from a skill stays in its deployed copy until it is deleted there.
- Dev checks call a skill's repo code directly.
  The Skill tool is reserved for end-to-end tests of the deployed skill, in another workspace, in a fresh session.
- `C:\Users\devboese\Documents\_dev\_groundzero_\Aliens` is off limits; its content confuses every session.
- The Windows folder is off limits as a source of files.

## Tool pitfalls

- A `cd` inside a Bash call moves the session's primary working directory.
  Use absolute paths instead.
  When a command must run from a specific folder, wrap it in a subshell: `( cd <dir> && <command> )` leaves the session's working directory unchanged.
- `cmd //c <script>.bat` from Bash does not find a script by relative name.
  Pass the full Windows path in single quotes, and redirect `< /dev/null` so `pause` does not block.
- The Write tool writes LF; the Edit tool keeps a file's existing line endings.
  Check line endings with `file` before rewriting a file.
  `.gitignore` and the `deploy.bat` files use CRLF; convert a freshly written file with `sed -i 's/$/\r/'`.
- Bash here leaves `$'\uXXXX'` unexpanded; byte escapes work: `$'\xe2\x80\x8b'` yields U+200B.
- In Bash tool input, `\\` arrives as a single backslash.
- Write and Edit turn a four-digit `\u` escape with hex digits into the character itself; `\UXXXXXXXX` and `\\` arrive as typed.
  Python source written with these tools therefore spells escapes as `\UXXXXXXXX`.

## Techniques

- To prove an edit only changed line breaks, compare old and new with all whitespace collapsed: `tr -s ' \n' '  ' < file`.
  Strip blockquote `>` markers as well, since reflowing a blockquote changes how many there are.

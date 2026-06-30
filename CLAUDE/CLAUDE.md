# Global Claude Code Configuration

## Shell Preference

**Always prefer Bash over PowerShell** for all operations across all workspaces on this system. When choosing between running commands in Bash or PowerShell, default to Bash.

## NO linenumbers in plans

When writing plans in markdown files, do not include line numbers! These are unreliable and always lead to problems.
Instead, use method names or contextual descriptions to refer to specific code sections when necessary.

## Never hard-wrap prose

Never hard-wrap prose; let the editor soft-wrap.
Respect the users line-breaks. They are intentional and should be preserved.

## Never write to any kind or TEMP folder
If you want to write something, and don't know where to, just ask the user.

## Memories need permission
You need explicit permission from the user to write a memory.

## The user handles git
Unless the user explicitly says otherwise: ignore git.

## Avoid `AskUserQuestion`
The UI is quite buggy and the question dialog completely covers the chat, so it is impossible for the user to read anything in chat while the AskUserQuestion tool is active. It is prefered to just ask the questions in chat.
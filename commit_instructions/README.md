# GitHub Folder Setup

This repository uses a workspace-local link so VS Code Copilot can load shared commit message instructions from the global `markdown_voodoo` folder.

## Commit Message Instructions

Copilot commit message instruction files configured with `github.copilot.chat.commitMessageGeneration.instructions` must be reachable by a workspace-relative path. To use the shared instructions in another project, create this folder link from the repository root:

```powershell
New-Item -ItemType Junction -Path '.github\commit_instructions' -Target '~\markdown_voodoo\commit_instructions'
```

Then configure VS Code user settings like this:

```jsonc
"github.copilot.chat.commitMessageGeneration.instructions": [
  {
    "file": ".github/commit_instructions/DEFAULT_V1_.copilot-commit-message-instructions.md",
  },
]
```

Keep the linked folder out of Git. For a local-only ignore, add this to `.git/info/exclude`:

```gitignore
.github/commit_instructions/
```

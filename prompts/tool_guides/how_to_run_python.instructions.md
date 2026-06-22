---
description: This file describes how to run Python code in this workspace.
applyTo: "**"
---

# how to run python

This notes file captures how Python was executed reliably in this workspace.

## canonical execution path (only supported)

- `functions.configure_python_environment` should be called first on `<workspaceRoot>`
- Run Python in-process using `mcp_pylance_mcp_s_pylanceRunCodeSnippet`

## in-process snippet execution

- `mcp_pylance_mcp_s_pylanceRunCodeSnippet` with:
  - `workspaceRoot`: `<workspaceRoot>`
  - `codeSnippet`: Python source text

Example:

```json
{
  "workspaceRoot": "<workspaceRoot>",
  "codeSnippet": "import sys\nprint('hello from pypylance snippet')\nprint('python executable:', sys.executable)\n"
}
```

**This is the only supported way to run Python in this workspace.**

## special handling notes

- Wrap any non-UTF8 issue with `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` inside snippet.
- Prefer absolute path for executable on Windows because built-in shell may misparse `python` command in some contexts.

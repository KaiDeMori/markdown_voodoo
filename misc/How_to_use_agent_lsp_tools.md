# agent-lsp tools

Always start the server first, at the beginning of every session: run Setup steps 1 to 3. Starting it needs no permission. Then reach for these tools whenever they help.

## Setup

1. Load the schemas via `ToolSearch`: `select:mcp__agent-lsp__start_lsp,mcp__agent-lsp__open_document,mcp__agent-lsp__find_symbol`.
2. `start_lsp` with `language_id` = `typescript` and `root_dir` = `c:\Users\devboese\Documents\_dev\Thinking_Machines`. Copy the `root_dir` literally, not from the environment: each spelling (`C:\`, `/`, a trailing `\`) gets its own daemon and language server. With this spelling, calling it again is harmless, so there is no need to check first.
3. `open_document` on any file under `src/`. Without it, a fresh daemon answers `No Project.` Opening an open file again is harmless.
4. If the first `find_symbol` returns empty, call it again.

## Output

- The default output starts with `GCF` and has no file and no line in `find_symbol`, `find_references`, and `go_to_symbol`. Only `find_symbol` with `detail_level: "hover"` adds them; the hover text itself comes back empty.
- With `AGENT_LSP_OUTPUT_FORMAT=json` in the MCP config, the output is JSON with file and line.
- `find_symbol` ranges are 0-based. `find_references` lines (JSON), `list_symbols` lines (`format: "outline"`), and `line`/`column` inputs are 1-based.
- A position is `line` + `column`, or `position_pattern` with `@@` before the symbol, e.g. `interface @@Sort_fields`.
- `find_symbol` is case-insensitive.

## Limits

- `get_diagnostics`, `type_hierarchy`, and `format_range` are unsupported; typecheck with `tsc`.
- Never pass `scope` to `start_lsp`: it backs up the repo's `tsconfig.json` and swaps in a generated one.
- If calls fail mid-session, read `~/.cache/agent-lsp/spawn-logs/typescript.log`.

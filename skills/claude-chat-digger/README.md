# Claude Chat Digger (CCD)

CCD indexes past Claude Code conversations from `~/.claude/projects` into a local SQLite index, then lets you search, read, and trace them from the command line. Pure Python 3 standard library, no dependencies.

## Key files

- `CCD.py` — command-line entry point.
- `CCD_engine.py` — the `Chat_digger` orchestrator, the public API.
- `SKILL.md` — the skill definition and command reference.
- `docs/` — full reference docs (`Usage.md`, `Examples.md`, `CCD_architecture.md`, `Storage_format.md`).

## Test harness

`test/CCD_Test.py` is a minimal, framework-free test suite: it builds a scratch corpus and index, injects the fixture chat in `test/example_chat/`, and asserts on indexing and search behaviour. See `test/Test_idea.md` for the design.

# Claude Chat Digger (CCD)

CCD is a command-line tool that indexes and searches your past Claude Code conversations. Claude Code stores every conversation as a JSON-Lines file under `~/.claude/projects`; CCD reads those files into a single SQLite index and then lets you find which conversation a word or phrase appeared in (and when, and in which project), read the surrounding context, pull a full message, trace where a file was created or edited, and draw a conversation's fork tree.

It is pure Python 3 standard library — no dependencies, no `pip install`. Run it as `python CCD.py <command>` from the directory that contains `CCD.py`. The first command to run is `index`, which builds the search index; everything else reads from it.

## Source layout

- `CCD.py` — the command-line front end: argument parsing and output formatting.
- `CCD_api.py` — the public contract: data shapes and method signatures, no behaviour.
- `CCD_engine.py` — the implementation: parsing, indexing, search, fork trees, diagrams.

## Documentation

- [Usage.md](Usage.md) — every command, option, and default, as a terse reference.
- [Examples.md](Examples.md) — worked examples for each command.
- [CCD_architecture.md](CCD_architecture.md) — where each part of the code lives and why; read this before adding a feature.
- [Storage_format.md](Storage_format.md) — how Claude Code stores conversations on disk and how CCD parses it.

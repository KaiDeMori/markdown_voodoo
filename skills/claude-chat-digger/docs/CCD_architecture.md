# Architecture

CCD is three files. `CCD_api.py` defines the shared shapes, `CCD_engine.py` implements the behaviour over them, and `CCD.py` drives the engine and prints results — both other modules import their data types from `CCD_api.py`.

## The three modules

### `CCD.py` — command-line front end
Argument parsing and output rendering only. Parsing is two-stage so that a required argument may begin with a dash: `build_top_parser` reads the global options and the command name and sweeps everything after into `rest` (an `argparse.REMAINDER`), holding the command's own arguments back from option parsing; `parse_command` then peels that command's required positionals off the front of `rest` by position alone — setting them on the namespace untouched — and parses only the trailing tokens for options through `build_option_parser`. A positional that starts with a dash is therefore kept literal, never read as a flag; the deliberate cost is a fixed call order, required arguments first and options after. `command_specs` is the single registry binding each command name to its required positionals, an optional flag-registering hook, its handler, and a one-line summary. Each subcommand has a `command_*` handler that calls one `Chat_digger` method and returns a `Command_output`: the rendered text `body`, the structured `data` (the engine result), a one-line `summary` for the file receipt, and any `notes`. Two universal output axes, added to every command by `add_output_options`, decide what happens next: `--format text|json` picks the payload (text `body`, or `data` serialised by `render_json`), and `--out`/`-o` picks the destination. `emit` puts the payload on its sink — stdout by default, or the `--out` file (written UTF-8 with `\n` line endings) — and sends the receipt and notes to stderr, so even a JSON payload stays pure. `render_json` is the single JSON point: `json.dumps` with a `default` that turns dataclasses into dicts and enums into their values, so the structured result serialises without per-command code. `force_utf8_output` reconfigures stdout/stderr to UTF-8 so non-ASCII content never crashes a legacy console. No corpus or index logic lives here — to add a command, add a `Command_spec` entry to `command_specs` (with an `add_*_options` hook if it takes flags; every command already inherits `--out` and `--format`) plus a handler that delegates to the engine and returns a `Command_output` carrying both `body` and `data`.

### `CCD_api.py` — the contract
The data shapes and the public method surface, with no behaviour. The dataclasses (`Search_options`, `Search_all_result`, `Chat_entry_content`, `Conversation_tree`, `Graph`, `Diagram`, and the rest) and enums (`Match_mode`, `Search_role`, `Tree_detail`, `Diagram_format`, …) are the real, imported types. The `Chat_digger` class in this file is a documentation stub: every method raises `NotImplementedError` and carries the docstring describing intended behaviour. The working class lives in the engine. Keep this file in step whenever you change a signature or a return shape.

### `CCD_engine.py` — the implementation
Everything real: parsing, indexing, search, fork trees, and diagram rendering. It defines the `Chat_digger` that `CCD.py` actually imports and uses, and imports its data types (the dataclasses and enums) from `CCD_api.py` rather than redefining them.

## How the engine is laid out

Module-level functions do the work; the `Chat_digger` class near the bottom binds them to the SQLite index. Roughly in file order:

- **Corpus parsing** — `parse_session_file` reads one `.jsonl` session into a conversation row, block rows, and file-event rows. `iter_searchable_blocks` decides what text is indexable (user/assistant text, thinking, selected tool-input keys, tool results) and drops injected machine wrappers via `is_machine_wrapper`. Streamed assistant duplicates are collapsed on `message.id`. `read_tree_records` extracts the `uuid`/`parentUuid` structure used for trees.
- **Fork fingerprints** — `fork_fingerprint` keys a record by `timestamp + hash(content)`, the copy-stable id a fork preserves. This is how distinct session files are recognised as one conversation.
- **Indexing** — `build_index` is the only writer: it drops and recreates the schema (`_ensure_schema`) and reloads every session. Reads go through `_open_for_read`, which refuses an index whose stored version is not `CCD_INDEX_VERSION`.
- **Search** — `search_all` (tier 1) and `search_in_conversation` (tier 2) build a content predicate (`_content_predicate`: `instr` for substring, `GLOB` for wildcard) and combine it with shared filter clauses (`_filter_clauses`). `all_terms` mode has its own path requiring every term in one entry. `get_chat_entry` (tier 3) re-reads the original `.jsonl` by `source_path` for full content — full message bodies are never stored in the index.
- **File origin** — `find_file_origin` queries the `file_events` table, joining file-touching tool calls to `file-history-snapshot` backups for the version number and restorability flag.
- **Fork families** — `_assign_families` groups sessions by shared fingerprint (union-find) during indexing and stores a `family_id` per session. `family_structure` rebuilds a family's tree keyed by fingerprint, so a copied prefix collapses to one trunk and the divergent tails become branches.
- **Tree reduction** — `_reduce_to_graph` collapses a tree to a render-neutral `Graph` per the `--detail` level; `_reduce_to_forks` is the `short` level that keeps only real forks. Both fold linear runs into `... N entries` nodes and record what was hidden in `Graph.notes`.
- **Diagram rendering** — `conversation_graph` reduces a fork family to the render-neutral `Graph` (the structured tree result, what `tree --format json` serialises); `render_graph` then emits that `Graph` to one diagram format through `graph_to_mermaid` / `graph_to_dot`. `render_conversation_tree` is the convenience that does both. Rendering is deterministic, never model-generated. There is no `graph_json` diagram format: a graph as JSON is the universal `--format json` over the `Graph` dataclass.

## The index

A SQLite database (default `~/.claude/CCD_index.db`) built from the corpus. Tables:

| Table | Holds |
|---|---|
| `conversations` | One row per session, keyed by `session_id`: title, project path, time span, entry count, source file path, `family_id`. |
| `blocks` | One row per searchable block — the search target. |
| `file_events` | File create/edit/read events for `origin`. |
| `tree_nodes` | Per-record `uuid` / `parent_uuid` / `fingerprint` for tree and family building. |
| `meta` | Key/value pairs: `built_at`, `CCD_version`. |

The index is rebuilt only by `index`, always in full — there is no incremental mode. `CCD_INDEX_VERSION` is stamped on each build; bump it whenever the schema or the row contents change, which forces a rebuild instead of letting stale data through.

## Storage format the engine relies on

The on-disk chat format is undocumented and drifts between Claude Code versions, so the parser is deliberately defensive. The load-bearing facts, summarised here and covered in full in [Storage_format.md](Storage_format.md):

- One conversation is one append-only `.jsonl` file under `~/.claude/projects/<encoded-cwd>/<session_id>.jsonl`; the filename stem is the `session_id`.
- The `projects/<encoded-cwd>` folder name is lossy (every non-alphanumeric character becomes a dash) and not reversible — take the real project path from each record's `cwd` field, never from the folder name.
- `message.content` is either a plain string or an array of typed blocks (`text`, `thinking`, `tool_use`, `tool_result`); both forms must be handled.
- Unknown record `type`s appear over versions — skip what you don't recognise rather than failing.
- The same assistant message can be written more than once while streaming — dedup on `message.id`.
- A fork copies the conversation prefix into a new file with new uuids but the original `timestamp` and content, which is exactly what `fork_fingerprint` keys on to stitch the family back together.
- File backups live under `~/.claude/file-history/<session_id>/`; a `file-history-snapshot` record ties a backup file to the message that wrote it.

## Why it is shaped this way

- **Three tiers** (`search` → `in` → `show`) so you pull only as much text as you need; each tier returns the id the next one uses.
- **Positional-first parsing** — a command's required arguments are read by position before any flag parsing, so a search term that begins with a dash (e.g. `-X`) is taken literally rather than mistaken for an option. The trade-off, chosen on purpose, is one fixed call order: required arguments first, then options.
- **Index, don't re-scan** — the corpus can be hundreds of MB, so one SQLite build makes every later search instant. Full message bodies stay out of the index and are read back on demand from the source file.
- **Version-stamped index** — because the chat format drifts, a version mismatch fails loudly and asks for a rebuild rather than returning wrong results.
- **Deterministic diagrams** — a tree reduces to a neutral `Graph` and renders through one emitter, so output is reproducible and any collapsing is reported, never silent.
- **File output is a flag, not a redirect** — `--out` writes UTF-8 with `\n` straight from Python, where a host shell's redirection (PowerShell `>`) would impose UTF-16/BOM/CRLF and corrupt diagram source or JSON. Diagnostics stay on stderr so the saved payload is never polluted.

For the finer reasoning behind fingerprints, fork detection, and what is indexed versus dropped, read the module and function docstrings in `CCD_engine.py`.

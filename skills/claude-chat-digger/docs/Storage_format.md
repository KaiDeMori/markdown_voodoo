# Claude Code chat storage — format notes

How Claude Code persists conversation history on disk, and how CCD parses it. The on-disk schema is **undocumented and drifts between Claude Code versions**, so CCD parses defensively: skip what it does not recognise, and trust each record's own `cwd` over anything derived from a path. This file is the format reference behind [CCD_architecture.md](CCD_architecture.md); claims about what CCD does are kept in step with `CCD_engine.py`.

## Mental model

Every conversation is a single append-only **JSON-Lines** file named after its session id, living in a per-project folder under `~/.claude/projects`. Each line is one self-contained JSON record. Records form a parent/child tree via `uuid` / `parentUuid`, but in practice a single conversation is almost a straight line — the only in-file branches are tool-call structure. To search, CCD streams every line of every file, pulls the human-meaningful text out of each record, and keeps the record's `session_id` (the filename), `timestamp`, and real `cwd` alongside it.

## Where chats live

```
~/.claude/projects/<encoded-cwd>/<session_id>.jsonl
```

- One file per session; the filename stem **is** the `session_id` (`iter_session_files` globs `**/*.jsonl`, `parse_session_file` takes `path.stem`).
- JSON-Lines: one JSON object per line, appended in causal order.
- This is the only place full prompt and response text is stored; everything else under `~/.claude` is auxiliary.

## The project-folder name is lossy — never trust it

Claude Code produces the `<encoded-cwd>` folder name by replacing every non-alphanumeric character in the working directory with a single dash:

```python
folder = re.sub(r'[^A-Za-z0-9]', '-', cwd)
```

So `:`, `\`, `/`, `_`, `.`, and spaces all collapse to `-`. This is **not reversible** and genuinely collides:

- A dash in the folder name could have been any of several source characters; e.g. a project named `My_Tool` and a hypothetical `My-Tool` encode to the identical folder.
- Drive-letter case is preserved, not normalised, so two launches of the same project from different entrypoints can land in two different folders.
- A single folder can hold records from **several** `cwd`s — the root plus any subdirectory entered during the session.

Therefore CCD treats the `projects/<encoded>` folder as an **opaque bucket id used only to find files** and recovers the real project path from each record's `cwd`. In `parse_session_file` it counts every record's `cwd` and takes the most common as the conversation's `project_path`.

## The record envelope

Message records (`type` of `user` / `assistant`) carry a consistent envelope. The fields CCD reads:

| Field | Meaning | Used by CCD for |
|---|---|---|
| `uuid` | Globally unique id of this record. | Message id (`show`), tree nodes. |
| `parentUuid` | `uuid` of the preceding record; `null` on the first record. | Tree / fork structure. |
| `timestamp` | ISO-8601 instant the record was written. | The "when"; the time half of a fork fingerprint. |
| `type` | Record kind (see below). | Dispatch while parsing. |
| `message` | Payload `{ role, content, id, ... }`. | All searchable text; `id` for dedup. |
| `cwd` | The **real** working directory. | The trustworthy project path. |
| `requestId` | Groups an assistant turn with the tool result answering it. | Telling tool structure from a real fork. |
| `snapshot` | Carries `trackedFileBackups` on file-history records. | File versions / backups for `origin`. |

Other fields are present in real records but **not** consumed by CCD: `sessionId` (redundant with the filename), `gitBranch`, `version`, `entrypoint`, `userType`, `isSidechain`, `isMeta`, `isCompactSummary`, `leafUuid`, `lastPrompt`, `agentId`, `attributionAgent` / `attributionMcpServer` / `attributionMcpTool` / `attributionSkill`, `slug`, `operation`, `permissionMode`. A few of these matter for future features (see Subagents and Gotchas).

## Record types

Distinguished by the `type` field. Observed types and how CCD treats each:

| `type` | What it is | CCD |
|---|---|---|
| `user` | A user turn (or a `tool_result`, delivered as a user record). | Indexed. |
| `assistant` | An assistant turn (text / thinking / tool_use). | Indexed. |
| `ai-title` | An AI-generated conversation title, keyed by session. | Used as a label (latest wins). |
| `custom-title` | A user-set title override, keyed by session. | Used as a label (latest wins). |
| `file-history-snapshot` | Ties edited-file backups to a message. | Read for `origin` versions. |
| `attachment` | Injected context: hook output, pasted content, command stdout. | Skipped as a record type. |
| `last-prompt`, `queue-operation`, `mode`, `permission-mode`, `system` | Bookmark / control / meta records. | Skipped. |

New `type` values appear over versions. `parse_session_file` decides what to index with an **allow-list on the record `type`**: `user` / `assistant` records go through `iter_searchable_blocks`, `ai-title` / `custom-title` / `file-history-snapshot` are handled specially, and every other type — known or not — is skipped. Skipping is non-fatal, so an unrecognised type never breaks parsing. (An `attachment` *field* on a `user` / `assistant` record can still supply fork-fingerprint content as a fallback; a record whose `type` is literally `attachment` is skipped.)

## Message content shapes

`message.content` is **either a plain string or an array of typed blocks**. Block types seen: `text`, `thinking`, `tool_use`, `tool_result`, `document`. A `tool_result` arrives nested inside a record whose `role` is `user`. `iter_searchable_blocks` handles both the string and the array form; block types it does not recognise (e.g. `document`) are simply not indexed.

## Threading: a tree that is practically a line

`uuid` + `parentUuid` link records into a tree. The first record has `parentUuid: null`; each later record points back at its predecessor. Within a single file the branches that exist are tool-call structure — an assistant `tool_use` and the `user` `tool_result` answering it, sharing a `requestId`.

Consequences, and how CCD handles them:

- **For indexing and search, iterate all lines in file order.** That is sufficient and robust; records are written append-only in causal order. CCD never reconstructs the conversation by walking the parent chain to decide what to index.
- **A known bug lets `parentUuid` reference a `uuid` that exists nowhere in the file.** When CCD *does* use the parent links — for the tree view — `read_tree_records` reparents each message to its nearest message ancestor, and a parent that resolves to nothing becomes a local root, so a phantom parent never silently drops messages.

## One file = one session (resume and compaction)

- Every record in a file shares the filename's session id; `uuid`s are globally unique with no cross-file references.
- **Resume / continue appends to the same file.** Sessions with multi-day internal idle gaps keep an unbroken chain in one growing file.
- **`/compact`** writes an `isCompactSummary: true` user record mid-file and the conversation continues in the same file; the summary text restates earlier turns. CCD indexes it like any other message.
- Older pure-CLI `--resume` builds historically wrote a **new** session-id file. So treat each file as a conversation but never *rely* on one-file-per-conversation.

## Forks across files

A **fork** copies the conversation prefix into a *new* session file, assigning new uuids but preserving each copied record's original `timestamp` and content, with no stored back-reference to the origin. CCD reconstructs the relationship from the data itself:

- `fork_fingerprint` keys a record by `timestamp + "|" + hash(content)` (falling back to a uuid-based id when timestamp or content is missing, so unstamped records never merge by accident). Because nothing other than a fork writes the same millisecond-stamped, same-content record into a second file, a shared fingerprint across files **is** a copied record.
- `_assign_families` runs union-find over fingerprints shared by more than one session, grouping a conversation and all its forks into a **fork family** (a lone conversation is a family of one), and stores a `family_id` per session.
- `family_structure` rebuilds the family tree keyed by fingerprint: the shared prefix produces identical fingerprint edges in every file and collapses to one trunk, while the divergent tails become branches. A fork point can land mid-turn (the copy can stop inside a thinking block, with the answer regenerated in the fork); fingerprint matching finds the true split wherever it falls.

This is the load-bearing assumption behind the `tree`, `family`, and `families` commands: it relies on forks preserving original timestamps. A future Claude Code that re-stamped copied records would weaken it.

## Labeling a conversation ("which conversation")

Title records carry only `{ type, session, aiTitle | customTitle }` — no `uuid`, no `parentUuid` — and bind to a session purely by the session id.

- **Multiple `ai-title` records per session is normal** (the AI re-titles as the conversation grows); CCD keeps the **last** one in the file.
- Display-label precedence in `parse_session_file`: **latest `custom-title` → latest `ai-title` → first real user prompt → `(untitled)`**.
- Titles are used **only** as labels; they are not stored as searchable blocks, so a title is not independently searchable (its words match only where they also appear in a message).

## Timestamps ("when")

Every record has an ISO-8601 `timestamp`. For "when did this word appear", CCD uses the timestamp of the **matching message record**, not the file's overall span — a single session can run across several days. The conversation's `started_at` / `last_active_at` are the min / max record timestamps.

## What CCD indexes, what it drops

One row goes into the `blocks` table per searchable block. Block kinds and when they are searched:

| Block kind | Source | Searched by default? |
|---|---|---|
| `text` | `user` / `assistant` text blocks and the plain-string `content` form. | Yes. |
| `thinking` | Assistant reasoning blocks. | No — `--thinking` to include. |
| `tool_input` | Text pulled from `tool_use.input` (see keys below). | Yes — `--no-tool-input` to skip. |
| `tool_result` | Tool output text. | No — `--tool-result` to include (noisy). |

`tool_input` text is extracted (`extract_tool_input_text`) from these `input` keys, in this order: `command`, `description`, `content`, `query`, `pattern`, `prompt`, `old_string`, `new_string`, `url`, `file_path`, `path`, `todos`, `questions`, `plan`. String values are taken as-is; list / dict values are JSON-encoded. Pure flags (`limit`, `offset`, `timeout`, …) are never indexed.

Dropped or deduped to avoid false and duplicate hits:

- **Machine wrappers inside `user` records** — a user text block that *begins* with one of these injected tags is treated as machinery, not something the user typed, and is skipped: `<ide_opened_file>`, `<ide_selection>`, `<command-name>`, `<command-message>`, `<command-args>`, `<system-reminder>`, `<local-command-stdout>`, `<local-command-stderr>`, `<user-prompt-submit-hook>`, `<session-start-hook>` (see `WRAPPER_PATTERN`).
- **Streamed assistant duplicates** — the same logical message is written more than once during streaming; CCD dedups on `message.id` (falling back to `uuid`) and keeps the last copy.
- **Titles** — used for labeling, never indexed as content (see above).
- **Records of types CCD does not consume** — `last-prompt`, `queue-operation`, and the like are skipped, so a `lastPrompt` echo of a real user message is not indexed twice.

## File history and backups

Edited-file backups live under `~/.claude/file-history/<session_id>/`. A `file-history-snapshot` record's `snapshot.trackedFileBackups` maps a tracked path to a `{ version, backupFileName, backupTime }`. `find_file_origin` joins file-touching tool calls (`Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`) to these backups:

- Operation is classified from the tool and version (`classify_file_operation`): `Read` → `read`; `Edit` / `MultiEdit` / `NotebookEdit` → `edited`; a `Write` with version `None` or `1` → `created`, otherwise `edited`.
- The nearest backup by time supplies the version number; `has_backup` is true only when the named backup file actually exists on disk under `file-history/<session_id>/`.

## Other storage under `~/.claude`

CCD reads only `projects/` (the corpus) and `file-history/` (backups). The rest is mapped here for future features:

| Location | Holds | Useful for chat search? |
|---|---|---|
| `projects/<enc>/<sid>.jsonl` | Full transcript. | **Yes — the corpus.** |
| `file-history/<sid>/<hash>@vN` | Raw prior versions of edited files. | Secondary — old file states, tied to a message. |
| `history.jsonl` | Up-arrow recall buffer (truncated, mostly slash-commands; epoch-ms timestamps). | No. |
| `sessions/<pid>.json` | Live-process pointer (PID → session + cwd). | No content; a clean path anchor only. |
| `session-env/<sid>/` | Per-session env scratch. | No (but enumerates session ids). |
| `plans/*.md` | Plan-mode documents (prose). | Partial; weak attribution. |
| `shell-snapshots/*.sh` | Captured shell environment. | No. |
| `backups/.claude.json.backup.*` | Global config snapshots; `projects` map keyed by real path. | No content; an authoritative real-path list. |
| `config.json` | Global config — **may contain an API key**. | No — never index or echo this file. |
| `debug/`, `cache/`, `stats-cache.json` | Logs / aggregates / housekeeping. | No. |

## Subagents / sidechains

`isSidechain` marks subagent traffic. When subagents run, their turns are written into the **same** session file, interleaved, flagged `isSidechain: true` and tagged with an `agentId`. CCD does not currently distinguish sidechain records — it indexes them like any other message — so a search hit is attributed to its parent session without a subagent flag. An `isSidechain` / `agentId` filter is a natural future addition.

## Known gotchas and format drift

- The schema is **undocumented and version-specific**; new `type`s appear over time. Default to skipping unknown records, not crashing.
- **Phantom `parentUuid`** values that reference nothing in the file — iterate all lines for indexing; treat unresolved parents as roots when building trees.
- **Streamed duplicate** assistant records — dedup on `message.id` / `uuid`.
- **`messageId` / `uuid` collisions** on resume — do not assume id uniqueness across different record types.
- **`/compact` corruption** can leave a `leafUuid` that no longer resolves — treat summary text as searchable but do not trust its pointer.
- **Retention** — Claude Code's `cleanupPeriodDays` deletes old conversations; if the index is meant as an archive, rebuild before the source is pruned.
- **Windows path quirks** — UNC paths, spaces, and drive-letter case all need care.
- **Unconfirmed format edges** — whether a given CLI build forks a new session-id file on `--resume`, and the exact interleaving / attribution fields of live subagent traffic, are inferred from the schema rather than observed; CCD avoids depending on either.

## References

- Official `.claude` directory overview: <https://code.claude.com/docs/en/claude-directory>
- Piebald, "Messages as Commits: Claude Code's Git-Like DAG": <https://piebald.ai/blog/messages-as-commits-claude-codes-git-like-dag-of-conversations>
- "Inside Claude Code: The Session File Format": <https://databunny.medium.com/inside-claude-code-the-session-file-format-and-how-to-inspect-it-b9998e66d56b>
- Path-encoding compatibility issue: <https://github.com/anthropics/claude-code/issues/19972>
- Phantom `parentUuid` regression: <https://github.com/anthropics/claude-code/issues/22526>
- `messageId` / `uuid` collision: <https://github.com/anthropics/claude-code/issues/36583>

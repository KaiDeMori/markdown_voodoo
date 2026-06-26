"""CCD engine — corpus parsing, indexing, and search over Claude Code conversations.

The index is a plain SQLite database with one row per searchable block; matching uses
substring / glob scans (the agreed wildcard model) rather than a tokenised full-text
index. A separate table records file create/edit/read events for `find_file_origin`.
Indexing is always a full rebuild — searches read the stored index and refuse to run if
its `CCD_version` does not match this code. The public surface mirrors `CCD_api.py`.
"""

from __future__ import annotations

import collections
import hashlib
import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from CCD_api import (
    Block,
    Branch_point,
    Chat_entry_content,
    Chat_entry_locator,
    Chat_entry_match,
    Context_unit,
    Context_window,
    Conversation_match,
    Conversation_meta,
    Conversation_search_result,
    Conversation_tree,
    Diagram,
    Diagram_format,
    Family_summary,
    File_origin,
    Graph,
    Graph_edge,
    Graph_node,
    Index_stats,
    Match_mode,
    Search_all_result,
    Search_options,
    Search_role,
    Snippet,
    Tree_detail,
    Tree_node,
)

CCD_INDEX_VERSION = 3

WRAPPER_PATTERN = re.compile(
    r"^\s*</?(?:ide_opened_file|ide_selection|command-name|command-message|command-args"
    r"|system-reminder|local-command-stdout|local-command-stderr|user-prompt-submit-hook"
    r"|session-start-hook)\b"
)

TOOL_INPUT_TEXT_KEYS = (
    "command",
    "description",
    "content",
    "query",
    "pattern",
    "prompt",
    "old_string",
    "new_string",
    "url",
    "file_path",
    "path",
    "todos",
    "questions",
    "plan",
)

FILE_TOOLS = ("Read", "Write", "Edit", "MultiEdit", "NotebookEdit")
FILE_PATH_KEYS = ("file_path", "notebook_path", "path")
EDIT_TOOLS = ("Edit", "MultiEdit", "NotebookEdit")

MESSAGE_TYPES = ("user", "assistant")

TITLE_FALLBACK_LENGTH = 90


def default_corpus_root() -> Path:
    return Path.home() / ".claude" / "projects"


def default_index_path() -> Path:
    return Path.home() / ".claude" / "CCD_index.db"


def iter_session_files(corpus_root: Path):
    yield from sorted(corpus_root.glob("**/*.jsonl"))


def path_basename(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def is_machine_wrapper(text: str) -> bool:
    """Whether a user text block is injected machinery rather than something typed."""
    return bool(WRAPPER_PATTERN.match(text))


def extract_tool_input_text(tool_input) -> str:
    if not isinstance(tool_input, dict):
        return ""
    parts = []
    for key in TOOL_INPUT_TEXT_KEYS:
        if key not in tool_input:
            continue
        value = tool_input[key]
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, (list, dict)):
            parts.append(json.dumps(value, ensure_ascii=False))
    return "\n".join(parts)


def extract_tool_result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def extract_file_path(tool_input) -> str:
    if not isinstance(tool_input, dict):
        return ""
    for key in FILE_PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def classify_file_operation(tool: str, backup_version: Optional[int]) -> str:
    """Created vs edited vs read, using the file-history version when available."""
    if tool == "Read":
        return "read"
    if tool in EDIT_TOOLS:
        return "edited"
    if backup_version is None or backup_version == 1:
        return "created"
    return "edited"


def iter_file_operations(record: dict):
    """Yield (tool, file_path) for file-touching tool calls in a record."""
    message = record.get("message")
    if not isinstance(message, dict):
        return
    content = message.get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        tool = block.get("name")
        if tool not in FILE_TOOLS:
            continue
        file_path = extract_file_path(block.get("input"))
        if file_path:
            yield tool, file_path


def iter_searchable_blocks(record: dict):
    """Yield (block_index, block_kind, content) for the indexable parts of a record."""
    message = record.get("message")
    if not isinstance(message, dict):
        return
    role = message.get("role")
    content = message.get("content")
    if isinstance(content, str):
        if not (role == "user" and is_machine_wrapper(content)):
            yield 0, "text", content
        return
    if not isinstance(content, list):
        return
    for block_index, block in enumerate(content):
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            text = block.get("text", "")
            if role == "user" and is_machine_wrapper(text):
                continue
            yield block_index, "text", text
        elif block_type == "thinking":
            yield block_index, "thinking", block.get("thinking", "")
        elif block_type == "tool_use":
            text = extract_tool_input_text(block.get("input"))
            if text:
                yield block_index, "tool_input", text
        elif block_type == "tool_result":
            text = extract_tool_result_text(block.get("content"))
            if text:
                yield block_index, "tool_result", text


def _parse_iso(timestamp: Optional[str]):
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def _collect_backups(record: dict, backups_by_basename: dict) -> None:
    """Record file-history versions per basename: {basename: {version: (time, backup_name)}}.

    `trackedFileBackups` is a cumulative per-version map, so versions are keyed directly
    and a backup file name is preferred over a null when the same version recurs.
    """
    tracked = (record.get("snapshot") or {}).get("trackedFileBackups")
    if not isinstance(tracked, dict):
        return
    for tracked_path, info in tracked.items():
        if not isinstance(info, dict):
            continue
        version = info.get("version")
        if version is None:
            continue
        per_version = backups_by_basename.setdefault(path_basename(tracked_path).lower(), {})
        backup_name = info.get("backupFileName")
        existing = per_version.get(version)
        if existing is None or (existing[1] is None and backup_name):
            per_version[version] = (info.get("backupTime"), backup_name)


def _nearest_backup(per_version: dict, event_time):
    """The (version, backup_name) whose backup time is nearest the operation time."""
    best = None
    for version, (backup_time, backup_name) in per_version.items():
        moment = _parse_iso(backup_time)
        if moment is None or event_time is None:
            continue
        difference = abs((moment - event_time).total_seconds())
        if best is None or difference < best[0]:
            best = (difference, version, backup_name)
    if best is None:
        version = max(per_version)
        return version, per_version[version][1]
    return best[1], best[2]


def parse_session_file(path: Path, file_history_root: Path):
    """Read one session file into a conversation row, block rows, and file-event rows.

    Streaming assistant duplicates (same message id) are collapsed to the last copy.
    Returns (conversation_row, block_rows, file_event_rows) or (None, [], []).
    """
    session_id = path.stem
    title_ai = None
    title_custom = None
    first_user_prompt = None
    started_at = None
    last_active_at = None
    working_directories = collections.Counter()
    entries = {}
    backups_by_basename = {}

    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            record_type = record.get("type")
            timestamp = record.get("timestamp")
            if timestamp:
                if started_at is None or timestamp < started_at:
                    started_at = timestamp
                if last_active_at is None or timestamp > last_active_at:
                    last_active_at = timestamp
            record_cwd = record.get("cwd")
            if record_cwd:
                working_directories[record_cwd] += 1
            if record_type == "ai-title":
                title_ai = record.get("aiTitle") or title_ai
            elif record_type == "custom-title":
                title_custom = record.get("customTitle") or title_custom
            elif record_type == "file-history-snapshot":
                _collect_backups(record, backups_by_basename)
            elif record_type in MESSAGE_TYPES:
                blocks = list(iter_searchable_blocks(record))
                if first_user_prompt is None and record_type == "user":
                    for _, block_kind, content in blocks:
                        if block_kind == "text" and content.strip():
                            first_user_prompt = content.strip()[:TITLE_FALLBACK_LENGTH]
                            break
                message = record.get("message") or {}
                dedup_key = message.get("id") or record.get("uuid")
                entries[dedup_key] = {
                    "uuid": record.get("uuid"),
                    "role": message.get("role"),
                    "chat_entry_type": record_type,
                    "timestamp": timestamp,
                    "cwd": record_cwd,
                    "blocks": blocks,
                    "file_ops": list(iter_file_operations(record)),
                }

    if started_at is None and not entries:
        return None, [], []

    project_path = working_directories.most_common(1)[0][0] if working_directories else ""
    title = title_custom or title_ai or first_user_prompt or "(untitled)"

    block_rows = []
    file_event_rows = []
    for entry in entries.values():
        entry_cwd = entry["cwd"] or project_path
        for block_index, block_kind, content in entry["blocks"]:
            block_rows.append(
                (
                    session_id,
                    entry["uuid"],
                    entry["role"],
                    entry["chat_entry_type"],
                    block_index,
                    block_kind,
                    entry["timestamp"],
                    entry_cwd,
                    content,
                )
            )
        event_time = _parse_iso(entry["timestamp"])
        for tool, file_path in entry["file_ops"]:
            basename = path_basename(file_path).lower()
            backup_version = None
            backup_name = None
            if tool != "Read":
                per_version = backups_by_basename.get(basename)
                if per_version:
                    backup_version, backup_name = _nearest_backup(per_version, event_time)
            has_backup = bool(backup_name) and (file_history_root / session_id / backup_name).exists()
            file_event_rows.append(
                (
                    session_id,
                    entry["uuid"],
                    entry["timestamp"],
                    file_path,
                    basename,
                    tool,
                    classify_file_operation(tool, backup_version),
                    backup_version,
                    1 if has_backup else 0,
                )
            )

    conversation_row = (
        session_id,
        title,
        project_path,
        started_at,
        last_active_at,
        len(entries),
        str(path),
    )
    return conversation_row, block_rows, file_event_rows


def _allowed_block_kinds(options: Search_options) -> list[str]:
    kinds = ["text"]
    if options.include_thinking:
        kinds.append("thinking")
    if options.include_tool_input:
        kinds.append("tool_input")
    if options.include_tool_result:
        kinds.append("tool_result")
    return kinds


def count_occurrences(content: str, query: str, options: Search_options) -> int:
    if options.match_mode in (Match_mode.substring, Match_mode.phrase):
        if options.case_sensitive:
            return content.count(query)
        return content.lower().count(query.lower())
    return 1


def _iter_match_positions(content: str, query: str, options: Search_options, cap: int = 3):
    haystack = content if options.case_sensitive else content.lower()
    needle = query if options.case_sensitive else query.lower()
    start = 0
    found = 0
    while found < cap:
        position = haystack.find(needle, start)
        if position < 0:
            return
        yield position, len(query)
        start = position + max(len(needle), 1)
        found += 1


def _build_snippet(content: str, position: int, length: int, context: Context_window, block_index: int, block_kind: str) -> Snippet:
    if context.unit is Context_unit.lines:
        line_start = content.rfind("\n", 0, position) + 1
        line_end = content.find("\n", position)
        if line_end < 0:
            line_end = len(content)
        preceding = content[:line_start].split("\n")[:-1][-context.before:] if line_start else []
        following = content[line_end + 1:].split("\n")[:context.after] if line_end < len(content) else []
        before = ("\n".join(preceding) + "\n" if preceding else "") + content[line_start:position]
        after = content[position + length:line_end] + (("\n" + "\n".join(following)) if following else "")
    else:
        before = content[max(0, position - context.before):position]
        after = content[position + length:position + length + context.after]
    consumed = len(before) + length + len(after)
    return Snippet(
        block_index=block_index,
        block_type=block_kind,
        before=before,
        match=content[position:position + length],
        after=after,
        char_offset=position,
        truncated=consumed < len(content),
    )


TREE_PREVIEW_LENGTH = 40


def fork_fingerprint(timestamp: Optional[str], content_text: str, uuid: str) -> str:
    """A copy-stable id for a record: timestamp + content hash.

    A fork copies records verbatim, so two records sharing this fingerprint across
    files are the same copied record. Records with no timestamp or empty content fall
    back to a uuid-based id so they never merge across files by accident.
    """
    text = (content_text if isinstance(content_text, str) else str(content_text or "")).strip()
    if timestamp and text:
        digest = hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:16]
        return timestamp + "|" + digest
    return "u|" + uuid


def _record_content_text(record: dict) -> str:
    message = record.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type")
                if block_type == "text":
                    parts.append(block.get("text") or "")
                elif block_type == "thinking":
                    parts.append(block.get("thinking") or "")
                elif block_type == "tool_use":
                    parts.append("tool_use:%s:%s" % (block.get("name"), json.dumps(block.get("input"), sort_keys=True, ensure_ascii=False)))
                elif block_type == "tool_result":
                    parts.append("tool_result:" + extract_tool_result_text(block.get("content")))
                else:
                    parts.append(block_type or "")
            return "\n".join(parts)
    attachment = record.get("attachment")
    if isinstance(attachment, dict):
        value = attachment.get("content") or attachment.get("stdout") or ""
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return ""


def read_tree_records(path: Path) -> list[dict]:
    """Read a session's conversation messages with metadata for tree rendering.

    Only `user` / `assistant` records become tree nodes; injected attachment / system /
    queue records are skipped and each message is reparented to its nearest message
    ancestor, so the tree is the conversation flow rather than the plumbing — and forks
    are not confused by attachments being linked differently across copied files.
    """
    raw = []
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("uuid"):
                raw.append(record)
    by_uuid = {record["uuid"]: record for record in raw}

    def nearest_message_parent(record):
        parent = record.get("parentUuid")
        while parent:
            parent_record = by_uuid.get(parent)
            if parent_record is None:
                return None
            if parent_record.get("type") in MESSAGE_TYPES:
                return parent
            parent = parent_record.get("parentUuid")
        return None

    records = []
    for record in raw:
        if record.get("type") not in MESSAGE_TYPES:
            continue
        message = record.get("message") or {}
        content = message.get("content")
        has_tool_result = False
        preview = ""
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result":
                        has_tool_result = True
                    if not preview and block.get("type") == "text":
                        preview = (block.get("text") or "").strip()[:TREE_PREVIEW_LENGTH]
        elif isinstance(content, str):
            preview = content.strip()[:TREE_PREVIEW_LENGTH]
        records.append(
            {
                "uuid": record["uuid"],
                "parent_uuid": nearest_message_parent(record),
                "type": record.get("type"),
                "role": message.get("role"),
                "timestamp": record.get("timestamp"),
                "request_id": record.get("requestId"),
                "has_tool_result": has_tool_result,
                "preview": preview,
                "fingerprint": fork_fingerprint(record.get("timestamp"), _record_content_text(record), record["uuid"]),
            }
        )
    return records


def _child_map(records: list[dict]):
    by_uuid = {record["uuid"]: record for record in records}
    children = {record["uuid"]: [] for record in records}
    for record in records:
        parent = record["parent_uuid"]
        if parent in children:
            children[parent].append(record["uuid"])
    return by_uuid, children


def classify_branch(by_uuid: dict, parent_uuid: str, child_uuids: list[str]) -> str:
    """Tool-call structure vs a genuine rewind, by shared requestId / tool_result children."""
    parent_request = by_uuid[parent_uuid].get("request_id")
    for child_uuid in child_uuids:
        child = by_uuid.get(child_uuid, {})
        is_continuation = bool(child.get("request_id")) and child.get("request_id") == parent_request
        if not (is_continuation or child.get("has_tool_result")):
            return "real_fork"
    return "tool_structure"


def build_conversation_tree(session_id: str, records: list[dict]) -> Conversation_tree:
    by_uuid, children = _child_map(records)
    nodes = [
        Tree_node(
            uuid=record["uuid"],
            chat_entry_type=record["type"],
            timestamp=record["timestamp"],
            parent_uuid=record["parent_uuid"],
            child_uuids=children[record["uuid"]],
        )
        for record in records
    ]
    branch_points = [
        Branch_point(uuid=uuid, child_uuids=children[uuid], kind=classify_branch(by_uuid, uuid, children[uuid]))
        for uuid in children
        if len(children[uuid]) > 1
    ]
    leaves = [uuid for uuid in children if not children[uuid]]
    return Conversation_tree(session_id=session_id, nodes=nodes, branch_points=branch_points, leaves=leaves)


def _node_label(record: dict) -> str:
    who = record.get("role") or record.get("type") or "?"
    when = (record.get("timestamp") or "")[11:16]
    preview = record.get("preview") or ""
    label = who + (" " + when if when else "")
    return label + (": " + preview if preview else "")


SHORT_FORK_MIN_BRANCH = 3


def _subtree_sizes(children: dict, nodes: list) -> dict:
    """Descendant count (inclusive) under each node, for telling a real branch from a stub.

    Iterative so a long conversation cannot overflow the recursion limit; a node reached
    by more than one parent is sized once, which is good enough for the branch test.
    """
    size: dict = {}
    for start in nodes:
        if start in size:
            continue
        order = []
        stack = [start]
        local = set()
        while stack:
            node_id = stack.pop()
            if node_id in local or node_id in size:
                continue
            local.add(node_id)
            order.append(node_id)
            for kid in children.get(node_id, []):
                if kid not in size and kid not in local:
                    stack.append(kid)
        for node_id in reversed(order):
            total = 1
            for kid in children.get(node_id, []):
                total += size.get(kid, 1)
            size[node_id] = total
    return size


def _reduce_to_forks(meta: dict, children: dict, roots: list, branch_kind: dict, max_nodes: int) -> Graph:
    """Reduce a node tree to its real forks plus the entries immediately around them.

    A fork is a node where two or more branches each carry real content; a branch of only
    a entry or two is treated as noise (tool structure, a dead-end rewind) rather than a
    fork, so a long backbone does not turn every turn into a branch. Each fork keeps the
    entry just before it and the first entry of each branch after it; everything else
    between forks folds into one aggregated count node, and dead-end runs below a fork fold
    into a single count node rather than several parallel ones.
    """
    sizes = _subtree_sizes(children, list(meta.keys()))
    forks = set()
    for node_id in meta:
        substantial = sum(1 for kid in children.get(node_id, []) if sizes.get(kid, 1) >= SHORT_FORK_MIN_BRANCH)
        if substantial >= 2:
            forks.add(node_id)

    parent_of = {kid: node_id for node_id, kids in children.items() for kid in kids}
    shown = set(roots) | forks
    for fork in forks:
        shown.update(children.get(fork, []))
        if fork in parent_of:
            shown.add(parent_of[fork])

    graph = Graph(directed=True, nodes=[], edges=[], notes=[])
    identifiers = {}
    counter = [0]
    collapsed_total = [0]

    def node_kind(node_id):
        if node_id in roots:
            return "root"
        if node_id in forks:
            return "branch_point"
        if not children.get(node_id):
            return "leaf"
        return "turn"

    def ensure(node_id):
        if node_id not in identifiers:
            identifiers[node_id] = "n%d" % counter[0]
            counter[0] += 1
            graph.nodes.append(
                Graph_node(id=identifiers[node_id], label=meta[node_id]["label"], kind=node_kind(node_id), ref_uuid=meta[node_id].get("ref"))
            )
        return identifiers[node_id]

    def add_collapsed(source_id, count):
        collapsed_id = "n%d" % counter[0]
        counter[0] += 1
        graph.nodes.append(Graph_node(id=collapsed_id, label="... %d entries" % count, kind="collapsed", collapsed_count=count))
        graph.edges.append(Graph_edge(source_id=source_id, target_id=collapsed_id))
        collapsed_total[0] += count
        return collapsed_id

    def process(shown_id):
        source_id = ensure(shown_id)
        reached = {}
        terminal_entries = 0
        walked = set()
        stack = [(child, 0) for child in children.get(shown_id, [])]
        while stack:
            node_id, skipped = stack.pop()
            if node_id in walked:
                continue
            walked.add(node_id)
            if node_id in shown:
                previous = reached.get(node_id)
                reached[node_id] = skipped if previous is None else min(previous, skipped)
                continue
            kids = children.get(node_id, [])
            if not kids:
                terminal_entries += skipped + 1
                continue
            for kid in kids:
                stack.append((kid, skipped + 1))

        for target_id, between in reached.items():
            target_node = ensure(target_id)
            if between > 0:
                collapsed_id = add_collapsed(source_id, between)
                graph.edges.append(Graph_edge(source_id=collapsed_id, target_id=target_node))
            else:
                graph.edges.append(Graph_edge(source_id=source_id, target_id=target_node))
        if terminal_entries > 0:
            add_collapsed(source_id, terminal_entries)
        return list(reached.keys())

    for root in roots:
        ensure(root)
    pending = list(roots)
    seen = set()
    while pending:
        shown_id = pending.pop(0)
        if shown_id in seen:
            continue
        seen.add(shown_id)
        for next_shown in process(shown_id):
            if next_shown not in seen:
                pending.append(next_shown)

    if not forks:
        graph.notes.append("no forks: this is a single thread, collapsed to its entry count")
    if collapsed_total[0]:
        graph.notes.append("%d entries folded into collapsed nodes" % collapsed_total[0])
    if len(graph.nodes) > max_nodes:
        graph.notes.append("graph has %d nodes (> max_nodes=%d); raise --max-nodes or use --single" % (len(graph.nodes), max_nodes))
    return graph


def _reduce_to_graph(meta: dict, children: dict, roots: list, branch_kind: dict, detail: Tree_detail, max_nodes: int) -> Graph:
    """Collapse a node tree to a render-neutral graph per the detail level.

    `meta[node_id]` carries `type`, `has_tool_result`, `label`, and `ref`. Works for a
    single file (nodes keyed by uuid) or a whole fork family (nodes keyed by fingerprint).
    """
    if detail is Tree_detail.short:
        return _reduce_to_forks(meta, children, roots, branch_kind, max_nodes)
    if detail is Tree_detail.full:
        is_kept = lambda node_id: True
    elif detail is Tree_detail.turns:
        is_kept = lambda node_id: meta[node_id]["type"] in MESSAGE_TYPES and not meta[node_id]["has_tool_result"]
    else:
        is_kept = lambda node_id: branch_kind.get(node_id) == "real_fork"

    kept = set(node_id for node_id in meta if is_kept(node_id))
    kept.update(roots)
    for node_id in meta:
        if not children.get(node_id) and (detail is Tree_detail.full or not meta[node_id]["has_tool_result"]):
            kept.add(node_id)

    graph = Graph(directed=True, nodes=[], edges=[], notes=[])
    identifiers = {}
    counter = [0]

    def node_kind(node_id):
        if node_id in roots:
            return "root"
        if branch_kind.get(node_id) == "real_fork":
            return "branch_point"
        if not children.get(node_id):
            return "leaf"
        return "turn"

    def ensure(node_id):
        if node_id not in identifiers:
            identifiers[node_id] = "n%d" % counter[0]
            counter[0] += 1
            graph.nodes.append(
                Graph_node(id=identifiers[node_id], label=meta[node_id]["label"], kind=node_kind(node_id), ref_uuid=meta[node_id].get("ref"))
            )
        return identifiers[node_id]

    def reached_kept(start):
        results = []
        seen = set()
        stack = [(start, 0)]
        while stack:
            node_id, skipped = stack.pop()
            if node_id in seen:
                continue
            seen.add(node_id)
            if node_id in kept:
                results.append((node_id, skipped))
                continue
            for child in children.get(node_id, []):
                stack.append((child, skipped + 1))
        return results

    collapsed_total = 0
    for root in roots:
        ensure(root)
    pending = list(roots)
    visited = set()
    while pending:
        node_id = pending.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)
        source = ensure(node_id)
        for child in children.get(node_id, []):
            for destination, skipped in reached_kept(child):
                target = ensure(destination)
                if skipped:
                    collapsed_id = "n%d" % counter[0]
                    counter[0] += 1
                    graph.nodes.append(
                        Graph_node(id=collapsed_id, label="... %d entries" % skipped, kind="collapsed", collapsed_count=skipped)
                    )
                    collapsed_total += skipped
                    graph.edges.append(Graph_edge(source_id=source, target_id=collapsed_id))
                    graph.edges.append(Graph_edge(source_id=collapsed_id, target_id=target))
                else:
                    graph.edges.append(Graph_edge(source_id=source, target_id=target))
                if destination not in visited:
                    pending.append(destination)

    if collapsed_total:
        graph.notes.append("%d entries folded into collapsed nodes" % collapsed_total)
    if len(graph.nodes) > max_nodes:
        hint = "raise --max-nodes or use --single" if detail is Tree_detail.forks_only else "try --detail forks_only"
        graph.notes.append("graph has %d nodes (> max_nodes=%d); %s" % (len(graph.nodes), max_nodes, hint))
    return graph


def build_tree_graph(records: list[dict], detail: Tree_detail, max_nodes: int) -> Graph:
    """Single-file tree to graph (a fork family of one)."""
    by_uuid, children = _child_map(records)
    roots = [r["uuid"] for r in records if not r["parent_uuid"] or r["parent_uuid"] not in by_uuid]
    branch_kind = {uuid: classify_branch(by_uuid, uuid, children[uuid]) for uuid in children if len(children[uuid]) > 1}
    meta = {
        uuid: {
            "type": by_uuid[uuid].get("type"),
            "has_tool_result": by_uuid[uuid].get("has_tool_result"),
            "label": _node_label(by_uuid[uuid]),
            "ref": uuid,
        }
        for uuid in by_uuid
    }
    return _reduce_to_graph(meta, children, roots, branch_kind, detail, max_nodes)


def _classify_family_branch(meta: dict, children: dict, fingerprint: str) -> str:
    """A branch is a fork when it splits the family across sessions; else tool structure."""
    parent_sessions = meta[fingerprint]["sessions"]
    if len(parent_sessions) <= 1:
        return "tool_structure"
    if any(meta[child]["sessions"] != parent_sessions for child in children[fingerprint]):
        return "real_fork"
    return "tool_structure"


def family_structure(rows: list[dict], session_titles: dict):
    """Build a fingerprint-keyed tree from the tree_nodes of one or more sessions.

    Records a fork copied share a fingerprint and collapse to one node; the within-file
    parent links, translated to fingerprints and unioned, reveal the cross-file forks.
    Returns (meta, children, roots, branch_kind).
    """
    fingerprint_of = {}
    for row in rows:
        fingerprint_of[(row["session_id"], row["uuid"])] = row["fingerprint"]

    meta = {}
    children = {}
    edges = set()
    has_parent = set()
    for row in rows:
        fingerprint = row["fingerprint"]
        node = meta.get(fingerprint)
        if node is None:
            node = {
                "type": row["type"],
                "has_tool_result": bool(row["has_tool_result"]),
                "label": _node_label(row),
                "ref": fingerprint,
                "sessions": set(),
                "timestamp": row["timestamp"],
                "parent": None,
            }
            meta[fingerprint] = node
            children[fingerprint] = set()
        node["sessions"].add(row["session_id"])
        if row["has_tool_result"]:
            node["has_tool_result"] = True
        parent_fingerprint = fingerprint_of.get((row["session_id"], row["parent_uuid"]))
        if parent_fingerprint and parent_fingerprint != fingerprint:
            edges.add((parent_fingerprint, fingerprint))
            node["parent"] = parent_fingerprint
    for parent_fingerprint, child_fingerprint in edges:
        children.setdefault(parent_fingerprint, set()).add(child_fingerprint)
        has_parent.add(child_fingerprint)
    children = {key: list(value) for key, value in children.items()}
    roots = [fingerprint for fingerprint in meta if fingerprint not in has_parent]

    for fingerprint, node in meta.items():
        if not children.get(fingerprint) and len(node["sessions"]) == 1:
            session_id = next(iter(node["sessions"]))
            node["label"] = node["label"] + "  [%s]" % session_titles.get(session_id, session_id[:8])

    branch_kind = {
        fingerprint: _classify_family_branch(meta, children, fingerprint)
        for fingerprint, kids in children.items()
        if len(kids) > 1
    }
    return meta, children, roots, branch_kind


def build_family_tree(session_id: str, rows: list[dict], session_titles: dict) -> Conversation_tree:
    meta, children, roots, branch_kind = family_structure(rows, session_titles)
    nodes = [
        Tree_node(
            uuid=fingerprint,
            chat_entry_type=node["type"],
            timestamp=node["timestamp"],
            parent_uuid=node["parent"],
            child_uuids=children.get(fingerprint, []),
        )
        for fingerprint, node in meta.items()
    ]
    branch_points = [
        Branch_point(uuid=fingerprint, child_uuids=children[fingerprint], kind=kind)
        for fingerprint, kind in branch_kind.items()
    ]
    leaves = [fingerprint for fingerprint in meta if not children.get(fingerprint)]
    sessions = sorted(set().union(*(node["sessions"] for node in meta.values()))) if meta else []
    return Conversation_tree(session_id=session_id, sessions=sessions, nodes=nodes, branch_points=branch_points, leaves=leaves)


def _mermaid_label(label: str) -> str:
    return label.replace("\\", "/").replace('"', "'").replace("\n", " ")[:70]


def graph_to_mermaid(graph: Graph) -> str:
    lines = ["flowchart TD"]
    for node in graph.nodes:
        label = _mermaid_label(node.label)
        if node.kind == "branch_point":
            lines.append('    %s{"%s"}' % (node.id, label))
        elif node.kind == "collapsed":
            lines.append('    %s(["%s"])' % (node.id, label))
        else:
            lines.append('    %s["%s"]' % (node.id, label))
    for edge in graph.edges:
        lines.append("    %s --> %s" % (edge.source_id, edge.target_id))
    forks = [node.id for node in graph.nodes if node.kind == "branch_point"]
    if forks:
        lines.append("    classDef fork fill:#fde,stroke:#b06,stroke-width:2px;")
        lines.append("    class %s fork;" % ",".join(forks))
    return "\n".join(lines)


def graph_to_dot(graph: Graph) -> str:
    lines = ["digraph conversation {", "  rankdir=TB;", '  node [shape=box, fontname="monospace"];']
    for node in graph.nodes:
        label = node.label.replace("\\", "/").replace('"', "'").replace("\n", " ")
        shape = "diamond" if node.kind == "branch_point" else ("ellipse" if node.kind == "collapsed" else "box")
        lines.append('  %s [label="%s", shape=%s];' % (node.id, label, shape))
    for edge in graph.edges:
        lines.append("  %s -> %s;" % (edge.source_id, edge.target_id))
    lines.append("}")
    return "\n".join(lines)


def graph_to_json(graph: Graph) -> str:
    return json.dumps(
        {
            "directed": graph.directed,
            "nodes": [
                {"id": n.id, "label": n.label, "kind": n.kind, "ref_uuid": n.ref_uuid, "collapsed_count": n.collapsed_count}
                for n in graph.nodes
            ],
            "edges": [{"source": e.source_id, "target": e.target_id, "label": e.label} for e in graph.edges],
            "notes": graph.notes,
        },
        ensure_ascii=False,
        indent=2,
    )


GRAPH_RENDERERS = {
    Diagram_format.mermaid: graph_to_mermaid,
    Diagram_format.dot: graph_to_dot,
    Diagram_format.graph_json: graph_to_json,
}


class Chat_digger:
    """Search over an indexed corpus of Claude Code conversations."""

    def __init__(self, index_path: Optional[str] = None, corpus_root: Optional[str] = None) -> None:
        self.index_path = Path(index_path) if index_path else default_index_path()
        self.corpus_root = Path(corpus_root) if corpus_root else default_corpus_root()

    def _file_history_root(self) -> Path:
        return self.corpus_root.parent / "file-history"

    def _connect(self) -> sqlite3.Connection:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.index_path))
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                project_path TEXT,
                started_at TEXT,
                last_active_at TEXT,
                entry_count INTEGER,
                source_path TEXT,
                family_id TEXT
            );
            CREATE TABLE IF NOT EXISTS blocks (
                session_id TEXT,
                uuid TEXT,
                role TEXT,
                chat_entry_type TEXT,
                block_index INTEGER,
                block_kind TEXT,
                timestamp TEXT,
                project_path TEXT,
                content TEXT
            );
            CREATE INDEX IF NOT EXISTS index_blocks_session ON blocks(session_id);
            CREATE TABLE IF NOT EXISTS file_events (
                session_id TEXT,
                chat_entry_uuid TEXT,
                timestamp TEXT,
                file_path TEXT,
                basename TEXT,
                tool TEXT,
                operation TEXT,
                version INTEGER,
                has_backup INTEGER
            );
            CREATE INDEX IF NOT EXISTS index_file_events_basename ON file_events(basename);
            CREATE TABLE IF NOT EXISTS tree_nodes (
                session_id TEXT,
                uuid TEXT,
                parent_uuid TEXT,
                timestamp TEXT,
                type TEXT,
                role TEXT,
                has_tool_result INTEGER,
                request_id TEXT,
                fingerprint TEXT,
                preview TEXT
            );
            CREATE INDEX IF NOT EXISTS index_tree_nodes_session ON tree_nodes(session_id);
            CREATE INDEX IF NOT EXISTS index_tree_nodes_fingerprint ON tree_nodes(fingerprint);
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
            """
        )

    def _stored_version(self, connection: sqlite3.Connection) -> Optional[int]:
        row = connection.execute("SELECT value FROM meta WHERE key = 'CCD_version'").fetchone()
        return int(row[0]) if row else None

    def _open_for_read(self) -> sqlite3.Connection:
        connection = self._connect()
        self._ensure_schema(connection)
        version = self._stored_version(connection)
        if version != CCD_INDEX_VERSION:
            connection.close()
            raise ValueError(
                "index not built, or built by a different CCD version (db=%s, code=%d). "
                "Run: python CCD.py index" % (version, CCD_INDEX_VERSION)
            )
        return connection

    def index_version(self) -> Optional[int]:
        connection = self._connect()
        self._ensure_schema(connection)
        version = self._stored_version(connection)
        connection.close()
        return version

    def build_index(self) -> Index_stats:
        """Rebuild the whole index from scratch. The only path that writes it."""
        file_history_root = self._file_history_root()
        connection = self._connect()
        connection.executescript(
            "DROP TABLE IF EXISTS files; DROP TABLE IF EXISTS blocks; DROP TABLE IF EXISTS conversations; "
            "DROP TABLE IF EXISTS file_events; DROP TABLE IF EXISTS tree_nodes; DROP TABLE IF EXISTS meta;"
        )
        self._ensure_schema(connection)
        for path in iter_session_files(self.corpus_root):
            conversation_row, block_rows, file_event_rows = parse_session_file(path, file_history_root)
            if not conversation_row:
                continue
            connection.execute(
                "INSERT OR REPLACE INTO conversations "
                "(session_id, title, project_path, started_at, last_active_at, entry_count, source_path) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                conversation_row,
            )
            connection.executemany("INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", block_rows)
            connection.executemany("INSERT INTO file_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", file_event_rows)
            session_id = path.stem
            tree_rows = [
                (
                    session_id,
                    node["uuid"],
                    node["parent_uuid"],
                    node["timestamp"],
                    node["type"],
                    node["role"],
                    1 if node["has_tool_result"] else 0,
                    node["request_id"],
                    node["fingerprint"],
                    node["preview"],
                )
                for node in read_tree_records(path)
            ]
            connection.executemany("INSERT INTO tree_nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tree_rows)
        self._assign_families(connection)
        connection.execute("INSERT OR REPLACE INTO meta VALUES ('built_at', ?)", (repr(time.time()),))
        connection.execute("INSERT OR REPLACE INTO meta VALUES ('CCD_version', ?)", (str(CCD_INDEX_VERSION),))
        connection.commit()
        result = self._index_stats(connection)
        connection.close()
        return result

    @staticmethod
    def _assign_families(connection: sqlite3.Connection) -> None:
        """Group sessions that share a fork fingerprint into families (union-find)."""
        rows = connection.execute(
            "SELECT fingerprint, session_id FROM tree_nodes WHERE fingerprint IN "
            "(SELECT fingerprint FROM tree_nodes GROUP BY fingerprint HAVING COUNT(DISTINCT session_id) > 1)"
        ).fetchall()
        parent = {}

        def find(node):
            parent.setdefault(node, node)
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(left, right):
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[left_root] = right_root

        sessions_by_fingerprint = {}
        for row in rows:
            sessions_by_fingerprint.setdefault(row["fingerprint"], set()).add(row["session_id"])
        for sessions in sessions_by_fingerprint.values():
            sessions = list(sessions)
            for other in sessions[1:]:
                union(sessions[0], other)

        members = {}
        for session in parent:
            members.setdefault(find(session), set()).add(session)
        for sessions in members.values():
            if len(sessions) < 2:
                continue
            family_id = min(sessions)
            for session in sessions:
                connection.execute("UPDATE conversations SET family_id = ? WHERE session_id = ?", (family_id, session))

    def get_fork_family(self, session_id: str) -> list[str]:
        """The sessions in this conversation's fork family, oldest first (just one if none)."""
        connection = self._open_for_read()
        row = connection.execute("SELECT family_id FROM conversations WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            connection.close()
            raise ValueError("unknown session_id: %s" % session_id)
        family_id = row["family_id"]
        if not family_id:
            connection.close()
            return [session_id]
        sessions = [
            r["session_id"]
            for r in connection.execute(
                "SELECT session_id FROM conversations WHERE family_id = ? ORDER BY started_at", (family_id,)
            ).fetchall()
        ]
        connection.close()
        return sessions

    @staticmethod
    def _load_tree_node_rows(connection: sqlite3.Connection, sessions: list[str]) -> list[dict]:
        """Tree-node rows for many sessions, chunked to stay under the SQL parameter cap."""
        rows: list[dict] = []
        chunk_size = 400
        for start in range(0, len(sessions), chunk_size):
            chunk = sessions[start:start + chunk_size]
            placeholder = ",".join("?" * len(chunk))
            rows.extend(
                dict(row)
                for row in connection.execute(
                    "SELECT session_id, uuid, parent_uuid, timestamp, type, role, has_tool_result, request_id, fingerprint, preview "
                    "FROM tree_nodes WHERE session_id IN (%s)" % placeholder,
                    chunk,
                ).fetchall()
            )
        return rows

    def list_families(
        self,
        workspace: Optional[str] = None,
        project: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Family_summary]:
        """Every fork family in a workspace as one summary each, most recent first."""
        clauses = []
        params: list = []
        if project:
            clauses.append("project_path = ?")
            params.append(project)
        if workspace:
            clauses.append("instr(lower(project_path), lower(?)) > 0")
            params.append(workspace.rstrip("/\\"))
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

        connection = self._open_for_read()
        conversation_rows = connection.execute(
            "SELECT session_id, title, project_path, started_at, last_active_at, family_id "
            "FROM conversations" + where,
            params,
        ).fetchall()
        families: dict = {}
        titles: dict = {}
        for row in conversation_rows:
            titles[row["session_id"]] = row["title"]
            family_key = row["family_id"] or row["session_id"]
            families.setdefault(family_key, []).append(dict(row))
        node_rows = self._load_tree_node_rows(connection, list(titles.keys()))
        connection.close()

        rows_by_session: dict = {}
        for node in node_rows:
            rows_by_session.setdefault(node["session_id"], []).append(node)

        summaries = []
        for family_key, members in families.items():
            members.sort(key=lambda member: member["started_at"] or "")
            root = members[0]
            family_rows = [node for member in members for node in rows_by_session.get(member["session_id"], [])]
            if family_rows:
                meta, children, _, _ = family_structure(family_rows, titles)
                leaf_count = sum(1 for fingerprint in meta if not children.get(fingerprint))
                node_count = len(meta)
            else:
                leaf_count = 0
                node_count = 0
            summaries.append(
                Family_summary(
                    family_id=family_key,
                    root_session_id=root["session_id"],
                    title=root["title"] or "(untitled)",
                    project_path=root["project_path"] or "",
                    started_at=root["started_at"] or "",
                    last_active_at=max((member["last_active_at"] or "") for member in members),
                    session_count=len(members),
                    leaf_count=leaf_count,
                    node_count=node_count,
                )
            )
        summaries.sort(key=lambda summary: summary.last_active_at, reverse=True)
        if limit is not None:
            summaries = summaries[:limit]
        return summaries

    def _index_stats(self, connection: sqlite3.Connection) -> Index_stats:
        conversation_count = connection.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        block_count = connection.execute("SELECT COUNT(*) FROM blocks").fetchone()[0]
        built_row = connection.execute("SELECT value FROM meta WHERE key = 'built_at'").fetchone()
        built_at = float(built_row[0]) if built_row else 0.0
        is_stale = self._is_stale(built_at)
        return Index_stats(
            conversation_count=conversation_count,
            chat_entry_count=block_count,
            built_at=built_at,
            is_stale=is_stale,
        )

    def _is_stale(self, built_at: float) -> bool:
        for path in iter_session_files(self.corpus_root):
            if path.stat().st_mtime > built_at:
                return True
        return False

    def index_status(self) -> Index_stats:
        connection = self._connect()
        self._ensure_schema(connection)
        result = self._index_stats(connection)
        connection.close()
        return result

    def list_conversations(self, options: Optional[Search_options] = None) -> list[Conversation_meta]:
        connection = self._open_for_read()
        rows = connection.execute(
            "SELECT session_id, title, project_path, started_at, last_active_at, entry_count "
            "FROM conversations ORDER BY last_active_at DESC"
        ).fetchall()
        connection.close()
        return [
            Conversation_meta(
                session_id=row["session_id"],
                title=row["title"],
                project_path=row["project_path"],
                started_at=row["started_at"],
                last_active_at=row["last_active_at"],
                chat_entry_count=row["entry_count"],
            )
            for row in rows
        ]

    def _filter_clauses(self, options: Search_options, session_id: Optional[str]):
        """Non-content WHERE clauses shared by every search mode."""
        clauses = []
        params: list = []
        kinds = _allowed_block_kinds(options)
        clauses.append("block_kind IN (%s)" % ",".join("?" * len(kinds)))
        params.extend(kinds)
        if session_id is not None:
            clauses.append("session_id = ?")
            params.append(session_id)
        if options.roles is not Search_role.both:
            clauses.append("role = ?")
            params.append(options.roles.value)
        if options.projects:
            clauses.append("project_path IN (%s)" % ",".join("?" * len(options.projects)))
            params.extend(options.projects)
        if options.workspace:
            clauses.append("instr(lower(project_path), lower(?)) > 0")
            params.append(options.workspace.rstrip("/\\"))
        if options.date_from:
            clauses.append("timestamp >= ?")
            params.append(options.date_from)
        if options.date_to:
            clauses.append("timestamp <= ?")
            params.append(options.date_to)
        return clauses, params

    def _run_block_query(self, predicate: str, predicate_params: list, options: Search_options, session_id: Optional[str]):
        clauses, params = self._filter_clauses(options, session_id)
        connection = self._open_for_read()
        rows = connection.execute(
            "SELECT session_id, uuid, role, chat_entry_type, block_index, block_kind, timestamp, content "
            "FROM blocks WHERE " + " AND ".join([predicate] + clauses),
            predicate_params + params,
        ).fetchall()
        connection.close()
        return rows

    def _content_predicate(self, query: str, options: Search_options):
        if options.match_mode is Match_mode.wildcard:
            return "content GLOB ?", ["*" + query + "*"]
        if options.case_sensitive:
            return "instr(content, ?) > 0", [query]
        return "instr(lower(content), lower(?)) > 0", [query]

    def _matching_rows(self, query: str, options: Search_options, session_id: Optional[str] = None):
        if options.match_mode is Match_mode.regex:
            raise NotImplementedError("regex match_mode is not implemented yet")
        predicate, predicate_params = self._content_predicate(query, options)
        return self._run_block_query(predicate, predicate_params, options, session_id)

    def _all_terms_rows(self, terms: list[str], options: Search_options, session_id: Optional[str] = None):
        term_predicates = []
        predicate_params: list = []
        for term in terms:
            if options.case_sensitive:
                term_predicates.append("instr(content, ?) > 0")
            else:
                term_predicates.append("instr(lower(content), lower(?)) > 0")
            predicate_params.append(term)
        predicate = "(" + " OR ".join(term_predicates) + ")"
        return self._run_block_query(predicate, predicate_params, options, session_id)

    def search_all(self, query: str, options: Optional[Search_options] = None) -> Search_all_result:
        options = options or Search_options()
        if options.match_mode is Match_mode.all_terms:
            return self._search_all_terms(query, options)

        rows = self._matching_rows(query, options)
        conversations: dict = {}
        locators: dict = {}
        total_matches = 0
        for row in rows:
            occurrences = count_occurrences(row["content"], query, options)
            total_matches += occurrences
            session_id = row["session_id"]
            conversations[session_id] = conversations.get(session_id, 0) + occurrences
            locator_key = (session_id, row["uuid"])
            locator = locators.get(locator_key)
            if locator is None:
                locator = Chat_entry_locator(
                    uuid=row["uuid"],
                    chat_entry_type=row["chat_entry_type"],
                    timestamp=row["timestamp"],
                    match_count=0,
                    role=row["role"],
                )
                locators[locator_key] = locator
            locator.match_count += occurrences

        locators_by_session: dict = {}
        for (session_id, _), locator in locators.items():
            locators_by_session.setdefault(session_id, []).append(locator)
        return self._assemble_search_result(query, options, conversations, locators_by_session, total_matches)

    def _search_all_terms(self, query: str, options: Search_options) -> Search_all_result:
        terms = query.split()
        if not terms:
            return Search_all_result(query=query, match_mode=options.match_mode, total_conversations=0, total_matches=0, conversations=[])
        unique_terms = set(terms)
        rows = self._all_terms_rows(terms, options)

        present_terms: dict = {}
        entry_matches: dict = {}
        entry_meta: dict = {}
        for row in rows:
            key = (row["session_id"], row["uuid"])
            haystack = row["content"] if options.case_sensitive else row["content"].lower()
            present = present_terms.setdefault(key, set())
            count = 0
            for term in unique_terms:
                occurrences = haystack.count(term if options.case_sensitive else term.lower())
                if occurrences:
                    present.add(term)
                    count += occurrences
            entry_matches[key] = entry_matches.get(key, 0) + count
            entry_meta.setdefault(key, row)

        conversations: dict = {}
        locators_by_session: dict = {}
        total_matches = 0
        for key, present in present_terms.items():
            if len(present) < len(unique_terms):
                continue
            session_id, uuid = key
            count = entry_matches[key]
            total_matches += count
            conversations[session_id] = conversations.get(session_id, 0) + count
            row = entry_meta[key]
            locators_by_session.setdefault(session_id, []).append(
                Chat_entry_locator(
                    uuid=uuid,
                    chat_entry_type=row["chat_entry_type"],
                    timestamp=row["timestamp"],
                    match_count=count,
                    role=row["role"],
                )
            )
        return self._assemble_search_result(query, options, conversations, locators_by_session, total_matches)

    def _assemble_search_result(self, query, options, conversations, locators_by_session, total_matches) -> Search_all_result:
        metadata = self._conversation_metadata(conversations.keys())
        matches = []
        for session_id, match_count in conversations.items():
            meta = metadata.get(session_id, {})
            entries = locators_by_session.get(session_id, [])
            entries.sort(key=lambda item: item.timestamp or "")
            matches.append(
                Conversation_match(
                    session_id=session_id,
                    title=meta.get("title", "(unknown)"),
                    project_path=meta.get("project_path", ""),
                    started_at=meta.get("started_at", ""),
                    last_active_at=meta.get("last_active_at", ""),
                    match_count=match_count,
                    matched_chat_entries=entries,
                )
            )
        matches.sort(key=lambda item: item.match_count, reverse=True)
        if options.offset:
            matches = matches[options.offset:]
        if options.limit is not None:
            matches = matches[: options.limit]
        return Search_all_result(
            query=query,
            match_mode=options.match_mode,
            total_conversations=len(matches),
            total_matches=total_matches,
            conversations=matches,
        )

    def _conversation_metadata(self, session_ids) -> dict:
        session_ids = list(session_ids)
        if not session_ids:
            return {}
        connection = self._connect()
        placeholder = ",".join("?" * len(session_ids))
        rows = connection.execute(
            "SELECT session_id, title, project_path, started_at, last_active_at "
            "FROM conversations WHERE session_id IN (%s)" % placeholder,
            session_ids,
        ).fetchall()
        connection.close()
        return {row["session_id"]: dict(row) for row in rows}

    def search_in_conversation(
        self,
        session_id: str,
        query: str,
        options: Optional[Search_options] = None,
        context: Optional[Context_window] = None,
    ) -> Conversation_search_result:
        options = options or Search_options()
        context = context or Context_window()
        if options.match_mode is Match_mode.all_terms:
            return self._search_in_conversation_all_terms(session_id, query, options, context)

        rows = self._matching_rows(query, options, session_id=session_id)
        entries: dict = {}
        match_count = 0
        for row in rows:
            match = entries.get(row["uuid"])
            if match is None:
                match = Chat_entry_match(
                    uuid=row["uuid"],
                    chat_entry_type=row["chat_entry_type"],
                    timestamp=row["timestamp"],
                    snippets=[],
                    role=row["role"],
                )
                entries[row["uuid"]] = match
            for position, length in _iter_match_positions(row["content"], query, options):
                match_count += 1
                match.snippets.append(
                    _build_snippet(row["content"], position, length, context, row["block_index"], row["block_kind"])
                )
        return self._assemble_conversation_result(session_id, query, options, entries, match_count)

    def _search_in_conversation_all_terms(self, session_id, query, options, context) -> Conversation_search_result:
        terms = query.split()
        unique_terms = set(terms)
        rows = self._all_terms_rows(terms, options, session_id=session_id) if terms else []

        rows_by_entry: dict = {}
        present_terms: dict = {}
        entry_meta: dict = {}
        for row in rows:
            key = row["uuid"]
            rows_by_entry.setdefault(key, []).append(row)
            haystack = row["content"] if options.case_sensitive else row["content"].lower()
            present = present_terms.setdefault(key, set())
            for term in unique_terms:
                if (term if options.case_sensitive else term.lower()) in haystack:
                    present.add(term)
            entry_meta.setdefault(key, row)

        entries: dict = {}
        match_count = 0
        for key, present in present_terms.items():
            if len(present) < len(unique_terms):
                continue
            meta_row = entry_meta[key]
            match = Chat_entry_match(
                uuid=key,
                chat_entry_type=meta_row["chat_entry_type"],
                timestamp=meta_row["timestamp"],
                snippets=[],
                role=meta_row["role"],
            )
            for row in rows_by_entry[key]:
                for term in unique_terms:
                    for position, length in _iter_match_positions(row["content"], term, options):
                        match_count += 1
                        match.snippets.append(
                            _build_snippet(row["content"], position, length, context, row["block_index"], row["block_kind"])
                        )
            entries[key] = match
        return self._assemble_conversation_result(session_id, query, options, entries, match_count)

    def _assemble_conversation_result(self, session_id, query, options, entries, match_count) -> Conversation_search_result:
        metadata = self._conversation_metadata([session_id]).get(session_id, {})
        ordered = sorted(entries.values(), key=lambda item: item.timestamp or "")
        return Conversation_search_result(
            session_id=session_id,
            title=metadata.get("title", "(unknown)"),
            query=query,
            match_mode=options.match_mode,
            match_count=match_count,
            chat_entries=ordered,
        )

    def find_file_origin(self, filename: str, mode: str = "all", tools: Optional[list[str]] = None) -> list[File_origin]:
        basename = path_basename(filename).lower()
        clauses = ["event.basename = ?"]
        params: list = [basename]
        if mode != "all":
            clauses.append("event.operation = ?")
            params.append(mode)
        if tools:
            clauses.append("event.tool IN (%s)" % ",".join("?" * len(tools)))
            params.extend(tools)

        connection = self._open_for_read()
        rows = connection.execute(
            "SELECT event.session_id, event.chat_entry_uuid, event.timestamp, event.file_path, event.tool, "
            "event.operation, event.version, event.has_backup, conversation.title, conversation.project_path "
            "FROM file_events AS event "
            "LEFT JOIN conversations AS conversation ON conversation.session_id = event.session_id "
            "WHERE " + " AND ".join(clauses) + " ORDER BY event.timestamp",
            params,
        ).fetchall()
        connection.close()
        return [
            File_origin(
                file_path=row["file_path"],
                session_id=row["session_id"],
                title=row["title"] or "(unknown)",
                project_path=row["project_path"] or "",
                chat_entry_uuid=row["chat_entry_uuid"],
                timestamp=row["timestamp"],
                operation=row["operation"],
                tool=row["tool"],
                has_backup=bool(row["has_backup"]),
                version=row["version"],
            )
            for row in rows
        ]

    def _session_source_path(self, session_id: str) -> Path:
        connection = self._open_for_read()
        row = connection.execute(
            "SELECT source_path FROM conversations WHERE session_id = ?", (session_id,)
        ).fetchone()
        connection.close()
        if row is None:
            raise ValueError("unknown session_id: %s" % session_id)
        return Path(row["source_path"])

    def _load_family_nodes(self, sessions: list[str]):
        connection = self._open_for_read()
        placeholder = ",".join("?" * len(sessions))
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT session_id, uuid, parent_uuid, timestamp, type, role, has_tool_result, request_id, fingerprint, preview "
                "FROM tree_nodes WHERE session_id IN (%s)" % placeholder,
                sessions,
            ).fetchall()
        ]
        titles = {
            row["session_id"]: row["title"]
            for row in connection.execute(
                "SELECT session_id, title FROM conversations WHERE session_id IN (%s)" % placeholder, sessions
            ).fetchall()
        }
        connection.close()
        return rows, titles

    def get_conversation_tree(
        self,
        session_id: str,
        detail: Tree_detail = Tree_detail.forks_only,
        single: bool = False,
    ) -> Conversation_tree:
        sessions = [session_id] if single else self.get_fork_family(session_id)
        rows, titles = self._load_family_nodes(sessions)
        return build_family_tree(session_id, rows, titles)

    def render_conversation_tree(
        self,
        session_id: str,
        diagram_format: Diagram_format = Diagram_format.mermaid,
        detail: Tree_detail = Tree_detail.forks_only,
        max_nodes: int = 200,
        single: bool = False,
    ) -> Diagram:
        sessions = [session_id] if single else self.get_fork_family(session_id)
        rows, titles = self._load_family_nodes(sessions)
        meta, children, roots, branch_kind = family_structure(rows, titles)
        graph = _reduce_to_graph(meta, children, roots, branch_kind, detail, max_nodes)
        if len(sessions) > 1:
            graph.notes.insert(0, "fork family of %d conversations" % len(sessions))
        return self.render_graph(graph, diagram_format)

    def render_graph(self, graph: Graph, diagram_format: Diagram_format = Diagram_format.mermaid) -> Diagram:
        source = GRAPH_RENDERERS[diagram_format](graph)
        collapsed = sum(node.collapsed_count for node in graph.nodes if node.kind == "collapsed")
        return Diagram(
            diagram_format=diagram_format,
            source=source,
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
            collapsed_count=collapsed,
            notes=list(graph.notes),
        )

    def get_chat_entry(
        self,
        uuid: str,
        session_id: str,
        block_index: Optional[int] = None,
        include_thinking: bool = False,
    ) -> Chat_entry_content:
        connection = self._open_for_read()
        row = connection.execute(
            "SELECT source_path, project_path FROM conversations WHERE session_id = ?", (session_id,)
        ).fetchone()
        connection.close()
        if row is None:
            raise ValueError("unknown session_id: %s" % session_id)

        record = self._find_record(Path(row["source_path"]), uuid)
        if record is None:
            raise ValueError("uuid %s not found in session %s" % (uuid, session_id))

        message = record.get("message") or {}
        blocks = self._reconstruct_blocks(message.get("content"), include_thinking)
        if block_index is not None:
            blocks = [block for block in blocks if block.block_index == block_index]
        return Chat_entry_content(
            uuid=uuid,
            session_id=session_id,
            chat_entry_type=record.get("type"),
            timestamp=record.get("timestamp"),
            project_path=record.get("cwd") or row["project_path"],
            blocks=blocks,
            role=message.get("role"),
        )

    @staticmethod
    def _find_record(path: Path, uuid: str) -> Optional[dict]:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if uuid not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if record.get("uuid") == uuid:
                    return record
        return None

    @staticmethod
    def _reconstruct_blocks(content, include_thinking: bool) -> list[Block]:
        if isinstance(content, str):
            return [Block(block_index=0, block_type="text", text=content)]
        if not isinstance(content, list):
            return []
        blocks = []
        for block_index, raw in enumerate(content):
            if not isinstance(raw, dict):
                continue
            block_type = raw.get("type")
            if block_type == "text":
                blocks.append(Block(block_index=block_index, block_type="text", text=raw.get("text", "")))
            elif block_type == "thinking":
                if include_thinking:
                    blocks.append(Block(block_index=block_index, block_type="thinking", text=raw.get("thinking", "")))
            elif block_type == "tool_use":
                blocks.append(
                    Block(
                        block_index=block_index,
                        block_type="tool_use",
                        tool_name=raw.get("name"),
                        tool_input=raw.get("input"),
                    )
                )
            elif block_type == "tool_result":
                blocks.append(
                    Block(
                        block_index=block_index,
                        block_type="tool_result",
                        tool_result_text=extract_tool_result_text(raw.get("content")),
                    )
                )
        return blocks

"""CCD conversation structure — fork fingerprints, trees, fork families, diagrams.

Module-level functions build a render-neutral `Graph` from a session's `uuid`/`parentUuid` structure or from a whole fork family; `graph_to_mermaid` / `graph_to_dot` are the only two diagram emitters.
`Tree_mixin` is mixed into `Chat_digger` (see `CCD_engine.py`); its methods rely on `self._open_for_read()`, which the concrete class provides.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Optional

from CCD_api import (
    MESSAGE_TYPES,
    Branch_point,
    Conversation_tree,
    Diagram,
    Diagram_format,
    Family_summary,
    Graph,
    Graph_edge,
    Graph_node,
    Tree_detail,
    Tree_node,
)
from CCD_parsing import extract_tool_result_text

TREE_PREVIEW_LENGTH = 40


def fork_fingerprint(timestamp: Optional[str], content_text: str, uuid: str) -> str:
    """A copy-stable id for a record: timestamp + content hash.

    A fork copies records verbatim, so two records sharing this fingerprint across files are the same copied record.
    Records with no timestamp or empty content fall back to a uuid-based id so they never merge across files by accident.
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

    Only `user` / `assistant` records become tree nodes.
    Injected attachment / system / queue records are skipped and each message is reparented to its nearest message ancestor, so the tree is the conversation flow rather than the plumbing — and forks are not confused by attachments being linked differently across copied files.
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

    Iterative so a long conversation cannot overflow the recursion limit; a node reached by more than one parent is sized once, which is good enough for the branch test.
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

    A fork is a node where two or more branches each carry real content; a branch of only an entry or two is treated as noise (tool structure, a dead-end rewind) rather than a fork, so a long backbone does not turn every turn into a branch.
    Each fork keeps the entry just before it and the first entry of each branch after it; everything else between forks folds into one aggregated count node, and dead-end runs below a fork fold into a single count node rather than several parallel ones.
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

    `meta[node_id]` carries `type`, `has_tool_result`, `label`, and `ref`.
    Works for a single file (nodes keyed by uuid) or a whole fork family (nodes keyed by fingerprint).
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

    Records a fork copied share a fingerprint and collapse to one node; the within-file parent links, translated to fingerprints and unioned, reveal the cross-file forks.
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


GRAPH_RENDERERS = {
    Diagram_format.mermaid: graph_to_mermaid,
    Diagram_format.dot: graph_to_dot,
}


class Tree_mixin:
    """`Chat_digger` methods for fork families, conversation trees, and diagrams."""

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

    def conversation_graph(
        self,
        session_id: str,
        detail: Tree_detail = Tree_detail.forks_only,
        max_nodes: int = 200,
        single: bool = False,
    ) -> Graph:
        sessions = [session_id] if single else self.get_fork_family(session_id)
        rows, titles = self._load_family_nodes(sessions)
        meta, children, roots, branch_kind = family_structure(rows, titles)
        graph = _reduce_to_graph(meta, children, roots, branch_kind, detail, max_nodes)
        if len(sessions) > 1:
            graph.notes.insert(0, "fork family of %d conversations" % len(sessions))
        return graph

    def render_conversation_tree(
        self,
        session_id: str,
        diagram_format: Diagram_format = Diagram_format.mermaid,
        detail: Tree_detail = Tree_detail.forks_only,
        max_nodes: int = 200,
        single: bool = False,
    ) -> Diagram:
        graph = self.conversation_graph(session_id, detail=detail, max_nodes=max_nodes, single=single)
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

"""CCD engine — indexing and the `Chat_digger` orchestrator.

The index is a plain SQLite database with one row per searchable block; matching uses substring / glob scans rather than a tokenised full-text index.
A separate table records file create/edit/read events for `find_file_origin`.
Indexing is always a full rebuild — searches read the stored index and refuse to run if its `CCD_version` does not match this code.
The public surface mirrors `CCD_api.py`.

`Chat_digger` binds three concerns to the SQLite index: corpus parsing (`CCD_parsing`), content search (`CCD_search.Search_mixin`), and conversation structure — fork families, trees, diagrams (`CCD_tree.Tree_mixin`).
This module holds connection/schema management, indexing, and the handful of methods (`find_file_origin`, `get_chat_entry`, ...) that don't belong to either mixin.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from CCD_api import Block, Chat_entry_content, Conversation_meta, File_origin, Index_stats, Search_options
from CCD_parsing import (
    default_corpus_root,
    default_index_path,
    extract_tool_result_text,
    iter_session_files,
    parse_session_file,
    path_basename,
    _extract_message_meta,
)
from CCD_search import Search_mixin
from CCD_tree import Tree_mixin, read_tree_records

CCD_INDEX_VERSION = 3


class Chat_digger(Search_mixin, Tree_mixin):
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
        """Rebuild the whole index from scratch.

        The only path that writes it.
        """
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

    def get_chat_entry(
        self,
        uuid: str,
        session_id: str,
        block_index: Optional[int] = None,
        include_thinking: bool = False,
        include_meta: bool = False,
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
            meta=_extract_message_meta(record) if include_meta else None,
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

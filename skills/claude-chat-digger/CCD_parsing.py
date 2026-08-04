"""CCD corpus parsing — raw `.jsonl` records to structured rows.

Turns one session file into a conversation row, block rows, and file-event rows (`parse_session_file`), and reads a record's full metadata on demand for `show --meta` (`_extract_message_meta`).
No SQLite or search logic lives here.
"""

from __future__ import annotations

import collections
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from CCD_api import MESSAGE_TYPES, Message_meta

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

    `trackedFileBackups` is a cumulative per-version map, so versions are keyed directly and a backup file name is preferred over a null when the same version recurs.
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


RECORD_META_CONSUMED_KEYS = {
    "uuid",
    "parentUuid",
    "timestamp",
    "type",
    "message",
    "cwd",
    "sessionId",
    "snapshot",
    "gitBranch",
    "version",
    "entrypoint",
    "userType",
    "permissionMode",
    "isSidechain",
    "agentId",
    "requestId",
    "promptId",
    "promptSource",
    "attributionAgent",
    "attributionMcpServer",
    "attributionMcpTool",
    "attributionSkill",
}

MESSAGE_META_CONSUMED_KEYS = {"content", "role", "id", "model", "usage", "stop_reason"}


def _extract_message_meta(record: dict) -> Message_meta:
    """Everything on a record and its message beyond content, for `show --meta`.

    Reads straight from the already-parsed raw record — model, usage, git branch, and the rest of the well-established fields by name; every other top-level or message field lands in `extra` so a field this function does not yet know about is never silently dropped.
    """
    message = record.get("message") if isinstance(record.get("message"), dict) else {}
    extra = {key: value for key, value in record.items() if key not in RECORD_META_CONSUMED_KEYS}
    extra.update({key: value for key, value in message.items() if key not in MESSAGE_META_CONSUMED_KEYS})
    return Message_meta(
        model=message.get("model"),
        usage=message.get("usage"),
        stop_reason=message.get("stop_reason"),
        git_branch=record.get("gitBranch"),
        cc_version=record.get("version"),
        entrypoint=record.get("entrypoint"),
        user_type=record.get("userType"),
        permission_mode=record.get("permissionMode"),
        is_sidechain=bool(record.get("isSidechain")),
        agent_id=record.get("agentId"),
        attribution_agent=record.get("attributionAgent"),
        attribution_mcp_server=record.get("attributionMcpServer"),
        attribution_mcp_tool=record.get("attributionMcpTool"),
        attribution_skill=record.get("attributionSkill"),
        request_id=record.get("requestId"),
        prompt_id=record.get("promptId"),
        prompt_source=record.get("promptSource"),
        extra=extra,
    )

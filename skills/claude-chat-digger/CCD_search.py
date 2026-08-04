"""CCD content search — matching primitives plus the `Chat_digger` search methods.

`Search_mixin` is mixed into `Chat_digger` (see `CCD_engine.py`); its methods rely on `self._open_for_read()` / `self.index_path`, which the concrete class provides.
"""

from __future__ import annotations

import re
from typing import Optional

from CCD_api import (
    Chat_entry_locator,
    Chat_entry_match,
    Context_unit,
    Context_window,
    Conversation_match,
    Conversation_search_result,
    Match_mode,
    Search_all_result,
    Search_options,
    Search_role,
    Snippet,
)


def _allowed_block_kinds(options: Search_options) -> list[str]:
    kinds = ["text"]
    if options.include_thinking:
        kinds.append("thinking")
    if options.include_tool_input:
        kinds.append("tool_input")
    if options.include_tool_result:
        kinds.append("tool_result")
    return kinds


WILDCARD_TOKEN_PATTERN = re.compile(r"\*|\?|\[[^\]]*\]|[^*?\[]+|.", re.DOTALL)


def _wildcard_pattern(query: str, case_sensitive: bool) -> re.Pattern:
    """A glob pattern as a "find each occurrence" regex.

    This is deliberately not the same test the SQL GLOB filter runs: GLOB is a whole-string membership test with no notion of greediness, while this pattern locates and counts individual occurrences within a block, so `*` is translated to a non-greedy `.*?` rather than the mathematically literal "any sequence".
    A greedy `*` would let one occurrence span from its first anchor to the *last* matching text anywhere later in the block, collapsing what should be several separate hits (e.g. three instances of "fix...bug" in one block) into a single sprawling match.
    Bracket expressions (`[...]`) pass through unmodified, on a best-effort basis: glob's bracket syntax and Python regex character classes mostly overlap but are not guaranteed identical.
    """
    parts = []
    for token in WILDCARD_TOKEN_PATTERN.findall(query):
        if token == "*":
            parts.append(".*?")
        elif token == "?":
            parts.append(".")
        elif token.startswith("[") and token.endswith("]"):
            parts.append(token)
        else:
            parts.append(re.escape(token))
    return re.compile("".join(parts), 0 if case_sensitive else re.IGNORECASE)


def count_occurrences(content: str, query: str, options: Search_options) -> int:
    if options.match_mode is Match_mode.substring:
        if options.case_sensitive:
            return content.count(query)
        return content.lower().count(query.lower())
    if options.match_mode is Match_mode.wildcard:
        return len(list(_wildcard_pattern(query, options.case_sensitive).finditer(content)))
    return 1


def _iter_match_positions(content: str, query: str, options: Search_options, cap: int = 3):
    if options.match_mode is Match_mode.wildcard:
        pattern = _wildcard_pattern(query, options.case_sensitive)
        found = 0
        for match in pattern.finditer(content):
            if found >= cap:
                return
            yield match.start(), match.end() - match.start()
            found += 1
        return
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


class Search_mixin:
    """`Chat_digger` methods for tier-1 / tier-2 content search."""

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
            pattern = "*" + query + "*"
            if options.case_sensitive:
                return "content GLOB ?", [pattern]
            return "lower(content) GLOB lower(?)", [pattern]
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

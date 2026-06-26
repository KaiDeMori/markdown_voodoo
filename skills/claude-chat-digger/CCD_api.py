"""CCD public API — shapes only.

Signatures and return types for discussion; no behaviour is implemented. The three
search methods form a progressive-disclosure ladder: locate without content, then
bounded snippets, then full content by exact id. A conversation tree is serialised to
diagram-ready text deterministically — the model never draws a graph by hand. See
api_design.md for rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Match_mode(Enum):
    substring = "substring"
    all_terms = "all_terms"  # every whitespace-separated term, same chat_entry, any order
    wildcard = "wildcard"  # glob-style * and ?
    phrase = "phrase"
    regex = "regex"


class Context_unit(Enum):
    chars = "chars"
    lines = "lines"


class Search_role(Enum):
    user = "user"
    assistant = "assistant"
    both = "both"


class Tree_detail(Enum):
    """How much of a conversation tree survives collapsing before rendering."""

    short = "short"  # only real forks; everything between them aggregated into one count node
    forks_only = "forks_only"
    turns = "turns"
    full = "full"


class Diagram_format(Enum):
    mermaid = "mermaid"
    dot = "dot"
    graph_json = "graph_json"


@dataclass
class Search_options:
    """Filters shared by the search methods."""

    match_mode: Match_mode = Match_mode.substring
    case_sensitive: bool = False
    projects: Optional[list[str]] = None
    workspace: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    roles: Search_role = Search_role.both
    include_thinking: bool = False
    include_tool_input: bool = True
    include_tool_result: bool = False
    limit: Optional[int] = None
    offset: int = 0


@dataclass
class Context_window:
    """How much surrounding text a tier-2 snippet carries around each match."""

    before: int = 2
    after: int = 2
    unit: Context_unit = Context_unit.lines


@dataclass
class Chat_entry_locator:
    """Where a match is, with no content — the tier-1 unit."""

    uuid: str
    chat_entry_type: str
    timestamp: str
    match_count: int
    role: Optional[str] = None


@dataclass
class Conversation_match:
    session_id: str
    title: str
    project_path: str
    started_at: str
    last_active_at: str
    match_count: int
    matched_chat_entries: list[Chat_entry_locator] = field(default_factory=list)


@dataclass
class Search_all_result:
    query: str
    match_mode: Match_mode
    total_conversations: int
    total_matches: int
    conversations: list[Conversation_match] = field(default_factory=list)


@dataclass
class Snippet:
    """A single match plus its bounded surrounding context, located to a block.

    `block_index` is the position of the matched block within its entry — the handle
    a tier-3 `get_chat_entry(..., block_index=...)` uses to fetch just that block.
    """

    block_index: int
    block_type: str
    before: str
    match: str
    after: str
    char_offset: int
    truncated: bool


@dataclass
class Chat_entry_match:
    uuid: str
    chat_entry_type: str
    timestamp: str
    snippets: list[Snippet] = field(default_factory=list)
    role: Optional[str] = None


@dataclass
class Conversation_search_result:
    session_id: str
    title: str
    query: str
    match_mode: Match_mode
    match_count: int
    chat_entries: list[Chat_entry_match] = field(default_factory=list)


@dataclass
class Block:
    """One content block of a chat entry, fully reconstructed."""

    block_index: int
    block_type: str
    text: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_result_text: Optional[str] = None


@dataclass
class Chat_entry_content:
    """The full content of one chat entry, or a single block of it.

    The only shape that returns unbounded content; a `block_index` fetch narrows it to
    one block so a small text block need not drag along a huge `tool_result`.
    """

    uuid: str
    session_id: str
    chat_entry_type: str
    timestamp: str
    project_path: str
    blocks: list[Block] = field(default_factory=list)
    role: Optional[str] = None


@dataclass
class File_origin:
    """A point where a file was created, edited, or read within some conversation."""

    file_path: str
    session_id: str
    title: str
    project_path: str
    chat_entry_uuid: str
    timestamp: str
    operation: str  # created | edited | read
    tool: str  # Write | Edit | NotebookEdit | Read
    has_backup: bool
    version: Optional[int] = None


@dataclass
class Tree_node:
    uuid: str
    chat_entry_type: str
    timestamp: str
    parent_uuid: Optional[str]
    child_uuids: list[str] = field(default_factory=list)


@dataclass
class Branch_point:
    uuid: str
    child_uuids: list[str]
    kind: str  # tool_structure | real_fork


@dataclass
class Conversation_tree:
    """A fork family reduced to its branch points and leaves.

    Spans the whole family (a lone conversation is a family of one). Nodes are keyed by
    fork fingerprint, so a record copied into several forked files is one node; the
    `sessions` it carries say which conversations share it.
    """

    session_id: str
    sessions: list[str] = field(default_factory=list)
    nodes: list[Tree_node] = field(default_factory=list)
    branch_points: list[Branch_point] = field(default_factory=list)
    leaves: list[str] = field(default_factory=list)


@dataclass
class Graph_node:
    """A render-neutral node. `ref_uuid` ties it back to a chat entry for
    click-through; `collapsed_count` is how many original entries it stands in for.
    """

    id: str
    label: str
    kind: str  # root | branch_point | leaf | collapsed | turn
    ref_uuid: Optional[str] = None
    collapsed_count: int = 1


@dataclass
class Graph_edge:
    source_id: str
    target_id: str
    label: Optional[str] = None


@dataclass
class Graph:
    """A render-neutral graph that any diagram format is emitted from."""

    directed: bool = True
    nodes: list[Graph_node] = field(default_factory=list)
    edges: list[Graph_edge] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class Diagram:
    """Diagram-ready source text plus a record of what it took to fit on a page.

    `notes` carries any deterministic reductions (collapsed runs, applied caps) so a
    reader is told what was hidden rather than it vanishing silently.
    """

    diagram_format: Diagram_format
    source: str
    node_count: int
    edge_count: int
    collapsed_count: int = 0
    notes: list[str] = field(default_factory=list)


@dataclass
class Conversation_meta:
    """A conversation's identity for browsing, independent of any search."""

    session_id: str
    title: str
    project_path: str
    started_at: str
    last_active_at: str
    chat_entry_count: int


@dataclass
class Family_summary:
    """One fork family condensed for a workspace overview.

    A lone conversation is a family of one — `session_count` 1 and, for a linear chat,
    one leaf. `root_session_id` is the family's original (oldest) conversation, the one
    to hand to `tree`; `node_count` is the family's unique entries, the shared prefix
    counted once across forks.
    """

    family_id: str
    root_session_id: str
    title: str
    project_path: str
    started_at: str
    last_active_at: str
    session_count: int
    leaf_count: int
    node_count: int


@dataclass
class Index_stats:
    conversation_count: int
    chat_entry_count: int
    built_at: str
    is_stale: bool


class Chat_digger:
    """Entry point over an indexed corpus of Claude Code conversations.

    `index_path` is where the search index lives; the corpus root defaults to the
    standard `~/.claude/projects` location when not given.
    """

    def __init__(self, index_path: Optional[str] = None, corpus_root: Optional[str] = None) -> None:
        raise NotImplementedError

    def build_index(self) -> Index_stats:
        """Rebuild the whole search index from scratch — the only path that builds it.

        Always a full rebuild (no incremental). Searches never build on their own; they
        read whatever this last produced and refuse to run against an index whose stored
        `CCD_version` does not match the code.
        """
        raise NotImplementedError

    def index_status(self) -> Index_stats:
        """Report what the index holds and whether it is stale — i.e. the corpus
        changed since the last `build_index`, so a rebuild is due.
        """
        raise NotImplementedError

    def list_conversations(self, options: Optional[Search_options] = None) -> list[Conversation_meta]:
        """Browse conversations (optionally filtered) without a text query."""
        raise NotImplementedError

    def search_all(self, query: str, options: Optional[Search_options] = None) -> Search_all_result:
        """Tier 1: locate matches across all conversations.

        Returns conversation metadata and matched chat-entry locators only. Never
        returns chat content or snippets.
        """
        raise NotImplementedError

    def search_in_conversation(
        self,
        session_id: str,
        query: str,
        options: Optional[Search_options] = None,
        context: Optional[Context_window] = None,
    ) -> Conversation_search_result:
        """Tier 2: matches within one conversation, each as bounded snippets.

        A chat entry is never returned whole here, regardless of its size; only
        `context` worth of surrounding text accompanies each match. Each snippet
        carries its `block_index` so the exact block can be fetched at tier 3.
        """
        raise NotImplementedError

    def get_chat_entry(
        self,
        uuid: str,
        session_id: str,
        block_index: Optional[int] = None,
        include_thinking: bool = False,
    ) -> Chat_entry_content:
        """Tier 3: the full content of one chat entry by exact id.

        `session_id` is required: it locates the file directly and doubles as a safety
        check — a uuid not found under that session is an error, not an empty result.
        `block_index` returns just that one block (omit for every block), so a one-line
        text block need not drag along a huge `tool_result` in the same entry.
        """
        raise NotImplementedError

    def find_file_origin(
        self,
        filename: str,
        mode: str = "all",
        tools: Optional[list[str]] = None,
    ) -> list[File_origin]:
        """Conversations where a file was created, edited, or read.

        Reads `file-history-snapshot` records and Read/Write/Edit/NotebookEdit tool
        calls rather than free-text search. `filename` is matched against the recorded
        path's basename (case-insensitive). `mode` is one of created | edited | read |
        all; `tools` defaults to all four tools when not given.
        """
        raise NotImplementedError

    def get_fork_family(self, session_id: str) -> list[str]:
        """The sessions in this conversation's fork family (just itself if it has none)."""
        raise NotImplementedError

    def list_families(
        self,
        workspace: Optional[str] = None,
        project: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> "list[Family_summary]":
        """Every fork family in a workspace, condensed to one summary each.

        Each lone conversation is its own family of one, so the overview is uniform: one
        line per family with its session and leaf counts. `workspace` matches a project
        folder and everything under it; `project` is one exact path. Most recent first.
        """
        raise NotImplementedError

    def get_conversation_tree(
        self,
        session_id: str,
        detail: Tree_detail = Tree_detail.forks_only,
        single: bool = False,
    ) -> Conversation_tree:
        """A fork family's structure reduced to branch points and leaves.

        Auto-spans the whole family; `single=True` restricts to the one session file.
        Branch points are classified as tool-call structure vs genuine cross-file forks.
        """
        raise NotImplementedError

    def render_conversation_tree(
        self,
        session_id: str,
        diagram_format: Diagram_format = Diagram_format.mermaid,
        detail: Tree_detail = Tree_detail.forks_only,
        max_nodes: int = 200,
        single: bool = False,
    ) -> Diagram:
        """Render the fork family as one diagram, splicing forks at their fork points.

        Auto-spans the family (`single=True` restricts to one file). Deterministic end
        to end; beyond `max_nodes` the tree is coarsened and the reduction is noted.
        """
        raise NotImplementedError

    def render_graph(self, graph: Graph, diagram_format: Diagram_format = Diagram_format.mermaid) -> Diagram:
        """Serialise an already-built render-neutral graph into one diagram format.

        Pure: identifiers are sanitised and labels escaped per the target format; no
        corpus access. This is the single point every diagram format is emitted from.
        """
        raise NotImplementedError

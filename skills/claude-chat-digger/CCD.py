"""CCD command line — index and search past Claude Code conversations.

Usage:
    python CCD.py index [--rebuild]
    python CCD.py status
    python CCD.py search "<query>" [options]
    python CCD.py in <session_id> "<query>" [--context N] [options]
    python CCD.py show <session_id> <uuid> [--block N] [--thinking]
    python CCD.py list [--limit N]
"""

from __future__ import annotations

import argparse
import sys

from CCD_api import (
    Context_unit,
    Context_window,
    Diagram_format,
    Match_mode,
    Search_options,
    Search_role,
    Tree_detail,
)
from CCD_engine import CCD_INDEX_VERSION, Chat_digger


def force_utf8_output() -> None:
    """Keep output alive on a legacy Windows console that cannot encode unicode."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def format_when(timestamp: str) -> str:
    if not timestamp:
        return "?"
    return timestamp.replace("T", " ")[:16]


def build_search_options(arguments) -> Search_options:
    match_mode = Match_mode.all_terms if arguments.all else Match_mode(arguments.mode)
    return Search_options(
        match_mode=match_mode,
        case_sensitive=arguments.case_sensitive,
        projects=[arguments.project] if arguments.project else None,
        workspace=arguments.workspace,
        date_from=arguments.date_from,
        date_to=arguments.date_to,
        roles=Search_role(arguments.role),
        include_thinking=arguments.thinking,
        include_tool_input=not arguments.no_tool_input,
        include_tool_result=arguments.tool_result,
        limit=arguments.limit,
    )


def add_search_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mode", choices=[mode.value for mode in Match_mode], default="substring")
    parser.add_argument("--all", action="store_true", help="require ALL whitespace-separated terms in the same chat_entry")
    parser.add_argument("--case-sensitive", action="store_true")
    parser.add_argument("--role", choices=[role.value for role in Search_role], default="both")
    parser.add_argument("--project", default=None, help="restrict to one exact project path")
    parser.add_argument("--workspace", default=None, help="restrict to a workspace folder and everything under it")
    parser.add_argument("--date-from", default=None)
    parser.add_argument("--date-to", default=None)
    parser.add_argument("--thinking", action="store_true", help="also search thinking blocks")
    parser.add_argument("--no-tool-input", action="store_true", help="skip tool inputs")
    parser.add_argument("--tool-result", action="store_true", help="also search tool result bodies")
    parser.add_argument("--limit", type=int, default=20)


def command_index(digger: Chat_digger, arguments) -> None:
    print("Indexing %s ..." % digger.corpus_root)
    stats = digger.build_index()
    print("Indexed %d conversations, %d searchable blocks." % (stats.conversation_count, stats.chat_entry_count))


def command_status(digger: Chat_digger, arguments) -> None:
    stats = digger.index_status()
    version = digger.index_version()
    print("Index: %s" % digger.index_path)
    print("Conversations : %d" % stats.conversation_count)
    print("Blocks        : %d" % stats.chat_entry_count)
    print("Stale         : %s" % ("yes — rebuild due" if stats.is_stale else "no"))
    print("CCD_version   : db=%s code=%d%s" % (version, CCD_INDEX_VERSION, "" if version == CCD_INDEX_VERSION else "  -> rebuild needed"))


def command_search(digger: Chat_digger, arguments) -> None:
    options = build_search_options(arguments)
    result = digger.search_all(arguments.query, options)
    print(
        "'%s' — %d matches across %d conversations\n"
        % (result.query, result.total_matches, result.total_conversations)
    )
    for rank, conversation in enumerate(result.conversations, start=1):
        print("%2d. [%d] %s" % (rank, conversation.match_count, conversation.title))
        print("      when    : %s" % format_when(conversation.last_active_at))
        print("      project : %s" % conversation.project_path)
        print("      session : %s" % conversation.session_id)
        print("      entries : %d matched" % len(conversation.matched_chat_entries))
        print()


def command_in(digger: Chat_digger, arguments) -> None:
    options = build_search_options(arguments)
    context = Context_window(before=arguments.context, after=arguments.context, unit=Context_unit.lines)
    result = digger.search_in_conversation(arguments.session_id, arguments.query, options, context)
    print("'%s' in %s — %s" % (result.query, result.title, result.session_id))
    print("%d matches in %d entries\n" % (result.match_count, len(result.chat_entries)))
    for entry in result.chat_entries:
        print("- %s %s  %s" % (entry.chat_entry_type, format_when(entry.timestamp), entry.uuid))
        for snippet in entry.snippets:
            body = "%s>>>%s<<<%s" % (snippet.before, snippet.match, snippet.after)
            print("    [block %d/%s] %s" % (snippet.block_index, snippet.block_type, body.replace("\n", "\n      ")))
        print()


def command_show(digger: Chat_digger, arguments) -> None:
    entry = digger.get_chat_entry(
        arguments.uuid, arguments.session_id, block_index=arguments.block, include_thinking=arguments.thinking
    )
    print("%s %s  %s" % (entry.chat_entry_type, format_when(entry.timestamp), entry.uuid))
    print("project: %s\n" % entry.project_path)
    for block in entry.blocks:
        header = "[block %d/%s]" % (block.block_index, block.block_type)
        if block.block_type == "tool_use":
            print("%s %s %s" % (header, block.tool_name, block.tool_input))
        elif block.block_type == "tool_result":
            print("%s\n%s" % (header, block.tool_result_text))
        else:
            print("%s\n%s" % (header, block.text))
        print()


def command_origin(digger: Chat_digger, arguments) -> None:
    tools = arguments.tool.split(",") if arguments.tool else None
    origins = digger.find_file_origin(arguments.filename, mode=arguments.mode, tools=tools)
    print("'%s' — %d file events\n" % (arguments.filename, len(origins)))
    for origin in origins:
        version = "" if origin.version is None else "  v%d%s" % (origin.version, " [backup]" if origin.has_backup else "")
        print("%s  %-7s via %-12s %s" % (format_when(origin.timestamp), origin.operation, origin.tool, origin.file_path))
        print("      %s  —  %s%s" % (origin.title, origin.session_id, version))
        print()


def command_family(digger: Chat_digger, arguments) -> None:
    sessions = digger.get_fork_family(arguments.session_id)
    print("fork family of %d conversation(s):\n" % len(sessions))
    for session_id in sessions:
        print("  %s" % session_id)


def command_families(digger: Chat_digger, arguments) -> None:
    families = digger.list_families(workspace=arguments.workspace, project=arguments.project, limit=arguments.limit)
    scope = arguments.workspace or arguments.project
    print("%d fork %s%s\n" % (len(families), "family" if len(families) == 1 else "families", " in %s" % scope if scope else ""))
    for family in families:
        if family.session_count == 1:
            shape = "single conversation"
        else:
            shape = "%d sessions, %d forks" % (family.session_count, family.session_count - 1)
        print("%s  %s  %s" % (format_when(family.last_active_at), family.root_session_id, family.title))
        print("      %s · %d leaves · %d entries" % (shape, family.leaf_count, family.node_count))
        print("      project : %s" % family.project_path)
        print()


def command_tree(digger: Chat_digger, arguments) -> None:
    diagram = digger.render_conversation_tree(
        arguments.session_id,
        diagram_format=Diagram_format(arguments.format),
        detail=Tree_detail(arguments.detail),
        max_nodes=arguments.max_nodes,
        single=arguments.single,
    )
    summary = "%d nodes, %d edges, %d entries folded" % (diagram.node_count, diagram.edge_count, diagram.collapsed_count)
    if arguments.out:
        with open(arguments.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(diagram.source if diagram.source.endswith("\n") else diagram.source + "\n")
        print("wrote %s diagram (%s) to %s" % (arguments.format, summary, arguments.out))
        for note in diagram.notes:
            print("note: %s" % note)
        return
    print("# %s" % summary)
    for note in diagram.notes:
        print("# note: %s" % note)
    print()
    print(diagram.source)


def command_list(digger: Chat_digger, arguments) -> None:
    conversations = digger.list_conversations()
    for conversation in conversations[: arguments.limit]:
        print(
            "%s  %s  %s"
            % (format_when(conversation.last_active_at), conversation.session_id, conversation.title)
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="CCD", description="Search past Claude Code conversations.")
    parser.add_argument("--index-path", default=None)
    parser.add_argument("--corpus-root", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="rebuild the search index from scratch")
    index_parser.set_defaults(handler=command_index)

    status_parser = subparsers.add_parser("status", help="show index status")
    status_parser.set_defaults(handler=command_status)

    search_parser = subparsers.add_parser("search", help="search all conversations")
    search_parser.add_argument("query")
    add_search_filters(search_parser)
    search_parser.set_defaults(handler=command_search)

    in_parser = subparsers.add_parser("in", help="search within one conversation")
    in_parser.add_argument("session_id")
    in_parser.add_argument("query")
    in_parser.add_argument("--context", type=int, default=2)
    add_search_filters(in_parser)
    in_parser.set_defaults(handler=command_in)

    show_parser = subparsers.add_parser("show", help="show one chat entry in full")
    show_parser.add_argument("session_id")
    show_parser.add_argument("uuid")
    show_parser.add_argument("--block", type=int, default=None)
    show_parser.add_argument("--thinking", action="store_true")
    show_parser.set_defaults(handler=command_show)

    origin_parser = subparsers.add_parser("origin", help="find where a file was created/edited/read")
    origin_parser.add_argument("filename")
    origin_parser.add_argument("--mode", choices=["all", "created", "edited", "read"], default="all")
    origin_parser.add_argument("--tool", default=None, help="comma-separated tools, e.g. Write,Edit")
    origin_parser.set_defaults(handler=command_origin)

    tree_parser = subparsers.add_parser("tree", help="render a conversation's fork family as a diagram")
    tree_parser.add_argument("session_id")
    tree_parser.add_argument("--format", choices=[fmt.value for fmt in Diagram_format], default="mermaid")
    tree_parser.add_argument("--detail", choices=[detail.value for detail in Tree_detail], default="forks_only")
    tree_parser.add_argument("--max-nodes", type=int, default=200)
    tree_parser.add_argument("--single", action="store_true", help="restrict to this one session, not the whole family")
    tree_parser.add_argument("--out", "-o", default=None, help="write the diagram source to this file instead of stdout")
    tree_parser.set_defaults(handler=command_tree)

    family_parser = subparsers.add_parser("family", help="list the sessions in a conversation's fork family")
    family_parser.add_argument("session_id")
    family_parser.set_defaults(handler=command_family)

    families_parser = subparsers.add_parser("families", help="overview of all fork families in a workspace")
    families_parser.add_argument("--workspace", default=None, help="restrict to a workspace folder and everything under it")
    families_parser.add_argument("--project", default=None, help="restrict to one exact project path")
    families_parser.add_argument("--limit", type=int, default=40)
    families_parser.set_defaults(handler=command_families)

    list_parser = subparsers.add_parser("list", help="list indexed conversations")
    list_parser.add_argument("--limit", type=int, default=40)
    list_parser.set_defaults(handler=command_list)

    return parser


def main() -> None:
    force_utf8_output()
    arguments = build_parser().parse_args()
    digger = Chat_digger(index_path=arguments.index_path, corpus_root=arguments.corpus_root)
    try:
        arguments.handler(digger, arguments)
    except (ValueError, FileNotFoundError) as error:
        print("error: %s" % error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

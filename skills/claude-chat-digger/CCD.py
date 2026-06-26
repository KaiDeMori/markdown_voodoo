"""CCD command line — index and search past Claude Code conversations.

Usage:
    python CCD.py index [--rebuild]
    python CCD.py status
    python CCD.py search "<query>" [options]
    python CCD.py in <session_id> "<query>" [--context N] [options]
    python CCD.py show <session_id> <uuid> [--block N] [--thinking]
    python CCD.py list [--limit N]

Every command accepts --out/-o FILE to write its full result to a UTF-8 file and
print a one-line receipt to the console instead of dumping the result to stdout.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

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


@dataclass
class Command_output:
    """A command's rendered result, decoupled from where it is sent.

    `body` is the full payload — the only thing ever written to an `--out` file.
    `summary` is a one-line detail (counts) for the file-write receipt; `notes`
    are deterministic reductions reported alongside the result, never folded into
    the payload so a saved file stays clean.
    """

    body: str
    summary: str = ""
    notes: list[str] = field(default_factory=list)


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


def add_output_option(parser: argparse.ArgumentParser) -> None:
    """Give a subcommand the uniform `--out`/`-o` file destination.

    Writing through this flag rather than shell redirection guarantees a UTF-8 file
    with newline line endings regardless of the host shell, and keeps the receipt
    out of the saved payload.
    """
    parser.add_argument(
        "--out",
        "-o",
        default=None,
        help="write the full result to this file (UTF-8); print a one-line receipt instead",
    )


def emit(output: Command_output, out_path) -> None:
    """Send a command's result to its destination: a file plus a receipt, or stdout.

    The payload (`body`) is the only thing on the chosen sink; the receipt and any
    notes are diagnostics and go to stderr, so a piped or redirected payload stays
    pure even for formats like JSON where a trailing note line would be invalid.
    """
    if out_path:
        text = output.body if output.body.endswith("\n") else output.body + "\n"
        with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        detail = " (%s)" % output.summary if output.summary else ""
        print("wrote output%s to %s" % (detail, out_path), file=sys.stderr)
    else:
        print(output.body)
    for note in output.notes:
        print("note: %s" % note, file=sys.stderr)


def command_index(digger: Chat_digger, arguments) -> Command_output:
    print("Indexing %s ..." % digger.corpus_root)
    stats = digger.build_index()
    summary = "%d conversations, %d blocks" % (stats.conversation_count, stats.chat_entry_count)
    body = "Indexed %d conversations, %d searchable blocks." % (stats.conversation_count, stats.chat_entry_count)
    return Command_output(body=body, summary=summary)


def command_status(digger: Chat_digger, arguments) -> Command_output:
    stats = digger.index_status()
    version = digger.index_version()
    version_note = "" if version == CCD_INDEX_VERSION else "  -> rebuild needed"
    lines = [
        "Index: %s" % digger.index_path,
        "Conversations : %d" % stats.conversation_count,
        "Blocks        : %d" % stats.chat_entry_count,
        "Stale         : %s" % ("yes — rebuild due" if stats.is_stale else "no"),
        "CCD_version   : db=%s code=%d%s" % (version, CCD_INDEX_VERSION, version_note),
    ]
    return Command_output(body="\n".join(lines))


def command_search(digger: Chat_digger, arguments) -> Command_output:
    options = build_search_options(arguments)
    result = digger.search_all(arguments.query, options)
    summary = "%d matches across %d conversations" % (result.total_matches, result.total_conversations)
    lines = ["'%s' — %s" % (result.query, summary), ""]
    for rank, conversation in enumerate(result.conversations, start=1):
        lines.append("%2d. [%d] %s" % (rank, conversation.match_count, conversation.title))
        lines.append("      when    : %s" % format_when(conversation.last_active_at))
        lines.append("      project : %s" % conversation.project_path)
        lines.append("      session : %s" % conversation.session_id)
        lines.append("      entries : %d matched" % len(conversation.matched_chat_entries))
        lines.append("")
    return Command_output(body="\n".join(lines).rstrip("\n"), summary=summary)


def command_in(digger: Chat_digger, arguments) -> Command_output:
    options = build_search_options(arguments)
    context = Context_window(before=arguments.context, after=arguments.context, unit=Context_unit.lines)
    result = digger.search_in_conversation(arguments.session_id, arguments.query, options, context)
    summary = "%d matches in %d entries" % (result.match_count, len(result.chat_entries))
    lines = ["'%s' in %s — %s" % (result.query, result.title, result.session_id), summary, ""]
    for entry in result.chat_entries:
        lines.append("- %s %s  %s" % (entry.chat_entry_type, format_when(entry.timestamp), entry.uuid))
        for snippet in entry.snippets:
            body = "%s>>>%s<<<%s" % (snippet.before, snippet.match, snippet.after)
            lines.append("    [block %d/%s] %s" % (snippet.block_index, snippet.block_type, body.replace("\n", "\n      ")))
        lines.append("")
    return Command_output(body="\n".join(lines).rstrip("\n"), summary=summary)


def command_show(digger: Chat_digger, arguments) -> Command_output:
    entry = digger.get_chat_entry(
        arguments.uuid, arguments.session_id, block_index=arguments.block, include_thinking=arguments.thinking
    )
    lines = [
        "%s %s  %s" % (entry.chat_entry_type, format_when(entry.timestamp), entry.uuid),
        "project: %s" % entry.project_path,
        "",
    ]
    for block in entry.blocks:
        header = "[block %d/%s]" % (block.block_index, block.block_type)
        if block.block_type == "tool_use":
            lines.append("%s %s %s" % (header, block.tool_name, block.tool_input))
        elif block.block_type == "tool_result":
            lines.append(header)
            lines.append(block.tool_result_text or "")
        else:
            lines.append(header)
            lines.append(block.text or "")
        lines.append("")
    return Command_output(body="\n".join(lines).rstrip("\n"), summary="%d blocks" % len(entry.blocks))


def command_origin(digger: Chat_digger, arguments) -> Command_output:
    tools = arguments.tool.split(",") if arguments.tool else None
    origins = digger.find_file_origin(arguments.filename, mode=arguments.mode, tools=tools)
    summary = "%d file events" % len(origins)
    lines = ["'%s' — %s" % (arguments.filename, summary), ""]
    for origin in origins:
        version = "" if origin.version is None else "  v%d%s" % (origin.version, " [backup]" if origin.has_backup else "")
        lines.append("%s  %-7s via %-12s %s" % (format_when(origin.timestamp), origin.operation, origin.tool, origin.file_path))
        lines.append("      %s  —  %s%s" % (origin.title, origin.session_id, version))
        lines.append("")
    return Command_output(body="\n".join(lines).rstrip("\n"), summary=summary)


def command_family(digger: Chat_digger, arguments) -> Command_output:
    sessions = digger.get_fork_family(arguments.session_id)
    lines = ["fork family of %d conversation(s):" % len(sessions), ""]
    for session_id in sessions:
        lines.append("  %s" % session_id)
    return Command_output(body="\n".join(lines), summary="%d sessions" % len(sessions))


def command_families(digger: Chat_digger, arguments) -> Command_output:
    families = digger.list_families(workspace=arguments.workspace, project=arguments.project, limit=arguments.limit)
    scope = arguments.workspace or arguments.project
    summary = "%d fork %s" % (len(families), "family" if len(families) == 1 else "families")
    lines = ["%s%s" % (summary, " in %s" % scope if scope else ""), ""]
    for family in families:
        if family.session_count == 1:
            shape = "single conversation"
        else:
            shape = "%d sessions, %d forks" % (family.session_count, family.session_count - 1)
        lines.append("%s  %s  %s" % (format_when(family.last_active_at), family.root_session_id, family.title))
        lines.append("      %s · %d leaves · %d entries" % (shape, family.leaf_count, family.node_count))
        lines.append("      project : %s" % family.project_path)
        lines.append("")
    return Command_output(body="\n".join(lines).rstrip("\n"), summary=summary)


def command_tree(digger: Chat_digger, arguments) -> Command_output:
    diagram = digger.render_conversation_tree(
        arguments.session_id,
        diagram_format=Diagram_format(arguments.format),
        detail=Tree_detail(arguments.detail),
        max_nodes=arguments.max_nodes,
        single=arguments.single,
    )
    summary = "%d nodes, %d edges, %d entries folded" % (diagram.node_count, diagram.edge_count, diagram.collapsed_count)
    return Command_output(body=diagram.source.rstrip("\n"), summary=summary, notes=list(diagram.notes))


def command_list(digger: Chat_digger, arguments) -> Command_output:
    conversations = digger.list_conversations()
    shown = conversations[: arguments.limit]
    lines = [
        "%s  %s  %s" % (format_when(conversation.last_active_at), conversation.session_id, conversation.title)
        for conversation in shown
    ]
    return Command_output(body="\n".join(lines), summary="%d conversations" % len(shown))


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

    for subparser in subparsers.choices.values():
        add_output_option(subparser)

    return parser


def main() -> None:
    force_utf8_output()
    arguments = build_parser().parse_args()
    digger = Chat_digger(index_path=arguments.index_path, corpus_root=arguments.corpus_root)
    try:
        output = arguments.handler(digger, arguments)
        emit(output, arguments.out)
    except (ValueError, FileNotFoundError) as error:
        print("error: %s" % error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

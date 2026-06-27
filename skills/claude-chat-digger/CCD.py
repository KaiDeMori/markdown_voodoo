"""CCD command line — index and search past Claude Code conversations.

Usage:
    python CCD.py index
    python CCD.py status
    python CCD.py search "<query>" [options]
    python CCD.py in <session_id> "<query>" [--context N] [options]
    python CCD.py show <session_id> <uuid> [--block N] [--thinking]
    python CCD.py list [--limit N]

A command's required arguments are positional: they come first, in the order shown,
immediately after the command and before any options. A value may begin with a dash
(searching for "-X", say) and is taken literally, so no "--" escape is needed.

Two output axes apply to every command: --out/-o FILE writes the result to a UTF-8
file and prints a one-line receipt; --format text|json chooses human-readable text
(the default) or the full structured result as JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Callable, Optional

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
    """A command's rendered result, decoupled from where and how it is sent.

    `body` is the human-readable text and `data` the structured result; `--format`
    picks which becomes the payload. `summary` is a one-line detail for the file
    receipt, and `notes` are deterministic reductions reported alongside the result —
    both diagnostics, never folded into the payload so a saved file stays clean.
    """

    body: str
    summary: str = ""
    notes: list[str] = field(default_factory=list)
    data: object = None


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


def _json_default(value):
    """Serialise the result dataclasses JSON cannot handle natively."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise TypeError("not JSON serialisable: %r" % type(value))


def render_json(data) -> str:
    """The single point structured results become JSON, dataclasses and enums included."""
    return json.dumps(data, default=_json_default, ensure_ascii=False, indent=2)


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


def add_output_options(parser: argparse.ArgumentParser) -> None:
    """Give a subcommand the two universal output axes: destination and encoding.

    `--out` writes through Python rather than shell redirection, which guarantees a
    UTF-8 file with newline line endings on any shell and keeps the receipt out of the
    saved payload. `--format` selects text or the full structured result as JSON.
    """
    parser.add_argument(
        "--out",
        "-o",
        default=None,
        help="write the full result to this file (UTF-8); print a one-line receipt instead",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output as human-readable text (default) or the full structured result as JSON",
    )


def emit(output: Command_output, out_path, output_format: str) -> None:
    """Send a command's result to its destination in the chosen encoding.

    The payload (text or JSON) is the only thing on the chosen sink; the receipt and
    any notes are diagnostics on stderr, so a piped or redirected payload stays pure
    even as JSON, where a trailing note line would be invalid.
    """
    if output_format == "json" and output.data is not None:
        payload = render_json(output.data)
    else:
        payload = output.body
    if out_path:
        text = payload if payload.endswith("\n") else payload + "\n"
        with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        detail = " (%s)" % output.summary if output.summary else ""
        print("wrote output%s to %s" % (detail, out_path), file=sys.stderr)
    else:
        print(payload)
    for note in output.notes:
        print("note: %s" % note, file=sys.stderr)


def command_index(digger: Chat_digger, arguments) -> Command_output:
    print("Indexing %s ..." % digger.corpus_root)
    stats = digger.build_index()
    summary = "%d conversations, %d blocks" % (stats.conversation_count, stats.chat_entry_count)
    body = "Indexed %d conversations, %d searchable blocks." % (stats.conversation_count, stats.chat_entry_count)
    data = {"conversations": stats.conversation_count, "blocks": stats.chat_entry_count}
    return Command_output(body=body, summary=summary, data=data)


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
    data = {
        "index_path": str(digger.index_path),
        "conversations": stats.conversation_count,
        "blocks": stats.chat_entry_count,
        "stale": stats.is_stale,
        "version_db": version,
        "version_code": CCD_INDEX_VERSION,
    }
    return Command_output(body="\n".join(lines), data=data)


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
    return Command_output(body="\n".join(lines).rstrip("\n"), summary=summary, data=result)


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
    return Command_output(body="\n".join(lines).rstrip("\n"), summary=summary, data=result)


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
    return Command_output(body="\n".join(lines).rstrip("\n"), summary="%d blocks" % len(entry.blocks), data=entry)


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
    data = {"filename": arguments.filename, "mode": arguments.mode, "count": len(origins), "events": origins}
    return Command_output(body="\n".join(lines).rstrip("\n"), summary=summary, data=data)


def command_family(digger: Chat_digger, arguments) -> Command_output:
    sessions = digger.get_fork_family(arguments.session_id)
    lines = ["fork family of %d conversation(s):" % len(sessions), ""]
    for session_id in sessions:
        lines.append("  %s" % session_id)
    data = {"session_id": arguments.session_id, "count": len(sessions), "sessions": sessions}
    return Command_output(body="\n".join(lines), summary="%d sessions" % len(sessions), data=data)


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
    data = {"scope": scope, "count": len(families), "families": families}
    return Command_output(body="\n".join(lines).rstrip("\n"), summary=summary, data=data)


def command_tree(digger: Chat_digger, arguments) -> Command_output:
    graph = digger.conversation_graph(
        arguments.session_id,
        detail=Tree_detail(arguments.detail),
        max_nodes=arguments.max_nodes,
        single=arguments.single,
    )
    diagram = digger.render_graph(graph, Diagram_format(arguments.diagram_format))
    summary = "%d nodes, %d edges, %d entries folded" % (diagram.node_count, diagram.edge_count, diagram.collapsed_count)
    return Command_output(body=diagram.source.rstrip("\n"), summary=summary, notes=list(diagram.notes), data=graph)


def command_list(digger: Chat_digger, arguments) -> Command_output:
    conversations = digger.list_conversations()
    shown = conversations[: arguments.limit]
    lines = [
        "%s  %s  %s" % (format_when(conversation.last_active_at), conversation.session_id, conversation.title)
        for conversation in shown
    ]
    data = {"count": len(shown), "conversations": shown}
    return Command_output(body="\n".join(lines), summary="%d conversations" % len(shown), data=data)


def add_in_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--context", type=int, default=2)
    add_search_filters(parser)


def add_show_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--block", type=int, default=None)
    parser.add_argument("--thinking", action="store_true")


def add_origin_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mode", choices=["all", "created", "edited", "read"], default="all")
    parser.add_argument("--tool", default=None, help="comma-separated tools, e.g. Write,Edit")


def add_tree_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--diagram-format",
        choices=[fmt.value for fmt in Diagram_format],
        default="mermaid",
        help="diagram drawing language when --format text (ignored for --format json)",
    )
    parser.add_argument("--detail", choices=[detail.value for detail in Tree_detail], default="forks_only")
    parser.add_argument("--max-nodes", type=int, default=200)
    parser.add_argument("--single", action="store_true", help="restrict to this one session, not the whole family")


def add_families_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", default=None, help="restrict to a workspace folder and everything under it")
    parser.add_argument("--project", default=None, help="restrict to one exact project path")
    parser.add_argument("--limit", type=int, default=40)


def add_list_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=40)


@dataclass
class Command_spec:
    """The fixed signature of one subcommand: its required positionals in the order they must be
    given, an optional hook that registers the command's flags, the handler that runs it, and a
    one-line summary. The required positionals are peeled off the token stream literally before any
    option parsing, so a value that starts with a dash is taken as-is rather than read as a flag."""

    positionals: list[str]
    add_options: Optional[Callable[[argparse.ArgumentParser], None]]
    handler: Callable[..., Command_output]
    summary: str


command_specs = {
    "index": Command_spec([], None, command_index, "rebuild the search index from scratch"),
    "status": Command_spec([], None, command_status, "show index status"),
    "search": Command_spec(["query"], add_search_filters, command_search, "search all conversations"),
    "in": Command_spec(["session_id", "query"], add_in_options, command_in, "search within one conversation"),
    "show": Command_spec(["session_id", "uuid"], add_show_options, command_show, "show one chat entry in full"),
    "origin": Command_spec(["filename"], add_origin_options, command_origin, "find where a file was created/edited/read"),
    "tree": Command_spec(["session_id"], add_tree_options, command_tree, "render a conversation's fork family as a diagram"),
    "family": Command_spec(["session_id"], None, command_family, "list the sessions in a conversation's fork family"),
    "families": Command_spec([], add_families_options, command_families, "overview of all fork families in a workspace"),
    "list": Command_spec([], add_list_options, command_list, "list indexed conversations"),
}


def command_signature(command: str, spec: Command_spec) -> str:
    """The one true call form of a command, positionals first in their mandatory order."""
    parts = ["CCD", command] + ["<%s>" % name for name in spec.positionals] + ["[options]"]
    return " ".join(parts)


def build_top_parser() -> argparse.ArgumentParser:
    """The pre-parser: it reads the global options and the command name, then sweeps everything that
    follows into `rest` verbatim. Holding the command's own arguments back from option parsing here is
    what lets a dash-leading positional such as a "-X" search term survive intact."""
    epilog_lines = ["commands (arguments must appear in the order shown):"]
    name_width = max(len(name) for name in command_specs)
    for name, spec in command_specs.items():
        positionals = " ".join("<%s>" % positional for positional in spec.positionals)
        epilog_lines.append("  %-*s  %s" % (name_width, name, positionals))
    epilog_lines.append("")
    epilog_lines.append("run  CCD <command> <args> --help  for a command's options")

    parser = argparse.ArgumentParser(
        prog="CCD",
        description="Search past Claude Code conversations.",
        epilog="\n".join(epilog_lines),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--index-path", default=None)
    parser.add_argument("--corpus-root", default=None)
    parser.add_argument("command", metavar="command", choices=list(command_specs), help="one of: %s" % ", ".join(command_specs))
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="the command's arguments, in the fixed order shown below")
    return parser


def build_option_parser(command: str, spec: Command_spec) -> argparse.ArgumentParser:
    """A command's option parser. It carries no positionals — those are peeled off beforehand — so it
    only ever sees the trailing flags. Its usage line still advertises the full fixed signature."""
    parser = argparse.ArgumentParser(prog="CCD %s" % command, usage=command_signature(command, spec), description=spec.summary)
    if spec.add_options is not None:
        spec.add_options(parser)
    add_output_options(parser)
    return parser


def parse_command(argv: list[str]) -> argparse.Namespace:
    """Resolve a full argument list into one namespace ready for its handler.

    The required positionals are taken from the front of the command's arguments by position alone and
    set on the namespace untouched; only the tokens after them are parsed for options. A required
    positional that begins with a dash is therefore kept as a literal value, never mistaken for a flag.
    """
    arguments = build_top_parser().parse_args(argv)
    spec = command_specs[arguments.command]
    option_parser = build_option_parser(arguments.command, spec)

    required = spec.positionals
    given = arguments.rest
    if len(given) < len(required):
        option_parser.error("missing required argument: %s" % ", ".join(required[len(given):]))
    for name, value in zip(required, given):
        setattr(arguments, name, value)
    option_parser.parse_args(given[len(required):], namespace=arguments)
    arguments.handler = spec.handler
    return arguments


def main() -> None:
    force_utf8_output()
    arguments = parse_command(sys.argv[1:])
    digger = Chat_digger(index_path=arguments.index_path, corpus_root=arguments.corpus_root)
    try:
        output = arguments.handler(digger, arguments)
        emit(output, arguments.out, arguments.format)
    except (ValueError, FileNotFoundError) as error:
        print("error: %s" % error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

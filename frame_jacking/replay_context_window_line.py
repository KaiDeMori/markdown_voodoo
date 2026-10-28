"""Replays context_window_line.py at every turn of a transcript: what the hook would have said there.

Usage: python replay_context_window_line.py <session_id> [<session_id> ...]
Prints every turn where the hook would have spoken; on every other turn it stays silent.
"""
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

script_path = Path(__file__).with_name("context_window_line.py")
specification = importlib.util.spec_from_file_location("context_window_line", script_path)
context_window_line = importlib.util.module_from_spec(specification)
specification.loader.exec_module(context_window_line)


def local_time(timestamp_UTC):
    return datetime.fromisoformat(timestamp_UTC.replace("Z", "+00:00")).astimezone().isoformat(timespec="minutes")


for session_id in sys.argv[1:]:
    log_paths = sorted((Path.home() / ".claude" / "projects").glob(f"*/{session_id}.jsonl"))
    if not log_paths:
        print(f"=== {session_id}: no log found")
        continue
    events = context_window_line.parse_events(log_paths[0].read_text(encoding="utf-8", errors="replace").splitlines())
    turn_positions = [index for index, event in enumerate(events) if event[0] == "turn"]
    reports = [(events[position][1], context_window_line.window_line(events[:position])) for position in turn_positions]
    spoken = [(timestamp, line) for timestamp, line in reports if line]
    print(f"=== {session_id}: {len(reports)} turns, {len(spoken)} with news")
    for timestamp, line in spoken:
        print(f"   {local_time(timestamp)}  {line}")

"""Tells a window its news in a UserPromptSubmit hook, and stays silent on every other turn.

The news is one of three: the window crossed 50% or 80% of its size, or it lost tokens unseen, as after a resume or a fork.
The fill level is the input of the window's last request, as the server reported it in the transcript;
the /context gauge shows the same number.
A loss is what a request should have carried over from the one before it, its input and its output, and didn't.
The line is one turn behind: the request about to be sent is not in the transcript yet.
Any failure prints nothing, so the prompt always goes through.
"""
import json
import sys
from pathlib import Path

window_size_by_model = {
    "claude-opus-5-5": 1_000_000,
}
default_window_size = 1_000_000
drop_threshold = 2_000
tail_bytes = 4_000_000
# A window that crosses one of these levels hears it once, the highest level first; Wally used to announce them by hand.
milestones = (
    (80, "the Tannhäuser Gate in sight ✨; burn through with glee 🚀"),
    (50, "High-Noon 😎; the best is yet to come 🤗"),
)
drop_text = "the window got lighter 🪶; when memory and file disagree, the file wins"


def short(tokens):
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:g}M"
    return f"{int(tokens / 1000 + 0.5)}k"


def read_tail_lines(transcript_path, size):
    with open(transcript_path, "rb") as file:
        file.seek(0, 2)
        start = max(0, file.tell() - size)
        file.seek(start)
        lines = file.read().decode("utf-8", errors="replace").splitlines()
    if start > 0:
        lines = lines[1:]
    return lines, start == 0


def parse_events(lines):
    """The main chain as events: ("turn", timestamp), ("compact", timestamp), and one request per API call."""
    events = []
    requests = {}
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict) or record.get("isSidechain"):
            continue
        record_type = record.get("type")
        timestamp = record.get("timestamp")
        if record_type == "user":
            if record.get("isCompactSummary"):
                events.append(("compact", timestamp))
            elif not record.get("isMeta") and not record.get("toolUseResult"):
                events.append(("turn", timestamp))
        elif record_type == "system" and record.get("subtype") == "compact_boundary":
            events.append(("compact", timestamp))
        elif record_type == "assistant":
            message = record.get("message") or {}
            usage = message.get("usage") or {}
            key = record.get("requestId") or message.get("id")
            input_total = sum(usage.get(name) or 0 for name in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
            if not key or not input_total:
                continue
            output_tokens = usage.get("output_tokens") or 0
            if key in requests:
                requests[key][2] = max(requests[key][2], output_tokens)
            else:
                requests[key] = ["request", input_total, output_tokens, message.get("model"), timestamp]
                events.append(requests[key])
    return events


def has_enough(events):
    request_indexes = [index for index, event in enumerate(events) if event[0] == "request"]
    if not request_indexes:
        return False
    turn_indexes = [index for index in range(request_indexes[-1]) if events[index][0] == "turn"]
    return bool(turn_indexes) and request_indexes[0] < turn_indexes[-1]


def window_line(events):
    request_indexes = [index for index, event in enumerate(events) if event[0] == "request"]
    if not request_indexes:
        return None
    last_index = request_indexes[-1]
    turn_indexes = [index for index in range(last_index) if events[index][0] == "turn"]
    start_index = turn_indexes[-1] if turn_indexes else last_index
    earlier = [index for index in request_indexes if index < start_index]
    if earlier:
        start_index = earlier[-1]
    missing = 0
    compacted = False
    previous = None
    for event in events[start_index:last_index + 1]:
        if event[0] == "compact":
            compacted = True
        elif event[0] == "request":
            if previous is not None:
                missing += max(0, previous[1] + previous[2] - event[1])
            previous = event
    last = events[last_index]
    window_size = window_size_by_model.get(last[3], default_window_size)
    # A loss is news first: what the window lost matters more than how full it is.
    if missing > drop_threshold:
        line = f"↓ {short(missing)} cw since last turn{', compacted' if compacted else ''}; {drop_text}"
    elif earlier:
        # A level is crossed between the last request before the last turn and the last request of it.
        before = events[earlier[-1]]
        crossed = [text for level, text in milestones if before[1] * 100 < level * window_size <= last[1] * 100]
        if not crossed:
            return None
        line = f"{int(last[1] * 100 / window_size + 0.5)}% cw used; {crossed[0]}"
    else:
        return None
    return f"<context_window>{line}</context_window>"


def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    transcript_path = payload.get("transcript_path")
    if not transcript_path or not Path(transcript_path).is_file():
        return
    size = tail_bytes
    while True:
        lines, whole_file = read_tail_lines(transcript_path, size)
        events = parse_events(lines)
        if whole_file or has_enough(events):
            break
        size *= 4
    line = window_line(events)
    if line:
        sys.stdout.buffer.write((line + "\n").encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

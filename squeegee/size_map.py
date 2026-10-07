"""Draws the size map of a Claude Code transcript, and optionally its growth map.

The size map is an SVG mirror chart with one column per turn.
Bytes in the file go up from the middle line, estimated tokens in the context go down.
Each half shows shares of its own total, so both halves share one scale.

The growth map uses the API's own usage numbers.
Its top panel shows the measured context at the end of each turn.
Its bottom panel shows what each turn added, split into text visible in the transcript and the rest.

A summary table goes to stdout.
The script only reads the transcript and never changes it.

Usage: python size_map.py <transcript.jsonl> --output-file <map.svg> [--growth-file <growth.svg>]
"""

import argparse
import base64
import binascii
import json
import math
import struct
import sys
from pathlib import Path
from xml.sax.saxutils import escape

characters_per_token = 4
image_patch_size = 28
image_max_long_edge = 2576
image_max_tokens = 4784

# User text that starts with one of these tags is machinery, not words the user typed.
injected_prefixes = (
    "<ide_opened_file>",
    "<ide_selection>",
    "<command-name>",
    "<command-message>",
    "<command-args>",
    "<system-reminder>",
    "<local-command-stdout>",
    "<local-command-stderr>",
    "<user-prompt-submit-hook>",
    "<session-start-hook>",
)

# Size map categories in stack order from the middle line outwards, in the reference palette's slot order.
categories = [
    ("source", "file reads", "#2a78d6"),
    ("image", "images", "#eb6834"),
    ("tool_output", "other tool output", "#1baf7a"),
    ("tool_call", "tool calls", "#eda100"),
    ("thinking", "thinking (summary text)", "#e87ba4"),
    ("assistant_text", "assistant words", "#008300"),
    ("user_text", "user words", "#4a3aa7"),
    ("other", "other", "#e34948"),
]
category_keys = [key for key, _, _ in categories]

# Parts that fold into "other" on the chart; the table lists them one by one.
other_parts = {
    "injected": "injected context",
    "envelope": "envelope and metadata",
    "mirror": "mirror fields",
    "bookkeeping": "bookkeeping records",
    "subagent": "subagent records",
}
part_names = category_keys[:-1] + list(other_parts)

# The growth map measures tokens only, so it uses one hue: light for visible, dark for the rest.
visible_color = "#86b6ef"
invisible_color = "#1c5cab"
context_line_color = "#2a78d6"
context_area_color = "#cde2fb"

surface_color = "#fcfcfb"
primary_ink = "#0b0b0b"
secondary_ink = "#52514e"
muted_ink = "#898781"
gridline_color = "#e1e0d9"
baseline_color = "#c3c2b7"
font_family = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def encoded_text(value):
    """Serializes a value the way JavaScript's JSON.stringify does."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def encoded_size(value):
    return len(encoded_text(value).encode("utf-8"))


def text_tokens(text):
    return math.ceil(len(text) / characters_per_token)


def collect_strings(value):
    """Joins every string value inside a nested JSON value."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "".join(collect_strings(item) for item in value.values())
    if isinstance(value, list):
        return "".join(collect_strings(item) for item in value)
    return ""


def context_tokens(usage):
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )


def image_size(raw):
    """Reads width and height from PNG, GIF, WebP or JPEG bytes; None when the format is unknown."""
    if raw[:8] == b"\x89PNG\r\n\x1a\n" and len(raw) >= 24:
        return struct.unpack(">II", raw[16:24])
    if raw[:6] in (b"GIF87a", b"GIF89a") and len(raw) >= 10:
        return struct.unpack("<HH", raw[6:10])
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return webp_size(raw)
    if raw[:2] == b"\xff\xd8":
        return jpeg_size(raw)
    return None


def webp_size(raw):
    chunk = raw[12:16]
    if chunk == b"VP8X" and len(raw) >= 30:
        return 1 + int.from_bytes(raw[24:27], "little"), 1 + int.from_bytes(raw[27:30], "little")
    if chunk == b"VP8 " and len(raw) >= 30:
        width, height = struct.unpack("<HH", raw[26:30])
        return width & 0x3FFF, height & 0x3FFF
    if chunk == b"VP8L" and len(raw) >= 25:
        bits = int.from_bytes(raw[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def jpeg_size(raw):
    start_of_frame_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    position = 2
    while position + 9 <= len(raw):
        if raw[position] != 0xFF:
            position += 1
            continue
        marker = raw[position + 1]
        if marker == 0xFF:
            position += 1
            continue
        if marker == 0x01 or 0xD0 <= marker <= 0xD9:
            position += 2
            continue
        if marker in start_of_frame_markers:
            height, width = struct.unpack(">HH", raw[position + 5:position + 9])
            return width, height
        segment_length = struct.unpack(">H", raw[position + 2:position + 4])[0]
        position += 2 + segment_length
    return None


def image_size_from_base64(data):
    """Decodes as little of the base64 data as needed to read the image size."""
    for length in (65536, len(data)):
        try:
            raw = base64.b64decode(data[:length - length % 4])
        except (binascii.Error, ValueError):
            return None
        size = image_size(raw)
        if size or length >= len(data):
            return size
    return None


def image_tokens(width, height):
    """Estimates visual tokens with the API formula, after the high-resolution downscale."""
    if width <= 0 or height <= 0:
        return 0
    scale = min(1.0, image_max_long_edge / max(width, height))
    width, height = width * scale, height * scale
    tokens = math.ceil(width / image_patch_size) * math.ceil(height / image_patch_size)
    if tokens > image_max_tokens:
        shrink = math.sqrt(image_max_tokens / tokens)
        tokens = math.ceil(width * shrink / image_patch_size) * math.ceil(height * shrink / image_patch_size)
    return min(tokens, image_max_tokens)


def image_block_tokens(block, statistics):
    source = block.get("source") or {}
    data = source.get("data")
    size = image_size_from_base64(data) if source.get("type") == "base64" and isinstance(data, str) else None
    if size is None:
        statistics["images_without_size"] += 1
        return 0
    return image_tokens(*size)


class Size_map:
    """Tallies one transcript, turn by turn, in bytes and estimated tokens, and records every request."""

    def __init__(self):
        self.turns = [self.new_turn()]
        self.tool_names = {}
        self.seen_assistant_blocks = set()
        self.seen_requests = set()
        # One entry per API request: turn index, estimated tokens before it, thinking bytes before it, measured context.
        self.requests = []
        self.cumulative_tokens = 0
        self.cumulative_thinking_bytes = 0
        self.last_usage = None
        self.statistics = {
            "file_bytes": 0,
            "records": 0,
            "unparsable_records": 0,
            "images": 0,
            "images_from_reads": 0,
            "images_without_size": 0,
        }

    @staticmethod
    def new_turn():
        return {"bytes": dict.fromkeys(part_names, 0), "tokens": dict.fromkeys(part_names, 0), "records": 0}

    def read(self, transcript_path):
        with open(transcript_path, "rb") as transcript:
            for raw_line in transcript:
                self.statistics["file_bytes"] += len(raw_line)
                line = raw_line.rstrip(b"\r\n")
                if not line.strip():
                    continue
                self.statistics["records"] += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    self.statistics["unparsable_records"] += 1
                    self.add(self.turns[-1], [("bookkeeping", len(line), 0)])
                    continue
                self.add_record(record, len(line))

    def add(self, turn, parts):
        for part, part_bytes, part_tokens in parts:
            turn["bytes"][part] += part_bytes
            turn["tokens"][part] += part_tokens
            self.cumulative_tokens += part_tokens
        turn["records"] += 1

    def add_record(self, record, line_bytes):
        record_type = record.get("type")
        if record.get("isSidechain"):
            self.add(self.turns[-1], [("subagent", line_bytes, 0)])
            return
        if record_type == "attachment":
            tokens = text_tokens(collect_strings(record.get("attachment")))
            self.add(self.turns[-1], [("injected", line_bytes, tokens)])
            return
        if record_type not in ("user", "assistant"):
            self.add(self.turns[-1], [("bookkeeping", line_bytes, 0)])
            return
        message = record.get("message") or {}
        usage = message.get("usage") if record_type == "assistant" else None
        if usage:
            self.last_usage = usage
            request_key = message.get("id") or record.get("uuid")
            # The request happened before the first record of its answer, so it sees everything tallied so far.
            if request_key not in self.seen_requests:
                self.seen_requests.add(request_key)
                self.requests.append(
                    (len(self.turns) - 1, self.cumulative_tokens, self.cumulative_thinking_bytes, context_tokens(usage))
                )
        content = message.get("content")
        blocks = content if isinstance(content, list) else []
        if isinstance(content, str):
            parts = [(self.text_part(record_type, record, content), encoded_size(content), text_tokens(content))]
        else:
            parts = [part for block in blocks for part in self.classify_block(block, record_type, record, message)]
        if record_type == "user" and self.starts_turn(parts, blocks):
            self.turns.append(self.new_turn())
        mirror = record.get("toolUseResult")
        mirror_bytes = encoded_size(mirror) if mirror is not None else 0
        attributed = sum(part_bytes for _, part_bytes, _ in parts) + mirror_bytes
        parts.append(("mirror", mirror_bytes, 0))
        parts.append(("envelope", max(0, line_bytes - attributed), 0))
        self.add(self.turns[-1], parts)

    @staticmethod
    def text_part(record_type, record, text):
        if record_type == "assistant":
            return "assistant_text"
        if record.get("isMeta") or text.lstrip().startswith(injected_prefixes):
            return "injected"
        return "user_text"

    @staticmethod
    def starts_turn(parts, blocks):
        has_user_words = any(part == "user_text" for part, _, _ in parts)
        has_tool_result = any(isinstance(block, dict) and block.get("type") == "tool_result" for block in blocks)
        return has_user_words and not has_tool_result

    def classify_block(self, block, record_type, record, message):
        """Returns (part, bytes, tokens) tuples for one content block."""
        if not isinstance(block, dict):
            return [("envelope", encoded_size(block), 0)]
        encoded = encoded_text(block)
        block_bytes = len(encoded.encode("utf-8"))
        block_type = block.get("type")
        # Claude Code writes an assistant message more than once while streaming; tokens count once.
        counted = True
        if record_type == "assistant":
            fingerprint = (message.get("id"), hash(encoded))
            counted = fingerprint not in self.seen_assistant_blocks
            self.seen_assistant_blocks.add(fingerprint)
        if block_type == "text":
            text = block.get("text") or ""
            return [(self.text_part(record_type, record, text), block_bytes, text_tokens(text) if counted else 0)]
        if block_type in ("thinking", "redacted_thinking"):
            if counted:
                self.cumulative_thinking_bytes += block_bytes
            return [("thinking", block_bytes, text_tokens(block.get("thinking") or "") if counted else 0)]
        if block_type == "tool_use":
            self.tool_names[block.get("id")] = block.get("name")
            tokens = text_tokens((block.get("name") or "") + encoded_text(block.get("input"))) if counted else 0
            return [("tool_call", block_bytes, tokens)]
        if block_type == "tool_result":
            return self.classify_tool_result(block, block_bytes)
        if block_type == "image":
            self.statistics["images"] += 1
            return [("image", block_bytes, image_block_tokens(block, self.statistics))]
        if block_type == "document":
            source = block.get("source") or {}
            tokens = text_tokens(source.get("data") or "") if source.get("type") == "text" else 0
            return [(self.text_part(record_type, record, ""), block_bytes, tokens)]
        return [("envelope", block_bytes, 0)]

    def classify_tool_result(self, block, block_bytes):
        is_read = self.tool_names.get(block.get("tool_use_id")) == "Read"
        text_part = "source" if is_read else "tool_output"
        inner = block.get("content")
        parts = []
        if isinstance(inner, str):
            parts.append((text_part, encoded_size(inner), text_tokens(inner)))
        elif isinstance(inner, list):
            for inner_block in inner:
                inner_bytes = encoded_size(inner_block)
                if isinstance(inner_block, dict) and inner_block.get("type") == "image":
                    self.statistics["images"] += 1
                    self.statistics["images_from_reads"] += int(is_read)
                    parts.append(("image", inner_bytes, image_block_tokens(inner_block, self.statistics)))
                elif isinstance(inner_block, dict) and inner_block.get("type") == "text":
                    parts.append((text_part, inner_bytes, text_tokens(inner_block.get("text") or "")))
                else:
                    parts.append((text_part, inner_bytes, text_tokens(collect_strings(inner_block))))
        attributed = sum(part_bytes for _, part_bytes, _ in parts)
        parts.append(("envelope", max(0, block_bytes - attributed), 0))
        return parts

    def category_totals(self, turn, measure):
        totals = dict.fromkeys(category_keys, 0)
        for part in part_names:
            totals[part if part in category_keys else "other"] += turn[measure][part]
        return totals

    def part_totals(self, measure):
        totals = dict.fromkeys(part_names, 0)
        for turn in self.turns:
            for part in part_names:
                totals[part] += turn[measure][part]
        return totals


def growth_series(size_map):
    """Splits the measured context into a base and per-turn growth.

    The base is the context of the first request.
    Each turn is measured at its last request, so a turn's final answer counts toward the next turn.
    Growth splits into the part visible as text, which is estimated, and the rest.
    """
    if not size_map.requests:
        return None, []
    _, base_estimate, base_thinking, base_measured = size_map.requests[0]
    last_request_by_turn = {request[0]: request for request in size_map.requests}
    series = []
    previous_estimate, previous_thinking, previous_measured = base_estimate, base_thinking, base_measured
    for index in range(len(size_map.turns)):
        request = last_request_by_turn.get(index)
        if request:
            _, estimate, thinking, measured = request
        else:
            estimate, thinking, measured = previous_estimate, previous_thinking, previous_measured
        growth = measured - previous_measured
        visible = estimate - previous_estimate
        series.append({
            "turn": index,
            "measured": measured,
            "growth": growth,
            "visible": visible,
            "invisible": growth - visible,
            "thinking_bytes": thinking - previous_thinking,
            "has_request": request is not None,
        })
        previous_estimate, previous_thinking, previous_measured = estimate, thinking, measured
    return {"measured": base_measured, "visible": base_estimate}, series


def pearson(first_values, second_values):
    count = len(first_values)
    if count < 2:
        return None
    first_mean = sum(first_values) / count
    second_mean = sum(second_values) / count
    covariance = sum((a - first_mean) * (b - second_mean) for a, b in zip(first_values, second_values))
    first_spread = math.sqrt(sum((a - first_mean) ** 2 for a in first_values))
    second_spread = math.sqrt(sum((b - second_mean) ** 2 for b in second_values))
    if first_spread == 0 or second_spread == 0:
        return None
    return covariance / (first_spread * second_spread)


def thinking_relation(series):
    """Returns Pearson r and tokens per KB between thinking bytes and invisible growth, per turn with a request."""
    measured = [entry for entry in series if entry["has_request"]]
    thinking = [entry["thinking_bytes"] for entry in measured]
    invisible = [entry["invisible"] for entry in measured]
    correlation = pearson(thinking, invisible)
    squares = sum(value * value for value in thinking)
    if correlation is None or not squares:
        return None, None
    return correlation, 1000 * sum(x * y for x, y in zip(thinking, invisible)) / squares


def svg_text(x, y, content, color, size, anchor="start", weight="normal", numeric=False):
    style = ' style="font-variant-numeric: tabular-nums"' if numeric else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}"{style}>{escape(content)}</text>'
    )


def svg_line(x1, x2, y, color):
    return f'<line x1="{x1:.1f}" x2="{x2:.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="{color}" stroke-width="1"/>'


def svg_document(width, height, elements):
    body = "\n".join(elements)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{font_family}">\n{body}\n</svg>\n'
    )


def nice_scale(max_percent):
    """Returns the gridline step and the top of the scale, both in percent."""
    for step in (0.5, 1, 2, 2.5, 5, 10, 20, 25, 50):
        if max_percent / step <= 5:
            return step, max(step, math.ceil(max_percent / step) * step)
    return 50, 100


def nice_token_scale(max_value):
    """Returns the gridline step and the top of the scale, in tokens."""
    if max_value <= 0:
        return 1, 1
    magnitude = 10 ** math.floor(math.log10(max_value))
    for factor in (0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10):
        step = factor * magnitude
        if max_value / step <= 5:
            return step, math.ceil(max_value / step) * step
    return 10 * magnitude, 10 * magnitude


def nice_label_step(turn_count):
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 500):
        if turn_count / step <= 20:
            return step
    return 1000


def token_label(value):
    return f"{value / 1000:g}k" if abs(value) >= 1000 else f"{value:g}"


def share_text(value, total):
    return f"{value / total:.1%}" if total else "-"


def turn_axis(elements, turn_count, margin_left, slot, plot_width, plot_bottom):
    label_step = nice_label_step(turn_count)
    for index in range(0, turn_count, label_step):
        x = margin_left + (index + 0.5) * slot
        elements.append(svg_text(x, plot_bottom + 18, str(index), muted_ink, 11, anchor="middle", numeric=True))
    elements.append(svg_text(margin_left + plot_width, plot_bottom + 36, "turn", muted_ink, 11, anchor="end"))


def draw_svg(size_map, transcript_name):
    turns = size_map.turns
    byte_totals = [size_map.category_totals(turn, "bytes") for turn in turns]
    token_totals = [size_map.category_totals(turn, "tokens") for turn in turns]
    all_bytes = sum(sum(totals.values()) for totals in byte_totals) or 1
    all_tokens = sum(sum(totals.values()) for totals in token_totals) or 1
    max_percent = 100 * max(
        max(sum(totals.values()) / all_bytes for totals in byte_totals),
        max(sum(totals.values()) / all_tokens for totals in token_totals),
    )
    step, top = nice_scale(max_percent)

    margin_left, margin_right, plot_width = 64, 24, 1600
    title_height, half_height = 92, 240
    middle_y = title_height + half_height
    plot_bottom = middle_y + half_height
    legend_top = plot_bottom + 64
    row_height = 22
    width = margin_left + plot_width + margin_right
    height = legend_top + (len(categories) + 2) * row_height + 24
    slot = plot_width / len(turns)
    gap = 2 if slot >= 5 else (1 if slot >= 3 else 0)
    bar_width = max(slot - gap, 0.5)

    def pixels(share):
        return share * 100 / top * half_height

    statistics = size_map.statistics
    measured = f"{context_tokens(size_map.last_usage):,} tokens" if size_map.last_usage else "not recorded"
    elements = [
        f'<rect width="{width}" height="{height}" fill="{surface_color}"/>',
        svg_text(margin_left, 32, f"Size map: {transcript_name}", primary_ink, 18, weight="600"),
        svg_text(
            margin_left, 54,
            f"{statistics['records']:,} records, {len(turns)} turns, {statistics['file_bytes']:,} bytes; "
            f"measured context at the last request: {measured}",
            secondary_ink, 12, numeric=True,
        ),
        svg_text(
            margin_left, 72,
            "Bytes go up, estimated tokens go down; each half shows shares of its own total. "
            f"Text counts {characters_per_token} characters per token; images follow the API formula.",
            muted_ink, 11,
        ),
    ]
    tick = step
    while tick <= top + 1e-9:
        for direction in (-1, 1):
            y = middle_y + direction * tick / top * half_height
            elements.append(svg_line(margin_left, margin_left + plot_width, y, gridline_color))
            elements.append(svg_text(margin_left - 8, y + 4, f"{tick:g}%", muted_ink, 11, anchor="end", numeric=True))
        tick += step

    for index, turn in enumerate(turns):
        x = margin_left + index * slot + gap / 2
        turn_bytes = sum(byte_totals[index].values())
        turn_tokens = sum(token_totals[index].values())
        title = (
            f"turn {index}: {turn_bytes:,} bytes ({share_text(turn_bytes, all_bytes)}), "
            f"about {turn_tokens:,} tokens ({share_text(turn_tokens, all_tokens)}), {turn['records']} records"
        )
        elements.append(f"<g><title>{escape(title)}</title>")
        for measure_totals, all_measure, direction in ((byte_totals, all_bytes, -1), (token_totals, all_tokens, 1)):
            cumulative = 0.0
            for key, _, color in categories:
                bar_height = pixels(measure_totals[index][key] / all_measure)
                if bar_height >= 0.05:
                    y = middle_y - cumulative - bar_height if direction < 0 else middle_y + cumulative
                    elements.append(
                        f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" fill="{color}"/>'
                    )
                cumulative += bar_height
        elements.append("</g>")

    elements.append(svg_line(margin_left, margin_left + plot_width, middle_y, baseline_color))
    elements.append(svg_text(margin_left + 8, title_height + 16, "bytes in the file, share per turn ↑", secondary_ink, 12))
    elements.append(svg_text(margin_left + 8, plot_bottom - 8, "estimated tokens in the context, share per turn ↓", secondary_ink, 12))
    turn_axis(elements, len(turns), margin_left, slot, plot_width, plot_bottom)

    columns = [margin_left + 20, margin_left + 330, margin_left + 410, margin_left + 540, margin_left + 620]
    elements.append(svg_text(columns[0], legend_top, "category", secondary_ink, 12, weight="600"))
    for column, header in zip(columns[1:], ("bytes", "share", "est. tokens", "share")):
        elements.append(svg_text(column, legend_top, header, secondary_ink, 12, anchor="end", weight="600"))
    category_bytes = {key: sum(totals[key] for totals in byte_totals) for key in category_keys}
    category_tokens = {key: sum(totals[key] for totals in token_totals) for key in category_keys}
    for row, (key, label, color) in enumerate(categories, start=1):
        y = legend_top + row * row_height
        elements.append(f'<rect x="{margin_left}" y="{y - 11}" width="12" height="12" rx="2" fill="{color}"/>')
        elements.append(svg_text(columns[0], y, label, primary_ink, 12))
        values = (
            f"{category_bytes[key]:,}", share_text(category_bytes[key], all_bytes),
            f"{category_tokens[key]:,}", share_text(category_tokens[key], all_tokens),
        )
        for column, value in zip(columns[1:], values):
            elements.append(svg_text(column, y, value, primary_ink, 12, anchor="end", numeric=True))
    y = legend_top + (len(categories) + 1) * row_height
    elements.append(svg_text(columns[0], y, "total", primary_ink, 12, weight="600"))
    for column, value in zip(columns[1:], (f"{all_bytes:,}", "100%", f"{all_tokens:,}", "100%")):
        elements.append(svg_text(column, y, value, primary_ink, 12, anchor="end", weight="600", numeric=True))
    return svg_document(width, height, elements)


def draw_growth_svg(transcript_name, base, series):
    margin_left, margin_right, plot_width = 72, 24, 1600
    title_height = 92
    context_top, context_height = title_height + 16, 180
    growth_top, growth_height = context_top + context_height + 56, 220
    plot_bottom = growth_top + growth_height
    legend_top = plot_bottom + 64
    row_height = 22
    width = margin_left + plot_width + margin_right
    height = legend_top + 5 * row_height + 24
    slot = plot_width / len(series)
    gap = 2 if slot >= 5 else (1 if slot >= 3 else 0)
    bar_width = max(slot - gap, 0.5)

    context_step, context_top_value = nice_token_scale(max(entry["measured"] for entry in series))
    positive_max = max(entry["visible"] + max(entry["invisible"], 0) for entry in series)
    negative_max = max([0] + [-entry["invisible"] for entry in series])
    growth_step, growth_top_value = nice_token_scale(max(positive_max, 1))
    growth_bottom_value = math.ceil(negative_max / growth_step) * growth_step
    growth_span = growth_top_value + growth_bottom_value
    zero_y = growth_top + growth_top_value / growth_span * growth_height

    def context_y(value):
        return context_top + context_height - value / context_top_value * context_height

    def growth_pixels(value):
        return value / growth_span * growth_height

    total_growth = sum(entry["growth"] for entry in series)
    total_visible = sum(entry["visible"] for entry in series)
    correlation, tokens_per_kilobyte = thinking_relation(series)
    elements = [
        f'<rect width="{width}" height="{height}" fill="{surface_color}"/>',
        svg_text(margin_left, 32, f"Growth map: {transcript_name}", primary_ink, 18, weight="600"),
        svg_text(
            margin_left, 54,
            f"base context at the first request: {base['measured']:,} tokens; "
            f"measured context at the end: {series[-1]['measured']:,} tokens",
            secondary_ink, 12, numeric=True,
        ),
        svg_text(
            margin_left, 72,
            "Measured by the API at each turn's last request, so a turn's final answer counts toward the next turn. "
            f"Visible text is estimated at {characters_per_token} characters per token.",
            muted_ink, 11,
        ),
    ]

    tick = 0
    while tick <= context_top_value + 1e-9:
        y = context_y(tick)
        elements.append(svg_line(margin_left, margin_left + plot_width, y, gridline_color if tick else baseline_color))
        elements.append(svg_text(margin_left - 8, y + 4, token_label(tick), muted_ink, 11, anchor="end", numeric=True))
        tick += context_step
    points = [(margin_left + (index + 0.5) * slot, context_y(entry["measured"])) for index, entry in enumerate(series)]
    line_path = " ".join(f"{'M' if index == 0 else 'L'}{x:.1f},{y:.1f}" for index, (x, y) in enumerate(points))
    bottom_y = context_y(0)
    elements.append(
        f'<path d="{line_path} L{points[-1][0]:.1f},{bottom_y:.1f} L{points[0][0]:.1f},{bottom_y:.1f} Z" '
        f'fill="{context_area_color}"/>'
    )
    elements.append(f'<path d="{line_path}" fill="none" stroke="{context_line_color}" stroke-width="2"/>')
    elements.append(svg_text(margin_left + 8, context_top + 14, "measured context at the end of each turn", secondary_ink, 12))

    tick = -growth_bottom_value
    while tick <= growth_top_value + 1e-9:
        y = zero_y - growth_pixels(tick)
        elements.append(svg_line(margin_left, margin_left + plot_width, y, gridline_color))
        elements.append(svg_text(margin_left - 8, y + 4, token_label(tick), muted_ink, 11, anchor="end", numeric=True))
        tick += growth_step
    for index, entry in enumerate(series):
        x = margin_left + index * slot + gap / 2
        title = (
            f"turn {index}: context {entry['measured']:,} tokens at the end; added {entry['growth']:,} "
            f"(visible as text about {entry['visible']:,}, not visible about {entry['invisible']:,}); "
            f"thinking bytes {entry['thinking_bytes']:,}"
        )
        elements.append(f"<g><title>{escape(title)}</title>")
        visible_height = growth_pixels(max(entry["visible"], 0))
        if visible_height >= 0.05:
            elements.append(
                f'<rect x="{x:.2f}" y="{zero_y - visible_height:.2f}" width="{bar_width:.2f}" '
                f'height="{visible_height:.2f}" fill="{visible_color}"/>'
            )
        invisible_height = growth_pixels(abs(entry["invisible"]))
        if invisible_height >= 0.05:
            y = zero_y - visible_height - invisible_height if entry["invisible"] > 0 else zero_y
            elements.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{invisible_height:.2f}" '
                f'fill="{invisible_color}"/>'
            )
        elements.append("</g>")
    elements.append(svg_line(margin_left, margin_left + plot_width, zero_y, baseline_color))
    elements.append(svg_text(margin_left + 8, growth_top + 14, "tokens added per turn; below zero, the estimate exceeds the measurement", secondary_ink, 12))
    turn_axis(elements, len(series), margin_left, slot, plot_width, plot_bottom)

    rows = [
        ("rect", visible_color, "visible as text (estimated)", f"{total_visible:,}"),
        ("rect", invisible_color, "not visible as text (measured minus estimated)", f"{total_growth - total_visible:,}"),
        ("line", context_line_color, "measured context at the end", f"{series[-1]['measured']:,}"),
    ]
    elements.append(svg_text(margin_left + 20, legend_top, "series", secondary_ink, 12, weight="600"))
    elements.append(svg_text(margin_left + 520, legend_top, "tokens", secondary_ink, 12, anchor="end", weight="600"))
    for row, (shape, color, label, value) in enumerate(rows, start=1):
        y = legend_top + row * row_height
        if shape == "rect":
            elements.append(f'<rect x="{margin_left}" y="{y - 11}" width="12" height="12" rx="2" fill="{color}"/>')
        else:
            elements.append(f'<line x1="{margin_left}" x2="{margin_left + 12}" y1="{y - 5}" y2="{y - 5}" stroke="{color}" stroke-width="2"/>')
        elements.append(svg_text(margin_left + 20, y, label, primary_ink, 12))
        elements.append(svg_text(margin_left + 520, y, value, primary_ink, 12, anchor="end", numeric=True))
    if correlation is not None:
        y = legend_top + 4 * row_height + 4
        elements.append(svg_text(
            margin_left, y,
            f"Per turn, invisible growth against thinking bytes: Pearson r = {correlation:.2f}, "
            f"about {tokens_per_kilobyte:,.0f} tokens per KB of thinking bytes.",
            secondary_ink, 12, numeric=True,
        ))
    return svg_document(width, height, elements)


def print_summary(size_map, transcript_path, base, series):
    statistics = size_map.statistics
    part_bytes = size_map.part_totals("bytes")
    part_tokens = size_map.part_totals("tokens")
    all_bytes = sum(part_bytes.values())
    all_tokens = sum(part_tokens.values())
    print(f"Size map of {transcript_path.name}")
    print(
        f"  file: {statistics['file_bytes']:,} bytes, {statistics['records']:,} records "
        f"({statistics['unparsable_records']} unparsable), {len(size_map.turns)} turns"
    )
    print(
        f"  images: {statistics['images']} ({statistics['images_from_reads']} from file reads, "
        f"{statistics['images_without_size']} without a readable size)"
    )
    print(f"  requests with usage numbers: {len(size_map.seen_requests):,}")
    if size_map.last_usage:
        usage = size_map.last_usage
        measured = context_tokens(usage)
        print(
            f"  measured context at the last request: {measured:,} tokens "
            f"(input {usage.get('input_tokens', 0):,}, cache read {usage.get('cache_read_input_tokens', 0):,}, "
            f"cache write {usage.get('cache_creation_input_tokens', 0):,})"
        )
        print(f"  estimated tokens of all content: {all_tokens:,}; measured minus estimated: {measured - all_tokens:,}")
    if base:
        total_growth = sum(entry["growth"] for entry in series)
        total_visible = sum(entry["visible"] for entry in series)
        print(f"  base context at the first request: {base['measured']:,} tokens, about {base['visible']:,} of them visible as text")
        print(
            f"  growth after that: {total_growth:,} tokens; visible as text about {total_visible:,}, "
            f"not visible as text about {total_growth - total_visible:,}"
        )
        correlation, tokens_per_kilobyte = thinking_relation(series)
        if correlation is not None:
            print(
                f"  per turn, invisible growth against thinking bytes: Pearson r = {correlation:.2f}, "
                f"about {tokens_per_kilobyte:,.0f} tokens per KB of thinking bytes"
            )
        top_turns = sorted(series, key=lambda entry: entry["invisible"], reverse=True)[:5]
        listing = ", ".join(f"{entry['turn']} ({entry['invisible']:,})" for entry in top_turns)
        print(f"  turns with the most invisible growth: {listing}")
    print()
    print(f"  {'part':<30}{'bytes':>14}{'share':>9}{'est. tokens':>14}{'share':>9}")
    labels = {key: label for key, label, _ in categories}
    for part in part_names:
        label = labels.get(part) or f"other: {other_parts[part]}"
        print(
            f"  {label:<30}{part_bytes[part]:>14,}{share_text(part_bytes[part], all_bytes):>9}"
            f"{part_tokens[part]:>14,}{share_text(part_tokens[part], all_tokens):>9}"
        )
    print(f"  {'total':<30}{all_bytes:>14,}{'100%':>9}{all_tokens:>14,}{'100%':>9}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Draws the size map of a Claude Code transcript.")
    parser.add_argument("transcript", type=Path, help="the transcript, a .jsonl file")
    parser.add_argument("--output-file", type=Path, required=True, help="where the size map SVG goes")
    parser.add_argument("--growth-file", type=Path, help="where the growth map SVG goes; optional")
    arguments = parser.parse_args()
    size_map = Size_map()
    size_map.read(arguments.transcript)
    base, series = growth_series(size_map)
    arguments.output_file.parent.mkdir(parents=True, exist_ok=True)
    arguments.output_file.write_text(draw_svg(size_map, arguments.transcript.name), encoding="utf-8")
    print_summary(size_map, arguments.transcript, base, series)
    print(f"\n  size map: {arguments.output_file}")
    if arguments.growth_file and base:
        arguments.growth_file.parent.mkdir(parents=True, exist_ok=True)
        arguments.growth_file.write_text(draw_growth_svg(arguments.transcript.name, base, series), encoding="utf-8")
        print(f"  growth map: {arguments.growth_file}")


if __name__ == "__main__":
    main()

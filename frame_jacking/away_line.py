"""Tells a window when Wally was away, in a UserPromptSubmit hook, and stays silent on every other turn.

Away means more than away_threshold_minutes since Wally's last message in the transcript; the line comes with Wally's next message.
Only Wally's messages count: a task notification is a prompt too, so on a notification turn the hook stays silent, and notifications in the transcript are passed over.
The line says it in whole units: minutes under an hour, hours under a day, days after that; no dates, and no time of day.
The message about to be sent is not in the transcript yet, so the last message found is the one before it.
Any failure prints nothing, so the prompt always goes through.
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

away_threshold_minutes = 10
tail_bytes = 4_000_000
number_words = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")


def message_text(record):
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(block.get("text", "") for block in content if isinstance(block, dict))
    return ""


def is_wallys_message(record):
    if not isinstance(record, dict) or record.get("type") != "user" or "toolUseResult" in record:
        return False
    if record.get("isSidechain") or record.get("isMeta") or record.get("isCompactSummary"):
        return False
    # A tool result is a user record too, made of tool_result blocks.
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list) and any(isinstance(block, dict) and block.get("type") == "tool_result" for block in content):
        return False
    return "<task-notification>" not in message_text(record)


def last_message_time(transcript_path):
    # Read from the end, and further back while Wally's last message is not in sight yet.
    size = tail_bytes
    while True:
        with open(transcript_path, "rb") as file:
            file.seek(0, 2)
            start = max(0, file.tell() - size)
            file.seek(start)
            lines = file.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if is_wallys_message(record):
                return datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")).timestamp()
        if start == 0:
            return None
        size *= 4


def amount(count, unit):
    word = number_words[count] if count < len(number_words) else str(count)
    return f"{word} {unit}{'' if count == 1 else 's'}"


def away_text(seconds):
    minutes = round(seconds / 60)
    if minutes < 60:
        return amount(minutes, "minute")
    hours = round(seconds / 3600)
    if hours < 24:
        return amount(hours, "hour")
    return amount(round(seconds / 86400), "day")


def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    if "<task-notification>" in (payload.get("prompt") or ""):
        return
    transcript_path = payload.get("transcript_path")
    if not transcript_path or not Path(transcript_path).is_file():
        return
    since = last_message_time(transcript_path)
    if since is None:
        return
    seconds = time.time() - since
    if seconds > away_threshold_minutes * 60:
        line = f"<away>Wally was away for about {away_text(seconds)}.</away>"
        sys.stdout.buffer.write((line + "\n").encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

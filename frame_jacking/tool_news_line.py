"""Tells a window when a marked tool changed since its last turn, in a UserPromptSubmit hook, and stays silent on every other turn.

A tool changed when its deployed SKILL.md is newer than the window's last prompt in the transcript; a window's first turn stays silent.
Any failure prints nothing, so the prompt always goes through.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

skills_location = Path.home() / ".claude" / "skills"
tail_bytes = 4_000_000


def last_prompt_time(transcript_path):
    # The window's last prompt, read from the end of its transcript; the prompt about to be sent is not in it yet.
    with open(transcript_path, "rb") as file:
        file.seek(0, 2)
        file.seek(max(0, file.tell() - tail_bytes))
        lines = file.read().decode("utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and record.get("type") == "user" and not record.get("isSidechain") and not record.get("toolUseResult"):
            return datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")).timestamp()
    return None


def changed_tools(since):
    # Every deployed skill whose front matter carries the mark, and whose SKILL.md is newer than the last prompt.
    changed = []
    for skill_file in sorted(skills_location.glob("*/SKILL.md")):
        if skill_file.stat().st_mtime <= since:
            continue
        data = skill_file.read_bytes()
        front_matter = data.split(b"---", 2)[1] if data.startswith(b"---") else b""
        if b"hallmark_tool" in front_matter:
            changed.append(skill_file.parent.name)
    return changed


def main():
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
    transcript_path = payload.get("transcript_path")
    if not transcript_path or not Path(transcript_path).is_file():
        return
    since = last_prompt_time(transcript_path)
    if since is None:
        return
    changed = changed_tools(since)
    if changed:
        names = changed[0] if len(changed) == 1 else ", ".join(changed[:-1]) + " and " + changed[-1]
        line = f"<tool_news>🔧 {names} changed: load {'it' if len(changed) == 1 else 'them'} again</tool_news>"
        sys.stdout.buffer.write((line + "\n").encode("utf-8"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass

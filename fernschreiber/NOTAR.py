"""NOTAR, a notice to all ravens: the prepared messages, one `##` chapter each, from one markdown file."""

import re
from dataclasses import dataclass
from pathlib import Path

HEADING = re.compile(r"^(#+)\s*(.*?)\s*$")


@dataclass
class NOTAR_message:
    title: str
    text: str


def load_NOTAR_messages(file_location: Path) -> list[NOTAR_message]:
    """Reads the messages, and stops fernschreiber before its window opens when the file breaks a rule, naming the line and the rule."""

    def fail(line_number: int, problem: str) -> None:
        raise ValueError(f"{file_location}, line {line_number}: {problem}")

    chapters: list[tuple[int, str, list[str]]] = []
    seen_title_line = False
    for line_number, line in enumerate(file_location.read_text(encoding="utf-8").splitlines(), start=1):
        heading = HEADING.match(line)
        if heading and len(heading.group(1)) == 1:
            if seen_title_line:
                fail(line_number, f"a second `#` title ({line.strip()}); the file has one at most")
            if chapters:
                fail(line_number, f"a `#` title below the chapters ({line.strip()}); it belongs on top")
            seen_title_line = True
        elif heading and len(heading.group(1)) == 2:
            if not heading.group(2):
                fail(line_number, "a chapter without a title")
            chapters.append((line_number, heading.group(2), []))
        elif heading:
            fail(line_number, f"a subchapter ({line.strip()}); a NOTAR has no subchapters")
        elif chapters:
            chapters[-1][2].append(line)
        elif line.strip():
            fail(line_number, "text before the first `##` chapter")

    if not chapters:
        raise ValueError(f"{file_location}: no `##` chapter, so no NOTAR to send")
    messages = []
    titles = set()
    for line_number, title, lines in chapters:
        text = "\n".join(lines).strip()
        if not text:
            fail(line_number, f"the chapter `{title}` has no text")
        if title in titles:
            fail(line_number, f"a second chapter titled `{title}`")
        titles.add(title)
        messages.append(NOTAR_message(title, text))
    return messages

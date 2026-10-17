"""Mail in the Hrafnsmal format, and the own seat's history."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import settings


@dataclass
class Mail:
    time: str
    sender: str
    text: str


def display_time(moment: datetime) -> str:
    """The time alone for today, the date and time for earlier days."""
    moment = moment.astimezone()
    if moment.date() == datetime.now().astimezone().date():
        return moment.strftime("%H:%M")
    return moment.strftime("%Y-%m-%d %H:%M")


def read_mail(file_location: Path) -> Mail:
    """A mail file in the Hrafnsmal format: timestamp, From, To, then the text; anything else shows whole, under its file name."""
    content = file_location.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    try:
        moment = datetime.fromisoformat(lines[0].strip())
    except (IndexError, ValueError):
        moment = datetime.fromtimestamp(file_location.stat().st_mtime)
    if len(lines) >= 3 and lines[1].startswith("From: ") and lines[2].startswith("To: "):
        return Mail(display_time(moment), lines[1].removeprefix("From: ").strip(), "\n".join(lines[3:]).strip("\n"))
    return Mail(display_time(moment), file_location.name, content.strip("\n"))


def already_read_files() -> list[Path]:
    """The files in the own seat's already_read folder, oldest first."""
    folder = settings.HRAFNSMAL / settings.OWN_SEAT / "already_read"
    if not folder.is_dir():
        return []
    return sorted((file for file in folder.iterdir() if file.is_file()), key=lambda file: file.stat().st_mtime)

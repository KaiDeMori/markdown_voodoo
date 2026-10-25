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
    to: str = ""

    @property
    def group(self) -> str:
        """The group a mail went to, or "" for a mail to the own seat."""
        return self.to if self.to and self.to != settings.OWN_SEAT else ""


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
        sender, to = lines[1].removeprefix("From: ").strip(), lines[2].removeprefix("To: ").strip()
        return Mail(display_time(moment), sender, "\n".join(lines[3:]).strip("\n"), to)
    return Mail(display_time(moment), file_location.name, content.strip("\n"))


def recent_direct_mails(count: int) -> list[Mail]:
    """The last mails to the own seat, oldest first; group mails are skipped on the way back, since they live in their threads."""
    mails = []
    for file in reversed(already_read_files()):
        mail = read_mail(file)
        if not mail.group:
            mails.append(mail)
            if len(mails) == count:
                break
    return mails[::-1]


def already_read_files() -> list[Path]:
    """The files in the own seat's already_read folder, oldest first."""
    folder = settings.HRAFNSMAL / settings.OWN_SEAT / "already_read"
    if not folder.is_dir():
        return []
    return sorted((file for file in folder.iterdir() if file.is_file()), key=lambda file: file.stat().st_mtime)

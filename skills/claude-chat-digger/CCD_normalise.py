"""CCD value normalisation — path spellings and timestamps, shared by every layer.

Claude Code records one folder under several spellings (`c:\\dev\\app`, `C:\\dev\\app`), and a caller may type more (`C:/dev/app`, `~/app`, Git Bash's `/c/dev/app`).
`display_path` is the one form CCD stores and shows; `path_key` is the one form it compares, and `in_workspace` compares two keys by whole folder names.
Timestamps stay as Claude Code writes them, UTC ISO 8601 with milliseconds; `local_time_text` shows one in local time, and `time_span` turns a typed date or date-time bound into that stored form.
No SQLite, corpus, or search logic lives here.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

DRIVE_PATTERN = re.compile(r"^([A-Za-z]):(?=[\\/]|$)")
GIT_BASH_DRIVE_PATTERN = re.compile(r"^/([a-z])(?=/|$)")
ABSOLUTE_KEY_PATTERN = re.compile(r"^(?:[a-z]:(?:/|$)|/)")
TIME_BOUND_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})"
    r"(?:[T ](?P<minutes>\d{2}:\d{2})(?P<seconds>:\d{2})?(?P<fraction>\.\d+)?(?P<offset>Z|[+-]\d{2}:?\d{2})?)?$"
)


def display_path(path: Optional[str]) -> str:
    """A recorded path as CCD shows it: the drive letter upper-cased, everything else as recorded."""
    if not path:
        return ""
    return DRIVE_PATTERN.sub(lambda match: match.group(1).upper() + ":", path, count=1)


def path_key(path: Optional[str]) -> str:
    """The form every spelling of one folder shares, used only to compare.

    Forward slashes, lower case, no trailing slash.
    A leading `~` is expanded, and on Windows Git Bash's `/c/...` becomes `c:/...`.
    """
    if not path:
        return ""
    if path.startswith("~"):
        path = os.path.expanduser(path)
    key = path.replace("\\", "/").lower()
    if os.name == "nt":
        key = GIT_BASH_DRIVE_PATTERN.sub(r"\1:", key, count=1)
    if len(key) > 1:
        key = key.rstrip("/") or "/"
    return key


def in_workspace(project_key: Optional[str], workspace_key: Optional[str]) -> bool:
    """Whether a project folder lies in a workspace, comparing whole folder names.

    An absolute workspace (`c:/dev/app`) matches that folder and everything under it.
    A relative one (`app`, `dev/app`) matches those folder names anywhere in the path.
    Either way, `app` never matches `apple`.
    Both arguments are `path_key` forms; `Chat_digger._connect` registers this as an SQL function.
    """
    if not project_key or not workspace_key:
        return False
    if ABSOLUTE_KEY_PATTERN.match(workspace_key):
        prefix = workspace_key if workspace_key.endswith("/") else workspace_key + "/"
        return project_key == workspace_key or project_key.startswith(prefix)
    return ("/" + workspace_key + "/") in ("/" + project_key + "/")


def parse_timestamp(text: Optional[str]) -> Optional[datetime]:
    """An ISO 8601 timestamp as an aware datetime; one without an offset is taken as local time."""
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.astimezone()


def local_time_text(timestamp: Optional[str]) -> str:
    """A timestamp in local time, ISO 8601 to the minute with its offset, e.g. `2026-10-01T15:51+02:00`."""
    moment = parse_timestamp(timestamp)
    if moment is None:
        return timestamp or "?"
    return moment.astimezone().isoformat(timespec="minutes")


def stored_time_text(moment: datetime) -> str:
    """A moment in the stored timestamp form, UTC with milliseconds, so it compares correctly as text."""
    utc = moment.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S") + ".%03dZ" % (utc.microsecond // 1000)


def time_span(bound: str) -> tuple[str, str]:
    """The stretch of time a typed bound names, as stored timestamps `[start, end)`.

    A bare date is a local calendar day; a date-time without an offset is local time.
    The stretch is as long as the bound's own precision, a minute for `15:51` and a second for `15:51:30`, so an upper bound keeps everything CCD shows with that value.
    """
    match = TIME_BOUND_PATTERN.match(bound.strip())
    start = parse_timestamp(bound) if match else None
    if start is None:
        raise ValueError("not a date or ISO 8601 date-time: %r" % bound)
    if match.group("minutes") is None:
        following = date.fromisoformat(match.group("date")) + timedelta(days=1)
        end = datetime(following.year, following.month, following.day).astimezone()
    elif match.group("fraction"):
        digits = min(len(match.group("fraction")) - 1, 3)
        end = start + timedelta(milliseconds=10 ** (3 - digits))
    elif match.group("seconds"):
        end = start + timedelta(seconds=1)
    else:
        end = start + timedelta(minutes=1)
    return stored_time_text(start), stored_time_text(end)

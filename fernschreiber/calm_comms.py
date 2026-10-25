"""The bridge to calm-comms: every call to calm_comms.sh goes through here."""

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import settings

# The raw MSYS bash takes PATH as it comes; without Git's usr/bin first, date, sleep and rm are missing, and find and sort are Windows' own.
# Terminal mode: present without a timer, one line per mail, no pause after a write, no inbox limits.
CALM_COMMS_ENVIRONMENT = dict(
    os.environ,
    LANG="C.UTF-8",
    PATH=settings.GIT_USR_BIN + os.pathsep + os.environ.get("PATH", ""),
    calm_comms_mode="terminal",
)
CALM_COMMS_OPTIONS = dict(stdin=subprocess.DEVNULL, env=CALM_COMMS_ENVIRONMENT)
# The text goes in on stdin, so the Windows command line never carries it: no quoting, no globbing.
SEND_SCRIPT = 'exec bash "$0" "$1" "$2" "$3" "$(cat)"'


@dataclass
class Group:
    name: str
    members: list[str]

    @property
    def joined(self) -> bool:
        return settings.OWN_SEAT in self.members


def calm_comms_command(*arguments: str) -> list[str]:
    return [settings.BASH, settings.CALM_COMMS, *arguments]


def run_calm_comms(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(calm_comms_command(*arguments), capture_output=True, **CALM_COMMS_OPTIONS)


def start_watcher() -> subprocess.Popen:
    """Starts the own seat's watcher; in terminal mode it prints one line per mail, and leaves as soon as its stdin closes."""
    # The open stdin pipe is fernschreiber's presence: when fernschreiber ends, even hard, the pipe closes and the watcher leaves.
    return subprocess.Popen(
        calm_comms_command("on", settings.OWN_SEAT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=CALM_COMMS_ENVIRONMENT,
    )


def send_mail(target: str, text: str, verb: str = "send") -> subprocess.CompletedProcess:
    """Sends a mail from the own seat through calm-comms: `send` to a seat, or `group` to a group."""
    return subprocess.run(
        [settings.BASH, "-c", SEND_SCRIPT, settings.CALM_COMMS, verb, settings.OWN_SEAT, target],
        input=text.encode("utf-8"),
        capture_output=True,
        env=CALM_COMMS_ENVIRONMENT,
    )


def read_groups() -> list[Group]:
    """Every group in group_chat: a folder with a members folder, one empty file per member seat."""
    groups = []
    if settings.GROUP_CHAT.is_dir():
        for folder in sorted(settings.GROUP_CHAT.iterdir()):
            members_folder = folder / "members"
            if members_folder.is_dir():
                groups.append(Group(folder.name, sorted(member.name for member in members_folder.iterdir() if member.is_file())))
    return groups


def group_snapshot() -> tuple:
    """What the groups look like right now: each group's name, its members and its thread files; equal snapshots mean nothing changed."""
    snapshot = []
    for group in read_groups():
        threads = tuple(sorted(file.name for file in (settings.GROUP_CHAT / group.name).glob("*.md")))
        snapshot.append((group.name, tuple(group.members), threads))
    return tuple(snapshot)


def thread_files(group_name: str) -> list[Path]:
    """A group's thread: its mail files, oldest first."""
    folder = settings.GROUP_CHAT / group_name
    files = [file for file in folder.glob("*.md") if file.is_file() and file.name != "README.md"]
    return sorted(files, key=lambda file: file.stat().st_mtime)


def join_or_leave(verb: str, group_name: str) -> tuple[bool, str]:
    """`join` or `leave` for the own seat; returns whether it worked and calm-comms' own line."""
    result = run_calm_comms(verb, settings.OWN_SEAT, group_name)
    output = (result.stdout + result.stderr).decode("utf-8", "replace").strip()
    return result.returncode == 0, output or f"calm-comms stopped with exit code {result.returncode}"


def is_watching(state: list[str], now: datetime) -> bool:
    """Whether an overview state names a raven that listens: `present` in terminal mode, `awake` while it re-arms, or `until 2026-10-17T12:09+02:00` that has not run out."""
    if state in (["present"], ["awake"]):
        return True
    if len(state) != 2 or state[0] != "until":
        return False
    try:
        return datetime.fromisoformat(state[1]) > now
    except ValueError:
        return False


def read_seats() -> list[tuple[str, bool]] | None:
    """The seats from calm-comms `overview`, without Wally's own, each with whether it is watching; None when overview fails."""
    result = run_calm_comms("overview")
    if result.returncode != 0:
        return None
    now = datetime.now().astimezone()
    seats = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if parts and parts[0] != settings.OWN_SEAT:
            seats.append((parts[0], is_watching(parts[1:], now)))
    return seats

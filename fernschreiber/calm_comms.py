"""The bridge to calm-comms: every call to calm_comms.sh goes through here."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import settings

# The raw MSYS bash takes PATH as it comes; Git's usr/bin goes first, so the script finds its own tools.
CALM_COMMS_ENVIRONMENT = dict(
    os.environ,
    LANG="C.UTF-8",
    PATH=settings.GIT_USR_BIN + os.pathsep + os.environ.get("PATH", ""),
)
# A mailbox with its door open: a raven watches the seat.
WATCHING_MAILBOXES = ("📬", "📭")
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
    """Starts the own seat's watcher: it prints one line, `<moment> mail: <file>` or `<moment> timer`, and exits."""
    return subprocess.Popen(calm_comms_command("on", settings.OWN_SEAT), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **CALM_COMMS_OPTIONS)


def stop_watcher() -> None:
    """Runs `off` without waiting for it: it stops the watcher and closes the door."""
    subprocess.Popen(calm_comms_command("off", settings.OWN_SEAT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **CALM_COMMS_OPTIONS)


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


def read_seats() -> list[tuple[str, bool]] | None:
    """The seats from calm-comms `overview`, `<seat> <mailbox>` each, without Wally's own, each with whether it is watching; None when overview fails."""
    result = run_calm_comms("overview")
    if result.returncode != 0:
        return None
    seats = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if parts and parts[0] != settings.OWN_SEAT:
            seats.append((parts[0], len(parts) > 1 and parts[1] in WATCHING_MAILBOXES))
    return seats

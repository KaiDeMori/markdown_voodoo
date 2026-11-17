"""The bridge to calm-comms: every call to calm_comms.sh goes through here."""

import os
import re
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
# A mail's file name carries the moment it was written, and these moments sort the way time runs.
MAIL_MOMENT = re.compile(r"\d{4}-\d{2}-\d{2}_\d{6}")
# A group's name becomes a folder's name and a word in calm-comms commands.
GROUP_NAME = re.compile(r"[A-Za-z0-9_-]+")


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
    """What the groups look like right now: each group's name, its members and its thread's mail names; equal snapshots mean nothing changed."""
    snapshot = []
    for group in read_groups():
        # Names, not places: a mail that every member has read moves into already_read, and the thread stays the same.
        threads = tuple(file.name for file in thread_files(group.name))
        snapshot.append((group.name, tuple(group.members), threads))
    return tuple(snapshot)


def thread_files(group_name: str) -> list[Path]:
    """A group's thread, oldest first: the mails still on their way to a reader, and those every member has read, in already_read."""
    folder = settings.GROUP_CHAT / group_name
    # Listed before already_read, so a mail that moves in between still turns up there.
    files = {file.name: file for file in folder.glob("*.md") if file.is_file() and file.name != "README.md"}
    files.update({file.name: file for file in (folder / "already_read").glob("*.md") if file.is_file()})
    return sorted(files.values(), key=mail_moment)


def mail_moment(file: Path) -> tuple[str, str]:
    """Sorts by the moment in a mail's file name, which a move into already_read never changes; a name without one sorts by itself."""
    moment = MAIL_MOMENT.search(file.name)
    return (moment.group() if moment else file.name, file.name)


def join_or_leave(verb: str, group_name: str) -> tuple[bool, str]:
    """`join` or `leave` for the own seat; returns whether it worked and calm-comms' own line."""
    result = run_calm_comms(verb, settings.OWN_SEAT, group_name)
    output = (result.stdout + result.stderr).decode("utf-8", "replace").strip()
    return result.returncode == 0, output or f"calm-comms stopped with exit code {result.returncode}"


def new_group_problem(group_name: str, purpose: str) -> str | None:
    """Why a group by this name can't be created, or None when it can."""
    if not group_name:
        return "the first line names the new group"
    if not GROUP_NAME.fullmatch(group_name):
        return f"{group_name}: a group's name takes only letters, digits, _ and -"
    if (settings.GROUP_CHAT / group_name).exists():
        return f"#{group_name} exists already"
    if (settings.HRAFNSMAL / group_name).exists():
        return f"{group_name} is a seat's name"
    if not purpose:
        return "the second line says what the group is for; it goes into the README"
    return None


def create_group(group_name: str, purpose: str) -> str:
    """Creates the group's folder, its members folder and a README that says what it is for, then joins the own seat; returns the line to show."""
    folder = settings.GROUP_CHAT / group_name
    try:
        folder.mkdir()
        (folder / "members").mkdir()
        (folder / "README.md").write_text(f"# {group_name}\n\n{purpose}\n", encoding="utf-8")
    except OSError as error:
        return f"#{group_name} could not be created: {error.strerror or error}"
    return join_or_leave("join", group_name)[1]


def read_mailboxes() -> dict[str, str] | None:
    """Every seat's mailbox from calm-comms `overview`, `<seat> <mailbox>` each; None when overview fails."""
    result = run_calm_comms("overview")
    if result.returncode != 0:
        return None
    mailboxes = {}
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if parts:
            mailboxes[parts[0]] = parts[1] if len(parts) > 1 else ""
    return mailboxes


def seats_from(mailboxes: dict[str, str]) -> list[tuple[str, bool]]:
    """The seats without Wally's own, each with whether a raven watches it."""
    return [(name, mailbox in WATCHING_MAILBOXES) for name, mailbox in mailboxes.items() if name != settings.OWN_SEAT]

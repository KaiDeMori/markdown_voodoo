"""The bridge to calm-comms: every call to calm_comms.sh goes through here."""

import os
import subprocess
from datetime import datetime

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
SEND_SCRIPT = 'exec bash "$0" send "$1" "$2" "$(cat)"'


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


def send_mail(target_seat: str, text: str) -> subprocess.CompletedProcess:
    """Sends a mail from the own seat through calm-comms `send`."""
    return subprocess.run(
        [settings.BASH, "-c", SEND_SCRIPT, settings.CALM_COMMS, settings.OWN_SEAT, target_seat],
        input=text.encode("utf-8"),
        capture_output=True,
        env=CALM_COMMS_ENVIRONMENT,
    )


def is_watching(state: list[str], now: datetime) -> bool:
    """Whether an overview state names a running watcher: `present` in terminal mode, or `until 2026-10-17T12:09+02:00` that has not run out."""
    if state == ["present"]:
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

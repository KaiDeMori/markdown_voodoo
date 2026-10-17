"""fernschreiber: a calm terminal for Wally's Rabenschnack mail."""

import os
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Input, Static

TITLE = "RABENSCHNACK"
KEY_HINTS = "[Up/Down] seat   [Enter] send   [Ctrl+Q] quit"
SEAT_PANE_WIDTH = 22
SEAT_REFRESH_SECONDS = 30
WATCH_MINUTES = 15
HISTORY_MAIL_COUNT = 20
INBOX_MAIL_LIMIT = 100

FRAME_COLOR = "#6c6c6c"
TEXT_COLOR = "#c8c8c8"
DIM_COLOR = "#8a8a8a"
BACKGROUND_COLOR = "#0c0c0c"

GIT_USR_BIN = r"C:\Program Files\Git\usr\bin"
BASH = GIT_USR_BIN + r"\bash.exe"
CALM_COMMS = "C:/Users/devboese/.claude/skills/calm-comms/calm_comms.sh"
HRAFNSMAL = Path("C:/haven/Hall/thing/Hrafnsmal")
OWN_SEAT = "wally"


@dataclass
class Mail:
    time: str
    sender: str
    text: str


def ascii_rule(width: int, left: str = "", right: str = "", junction: int | None = None) -> str:
    """A horizontal frame line: corners, a label after the left corner, a label before the right corner, and an optional junction."""
    if width < 2:
        return "+" * width
    cells = ["+"] + ["-"] * (width - 2) + ["+"]
    if junction is not None and 0 < junction < width - 1:
        cells[junction] = "+"
    if left and len(left) + 6 <= width:
        cells[3:5 + len(left)] = f" {left} "
    if right and len(right) + 6 <= width:
        cells[width - 5 - len(right):width - 3] = f" {right} "
    return "".join(cells)


def calm_comms_command(*arguments: str) -> list[str]:
    return [BASH, CALM_COMMS, *arguments]


# The raw MSYS bash takes PATH as it comes; without Git's usr/bin first, date, sleep and rm are missing, and find and sort are Windows' own.
CALM_COMMS_OPTIONS = dict(
    stdin=subprocess.DEVNULL,
    env=dict(os.environ, LANG="C.UTF-8", PATH=GIT_USR_BIN + os.pathsep + os.environ.get("PATH", "")),
)


def run_calm_comms(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(calm_comms_command(*arguments), capture_output=True, **CALM_COMMS_OPTIONS)


def is_watching(state: list[str], now: datetime) -> bool:
    """Whether an overview state such as `until 2026-10-17T12:09+02:00` names a watcher whose time has not run out."""
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
        if parts and parts[0] != OWN_SEAT:
            seats.append((parts[0], is_watching(parts[1:], now)))
    return seats


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
    folder = HRAFNSMAL / OWN_SEAT / "already_read"
    if not folder.is_dir():
        return []
    return sorted((file for file in folder.iterdir() if file.is_file()), key=lambda file: file.stat().st_mtime)


class Rule_line(Static):
    """A horizontal frame line that redraws itself whenever its width changes."""

    def __init__(self, left: str = "", right: str = "", junction: int | None = None, **kwargs) -> None:
        super().__init__(markup=False, **kwargs)
        self.left = left
        self.right = right
        self.junction = junction
        self.line = ""

    def on_resize(self) -> None:
        self.redraw()

    def redraw(self) -> None:
        self.line = ascii_rule(self.size.width, self.left, self.right, self.junction)
        self.update(self.line)


class Seat_list(Static):
    """The seats, with "~" for the ones watching and ">" for the one Wally writes to."""

    def __init__(self, **kwargs) -> None:
        super().__init__(markup=False, **kwargs)
        self.seats: list[tuple[str, bool]] = []
        self.selected = 0

    def on_mount(self) -> None:
        self.redraw()

    @property
    def selected_name(self) -> str:
        return self.seats[self.selected][0] if self.seats else ""

    def set_seats(self, seats: list[tuple[str, bool]]) -> None:
        """Takes a fresh list and keeps the selection on the same seat; a new selection starts at the first watching seat."""
        previous = self.selected_name
        self.seats = seats
        names = [name for name, _ in seats]
        if previous in names:
            self.selected = names.index(previous)
        else:
            watching = [index for index, (_, is_watching) in enumerate(seats) if is_watching]
            self.selected = watching[0] if watching else 0
        self.redraw()

    def move(self, step: int) -> None:
        if self.seats:
            self.selected = max(0, min(len(self.seats) - 1, self.selected + step))
            self.redraw()

    def redraw(self) -> None:
        lines = [" seats"]
        for index, (name, watching) in enumerate(self.seats):
            lines.append(f"{'>' if index == self.selected else ' '} {'~' if watching else ' '} {name}")
        self.update("\n".join(lines))


class Fernschreiber(App):
    TITLE = "fernschreiber"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("up", "move_seat(-1)", show=False, priority=True),
        Binding("down", "move_seat(1)", show=False, priority=True),
        Binding("pageup", "scroll_inbox(-1)", show=False, priority=True),
        Binding("pagedown", "scroll_inbox(1)", show=False, priority=True),
    ]
    CSS = f"""
    Screen {{ background: {BACKGROUND_COLOR}; color: {TEXT_COLOR}; }}
    .rule {{ height: 1; color: {FRAME_COLOR}; }}
    #main {{ height: 1fr; }}
    #seats {{ width: {SEAT_PANE_WIDTH}; height: 1fr; border-left: ascii {FRAME_COLOR}; border-right: ascii {FRAME_COLOR}; }}
    #inbox {{ width: 1fr; height: 1fr; padding: 0 1; border-right: ascii {FRAME_COLOR}; scrollbar-size: 0 0; }}
    .mail_head {{ color: {DIM_COLOR}; margin-top: 1; }}
    .mail_body {{ padding-left: 2; }}
    #input_row {{ height: 1; border-left: ascii {FRAME_COLOR}; border-right: ascii {FRAME_COLOR}; }}
    #prompt {{ width: auto; }}
    Input {{ width: 1fr; height: 1; padding: 0; border: none; background: {BACKGROUND_COLOR}; color: {TEXT_COLOR}; }}
    Input:focus {{ border: none; }}
    """

    def __init__(self) -> None:
        super().__init__()
        self.watcher: subprocess.Popen | None = None
        self.watcher_lock = threading.Lock()
        self.stopping = False

    def compose(self) -> ComposeResult:
        yield Rule_line(left=TITLE, right=self.clock_text(), id="top_rule", classes="rule")
        with Horizontal(id="main"):
            yield Seat_list(id="seats")
            with VerticalScroll(id="inbox"):
                yield Static(OWN_SEAT, markup=False)
        yield Rule_line(junction=SEAT_PANE_WIDTH - 1, id="middle_rule", classes="rule")
        with Horizontal(id="input_row"):
            yield Static("", markup=False, id="prompt")
            yield Input(id="message")
        yield Rule_line(left=KEY_HINTS, id="bottom_rule", classes="rule")

    def on_mount(self) -> None:
        self.update_prompt()
        self.query_one(Input).focus()
        # Anchored, the inbox stays at the bottom as mail comes in, until Wally scrolls up.
        self.query_one("#inbox", VerticalScroll).anchor()
        self.set_interval(5, self.tick)
        self.refresh_seats()
        self.set_interval(SEAT_REFRESH_SECONDS, self.refresh_seats)
        self.run_worker(self.watch_loop, thread=True, group="watch")

    def on_unmount(self) -> None:
        self.stop_watching()

    async def action_quit(self) -> None:
        self.stop_watching()
        self.exit()

    # The clock

    def clock_text(self) -> str:
        return datetime.now().strftime("%H:%M")

    def tick(self) -> None:
        top_rule = self.query_one("#top_rule", Rule_line)
        clock = self.clock_text()
        if top_rule.right != clock:
            top_rule.right = clock
            top_rule.redraw()

    # The seats

    def refresh_seats(self) -> None:
        self.run_worker(self.load_seats, thread=True, exclusive=True, group="seats")

    def load_seats(self) -> None:
        seats = read_seats()
        if seats is not None:
            self.post(self.show_seats, seats)

    def show_seats(self, seats: list[tuple[str, bool]]) -> None:
        self.query_one(Seat_list).set_seats(seats)
        self.update_prompt()

    def update_prompt(self) -> None:
        self.query_one("#prompt", Static).update(f" to {self.query_one(Seat_list).selected_name or '...'}: ")

    def action_move_seat(self, step: int) -> None:
        self.query_one(Seat_list).move(step)
        self.update_prompt()

    # The inbox

    def watch_loop(self) -> None:
        """Shows the history, then keeps the own seat watched: start `on`, deliver what is waiting, wait for the watcher, again."""
        self.post(self.add_mails, [read_mail(file) for file in already_read_files()[-HISTORY_MAIL_COUNT:]], False)
        while True:
            with self.watcher_lock:
                if self.stopping:
                    return
                self.watcher = subprocess.Popen(calm_comms_command("on", OWN_SEAT, str(WATCH_MINUTES)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **CALM_COMMS_OPTIONS)
            self.deliver_mail()
            return_code = self.watcher.wait()
            if self.stopping:
                return
            if return_code != 0:
                self.post(self.add_mails, [Mail(self.clock_text(), "fernschreiber", f"The watcher stopped with exit code {return_code}; fernschreiber no longer watches.")], True)
                return

    def deliver_mail(self) -> None:
        """Runs `inbox` until nothing more is waiting, and shows the mails it moved into already_read."""
        for _ in range(50):
            before = {file.name for file in already_read_files()}
            result = run_calm_comms("inbox", OWN_SEAT, str(INBOX_MAIL_LIMIT))
            output = result.stdout.decode("utf-8", "replace")
            mails = [read_mail(file) for file in already_read_files() if file.name not in before]
            if result.returncode != 0:
                mails.append(Mail(self.clock_text(), "fernschreiber", output.strip() or f"inbox stopped with exit code {result.returncode}"))
            if mails:
                self.post(self.add_mails, mails, True)
            if result.returncode != 0 or " more waiting: " not in output:
                return

    def add_mails(self, mails: list[Mail], ring: bool) -> None:
        if not mails:
            return
        inbox = self.query_one("#inbox", VerticalScroll)
        widgets = []
        for mail in mails:
            widgets.append(Static(f"{mail.time}  {mail.sender}", markup=False, classes="mail_head"))
            widgets.append(Static(mail.text, markup=False, classes="mail_body"))
        inbox.mount_all(widgets)
        if ring:
            # New mail brings the view back down, even when Wally was reading further up.
            inbox.scroll_end(animate=False)
            self.bell()

    def action_scroll_inbox(self, step: int) -> None:
        inbox = self.query_one("#inbox", VerticalScroll)
        if step < 0:
            inbox.scroll_page_up(animate=False)
        else:
            inbox.scroll_page_down(animate=False)

    def stop_watching(self) -> None:
        """Stops the running watcher and deletes watching.md, which a stopped watcher leaves behind."""
        with self.watcher_lock:
            if self.stopping:
                return
            self.stopping = True
            if self.watcher is not None and self.watcher.poll() is None:
                self.watcher.terminate()
        subprocess.Popen(calm_comms_command("off", OWN_SEAT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **CALM_COMMS_OPTIONS)

    def post(self, callback, *arguments) -> None:
        """Hands a call from a worker thread to the app, unless the app is already on its way out."""
        if self.stopping:
            return
        try:
            self.call_from_thread(callback, *arguments)
        except RuntimeError:
            pass

    # Sending

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.value = ""


if __name__ == "__main__":
    Fernschreiber().run()

"""fernschreiber: a calm terminal for Wally's Rabenschnack mail."""

import os
import subprocess
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Input, Static

TITLE = "RABENSCHNACK"
KEY_HINTS = "[Up/Down] seat   [Enter] send   [Ctrl+Q] quit"
SEAT_PANE_WIDTH = 22
SEAT_REFRESH_SECONDS = 30

FRAME_COLOR = "#6c6c6c"
TEXT_COLOR = "#c8c8c8"
DIM_COLOR = "#8a8a8a"
BACKGROUND_COLOR = "#0c0c0c"

BASH = r"C:\Program Files\Git\usr\bin\bash.exe"
CALM_COMMS = "C:/Users/devboese/.claude/skills/calm-comms/calm_comms.sh"
OWN_SEAT = "wally"

# Dummy data for the first look; step 3 replaces it with Wally's inbox.
DUMMY_MAILS = [
    ("08:05", "tool_builder", "Hi Wally! The red cardinal was a black bird all along."),
    ("09:48", "test_pilot", "Your \U0001F970 landed whole: U+1F970, f0 9f a5 b0."),
]


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


def run_calm_comms(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, CALM_COMMS, *arguments],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        env=dict(os.environ, LANG="C.UTF-8"),
    )


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

    def compose(self) -> ComposeResult:
        yield Rule_line(left=TITLE, right=self.clock_text(), id="top_rule", classes="rule")
        with Horizontal(id="main"):
            yield Seat_list(id="seats")
            with VerticalScroll(id="inbox"):
                yield Static(OWN_SEAT, markup=False)
                for time, sender, text in DUMMY_MAILS:
                    yield Static(f"{time}  {sender}", markup=False, classes="mail_head")
                    yield Static(text, markup=False, classes="mail_body")
        yield Rule_line(junction=SEAT_PANE_WIDTH - 1, id="middle_rule", classes="rule")
        with Horizontal(id="input_row"):
            yield Static("", markup=False, id="prompt")
            yield Input(id="message")
        yield Rule_line(left=KEY_HINTS, id="bottom_rule", classes="rule")

    def on_mount(self) -> None:
        self.update_prompt()
        self.query_one(Input).focus()
        self.set_interval(5, self.tick)
        self.refresh_seats()
        self.set_interval(SEAT_REFRESH_SECONDS, self.refresh_seats)

    def clock_text(self) -> str:
        return datetime.now().strftime("%H:%M")

    def tick(self) -> None:
        top_rule = self.query_one("#top_rule", Rule_line)
        clock = self.clock_text()
        if top_rule.right != clock:
            top_rule.right = clock
            top_rule.redraw()

    def refresh_seats(self) -> None:
        self.run_worker(self.load_seats, thread=True, exclusive=True, group="seats")

    def load_seats(self) -> None:
        seats = read_seats()
        if seats is not None:
            self.call_from_thread(self.show_seats, seats)

    def show_seats(self, seats: list[tuple[str, bool]]) -> None:
        self.query_one(Seat_list).set_seats(seats)
        self.update_prompt()

    def update_prompt(self) -> None:
        self.query_one("#prompt", Static).update(f" to {self.query_one(Seat_list).selected_name or '...'}: ")

    def action_move_seat(self, step: int) -> None:
        self.query_one(Seat_list).move(step)
        self.update_prompt()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.value = ""


if __name__ == "__main__":
    Fernschreiber().run()

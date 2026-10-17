"""fernschreiber: a calm terminal for Wally's Rabenschnack mail."""

from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Input, Static

TITLE = "RABENSCHNACK"
KEY_HINTS = "[Up/Down] seat   [Enter] send   [Ctrl+Q] quit"
SEAT_PANE_WIDTH = 22

FRAME_COLOR = "#6c6c6c"
TEXT_COLOR = "#c8c8c8"
DIM_COLOR = "#8a8a8a"
BACKGROUND_COLOR = "#0c0c0c"

# Dummy data for the first look; calm-comms replaces it later.
DUMMY_SEATS = [
    ("hallmaster", True),
    ("librarian", False),
    ("otis_builder", True),
    ("test_pilot", True),
    ("tool_builder", True),
]
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

    def __init__(self, seats: list[tuple[str, bool]], **kwargs) -> None:
        super().__init__(markup=False, **kwargs)
        self.seats = seats
        self.selected = len(seats) - 1

    def on_mount(self) -> None:
        self.redraw()

    @property
    def selected_name(self) -> str:
        return self.seats[self.selected][0]

    def move(self, step: int) -> None:
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
            yield Seat_list(DUMMY_SEATS, id="seats")
            with VerticalScroll(id="inbox"):
                yield Static("wally", markup=False)
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

    def clock_text(self) -> str:
        return datetime.now().strftime("%H:%M")

    def tick(self) -> None:
        top_rule = self.query_one("#top_rule", Rule_line)
        clock = self.clock_text()
        if top_rule.right != clock:
            top_rule.right = clock
            top_rule.redraw()

    def update_prompt(self) -> None:
        self.query_one("#prompt", Static).update(f" to {self.query_one(Seat_list).selected_name}: ")

    def action_move_seat(self, step: int) -> None:
        self.query_one(Seat_list).move(step)
        self.update_prompt()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.value = ""


if __name__ == "__main__":
    Fernschreiber().run()

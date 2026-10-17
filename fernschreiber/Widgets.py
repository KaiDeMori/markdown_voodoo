"""fernschreiber's widgets: the frame lines, the seat list, the input and the help."""

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static, TextArea

import settings


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


class Seat_list(Static, can_focus=True):
    """The seats, with "~" for the ones watching and ">" for the one Wally writes to."""

    def __init__(self, **kwargs) -> None:
        super().__init__(markup=False, **kwargs)
        self.seats: list[tuple[str, bool]] = []
        self.selected = 0

    def on_mount(self) -> None:
        self.redraw()

    def on_focus(self) -> None:
        self.redraw()

    def on_blur(self) -> None:
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
        text = Text(" seats", style=f"bold {settings.FOCUS_COLOR}" if self.has_focus else settings.DIM_COLOR)
        for index, (name, watching) in enumerate(self.seats):
            text.append(f"\n{'>' if index == self.selected else ' '} {'~' if watching else ' '} {name}")
        self.update(text)


class Message_area(TextArea):
    """The input; it lights up the prompt beside it while it has the focus."""

    def on_focus(self) -> None:
        self.parent.query_one("#prompt", Static).set_class(True, "focused")

    def on_blur(self) -> None:
        self.parent.query_one("#prompt", Static).set_class(False, "focused")


class Help_screen(ModalScreen):
    BINDINGS = [
        Binding("escape", "close", show=False),
        Binding("f1", "close", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Static(settings.HELP_TEXT, markup=False, id="help")

    def action_close(self) -> None:
        self.dismiss()

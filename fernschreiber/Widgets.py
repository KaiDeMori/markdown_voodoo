"""fernschreiber's widgets: the frame lines with their clock, the lists and the input."""

from datetime import datetime

from rich.text import Text
from textual.geometry import Region
from textual.widgets import Static, TextArea


def clock_text() -> str:
    return datetime.now().strftime("%H:%M")


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


class Divider_line(Static):
    """A plain line of dashes across its whole width, without corners; it redraws itself whenever its width changes."""

    def on_resize(self) -> None:
        self.update("-" * self.size.width)


class Title_list(Static, can_focus=True):
    """A list of titles, with ">" for the selected one."""

    def __init__(self, header: str, titles: list[str], **kwargs) -> None:
        super().__init__(markup=False, **kwargs)
        self.header = header
        self.titles = titles
        self.selected = 0

    def on_mount(self) -> None:
        self.redraw()

    # has_focus changes only after these handlers, so they hand the new state in themselves.
    def on_focus(self) -> None:
        self.redraw(focused=True)

    def on_blur(self) -> None:
        self.redraw(focused=False)

    def move(self, step: int) -> None:
        if self.titles:
            self.selected = max(0, min(len(self.titles) - 1, self.selected + step))
            self.redraw()

    def set_titles(self, titles: list[str]) -> None:
        """Takes fresh titles, and keeps the cursor where it was, or on the last one."""
        self.titles = titles
        self.selected = max(0, min(self.selected, len(titles) - 1))
        self.redraw()

    def redraw(self, focused: bool | None = None) -> None:
        text = Text(f" {self.header}", style=header_style(self, focused))
        for index, title in enumerate(self.titles):
            # A title may be a styled Text, which keeps its styles here.
            text.append(f"\n{'>' if index == self.selected else ' '} ")
            text.append(title)
        self.update(text)


class Seat_picker(Static, can_focus=True):
    """The seats, with "[x]" for the marked ones, each seat's mailbox from the last overview, and ">" for the one under the cursor."""

    def __init__(self, header: str, **kwargs) -> None:
        super().__init__(markup=False, **kwargs)
        self.header = header
        self.seats: list[tuple[str, bool]] = []
        self.marked_names: set[str] = set()
        self.selected = 0

    def on_mount(self) -> None:
        self.redraw()

    # has_focus changes only after these handlers, so they hand the new state in themselves.
    def on_focus(self) -> None:
        self.redraw(focused=True)

    def on_blur(self) -> None:
        self.redraw(focused=False)

    @property
    def marked(self) -> list[str]:
        """The marked seats, in the order of the list."""
        return [name for name, _ in self.seats if name in self.marked_names]

    @property
    def selected_name(self) -> str:
        return self.seats[self.selected][0] if self.seats else ""

    def set_seats(self, seats: list[tuple[str, bool]]) -> None:
        """Takes a fresh list, and keeps the cursor and the marks on the seats that are still there; a new cursor starts at the first watching seat."""
        previous = self.selected_name
        self.seats = seats
        names = [name for name, _ in seats]
        self.marked_names &= set(names)
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

    def toggle(self) -> None:
        if self.seats:
            self.marked_names ^= {self.seats[self.selected][0]}
            self.redraw()

    def mark_watching(self) -> None:
        self.marked_names = {name for name, watching in self.seats if watching}
        self.redraw()

    def clear_marks(self) -> None:
        self.marked_names.clear()
        self.redraw()

    def redraw(self, focused: bool | None = None) -> None:
        text = Text(f" {self.header}", style=header_style(self, focused))
        for index, (name, watching) in enumerate(self.seats):
            # Condensed: one cell for the cursor, two for the mark, two for the mailbox, like ">✔️📭 tool_builder".
            # Before the first overview there is no mailbox yet; "~ " keeps the two cells an icon takes.
            mailbox = self.app.mailboxes.get(name) or ("~ " if watching else "  ")
            mark = "\U00002714\U0000FE0F" if name in self.marked_names else "  "
            text.append(f"\n{'>' if index == self.selected else ' '}{mark}{mailbox} {name}")
        self.update(text)
        self.call_after_refresh(self.keep_cursor_in_view)

    def keep_cursor_in_view(self) -> None:
        """Scrolls the surrounding container so the line under ">" stays visible; the header is line 0."""
        if self.seats and self.parent is not None:
            self.parent.scroll_to_region(Region(0, self.selected + 1, max(1, self.size.width), 1), animate=False)


def header_style(widget: Static, focused: bool | None) -> str:
    """A pane's header: lit while the pane has the focus, dim otherwise, in the theme's colors when there is a theme."""
    if focused is None:
        focused = widget.has_focus
    color_theme = widget.app.color_theme
    if focused:
        return f"bold {color_theme.focus}" if color_theme else "bold"
    return color_theme.dim if color_theme else ""


class Message_area(TextArea):
    """The input; it lights up the prompt beside it while it has the focus."""

    # The prompt is the one Static in the same row, whatever its id.
    def on_focus(self) -> None:
        self.parent.query_one(Static).set_class(True, "focused")

    def on_blur(self) -> None:
        self.parent.query_one(Static).set_class(False, "focused")

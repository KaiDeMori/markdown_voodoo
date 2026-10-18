"""NOTAR, a notice to all ravens, on F3: prepared messages from one markdown file, sent to every watching seat at once."""

import re
from dataclasses import dataclass
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

import settings
from calm_comms import send_mail
from Widgets import Rule_line, Title_list, clock_text

HEADING = re.compile(r"^(#+)\s*(.*?)\s*$")


@dataclass
class NOTAR_message:
    title: str
    text: str


def load_NOTAR_messages(file_location: Path) -> list[NOTAR_message]:
    """Reads the messages, one `##` chapter each, and stops fernschreiber before its window opens when the file breaks a rule, naming the line and the rule."""

    def fail(line_number: int, problem: str) -> None:
        raise ValueError(f"{file_location}, line {line_number}: {problem}")

    chapters: list[tuple[int, str, list[str]]] = []
    seen_title_line = False
    for line_number, line in enumerate(file_location.read_text(encoding="utf-8").splitlines(), start=1):
        heading = HEADING.match(line)
        if heading and len(heading.group(1)) == 1:
            if seen_title_line:
                fail(line_number, f"a second `#` title ({line.strip()}); the file has one at most")
            if chapters:
                fail(line_number, f"a `#` title below the chapters ({line.strip()}); it belongs on top")
            seen_title_line = True
        elif heading and len(heading.group(1)) == 2:
            if not heading.group(2):
                fail(line_number, "a chapter without a title")
            chapters.append((line_number, heading.group(2), []))
        elif heading:
            fail(line_number, f"a subchapter ({line.strip()}); a NOTAR has no subchapters")
        elif chapters:
            chapters[-1][2].append(line)
        elif line.strip():
            fail(line_number, "text before the first `##` chapter")

    if not chapters:
        raise ValueError(f"{file_location}: no `##` chapter, so no NOTAR to send")
    messages = []
    titles = set()
    for line_number, title, lines in chapters:
        text = "\n".join(lines).strip()
        if not text:
            fail(line_number, f"the chapter `{title}` has no text")
        if title in titles:
            fail(line_number, f"a second chapter titled `{title}`")
        titles.add(title)
        messages.append(NOTAR_message(title, text))
    return messages


class NOTAR_screen(Screen):
    """NOTAR, a notice to all ravens: one prepared message, sent to every watching seat at once."""

    BINDINGS = [
        Binding("ctrl+enter", "send", show=False, priority=True),
        Binding("up", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
        Binding("escape", "app.switch_mode('rabenschnack')", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.sending = False

    def compose(self) -> ComposeResult:
        yield Rule_line(left="NOTAR", right=clock_text(), id="top_rule", classes="rule")
        with Horizontal(id="notar_main"):
            yield Title_list("NOTARs", [message.title for message in self.app.NOTAR_messages], id="notar_titles")
            with VerticalScroll(id="notar_preview"):
                yield Static("", markup=False, id="notar_recipients")
                yield Static("", markup=False, id="notar_text")
        yield Rule_line(junction=settings.SEAT_PANE_WIDTH - 1, id="middle_rule", classes="rule")
        yield Static("ready", markup=False, id="notar_status")
        yield Rule_line(left=settings.NOTAR_KEY_HINTS, id="bottom_rule", classes="rule")

    def on_mount(self) -> None:
        self.top_rule = self.query_one("#top_rule", Rule_line)
        self.title_list = self.query_one(Title_list)
        self.recipients_label = self.query_one("#notar_recipients", Static)
        self.text_label = self.query_one("#notar_text", Static)
        self.status_label = self.query_one("#notar_status", Static)
        self.title_list.focus()
        self.app.notar = self
        self.show_selected()

    def on_screen_resume(self) -> None:
        self.app.tick()

    @property
    def watching_seats(self) -> list[str]:
        return [name for name, watching in self.app.seats if watching]

    def show_selected(self) -> None:
        """Shows the selected message, and the seats it would go to right now."""
        seats = self.watching_seats
        if seats:
            self.recipients_label.update(f"to {len(seats)} watching seat{'' if len(seats) == 1 else 's'}: {', '.join(seats)}")
        else:
            self.recipients_label.update("nobody is watching right now")
        self.text_label.update(self.app.NOTAR_messages[self.title_list.selected].text)

    def action_move(self, step: int) -> None:
        self.title_list.move(step)
        self.show_selected()

    def action_send(self) -> None:
        if self.sending:
            return
        seats = self.watching_seats
        message = self.app.NOTAR_messages[self.title_list.selected]
        if not seats:
            self.status_label.update("nobody is watching, so nothing was sent")
            return
        self.sending = True
        self.status_label.update(f"sending to {len(seats)} seat{'' if len(seats) == 1 else 's'} ...")
        self.run_worker(lambda: self.send_in_background(message, seats), thread=True, group="notar")

    def send_in_background(self, message: NOTAR_message, seats: list[str]) -> None:
        failures = []
        for seat in seats:
            result = send_mail(seat, message.text)
            if result.returncode != 0:
                failures.append((seat, (result.stdout + result.stderr).decode("utf-8", "replace").strip() or f"exit code {result.returncode}"))
        self.app.post(self.finish_send, message, seats, failures)

    def finish_send(self, message: NOTAR_message, seats: list[str], failures: list[tuple[str, str]]) -> None:
        """Reports how many seats got the message, and echoes it into Rabenschnack."""
        self.sending = False
        sent_count = len(seats) - len(failures)
        status = f"{clock_text()}  {message.title}: sent to {sent_count} of {len(seats)}"
        if failures:
            status += "; not to " + ", ".join(f"{seat} ({reason})" for seat, reason in failures)
        self.status_label.update(status)
        self.app.rabenschnack.add_note(f"{clock_text()}  -> NOTAR {message.title}, {sent_count} of {len(seats)} seats", message.text, sent=True)

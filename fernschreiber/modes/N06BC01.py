"""N06BC01, on F4: Wally marks the seats to wake, and one mail asks the hallmaster to wake them."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

import settings
from calm_comms import send_mail
from Widgets import Rule_line, Seat_picker, clock_text


def wake_mail(seats: list[str]) -> str:
    """The mail the hallmaster expects: the fixed first line, then one seat per line, nothing else."""
    return "\n".join([settings.N06BC01_FIRST_LINE, *seats])


class N06BC01_screen(Screen):
    """N06BC01: the seats to wake, the mail as it will go out, and one send to the hallmaster."""

    BINDINGS = [
        Binding("ctrl+enter", "send", show=False, priority=True),
        Binding("up", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
        Binding("space", "toggle", show=False),
        Binding("escape", "app.switch_mode('rabenschnack')", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.sending = False
        self.hallmaster_state = "missing"

    def compose(self) -> ComposeResult:
        yield Rule_line(left="N06BC01", right=clock_text(), id="top_rule", classes="rule")
        with Horizontal(id="wake_main"):
            yield Seat_picker(id="wake_seats")
            with VerticalScroll(id="wake_preview"):
                yield Static("", markup=False, id="wake_recipient")
                yield Static("", markup=False, id="wake_mail")
        yield Rule_line(junction=settings.WAKE_PANE_WIDTH - 1, id="middle_rule", classes="rule")
        yield Static("ready", markup=False, id="wake_status")
        yield Rule_line(left=settings.N06BC01_KEY_HINTS, id="bottom_rule", classes="rule")

    def on_mount(self) -> None:
        self.top_rule = self.query_one("#top_rule", Rule_line)
        self.picker = self.query_one(Seat_picker)
        self.recipient_label = self.query_one("#wake_recipient", Static)
        self.mail_label = self.query_one("#wake_mail", Static)
        self.status_label = self.query_one("#wake_status", Static)
        self.picker.focus()
        self.app.wake = self
        self.show_seats(self.app.seats)

    def on_screen_resume(self) -> None:
        self.app.tick()

    def show_seats(self, seats: list[tuple[str, bool]]) -> None:
        """Takes the seats without the hallmaster, who gets the mail, and notes whether the hallmaster is watching."""
        hallmaster = [watching for name, watching in seats if name == settings.HALLMASTER_SEAT]
        self.hallmaster_state = "missing" if not hallmaster else "watching" if hallmaster[0] else "not watching"
        self.picker.set_seats([(name, watching) for name, watching in seats if name != settings.HALLMASTER_SEAT])
        self.show_mail()

    def show_mail(self) -> None:
        """Shows the mail exactly as it will go out, and to whom."""
        recipient = {
            "watching": f"to {settings.HALLMASTER_SEAT}, watching",
            "not watching": f"to {settings.HALLMASTER_SEAT}, not watching: the mail waits for them",
            "missing": f"to {settings.HALLMASTER_SEAT}, a seat not found in Hrafnsmal",
        }[self.hallmaster_state]
        self.recipient_label.update(recipient)
        marked = self.picker.marked
        self.mail_label.update(wake_mail(marked) if marked else f"{settings.N06BC01_FIRST_LINE}\n(no seat marked yet)")

    def action_move(self, step: int) -> None:
        self.picker.move(step)

    def action_toggle(self) -> None:
        self.picker.toggle()
        self.show_mail()

    def action_send(self) -> None:
        if self.sending:
            return
        marked = self.picker.marked
        if not marked:
            self.status_label.update("no seat marked, so nothing was sent")
            return
        self.sending = True
        self.status_label.update(f"sending to {settings.HALLMASTER_SEAT} ...")
        text = wake_mail(marked)
        self.run_worker(lambda: self.send_in_background(text, marked), thread=True, group="n06bc01")

    def send_in_background(self, text: str, seats: list[str]) -> None:
        result = send_mail(settings.HALLMASTER_SEAT, text)
        output = (result.stdout + result.stderr).decode("utf-8", "replace").strip()
        self.app.post(self.finish_send, text, seats, result.returncode == 0, output)

    def finish_send(self, text: str, seats: list[str], sent: bool, output: str) -> None:
        """Reports the send and echoes it into Rabenschnack; a failed send keeps the marks and says why."""
        self.sending = False
        if not sent:
            self.status_label.update(f"{clock_text()}  not sent: {output or 'calm-comms gave no reason'}")
            return
        self.status_label.update(f"{clock_text()}  sent to {settings.HALLMASTER_SEAT}: {len(seats)} seat{'' if len(seats) == 1 else 's'} to wake")
        self.picker.clear_marks()
        self.show_mail()
        self.app.rabenschnack.add_note(f"{clock_text()}  -> {settings.HALLMASTER_SEAT}, N06BC01", text, sent=True)

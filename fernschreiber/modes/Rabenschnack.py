"""Rabenschnack, on F1: the seats, the own inbox and the input."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static, TextArea

import settings
from calm_comms import send_mail
from Mail import Mail
from Widgets import Message_area, Rule_line, Seat_picker, clock_text


class Rabenschnack_screen(Screen):
    """Rabenschnack: the seats, the own inbox and the input."""

    BINDINGS = [
        Binding("ctrl+enter", "send", show=False, priority=True),
        Binding("pageup", "scroll_inbox(-1)", show=False, priority=True),
        Binding("pagedown", "scroll_inbox(1)", show=False, priority=True),
        Binding("space", "mark('toggle')", show=False),
        Binding("a", "mark('watching')", show=False),
        Binding("n", "mark('none')", show=False),
        Binding("escape", "focus_input", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.sending = False

    def compose(self) -> ComposeResult:
        yield Rule_line(left=settings.TITLE, right=clock_text(), id="top_rule", classes="rule")
        with Horizontal(id="main"):
            with VerticalScroll(id="seats_scroll", can_focus=False):
                yield Seat_picker("seats", id="seats")
            with VerticalScroll(id="inbox"):
                yield Static(settings.OWN_SEAT, markup=False, id="inbox_title")
        yield Rule_line(junction=settings.SEAT_PANE_WIDTH - 1, id="middle_rule", classes="rule")
        with Horizontal(id="input_row"):
            yield Static("", markup=False, id="prompt")
            yield Message_area(id="message", soft_wrap=True, show_line_numbers=False, highlight_cursor_line=False)
        yield Rule_line(left=settings.KEY_HINTS, id="bottom_rule", classes="rule")

    def on_mount(self) -> None:
        self.top_rule = self.query_one("#top_rule", Rule_line)
        self.seat_list = self.query_one(Seat_picker)
        self.inbox = self.query_one("#inbox", VerticalScroll)
        self.prompt_label = self.query_one("#prompt", Static)
        self.message_area = self.query_one("#message", TextArea)
        self.update_prompt()
        self.message_area.focus()
        # Anchored, the inbox stays at the bottom as mail comes in, until Wally scrolls up.
        self.inbox.anchor()
        self.app.start_rabenschnack(self)

    def on_screen_resume(self) -> None:
        self.app.tick()

    # The seats

    def show_seats(self, seats: list[tuple[str, bool]]) -> None:
        self.seat_list.set_seats(seats)
        self.update_prompt()

    @property
    def recipients(self) -> list[str]:
        """The marked seats; without marks, the one under the cursor."""
        if self.seat_list.marked:
            return self.seat_list.marked
        return [self.seat_list.selected_name] if self.seat_list.selected_name else []

    def update_prompt(self) -> None:
        marked = self.seat_list.marked
        target = f"{len(marked)} marked" if marked else self.seat_list.selected_name or "..."
        self.prompt_label.update(f" to {target}: ")

    def seat_moved(self) -> None:
        """Called by the seat list after Up or Down: the prompt names the seat under the cursor."""
        self.update_prompt()

    def action_mark(self, how: str) -> None:
        """Space, A and N act on the seats only while the seats have the focus."""
        if not self.seat_list.has_focus:
            return
        {"toggle": self.seat_list.toggle, "watching": self.seat_list.mark_watching, "none": self.seat_list.clear_marks}[how]()
        self.update_prompt()

    # Keys

    def action_focus_input(self) -> None:
        self.message_area.focus()

    def action_scroll_inbox(self, step: int) -> None:
        if step < 0:
            self.inbox.scroll_page_up(animate=False)
        else:
            self.inbox.scroll_page_down(animate=False)

    # The inbox

    @staticmethod
    def entry_widgets(head: str, body: str, sent: bool = False) -> list[Static]:
        return [
            Static(head, markup=False, classes="mail_head"),
            Static(body, markup=False, classes="mail_body sent" if sent else "mail_body"),
        ]

    def add_mails(self, mails: list[Mail], ring: bool) -> None:
        """Shows the mails to Wally; group mails stay in their thread on F2, but still ring the bell."""
        if not mails:
            return
        widgets = []
        for mail in mails:
            if not mail.group:
                widgets += self.entry_widgets(f"{mail.time}  {mail.sender}", mail.text)
        if widgets:
            self.inbox.mount_all(widgets)
        if ring:
            if widgets:
                # New mail brings the view back down, even when Wally was reading further up.
                self.inbox.scroll_end(animate=False)
            self.app.bell()

    def add_note(self, head: str, body: str, sent: bool = False) -> None:
        self.inbox.mount_all(self.entry_widgets(head, body, sent))
        self.inbox.scroll_end(animate=False)

    # Sending

    def action_send(self) -> None:
        text = self.message_area.text.strip()
        recipients = self.recipients
        if self.sending or not text or not recipients:
            return
        self.sending = True
        # Locked until calm-comms comes back from every seat.
        self.message_area.read_only = True
        self.run_worker(lambda: self.send_in_background(recipients, text), thread=True, group="send")

    def send_in_background(self, recipients: list[str], text: str) -> None:
        reached = []
        failures = []
        for seat in recipients:
            result = send_mail(seat, text)
            output = (result.stdout + result.stderr).decode("utf-8", "replace").strip()
            if result.returncode == 0:
                # send answers with the target's mailbox, such as `otis_builder 📬`.
                reached.append(output or seat)
            else:
                failures.append((seat, output or "calm-comms gave no reason"))
        self.app.post(self.finish_send, text, reached, failures)

    def finish_send(self, text: str, reached: list[str], failures: list[tuple[str, str]]) -> None:
        """Echoes the mail with each reached seat's mailbox; when a seat refused it, the text stays in the input and the reason shows."""
        self.sending = False
        self.message_area.read_only = False
        if reached:
            self.add_note(f"{clock_text()}  -> {', '.join(reached)}", text, sent=True)
        if failures:
            self.add_note(f"{clock_text()}  fernschreiber", "\n".join(f"not sent to {seat}: {reason}" for seat, reason in failures))
        else:
            self.message_area.clear()

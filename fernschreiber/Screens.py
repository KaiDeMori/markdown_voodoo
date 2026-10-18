"""fernschreiber's screens, one per mode: Rabenschnack on F1, the help on F2, NOTAR on F3."""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static, TextArea

import settings
from calm_comms import send_mail
from Mail import Mail
from NOTAR import NOTAR_message
from Widgets import Message_area, Rule_line, Seat_list, Title_list


def clock_text() -> str:
    return datetime.now().strftime("%H:%M")


class Rabenschnack_screen(Screen):
    """Rabenschnack: the seats, the own inbox and the input."""

    BINDINGS = [
        Binding("ctrl+enter", "send", show=False, priority=True),
        Binding("pageup", "scroll_inbox(-1)", show=False, priority=True),
        Binding("pagedown", "scroll_inbox(1)", show=False, priority=True),
        # Up and Down reach the screen only when the focused pane leaves them alone, which the seats do.
        Binding("up", "move_seat(-1)", show=False),
        Binding("down", "move_seat(1)", show=False),
        Binding("escape", "focus_input", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.sending = False

    def compose(self) -> ComposeResult:
        yield Rule_line(left=settings.TITLE, right=clock_text(), id="top_rule", classes="rule")
        with Horizontal(id="main"):
            yield Seat_list(id="seats")
            with VerticalScroll(id="inbox"):
                yield Static(settings.OWN_SEAT, markup=False, id="inbox_title")
        yield Rule_line(junction=settings.SEAT_PANE_WIDTH - 1, id="middle_rule", classes="rule")
        with Horizontal(id="input_row"):
            yield Static("", markup=False, id="prompt")
            yield Message_area(id="message", soft_wrap=True, show_line_numbers=False, highlight_cursor_line=False)
        yield Rule_line(left=settings.KEY_HINTS, id="bottom_rule", classes="rule")

    def on_mount(self) -> None:
        self.top_rule = self.query_one("#top_rule", Rule_line)
        self.seat_list = self.query_one(Seat_list)
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

    def update_prompt(self) -> None:
        self.prompt_label.update(f" to {self.seat_list.selected_name or '...'}: ")

    def action_move_seat(self, step: int) -> None:
        self.seat_list.move(step)
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
        if not mails:
            return
        widgets = []
        for mail in mails:
            widgets += self.entry_widgets(f"{mail.time}  {mail.sender}", mail.text)
        self.inbox.mount_all(widgets)
        if ring:
            # New mail brings the view back down, even when Wally was reading further up.
            self.inbox.scroll_end(animate=False)
            self.app.bell()

    def add_note(self, head: str, body: str, sent: bool = False) -> None:
        self.inbox.mount_all(self.entry_widgets(head, body, sent))
        self.inbox.scroll_end(animate=False)

    # Sending

    def action_send(self) -> None:
        text = self.message_area.text.strip()
        target = self.seat_list.selected_name
        if self.sending or not text or not target:
            return
        self.sending = True
        # Locked until calm-comms comes back.
        self.message_area.read_only = True
        self.run_worker(lambda: self.send_in_background(target, text), thread=True, group="send")

    def send_in_background(self, target: str, text: str) -> None:
        result = send_mail(target, text)
        output = (result.stdout + result.stderr).decode("utf-8", "replace").strip()
        self.app.post(self.finish_send, target, text, result.returncode == 0, output)

    def finish_send(self, target: str, text: str, sent: bool, output: str) -> None:
        """Echoes a sent mail and clears the input; a failed send keeps the text and shows why."""
        self.sending = False
        self.message_area.read_only = False
        if sent:
            self.add_note(f"{clock_text()}  -> {target}", text, sent=True)
            self.message_area.clear()
        else:
            self.add_note(f"{clock_text()}  fernschreiber", f"not sent to {target}: {output or 'calm-comms gave no reason'}")


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


class Help_screen(Screen):
    """The help: every key, in a mode of its own."""

    BINDINGS = [
        Binding("escape", "app.switch_mode('rabenschnack')", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Rule_line(left="HELP", right=clock_text(), id="top_rule", classes="rule")
        yield Static(settings.HELP_TEXT, markup=False, id="help_text")
        yield Rule_line(left=settings.KEY_HINTS, id="bottom_rule", classes="rule")

    def on_mount(self) -> None:
        self.top_rule = self.query_one("#top_rule", Rule_line)

    def on_screen_resume(self) -> None:
        self.app.tick()

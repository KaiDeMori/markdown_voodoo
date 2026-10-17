"""fernschreiber: a calm terminal for Wally's Rabenschnack mail."""

import subprocess
import threading
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static, TextArea

import settings
from calm_comms import read_seats, run_calm_comms, send_mail, start_calm_comms
from Mail import Mail, already_read_files, read_mail
from Widgets import Help_screen, Message_area, Rule_line, Seat_list


class Fernschreiber(App):
    TITLE = "fernschreiber"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("ctrl+enter", "send", show=False, priority=True),
        Binding("pageup", "scroll_inbox(-1)", show=False, priority=True),
        Binding("pagedown", "scroll_inbox(1)", show=False, priority=True),
        # Up and Down reach the app only when the focused pane leaves them alone, which the seats do.
        Binding("up", "move_seat(-1)", show=False),
        Binding("down", "move_seat(1)", show=False),
        Binding("escape", "focus_input", show=False),
        Binding("f1", "help", show=False),
    ]
    CSS = f"""
    Screen {{ background: {settings.BACKGROUND_COLOR}; color: {settings.TEXT_COLOR}; }}
    .rule {{ height: 1; color: {settings.FRAME_COLOR}; }}
    #main {{ height: 1fr; }}
    #seats {{ width: {settings.SEAT_PANE_WIDTH}; height: 1fr; border-left: ascii {settings.FRAME_COLOR}; border-right: ascii {settings.FRAME_COLOR}; }}
    #inbox {{ width: 1fr; height: 1fr; padding: 0 1; border-right: ascii {settings.FRAME_COLOR}; scrollbar-size: 0 0; }}
    #inbox_title {{ color: {settings.DIM_COLOR}; }}
    #inbox:focus #inbox_title {{ color: {settings.FOCUS_COLOR}; text-style: bold; }}
    .mail_head {{ color: {settings.DIM_COLOR}; margin-top: 1; }}
    .mail_body {{ padding-left: 2; }}
    .sent {{ color: {settings.DIM_COLOR}; }}
    #input_row {{ height: {settings.INPUT_LINES}; border-left: ascii {settings.FRAME_COLOR}; border-right: ascii {settings.FRAME_COLOR}; }}
    #prompt {{ width: auto; height: {settings.INPUT_LINES}; color: {settings.DIM_COLOR}; }}
    #prompt.focused {{ color: {settings.FOCUS_COLOR}; text-style: bold; }}
    #message {{ width: 1fr; height: {settings.INPUT_LINES}; padding: 0; border: none; background: {settings.BACKGROUND_COLOR}; color: {settings.TEXT_COLOR}; }}
    #message:focus {{ border: none; }}
    #message.-read-only {{ color: {settings.DIM_COLOR}; }}
    #message.-read-only .text-area--cursor {{ background: {settings.BACKGROUND_COLOR}; color: {settings.DIM_COLOR}; text-style: none; }}
    #help_screen {{ align: center middle; }}
    #help {{ width: auto; height: auto; padding: 0 1; border: ascii {settings.FRAME_COLOR}; background: {settings.BACKGROUND_COLOR}; color: {settings.TEXT_COLOR}; }}
    """

    def __init__(self) -> None:
        super().__init__()
        self.watcher: subprocess.Popen | None = None
        self.watcher_lock = threading.Lock()
        self.stopping = False
        self.sending = False

    def compose(self) -> ComposeResult:
        yield Rule_line(left=settings.TITLE, right=self.clock_text(), id="top_rule", classes="rule")
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
        # Kept at hand, so mail and seats still find their panes while the help is open.
        self.top_rule = self.query_one("#top_rule", Rule_line)
        self.seat_list = self.query_one(Seat_list)
        self.inbox = self.query_one("#inbox", VerticalScroll)
        self.prompt_label = self.query_one("#prompt", Static)
        self.message_area = self.query_one("#message", TextArea)
        self.update_prompt()
        self.message_area.focus()
        # Anchored, the inbox stays at the bottom as mail comes in, until Wally scrolls up.
        self.inbox.anchor()
        self.set_interval(5, self.tick)
        self.refresh_seats()
        self.set_interval(settings.SEAT_REFRESH_SECONDS, self.refresh_seats)
        self.run_worker(self.watch_loop, thread=True, group="watch")

    def on_unmount(self) -> None:
        self.stop_watching()

    async def action_quit(self) -> None:
        self.stop_watching()
        self.exit()

    @property
    def help_is_open(self) -> bool:
        return len(self.screen_stack) > 1

    # The clock

    def clock_text(self) -> str:
        return datetime.now().strftime("%H:%M")

    def tick(self) -> None:
        clock = self.clock_text()
        if self.top_rule.right != clock:
            self.top_rule.right = clock
            self.top_rule.redraw()

    # Keys

    def action_focus_input(self) -> None:
        self.message_area.focus()

    def action_help(self) -> None:
        if not self.help_is_open:
            self.push_screen(Help_screen(id="help_screen"))

    def action_scroll_inbox(self, step: int) -> None:
        if step < 0:
            self.inbox.scroll_page_up(animate=False)
        else:
            self.inbox.scroll_page_down(animate=False)

    # The seats

    def refresh_seats(self) -> None:
        self.run_worker(self.load_seats, thread=True, exclusive=True, group="seats")

    def load_seats(self) -> None:
        seats = read_seats()
        if seats is not None:
            self.post(self.show_seats, seats)

    def show_seats(self, seats: list[tuple[str, bool]]) -> None:
        self.seat_list.set_seats(seats)
        self.update_prompt()

    def update_prompt(self) -> None:
        self.prompt_label.update(f" to {self.seat_list.selected_name or '...'}: ")

    def action_move_seat(self, step: int) -> None:
        if not self.help_is_open:
            self.seat_list.move(step)
            self.update_prompt()

    # The inbox

    def watch_loop(self) -> None:
        """Shows the history, then keeps the own seat watched: start `on`, deliver what is waiting, wait for the watcher, again."""
        self.post(self.add_mails, [read_mail(file) for file in already_read_files()[-settings.HISTORY_MAIL_COUNT:]], False)
        while True:
            with self.watcher_lock:
                if self.stopping:
                    return
                self.watcher = start_calm_comms("on", settings.OWN_SEAT, str(settings.WATCH_MINUTES))
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
            result = run_calm_comms("inbox", settings.OWN_SEAT, str(settings.INBOX_MAIL_LIMIT))
            output = result.stdout.decode("utf-8", "replace")
            mails = [read_mail(file) for file in already_read_files() if file.name not in before]
            if result.returncode != 0:
                mails.append(Mail(self.clock_text(), "fernschreiber", output.strip() or f"inbox stopped with exit code {result.returncode}"))
            if mails:
                self.post(self.add_mails, mails, True)
            if result.returncode != 0 or " more waiting: " not in output:
                return

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
            self.bell()

    def add_note(self, head: str, body: str, sent: bool = False) -> None:
        self.inbox.mount_all(self.entry_widgets(head, body, sent))
        self.inbox.scroll_end(animate=False)

    def stop_watching(self) -> None:
        """Stops the running watcher and deletes watching.md, which a stopped watcher leaves behind."""
        with self.watcher_lock:
            if self.stopping:
                return
            self.stopping = True
            if self.watcher is not None and self.watcher.poll() is None:
                self.watcher.terminate()
        start_calm_comms("off", settings.OWN_SEAT)

    def post(self, callback, *arguments) -> None:
        """Hands a call from a worker thread to the app, unless the app is already on its way out."""
        if self.stopping:
            return
        try:
            self.call_from_thread(callback, *arguments)
        except RuntimeError:
            pass

    # Sending

    def action_send(self) -> None:
        text = self.message_area.text.strip()
        target = self.seat_list.selected_name
        if self.help_is_open or self.sending or not text or not target:
            return
        self.sending = True
        # Locked until calm-comms comes back, so the lock lasts exactly as long as its write throttle.
        self.message_area.read_only = True
        self.run_worker(lambda: self.send_in_background(target, text), thread=True, group="send")

    def send_in_background(self, target: str, text: str) -> None:
        result = send_mail(target, text)
        output = (result.stdout + result.stderr).decode("utf-8", "replace").strip()
        self.post(self.finish_send, target, text, result.returncode == 0, output)

    def finish_send(self, target: str, text: str, sent: bool, output: str) -> None:
        """Echoes a sent mail and clears the input; a failed send keeps the text and shows why."""
        self.sending = False
        self.message_area.read_only = False
        if sent:
            self.add_note(f"{self.clock_text()}  -> {target}", text, sent=True)
            self.message_area.clear()
        else:
            self.add_note(f"{self.clock_text()}  fernschreiber", f"not sent to {target}: {output or 'calm-comms gave no reason'}")


if __name__ == "__main__":
    Fernschreiber().run()

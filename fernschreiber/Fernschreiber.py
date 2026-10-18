"""fernschreiber: a calm terminal for Wally's Rabenschnack mail."""

import argparse
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Static, TextArea

import settings
from calm_comms import read_seats, run_calm_comms, send_mail, start_watcher
from Color_theme import Color_theme, load_color_theme
from Mail import Mail, already_read_files, read_mail
from Widgets import Help_screen, Message_area, Rule_line, Seat_list


def build_css(color_theme: Color_theme | None) -> str:
    """The layout always; colors only from a theme file, so without one, Textual's own defaults show."""
    css = f"""
    .rule {{ height: 1; }}
    #main {{ height: 1fr; }}
    #seats {{ width: {settings.SEAT_PANE_WIDTH}; height: 1fr; border-left: ascii; border-right: ascii; }}
    #inbox {{ width: 1fr; height: 1fr; padding: 0 1; border-right: ascii; scrollbar-size: 0 0; }}
    #inbox:focus #inbox_title {{ text-style: bold; }}
    .mail_head {{ margin-top: 1; }}
    .mail_body {{ padding-left: 2; }}
    #input_row {{ height: {settings.INPUT_LINES}; border-left: ascii; border-right: ascii; }}
    #prompt {{ width: auto; height: {settings.INPUT_LINES}; }}
    #prompt.focused {{ text-style: bold; }}
    #message {{ width: 1fr; height: {settings.INPUT_LINES}; padding: 0; border: none; }}
    #message:focus {{ border: none; }}
    #message.-read-only {{ color: $text-muted; }}
    #message.-read-only .text-area--cursor {{ background: transparent; color: $text-muted; text-style: none; }}
    #help_screen {{ align: center middle; }}
    #help {{ width: auto; height: auto; padding: 0 1; border: ascii; background: $surface; }}
    """
    if color_theme is None:
        return css
    background, text, dim, frame, focus = color_theme.background, color_theme.text, color_theme.dim, color_theme.frame, color_theme.focus
    return css + f"""
    Screen {{ background: {background}; color: {text}; }}
    .rule {{ color: {frame}; }}
    #seats {{ border-left: ascii {frame}; border-right: ascii {frame}; }}
    #inbox {{ border-right: ascii {frame}; }}
    #inbox_title {{ color: {dim}; }}
    #inbox:focus #inbox_title {{ color: {focus}; }}
    .mail_head {{ color: {dim}; }}
    .sent {{ color: {dim}; }}
    #input_row {{ border-left: ascii {frame}; border-right: ascii {frame}; }}
    #prompt {{ color: {dim}; }}
    #prompt.focused {{ color: {focus}; }}
    #message {{ background: {background}; color: {text}; }}
    #message.-read-only {{ color: {dim}; }}
    #message.-read-only .text-area--cursor {{ color: {dim}; }}
    #help {{ border: ascii {frame}; background: {background}; color: {text}; }}
    """


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
    def __init__(self, color_theme: Color_theme | None = None) -> None:
        super().__init__()
        self.color_theme = color_theme
        # Textual reads CSS only at startup, so each instance can bring its own.
        self.CSS = build_css(color_theme)
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
        if self.color_theme is not None:
            self.theme = self.color_theme.base
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
        """Shows the history and what is waiting, then delivers mail for every line the watcher prints, until `off` stops it."""
        self.post(self.add_mails, [read_mail(file) for file in already_read_files()[-settings.HISTORY_MAIL_COUNT:]], False)
        with self.watcher_lock:
            if self.stopping:
                return
            self.watcher = start_watcher()
        self.deliver_mail()
        for _ in iter(self.watcher.stdout.readline, b""):
            if self.stopping:
                return
            self.deliver_mail()
        return_code = self.watcher.wait()
        if not self.stopping:
            self.post(self.add_mails, [Mail(self.clock_text(), "fernschreiber", f"The watcher stopped with exit code {return_code}; fernschreiber no longer watches.")], True)

    def deliver_mail(self) -> None:
        """Runs `inbox`, which in terminal mode hands out everything waiting, and shows the mails it moved into already_read."""
        before = {file.name for file in already_read_files()}
        result = run_calm_comms("inbox", settings.OWN_SEAT)
        mails = [read_mail(file) for file in already_read_files() if file.name not in before]
        if result.returncode != 0:
            output = result.stdout.decode("utf-8", "replace").strip()
            mails.append(Mail(self.clock_text(), "fernschreiber", output or f"inbox stopped with exit code {result.returncode}"))
        if mails:
            self.post(self.add_mails, mails, True)

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
        """Closes the watcher's stdin; the watcher leaves at once and removes its marker."""
        with self.watcher_lock:
            if self.stopping:
                return
            self.stopping = True
            if self.watcher is not None:
                self.watcher.stdin.close()

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


def main() -> None:
    parser = argparse.ArgumentParser(description="fernschreiber: a calm terminal for Wally's Rabenschnack mail.")
    parser.add_argument("theme_file", nargs="?", type=Path, help="a color theme, such as themes/paper.toml; without one, Textual's defaults show")
    arguments = parser.parse_args()
    color_theme = load_color_theme(arguments.theme_file) if arguments.theme_file else None
    app = Fernschreiber(color_theme)
    app.run()
    sys.exit(app.return_code)


if __name__ == "__main__":
    main()

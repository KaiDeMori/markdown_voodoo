"""fernschreiber: a calm terminal for Wally's Rabenschnack mail."""

import argparse
import subprocess
import sys
import threading
from pathlib import Path

from textual.app import App
from textual.binding import Binding

import settings
from calm_comms import read_seats, run_calm_comms, start_watcher, stop_watcher
from Color_theme import Color_theme, load_color_theme
from Mail import Mail, already_read_files, read_mail, recent_direct_mails
from modes.Catalog import Catalog_screen
from modes.Groups import Groups_screen
from modes.Help import Help_screen
from modes.N06BC01 import N06BC01_screen
from modes.NOTAR import NOTAR_screen, load_NOTAR_messages
from modes.Rabenschnack import Rabenschnack_screen
from Widgets import clock_text


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
    #help_text {{ height: 1fr; padding: 1 2; border-left: ascii; border-right: ascii; }}
    #notar_main {{ height: 1fr; }}
    #notar_titles {{ width: {settings.SEAT_PANE_WIDTH}; height: 1fr; border-left: ascii; border-right: ascii; }}
    #notar_preview {{ width: 1fr; height: 1fr; padding: 0 1; border-right: ascii; scrollbar-size: 0 0; }}
    #notar_text {{ margin-top: 1; }}
    #notar_status {{ height: 1; padding: 0 1; border-left: ascii; border-right: ascii; }}
    #wake_main {{ height: 1fr; }}
    #wake_seats {{ width: {settings.SEAT_PANE_WIDTH}; height: 1fr; border-left: ascii; border-right: ascii; }}
    #wake_preview {{ width: 1fr; height: 1fr; padding: 0 1; border-right: ascii; scrollbar-size: 0 0; }}
    #wake_mail {{ margin-top: 1; }}
    #wake_status {{ height: 1; padding: 0 1; border-left: ascii; border-right: ascii; }}
    #catalog_entries {{ height: 1fr; border-left: ascii; border-right: ascii; }}
    #catalog_input_row {{ height: 1; border-left: ascii; border-right: ascii; }}
    #catalog_prompt {{ width: auto; }}
    #catalog_input {{ width: 1fr; height: 1; padding: 0; border: none; }}
    #catalog_input:focus {{ border: none; }}
    #catalog_status {{ height: 1; padding: 0 1; border-left: ascii; border-right: ascii; }}
    #groups_main {{ height: 1fr; }}
    #group_list {{ width: {settings.SEAT_PANE_WIDTH}; height: 1fr; border-left: ascii; border-right: ascii; }}
    #group_thread {{ width: 1fr; height: 1fr; padding: 0 1; border-right: ascii; scrollbar-size: 0 0; }}
    #group_input_row {{ height: {settings.INPUT_LINES}; border-left: ascii; border-right: ascii; }}
    #group_prompt {{ width: auto; height: {settings.INPUT_LINES}; }}
    #group_prompt.focused {{ text-style: bold; }}
    #group_message {{ width: 1fr; height: {settings.INPUT_LINES}; padding: 0; border: none; }}
    #group_message:focus {{ border: none; }}
    #group_message.-read-only {{ color: $text-muted; }}
    #group_message.-read-only .text-area--cursor {{ background: transparent; color: $text-muted; text-style: none; }}
    #group_status {{ height: 1; padding: 0 1; border-left: ascii; border-right: ascii; }}
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
    #help_text {{ border-left: ascii {frame}; border-right: ascii {frame}; }}
    #notar_titles {{ border-left: ascii {frame}; border-right: ascii {frame}; }}
    #notar_preview {{ border-right: ascii {frame}; }}
    #notar_recipients {{ color: {dim}; }}
    #notar_status {{ border-left: ascii {frame}; border-right: ascii {frame}; color: {dim}; }}
    #wake_seats {{ border-left: ascii {frame}; border-right: ascii {frame}; }}
    #wake_preview {{ border-right: ascii {frame}; }}
    #wake_recipient {{ color: {dim}; }}
    #wake_status {{ border-left: ascii {frame}; border-right: ascii {frame}; color: {dim}; }}
    #catalog_entries {{ border-left: ascii {frame}; border-right: ascii {frame}; }}
    #catalog_input_row {{ border-left: ascii {frame}; border-right: ascii {frame}; }}
    #catalog_prompt {{ color: {dim}; }}
    #catalog_input {{ background: {background}; color: {text}; }}
    #catalog_status {{ border-left: ascii {frame}; border-right: ascii {frame}; color: {dim}; }}
    #group_list {{ border-left: ascii {frame}; border-right: ascii {frame}; }}
    #group_thread {{ border-right: ascii {frame}; }}
    #thread_title {{ color: {dim}; }}
    #group_input_row {{ border-left: ascii {frame}; border-right: ascii {frame}; }}
    #group_prompt {{ color: {dim}; }}
    #group_prompt.focused {{ color: {focus}; }}
    #group_message {{ background: {background}; color: {text}; }}
    #group_message.-read-only {{ color: {dim}; }}
    #group_message.-read-only .text-area--cursor {{ color: {dim}; }}
    #group_status {{ border-left: ascii {frame}; border-right: ascii {frame}; color: {dim}; }}
    """


class Fernschreiber(App):
    """The frame around the modes; the clock, the seats and the watcher live here, so they keep running in every mode."""

    TITLE = "fernschreiber"
    ENABLE_COMMAND_PALETTE = False
    MODES = {
        "rabenschnack": Rabenschnack_screen,
        "help": Help_screen,
        "notar": NOTAR_screen,
        "n06bc01": N06BC01_screen,
        "catalog": Catalog_screen,
        "groups": Groups_screen,
    }
    DEFAULT_MODE = "rabenschnack"
    # With priority, the mode keys win over a focused widget's own bindings, such as F6 and F7 in a TextArea.
    BINDINGS = [
        Binding("f1", "switch_mode('rabenschnack')", show=False, priority=True),
        Binding("f2", "switch_mode('groups')", show=False, priority=True),
        Binding("f3", "switch_mode('notar')", show=False, priority=True),
        Binding("f4", "switch_mode('n06bc01')", show=False, priority=True),
        Binding("f5", "switch_mode('catalog')", show=False, priority=True),
        Binding("f6", "switch_mode('help')", show=False, priority=True),
    ]

    def __init__(self, color_theme: Color_theme | None = None) -> None:
        super().__init__()
        self.color_theme = color_theme
        # Textual reads CSS only at startup, so each instance can bring its own.
        self.CSS = build_css(color_theme)
        # Read before the window opens, so a broken file stops fernschreiber right away.
        self.NOTAR_messages = load_NOTAR_messages(settings.NOTAR_MESSAGES_FILE)
        self.seats: list[tuple[str, bool]] = []
        self.rabenschnack: Rabenschnack_screen | None = None
        self.notar: NOTAR_screen | None = None
        self.wake: N06BC01_screen | None = None
        self.groups: Groups_screen | None = None
        self.watcher: subprocess.Popen | None = None
        self.watcher_lock = threading.Lock()
        self.stopping = False

    def on_mount(self) -> None:
        if self.color_theme is not None:
            self.theme = self.color_theme.base

    def start_rabenschnack(self, screen: Rabenschnack_screen) -> None:
        """Called by the Rabenschnack screen once it stands: the clock, the seats and the watcher start."""
        self.rabenschnack = screen
        self.set_interval(5, self.tick)
        self.refresh_seats()
        self.set_interval(settings.SEAT_REFRESH_SECONDS, self.refresh_seats)
        self.run_worker(self.watch_loop, thread=True, group="watch")

    def on_unmount(self) -> None:
        self.stop_watching()

    async def action_quit(self) -> None:
        self.stop_watching()
        self.exit()

    def tick(self) -> None:
        """Keeps the clock in the current mode's top line."""
        top_rule = getattr(self.screen, "top_rule", None)
        clock = clock_text()
        if top_rule is not None and top_rule.right != clock:
            top_rule.right = clock
            top_rule.redraw()

    # The seats

    def refresh_seats(self) -> None:
        self.run_worker(self.load_seats, thread=True, exclusive=True, group="seats")

    def load_seats(self) -> None:
        seats = read_seats()
        if seats is not None:
            self.post(self.show_seats, seats)

    def show_seats(self, seats: list[tuple[str, bool]]) -> None:
        self.seats = seats
        self.rabenschnack.show_seats(seats)
        if self.notar is not None:
            self.notar.show_selected()
        if self.wake is not None:
            self.wake.show_seats(seats)

    # The watcher

    def watch_loop(self) -> None:
        """Shows the history, then keeps the own seat watched: start `on`, deliver what is waiting, wait for the watcher, again."""
        self.post(self.rabenschnack.add_mails, recent_direct_mails(settings.HISTORY_MAIL_COUNT), False)
        while True:
            with self.watcher_lock:
                if self.stopping:
                    return
                self.watcher = start_watcher()
            self.deliver_mail()
            self.watcher.stdout.read()
            return_code = self.watcher.wait()
            if self.stopping:
                return
            if return_code != 0:
                self.post(self.rabenschnack.add_mails, [Mail(clock_text(), "fernschreiber", f"The watcher stopped with exit code {return_code}; fernschreiber no longer watches.")], True)
                return

    def deliver_mail(self) -> None:
        """Runs `inbox` until nothing more is waiting, and shows the mails it moved into already_read."""
        for _ in range(50):
            before = {file.name for file in already_read_files()}
            result = run_calm_comms("inbox", settings.OWN_SEAT, str(settings.INBOX_MAIL_LIMIT))
            output = result.stdout.decode("utf-8", "replace")
            mails = [read_mail(file) for file in already_read_files() if file.name not in before]
            if result.returncode != 0:
                mails.append(Mail(clock_text(), "fernschreiber", output.strip() or f"inbox stopped with exit code {result.returncode}"))
            if mails:
                self.post(self.rabenschnack.add_mails, mails, True)
                self.post(self.mail_arrived)
            if result.returncode != 0 or " more waiting: " not in output:
                return

    def mail_arrived(self) -> None:
        """A group mail lands in the own seat too, so new mail may mean a grown thread in the groups mode."""
        if self.groups is not None:
            self.groups.mail_arrived()

    def stop_watching(self) -> None:
        """Runs `off`, which stops the watcher and closes the door."""
        with self.watcher_lock:
            if self.stopping:
                return
            self.stopping = True
        stop_watcher()

    def post(self, callback, *arguments) -> None:
        """Hands a call from a worker thread to the app, unless the app is already on its way out."""
        if self.stopping:
            return
        try:
            self.call_from_thread(callback, *arguments)
        except RuntimeError:
            pass


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

"""fernschreiber: a calm terminal for Wally's Rabenschnack mail."""

import argparse
import subprocess
import sys
import threading
from pathlib import Path

from textual.app import App
from textual.binding import Binding

import settings
from calm_comms import read_seats, run_calm_comms, start_watcher
from Color_theme import Color_theme, load_color_theme
from Mail import Mail, already_read_files, read_mail
from Screens import Help_screen, Rabenschnack_screen, clock_text


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
    """


class Fernschreiber(App):
    """The frame around the modes; the clock, the seats and the watcher live here, so they keep running in every mode."""

    TITLE = "fernschreiber"
    ENABLE_COMMAND_PALETTE = False
    MODES = {
        "rabenschnack": Rabenschnack_screen,
        "help": Help_screen,
    }
    DEFAULT_MODE = "rabenschnack"
    BINDINGS = [
        Binding("f1", "switch_mode('rabenschnack')", show=False),
        Binding("f2", "switch_mode('help')", show=False),
    ]

    def __init__(self, color_theme: Color_theme | None = None) -> None:
        super().__init__()
        self.color_theme = color_theme
        # Textual reads CSS only at startup, so each instance can bring its own.
        self.CSS = build_css(color_theme)
        self.rabenschnack: Rabenschnack_screen | None = None
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
            self.post(self.rabenschnack.show_seats, seats)

    # The watcher

    def watch_loop(self) -> None:
        """Shows the history and what is waiting, then delivers mail for every line the watcher prints, until its stdin closes."""
        self.post(self.rabenschnack.add_mails, [read_mail(file) for file in already_read_files()[-settings.HISTORY_MAIL_COUNT:]], False)
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
            self.post(self.rabenschnack.add_mails, [Mail(clock_text(), "fernschreiber", f"The watcher stopped with exit code {return_code}; fernschreiber no longer watches.")], True)

    def deliver_mail(self) -> None:
        """Runs `inbox`, which in terminal mode hands out everything waiting, and shows the mails it moved into already_read."""
        before = {file.name for file in already_read_files()}
        result = run_calm_comms("inbox", settings.OWN_SEAT)
        mails = [read_mail(file) for file in already_read_files() if file.name not in before]
        if result.returncode != 0:
            output = result.stdout.decode("utf-8", "replace").strip()
            mails.append(Mail(clock_text(), "fernschreiber", output or f"inbox stopped with exit code {result.returncode}"))
        if mails:
            self.post(self.rabenschnack.add_mails, mails, True)

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

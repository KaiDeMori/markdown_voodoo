"""The help, on F6: every key, in a mode of its own."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static

import settings
from Widgets import Rule_line, clock_text


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

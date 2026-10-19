"""The catalog, on F5: calm-email's circled letters and their addresses, to see, add and remove."""

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Input, Static

import settings
from calm_email import add_entry, catalog_meta, circled, read_catalog, remove_entry
from Widgets import Rule_line, Title_list, clock_text

NOT_SET = f"{settings.CATALOG_META_VARIABLE} is not set in this terminal"


class Catalog_screen(Screen):
    """The catalog: one line per letter; A adds, Del removes after a y."""

    BINDINGS = [
        Binding("up", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
        Binding("a", "add", show=False),
        Binding("delete", "remove", show=False),
        Binding("escape", "back", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[tuple[str, str]] = []
        self.confirming: str | None = None
        self.busy = False

    def compose(self) -> ComposeResult:
        yield Rule_line(left="CATALOG", right=clock_text(), id="top_rule", classes="rule")
        yield Title_list("catalog", [], id="catalog_entries")
        yield Rule_line(id="middle_rule", classes="rule")
        with Horizontal(id="catalog_input_row"):
            yield Static(" add: ", markup=False, id="catalog_prompt")
            yield Input(placeholder="T name@example.com", id="catalog_input")
        yield Static("", markup=False, id="catalog_status")
        yield Rule_line(left=settings.CATALOG_KEY_HINTS, id="bottom_rule", classes="rule")

    def on_mount(self) -> None:
        self.top_rule = self.query_one("#top_rule", Rule_line)
        self.entry_list = self.query_one(Title_list)
        self.input = self.query_one("#catalog_input", Input)
        self.status_label = self.query_one("#catalog_status", Static)
        self.entry_list.focus()
        self.load()

    def on_screen_resume(self) -> None:
        self.app.tick()
        if hasattr(self, "entry_list"):
            self.load()

    def say(self, line: str) -> None:
        self.status_label.update(line)

    # Reading

    def load(self) -> None:
        meta = catalog_meta()
        if meta is None:
            self.show_entries(None, NOT_SET)
            return
        self.run_worker(lambda: self.app.post(self.show_entries, *read_catalog(meta)), thread=True, exclusive=True, group="catalog")

    def show_entries(self, entries: list[tuple[str, str]] | None, message: str) -> None:
        """Shows the entries; calm-email's words, such as an empty catalog or a refusal, go to the status line."""
        self.entries = entries or []
        self.entry_list.set_titles([f"{letter}  {address}" for letter, address in self.entries])
        if message:
            self.say(message)

    # Keys

    def action_move(self, step: int) -> None:
        self.entry_list.move(step)

    def action_add(self) -> None:
        if not self.busy:
            self.input.focus()

    def action_remove(self) -> None:
        if self.busy or not self.entries:
            return
        letter, address = self.entries[self.entry_list.selected]
        self.confirming = letter
        self.say(f"Remove {letter} ({address})? y/n")

    def action_back(self) -> None:
        if self.input.has_focus:
            self.input.value = ""
            self.entry_list.focus()
        else:
            self.app.switch_mode("rabenschnack")

    def on_key(self, event: events.Key) -> None:
        """While a removal waits for its answer, every key answers it: y removes, anything else keeps."""
        if self.confirming is None:
            return
        event.stop()
        event.prevent_default()
        letter, self.confirming = self.confirming, None
        if event.key == "y":
            self.change(lambda meta: remove_entry(meta, letter))
        else:
            self.say(f"{letter} stays in the catalog")

    # Changing

    def on_input_submitted(self, event: Input.Submitted) -> None:
        parts = event.value.split(maxsplit=1)
        letter = circled(parts[0]) if parts else None
        if letter is None or len(parts) < 2:
            self.say("a letter, a space, then the address, like: T name@example.com")
            return
        address = parts[1].strip()
        self.change(lambda meta: add_entry(meta, letter, address))

    def change(self, verb) -> None:
        meta = catalog_meta()
        if meta is None:
            self.say(NOT_SET)
            return
        self.busy = True
        self.run_worker(lambda: self.app.post(self.changed, *verb(meta)), thread=True, group="catalog_change")

    def changed(self, worked: bool, line: str) -> None:
        """Shows calm-email's line; after a change that worked, the input clears and the list reloads."""
        self.busy = False
        self.say(line)
        if worked:
            self.input.value = ""
            self.entry_list.focus()
        self.load()

"""The catalog, on F5: calm-email's labels, their addresses and the notes about the people behind them, to see, add, note and remove."""

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Input, Static

import settings
from calm_email import Catalog_entry, add_entry, catalog_meta, read_catalog, remove_entry, set_note
from Widgets import Rule_line, Title_list, clock_text

NOT_SET = f"{settings.CATALOG_META_VARIABLE} is not set in this terminal"
ADD_PLACEHOLDER = "T name@example.com"
NOTE_PLACEHOLDER = "a note about the person, tags like friend_of_haven; empty clears it"


class Catalog_screen(Screen):
    """The catalog: one line per label; A adds, N writes the selected label's note, Del removes after a y."""

    BINDINGS = [
        Binding("up", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
        Binding("a", "add", show=False),
        Binding("n", "note", show=False),
        Binding("delete", "remove", show=False),
        Binding("escape", "back", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[Catalog_entry] = []
        self.confirming: str | None = None
        # The label whose note the input line is writing; None while it adds.
        self.note_label: str | None = None
        self.busy = False

    def compose(self) -> ComposeResult:
        yield Rule_line(left="CATALOG", right=clock_text(), id="top_rule", classes="rule")
        yield Title_list("catalog", [], id="catalog_entries")
        yield Rule_line(id="middle_rule", classes="rule")
        with Horizontal(id="catalog_input_row"):
            yield Static(" add: ", markup=False, id="catalog_prompt")
            # Without select_on_focus, a prefilled note keeps its text, and the cursor waits at the end.
            yield Input(placeholder=ADD_PLACEHOLDER, select_on_focus=False, id="catalog_input")
        yield Static("", markup=False, id="catalog_status")
        yield Rule_line(left=settings.CATALOG_KEY_HINTS, id="bottom_rule", classes="rule")

    def on_mount(self) -> None:
        self.top_rule = self.query_one("#top_rule", Rule_line)
        self.entry_list = self.query_one(Title_list)
        self.prompt_label = self.query_one("#catalog_prompt", Static)
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

    def show_entries(self, entries: list[Catalog_entry] | None, message: str) -> None:
        """Shows the entries, each note dimmed; calm-email's words, such as an empty catalog or a refusal, go to the status line."""
        self.entries = entries or []
        color_theme = self.app.color_theme
        note_style = color_theme.dim if color_theme else "dim"
        lines = []
        for entry in self.entries:
            line = Text(f"{entry.label}  {entry.address}")
            if entry.note:
                line.append(f"  {entry.note}", style=note_style)
            lines.append(line)
        self.entry_list.set_titles(lines)
        if message:
            self.say(message)

    # Keys

    def action_move(self, step: int) -> None:
        self.entry_list.move(step)

    def action_add(self) -> None:
        if not self.busy:
            self.input_mode(None, "")
            self.input.focus()

    def action_note(self) -> None:
        if self.busy or not self.entries:
            return
        entry = self.entries[self.entry_list.selected]
        self.input_mode(entry.label, entry.note)
        self.input.focus()

    def action_remove(self) -> None:
        if self.busy or not self.entries:
            return
        entry = self.entries[self.entry_list.selected]
        self.confirming = entry.label
        self.say(f"Remove {entry.label} ({entry.address})? y/n")

    def action_back(self) -> None:
        if self.input.has_focus:
            self.input_mode(None, "")
            self.entry_list.focus()
        else:
            self.app.switch_mode("rabenschnack")

    def input_mode(self, note_label: str | None, value: str) -> None:
        """Turns the input line into the add line, or into the note line of one label."""
        self.note_label = note_label
        self.prompt_label.update(f" note for {note_label}: " if note_label else " add: ")
        self.input.placeholder = NOTE_PLACEHOLDER if note_label else ADD_PLACEHOLDER
        self.input.value = value
        self.input.cursor_position = len(value)

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
        if self.note_label is not None:
            label, note = self.note_label, event.value.strip()
            self.change(lambda meta: set_note(meta, label, note))
            return
        parts = event.value.split(maxsplit=1)
        if len(parts) < 2:
            self.say("a letter, a space, then the address, like: T name@example.com")
            return
        letter, address = parts[0], parts[1].strip()
        self.change(lambda meta: add_entry(meta, letter, address))

    def change(self, verb) -> None:
        meta = catalog_meta()
        if meta is None:
            self.say(NOT_SET)
            return
        self.busy = True
        self.run_worker(lambda: self.app.post(self.changed, *verb(meta)), thread=True, group="catalog_change")

    def changed(self, worked: bool, line: str) -> None:
        """Shows calm-email's line; after a change that worked, the input line turns back into the add line, and the list reloads."""
        self.busy = False
        self.say(line)
        if worked:
            self.input_mode(None, "")
            self.entry_list.focus()
        self.load()

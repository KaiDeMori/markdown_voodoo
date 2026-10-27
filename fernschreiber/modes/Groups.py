"""The groups, on F2: every group in group_chat, the thread of the selected one, and posting to it."""

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static, TextArea

import settings
from calm_comms import Group, group_snapshot, join_or_leave, read_groups, send_mail, thread_files
from Mail import read_mail
from Widgets import Message_area, Rule_line, Title_list, clock_text


class Groups_screen(Screen):
    """The groups: yours lit, the others dimmed with their member count; the selected group's thread; an input that posts with `group`."""

    BINDINGS = [
        Binding("ctrl+enter", "post", show=False, priority=True),
        Binding("pageup", "scroll_thread(-1)", show=False, priority=True),
        Binding("pagedown", "scroll_thread(1)", show=False, priority=True),
        # Up, Down, J and L reach the screen only when the focused pane leaves them alone, which the list does.
        Binding("up", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
        Binding("j", "membership('join')", show=False),
        Binding("l", "membership('leave')", show=False),
        Binding("escape", "focus_input", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.groups: list[Group] = []
        self.shown_group = ""
        self.last_snapshot: tuple = ()
        self.busy = False

    def compose(self) -> ComposeResult:
        yield Rule_line(left="GROUPS", right=clock_text(), id="top_rule", classes="rule")
        with Horizontal(id="groups_main"):
            yield Title_list("groups", [], id="group_list")
            with Vertical(id="group_pane"):
                with VerticalScroll(id="group_thread"):
                    yield Static("", markup=False, id="thread_title")
                # The members stay in view at the bottom, however long the thread grows.
                yield Static("", markup=False, id="group_members")
        yield Rule_line(junction=settings.SEAT_PANE_WIDTH - 1, id="middle_rule", classes="rule")
        with Horizontal(id="group_input_row"):
            yield Static("", markup=False, id="group_prompt")
            yield Message_area(id="group_message", soft_wrap=True, show_line_numbers=False, highlight_cursor_line=False)
        yield Static("", markup=False, id="group_status")
        yield Rule_line(left=settings.GROUPS_KEY_HINTS, id="bottom_rule", classes="rule")

    def on_mount(self) -> None:
        self.top_rule = self.query_one("#top_rule", Rule_line)
        self.group_list = self.query_one(Title_list)
        self.thread = self.query_one("#group_thread", VerticalScroll)
        self.thread_title = self.query_one("#thread_title", Static)
        self.members_label = self.query_one("#group_members", Static)
        self.prompt_label = self.query_one("#group_prompt", Static)
        self.message_area = self.query_one("#group_message", TextArea)
        self.status_label = self.query_one("#group_status", Static)
        self.thread.anchor()
        self.group_list.focus()
        self.app.groups = self
        self.reload()
        # A calm look every few seconds: a join, a leave or a post elsewhere shows up without a key.
        self.set_interval(settings.GROUP_REFRESH_SECONDS, self.check_for_changes)

    def on_screen_resume(self) -> None:
        self.app.tick()
        if hasattr(self, "group_list"):
            self.check_for_changes()

    def say(self, line: str) -> None:
        self.status_label.update(line)

    @property
    def selected(self) -> Group | None:
        return self.groups[self.group_list.selected] if self.groups else None

    # Reading

    def check_for_changes(self) -> None:
        """Reloads only when the groups look different from the last time they were shown."""
        if group_snapshot() != self.last_snapshot:
            self.reload()

    def reload(self) -> None:
        """Reads the groups again, keeps the cursor on the same group, and shows its thread."""
        previous = self.selected.name if self.selected else ""
        self.last_snapshot = group_snapshot()
        self.groups = read_groups()
        names = [group.name for group in self.groups]
        if previous in names:
            self.group_list.selected = names.index(previous)
        color_theme = self.app.color_theme
        dim = color_theme.dim if color_theme else "dim"
        lines = []
        for group in self.groups:
            if group.joined:
                lines.append(Text(f"# {group.name}"))
            else:
                lines.append(Text(f"# {group.name} ({len(group.members)})", style=dim))
        self.group_list.set_titles(lines)
        if not self.groups:
            self.say("no group in group_chat yet")
        self.show_thread()

    def show_thread(self) -> None:
        """Shows the selected group's last mails, if Wally is a member; otherwise who is in it, and how to join."""
        group = self.selected
        self.thread.remove_children(".thread_entry")
        self.show_members()
        if group is None:
            self.thread_title.update("")
            self.prompt_label.update(" to ...: ")
            return
        self.prompt_label.update(f" to #{group.name}: ")
        self.thread_title.update(f"#{group.name}")
        if not group.joined:
            self.thread.mount(Static("You're not in this group. J joins it.", markup=False, classes="thread_entry mail_head"))
            return
        widgets = []
        for file in thread_files(group.name)[-settings.GROUP_THREAD_COUNT:]:
            mail = read_mail(file)
            own = mail.sender == settings.OWN_SEAT
            widgets.append(Static(f"{mail.time}  {'-> ' if own else ''}{mail.sender}", markup=False, classes="thread_entry mail_head"))
            widgets.append(Static(mail.text, markup=False, classes="thread_entry mail_body sent" if own else "thread_entry mail_body"))
        if not widgets:
            widgets.append(Static("No mail in this group yet.", markup=False, classes="thread_entry mail_head"))
        self.thread.mount_all(widgets)
        self.shown_group = group.name
        self.thread.scroll_end(animate=False)

    def show_members(self) -> None:
        """The selected group's members, each with the mailbox from the last overview: who would hear a group mail soon."""
        group = self.selected
        if group is None:
            self.members_label.update("")
            return
        members = [f"{member} {self.app.mailboxes.get(member, '')}".rstrip() for member in group.members]
        self.members_label.update(", ".join(members) or "no members")

    def mail_arrived(self) -> None:
        """Called by the app whenever mail came in: the thread may have grown, so no need to wait for the next look."""
        self.reload()

    # Keys

    def action_move(self, step: int) -> None:
        self.group_list.move(step)
        self.show_thread()

    def action_focus_input(self) -> None:
        self.message_area.focus()

    def action_scroll_thread(self, step: int) -> None:
        if step < 0:
            self.thread.scroll_page_up(animate=False)
        else:
            self.thread.scroll_page_down(animate=False)

    def action_membership(self, verb: str) -> None:
        """J and L act on the group under the cursor, only while the list has the focus."""
        group = self.selected
        if not self.group_list.has_focus or group is None or self.busy:
            return
        self.busy = True
        self.say(f"{verb} #{group.name} ...")
        self.run_worker(lambda: self.app.post(self.membership_done, *join_or_leave(verb, group.name)), thread=True, group="groups")

    def membership_done(self, worked: bool, line: str) -> None:
        self.busy = False
        self.say(line)
        self.reload()

    # Posting

    def action_post(self) -> None:
        group = self.selected
        text = self.message_area.text.strip()
        if self.busy or group is None or not text:
            return
        if not group.joined:
            self.say(f"You're not in #{group.name}. J joins it.")
            return
        self.busy = True
        # Locked until calm-comms comes back.
        self.message_area.read_only = True
        self.run_worker(lambda: self.post_in_background(group.name, text), thread=True, group="groups")

    def post_in_background(self, group_name: str, text: str) -> None:
        result = send_mail(group_name, text, verb="group")
        output = (result.stdout + result.stderr).decode("utf-8", "replace").strip()
        self.app.post(self.post_done, result.returncode == 0, output)

    def post_done(self, posted: bool, output: str) -> None:
        """Shows calm-comms' answer; a post that went out clears the input and shows up in the thread, a refused one keeps the text."""
        self.busy = False
        self.message_area.read_only = False
        self.say(f"{clock_text()}  {output or ('posted' if posted else 'calm-comms gave no reason')}")
        if posted:
            self.message_area.clear()
            self.show_thread()

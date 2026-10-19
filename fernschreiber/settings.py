"""fernschreiber's settings: every knob in one place."""

from pathlib import Path

TITLE = "RABENSCHNACK"
KEY_HINTS = "[Tab] focus  [^Enter] send  [F2] help  [^Q] quit"
NOTAR_KEY_HINTS = "[Up/Down] pick  [^Enter] send to all watching  [Esc] back"
NOTAR_MESSAGES_FILE = Path(__file__).with_name("NOTAR_messages.md")
NOTAR_FIRST_LINE = "📯 NOTAR: notice to all ravens"
N06BC01_KEY_HINTS = "[Space] mark  [^Enter] send to the hallmaster  [Esc] back"
N06BC01_FIRST_LINE = "☕ N06BC01: please wake these ravens and ask them to schnackon"
HALLMASTER_SEAT = "hallmaster"
WAKE_PANE_WIDTH = 26
HELP_TEXT = """\
fernschreiber keys

F1           Rabenschnack
F2           this help; Esc goes back
F3           NOTAR, a notice to all ravens; Esc goes back
F4           N06BC01, waking ravens; Esc goes back
Ctrl+Q       quit

In Rabenschnack
Tab          next pane: input, seats, mailbox
Esc          back to the input
Up/Down      move in the pane with the focus
PgUp/PgDn    scroll the mailbox, from anywhere
Enter        new line
Ctrl+Enter   send to the selected seat

In NOTAR
Up/Down      pick a message
Ctrl+Enter   send it to every watching seat

In N06BC01
Up/Down      move
Space        mark a seat to wake, or unmark it
Ctrl+Enter   send the wake list to the hallmaster

^ stands for Ctrl."""

SEAT_PANE_WIDTH = 22
INPUT_LINES = 2
SEAT_REFRESH_SECONDS = 30
HISTORY_MAIL_COUNT = 20

GIT_USR_BIN = r"C:\Program Files\Git\usr\bin"
BASH = GIT_USR_BIN + r"\bash.exe"
CALM_COMMS = "C:/Users/devboese/.claude/skills/calm-comms/calm_comms.sh"
HRAFNSMAL = Path("C:/haven/Hall/thing/Hrafnsmal")
OWN_SEAT = "wally"

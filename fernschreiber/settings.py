"""fernschreiber's settings: every knob in one place."""

from pathlib import Path

TITLE = "RABENSCHNACK"
KEY_HINTS = "[Tab] focus  [^Enter] send  [F2] help  [^Q] quit"
HELP_TEXT = """\
fernschreiber keys

F1           Rabenschnack
F2           this help; Esc goes back
Ctrl+Q       quit

In Rabenschnack
Tab          next pane: input, seats, mailbox
Esc          back to the input
Up/Down      move in the pane with the focus
PgUp/PgDn    scroll the mailbox, from anywhere
Enter        new line
Ctrl+Enter   send to the selected seat

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

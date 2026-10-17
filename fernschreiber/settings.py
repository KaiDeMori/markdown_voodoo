"""fernschreiber's settings: every knob in one place."""

from pathlib import Path

TITLE = "RABENSCHNACK"
KEY_HINTS = "[Tab] focus  [^Enter] send  [F1] help  [^Q] quit"
HELP_TEXT = """\
 fernschreiber keys

 Tab          next pane: input, seats, mailbox
 Esc          back to the input
 Up/Down      move in the pane with the focus
 PgUp/PgDn    scroll the mailbox, from anywhere
 Enter        new line
 Ctrl+Enter   send to the selected seat
 F1           this help, and back
 Ctrl+Q       quit

 ^ stands for Ctrl."""

SEAT_PANE_WIDTH = 22
INPUT_LINES = 2
SEAT_REFRESH_SECONDS = 30
WATCH_MINUTES = 15
HISTORY_MAIL_COUNT = 20
INBOX_MAIL_LIMIT = 100

FRAME_COLOR = "#6c6c6c"
TEXT_COLOR = "#c8c8c8"
DIM_COLOR = "#8a8a8a"
FOCUS_COLOR = "#f0f0f0"
BACKGROUND_COLOR = "#0c0c0c"

GIT_USR_BIN = r"C:\Program Files\Git\usr\bin"
BASH = GIT_USR_BIN + r"\bash.exe"
CALM_COMMS = "C:/Users/devboese/.claude/skills/calm-comms/calm_comms.sh"
HRAFNSMAL = Path("C:/haven/Hall/thing/Hrafnsmal")
OWN_SEAT = "wally"

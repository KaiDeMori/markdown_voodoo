"""Central configuration + the yt-dlp options every stage shares.

HOW YOUTUBE ACCESS WORKS HERE
-----------------------------
A modest transcript pull from a machine that normally browses YouTube usually
needs nothing special: yt-dlp already selects clients that avoid a
Proof-of-Origin (PO) token, and captions are public. The blocks people actually
hit come from request rate and IP reputation - downloading too fast or too
parallel, or from a datacenter/VPN address - not from a missing token or cookie.

When a specific video is walled anyway, escalate in order, cheapest first:
  1. Let yt-dlp pick the client (the default). If a playable video exposes no
     tracks, try a specific `--client`; which client is current is a moving
     target, so consult the yt-dlp wiki rather than any list baked in here.
  2. A PO token, minted by the optional bgutil provider server, helps with
     token-gated formats/subtitles on web-family clients. It does NOT lift a
     "Sign in to confirm you're not a bot" / LOGIN_REQUIRED wall.
  3. Cookies from a throwaway account lift that wall and unlock age-restricted
     videos, at some risk to the account - so they are off by default and opt-in
     (see resolve_cookies).

`base_ydl_opts()` wires the shared options (polite throttling, the JS runtime,
and the PO provider when it has been built). YouTube's enforcement changes
constantly and the specifics live upstream - see docs/Setup.md for the links.

Run `python -m ytx.config` for a no-network "doctor" report.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from yt_dlp.utils import sanitize_filename


def use_utf8_io() -> None:
    """Force stdout/stderr to UTF-8 so unicode titles/emoji don't crash on the
    Windows cp1252 console. Call once at the top of each CLI main()."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

# --- project layout -------------------------------------------------------
# PROJECT_DIR is the skill's own home (code + toolchain + cookies). Output NEVER
# lands here - that is what the output base below is for.
PROJECT_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_DIR / "tools"

# --- output base ----------------------------------------------------------
# Where transcripts and their caches are written: the user's workspace, never the
# skill folder. The clean .md lands at the base root; raw/ and meta/ sit beside it
# as subfolders. Resolution order: configure() (from --out-dir) > $YTX_OUT >
# <cwd>/YT-Transcripts. Agents pass --out-dir explicitly (see SKILL.md).
DEFAULT_OUTPUT_DIRNAME = "YT-Transcripts"


def default_output_base() -> Path:
    env = os.environ.get("YTX_OUT")
    return Path(env).expanduser() if env else Path.cwd() / DEFAULT_OUTPUT_DIRNAME


OUTPUT_BASE = default_output_base()
CLEAN_DIR = OUTPUT_BASE          # the deliverable .md sits at the base root
RAW_DIR = OUTPUT_BASE / "raw"    # download-once source of truth, never edited
META_DIR = OUTPUT_BASE / "meta"  # listing cache (info.json + subs.json)


def configure(out_dir: str | Path | None) -> Path:
    """Point the output dirs at out_dir (the deliverable base) and return it.

    A falsy out_dir keeps the default (env or cwd). Every call site reads
    config.RAW_DIR / CLEAN_DIR / META_DIR fresh at call time, so reassigning the
    module globals here is enough - nothing has to be threaded through.
    """
    global OUTPUT_BASE, CLEAN_DIR, RAW_DIR, META_DIR
    if out_dir:
        OUTPUT_BASE = Path(out_dir).expanduser().resolve()
        CLEAN_DIR = OUTPUT_BASE
        RAW_DIR = OUTPUT_BASE / "raw"
        META_DIR = OUTPUT_BASE / "meta"
    return OUTPUT_BASE

# --- optional PO-token toolchain ------------------------------------------
# bgutil PO-token provider, built locally in script mode. Optional: only needed
# when you escalate to a web-family client that requires a token (see the module
# docstring). An absent build just means base_ydl_opts does not advertise it.
BGUTIL_SERVER_HOME = TOOLS_DIR / "bgutil-provider" / "server"


def bgutil_built() -> bool:
    """True when the optional PO-token server has been built locally."""
    return (BGUTIL_SERVER_HOME / "build" / "generate_once.js").is_file()


# deno JS runtime, installed via the official user-scope installer.
DENO_EXE = Path(os.path.expanduser("~")) / ".deno" / "bin" / "deno.exe"

# --- cookies (opt-in) -----------------------------------------------------
# Cookies from a throwaway account, used only when cookie use is enabled (the
# settings file or --use-cookies) AND this file exists. They lift a
# LOGIN_REQUIRED / "not a bot" wall and unlock age-restricted videos, at some
# risk to that account, so cookie use is off by default. Lives inside the
# project but is gitignored (never committed). Re-export when it expires (see
# docs/Setup.md).
DEFAULT_COOKIES = PROJECT_DIR / "cookies" / "cookies.txt"

# Local preferences (gitignored). Copy settings.local.json.example to
# settings.local.json to change them; an absent file means defaults.
SETTINGS_FILE = PROJECT_DIR / "settings.local.json"


def load_settings() -> dict:
    """Read the local settings file; return {} if it is missing or unreadable."""
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# Whether cookies may be used automatically. Off by default: a cookie YouTube
# decides it dislikes can get the underlying account throttled or banned, so
# using one is a deliberate opt-in, never a silent default.
USE_COOKIES = bool(load_settings().get("use_cookies", False))


def resolve_cookies(explicit: str | None = None, use_cookies: bool | None = None) -> str | None:
    """Pick the cookies file to use, honoring the opt-in.

    explicit    - an explicit --cookies path always wins.
    use_cookies - True/False forces the choice for this run; None falls back to
                  the USE_COOKIES setting.

    Returns the default cookies file only when cookies are enabled AND it exists.
    """
    if explicit:
        return explicit
    enabled = USE_COOKIES if use_cookies is None else use_cookies
    if enabled and DEFAULT_COOKIES.is_file():
        return str(DEFAULT_COOKIES)
    return None

# --- politeness / anti-annoyance defaults ---------------------------------
SLEEP_REQUESTS = 2.0   # seconds between HTTP requests inside one yt-dlp run
RETRIES = 3

# How transcripts are laid out. Auto-captions have no chapters/usable pauses, so
# reflow leans on the ASR's sentence punctuation. One of:
#   sentences | paragraphs | wrapped | oneline | lines
DEFAULT_FLOW = "sentences"


# Let yt-dlp choose the player client. Its maintainers track YouTube's changes
# and pick a working, least-gated client better than any fixed list could - a
# hardcoded set here would be stale within days. Override per run with `--client`
# only when a playable video exposes no tracks, and consult the yt-dlp wiki for
# which client is currently best.
DEFAULT_PLAYER_CLIENTS = None


def base_ydl_opts(
    verbose: bool = False,
    player_clients: tuple[str, ...] | list[str] | None = DEFAULT_PLAYER_CLIENTS,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> dict:
    """Shared yt-dlp options: polite throttling, JS runtime, PO provider if built.

    Pin deno by absolute path (no PATH juggling). The bgutil node fallback finds
    `node` on PATH on its own. server_home is passed absolute, which is safe via
    the Python API (the ':' delimiter problem only bites the CLI).

    player_clients     - override YouTube's client selection. None (default) lets
                         yt-dlp pick; pass a specific client only to work around a
                         playable video that exposes no tracks.
    cookies_from_browser - e.g. "firefox": read cookies from a browser profile
                         instead of a file; ties requests to that account.
    """
    extractor_args: dict = {}
    # Advertise the local PO-token server only when it has been built. yt-dlp
    # requests a token from it only for clients that need one, so on the default
    # client this stays dormant.
    if bgutil_built():
        extractor_args["youtubepot-bgutilscript"] = {"server_home": [str(BGUTIL_SERVER_HOME)]}
    if player_clients:
        extractor_args["youtube"] = {"player_client": list(player_clients)}

    opts: dict = {
        "skip_download": True,
        "noplaylist": True,
        "retries": RETRIES,
        "sleep_interval_requests": SLEEP_REQUESTS,
        "extractor_args": extractor_args,
        # We want subtitle/caption metadata, not media. Without this, yt-dlp's
        # format selector raises "Requested format is not available" before it
        # ever hands back the info dict (which carries the subtitle tracks).
        "ignore_no_formats_error": True,
        # Keep yt-dlp's progress chatter off stdout so our stdout stays a clean,
        # parseable result (JSON). Diagnostics go to stderr.
        "logtostderr": True,
        "quiet": not verbose,
        "verbose": verbose,
        "no_warnings": False,
    }
    if DENO_EXE.exists():
        opts["js_runtimes"] = {"deno": {"path": str(DENO_EXE)}}
    if cookies_from_browser:
        # tuple form: (browser, profile, keyring, container).
        # "firefox:profilename" selects a non-default profile (good for an alt).
        browser, _, profile = cookies_from_browser.partition(":")
        opts["cookiesfrombrowser"] = (browser, profile or None, None, None)
    if cookies_file:
        # Netscape cookies.txt exported from a browser extension.
        opts["cookiefile"] = cookies_file
    return opts


def safe_filename(info: dict, suffix: str = "", max_len: int = 200) -> str:
    """Windows-safe filename: '<channel> - <title> [<id>]<suffix>', capped at max_len.

    Uses yt-dlp's own sanitize_filename (the logic behind --windows-filenames) to
    strip characters illegal on Windows, then truncates the title so the whole
    name stays within max_len while always keeping the id tag and suffix intact.
    """
    channel = sanitize_filename(info.get("channel") or info.get("uploader") or "", restricted=False)
    title = sanitize_filename(info.get("title") or "", restricted=False)
    vid = info.get("id") or ""
    idtag = f" [{vid}]" if vid else ""
    head = f"{channel} - {title}".strip(" -") if channel else title
    room = max(0, max_len - len(idtag) - len(suffix))
    if len(head) > room:
        head = head[:room].rstrip()
    return f"{head}{idtag}{suffix}"


def doctor() -> dict:
    """Cheap, network-free health check, split into the always-needed core and
    the optional escalation pieces (a missing optional piece is fine until you
    actually need that rung)."""
    node = shutil.which("node")
    return {
        "core": {
            "deno_exe": (str(DENO_EXE), DENO_EXE.exists()),
        },
        "optional_escalation": {
            "bgutil_server_build": (
                str(BGUTIL_SERVER_HOME / "build" / "generate_once.js"),
                bgutil_built(),
            ),
            "bgutil_node_modules": (
                str(BGUTIL_SERVER_HOME / "node_modules"),
                (BGUTIL_SERVER_HOME / "node_modules").is_dir(),
            ),
            "node_on_path": (node, node is not None),
            "cookies_enabled": (str(SETTINGS_FILE), USE_COOKIES),
            "cookies_file_present": (str(DEFAULT_COOKIES), DEFAULT_COOKIES.is_file()),
        },
        "output_base": (str(OUTPUT_BASE), OUTPUT_BASE.is_dir()),  # created on demand per run
    }


def main() -> int:
    print("ytx environment doctor (no network):\n")
    print(json.dumps(doctor(), indent=2))
    print(
        "\ncore = always needed; optional_escalation = only when a video is walled "
        "(see docs/Setup.md).\noutput_base false is expected - it is created per run "
        "in the workspace you point --out-dir at.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

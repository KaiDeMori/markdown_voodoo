"""Central configuration + the yt-dlp options that carry everything we learned.

WHY THIS FILE EXISTS
--------------------
Modern YouTube refuses anonymous metadata requests with
"Sign in to confirm you're not a bot". The cookie-free fix is a
Proof-of-Origin (PO) token, which needs:

  * a JS runtime  -> deno (installed user-scope at ~/.deno/bin/deno.exe)
  * a token provider -> the `bgutil-ytdlp-pot-provider` plugin (pip, in the
    venv) talking to its locally-built server in "script mode"
    (tools/bgutil-provider/server, built with `npm install && npx tsc`).

`base_ydl_opts()` wires all of that into a single options dict so callers
never have to remember the incantation again. No cookies, no account.

Run `python -m ytx.config` for a no-network "doctor" report.
"""
from __future__ import annotations

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
# lands here — that is what the output base below is for.
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
    module globals here is enough — nothing has to be threaded through.
    """
    global OUTPUT_BASE, CLEAN_DIR, RAW_DIR, META_DIR
    if out_dir:
        OUTPUT_BASE = Path(out_dir).expanduser().resolve()
        CLEAN_DIR = OUTPUT_BASE
        RAW_DIR = OUTPUT_BASE / "raw"
        META_DIR = OUTPUT_BASE / "meta"
    return OUTPUT_BASE

# --- toolchain we set up --------------------------------------------------
# bgutil PO-token provider, built locally in script mode.
BGUTIL_SERVER_HOME = TOOLS_DIR / "bgutil-provider" / "server"
# deno JS runtime, installed via the official user-scope installer.
DENO_EXE = Path(os.path.expanduser("~")) / ".deno" / "bin" / "deno.exe"

# Default alt-account cookies (YouTube returns LOGIN_REQUIRED without them).
# Used automatically if present and no explicit --cookies is given. Lives inside
# the project but is gitignored (never committed). If it expires, re-export from
# a logged-in private window (see docs/Setup.md).
DEFAULT_COOKIES = PROJECT_DIR / "cookies" / "cookies.txt"


def resolve_cookies(explicit: str | None = None) -> str | None:
    """Pick the cookies file to use: explicit > default-if-present > None."""
    if explicit:
        return explicit
    return str(DEFAULT_COOKIES) if DEFAULT_COOKIES.is_file() else None

# --- politeness / anti-annoyance defaults ---------------------------------
SLEEP_REQUESTS = 2.0   # seconds between HTTP requests inside one yt-dlp run
RETRIES = 3

# How transcripts are laid out. Auto-captions have no chapters/usable pauses, so
# reflow leans on the ASR's sentence punctuation. One of:
#   sentences | paragraphs | wrapped | oneline | lines
DEFAULT_FLOW = "sentences"


# Default client set is chosen by yt-dlp (currently android_vr/web_safari) and
# returns LOGIN_REQUIRED without engaging the PO token. The WebPO token from
# bgutil is only requested for "web"-family clients, so we force those to make
# the cookie-free bypass actually fire.
DEFAULT_PLAYER_CLIENTS = ("web", "mweb", "tv")


def base_ydl_opts(
    verbose: bool = False,
    player_clients: tuple[str, ...] | list[str] | None = DEFAULT_PLAYER_CLIENTS,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> dict:
    """Common yt-dlp options: cookie-free PO-token bypass + polite throttling.

    Pin deno by absolute path (no PATH juggling). The bgutil node fallback
    finds `node` on PATH on its own. server_home is passed absolute, which is
    safe via the Python API (the ':' delimiter problem only bites the CLI).

    player_clients     - force these YouTube clients (web-family => triggers the
                         WebPO token request to bgutil). None = yt-dlp default.
    cookies_from_browser - e.g. "firefox": last-resort fallback if PO tokens are
                         not enough; ties requests to your logged-in account.
    """
    extractor_args: dict = {
        "youtubepot-bgutilscript": {"server_home": [str(BGUTIL_SERVER_HOME)]},
    }
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
    """Cheap, network-free health check of the toolchain."""
    node = shutil.which("node")
    return {
        "deno_exe": (str(DENO_EXE), DENO_EXE.exists()),
        "node_on_path": (node, node is not None),
        "bgutil_server_home": (str(BGUTIL_SERVER_HOME), BGUTIL_SERVER_HOME.is_dir()),
        "bgutil_build_js": (
            str(BGUTIL_SERVER_HOME / "build" / "generate_once.js"),
            (BGUTIL_SERVER_HOME / "build" / "generate_once.js").is_file(),
        ),
        "bgutil_node_modules": (
            str(BGUTIL_SERVER_HOME / "node_modules"),
            (BGUTIL_SERVER_HOME / "node_modules").is_dir(),
        ),
        "tools_dir": (str(TOOLS_DIR), TOOLS_DIR.is_dir()),
        "output_base": (str(OUTPUT_BASE), OUTPUT_BASE.is_dir()),  # created on demand per run
    }


def main() -> int:
    import json

    print("ytx environment doctor (no network):\n")
    print(json.dumps(doctor(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The bridge to calm-email's catalog: its letters and their addresses, opened by Wally's value on stdin; letters pass through as they are."""

import os
import subprocess

import settings

# The same PATH as for calm-comms, for the same reason; see calm_comms.py.
CALM_EMAIL_ENVIRONMENT = dict(os.environ, LANG="C.UTF-8", PATH=settings.GIT_USR_BIN + os.pathsep + os.environ.get("PATH", ""))


def catalog_meta() -> str | None:
    """Wally's value from the environment, read at the moment it is needed and never shown."""
    return os.environ.get(settings.CATALOG_META_VARIABLE) or None


def run_catalog(arguments: list[str], stdin_text: str) -> tuple[bool, str]:
    """Runs one catalog verb; returns whether it worked and calm-email's own words."""
    result = subprocess.run(
        [settings.BASH, settings.CALM_EMAIL, "catalog", *arguments],
        input=stdin_text.encode("utf-8"),
        capture_output=True,
        env=CALM_EMAIL_ENVIRONMENT,
    )
    output = (result.stdout + result.stderr).decode("utf-8", "replace").strip()
    return result.returncode == 0, output or f"calm-email stopped with exit code {result.returncode}"


def read_catalog(meta: str) -> tuple[list[tuple[str, str]] | None, str]:
    """The entries as (letter, address), or None with calm-email's reason."""
    worked, output = run_catalog(["addresses"], meta)
    if not worked:
        return None, output
    entries = [tuple(line.split("\t", 1)) for line in output.splitlines() if "\t" in line]
    return entries, "" if entries else output


def add_entry(meta: str, letter: str, address: str) -> tuple[bool, str]:
    return run_catalog(["add", letter], f"{meta}\n{address}\n")


def remove_entry(meta: str, letter: str) -> tuple[bool, str]:
    return run_catalog(["remove", letter], meta)

import subprocess
import sys
from pathlib import Path

import pytest

calm_md_location = Path(__file__).resolve().parent.parent / "calm_md.py"


@pytest.fixture
def calm_md():
    """Runs calm-md the way a raven calls it, isolated, and gives its exit code and its answer."""

    def run(*arguments, stdin=b""):
        completed = subprocess.run([sys.executable, "-I", str(calm_md_location), *map(str, arguments)], input=stdin, capture_output=True)
        return completed.returncode, completed.stdout.decode("utf-8").strip()

    return run

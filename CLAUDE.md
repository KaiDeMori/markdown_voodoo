# markdown_voodoo

## Test runners and temporary files

Test runners write to the system TEMP folder by default — pytest to `%TEMP%\pytest-of-<user>\`. That folder lies outside this repo and is shared with every other test run on the machine.

**Before the first test run in any project here**, point the runner's temporary folder into the project:

- **pytest:** `addopts = --basetemp=.pytest_tmp` in `pytest.ini`, `.pytest_tmp/` in `.gitignore`, and a session guard that stops the run when the resolved folder lies outside the project.
- **Subprocesses started by tests** get `TEMP` and `TMP` pointing into the test folder as well.

Reference implementation: `skills/yt-transcript-extractor/` — `pytest.ini`, `tests/conftest.py` (`temp_stays_in_project`), `tests/test_relay_bat.py` (`isolated_environment`).

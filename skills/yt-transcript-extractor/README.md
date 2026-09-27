# yt-transcript-extractor

## For developers: tests never write outside this folder

Test runners write to the system TEMP folder by default — pytest to `%TEMP%\pytest-of-<user>\`, outside this repo and shared by every test run on the machine.

- `pytest.ini` points pytest's temporary folder at `.pytest_tmp/` (gitignored). Run pytest from this folder.
- `tests/conftest.py` (`temp_stays_in_project`) stops the session before the first file is written if that folder would land anywhere else.
- Subprocesses started by tests get `TEMP` and `TMP` pointing into the test folder too (`tests/test_relay_bat.py`, `isolated_environment`).

Keep all three when changing the tests.

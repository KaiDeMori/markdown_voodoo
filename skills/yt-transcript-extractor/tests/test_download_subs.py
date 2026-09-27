"""Download-stage guards: URL expiry, and the offline path that never fetches."""
from __future__ import annotations

import pytest

from ytx import config
from ytx.download_subs import present_raw_files, url_expired


@pytest.mark.parametrize("url, expected", [
    ("https://www.youtube.com/api/timedtext?lang=en&expire=1", True),
    ("https://www.youtube.com/api/timedtext?lang=en&expire=4102444800", False),
    ("https://www.youtube.com/api/timedtext?lang=en", False),
])
def test_url_expired(url, expected):
    assert url_expired({"url": url}) is expected


def test_present_raw_files_returns_what_is_there(seeded_out_dir, fixture_listing):
    saved = present_raw_files("iyJj9RxSsBY", fixture_listing, [("en", "manual", "json3")])
    assert saved == [config.RAW_DIR / "iyJj9RxSsBY.en.manual.json3"]


def test_present_raw_files_names_the_relay_command_for_a_missing_track(
        seeded_out_dir, fixture_listing):
    with pytest.raises(SystemExit, match="ytx_relay.bat iyJj9RxSsBY en-orig.auto"):
        present_raw_files("iyJj9RxSsBY", fixture_listing, [("en-orig", "auto", "json3")])

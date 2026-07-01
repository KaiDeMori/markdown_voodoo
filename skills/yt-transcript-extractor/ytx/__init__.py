"""ytx - a small, polite YouTube transcript extractor.

Staged pipeline (each network stage is run deliberately, never automatically):
  1. list_subs  - discover which subtitle tracks/formats exist   (network)
  2. download   - fetch only the chosen tracks into raw/         (network)
  3. clean      - dedupe/strip raw subs into plain text          (local)
  4. compare    - pick the best transcript                       (local)

The shared yt-dlp options (JS runtime, polite throttling, and the optional
PO-token provider when it has been built) live in config.py so callers stay
simple. Cookies and non-default clients are opt-in escalation - see config.py
and docs/Setup.md.
"""

__all__ = ["config"]

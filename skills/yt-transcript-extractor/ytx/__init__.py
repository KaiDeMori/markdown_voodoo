"""ytx - a small, polite YouTube transcript extractor.

Staged pipeline (each network stage is run deliberately, never automatically):
  1. list_subs  - discover which subtitle tracks/formats exist   (network)
  2. download   - fetch only the chosen tracks into raw/         (network)
  3. clean      - dedupe/strip raw subs into plain text          (local)
  4. compare    - pick the best transcript                       (local)

All the hard-won setup (deno JS runtime, bgutil PO-token provider,
throttling) lives in config.py so it is preserved as code, not lore.
"""

__all__ = ["config"]

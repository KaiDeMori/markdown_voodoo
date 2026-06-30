"""`python -m ytx <url>` == `python -m ytx.extract <url>` (the one-shot pipeline)."""
from .extract import main

if __name__ == "__main__":
    raise SystemExit(main())

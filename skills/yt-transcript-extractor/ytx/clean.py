"""Stage 3 + 4 - clean raw subs into plain text, and compare formats.

Fully local and non-destructive: reads raw/ , writes clean/ , never touches the
originals. Handles the two formats we care about:

  * json3 - structured JSON; each event's segs already hold one clean line.
  * vtt   - YouTube auto-caption rolling format; strip inline <...> tags then
            drop lines identical to the previous emitted line (kills the
            bridge + carryover triplication while keeping real repeats).

    python -m ytx.clean <id-or-url>          # clean every raw file for the id
    python -m ytx.clean <id-or-url> --compare-only
"""
from __future__ import annotations

import html
import json
import re
import sys
import textwrap

from . import config
from .list_subs import _take_opt, video_id

_TAG = re.compile(r"<[^>]+>")        # <00:00:01.234> and <c>...</c>
_WS = re.compile(r"\s+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")   # split after sentence enders

FLOW_MODES = ("sentences", "paragraphs", "wrapped", "oneline", "lines")


def _norm(text: str) -> str:
    # unescape first: VTT carries &nbsp; etc.; \xa0 then collapses as whitespace
    return _WS.sub(" ", html.unescape(text)).strip()


def clean_json3(path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    lines, last = [], None
    for ev in data.get("events", []):
        text = _norm("".join(s.get("utf8", "") for s in (ev.get("segs") or [])))
        if not text or text == last:
            continue
        lines.append(text)
        last = text
    return lines


def clean_vtt(path) -> list[str]:
    lines, last = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if (not line or line == "WEBVTT" or "-->" in line
                or line.startswith(("Kind:", "Language:", "NOTE"))):
            continue
        text = _norm(_TAG.sub("", line))
        if not text or text == last:
            continue
        lines.append(text)
        last = text
    return lines


_CLEANERS = {"json3": clean_json3, "vtt": clean_vtt}


def clean_file(path) -> list[str] | None:
    fmt = path.suffix.lstrip(".")
    fn = _CLEANERS.get(fmt)
    return fn(path) if fn else None


def to_sentences(lines: list[str]) -> list[str]:
    """Join caption lines into continuous text, re-split on sentence enders."""
    text = " ".join(lines)
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def reflow(lines: list[str], mode: str = "sentences",
           sentences_per_para: int = 4, width: int = 88) -> str:
    """Render cleaned caption lines as text in the chosen layout.

    sentences  - one sentence per line (default; faithful to real boundaries)
    paragraphs - sentences grouped into short blocks, blank line between
    wrapped    - one continuous block, hard-wrapped at `width`
    oneline    - everything on a single line
    lines      - keep the raw caption-line breaks (no reflow)
    """
    if mode == "lines":
        return "\n".join(lines) + "\n"
    if mode == "oneline":
        return " ".join(lines) + "\n"
    sents = to_sentences(lines)
    if mode == "sentences":
        return "\n".join(sents) + "\n"
    if mode == "paragraphs":
        paras = [" ".join(sents[i:i + sentences_per_para])
                 for i in range(0, len(sents), sentences_per_para)]
        return "\n\n".join(paras) + "\n"
    if mode == "wrapped":
        return textwrap.fill(" ".join(sents), width) + "\n"
    raise ValueError(f"unknown flow mode: {mode!r} (choose from {FLOW_MODES})")


def _stats(lines: list[str]) -> dict:
    words = sum(len(l.split()) for l in lines)
    return {"lines": len(lines), "words": words,
            "chars": sum(len(l) for l in lines)}


def run(vid: str, compare_only: bool = False, flow: str | None = None) -> int:
    flow = flow or config.DEFAULT_FLOW
    config.CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    raws = sorted(config.RAW_DIR.glob(f"{vid}.*"))
    if not raws:
        raise SystemExit(f"No raw files for {vid} in {config.RAW_DIR}. Run download_subs first.")

    results = {}
    for path in raws:
        lines = clean_file(path)
        if lines is None:
            print(f"  [skip ] {path.name}: no cleaner for .{path.suffix.lstrip('.')}")
            continue
        results[path.name] = lines
        if not compare_only:
            out = config.CLEAN_DIR / (path.name + ".txt")
            out.write_text(reflow(lines, flow), encoding="utf-8")
            print(f"  [clean] {out.name:45s} {_stats(lines)}  flow={flow}")

    # Stage 4 - compare the cleaned outputs.
    if len(results) >= 2:
        print("\n=== format comparison ===")
        for name, lines in results.items():
            print(f"  {name:45s} {_stats(lines)}")
        names = list(results)
        a, b = results[names[0]], results[names[1]]
        same = a == b
        print(f"\n  '{names[0]}' vs '{names[1]}' identical after cleaning: {same}")
        if not same:
            # show where they first diverge, to judge which is cleaner
            for i, (x, y) in enumerate(zip(a, b)):
                if x != y:
                    print(f"  first diff at line {i}:\n    A: {x!r}\n    B: {y!r}")
                    break
            print(f"  line counts: {names[0]}={len(a)}  {names[1]}={len(b)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    config.use_utf8_io()
    config.configure(_take_opt(argv, "--out-dir"))  # base whose raw/ to read, root to write
    compare_only = "--compare-only" in argv
    if compare_only:
        argv.remove("--compare-only")
    flow = _take_opt(argv, "--flow") or config.DEFAULT_FLOW
    if not argv:
        print(__doc__)
        return 2
    for target in argv:
        vid = video_id(target)
        print(f"\n=== cleaning {vid} (flow={flow}) ===")
        run(vid, compare_only=compare_only, flow=flow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

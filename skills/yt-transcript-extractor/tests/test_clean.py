"""The flow choice: a track with too few sentence enders falls back to its caption lines."""
from __future__ import annotations

import pytest

from conftest import FIXTURE_VIDEO_ID, UNPUNCTUATED_CAPTION_LINES
from ytx import clean, config

FALLBACK_LABEL = "lines (fallback from sentences: too few sentence enders)"
PUNCTUATED_CAPTION_LINES = [f"this is caption line {number} of the talk" + ("." if number % 2 else "")
                            for number in range(300)]


def punctuated_only_up_to(lines: list[str], punctuated_share: float) -> list[str]:
    kept = round(len(lines) * punctuated_share)
    return lines[:kept] + [line.rstrip(".") for line in lines[kept:]]


def test_unpunctuated_track_falls_back_to_lines():
    chosen_flow = clean.choose_flow(UNPUNCTUATED_CAPTION_LINES, None)
    assert chosen_flow == "lines"
    assert clean.flow_label(None, chosen_flow) == FALLBACK_LABEL


def test_punctuated_track_keeps_the_default_flow():
    chosen_flow = clean.choose_flow(PUNCTUATED_CAPTION_LINES, None)
    assert chosen_flow == "sentences"
    assert clean.flow_label(None, chosen_flow) == "sentences"


@pytest.mark.parametrize("caption_lines_per_sentence, expected_flow", [(10, "sentences"), (11, "lines")])
def test_the_fallback_starts_above_ten_caption_lines_per_sentence(caption_lines_per_sentence, expected_flow):
    lines = [f"caption line {number:03d} of the talk"
             + ("." if number % caption_lines_per_sentence == caption_lines_per_sentence - 1 else "")
             for number in range(300)]
    assert clean.choose_flow(lines, None) == expected_flow


def test_a_stray_sentence_ender_does_not_prevent_the_fallback():
    middle = len(UNPUNCTUATED_CAPTION_LINES) // 2
    lines = [*UNPUNCTUATED_CAPTION_LINES[:middle], "the uh game is very. good yeah",
             *UNPUNCTUATED_CAPTION_LINES[middle:]]
    assert clean.choose_flow(lines, None) == "lines"


@pytest.mark.parametrize("punctuated_share, expected_flow", [(0.3, "lines"), (0.7, "sentences")])
def test_a_partly_punctuated_track_falls_back_when_most_text_is_unsplit(punctuated_share, expected_flow):
    lines = punctuated_only_up_to(PUNCTUATED_CAPTION_LINES, punctuated_share)
    assert clean.choose_flow(lines, None) == expected_flow


def test_cjk_sentence_marks_are_not_sentence_enders():
    """The splitter knows only ASCII sentence enders, so a track punctuated with "。" gets lines."""
    lines = [line + ("。" if number % 3 == 2 else "")
             for number, line in enumerate(UNPUNCTUATED_CAPTION_LINES)]
    assert clean.choose_flow(lines, None) == "lines"


@pytest.mark.parametrize("flow", ["sentences", "paragraphs"])
def test_an_explicit_flow_is_honored(flow):
    chosen_flow = clean.choose_flow(UNPUNCTUATED_CAPTION_LINES, flow)
    assert chosen_flow == flow
    assert clean.flow_label(flow, chosen_flow) == flow


@pytest.mark.parametrize("lines", [[], ["hello there"]], ids=["empty", "one caption line"])
def test_a_tiny_track_keeps_the_default_flow(lines):
    assert clean.choose_flow(lines, None) == "sentences"


def test_a_default_flow_that_does_not_split_at_sentence_enders_never_falls_back(monkeypatch):
    monkeypatch.setattr(config, "DEFAULT_FLOW", "wrapped")
    assert clean.choose_flow(UNPUNCTUATED_CAPTION_LINES, None) == "wrapped"


def test_the_fallback_label_names_the_default_flow(monkeypatch):
    monkeypatch.setattr(config, "DEFAULT_FLOW", "paragraphs")
    chosen_flow = clean.choose_flow(UNPUNCTUATED_CAPTION_LINES, None)
    assert chosen_flow == "lines"
    assert clean.flow_label(None, chosen_flow) == "lines (fallback from paragraphs: too few sentence enders)"


def test_standalone_clean_applies_the_same_fallback(seeded_out_dir, unpunctuated_asr_track, run_cli):
    _exit_code, stdout = run_cli(clean.main, FIXTURE_VIDEO_ID)
    clean_text = (seeded_out_dir / f"{unpunctuated_asr_track.name}.txt").read_text(encoding="utf-8")
    assert clean_text == "\n".join(UNPUNCTUATED_CAPTION_LINES) + "\n"
    report_lines = {line.split()[1]: line for line in stdout.splitlines() if line.startswith("  [clean]")}
    assert report_lines[f"{unpunctuated_asr_track.name}.txt"].endswith(f"flow={FALLBACK_LABEL}")
    assert report_lines[f"{FIXTURE_VIDEO_ID}.en.manual.json3.txt"].endswith("flow=sentences")


def test_standalone_clean_honors_an_explicit_flow(seeded_out_dir, unpunctuated_asr_track, run_cli):
    _exit_code, stdout = run_cli(clean.main, "--flow", "sentences", FIXTURE_VIDEO_ID)
    clean_text = (seeded_out_dir / f"{unpunctuated_asr_track.name}.txt").read_text(encoding="utf-8")
    assert clean_text == " ".join(UNPUNCTUATED_CAPTION_LINES) + "\n"
    report_lines = {line.split()[1]: line for line in stdout.splitlines() if line.startswith("  [clean]")}
    assert report_lines[f"{unpunctuated_asr_track.name}.txt"].endswith("flow=sentences")

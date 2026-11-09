import pytest

t_line = "\U000FE054".encode("utf-8") + b"12 100"

nested_doc = (
    b"# Doc\n\n"
    b"## One\n\nfirst\n\n### One A\n\na\n\n"
    b"## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n#### Deeper\n\ndeepest\n\n"
    b"## Three\n\nthird\n"
)


def test_a_chapter_moves_after_a_sibling_with_its_subchapters(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("move", doc, "One", "after", "Two") == (0, "Doc > One: moved after Doc > Two.")
    assert doc.read_bytes() == (
        b"# Doc\n\n"
        b"## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n#### Deeper\n\ndeepest\n\n"
        b"## One\n\nfirst\n\n### One A\n\na\n\n"
        b"## Three\n\nthird\n"
    )


def test_the_last_chapter_moves_up_front_and_leaves_no_blank_line_at_the_end(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("move", doc, "Three", "before", "One") == (0, "Doc > Three: moved before Doc > One.")
    assert doc.read_bytes() == (
        b"# Doc\n\n"
        b"## Three\n\nthird\n\n"
        b"## One\n\nfirst\n\n### One A\n\na\n\n"
        b"## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n#### Deeper\n\ndeepest\n"
    )


def test_a_chapter_moved_to_the_end_leaves_its_blank_line_behind(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("move", doc, "One", "after", "Three") == (0, "Doc > One: moved after Doc > Three.")
    assert doc.read_bytes() == (
        b"# Doc\n\n"
        b"## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n#### Deeper\n\ndeepest\n\n"
        b"## Three\n\nthird\n\n"
        b"## One\n\nfirst\n\n### One A\n\na\n"
    )


def test_a_promoted_chapter_takes_its_subchapters_up_with_it(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("move", doc, "Deep", "after", "Two") == (0, "Doc > Two > Deep: moved after Doc > Two, one level up.")
    assert doc.read_bytes() == (
        b"# Doc\n\n"
        b"## One\n\nfirst\n\n### One A\n\na\n\n"
        b"## Two\n\nsecond\n\n"
        b"## Deep\n\ndeeper\n\n### Deeper\n\ndeepest\n\n"
        b"## Three\n\nthird\n"
    )


def test_a_demoted_chapter_lands_among_deeper_siblings(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("move", doc, "Three", "before", "One A") == (0, "Doc > Three: moved before Doc > One > One A, one level down.")
    assert doc.read_bytes() == (
        b"# Doc\n\n"
        b"## One\n\nfirst\n\n### Three\n\nthird\n\n### One A\n\na\n\n"
        b"## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n#### Deeper\n\ndeepest\n"
    )


def test_crlf_line_endings_stay(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc.replace(b"\n", b"\r\n"))
    assert calm_md("move", doc, "Deep", "after", "Two")[0] == 0
    assert doc.read_bytes() == (
        b"# Doc\n\n"
        b"## One\n\nfirst\n\n### One A\n\na\n\n"
        b"## Two\n\nsecond\n\n"
        b"## Deep\n\ndeeper\n\n### Deeper\n\ndeepest\n\n"
        b"## Three\n\nthird\n"
    ).replace(b"\n", b"\r\n")


def test_the_t_line_stays_on_top(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(t_line + b"\n" + nested_doc)
    assert calm_md("move", doc, "Three", "before", "One")[0] == 0
    assert doc.read_bytes() == t_line + (
        b"\n# Doc\n\n"
        b"## Three\n\nthird\n\n"
        b"## One\n\nfirst\n\n### One A\n\na\n\n"
        b"## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n#### Deeper\n\ndeepest\n"
    )


def test_a_shift_past_level_six_is_refused(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    deep_doc = b"# Doc\n\n## A\n\n### B\n\n#### C\n\n##### E\n\ne\n\n## F\n\n### G\n\n#### H\n\nh\n"
    doc.write_bytes(deep_doc)
    exit_code, answer = calm_md("move", doc, "F", "after", "E")
    assert exit_code == 1
    assert "#######" in answer
    assert doc.read_bytes() == deep_doc


def test_an_underlined_heading_is_not_shifted(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    underlined_doc = b"# Doc\n\n## One\n\n### Inner\n\ni\n\nTwo\n---\n\nsecond\n"
    doc.write_bytes(underlined_doc)
    exit_code, answer = calm_md("move", "--as-is", doc, "Two", "before", "Inner")
    assert exit_code == 1
    assert "underlined" in answer
    assert doc.read_bytes() == underlined_doc


@pytest.mark.parametrize(
    "arguments, refusal_words",
    [
        (("One", "behind", "Two"), "move takes"),
        (("@3", "after", "Two"), "title"),
        (("Two", "after", "Deep"), "into its own subchapters"),
        (("Two", "before", "Two"), "next to itself"),
    ],
)
def test_refusals_leave_the_file_as_it_was(tmp_path, calm_md, arguments, refusal_words):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    exit_code, answer = calm_md("move", doc, *arguments)
    assert exit_code == 1
    assert refusal_words in answer
    assert doc.read_bytes() == nested_doc

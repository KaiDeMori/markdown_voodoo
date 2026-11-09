import pytest

t_line = "\U000FE054".encode("utf-8") + b"12 100"

nested_doc = b"# Doc\n\n## One\n\nfirst\n\n## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n## Three\n\nthird\n"

new_chapter = b"## New\n\nnew\n"


def test_after_lands_behind_the_named_chapter_and_its_subchapters(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("insert", doc, "after", "Two", stdin=new_chapter) == (0, "Doc > New: inserted after Doc > Two, 4 lines.")
    assert doc.read_bytes() == b"# Doc\n\n## One\n\nfirst\n\n## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n## New\n\nnew\n\n## Three\n\nthird\n"


def test_before_lands_right_before_the_named_heading(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("insert", doc, "before", "Two", stdin=new_chapter) == (0, "Doc > New: inserted before Doc > Two, 4 lines.")
    assert doc.read_bytes() == b"# Doc\n\n## One\n\nfirst\n\n## New\n\nnew\n\n## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n## Three\n\nthird\n"


def test_after_the_last_chapter_a_blank_line_comes_before_the_heading(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("insert", doc, "after", "Three", stdin=new_chapter) == (0, "Doc > New: inserted after Doc > Three, 3 lines.")
    assert doc.read_bytes() == nested_doc + b"\n" + new_chapter


def test_a_deeper_chapter_hangs_under_the_chapter_before_it(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("insert", doc, "after", "Two", stdin=b"### Deeper\n\nx\n") == (0, "Doc > Two > Deeper: inserted after Doc > Two, 4 lines.")
    assert doc.read_bytes() == b"# Doc\n\n## One\n\nfirst\n\n## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n### Deeper\n\nx\n\n## Three\n\nthird\n"


def test_crlf_files_get_crlf_lines(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc.replace(b"\n", b"\r\n"))
    assert calm_md("insert", doc, "before", "Two", stdin=new_chapter)[0] == 0
    assert doc.read_bytes() == b"# Doc\n\n## One\n\nfirst\n\n## New\n\nnew\n\n## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n## Three\n\nthird\n".replace(b"\n", b"\r\n")


def test_the_t_line_stays_on_top(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(t_line + b"\n" + nested_doc)
    assert calm_md("insert", doc, "before", "One", stdin=new_chapter)[0] == 0
    assert doc.read_bytes() == t_line + b"\n# Doc\n\n## New\n\nnew\n\n## One\n\nfirst\n\n## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n## Three\n\nthird\n"


@pytest.mark.parametrize(
    "arguments, stdin, refusal_words",
    [
        (("behind", "Two"), new_chapter, "after or before"),
        (("after", "@3"), new_chapter, "title"),
        (("after", "Two"), b"just text\n", "heading line"),
        (("after", "Two"), b"", "Nothing to insert"),
        (("before", "Deep"), new_chapter, "pull"),
    ],
)
def test_refusals_leave_the_file_as_it_was(tmp_path, calm_md, arguments, stdin, refusal_words):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    exit_code, answer = calm_md("insert", doc, *arguments, stdin=stdin)
    assert exit_code == 1
    assert refusal_words in answer
    assert doc.read_bytes() == nested_doc

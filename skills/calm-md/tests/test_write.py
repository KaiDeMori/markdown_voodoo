two_chapter_doc = b"# Doc\n\n## One\n\nfirst\n\n## Two\n\nsecond\n"


def test_write_replaces_one_chapter_and_keeps_the_blank_line_before_the_next(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(two_chapter_doc)
    assert calm_md("write", doc, "One", stdin=b"## One\n\nchanged") == (0, "Doc > One: 4 lines became 4 lines.")
    assert doc.read_bytes() == b"# Doc\n\n## One\n\nchanged\n\n## Two\n\nsecond\n"


def test_an_issue_names_its_heading_not_a_line_of_the_unwritten_doc(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(two_chapter_doc)
    exit_code, answer = calm_md("write", doc, "One", stdin=b"## Two\n\nclash\n")
    assert exit_code == 1
    assert "Doc > Two: MD024" in answer
    assert doc.read_bytes() == two_chapter_doc


def test_write_refuses_an_empty_chapter(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(two_chapter_doc)
    assert calm_md("write", doc, "One", stdin=b"") == (1, "Nothing to write; an empty chapter is refused, and the file stays as it was.")
    assert doc.read_bytes() == two_chapter_doc

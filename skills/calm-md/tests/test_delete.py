t_line = "\U000FE054".encode("utf-8") + b"12 100"

nested_doc = b"# Doc\n\n## One\n\nfirst\n\n## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n## Three\n\nthird\n"


def test_a_middle_chapter_goes_with_its_subchapters_and_the_rest_stays_byte_for_byte(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("delete", doc, "Two") == (0, "Doc > Two: deleted, 8 lines.")
    assert doc.read_bytes() == b"# Doc\n\n## One\n\nfirst\n\n## Three\n\nthird\n"


def test_the_first_subchapter_goes_and_its_parent_keeps_its_heading(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("delete", doc, "One") == (0, "Doc > One: deleted, 4 lines.")
    assert doc.read_bytes() == b"# Doc\n\n## Two\n\nsecond\n\n### Deep\n\ndeeper\n\n## Three\n\nthird\n"


def test_the_last_chapter_takes_the_blank_lines_before_it_along(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    assert calm_md("delete", doc, "Three") == (0, "Doc > Three: deleted, 3 lines.")
    assert doc.read_bytes() == b"# Doc\n\n## One\n\nfirst\n\n## Two\n\nsecond\n\n### Deep\n\ndeeper\n"


def test_crlf_line_endings_stay(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc.replace(b"\n", b"\r\n"))
    assert calm_md("delete", doc, "Three")[0] == 0
    assert doc.read_bytes() == b"# Doc\n\n## One\n\nfirst\n\n## Two\n\nsecond\n\n### Deep\n\ndeeper\n".replace(b"\n", b"\r\n")


def test_the_t_line_stays_on_top(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(t_line + b"\n" + nested_doc)
    assert calm_md("delete", doc, "Two")[0] == 0
    assert doc.read_bytes() == t_line + b"\n# Doc\n\n## One\n\nfirst\n\n## Three\n\nthird\n"


def test_the_t_line_keeps_its_line_ending_when_the_only_chapter_goes(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(t_line + b"\n# Doc\n\nbody\n")
    assert calm_md("delete", doc, "Doc") == (0, "Doc: deleted, 3 lines.")
    assert doc.read_bytes() == t_line + b"\n"


def test_front_matter_stays_when_the_only_chapter_goes(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(b"---\ntitle: notes\n---\n\n# Doc\n\nbody\n")
    assert calm_md("delete", doc, "Doc")[0] == 0
    assert doc.read_bytes() == b"---\ntitle: notes\n---\n"


def test_a_number_is_refused_and_the_file_stays(tmp_path, calm_md):
    doc = tmp_path / "doc.md"
    doc.write_bytes(nested_doc)
    exit_code, answer = calm_md("delete", doc, "@3")
    assert exit_code == 1
    assert "title" in answer
    assert doc.read_bytes() == nested_doc

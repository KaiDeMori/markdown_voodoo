import re
import sys
from pathlib import Path

UNCLEAR_HEADING = "## Unclear"
PAGES_LINE_PATTERN = re.compile(r"^Pages: (\d+)$", re.MULTILINE)


def strip_trailing_blank_lines(lines):
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def split_page_file(page_file_text, page_number):
    lines = page_file_text.splitlines()
    page_heading_index = lines.index(f"## Page {page_number}")
    unclear_heading_index = lines.index(UNCLEAR_HEADING)
    header_lines = strip_trailing_blank_lines(lines[:page_heading_index])
    chapter_lines = strip_trailing_blank_lines(lines[page_heading_index:unclear_heading_index])
    unclear_entries = [line for line in lines[unclear_heading_index + 1:] if line.strip()]
    return header_lines, chapter_lines, unclear_entries


def main():
    """Joins the page files in page order: the header once, every page chapter, and all Unclear entries in one chapter at the end. Refuses while a page is missing or unread."""
    pages_folder = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    page_file_paths = sorted(pages_folder.glob("page_*.md"))
    if not page_file_paths:
        sys.exit(f"not merged: no page files in {pages_folder}")
    page_count = int(PAGES_LINE_PATTERN.search(page_file_paths[0].read_text(encoding="utf-8")).group(1))
    header_lines = None
    chapters = []
    unclear_entries = []
    missing_pages = []
    unread_pages = []
    for page_number in range(1, page_count + 1):
        page_file_path = pages_folder / f"page_{page_number:03}.md"
        if not page_file_path.exists():
            missing_pages.append(page_number)
            continue
        page_header_lines, chapter_lines, page_unclear_entries = split_page_file(page_file_path.read_text(encoding="utf-8"), page_number)
        if len(chapter_lines) <= 1:
            unread_pages.append(page_number)
            continue
        header_lines = header_lines or page_header_lines
        chapters.append(chapter_lines)
        unclear_entries += page_unclear_entries
    if missing_pages or unread_pages:
        sys.exit(f"not merged: missing pages {missing_pages or 'none'}, unread pages {unread_pages or 'none'}")
    output_lines = header_lines + [""]
    for chapter_lines in chapters:
        output_lines += chapter_lines + [""]
    output_lines += [UNCLEAR_HEADING, ""]
    if unclear_entries:
        output_lines += unclear_entries + [""]
    output_path.write_text("\n".join(output_lines), encoding="utf-8", newline="\n")
    print(f"{page_count} pages, {len(unclear_entries)} unclear entries -> {output_path}")


if __name__ == "__main__":
    main()

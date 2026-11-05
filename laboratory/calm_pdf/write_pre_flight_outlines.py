import datetime
import sys
from pathlib import Path

import pymupdf

READER_LABEL = "Haiku 5.5"
RENDER_DPI = 240


def build_header_lines(pdf_path, title, page_count):
    return [
        f"# {title}",
        "",
        f"Source: {pdf_path.name}",
        f"Pages: {page_count}",
        f"Converted: {datetime.date.today().isoformat()}, {READER_LABEL}, read by sight from {RENDER_DPI} dpi views",
        "",
    ]


def main():
    """Writes one pre_flight_outline per page and keeps every page file that already exists, so a rerun never wipes a page that was read."""
    pdf_path = Path(sys.argv[1])
    pages_folder = Path(sys.argv[2])
    title = sys.argv[3]
    pages_folder.mkdir(parents=True, exist_ok=True)
    page_count = len(pymupdf.open(pdf_path))
    header_lines = build_header_lines(pdf_path, title, page_count)
    written_count = 0
    for page_number in range(1, page_count + 1):
        page_file_path = pages_folder / f"page_{page_number:03}.md"
        if page_file_path.exists():
            continue
        lines = header_lines + [f"## Page {page_number}", "", "## Unclear", ""]
        page_file_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        written_count += 1
    print(f"{written_count} pre_flight_outlines written, {page_count - written_count} kept -> {pages_folder}")


if __name__ == "__main__":
    main()

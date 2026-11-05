import sys
from pathlib import Path

import pymupdf

OVERVIEW_LONG_SIDE = 1000
GLASS_LONG_SIDE = 1000
POINTS_PER_INCH = 72


def main():
    pdf_path = Path(sys.argv[1])
    page_number = int(sys.argv[2])
    x, y, width, height = (float(value) for value in sys.argv[3:7])
    output_folder = Path(sys.argv[7])
    page = pymupdf.open(pdf_path)[page_number - 1]
    points_per_overview_pixel = max(page.rect.width, page.rect.height) / OVERVIEW_LONG_SIDE
    visible_region = pymupdf.Rect(x, y, x + width, y + height) * points_per_overview_pixel
    dpi = GLASS_LONG_SIDE * POINTS_PER_INCH / max(visible_region.width, visible_region.height)
    pixmap = page.get_pixmap(dpi=round(dpi), clip=visible_region)
    output_path = output_folder / f"page_{page_number:03}_glass_{round(x)}_{round(y)}_{round(width)}x{round(height)}.png"
    pixmap.save(output_path)
    print(f"{pixmap.width}x{pixmap.height} at {round(dpi)} dpi -> {output_path}")


if __name__ == "__main__":
    main()

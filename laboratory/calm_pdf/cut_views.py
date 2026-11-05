import math
import sys
from pathlib import Path

import pymupdf
from PIL import Image

RENDER_DPI = 240
OVERVIEW_LONG_SIDE = 1000
BAND_HEIGHT = 700
MINIMUM_BAND_OVERLAP = 170
MAXIMUM_VIEW_SIDE = 2000


def render_page(page):
    pixmap = page.get_pixmap(dpi=RENDER_DPI)
    return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def scale_to_long_side(image, long_side):
    scale = long_side / max(image.size)
    size = (round(image.width * scale), round(image.height * scale))
    return image.resize(size, Image.Resampling.LANCZOS)


def cap_view_side(view_image):
    """Requests with many images accept only images within the API's per-side limit, and every reader's range makes such a request."""
    if max(view_image.size) <= MAXIMUM_VIEW_SIDE:
        return view_image
    return scale_to_long_side(view_image, MAXIMUM_VIEW_SIDE)


def band_tops(page_height):
    """Spreads the bands evenly from top to bottom, with as many bands as it takes for neighbours to overlap by at least the minimum, so that every line lies whole in at least one band."""
    if page_height <= BAND_HEIGHT:
        return [0]
    band_count = math.ceil((page_height - MINIMUM_BAND_OVERLAP) / (BAND_HEIGHT - MINIMUM_BAND_OVERLAP))
    step = (page_height - BAND_HEIGHT) / (band_count - 1)
    return [round(index * step) for index in range(band_count)]


def main():
    pdf_path = Path(sys.argv[1])
    output_folder = Path(sys.argv[2])
    output_folder.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(pdf_path)
    view_count = 0
    for page_number, page in enumerate(document, start=1):
        page_image = render_page(page)
        scale_to_long_side(page_image, OVERVIEW_LONG_SIDE).save(output_folder / f"page_{page_number:03}_overview.png")
        view_count += 1
        for band_number, top in enumerate(band_tops(page_image.height), start=1):
            bottom = min(top + BAND_HEIGHT, page_image.height)
            band_image = cap_view_side(page_image.crop((0, top, page_image.width, bottom)))
            band_image.save(output_folder / f"page_{page_number:03}_band_{band_number}.png")
            view_count += 1
    total_bytes = sum(path.stat().st_size for path in output_folder.glob("page_*.png"))
    print(f"{len(document)} pages, {view_count} views, {total_bytes / 1_000_000:.1f} MB -> {output_folder}")


if __name__ == "__main__":
    main()

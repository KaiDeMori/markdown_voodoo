"""calm-glass: see a large image clearly, one view at a time.

    calm-glass overview <image>
    calm-glass fit <image>
    calm-glass middle <image>
    calm-glass edges <image>
    calm-glass spot <image> <x> <y> [zoom]
    calm-glass band <image> <x> <y> <width> <height>

The overview shows the whole image, its long side at 1000 px at most.
A fit shows the whole image as large as the frame takes it untouched; an image that already fits, in a format the frame reads, stays as it is.
The middle and the edges are the largest squares at the center and at both
ends of the long side. A spot takes a point in the overview's pixels and shows
it zoom times closer, in the overview's shape. A band takes a strip of small
text, given by its top left corner and size in the overview's pixels, and
stacks it in overlapping strips into one sheet.
Every view but the overview brings its long side to 1000 px.
Every view answers with one line; ImageMagick does the pixel work.
Views land in the workspace's scratchpad/glass/, the workspace being the current folder.
"""

import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

view_long_side = 1000
tile_size = 28
# The frame takes an image untouched while it stays within both: this many tiles, and this long a side.
frame_tile_limit = 4784
frame_long_side_limit = 2576
# The formats the frame reads as they are; any other gets drawn into a png.
frame_formats = (".png", ".jpg", ".jpeg", ".gif", ".webp")
default_zoom = 4.0
views_folder = Path.cwd() / "scratchpad" / "glass"
usage = (
    "usage: calm-glass overview|fit|middle|edges <image> | calm-glass spot <image> <x> <y> [zoom]"
    " | calm-glass band <image> <x> <y> <width> <height>"
)


@dataclass
class View:
    name: str
    left: int
    top: int
    region_width: int
    region_height: int
    width: int
    height: int


def fail(message):
    print(message)
    sys.exit(1)


def magick(*arguments):
    try:
        result = subprocess.run(["magick", *arguments], capture_output=True, text=True)
    except FileNotFoundError:
        fail("magick is not on the PATH: calm-glass needs ImageMagick 7")
    if result.returncode != 0:
        reason = result.stderr.strip().splitlines()
        fail(f"magick refused: {reason[-1] if reason else 'no reason given'}")
    return result.stdout


def number(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def tokens(width, height):
    return math.ceil(width / tile_size) * math.ceil(height / tile_size)


def image_size(image):
    width, height = magick("identify", "-ping", "-format", "%w %h", f"{image}[0]").split()
    return int(width), int(height)


def overview_size(width, height):
    scale = min(1.0, view_long_side / max(width, height))
    return max(1, round(width * scale)), max(1, round(height * scale))


def fit_size(width, height):
    # The largest size within the frame's limits, never larger than the image: the long side shrinks pixel by pixel until the tiles fit.
    long_side = max(width, height)
    for fit_long_side in range(min(long_side, frame_long_side_limit), 0, -1):
        scale = fit_long_side / long_side
        fit_width, fit_height = max(1, round(width * scale)), max(1, round(height * scale))
        if tokens(fit_width, fit_height) <= frame_tile_limit:
            return fit_width, fit_height
    return 1, 1


def close_view(name, left, top, region_width, region_height):
    # Every view but the overview brings its long side to 1000 px, magnifying small regions.
    scale = view_long_side / max(region_width, region_height)
    width = max(1, round(region_width * scale))
    height = max(1, round(region_height * scale))
    return View(name, left, top, region_width, region_height, width, height)


def view_path(image, view):
    return views_folder / f"{Path(image).stem}_{view.name}.png"


def render(image, views):
    # One read of the image for all views: mpr keeps the pixels in memory between the crops.
    views_folder.mkdir(parents=True, exist_ok=True)
    arguments = [f"{image}[0]", "-write", "mpr:source", "+delete"]
    for view in views:
        arguments += [
            "(", "mpr:source",
            "-crop", f"{view.region_width}x{view.region_height}+{view.left}+{view.top}", "+repage",
            "-resize", f"{view.width}x{view.height}!",
            "-write", str(view_path(image, view)), ")",
        ]
    magick(*arguments, "null:")


def describe(image, view, label):
    return (
        f"{label}: {view.width}×{view.height}, {tokens(view.width, view.height)} tokens, "
        f"1 px = {number(view.region_width / view.width)} original px -> {view_path(image, view).as_posix()}"
    )


def to_overview(width, height, start, end):
    # A stretch of the long side, from original pixels into the overview's.
    scale = max(overview_size(width, height)) / max(width, height)
    return f"{round(start * scale)}-{round(end * scale)}"


def span(width, height, view):
    # Where a square lies along the long side, in the overview's pixels.
    if width > height:
        return f" (overview x {to_overview(width, height, view.left, view.left + view.region_width)})"
    if height > width:
        return f" (overview y {to_overview(width, height, view.top, view.top + view.region_height)})"
    return ""


def overview(image):
    width, height = image_size(image)
    view = View("overview", 0, 0, width, height, *overview_size(width, height))
    render(image, [view])
    print(describe(image, view, f"overview of {width}×{height}"))


def fit(image):
    width, height = image_size(image)
    fit_width, fit_height = fit_size(width, height)
    if (fit_width, fit_height) == (width, height) and Path(image).suffix.lower() in frame_formats:
        print(f"fit of {width}×{height}: fits as it is, {tokens(width, height)} tokens -> {Path(image).resolve().as_posix()}")
        return
    view = View("fit", 0, 0, width, height, fit_width, fit_height)
    render(image, [view])
    print(describe(image, view, f"fit of {width}×{height}"))


def middle(image):
    width, height = image_size(image)
    side = min(width, height)
    view = close_view("middle", (width - side) // 2, (height - side) // 2, side, side)
    render(image, [view])
    print(describe(image, view, f"middle{span(width, height, view)}"))


def edges(image):
    width, height = image_size(image)
    if width == height:
        fail("a square image has no edges beyond its middle")
    side = min(width, height)
    length = max(width, height)
    if width > height:
        first = close_view("edge_left", 0, 0, side, side)
        last = close_view("edge_right", width - side, 0, side, side)
        labels = ("edge left", "edge right")
    else:
        first = close_view("edge_top", 0, 0, side, side)
        last = close_view("edge_bottom", 0, height - side, side, side)
        labels = ("edge top", "edge bottom")
    render(image, [first, last])
    print(describe(image, first, f"{labels[0]}{span(width, height, first)}"))
    print(describe(image, last, f"{labels[1]}{span(width, height, last)}"))

    # On a very long image, the middle and the edges no longer overlap.
    middle_start = (length - side) // 2
    if middle_start > side:
        axis = "x" if width > height else "y"
        first_gap = to_overview(width, height, side, middle_start)
        last_gap = to_overview(width, height, middle_start + side, length - side)
        print(f"the middle and the edges leave gaps at overview {axis} {first_gap} and {last_gap}: spots cover them")


def spot(image, x, y, zoom):
    width, height = image_size(image)
    overview_width, overview_height = overview_size(width, height)
    if not (0 <= x <= overview_width and 0 <= y <= overview_height):
        fail(f"{number(x)},{number(y)} is outside the overview's {overview_width}×{overview_height}")
    if zoom < 1:
        fail("the zoom starts at 1, the overview itself")

    # The region keeps the overview's shape; near an edge it moves inside rather than shrinking.
    region_width = max(1, round(width / zoom))
    region_height = max(1, round(height / zoom))
    center_x = x * width / overview_width
    center_y = y * height / overview_height
    left = min(max(0, round(center_x - region_width / 2)), width - region_width)
    top = min(max(0, round(center_y - region_height / 2)), height - region_height)
    view = close_view(f"spot_{number(x)}_{number(y)}_x{number(zoom)}", left, top, region_width, region_height)
    render(image, [view])

    moved = ""
    shown_x = (left + region_width / 2) * overview_width / width
    shown_y = (top + region_height / 2) * overview_height / height
    if abs(shown_x - x) >= 1 or abs(shown_y - y) >= 1:
        moved = f", moved to {round(shown_x)},{round(shown_y)} to stay inside"
    print(describe(image, view, f"spot ×{number(zoom)} at {number(x)},{number(y)}{moved}"))


def band(image, x, y, band_width, band_height):
    width, height = image_size(image)
    overview_width, overview_height = overview_size(width, height)
    if band_width <= 0 or band_height <= 0 or x < 0 or y < 0 or x + band_width > overview_width or y + band_height > overview_height:
        fail(f"the band has to lie inside the overview's {overview_width}×{overview_height}")
    left = round(x * width / overview_width)
    top = round(y * height / overview_height)
    region_width = max(1, min(round(band_width * width / overview_width), width - left))
    region_height = max(1, min(round(band_height * height / overview_height), height - top))

    # Strips stacked into a sheet as square as possible; each overlaps the next by half a band height,
    # so a character cut at one strip's end is whole in the next.
    strips = max(1, round(math.sqrt(region_width / region_height)))
    overlap = region_height // 2 if strips > 1 else 0
    strip_width = math.ceil((region_width + (strips - 1) * overlap) / strips)
    sheet = close_view(f"band_{number(x)}_{number(y)}_{number(band_width)}x{number(band_height)}",
                       0, 0, strip_width, strips * region_height)

    views_folder.mkdir(parents=True, exist_ok=True)
    arguments = [f"{image}[0]", "-crop", f"{region_width}x{region_height}+{left}+{top}", "+repage",
                 "-write", "mpr:band", "+delete"]
    for strip in range(strips):
        strip_left = min(strip * (strip_width - overlap), region_width - strip_width)
        arguments += ["(", "mpr:band", "-crop", f"{strip_width}x{region_height}+{strip_left}+0", "+repage", ")"]
    arguments += ["-append", "-resize", f"{sheet.width}x{sheet.height}!", str(view_path(image, sheet))]
    magick(*arguments)
    print(describe(image, sheet, f"band in {strips} strips, overlapping by {overlap} original px"))


def main(arguments):
    commands = {"overview": overview, "fit": fit, "middle": middle, "edges": edges}
    if len(arguments) < 2 or arguments[0] not in (*commands, "spot", "band"):
        fail(usage)
    image = arguments[1]
    if not Path(image).is_file():
        fail(f"no such file: {image}")
    try:
        if arguments[0] in commands and len(arguments) == 2:
            commands[arguments[0]](image)
        elif arguments[0] == "spot" and len(arguments) in (4, 5):
            x, y = float(arguments[2]), float(arguments[3])
            zoom = float(arguments[4].lstrip("x×")) if len(arguments) == 5 else default_zoom
            spot(image, x, y, zoom)
        elif arguments[0] == "band" and len(arguments) == 6:
            band(image, *(float(value) for value in arguments[2:6]))
        else:
            fail(usage)
    except ValueError:
        fail(usage)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])

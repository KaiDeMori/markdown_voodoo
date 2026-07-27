import urllib.request
from pathlib import Path

FONT_DIRECTORY = Path(__file__).parent / "fonts"
RELEASE_BASE = "https://github.com/satbyy/go-noto-universal/releases/download/v7.0"

FONT_FILENAMES = (
    "GoNotoCurrent-Regular.ttf",
    "GoNotoAncient.ttf",
    "GoNotoEuropeAmericas.ttf",
    "GoNotoAfricaMiddleEast.ttf",
    "GoNotoSouthAsia.ttf",
    "GoNotoAsiaHistorical.ttf",
    "GoNotoEastAsia.ttf",
    "GoNotoCJKCore.ttf",
)


def download_font(filename):
    destination = FONT_DIRECTORY / filename
    if destination.exists():
        print(f"already present, skipping: {filename}")
        return
    print(f"downloading {filename}")
    urllib.request.urlretrieve(f"{RELEASE_BASE}/{filename}", destination)


def main():
    FONT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for filename in FONT_FILENAMES:
        download_font(filename)


if __name__ == "__main__":
    main()

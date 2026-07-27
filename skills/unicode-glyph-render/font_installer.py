import urllib.request
from pathlib import Path

FONT_DIRECTORY = Path(__file__).parent / "fonts"

GO_NOTO_RELEASE_BASE = "https://github.com/satbyy/go-noto-universal/releases/download/v7.0"
GO_NOTO_FILENAMES = (
    "GoNotoCurrent-Regular.ttf",
    "GoNotoAncient.ttf",
    "GoNotoEuropeAmericas.ttf",
    "GoNotoAfricaMiddleEast.ttf",
    "GoNotoSouthAsia.ttf",
    "GoNotoAsiaHistorical.ttf",
    "GoNotoEastAsia.ttf",
    "GoNotoCJKCore.ttf",
)

LAST_RESORT_RELEASE_BASE = "https://github.com/unicode-org/last-resort-font/releases/download/17.000"
LAST_RESORT_FILENAMES = ("LastResort-Regular.ttf",)

NOTO_EMOJI_RAW_BASE = "https://raw.githubusercontent.com/googlefonts/noto-emoji/v2.051/fonts"
NOTO_EMOJI_FILENAMES = ("NotoColorEmoji.ttf",)

DOWNLOADS = (
    (GO_NOTO_RELEASE_BASE, GO_NOTO_FILENAMES),
    (LAST_RESORT_RELEASE_BASE, LAST_RESORT_FILENAMES),
    (NOTO_EMOJI_RAW_BASE, NOTO_EMOJI_FILENAMES),
)


def download_font(base_url, filename):
    destination = FONT_DIRECTORY / filename
    if destination.exists():
        print(f"already present, skipping: {filename}")
        return
    print(f"downloading {filename}")
    urllib.request.urlretrieve(f"{base_url}/{filename}", destination)


def main():
    FONT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for base_url, filenames in DOWNLOADS:
        for filename in filenames:
            download_font(base_url, filename)


if __name__ == "__main__":
    main()

import io
import urllib.request
import zipfile
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

FIRA_CODE_ARCHIVE_URL = "https://github.com/tonsky/FiraCode/releases/download/6.2/Fira_Code_v6.2.zip"
FIRA_CODE_ARCHIVE_MEMBERS = ("ttf/FiraCode-Retina.ttf",)

DOWNLOADS = (
    (GO_NOTO_RELEASE_BASE, GO_NOTO_FILENAMES),
    (LAST_RESORT_RELEASE_BASE, LAST_RESORT_FILENAMES),
    (NOTO_EMOJI_RAW_BASE, NOTO_EMOJI_FILENAMES),
)

ARCHIVE_DOWNLOADS = (
    (FIRA_CODE_ARCHIVE_URL, FIRA_CODE_ARCHIVE_MEMBERS),
)


def download_font(base_url, filename):
    destination = FONT_DIRECTORY / filename
    if destination.exists():
        print(f"already present, skipping: {filename}")
        return
    print(f"downloading {filename}")
    urllib.request.urlretrieve(f"{base_url}/{filename}", destination)


def extract_fonts_from_archive(archive_url, members):
    missing_members = []
    for member in members:
        filename = Path(member).name
        if (FONT_DIRECTORY / filename).exists():
            print(f"already present, skipping: {filename}")
        else:
            missing_members.append(member)
    if not missing_members:
        return
    print(f"downloading {archive_url.rsplit('/', 1)[-1]}")
    with urllib.request.urlopen(archive_url) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    for member in missing_members:
        filename = Path(member).name
        print(f"extracting {filename}")
        (FONT_DIRECTORY / filename).write_bytes(archive.read(member))


def main():
    FONT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for base_url, filenames in DOWNLOADS:
        for filename in filenames:
            download_font(base_url, filename)
    for archive_url, members in ARCHIVE_DOWNLOADS:
        extract_fonts_from_archive(archive_url, members)


if __name__ == "__main__":
    main()

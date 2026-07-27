import urllib.request
from pathlib import Path

GITHUB_TREE_URL = "https://api.github.com/repos/google/fonts/git/trees/main?recursive=1"
OUTPUT_PATH = Path(__file__).parent / "font_tree.json"


def main():
    request = urllib.request.Request(
        GITHUB_TREE_URL, headers={"User-Agent": "unicode-glyph-render"}
    )
    with urllib.request.urlopen(request) as response:
        data = response.read()
    OUTPUT_PATH.write_bytes(data)
    print(f"saved {len(data)} bytes to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

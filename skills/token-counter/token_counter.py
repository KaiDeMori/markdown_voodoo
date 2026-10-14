"""token_counter: counts how many tokens files take up for a Claude model, before they enter a window.

Usage: token_counter.py <file> [<file> ...]
"""

import base64
import pathlib
import sys

from anthropic import Anthropic

model_name = "claude-opus-5-5"
hall_key_location = pathlib.Path(__file__).parent / "hall_key.txt"
image_media_types = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

sys.stdout.reconfigure(encoding="utf-8")

client = Anthropic(api_key=hall_key_location.read_text(encoding="utf-8").strip())


def count_tokens(file_location):
    media_type = image_media_types.get(file_location.suffix.lower())
    if media_type:
        image_data = base64.b64encode(file_location.read_bytes()).decode("ascii")
        message_content = [{"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}}]
    else:
        message_content = file_location.read_text(encoding="utf-8")
    return client.messages.count_tokens(
        model=model_name,
        messages=[{"role": "user", "content": message_content}],
    ).input_tokens


total_count = 0
for file_location in map(pathlib.Path, sys.argv[1:]):
    token_count = count_tokens(file_location)
    print(f"{file_location.name}: {token_count} tokens")
    total_count += token_count
if len(sys.argv) > 2:
    print(f"total: {total_count} tokens")

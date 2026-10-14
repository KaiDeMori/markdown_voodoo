"""token_counter: counts how many tokens a file takes up for a Claude model, before it enters a window.

Usage: token_counter.py <file>
"""

import base64
import pathlib
import sys

from anthropic import Anthropic

model_name = "claude-opus-5-5"
API_key_location = pathlib.Path(__file__).parent / "API_key.txt"
image_media_types = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

sys.stdout.reconfigure(encoding="utf-8")

file_location = pathlib.Path(sys.argv[1])
media_type = image_media_types.get(file_location.suffix.lower())
if media_type:
    image_data = base64.b64encode(file_location.read_bytes()).decode("ascii")
    message_content = [{"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}}]
else:
    message_content = file_location.read_text(encoding="utf-8")

token_count = Anthropic(api_key=API_key_location.read_text(encoding="utf-8").strip()).messages.count_tokens(
    model=model_name,
    messages=[{"role": "user", "content": message_content}],
).input_tokens
print(f"{file_location.name}: {token_count} tokens")

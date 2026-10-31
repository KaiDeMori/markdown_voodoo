"""token_counter: counts how many tokens files take up for a Claude model, before they enter a window.

A doc can carry its count on its first line, the T line: U+FE054, directly followed by the number, a space, and the size in bytes of the doc below the line.
The old T, U+E054, is still read, and every read swaps in the new one; the line keeps its numbers.
token-counter reads that line instead of counting while the doc keeps that size, and says so with (cached); a doc of another size gets counted fresh, and a line without a size is trusted as it is.
With --write, it counts a doc fresh, without its T line, and writes or updates the line, size included; SKILL.md files and images get none.
With -s, it counts the text that follows instead of a file.
The endpoint counts a whole message, and Anthropic calls its count an estimate; every count leaves out the tokens that wrap any message, the role markers around a turn.
Whatever goes wrong ends in one line, and exit 1.
Usage: token_counter.py [--write] <file> [<file> ...]
       token_counter.py -s <text>
"""

import base64
import pathlib
import re
import sys

from anthropic import Anthropic

model_name = "claude-opus-5-5"
# What wraps any message for that model, measured: the text "A" counted 9 tokens as a message.
message_wrapper_tokens = 8
hall_key_location = pathlib.Path(__file__).parent / "hall_key.txt"
image_media_types = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
# The T is U+FE054, in plane 15's private use area, with the T's 0x54 at its end; the old T, U+E054 in the BMP, is still read.
t_character = "\U000FE054"
old_t_character = "\U0000E054"
# The T line: the T, directly followed by the count; then a space and the doc's size in bytes, which older lines lack; then the line's end.
t_line_pattern = re.compile("([\U0000E054\U000FE054])([0-9]+)(?: ([0-9]+))?(\r\n|\r|\n)")

sys.stdout.reconfigure(encoding="utf-8")


def count_message(message_content):
    # The content's own tokens: the message's count without its wrapper.
    return client.messages.count_tokens(
        model=model_name,
        messages=[{"role": "user", "content": message_content}],
    ).input_tokens - message_wrapper_tokens


def token_text(count):
    return "1 token" if count == 1 else f"{count} tokens"


def count_file(file_location, write):
    # The count, and what the answer adds to it.
    media_type = image_media_types.get(file_location.suffix.lower())
    if media_type:
        image_data = base64.b64encode(file_location.read_bytes()).decode("ascii")
        return count_message([{"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}}]), ""
    # Bytes, not text mode, so a written doc keeps its own line endings.
    text = file_location.read_bytes().decode("utf-8")
    t_line = t_line_pattern.match(text)
    # An old T heals on every read: only the T changes, and the line keeps its numbers and its ending; --write rewrites the whole line anyway.
    if t_line and t_line.group(1) == old_t_character and not write:
        file_location.write_bytes((t_character + text[1:]).encode("utf-8"))
    doc = text[t_line.end():] if t_line else text
    doc_size = len(doc.encode("utf-8"))
    # A cached count holds while the doc below its line keeps its size; a line without a size always holds.
    if t_line and not write and (t_line.group(3) is None or int(t_line.group(3)) == doc_size):
        return int(t_line.group(2)), " (cached)"
    # Counted as text mode reads it, so a count stays what it always was.
    token_count = count_message(re.sub(r"\r\n|\r", "\n", doc))
    # A SKILL.md keeps its front matter first, so it never gets a T line.
    if write and file_location.name != "SKILL.md":
        line_ending = t_line.group(4) if t_line else ("\r\n" if "\r\n" in doc else "\n")
        file_location.write_bytes(f"{t_character}{token_count} {doc_size}{line_ending}{doc}".encode("utf-8"))
        return token_count, " (written)"
    return token_count, ""


def main():
    arguments = sys.argv[1:]
    # -s counts the text that follows, in one argument or in several.
    if arguments[:1] == ["-s"]:
        text = " ".join(arguments[1:])
        if not text:
            print("-s needs a text to count.")
            sys.exit(1)
        print(token_text(count_message(text)))
        return
    write = bool(arguments) and arguments[0] == "--write"
    if write:
        arguments = arguments[1:]
    if not arguments:
        print("token-counter [--write] <file> ..., or token-counter -s <text>?")
        sys.exit(1)
    total_count = 0
    failed = False
    for argument in arguments:
        file_location = pathlib.Path(argument)
        # A refusal names the file as it was typed, so a typo shows.
        if not file_location.is_file():
            print(f"{argument}: no such file")
            failed = True
            continue
        try:
            token_count, note = count_file(file_location, write)
        except UnicodeDecodeError:
            print(f"{argument}: neither UTF-8 text nor an image")
            failed = True
            continue
        print(f"{file_location.name}: {token_text(token_count)}{note}")
        total_count += token_count
    if len(arguments) > 1:
        print(f"total: {token_text(total_count)}")
    if failed:
        sys.exit(1)


# Nothing screams: whatever else goes wrong, a failed call to Anthropic included, ends in one line.
try:
    client = Anthropic(api_key=hall_key_location.read_text(encoding="utf-8").strip())
    main()
except Exception as error:
    print(f"Counting failed: {(str(error).splitlines() or [type(error).__name__])[0]}")
    sys.exit(1)

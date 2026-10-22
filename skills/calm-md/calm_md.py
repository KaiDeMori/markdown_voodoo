"""calm_md: a markdown file by chapter: its table of contents, one chapter to read, one chapter to write.

toc: one line per chapter, indented by level, with its weight in lines; a title path shows one chapter's part.
read: one chapter's original lines, its heading line included.
write: replaces one chapter's lines with what comes on stdin, in the same shape.
The parser only finds the headings; the original lines are cut and spliced, never re-rendered, so everything outside a chapter stays as it was.
A title path ends with the chapter's own title and needs only as many parents as it takes to fit one chapter.
Usage: calm_md.py toc <file> [title ...]
       calm_md.py read <file> <title> ...
       calm_md.py write <file> <title> ... < chapter
"""

import os
import re
import sys
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin

# The toc shows at most this many lines, and cuts a title after this many characters.
toc_line_limit = 40
title_character_limit = 60

# commonmark knows HTML blocks, and front matter is never mistaken for a heading.
parser = MarkdownIt("commonmark").use(front_matter_plugin)


def refuse(line):
    print(line)
    sys.exit(1)


def count(number, word):
    return f"{number} {word}{'' if number == 1 else 's'}"


def split_lines(text):
    # Lines end where markdown-it ends them: at \r\n, \r or \n, and nowhere else.
    return re.findall(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z", text)


def plain_title(inline_token):
    # A title is its plain text: inline markup gives its words, an image its alt text, a line break a space.
    words = []
    for child in inline_token.children or []:
        if child.type in ("text", "code_inline", "text_special"):
            words.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            words.append(" ")
        elif child.type == "image":
            words.append(plain_title(child))
    return re.sub(r"\s+", " ", "".join(words)).strip()


def find_chapters(text, line_count):
    chapters = []
    parents = []
    tokens = parser.parse(text)
    for index, token in enumerate(tokens):
        # Only a heading that stands in the document itself makes a chapter, not one inside a list item or a quote.
        if token.type != "heading_open" or token.level != 0:
            continue
        level = int(token.tag[1:])
        title = plain_title(tokens[index + 1])
        while parents and parents[-1]["level"] >= level:
            parents.pop()
        chapter = {"level": level, "title": title, "start": token.map[0], "path": [parent["title"] for parent in parents] + [title]}
        chapters.append(chapter)
        parents.append(chapter)
    # A chapter ends where the next heading of the same or a higher level begins, so it holds its subchapters.
    for position, chapter in enumerate(chapters):
        chapter["end"] = next((later["start"] for later in chapters[position + 1:] if later["level"] <= chapter["level"]), line_count)
    return chapters


def path_text(path):
    return " > ".join(path)


def find_chapter(chapters, titles):
    fits = [chapter for chapter in chapters if chapter["path"][-len(titles):] == titles]
    if len(fits) == 1:
        return fits[0]
    if not fits:
        refuse(f"No chapter fits {path_text(titles)}.")
    refuse(f"{path_text(titles)} fits {len(fits)} chapters: " + "; ".join(path_text(chapter["path"]) for chapter in fits))


def read_markdown(file_name):
    location = Path(file_name)
    if not location.is_file():
        refuse(f"No file {file_name}.")
    try:
        text = location.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        refuse(f"{file_name} is no UTF-8 text.")
    # A byte order mark stays where it was, but the parser never sees it.
    byte_order_mark = text.startswith("﻿")
    return location, byte_order_mark, text[1:] if byte_order_mark else text


def cut_title(title):
    if len(title) <= title_character_limit:
        return title
    return f"{title[:title_character_limit]}… (+{len(title) - title_character_limit})"


def show_toc(file_name, titles):
    _, _, text = read_markdown(file_name)
    lines = split_lines(text)
    chapters = find_chapters(text, len(lines))
    if not chapters:
        print(f"no chapters, {count(len(lines), 'line')}")
        return
    if titles:
        root = find_chapter(chapters, titles)
        chapters = [chapter for chapter in chapters if root["start"] <= chapter["start"] < root["end"]]
    top_level = min(chapter["level"] for chapter in chapters)
    for chapter in chapters[:toc_line_limit]:
        indent = "  " * (chapter["level"] - top_level)
        weight = count(chapter["end"] - chapter["start"], "line")
        print(f"{indent}{'#' * chapter['level']} {cut_title(chapter['title'])} ({weight})")
    if len(chapters) > toc_line_limit:
        print(f"and {len(chapters) - toc_line_limit} more chapters")


def read_chapter(file_name, titles):
    _, _, text = read_markdown(file_name)
    lines = split_lines(text)
    chapter = find_chapter(find_chapters(text, len(lines)), titles)
    # The original bytes go out as they are, line endings included.
    sys.stdout.buffer.write("".join(lines[chapter["start"]:chapter["end"]]).encode("utf-8"))


def write_chapter(file_name, titles):
    location, byte_order_mark, text = read_markdown(file_name)
    lines = split_lines(text)
    chapter = find_chapter(find_chapters(text, len(lines)), titles)
    try:
        new_text = sys.stdin.buffer.read().decode("utf-8")
    except UnicodeDecodeError:
        refuse("The new chapter is no UTF-8 text.")
    if not new_text.strip():
        refuse("Nothing to write; an empty chapter is refused, and the file stays as it was.")
    # The new chapter starts with its heading line, so no chapter loses its heading and joins the one before it.
    first_token = next(iter(parser.parse(new_text.lstrip("﻿"))), None)
    if first_token is None or first_token.type != "heading_open":
        refuse("The new chapter has to start with its heading line; the file stays as it was.")
    # The new lines take the file's own line endings.
    ending = "\r\n" if "\r\n" in text else "\n"
    new_text = re.sub(r"\r\n|\r|\n", ending, new_text.lstrip("﻿"))
    # A chapter followed by more ends with a blank line, so an underlined heading below never swallows its last line as part of its title.
    if chapter["end"] < len(lines):
        while not new_text.endswith(ending * 2):
            new_text += ending
    result = "".join(lines[:chapter["start"]]) + new_text + "".join(lines[chapter["end"]:])
    if byte_order_mark:
        result = "﻿" + result
    # The file is replaced in one step, so a reader never sees half of it.
    handle, temporary_name = tempfile.mkstemp(dir=location.parent, prefix=f".{location.name}.", suffix=".tmp")
    with os.fdopen(handle, "wb") as temporary_file:
        temporary_file.write(result.encode("utf-8"))
    os.replace(temporary_name, location)
    old_count = chapter["end"] - chapter["start"]
    print(f"{path_text(chapter['path'])}: {count(old_count, 'line')} became {count(len(split_lines(new_text)), 'line')}.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    verb, arguments = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if verb == "toc" and arguments:
        show_toc(arguments[0], arguments[1:])
    elif verb == "read" and len(arguments) > 1:
        read_chapter(arguments[0], arguments[1:])
    elif verb == "write" and len(arguments) > 1:
        write_chapter(arguments[0], arguments[1:])
    else:
        refuse("toc <file> [title ...], read <file> <title> ..., or write <file> <title> ...?")

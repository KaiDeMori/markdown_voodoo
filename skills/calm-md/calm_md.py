"""calm_md: a markdown file by chapter: its table of contents, one chapter to read, one chapter to write, insert, delete or move.

toc: one line per chapter, indented by level, with its weight in words, an estimate; a title path shows one chapter's part.
The toc shows the whole tree while it fits on a page; a bigger one shows where you are and the level right below, page by page.
read: one chapter's original lines, its heading line included.
write: replaces one chapter's lines with what comes on stdin, in the same shape.
replace: changes one piece of text inside one chapter: the old text on stdin's first line, the new text after it; the old text has to occur exactly once in the chapter.
insert: puts the chapter on stdin right after the named chapter, its subchapters included, or right before its heading; a heading higher than the named chapter's is refused.
delete: takes a chapter out, its subchapters with it.
move: puts a chapter right after or before the named one, as its sibling: it takes that level, and its subchapters shift along.
find: the places where words start with one word, case-insensitive, each with its chapter and five words on either side; more than ten give only their count.
calm-md works only on piko bello markdown: pymarkdownlnt checks the file by piko_bello.json first, and with issues calm-md only lists them.
--as-is skips that check for one call, and still says how many issues wait.
The parser only finds the headings; the original lines are cut and spliced, never re-rendered, so everything outside a chapter stays as it was.
A T line, the doc's token count on its first line, stays where it was, and neither the parser nor the linter sees it.
A title path ends with the chapter's own title and needs only as many parents as it takes to fit one chapter.
Every chapter has a number, its place in reading order, written @3; numbers are for looking, in toc, read and find, and the verbs that change a doc take titles.
Usage: calm_md.py toc [--as-is] [--page <number>] <file> [title ...]
       calm_md.py read [--as-is] <file> <title> ...
       calm_md.py write [--as-is] <file> <title> ... < chapter
       calm_md.py replace [--as-is] <file> <title> ... < old line, new text
       calm_md.py insert [--as-is] <file> after|before <title> ... < chapter
       calm_md.py delete [--as-is] <file> <title> ...
       calm_md.py move [--as-is] <file> <title> ... after|before <title> ...
       calm_md.py find [--as-is] <file> <word> [title ...]
"""

import bisect

import os
import re
import sys
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from pymarkdown.api import PyMarkdownApi, PyMarkdownApiException

# A page of the toc holds this many chapters, a title is cut after this many characters, and at most this many issues are listed.
page_line_limit = 100
title_character_limit = 60
# find shows at most this many hits, each with up to this many words on either side, from its own line.
hit_limit = 10
context_words = 5
issue_limit = 20
# The one central config: what piko bello means, tuned by feedback.
config_location = Path(__file__).resolve().parent / "piko_bello.json"

# commonmark knows HTML blocks, and front matter is never mistaken for a heading.
parser = MarkdownIt("commonmark").use(front_matter_plugin)
# A T line is a doc's first line with its token count: the T, U+FE054, directly followed by the number, and maybe a space and the doc's size in bytes.
# The old T, U+E054, is still looked past, and a write turns it into the new one.
t_line_pattern = re.compile("[\U0000E054\U000FE054][0-9]+(?: [0-9]+)?(?=\r\n|\r|\n)")


def refuse(line):
    print(line)
    sys.exit(1)


def count(number, word):
    return f"{number} {word}{'' if number == 1 else 's'}"


def split_lines(text):
    # Lines end where markdown-it ends them: at \r\n, \r or \n, and nowhere else.
    return re.findall(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z", text)


pragma_line = re.compile(r"[ \t]*<!--\s*(?:pyml|markdownlint)")


def lint(text):
    # An empty file has nothing to judge.
    if not text.strip():
        return []
    # A pragma comment cannot silence a rule: its line is left out of the scan, and every issue keeps the line number of the original.
    scanned_lines = []
    original_numbers = []
    for number, line in enumerate(split_lines(text), start=1):
        if not pragma_line.match(line):
            # The linter reads \r\n as two line breaks, so it sees every line ending as \n; the line count stays the same.
            scanned_lines.append(re.sub(r"\r\n|\r", "\n", line))
            original_numbers.append(number)
    try:
        result = PyMarkdownApi().enable_strict_configuration().configuration_file_path(str(config_location)).scan_string("".join(scanned_lines))
    except PyMarkdownApiException as error:
        refuse(f"The linter could not run: {error}")
    issues = []
    for failure in result.scan_failures:
        line_number = original_numbers[min(failure.line_number, len(original_numbers)) - 1]
        extra = f" {failure.extra_error_information.strip()}" if failure.extra_error_information else ""
        issues.append((line_number, failure.rule_id, f"{failure.rule_description}{extra}"))
    return sorted(issues)


def show_issues(issues, first_line):
    print(first_line)
    for line_number, rule_id, description in issues[:issue_limit]:
        print(f"line {line_number}: {rule_id} {description}")
    if len(issues) > issue_limit:
        print(f"and {len(issues) - issue_limit} more")
    sys.exit(1)


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
        # Its number is its place in reading order, counted fresh with every call.
        chapter = {
            "number": len(chapters) + 1,
            "level": level,
            "title": title,
            "start": token.map[0],
            "parent": parents[-1]["number"] if parents else None,
            "path": [parent["title"] for parent in parents] + [title],
        }
        chapters.append(chapter)
        parents.append(chapter)
    # A chapter ends where the next heading of the same or a higher level begins, so it holds its subchapters.
    for position, chapter in enumerate(chapters):
        chapter["end"] = next((later["start"] for later in chapters[position + 1:] if later["level"] <= chapter["level"]), line_count)
    return chapters


def path_text(path):
    return " > ".join(path)


def is_number(titles):
    return len(titles) == 1 and re.fullmatch(r"@\d+", titles[0]) is not None


def refuse_numbers(titles, verb):
    # Changing takes a title: a number can shift between two calls, a title cannot point at the wrong chapter.
    if any(re.fullmatch(r"@\d+", title) for title in titles):
        refuse(f"{verb} takes the chapter's title, not its number, so a number that shifted never changes the wrong chapter.")


def find_chapter(chapters, titles):
    if is_number(titles):
        number = int(titles[0][1:])
        if 1 <= number <= len(chapters):
            return chapters[number - 1]
        refuse(f"There is no chapter {titles[0]}; the doc has {count(len(chapters), 'chapter')}.")
    fits = [chapter for chapter in chapters if chapter["path"][-len(titles):] == titles]
    if len(fits) == 1:
        return fits[0]
    if not fits:
        refuse(f"No chapter fits {path_text(titles)}.")
    refuse(f"{path_text(titles)} fits {len(fits)} chapters: " + "; ".join(path_text(chapter["path"]) for chapter in fits))


def read_markdown(file_name, as_is):
    location = Path(file_name)
    if not location.is_file():
        refuse(f"No file {file_name}.")
    try:
        text = location.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        refuse(f"{file_name} is no UTF-8 text.")
    # A byte order mark and a T line, the doc's token count on its first line, stay where they were, but neither the parser nor the linter sees them.
    # The T line's ending stays behind as an empty first line, so every line number still fits the file.
    kept_start = "﻿" if text.startswith("﻿") else ""
    text = text[len(kept_start):]
    t_line = t_line_pattern.match(text)
    if t_line:
        kept_start += t_line.group(0)
        text = text[len(t_line.group(0)):]
    issues = lint(text)
    if issues and not as_is:
        show_issues(issues, f"{count(len(issues), 'issue')}, fix {'it' if len(issues) == 1 else 'them'} and call again:")
    if issues:
        # As-is works anyway, and the nudge goes to stderr, so a chapter read stays clean on stdout.
        print(f"{count(len(issues), 'issue')} {'waits' if len(issues) == 1 else 'wait'} in this doc.", file=sys.stderr)
    return location, kept_start, text


def find_word(file_name, word, titles, as_is):
    if not word or re.search(r"\s", word):
        refuse("find takes one word.")
    _, _, text = read_markdown(file_name, as_is)
    lines = split_lines(text)
    chapters = find_chapters(text, len(lines))
    line_starts = [0]
    for line in lines:
        line_starts.append(line_starts[-1] + len(line))
    first_line, end_line = 0, len(lines)
    if titles:
        root = find_chapter(chapters, titles)
        first_line, end_line = root["start"], root["end"]
    # A hit is a word that starts with the word looked for, in any case: fox finds Foxes, and the leaves other alone.
    pattern = re.compile(rf"(?<!\w){re.escape(word)}", re.IGNORECASE)
    hits = list(pattern.finditer(text, line_starts[first_line], line_starts[end_line]))
    if not hits:
        print("no hits")
        return
    if len(hits) > hit_limit:
        print(f"{len(hits)} hits, more than {hit_limit}: try a longer word, or a title path.")
        return
    found = []
    for hit in hits:
        line_index = bisect.bisect_right(line_starts, hit.start()) - 1
        # The innermost chapter holds the hit: the last one in reading order whose lines include it.
        holder = None
        for chapter in chapters:
            if chapter["start"] <= line_index < chapter["end"]:
                holder = chapter
        # The context counts whole words around the word the hit is in, and stays on the hit's own line.
        line_text = text[line_starts[line_index]:line_starts[line_index + 1]]
        offset = hit.start() - line_starts[line_index]
        word_start = re.search(r"\S*\Z", line_text[:offset]).start()
        before = line_text[:word_start].split()
        after = line_text[word_start:].split()
        context = " ".join(before[-context_words:] + after[:context_words + 1])
        if len(before) > context_words:
            context = "..." + context
        if len(after) > context_words + 1:
            context += "..."
        found.append((holder, context))
    width = max([len(f"@{holder['number']}") for holder, _ in found if holder] or [2])
    for holder, context in found:
        where = f"{'@' + str(holder['number']):<{width}}  {path_text(holder['path'])}" if holder else f"{'':<{width}}  (before the first chapter)"
        print(f"{where}: {context}")
    print(count(len(hits), "hit"))


def word_count(lines):
    # An estimate, and meant as one: whatever whitespace separates counts as a word, markdown signs included.
    return len("".join(lines).split())


def cut_title(title):
    if len(title) <= title_character_limit:
        return title
    return f"{title[:title_character_limit]}… (+{len(title) - title_character_limit})"


def show_toc(file_name, titles, as_is, page):
    _, _, text = read_markdown(file_name, as_is)
    lines = split_lines(text)
    chapters = find_chapters(text, len(lines))
    if not chapters:
        print(f"no chapters, {count(word_count(lines), 'word')}")
        return
    root = find_chapter(chapters, titles) if titles else None
    view = [chapter for chapter in chapters if root is None or root["start"] <= chapter["start"] < root["end"]]
    inside = {}
    for chapter in chapters:
        if chapter["parent"] is not None:
            inside[chapter["parent"]] = inside.get(chapter["parent"], 0) + 1

    def toc_line(chapter, top_level, number_width, with_inside):
        indent = "  " * (chapter["level"] - top_level)
        weight = count(word_count(lines[chapter["start"]:chapter["end"]]), "word")
        if with_inside and inside.get(chapter["number"]):
            weight += f", {inside[chapter['number']]} inside"
        return f"{'@' + str(chapter['number']):<{number_width}}  {indent}{'#' * chapter['level']} {cut_title(chapter['title'])} ({weight})"

    def number_width(shown):
        return max(len(f"@{chapter['number']}") for chapter in shown)

    # The whole tree, while it fits on a page.
    if len(view) <= page_line_limit:
        if page > 1:
            refuse("This toc fits on one page.")
        top_level = min(chapter["level"] for chapter in view)
        for chapter in view:
            print(toc_line(chapter, top_level, number_width(view), False))
        return
    # Too big for a page: where you are, and the level right below it; a piko bello doc starts at its one title.
    if root is None:
        top_chapters = [chapter for chapter in chapters if chapter["parent"] is None]
        if len(top_chapters) == 1:
            root = top_chapters[0]
    level = [chapter for chapter in chapters if chapter["parent"] == (root["number"] if root else None)]
    pages = (len(level) + page_line_limit - 1) // page_line_limit
    if page > pages:
        refuse(f"This level has {count(pages, 'page')}.")
    shown = level[(page - 1) * page_line_limit:page * page_line_limit]
    width = number_width(shown + ([root] if root else []))
    top_level = root["level"] if root else min(chapter["level"] for chapter in shown)
    print(f"{count(len(view), 'chapter')}, more than a page: one level shown; zoom in with a title path or a number.")
    if root:
        print(toc_line(root, top_level, width, True))
    for chapter in shown:
        print(toc_line(chapter, top_level, width, True))
    if pages > 1:
        print(f"page {page} of {pages}")


def read_chapter(file_name, titles, as_is):
    _, _, text = read_markdown(file_name, as_is)
    lines = split_lines(text)
    chapter = find_chapter(find_chapters(text, len(lines)), titles)
    # The original bytes go out as they are, line endings included.
    sys.stdout.buffer.write("".join(lines[chapter["start"]:chapter["end"]]).encode("utf-8"))


def read_new_chapter(verb, ending):
    """The chapter on stdin, in the file's own line endings, with its parsed tokens."""
    try:
        new_text = sys.stdin.buffer.read().decode("utf-8")
    except UnicodeDecodeError:
        refuse("The new chapter is no UTF-8 text.")
    if not new_text.strip():
        refuse(f"Nothing to {verb}; an empty chapter is refused, and the file stays as it was.")
    # The new chapter starts with its heading line, so no chapter loses its heading and joins the one before it.
    tokens = parser.parse(new_text.lstrip("﻿"))
    if not tokens or tokens[0].type != "heading_open":
        refuse("The new chapter has to start with its heading line; the file stays as it was.")
    return re.sub(r"\r\n|\r|\n", ending, new_text.lstrip("﻿")), tokens


def write_chapter(file_name, titles, as_is):
    refuse_numbers(titles, "write")
    location, kept_start, text = read_markdown(file_name, as_is)
    lines = split_lines(text)
    chapter = find_chapter(find_chapters(text, len(lines)), titles)
    ending = "\r\n" if "\r\n" in text else "\n"
    new_text, _ = read_new_chapter("write", ending)
    # A chapter followed by more ends with a blank line, so an underlined heading below never swallows its last line as part of its title.
    if chapter["end"] < len(lines):
        while not new_text.endswith(ending * 2):
            new_text += ending
    result = "".join(lines[:chapter["start"]]) + new_text + "".join(lines[chapter["end"]:])
    save_checked(location, kept_start, result, as_is, "The new chapter")
    old_count = chapter["end"] - chapter["start"]
    print(f"{path_text(chapter['path'])}: {count(old_count, 'line')} became {count(len(split_lines(new_text)), 'line')}.")


def save_checked(location, kept_start, result, as_is, what_changes):
    # A clean doc stays clean: the doc a change would leave behind is checked before anything is written.
    if not as_is:
        new_issues = lint(result)
        if new_issues:
            show_issues(new_issues, f"{what_changes} would bring {count(len(new_issues), 'issue')}; the file stays as it was:")
    result = kept_start.replace("\U0000E054", "\U000FE054") + result
    # The file is replaced in one step, so a reader never sees half of it.
    handle, temporary_name = tempfile.mkstemp(dir=location.parent, prefix=f".{location.name}.", suffix=".tmp")
    with os.fdopen(handle, "wb") as temporary_file:
        temporary_file.write(result.encode("utf-8"))
    os.replace(temporary_name, location)


def line_number_at(text, index, first_line):
    return first_line + len(re.findall(r"\r\n|\r|\n", text[:index])) + 1


def replace_in_chapter(file_name, titles, as_is):
    refuse_numbers(titles, "replace")
    location, kept_start, text = read_markdown(file_name, as_is)
    lines = split_lines(text)
    chapter = find_chapter(find_chapters(text, len(lines)), titles)
    try:
        given = sys.stdin.buffer.read().decode("utf-8").lstrip("﻿")
    except UnicodeDecodeError:
        refuse("The replacement is no UTF-8 text.")
    # The old text is the first line, the new text everything after it, so a one-word fix sends only a few words.
    given_lines = split_lines(given)
    if len(given_lines) < 2:
        refuse("replace takes the old text on the first line of stdin and the new text after it; the file stays as it was.")
    old_text = re.sub(r"(?:\r\n|\r|\n)\Z", "", given_lines[0])
    if not old_text:
        refuse("The old text is empty; the file stays as it was.")
    ending = "\r\n" if "\r\n" in text else "\n"
    new_text = re.sub(r"\r\n|\r|\n", ending, re.sub(r"(?:\r\n|\r|\n)\Z", "", "".join(given_lines[1:])))
    chapter_text = "".join(lines[chapter["start"]:chapter["end"]])
    places = [match.start() for match in re.finditer(re.escape(old_text), chapter_text)]
    if not places:
        refuse(f"The old text is not in {path_text(chapter['path'])}; the file stays as it was.")
    if len(places) > 1:
        line_numbers = sorted({line_number_at(chapter_text, place, chapter["start"]) for place in places})
        where = f"line {line_numbers[0]}" if len(line_numbers) == 1 else f"lines {', '.join(map(str, line_numbers))}"
        refuse(f"The old text is {len(places)} times in {path_text(chapter['path'])}, on {where}; give more of it, so it fits once.")
    start, end = places[0], places[0] + len(old_text)
    # An empty new text takes a whole line with it, its line ending included, so an item taken out of a list leaves no gap.
    if not new_text and (start == 0 or chapter_text[start - 1] in "\r\n"):
        line_ending = re.match(r"\r\n|\r|\n", chapter_text[end:])
        if line_ending:
            end += line_ending.end()
    new_chapter_text = chapter_text[:start] + new_text + chapter_text[end:]
    # The chapter keeps its heading line, so it never joins the chapter before it.
    first_token = next(iter(parser.parse(new_chapter_text)), None)
    if first_token is None or first_token.type != "heading_open":
        refuse("The chapter would lose its heading line; the file stays as it was.")
    result = "".join(lines[:chapter["start"]]) + new_chapter_text + "".join(lines[chapter["end"]:])
    save_checked(location, kept_start, result, as_is, "The replacement")
    print(f"{path_text(chapter['path'])}: replaced on line {line_number_at(chapter_text, places[0], chapter['start'])}.")


def t_line_ending_lines(kept_start):
    # A T line's ending stays behind as the text's first line; it has to stay, so the T line keeps its line.
    return 1 if kept_start.lstrip("﻿") else 0


def without_trailing_blank_lines(lines, kept_lines):
    lines = list(lines)
    while len(lines) > kept_lines and not lines[-1].strip():
        lines.pop()
    return lines


def delete_chapter(file_name, titles, as_is):
    refuse_numbers(titles, "delete")
    location, kept_start, text = read_markdown(file_name, as_is)
    lines = split_lines(text)
    chapter = find_chapter(find_chapters(text, len(lines)), titles)
    kept_lines = lines[:chapter["start"]]
    # When the last chapter goes, the blank lines before it would end the file, so they go too.
    if chapter["end"] == len(lines):
        kept_lines = without_trailing_blank_lines(kept_lines, t_line_ending_lines(kept_start))
    result = "".join(kept_lines) + "".join(lines[chapter["end"]:])
    save_checked(location, kept_start, result, as_is, "The deletion")
    print(f"{path_text(chapter['path'])}: deleted, {count(chapter['end'] - chapter['start'], 'line')}.")


def splice_chapter(lines, position, chapter_text, ending):
    """Puts a chapter's text in front of a line, with a blank line above its heading and, when more follows, one at its end."""
    before = "".join(lines[:position])
    after = "".join(lines[position:])
    if before.strip():
        if not re.search(r"(?:\r\n|\r|\n)\Z", before):
            before += ending
        if split_lines(before)[-1].strip():
            before += ending
    if after:
        while not chapter_text.endswith(ending * 2):
            chapter_text += ending
    return before, chapter_text, after


def insert_chapter(file_name, place, titles, as_is):
    if place not in ("after", "before"):
        refuse("insert takes after or before, then the title path of the chapter the new one goes next to.")
    refuse_numbers(titles, "insert")
    location, kept_start, text = read_markdown(file_name, as_is)
    lines = split_lines(text)
    named = find_chapter(find_chapters(text, len(lines)), titles)
    ending = "\r\n" if "\r\n" in text else "\n"
    new_text, tokens = read_new_chapter("insert", ending)
    # A heading higher than the named chapter's would end chapters early and pull the ones after it under the new one.
    top_level = min(int(token.tag[1:]) for token in tokens if token.type == "heading_open" and token.level == 0)
    if top_level < named["level"]:
        refuse(f"A {'#' * top_level} heading next to the {'#' * named['level']} chapter {path_text(named['path'])} would pull the chapters after it under itself; the file stays as it was.")
    before, new_text, after = splice_chapter(lines, named["end"] if place == "after" else named["start"], new_text, ending)
    result = before + new_text + after
    inserted = next((chapter for chapter in find_chapters(result, len(split_lines(result))) if chapter["start"] == len(split_lines(before))), None)
    if inserted is None:
        refuse("The new heading would not stand as a heading there; the file stays as it was.")
    save_checked(location, kept_start, result, as_is, "The new chapter")
    print(f"{path_text(inserted['path'])}: inserted {place} {path_text(named['path'])}, {count(len(split_lines(new_text)), 'line')}.")


# A # heading's marks: up to three spaces, then one to six #, then a space or the line's end.
heading_marks = re.compile(r"( {0,3})#{1,6}(?=[ \t\r\n]|\Z)")
level_words = ("", "one", "two", "three", "four", "five")


def move_chapter(file_name, arguments, as_is):
    places = [index for index, word in enumerate(arguments) if word in ("after", "before")]
    if not places or places[0] == 0 or places[0] == len(arguments) - 1:
        refuse("move takes the moved chapter's title path, then after or before, then the title path of the chapter it goes next to.")
    place = arguments[places[0]]
    moved_titles, named_titles = arguments[:places[0]], arguments[places[0] + 1:]
    refuse_numbers(moved_titles + named_titles, "move")
    location, kept_start, text = read_markdown(file_name, as_is)
    lines = split_lines(text)
    chapters = find_chapters(text, len(lines))
    moved = find_chapter(chapters, moved_titles)
    named = find_chapter(chapters, named_titles)
    if moved["start"] <= named["start"] < moved["end"]:
        refuse(f"{path_text(moved['path'])} can't move next to itself or into its own subchapters; the file stays as it was.")
    # The moved chapter becomes the named chapter's sibling, and its subchapters shift with it.
    shift = named["level"] - moved["level"]
    moved_lines = lines[moved["start"]:moved["end"]]
    if shift:
        for chapter in [chapter for chapter in chapters if moved["start"] <= chapter["start"] < moved["end"]]:
            new_level = chapter["level"] + shift
            if new_level > 6:
                refuse(f"{path_text(chapter['path'])} would need {'#' * new_level}, and headings stop at ######; the file stays as it was.")
            index = chapter["start"] - moved["start"]
            if not heading_marks.match(moved_lines[index]):
                refuse(f"{path_text(chapter['path'])} is an underlined heading, and underlines know only two levels; the file stays as it was.")
            moved_lines[index] = heading_marks.sub(lambda match: match.group(1) + "#" * new_level, moved_lines[index], count=1)
    remaining = lines[:moved["start"]] + lines[moved["end"]:]
    # A chapter that leaves the end, or arrives there, leaves its blank lines behind, like a deleted one.
    if moved["end"] == len(lines):
        remaining = without_trailing_blank_lines(lines[:moved["start"]], t_line_ending_lines(kept_start))
    position = named["end"] if place == "after" else named["start"]
    if position >= moved["end"]:
        position -= moved["end"] - moved["start"]
    position = min(position, len(remaining))
    if position == len(remaining):
        moved_lines = without_trailing_blank_lines(moved_lines, 1)
    ending = "\r\n" if "\r\n" in text else "\n"
    before, moved_text, after = splice_chapter(remaining, position, "".join(moved_lines), ending)
    save_checked(location, kept_start, before + moved_text + after, as_is, "The move")
    how = f", {level_words[abs(shift)]} level{'s' if abs(shift) > 1 else ''} {'up' if shift < 0 else 'down'}" if shift else ""
    print(f"{path_text(moved['path'])}: moved {place} {path_text(named['path'])}{how}.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    words = sys.argv[1:]
    as_is = "--as-is" in words
    words = [word for word in words if word != "--as-is"]
    page = 1
    if "--page" in words:
        position = words.index("--page")
        if position + 1 >= len(words) or not words[position + 1].isdigit() or int(words[position + 1]) < 1:
            refuse("--page takes a page number, like --page 2.")
        page = int(words[position + 1])
        del words[position:position + 2]
    verb, arguments = (words[0], words[1:]) if words else ("", [])
    if page > 1 and verb != "toc":
        refuse("--page belongs to toc.")
    if verb == "toc" and arguments:
        show_toc(arguments[0], arguments[1:], as_is, page)
    elif verb == "read" and len(arguments) > 1:
        read_chapter(arguments[0], arguments[1:], as_is)
    elif verb == "write" and len(arguments) > 1:
        write_chapter(arguments[0], arguments[1:], as_is)
    elif verb == "replace" and len(arguments) > 1:
        replace_in_chapter(arguments[0], arguments[1:], as_is)
    elif verb == "find" and len(arguments) > 1:
        find_word(arguments[0], arguments[1], arguments[2:], as_is)
    elif verb == "delete" and len(arguments) > 1:
        delete_chapter(arguments[0], arguments[1:], as_is)
    elif verb == "insert" and len(arguments) > 2:
        insert_chapter(arguments[0], arguments[1], arguments[2:], as_is)
    elif verb == "move" and len(arguments) > 3:
        move_chapter(arguments[0], arguments[1:], as_is)
    else:
        refuse("toc [--as-is] [--page <number>] <file> [title ...], read, write, replace or delete [--as-is] <file> <title> ..., insert [--as-is] <file> after|before <title> ..., move [--as-is] <file> <title> ... after|before <title> ..., or find [--as-is] <file> <word> [title ...]?")

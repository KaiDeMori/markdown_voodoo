# calm-code

A calm source file: its classes and methods at a glance, and one of them to read, without the whole file entering the window.
It parses one file at a time with Tree-sitter.

```text
calm-code toc [--page <number>] <file> [name ... | @number]
calm-code read [--limit <characters>] <file> <name ... | @number>
```

Start zoomed out, and zoom in only when the answer asks for it:

| Command | Answers | Happy path |
|---|---|---|
| `toc <file>` | How is the file built, and how big is each part? | `@3  open_menu(string name) (10 lines)` |
| `toc <file> <name>` | What is inside one class? | the class with everything nested in it |
| `read <file> <name> ...` | What does one method say? | its original lines, doc comment and attributes included |

## Languages

| Language | Extensions | Listed |
|---|---|---|
| C# | `.cs` | classes, structs, interfaces and records, with their methods and constructors |
| Python | `.py`, `.pyw` | classes with their methods, and functions |
| JavaScript | `.js`, `.mjs`, `.cjs`, `.jsx` | classes with their methods, and functions; arrow functions count when they have a name |

- Whatever is defined inside a function stays out: it is a detail of the function around it.
- What counts is written down in one query per language, in `src/queries/`.

## toc

```text
C#, 56 lines: 2 classes, 1 struct, 1 interface, 1 record, 8 methods
@1   class Menu_bar (39 lines)
@2     Menu_bar() (4 lines)
@3     open_menu(string name) (10 lines)
@4     open_menu(int index) (4 lines)
```

- The first line names the language and counts what the file holds.
- Every entry has a number, its place in reading order, like `@3`; `toc` and `read` take it instead of a name.
- An entry's weight is its number of lines, counted the way `read` returns them.
- Parameters show, so overloads can be told apart. A label longer than 60 characters is cut, with the count of what was cut.
- `toc` shows the whole tree while it fits on a page of 100 entries.
  A bigger one shows the top level, each entry with how many are inside it; zoom in with a name or a number, and turn pages with `--page 2`.

## read

```text
samples/Menu_bar.cs:18-27
    /// <summary>
    /// Opens the menu with the given name.
    /// </summary>
    [Obsolete("Use the index instead")]
    public void open_menu(string name)
```

- The first line is the location, `file:first-last`, ready for a Read with offset and limit.
- The lines follow as they stand in the file: the entry with its attributes, decorators and `export`, and the comments directly above it, on their own lines and without a blank line in between.
- `read` refuses an entry over 20,000 characters, about 5,000 tokens, and says how to go on: `toc` to look inside, or `--limit` to read it all for one call.

## Names

- A name path ends with the entry's own name and needs only as many enclosing names as it takes: `read Menu_bar.cs Menu_bar Menu_bar` reads the constructor, not the class.
- A path that fits more than one entry is refused, with the candidates: each with its number and the names around it, such as `@12 Title_list on_focus(self)`.
- In `toc`, a name prefers a class to a method, since a C# constructor shares its class's name.
- Names are case-sensitive. A miss that differs only in case is refused with the entries it missed.

## Good to know

- Options may stand anywhere after the command.
- A file with syntax errors still gets an answer, because Tree-sitter always builds a tree. `toc` adds a line about it, and `read` warns on stderr.
- Every refusal is one line on stderr, with exit code 1; exit code 0 means done.
- Files are read as UTF-8, and a byte order mark is skipped.
- The limits are the constants at the top of `src/main.rs`, `src/toc.rs` and `src/outline.rs`.

## Build

```bash
cargo build --release --manifest-path tree_sitting/Cargo.toml
```

The executable lands in `tree_sitting/target/release/calm-code.exe`.

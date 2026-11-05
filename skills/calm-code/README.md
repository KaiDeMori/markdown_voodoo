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
| `toc <file> <name>` | What is inside one class or function? | the entry with everything nested in it |
| `read <file> <name> ...` | What does one method say? | its original lines, doc comment and attributes included |

## Languages

| Language | Extensions | Listed |
|---|---|---|
| C# | `.cs` | classes, structs, interfaces and records, with their methods, constructors and properties with a body |
| Python | `.py`, `.pyw` | classes with their methods, and functions |
| JavaScript | `.js`, `.mjs`, `.cjs`, `.jsx` | classes with their methods, and functions; arrow functions count when they have a name |
| TypeScript | `.ts`, `.mts`, `.cts`, `.tsx` | like JavaScript, plus interfaces, type aliases and abstract classes with their signatures; overload signatures stay out |
| Rust | `.rs` | structs, enums, traits with their methods and signatures, `impl` blocks with their methods, modules with their functions, `macro_rules!` macros, and functions |
| CSS | `.css` | rules, named by their selectors, and at-rules such as `@media`, `@supports`, `@keyframes`, `@font-face` and `@import`; a rule's nested rules and an at-rule's rules count as its children |
| HTML | `.html`, `.htm` | the page's shape and every place its JavaScript and CSS live: `head`, `body`, `header`, `nav`, `main`, `section`, `article`, `aside`, `footer`, `form`, `dialog`, `template` and `iframe`, elements with an `id`, elements with `on…` handlers, `javascript:` links or `style` attributes, stylesheet links, and `script` and `style` blocks, whose functions and rules come along as their children |

- Functions declared directly in a function's body count as its children, the way methods count for a class: a factory shows what it builds.
- What sits deeper, in an `if` block or an anonymous callback, stays out. So do anonymous functions: they have no name to show or to read them by.
- A property like `{ get; set; }` stays out; it holds no code.
- A Rust closure stays out, even with a name: Rust's named functions are `fn` items.
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
- Some labels carry a word in front: `class`, `struct`, `enum`, `interface`, `trait`, `record` or `type` for a type, `impl` for a Rust `impl` block, `mod` for a module, `macro` for a macro, `property` for a C# property, and `get` or `set` for an accessor.
- An `impl` label shows its trait and its type as written, without its own generics and its `where` clause: `impl From<u8> for Menu_id`.
- A CSS rule's label is its selector list, and an at-rule's label its header, such as `@media (max-width: 600px)`.
- An HTML element's label is its start tag with the attributes that matter: its `id`, its handlers, `javascript:` links and `style`, a script's `type` and `src`, a stylesheet's `rel` and `href`.
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
- A Rust `//!`, `/*!` or `#![...]` documents the module around it, so it stays out.
- `read` refuses an entry over 20,000 characters, about 5,000 tokens, and says how to go on: `toc` to look inside, or `--limit` to read it all for one call.

## Names

- A name path ends with the entry's own name and needs only as many enclosing names as it takes: `read Menu_bar.cs Menu_bar Menu_bar` reads the constructor, not the class.
- A path that fits more than one entry is refused, with the candidates: each with its number and the names around it, such as `@12 Title_list on_focus(self)`.
- A Rust `impl` answers to its type's name and, for a trait impl, to its trait's name too, in either order: `read menu_bar.rs Display fmt` and `read menu_bar.rs Debug Menu_bar fmt`.
- These names leave out paths, generics and references: `impl fmt::Display for &'a Menu_bar<T>` answers to `Display` and `Menu_bar`.
- A CSS rule answers to its whole selector list and to each selector in it, an at-rule to its keyword and to its header: `read app.css ".menu > li"`, `read app.css h2`, `read app.css "@layer base"`.
- `@` followed by digits is a number; any other name may start with `@`.
- An HTML element answers to its tag, its `id` with and without `#`, its handlers' names, and a script's `src` or a stylesheet's `href`: `read index.html "#search"`, `read index.html onclick`.
- In `toc`, a name prefers a class to a method, since a C# constructor shares its class's name.
- Names are case-sensitive. A miss that differs only in case is refused with the entries it missed.

## Good to know

- Options may stand anywhere after the command.
- A script with a `src`, or with a `type` that is not JavaScript, such as `application/json`, is listed without an outline of its text.
- A file with syntax errors still gets an answer, because Tree-sitter always builds a tree. `toc` adds a line about it, and `read` warns on stderr.
- Rust's `safe fn` in an `unsafe extern` block counts as a syntax error; the Rust grammar does not know it.
- Every refusal is one line on stderr, with exit code 1; exit code 0 means done.
- Files are read as UTF-8, and a byte order mark is skipped.
- The limits are the constants at the top of `src/main.rs`, `src/toc.rs` and `src/outline.rs`.

## Build

```bash
cargo build --release --manifest-path skills/calm-code/Cargo.toml
```

The executable lands in `skills/calm-code/target/release/calm-code.exe`.

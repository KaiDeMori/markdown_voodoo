# calm-json

A calm JSON file: its keys at a glance, and the value at one path, without the whole file entering the window.
It parses with Tree-sitter, which gives every value its place in the file.

```text
calm-json toc [--page <number>] <file> [path | @number]
calm-json read [--limit <characters>] <file> <path | @number>
```

calm-json works only on piko bello JSON.
Before anything else, it checks the whole file; with issues, it only lists them, one line each, like `3 issues, fix them and call again:`.
Fix the file, then call again.

Start zoomed out, and zoom in only when the answer asks for it:

| Command | Answers | Happy path |
|---|---|---|
| `toc <file>` | Which keys are in here, and how big is each part? | `@2  hooks: object, 2 keys (255 characters)` |
| `toc <file> <path>` | What is inside one object or array? | the value with everything nested in it |
| `read <file> <path>` | What sits at a path? | its original text, key included |

## toc

```text
JSON, 31 lines, 530 characters: object, 4 keys
@1   model: "opus"
@2   hooks: object, 2 keys (255 characters)
@3     UserPromptSubmit: array, 1 object (214 characters)
@4       [0]: object, 2 keys (181 characters)
```

- The first line counts the file's lines and characters, and says what its root is.
- Every key and every array item is an entry, numbered in reading order, like `@3`; `toc` and `read` take the number instead of a path.
- The key or index comes first, then a short value: a scalar shows itself, an object its keys, an array its items and their kind, such as `array, 3 strings`. A label longer than 60 characters is cut, with the count of what was cut.
- An object or array weighs its characters, counted the way `read` returns them: characters fill a window, and a minified file has only one line.
- `toc` shows the whole tree while it fits on a page of 100 entries.
  A bigger one shows one level, each entry with how many are inside it; zoom in with a path or a number, and turn pages with `--page 2`.

## read

```text
samples/settings.json:5-13
      {
        "matcher": "",
        "hooks": [
```

- The first line is the location, `file:first-last`, ready for a Read with offset and limit.
- A member on lines of its own comes as whole lines, with its indentation, its trailing comma, and the comments directly above it and after it; one inside a line, as in a minified file, comes as its exact slice.
- `read` refuses a value over 20,000 characters, about 5,000 tokens, and says how to go on: `toc` to look inside, or `--limit` to read it all for one call.

## Paths

- Dots lead to keys, brackets to items: `hooks.UserPromptSubmit[0]`. `[-1]` is the last item.
- A key with dots, brackets or quotes goes in brackets and quotes: `env["my.dotted.key"]`, or `packages[""]` for the empty key. A leading `$` is fine.
- Keys are compared as they stand in the file, escapes included, and case-sensitive. A miss that differs only in case says so.
- A miss says what is there: `no key Missing in hooks; its keys: UserPromptSubmit, SessionStart`.

## Good to know

- Issues are syntax errors, trailing commas, a key that stands twice in one object, more than one value at the top, as in JSON Lines, and comments outside a `.jsonc` file.
- Options may stand anywhere after the command.
- Every refusal goes to stderr, with exit code 1: one line, or an issue list. Exit code 0 means done.
- Files are read as UTF-8, and a byte order mark is skipped.
- The limits are the constants at the top of `src/main.rs`, `src/toc.rs`, `src/document.rs`, `src/json_path.rs` and `src/issues.rs`.

## Build

```bash
cargo build --release --manifest-path skills/calm-json/Cargo.toml
```

The executable lands in `skills/calm-json/target/release/calm-json.exe`.

# Rust plan

calm-code learns Rust: `.rs` files get `toc` and `read` like the other languages.
The findings behind this plan are in [rust_findings.md](rust_findings.md).

## Result

### What is listed

- structs, enums and traits, with the trait's methods and signatures
- `impl` blocks, with their methods
- modules with a body, with their functions
- `macro_rules!` macros
- functions, with the functions declared directly in their bodies

Functions in an `impl` or a `trait` are methods; functions in a module or in a function are functions.
Labels carry `struct`, `enum`, `trait`, `impl`, `mod` or `macro` in front.
An impl's label shows the trait and the type as written, without the impl's own generics and its `where` clause, such as `impl From<u8> for Menu_id`.
Qualifiers such as `pub`, `async` and `unsafe` stay out of every label, as in the other languages.

### toc

For the sample of step 5, with labels and nesting, and the weights left out:

```text
@1   struct Menu_bar
@2   struct Menu
@3   impl Menu_bar
@4     new()
@5     open_menu(&self, name: &str)
@6       matches(menu: &Menu, name: &str)
@7   impl fmt::Display for Menu_bar
@8     fmt(&self, formatter: &mut fmt::Formatter<'_>)
@9   impl fmt::Debug for Menu_bar
@10    fmt(&self, formatter: &mut fmt::Formatter<'_>)
@11  trait Clickable
@12    click(&mut self)
@13    double_click(&mut self)
@14  impl Clickable for Menu_bar
@15    click(&mut self)
@16  macro menu_bar
@17  mod tests
@18    opens_menu()
```

The header line counts `2 structs, 1 trait, 4 impls, 1 mod, 1 macro, 7 methods, 2 functions`.

### read

- Attributes in front of an item travel with it, and so do the comments directly above them: `mod tests` comes with its `#[cfg(test)]`.
- `//!`, `/*!` and `#![...]` document the module around them and never travel with the item below.

### Names

- An impl answers to its type's name and, for a trait impl, to its trait's name too.
- The two names may stand in either order.
- A name is the type's or the trait's own identifier, without path and generics: `&'a Marker` answers to `Marker`, `fmt::Display` to `Display`.
- A type without an identifier of its own answers to its text as written, such as `[u8]`.
- A refusal shows both names of an enclosing impl in front of a candidate.

| Command | Result |
|---|---|
| `read menu_bar.rs open_menu` | @5 |
| `read menu_bar.rs Display fmt` | @8 |
| `read menu_bar.rs Menu_bar Debug fmt` | @10 |
| `read menu_bar.rs Debug Menu_bar fmt` | @10 |
| `toc menu_bar.rs Display` | @7 |
| `read menu_bar.rs fmt` | refused: `@8 Menu_bar Display fmt(...)`, `@10 Menu_bar Debug fmt(...)` |
| `read menu_bar.rs click` | refused: `@12 Clickable click(&mut self)`, `@15 Menu_bar Clickable click(&mut self)` |
| `toc menu_bar.rs Menu_bar` | refused: @1, @3, @7, @9 and @14 |

## Steps

### 1. Grammar and query

- [x] Add `tree-sitter-rust = "0.24.2"` to the dependencies in `Cargo.toml`.
- [x] Add `src/queries/rust.scm`, as verified in the lab:

```scheme
(struct_item
  name: (type_identifier) @name) @definition.struct

(enum_item
  name: (type_identifier) @name) @definition.enum

(trait_item
  name: (type_identifier) @name) @definition.trait

(impl_item
  "!"? @label
  trait: (_)? @second_name @label
  type: (_) @name @label) @definition.impl

(mod_item
  name: (identifier) @name
  body: (declaration_list)) @definition.mod

(macro_definition
  name: (identifier) @name) @definition.macro

(function_item
  name: (identifier) @name
  parameters: (parameters) @parameters) @definition.function

(trait_item
  body: (declaration_list
    (function_signature_item
      name: (identifier) @name
      parameters: (parameters) @parameters) @definition.method))
```

Two captures are new.
`@second_name` gives the second name an entry answers to.
`@label` may stand on several nodes, and the label's text runs from the first one's start to the last one's end.

### 2. Language support

`Language_support` in `languages.rs` gets four fields:

| Field | Meaning | C#, Python, JavaScript, TypeScript | Rust |
|---|---|---|---|
| `leading_kinds` | nodes in front of a definition that belong to it | `["decorator"]` | `["attribute_item"]` |
| `comment_kinds` | the node kinds of comments | `["comment"]` | `["line_comment", "block_comment"]` |
| `inner_comment_markers` | a comment holding a node of these kinds documents what surrounds it | `[]` | `["inner_doc_comment_marker"]` |
| `name_fields` | the fields a captured name follows down to the node that names it | `[]` | `["type", "name", "trait"]` |

- [x] Add the four fields.
- [x] Give the four existing languages their values from the table, which keep their behavior as it is.
- [x] Add the entry for `rs`: name `Rust`, grammar `tree_sitter_rust::LANGUAGE`, query `queries/rust.scm`, no `wrapper_kinds`, `body_kinds: ["block"]`, and the Rust values from the table.

### 3. Outline

In `outline.rs`:

- [x] `definition_kind_for` maps `enum`, `trait`, `impl`, `mod` and `macro` to containers.
- [x] A container carries whether it holds methods, such as `Container { word, holds_methods }`; `mod` and `macro` do not, so `nest_definitions` makes a callable in a module a function.
- [x] `collect_definitions` takes the language support:
  `@name` and `@second_name` follow `name_fields` down before their text is taken, and `@label` collects its span, flattened like parameters.
- [x] `Entry` gets `second_name: Option<String>`.
- [x] `label_for` puts the label text where the name would stand, such as `impl fmt::Display for Menu_bar`.
- [x] `span_rows` walks back over `leading_kinds` instead of `decorator`.
- [x] `is_attached_comment` checks `comment_kinds` instead of `comment`, and never attaches a comment that holds a node of `inner_comment_markers`.
- [x] `collect_comment_ranges` checks `comment_kinds` instead of `comment`.
- [x] `matching_entries` follows the name rules below.
- [x] `candidate_list` shows both names of an enclosing impl, the name first.

The name rules:

1. The last name of the path matches an entry's name or its second name.
2. The other names of the path are taken in order by the entries around it, from the outermost to the entry itself.
3. An entry takes the next name of the path when it matches one of its names not yet used, so an entry with two names takes up to two names in a row, in either order.
4. The entry itself offers only the name the last name of the path did not use.
5. An entry with one name matches as it does today.

### 4. toc

- [x] `KIND_WORDS` in `toc.rs` becomes `class`, `struct`, `enum`, `interface`, `trait`, `record`, `type`, `impl`, `mod`, `macro`, `method`, `property`, `function`; the words already there keep their order.

### 5. Sample

- [x] Add `samples/menu_bar.rs` with what the toc under Result shows:
  - a `//!` module doc at the top
  - `struct Menu_bar` with a `///` doc and a `#[derive(...)]`, and `struct Menu`
  - `impl Menu_bar` with `new` and `open_menu`, which declares `fn matches` in its body
  - `impl fmt::Display` and `impl fmt::Debug` for `Menu_bar`, each with `fmt`
  - `trait Clickable` with the signature `click` and the default method `double_click`
  - `impl Clickable for Menu_bar`
  - `macro_rules! menu_bar`
  - `#[cfg(test)] mod tests` with `#[test] fn opens_menu`

### 6. Docs

In `README.md` and `SKILL.md`:

- [x] Languages: add the row below.
- [x] toc: add `enum`, `trait`, `impl`, `mod` and `macro` to the words in front of labels.
- [x] read: a Rust `//!`, `/*!` or `#![...]` stays with the module around it.
- [x] Names: an `impl` answers to its type's name and its trait's name, in either order, such as `read menu_bar.rs Display fmt`.
- [x] Good to know: `safe fn` in an `unsafe extern` block counts as a syntax error.

```text
| Rust | `.rs` | structs, enums, traits with their methods and signatures, `impl` blocks with their methods, modules with their functions, `macro_rules!` macros, and functions |
```

### 7. Build and try out

- [x] Build as `README.md` says.
- [x] Try `toc` and `read` on `samples/menu_bar.rs`, on the lab samples in `scratchpad/rusty_lab/samples/`, and on calm-code's own `src/`.
- [x] Try `toc` and `read` on the samples of the other languages.
- [ ] Wally's test_pilot ravens fly it.
- [ ] After the test flight, tell Wally the skill is ready for a deploy.

## Check

Steps 2 to 4 change paths that every language goes through: the comment and decorator kinds, the name matching, the kind words and the label shapes.
`scratchpad/rusty_lab/check/capture.sh` runs a calm-code build over every sample: the whole `toc`, `toc` and `read` for every entry, and the calls in `name_paths.txt`, each with stdout, stderr and exit code.
`before/` holds the 515 calls of the build before any change.
`after/` holds the same 515 calls, byte-identical, plus the 37 calls of `samples/menu_bar.rs`.

## Limitations

- `safe fn` in an `unsafe extern` block counts as a syntax error; extern blocks are not listed.
- `impl Fn(u8) for Marker` is a nightly form and a syntax error, and its impl reads as `impl Marker`.

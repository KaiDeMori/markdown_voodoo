# Rust findings

What reading calm-code and parsing Rust with tree-sitter-rust showed, as the ground for [rust_plan.md](rust_plan.md).
The lab with the dump tool, the samples and the query is `scratchpad/rusty_lab/`.

## Scope

- Rust joins calm-code as one more language; there is no calm-rust.
- The hall splits its tools by kind of file, and a Rust file is source code like a C# file.
- The goal is basic navigation, as for the other languages.
- Crate-level work stays out, such as following `mod foo;` into its file or expanding macros.
- `toc` and `read` stay as they are; there is no new verb.

## Decisions

- An `impl` block answers to its type's name and, for a trait impl, to its trait's name too, in either order.
- `macro_rules!` is listed as `macro <name>`.
- Closures, `const`, `static`, type aliases, `use`, `mod foo;` without a body, `extern` blocks and unions stay out.

### Two names for an impl

- Numbers shift with every edit, so names are the stable handles.
- With one name, two trait impls of one type can leave a method without a unique name, such as `fmt` in `Display` and `Debug`.
- With two names, a refusal shows a path to copy, such as `@10 Menu_bar Debug fmt(...)`.
- Rust names a trait method by both names: `<Menu_bar as Debug>::fmt`.
- With one name, `Clickable click` picks the trait's signature without a word; with two names, it is refused with both candidates.
- The price: a trait's name finds its impls too, so `toc` with a trait's name is refused when the trait and an impl share a file.
- Sharing a file is idiomatic Rust, such as a blanket impl next to its trait, or a sealed trait with its impls.

### Closures

- In Rust, a named function is a `fn` item, and a closure is a value inside a function.
- The JavaScript rule for named arrow functions exists because JavaScript defines functions as values.

## Grammar

- `tree-sitter-rust` 0.24.2 is the latest release.
- It builds on `tree-sitter-language` 0.1, like the other grammars, with ABI 15, which tree-sitter 0.27.1 reads.
- The sources of calm-code and calm-json, 12 files in edition 2024, parse without a syntax error.
- Let-else, let chains, `&raw const`, `use<'a>` bounds, async closures, C string literals and `#[unsafe(...)]` attributes parse.
- `safe fn` in an `unsafe extern` block is a syntax error; the tree around it stays intact.
- `impl Fn(u8) for Marker`, a nightly form, is a syntax error, and its impl reads as `impl Marker`.

## Node kinds

| Rust | Node kind | Fields |
|---|---|---|
| `struct` | `struct_item` | `name` |
| `enum` | `enum_item` | `name` |
| `trait` | `trait_item` | `name`, `body` |
| `impl` | `impl_item` | `trait`, `type`, `type_parameters`, `body` |
| `mod` with a body | `mod_item` | `name`, `body` |
| `mod foo;` | `mod_item` | `name` |
| `macro_rules!` | `macro_definition` | `name` |
| `fn` | `function_item` | `name`, `parameters`, `body` |
| trait signature | `function_signature_item` | `name`, `parameters` |
| `//`, `///`, `//!` | `line_comment` | `outer` or `inner`, `doc` |
| `/* */`, `/** */`, `/*! */` | `block_comment` | `outer` or `inner`, `doc` |
| `#[...]` | `attribute_item` | |
| `#![...]` | `inner_attribute_item` | |
| `extern "C" { }` | `foreign_mod_item` | `body` |

- The body of a trait, an impl, a module and an extern block is a `declaration_list`; the body of a `fn` is a `block`.
- A `where_clause` is a child without a field name.
- In an impl header, `unsafe` and `!` are anonymous tokens.
- `visibility_modifier` and `function_modifiers`, such as `async`, `const`, `unsafe` and `extern "C"`, are children of their own, so a label from `name` and `parameters` leaves them out.
- What stays out has kinds of its own: `union_item`, `const_item`, `static_item`, `type_item`, `use_declaration`, `extern_crate_declaration` and `closure_expression`.
- A macro call is a `macro_invocation`; its body is a `token_tree`, and nothing in it is parsed as an item.

## Impl headers

- The `trait` field holds a path, such as `fmt::Display` or `From<u8>`.
- The `type` field holds any type: a path, a generic type, a reference, a pointer, a `dyn` type, an array, a tuple, a function type, `()` or `!`.
- Query alternations cannot name every type shape.
  Without a catch-all, an impl whose type fits no alternative is missing, such as `impl Printable for &str`.
  With a catch-all, a type that fits two alternatives gives two matches, in an order that varies.
- So the query captures the whole type and the whole trait, and code follows their fields `type`, `name` and `trait` down as far as they go.
- One pattern with an optional `trait` catches each of the 31 lab impls exactly once.
- The label spans from the first to the last `@label` capture: the `!` token, the trait and the type.

| Header | Name | Second name | Label |
|---|---|---|---|
| `impl Menu_bar` | `Menu_bar` | | `impl Menu_bar` |
| `impl fmt::Display for Menu_bar` | `Menu_bar` | `Display` | `impl fmt::Display for Menu_bar` |
| `impl From<u8> for Menu_id` | `Menu_id` | `From` | `impl From<u8> for Menu_id` |
| `impl<T: Clone> Menu_state<T> where T: Default` | `Menu_state` | | `impl Menu_state<T>` |
| `impl<T: fmt::Display> Printable for T` | `T` | `Printable` | `impl Printable for T` |
| `impl<'a> Printable for &'a dyn Printable` | `Printable` | `Printable` | `impl Printable for &'a dyn Printable` |
| `unsafe impl Send for Marker` | `Marker` | `Send` | `impl Send for Marker` |
| `impl !Sync for Marker` | `Marker` | `Sync` | `impl !Sync for Marker` |
| `impl Printable for <T as Iterator>::Item` | `Item` | `Printable` | `impl Printable for <T as Iterator>::Item` |
| `impl Printable for Option<&Marker>` | `Option` | `Printable` | `impl Printable for Option<&Marker>` |
| `impl Printable for &str` | `str` | `Printable` | `impl Printable for &str` |
| `impl Printable for [u8]` | `[u8]` | `Printable` | `impl Printable for [u8]` |
| `impl Printable for fn(u8) -> u8` | `fn(u8) -> u8` | `Printable` | `impl Printable for fn(u8) -> u8` |

## Comments and attributes

- A doc line comment ends at the start of the next line; a plain line comment ends on its own line.
  `last_row_of` handles both.
- The marker child tells `///` (`outer_doc_comment_marker`) from `//!` (`inner_doc_comment_marker`); a plain comment has no marker.
- `////` and `/***` are plain comments, as in Rust.
- A trailing comment shares its row with the item before it, so `is_attached_comment` leaves it out.
- An attribute is an `attribute_item` in front of its item, beside it like a TypeScript member decorator.
- An `inner_attribute_item` stops the walk back over leading nodes.
- A `//!` directly above an item counts as attached, unless its inner marker excludes it.
- With CRLF line endings, a plain line comment ends one column later on the same row; rows do not change.

## Nesting

- A `fn` directly in a function's body is a child of its `block`, so `body_kinds: ["block"]` makes it a child, as in Python.
- A `fn` inside an `if`, a `match`, a bare block or a closure has other kinds in between, such as `expression_statement`, so it stays out.
- Items directly in a function's body, such as a `struct` with its `impl`, are children of the function: a factory shows what it builds.
- Functions in the `declaration_list` of an impl, a trait or a module stand directly under it.

## calm-code today

- `language_for` in `languages.rs` gives a `Language_support` per extension: name, grammar, query, `wrapper_kinds` and `body_kinds`.
- `definition_kind_for` in `outline.rs` maps the `@definition.<kind>` captures to containers, callables and properties.
- `KIND_WORDS` in `toc.rs` lists the words of the header line, in their order.
- `nest_definitions` makes every callable in a container a method.
- `span_rows`, `is_attached_comment` and `collect_comment_ranges` look for the node kinds `comment` and `decorator`, in every language.
- `label_for` builds `word name`, `property name` and `name(parameters)`.
- `resolve`, `matching_entries`, `enclosing_names` and `candidate_list` work with one name per entry.
- There are no automated tests; `samples/` holds files per language for trying out.

## Lab

- `tree_dump/` prints a file's tree: `full`, `items`, `query <file.scm>` and `names <file.scm>`.
- `samples/` holds one file per theme: comments, functions, impls, impl shapes, items, modern syntax and traits.
- `queries/rust.scm` is the query the plan adopts.

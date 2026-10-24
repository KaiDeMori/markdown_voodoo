# Markdown parsers for calm-md: lay of the land

Research only. Web sources, read 2026-10-22. Nothing was installed, run or tested.
Scope: the parser only finds headings (level, line range). Text is cut and spliced from the original lines.
*inferred* = reasoned from source or docs, not run. *NOT VERIFIED* = could not be confirmed.
Labels 1 to 5 are the five questions of the task.

## Verdict

- Line ranges for `#` and setext headings: markdown-it-py, markdown-it, remark. remark adds column and offset.
- mistletoe: start line only. marko: character offsets only, added 2026-08. mistune: no positions.
- Front matter: plugin for markdown-it-py, markdown-it, remark. Missing in mistletoe, marko, mistune.
- Weight: mistletoe, marko, mistune 0 deps. markdown-it-py 1. markdown-it 6. remark-parse 42 packages in total.
- All six are maintained (a release or commit in 2026-05 or later).

## 1 and 5: release, runtime, dependencies

| Library | Latest release | Last commit | Python 3.12 / Node 22 | Runtime dependencies |
|---|---|---|---|---|
| markdown-it-py | 4.2.0, 2026-05-07 | 2026-09-17 | 3.12 yes: `>=3.10`, classifier, CI | 1: `mdurl` |
| mistletoe | 1.6.0, 2026-07-11 | 2026-10-22 | 3.12 yes: classifier (new in 1.6.0), CI 3.7 to 3.14 | 0 |
| marko | 2.2.4, 2026-08-12 | 2026-10-19 | 3.12 yes: `>=3.9`, classifier, CI 3.9 to 3.14 | 0 (extras only: python-slugify, pygments, objprint) |
| mistune | 3.4.0, 2026-10-19 | 2026-10-19 | 3.12 yes: `>=3.10`, classifier, CI. Unreleased `main` needs `>=3.11` | 0 (`typing-extensions` only on Python <3.11) |
| markdown-it (JS) | 15.0.3, 2026-10-16 (14.3.3 the same day) | 2026-10-16 | Node 22 not pinned: no `engines`, CI runs only `lts/*`. `import` and `require()` both work | 6 direct, nothing beyond them (deps.dev): argparse, entities, linkify-it, mdurl, punycode.js, uc.micro |
| remark (remark-parse + unified) | remark-parse 11.0.0, 2023-09-18 | 2026-09-27 (`remarkjs/remark`, docs only) | Node 22: no `engines`, README targets Node 16+, ESM-only | remark-parse: 4 direct, 42 in total incl. unified (deps.dev) |

Note on remark: unified 11.0.5 is from 2024-06-19. remark-frontmatter 5.0.0 and mdast-util-to-string 4.0.0 are from 2023.
The core still releases: micromark 4.0.3 (2026-09-26), mdast-util-from-markdown 2.1.0 (2026-10-03).

## 2 to 4: per library

### markdown-it-py (+ mdit-py-plugins)

- 2 Position: `Token.map = [line_begin, line_end]` on `heading_open` and `inline`. 0-based lines, end exclusive, no columns.
- ATX gives `[n, n+1]`. Setext `heading_open` includes the underline (title on line 0 over `===`: `[0, 2]`), `inline` excludes it (`[0, 1]`). `SyntaxTreeNode.map` exposes the same.
- Headings inside blockquotes and lists are tokenized as well.
- 3 Code/HTML: not headings. Rule order: table, code, fence, blockquote, hr, list, reference, html_block, heading, lheading, paragraph. The repo claims 100% CommonMark and CI runs the spec examples.
- HTML blocks need the `html` option. The default `commonmark` preset sets it.
- 3 Front matter: plugin `front_matter_plugin` from `mdit-py-plugins` 0.6.1 (2026-05-13, needs `markdown-it-py>=2.0.0,<5.0.0`). Emits a hidden `front_matter` token with `.map = [0, closing_line + 1]`. Only at line 0, only `---`. An unclosed block does not match.
- 4 Plain text: no helper. After `heading_open` comes the `inline` token. Join `.content` of its `children` of type `text` and `code_inline`. Add `text_special` if the `text_join` core rule is off. Recurse into `image.children`. Treat soft and hard breaks as a space.

### mistletoe

- 2 Position: `line_number` on block tokens only. Start line, 1-based. No end line, no column, nothing on span tokens (since v1.3.0). `AstRenderer` output includes `line_number` and `level`. `Heading` and `SetextHeading` are separate classes.
- Setext `line_number` is the first title line, not the underline (*inferred*: the paragraph that becomes the heading supplies the start).
- 3 Code/HTML: fenced and indented code stay non-heading. `HtmlBlock` is not in the default token set. Only `HtmlRenderer` and `MarkdownRenderer` register it.
- With plain `Document(...)` or `AstRenderer`, a `#` line inside `<div>` probably counts as a heading (*inferred*).
- 3 Front matter: missing. No contrib module. The one issue hit for "front matter" (#137) quotes another project.
- 4 Plain text: no helper. Recurse `.children` and join `RawText.content` (`InlineCode.children` is one `RawText`). `utils.traverse` is breadth-first and reorders nested text. Multi-line setext titles hold `LineBreak` tokens between the `RawText` nodes.
- The `Document` docstring has a CAUTION about Windows line endings (details not read).

### marko

- 2 Position: no lines. `source_span = (start, end)` on elements (plus `start_pos` and `end_pos`). 0-based character offsets, end exclusive, trailing newline included.
- Tests cover `"### Title ###\n"` and `"Title\n===\n"`, both `(0, len(text))`. A setext span covers title and underline.
- Offsets index normalized text (`\r\n`, `\r`, `\f` become `\n`). They match the original only for LF files. Derive line numbers by counting newlines.
- Brand new: PR #275 merged 2026-08-12, shortly before the 2.2.4 upload. Read on `master`. The 2.2.4 tag was not checked.
- 3 Code/HTML: not headings, by the CommonMark 0.31.2 claim and the CI spec run. `FencedCode` (priority 7) outranks `Heading` (6). Read, not run.
- 3 Front matter: missing. Bundled `ext`: footnote, toc, pangu, codehilite, gfm, latex_renderer.
- 4 Plain text: no helper (`toc` renders HTML and strips tags with a regex). Recurse `.children`: a `str` for `RawText`, `CodeSpan`, `Literal`, `LineBreak`, `InlineHTML`, otherwise a list.

### mistune

- 2 Position: none. Heading token: `type: heading`, `attrs: {level}`, `style: "atx" | "setext"`, `children`.
- Maintainer on #218: line numbers "would make the parser slower". On #402 (2026-07-21) they point to their sibling project `wenmode` (PyPI), which has a `positions=True` option. Not evaluated.
- 3 Code/HTML: fenced, indented and HTML blocks are consumed whole (`block_code`, `block_html`), so a `#` inside is not a heading. Docs claim CommonMark 0.31.2. CI loads the spec fixtures (skips not checked).
- 3 Front matter: missing. None of the 14 bundled plugins covers it.
- 4 Plain text: no helper in AST mode (`mistune.toc` renders HTML, strips tags and asserts a renderer). Recurse `children`. Leaf text sits under `raw` for `text` and `codespan`.

### markdown-it (JS)

- 2 Position: `Token.map = [line_begin, line_end]` on `heading_open` and `inline`. Docs give only that format, the code gives 0-based and end exclusive. Same shape as markdown-it-py: ATX `[n, n+1]`, setext `heading_open` includes the underline, `inline` excludes it. Newlines are normalized first.
- 3 Code/HTML: fences and indented code consume their lines first (an unclosed fence runs to the end). The repo claims 100% CommonMark.
- HTML blocks are parsed only when `options.html` is true. The default is false, the `commonmark` preset sets true. Use `markdownit({ html: true })`. Otherwise a `#` inside an HTML block probably counts as a heading (*inferred*).
- 3 Front matter: not built in, and its docs name no plugin. `markdown-it-front-matter` 0.2.4: published and last commit 2024-04-04, not archived. Emits a `front_matter` token with `.map = [startLine, nextLine + (auto_closed ? 1 : 0)]`, raw text in `.meta`. Callback required, line 0 only.
- *NOT VERIFIED*: that plugin with markdown-it 15 (dev dependency `^10.0.0`, no peer dependency).
- 4 Plain text: no helper. Join `.content` of `text` and `code_inline` children of the `inline` token. The default `text_join` rule turns `text_special` into `text`. `md.renderer.renderInlineAsText` exists, its comment says "Don't try to use it!".
- 15.x is a TypeScript rewrite (CHANGELOG). Exports map: `import` to `dist/markdown-it.mjs`, `require` to `dist/markdown-it.cjs.js`.

### remark (unified + remark-parse, mdast)

- 2 Position: every mdast node has `position.start` and `position.end`, each `{ line, column, offset }`. Line and column are 1-based, offset is 0-based in UTF-16 units. The end is the first character after the node, so `end.line` is the last line of the heading.
- ATX `# Default`: 5:1 (offset 24) to 5:10 (offset 33), line break excluded. Setext includes the underline: a depth-2 heading from 4:1 to 5:4, its text child ends at 4:18 (remark-frontmatter fixture `core-yaml-not-at-top`).
- 3 Code/HTML: *NOT VERIFIED* by test or fixture. Only claims: micromark README "100% CommonMark" (self-reported), remark-parse "commonmark compliant ... with positional info".
- 3 Front matter: plugin `remark-frontmatter` 5.0.0. `.use(remarkFrontmatter)`, default `'yaml'`, also `'toml'` or a custom matter. Emits a `yaml` node with `value` (no fences) and a `position` that includes the fences (example 1:1 offset 0 to 3:4 offset 22). Only at document start unless `anywhere`.
- 4 Plain text: `mdast-util-to-string` 4.0.0, `toString(node, { includeImageAlt: true, includeHtml: true })`. `inlineCode` gives its `value` without backticks. Emphasis and link give child text (link: derived from the rule, no test). Image gives `alt`. Inline HTML gives `value` unless `includeHtml: false`.
- Node 22: `require()` of ESM is on by default since Node 22.12.0 (Node release notes, still experimental). Not tried with these packages.

## Traps

- No front-matter step: `---` / YAML / `---` at file start parses as a thematic break plus a setext level-2 heading. The YAML lines become a heading, and a `# comment` line inside YAML would be an ATX heading. Seen in the remark-frontmatter fixture above. For the others it is *inferred*.
- HTML blocks are off by default in markdown-it JS (`html: false`) and in mistletoe (`HtmlBlock` unregistered). A `#` inside them may count as a heading.
- Position conventions differ. markdown-it and markdown-it-py: 0-based, end exclusive. mistletoe: 1-based, start only. marko: 0-based character offsets in LF-normalized text. remark: 1-based lines, 0-based offsets, end position exclusive.
- Setext in markdown-it and markdown-it-py: `heading_open.map` includes the underline, `inline.map` does not.

## Not verified

- markdown-it (JS): Node 22 itself (CI runs `lts/*` only), the front-matter plugin with v15, v15 breaking changes (search found nothing).
- marko: `source_span` in the 2.2.4 tag (read on `master`, a search did not corroborate it).
- remark: `#` inside code or HTML blocks (claims only).
- mistletoe: HTML-block handling and setext `line_number` are *inferred* from source.
- wenmode: not evaluated.

## Sources

PyPI per-version JSON (`https://pypi.org/pypi/<package>/<version>/json`), npm (`https://registry.npmjs.org/<package>/latest`), deps.dev (`https://api.deps.dev/v3/systems/npm/packages/<package>`), GitHub API and raw files on each default branch, project READMEs and docs, Node 22.12.0 release notes (nodejs.org).

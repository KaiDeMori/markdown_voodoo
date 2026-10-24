# md_linters_lay_of_the_land

State: 2026-10-22.
Basis: npm registry, PyPI, GitHub docs and source. Nothing was installed or run.
"Not verified" means no source confirmed it.

## Verdict

- markdownlint (the library) is the reference. PyMarkdown's own README calls it "a de-facto standard". The VS Code extension runs it through markdownlint-cli2.
- For findings as data, call the library. markdownlint-cli2 is CLI-first.
- pymarkdownlnt is a sibling, not a clone. Same rule numbers, small documented behavior differences.
- Pick by the runtime calm-md is written in.
- Traps for calm-md:
  - markdownlint has every rule on unless `"default": false` is set.
  - Inline `<!-- markdownlint-disable -->` comments silence rules unless `noInlineConfig: true`.
  - pymarkdownlnt recognizes front matter only with its `front-matter` extension on.

## 1. Maintenance and weight

| | markdownlint-cli2 | markdownlint (library) | pymarkdownlnt |
| --- | --- | --- | --- |
| Latest | 0.24.0, 2026-10-21 | 0.42.0, 2026-10-15 | 0.9.41, 2026-10-13 |
| Runtime | node >=22 | node >=22 | python >=3.10, 3.12 listed |
| Direct dependencies | 9 | 10 | 5 |
| Transitive dependencies | not verified | 40 | 6 |

- All three are maintained.
  - cli2: six releases between 2026-04-22 and 2026-10-21.
  - Library: 0.41.0 (2026-06-10), 0.41.1 (2026-07-13), 0.42.0 (2026-10-15).
  - pymarkdownlnt: six releases since 0.9.36 (2026-03-16). Pre-1.0, but its API declares interface version 1 stable.
- Node 22 is the minimum for both Node packages. cli2 0.24.0 pins markdownlint 0.42.0.
- Direct dependencies:
  - cli2: globby, js-yaml, smol-toml, micromatch, jsonpointer, markdown-it, jsonc-parser, markdownlint, a default formatter.
  - Library: eight micromark packages, re2js, string-width.
  - pymarkdownlnt: typing-extensions, application-properties, application-file-scanner, columnar, py-walk.
- Transitive counts are from deps.dev. It has no data yet for cli2 0.24.0, released yesterday.
- Dates: npm publish time (Node), PyPI upload and GitHub release (pymarkdownlnt, same day). DavidAnson's repos publish git tags, not GitHub Releases.

## 2. Library use and findings as data

- markdownlint: yes.
  - Call: `import { lint } from "markdownlint/promise"` (also `/sync`, `/async`).
  - Input: `strings: { name: text }` or `files: [...]`.
  - Output: `{ name: [finding, ...] }`.
  - Finding: `lineNumber`, `ruleNames` (id first, then aliases), `ruleDescription`, `ruleInformation` (doc URL), `errorDetail`, `errorContext`, `errorRange`, `fixInfo`, `severity`.
- markdownlint-cli2: not as data.
  - `main(params)` is exported but returns an exit code. The README has no programmatic-API section.
  - Findings leave only through output formatters. The JSON formatter writes a file.
  - It re-exports the library (`markdownlint-cli2/markdownlint/promise`), so code gets the exact version cli2 pins.
- pymarkdownlnt: yes.
  - Call: `from pymarkdown.api import PyMarkdownApi`, then `PyMarkdownApi().scan_string(text)` or `.scan_path(path)`.
  - Output: an object with `scan_failures`, `pragma_errors`, `critical_errors`.
  - Scan failure: `scan_file`, `line_number`, `column_number`, `rule_id`, `rule_name`, `rule_description`, `extra_error_information`.
  - `scan_string("")` raises `PyMarkdownApiArgumentException`.

## 3. Heading rules

Both linters have all five, on by default, with the same ids and aliases.

| Rule | markdownlint parameters | pymarkdownlnt parameters |
| --- | --- | --- |
| MD001 `heading-increment` | `front_matter_title` (regex) | `front_matter_title` (field name) |
| MD003 `heading-style` | `style`: atx, atx_closed, consistent, setext, setext_with_atx, setext_with_atx_closed | same six styles, plus `allow-setext-update` |
| MD022 `blanks-around-headings` | `lines_above`, `lines_below` (int or per-level list), `include_front_matter` | `lines_above`, `lines_below` (int) |
| MD024 `no-duplicate-heading` | `siblings_only` | `siblings_only` (alias `allow_different_nesting`) |
| MD025 `single-title`, `single-h1` | `level`, `front_matter_title` (regex) | `level`, `front_matter_title` (field name) |

- A paragraph line directly above `---`: no dedicated rule in either linter.
- markdownlint's MD003 doc names this case. A horizontal rule right below text makes it a level 2 setext heading, which can trigger MD003.
- It triggers only on a style mismatch.
  - `style: "atx"` flags every setext heading.
  - `consistent` misses it when the accidental heading is the first heading (the first heading sets the style).
- pymarkdownlnt documents MD003 as equivalent, so the same applies. Not run.

## 4. Configuration

- markdownlint library: per call only.
  - `options.config` maps a rule id, alias or tag to `true`, `false`, `"error"`, `"warning"` or a parameter object. An object enables and configures the rule.
  - `"default": false` switches everything off first. `{ "MD001": true }` alone keeps every other rule on.
  - It finds no config files itself. `readConfig` loads one file.
  - Front matter is ignored by default (`frontMatter` option).
- markdownlint-cli2: files.
  - `.markdownlint-cli2.{jsonc,yaml,cjs,mjs}` (all options, rules under `config`) and `.markdownlint.{jsonc,json,yaml,yml,cjs,mjs}` (rules only).
  - A file applies to its directory and below, and merges with files in parent directories. `overrides` apply per glob. `--config` loads one file.
  - `noInlineConfig` is an option here too.
- pymarkdownlnt: files or per call.
  - Files: `.pymarkdown` in the project root, `pyproject.toml` (`[tool.pymarkdown]`), or `--config file` (JSON, YAML, TOML).
  - API modifiers: `configuration_file_path`, `enable_rule_by_identifier`, `disable_rule_by_identifier`, `set_boolean_property`, `enable_extension_by_identifier`.
  - Most rules are on by default. Off: MD002, MD006, PML100 to PML102.
  - Only a chosen set: `plugins.selectively_enable_rules = true`, then `plugins.<id>.enabled = true` per rule. CLI shortcut: `-d "*"`.

Only the five heading rules, markdownlint (`atx` chosen so an accidental setext heading is flagged):

```json
{
  "default": false,
  "MD001": true,
  "MD003": { "style": "atx" },
  "MD022": true,
  "MD024": { "siblings_only": true },
  "MD025": true
}
```

## 5. pymarkdownlnt vs markdownlint

- Same numbers and aliases where a rule exists in both.
- README promise: keep each rule's intent, adjust behavior "to follow the Markdown specifications more closely". Equal numbers do not guarantee equal findings.
- Missing in pymarkdownlnt: MD052. Extra, off by default: MD002, MD006 (both deprecated), PML100, PML101, PML102.
- The five heading rules, per pymarkdownlnt's own "Differences" notes:
  - MD003: equivalent, plus the extra parameter `allow-setext-update`.
  - MD001, MD025: `front_matter_title` is a front matter field name, not a regex.
  - MD022: "largely cosmetic". Column numbers differ inside block quotes and lists. It says the original mis-assesses a few boundary cases next to thematic breaks and HTML blocks.
  - MD024: no differences listed.
- Only the pragmas extension is on by default. Front matter needs the `front-matter` extension.
- No complete per-rule difference list was found.

## 6. VS Code extension

- Same engine: its README says linting is performed by the markdownlint-cli2 engine, which runs the markdownlint library.
- Same config files: `.markdownlint-cli2.*` and `.markdownlint.*` in the same or a parent directory.
  - Precedence: cli2 files, then `.markdownlint.*`, then VS Code settings (`markdownlint.config`, `markdownlint.configFile`), then defaults.
- Same version is not guaranteed.
  - Marketplace 0.62.1 (2026-08-02) pins markdownlint-cli2 0.23.2, which pins markdownlint 0.41.1.
  - Latest today: cli2 0.24.0 with markdownlint 0.42.0.
- To agree: same pinned version, and our tool reads the same config files. A private per-call config will not match the editor. VS Code user settings are invisible to our tool.

## Another linter

- rumdl 0.3.0 (GitHub release 2026-10-17): Rust binary, installs via uvx, pip, npm, cargo or brew. Its docs claim all 53 markdownlint rules, automatic discovery of markdownlint configs, and `rumdl check --output-format json`. They also list intentional behavior differences. Not run.

## Not verified

- Transitive dependency count of markdownlint-cli2 0.24.0: deps.dev has no data yet.
- pymarkdownlnt flagging an accidental setext heading under `style: atx`: documented as equivalent, not run.
- Switching off inline `pyml` pragmas in pymarkdownlnt: no setting found.
- The API form of `selectively_enable_rules` (`set_boolean_property`): inferred from the documented `--set` mapping.
- Extension pin: read from the repo's main package.json (same version as the Marketplace listing), not from the installed extension.
- Per-rule differences beyond the five heading rules.

## Sources

- npm registry: [markdownlint-cli2](https://registry.npmjs.org/markdownlint-cli2) and [markdownlint](https://registry.npmjs.org/markdownlint) (versions, dependencies, engines, publish times).
- PyPI: [pymarkdownlnt](https://pypi.org/project/pymarkdownlnt/) (JSON API). [PyMarkdown releases](https://github.com/jackdewinter/pymarkdown/releases).
- markdownlint: [README](https://github.com/DavidAnson/markdownlint/blob/main/README.md) and [rule docs](https://github.com/DavidAnson/markdownlint/tree/main/doc) (md001, md003, md022, md024, md025).
- markdownlint-cli2: [README](https://github.com/DavidAnson/markdownlint-cli2/blob/main/README.md) and [markdownlint-cli2.mjs](https://github.com/DavidAnson/markdownlint-cli2/blob/main/markdownlint-cli2.mjs).
- VS Code extension: [README](https://github.com/DavidAnson/vscode-markdownlint/blob/main/README.md), [package.json](https://github.com/DavidAnson/vscode-markdownlint/blob/main/package.json), the Marketplace query API.
- PyMarkdown: [docs source](https://github.com/jackdewinter/pymarkdown/tree/main/newdocs/src) (rules, api, advanced_configuration, plugins/rule_md001, md003, md022, md024, md025), [README](https://github.com/jackdewinter/pymarkdown/blob/main/README.md), [api.py](https://github.com/jackdewinter/pymarkdown/blob/main/pymarkdown/api.py).
- rumdl: [README](https://github.com/rvben/rumdl/blob/main/README.md) and [markdownlint comparison](https://github.com/rvben/rumdl/blob/main/docs/markdownlint-comparison.md).
- Transitive counts: [deps.dev API](https://deps.dev).

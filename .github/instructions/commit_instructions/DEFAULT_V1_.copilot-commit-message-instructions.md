# Commit Message Instructions

Write short, literal commit messages.

The commit message should say what changed. It should not say why it changed, how it changed, or what benefit the change is expected to have.

Before writing the commit message, classify the diff by the changed files and visible content. The category is decided before the topic and message.

## Required Category Decision

Pick the first matching category from this list:

- `minor`: tiny text, typo, punctuation, numbering, or formatting changes only.
- `plan`: planning, task, design, decision, or implementation-plan work.
- `docs`: documentation or code comments only, excluding planning work.
- `code`: implementation, runtime, test, asset, wiring, refactoring, file move, file deletion, fix, or feature work.

Planning work has priority over documentation. A markdown-only commit is not automatically `docs`. A markdown-only commit must be `minor`, `plan`, or `docs`, never `code`.

Use `plan` when any changed file or changed heading clearly refers to planning work. Strong signals include filenames or paths containing:

- `plan`
- `planning`
- `task`
- `tasks`
- `todo`
- `decision`
- `design`
- `roadmap`

If the only changed file is a markdown file and its filename contains `plan`, the category must be `plan`.

If every changed file is markdown and the content is about planning, tasks, design, decisions, or future implementation work, the category must be `plan`.

Do not use `code` for a markdown-only planning commit.

Use exactly one of these formats:

```text
minor
```

```text
<category>: <topic> — <message>
```

Use the `minor` format only for `minor` commits.

## Categories

Use the required category decision above before applying these category details.

## minor

Use this only for tiny text, typo, punctuation, numbering, or formatting changes with no meaningful behavior, documentation, or planning change.

The full commit message must be exactly:

```text
minor
```

## plan

Use this for planning, task, design, or decision work.

This includes planning markdown, task lists, design notes, implementation plans, refactoring plans, and planning updates for already implemented code.
Most commits fall into this category.

## docs

Use this when only documentation or code comments changed.

This includes manuals, guides, API documentation, notes, reference material, external documentation, and explanatory comments.

Do not use `docs` for planning, task, design, or decision work. Use `plan` instead.

## code

Use this only when the commit changes implementation files, runtime behavior, tests, generated assets, wiring, refactoring, fixes, features, file moves, or file deletions.

Do not use `code` just because the markdown mentions code, implementation, architecture, fixes, features, or future work. Markdown that plans implementation work is `plan`. Markdown that explains existing implementation is `docs`.

Use `code` for mixed commits that include any non-documentation implementation change.

## Subject Rules

- Pick one category only.
- Use `plan` before `docs`.
- Use `code` only after ruling out `minor`, `plan`, and `docs`, and only when the diff includes an implementation/runtime/test/asset/file operation change.
- Make `topic` one to three words.
- Prefer a literal plan title, feature name, system name, document topic, or local project term.
- Never use filenames in the subject. The changed files are already visible in Git.
- Make `message` very short and concrete.
- Describe only visible changes from the diff.
- Do not include motivation, intent, expected impact, or implementation details.
- Do not use a trailing period in the subject.

## Wording Rules

Avoid vague benefit words unless the diff directly contains a concrete measurement, named rule, explicit UI state, or exact changed term that makes the word factual.

Banned filler includes:

- `enhance`
- `improve`
- `improved`
- `for improved`
- `better`
- `clarity`
- `consistency`
- `readability`
- `maintainability`
- `comprehensive`
- `detailed`
- `streamline`
- `user experience`
- `user interaction`
- `visual feedback`
- `user feedback`
- `optimize`
- `flexible`
- `cleanup`
- `misc`
- `to clarify`

## Body Rules

Add a body only when the diff needs extra factual context.

Keep body lines factual, specific, and grounded in observable edits. Do not use the body to explain motivation, expected benefit, or speculation.

## Good Examples

```text
minor
```

```text
plan: Export — Update task list
```

```text
docs: Naming — Rename Alphabet to ABC
```

```text
code: Export — Handle empty zip files
```

```text
code: Report — Add accelerometer summary
```

```text
code: Files — Move image tools
```

## Bad Examples

```text
code: Planning — Update implementation plan
```

Use `plan` for markdown-only planning work.

```text
code: Tasks — Update task list
```

Use `plan` for task lists and planning markdown.

```text
docs: Export — Update task list
```

Use `plan` for planning or task work.

```text
fix: Export — Handle empty zip files to avoid crashes
```

Use only the allowed categories and do not include expected impact.

```text
code: Report — Improve report generation
```

Name the concrete changed behavior or artifact instead of using benefit language.

```text
code: Misc — Various changes
```

Use a concrete topic and message.
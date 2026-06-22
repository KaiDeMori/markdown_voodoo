---
description: "Use when writing a git commit message for this repository."
---

Write short, literal commit messages.

Goal:
- Say what changed.
- Do not say why it changed.
- Do not say how it was changed.
- Do not speculate.

Use exactly one of these formats:
- <category>
- <category>: <topic> — <message>

Use <category> alone only for `minor`.

Pick the first matching category from this list:

1. `minor`
Use this only for tiny text, typo, or formatting changes with no real code or behavior change.
The full commit message must be exactly:
`minor`

2. `plan`
Use this only for planning markdown files.
If the changed file is a `.md` file and its filename contains `plan` or `task`, use `plan`.

3. `docs`
Use this when only documentation or code comments changed.
This includes manuals, guides, API documentation, notes, PDFs, and normal markdown documentation.
Do not use `docs` for planning markdown files.

4. `code`
Use this for all code changes.
This includes fixes, new behavior, refactoring, renames, moves, deletions, cleanup, and mixed commits.

Rules:
- Pick one category only.
- Check `plan` before `docs`.
- If a changed markdown filename contains `plan` or `task`, the category is `plan`.
- If the change is not `minor`, `plan`, or `docs`, use `code`.
- `topic` must be 1 to 3 words.
- `message` must be very short and concrete.
- Describe only visible changes.
- Do not include motivation.
- Do not include implementation details.
- Do not use filler words like "improve", "better", "cleanup" or "misc" unless they are the actual change.
- When unsure, use `code`.

Good examples:
- `minor`
- `plan: Cleanup — Update export task list`
- `docs: Naming — Rename Alphabet to ABC`
- `code: Export — Handle empty zip files`
- `code: Report — Add accelerometer summary`
- `code: Files — Move image tool sources`

Bad examples:
- `docs: Cleanup — Update export task list`
- `fix: Export — Handle empty zip files to avoid crashes`
- `new: Report — Improve report generation`
- `refactor: Misc — Various changes`
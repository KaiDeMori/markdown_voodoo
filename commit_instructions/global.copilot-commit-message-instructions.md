# Commit message instructions

- Use this subject format: `category: Caption — concise change phrase`.
Allowed categories are:
`doc`, `plan`, `impl`, and `typo`.
- Use `doc:` for documentation edits that explain existing behavior, APIs, workflows, or reference material.
- Use `plan:` for planning work. This is the default for planning folders and markdown-only planning diffs.
- Use `impl:` for implementation changes, including features, behavior changes, tests, assets, or runtime wiring.
- Use `typo:` for typo-only changes and tiny syntax fixes, such as adding a missing semicolon.
- Make `Caption` one to three words. Prefer a literal plan title, feature name, system name, or local project term. If none exists, infer a short contextual caption from the diff.
- After the dash, write a brief phrase that names the concrete changed idea, behavior, rule, or artifact. Use terms from the changed code or document.
- Do not put filenames in the subject. The changed files are already visible in the commit.
- Keep the subject brief, concise, and non-redundant. Omit a trailing period.
- Stay grounded in observable edits. Do not invent motivation, impact, cleanup, polish, readability, maintainability, performance, or user benefit unless the diff directly shows it.
- Do not use generic benefit language in the subject. Ban agent filler such as `enhance`, `improve`, `improved`, `for improved`, `clarity`, `consistency`, `readability`, `maintainability`, `comprehensive`, `detailed`, `streamline`, `better`, `user experience`, `user interaction`, `visual feedback`, `user feedback`, `optimize`, `flexible`, and `to clarify` unless the diff contains a concrete measurement, named rule, or explicit UI state that makes the word factual.
- Add a body only when the diff needs extra factual context. Keep body lines factual and specific.

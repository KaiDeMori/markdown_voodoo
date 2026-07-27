---
name: unicode-glyph-render
description: |
  - **`glyph`**: Renders a single Unicode codepoint — as `U+<HEX>` or a literal character — to a PNG at an absolute file path.
  - **`string`**: Renders a string of Unicode text to a PNG at an absolute file path.
---

## Usage

Render a single codepoint:

```
${CLAUDE_SKILL_DIR}/.venv/Scripts/python.exe ${CLAUDE_SKILL_DIR}/render_glyph.py glyph <codepoint> --output-file <absolute path>
```

Render a shaped string:

```
${CLAUDE_SKILL_DIR}/.venv/Scripts/python.exe ${CLAUDE_SKILL_DIR}/render_glyph.py string <text> --output-file <absolute path>
```

`<codepoint>` is `U+<HEX>` (e.g. `U+1F600`) or a single literal character.

`--output-file` is required and must be an absolute path to the PNG file to write; its parent directory is created automatically.

Stdout on success is one JSON object: `{"codepoint"` (or `"text"`), `"fonts": [...]`, `"path": ...}`. On failure: `{"argument": ..., "error": ...}`, exit code 1.

---
name: calm-vitest
description: >-
  hallmark_tool
  A calm Vitest run: how it went, from how many to where to what, without the flood.
  Use when a raven wants to run Vitest tests, or see which tests failed and why, without hundreds of lines of output.
---

# calm-vitest

```
calm-vitest [file ...]
calm-vitest where <file>
calm-vitest what <file> <test name>
```

Start zoomed out, and zoom in only when the answer asks for it:

| Command | Answers | Happy path |
|---|---|---|
| `calm-vitest [file ...]` | How did the run go? | `tests/memory/data_and_storage: 1 block red, 44 tests, 1 sentence` |
| `calm-vitest where <file>` | Where is it red, and why? | `stored record: 44 tests, 1 sentence`, then the sentence |
| `calm-vitest what <file> <test name>` | What exactly did one test say? | the test's full output |

- Run it where the suite lives, in the folder with `package.json`; it uses that project's own Vitest and never downloads anything.
- A block is a `describe`; a sentence is the first line of a failure's message, and failures that say the same sentence count once.
- Quoted values count as blanks, so `'conversation_halting'` and `'conversation_moved'` in the same words make one sentence in two variants; `what` still gives one test's exact words.
- The overview shows red files first, at most 20 lines, then how many more.
- `where` and `what` read the last run's report, so zooming in never runs the suite again.
- A file is named by its path, its label from the overview, or the end of it: `where data_and_storage` is enough when only one file fits.
- A test is named by its title, or by its block and title as `where` shows them: `what mixed "menu bar > settings > opens"`.
- The full report and Vitest's own output stay in the workspace's `scratchpad/calm-vitest/`.
- Exit 0 when the run ran, red included; 1 when Vitest made no report, or a name fits nothing.
- The limits are the variables at the top of `calm_vitest.sh` and `calm_vitest_report.mjs`.

'nough said.

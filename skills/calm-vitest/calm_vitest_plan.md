# calm-vitest plan

The otis builder's wish: a raven sees how a test run went, from zoomed out to zoomed in, without forty-four lines for one fact.

## Decided

- calm-vitest lives in `skills/calm-vitest/`, without the mark `hallmark_tool` until ravens have flown it; `calm_vitest.sh` gives it its short call.
- Vitest runs underneath, with its JSON reporter.
- The full report stays in the workspace's `scratchpad/calm-vitest/`, as calm-fetch keeps its files; only the lines below enter a window.
- Three levels, like calm-grep:
  - `calm-vitest [file ...]`: runs the files or the whole suite, and prints one line per file, like `data_and_storage: 1 block red, 44 tests, 1 sentence`, or `conversation_history: green`.
  - `calm-vitest where <file>`: the red blocks of one file, each with its count and its one sentence, cut like calm-grep cuts a line.
  - `calm-vitest what <file> <test name>`: one test's full output, nothing else.
- A sentence is the first line of a failure's message, with quoted values as blanks; failures with the same sentence count once, and their exact words count as variants.
- `where` and `what` read the last run's report, so zooming in never runs the suite again.
- Exit 0 when the run ran, red included.

## Steps

- [x] Ask the otis builder where the suite lives, how it runs, what a block is to them, and whether `scratchpad/` stays out of their git.
- [x] Write `calm_vitest.sh` and the report reader.
- [x] Test on a small suite with one red block that fails 44 times with one sentence.
- [x] `SKILL.md`, `deploy.bat` and a line in `INDEX.md`; the meta-deploy finds it by its `calm-` name.
- [ ] The otis builder flies it.

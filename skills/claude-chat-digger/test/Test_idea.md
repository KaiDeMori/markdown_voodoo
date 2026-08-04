# CCD test idea

## Goal

A minimal, dependency-free test for CCD's index/search round trip.
No test framework. One script: `CCD_Test.py`.

## Principle: full isolation

The test never touches the real corpus or the real index.
Every run uses its own scratch `corpus_root` and `index_path`, both accepted directly by `Chat_digger(index_path=..., corpus_root=...)`.

Reasons:

- No risk to real conversation history.
- No dependency on how large the real corpus is — a real rebuild reprocesses every stored conversation.
- Deterministic: the scratch corpus starts empty on every run.

## Folder layout

```
test/
  CCD_Test.py         the test script
  example_chat/        checked-in fixture: one recorded real chat, mirroring the real
                        projects/<encoded-cwd>/<session_id>.jsonl layout
  scratch/              created by the test script at run time, deleted/recreated each run
    corpus/               scratch corpus_root
    CCD_index.db           scratch index_path
```

`example_chat/` is committed. `scratch/` is generated, not committed.

## Fixture

One dedicated, real Claude Code chat session, recorded on purpose for this test.
Contains one or more distinctive, unique strings that cannot plausibly occur in an unrelated conversation.

Copied as-is from `~/.claude/projects/<encoded-cwd>/<session_id>.jsonl` into `example_chat/`, keeping the same nested shape for realism.
The encoded folder name itself is irrelevant to CCD — it only trusts each record's `cwd` field to recover the real project path, never the folder name.
Nesting is kept for realism, not because CCD requires it.

## Test flow

1. Recreate an empty `scratch/` directory.
2. `build_index()` against the empty scratch corpus.
   Required: a search against a never-built index raises rather than returning zero results, so this step is what makes step 3 valid rather than an error.
3. `search_all(<unique_string>)` — assert zero matches.
4. Copy `example_chat/`'s contents into `scratch/corpus/` ("inject").
5. `build_index()` again (rebuild is always a full rebuild — there is no incremental mode).
6. `search_all(<unique_string>)` — assert a match is found, in the expected session, with the expected content.
7. Clean up `scratch/`.

## Implementation notes

- Drive `Chat_digger` directly through its Python API (`CCD_engine.Chat_digger`), not the `CCD.py` CLI as a subprocess — `CCD.py`'s command handlers are thin wrappers over the same calls.
- CCD's modules import flatly (`from CCD_api import ...`, no package `__init__.py`).
  `CCD_Test.py` must add the skill root to `sys.path` before importing `CCD_engine`.
- Pass and fail with plain `assert` plus a clear message; no `unittest` / `pytest`.

## Out of scope for this first test

Only the index/search round trip above.

Not yet covered: `in`, `show`, `origin`, `tree`, `family`, `families`, `list`; forks, compaction, streamed duplicates, unknown record types.
This scaffold — scratch corpus, scratch index, fixture injection — is meant to be reused once those follow.

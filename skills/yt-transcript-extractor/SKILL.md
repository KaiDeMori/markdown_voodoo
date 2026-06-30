---
name: yt-transcript-extractor
description: Pull a clean, de-duplicated transcript from a YouTube video, then optionally fact-check its claims. Use when the user wants the transcript or captions of a YouTube video, wants a video turned into readable text/markdown, or wants to verify or fact-check the claims made in a video. Wraps the local `ytx` Python toolchain (yt-dlp + a PO-token provider) that lists tracks, auto-picks the most faithful one, downloads, and cleans it into a markdown transcript saved in the user's current workspace.
---

# YouTube Transcript Extractor (ytx)

`ytx` turns a YouTube URL into a clean transcript. One command lists the available subtitle tracks, decides which is most faithful (human subtitles > auto-captions, original language > translations, json3 > other formats), downloads it, and de-duplicates it into a tidy markdown file at a destination you choose (the user's workspace). Output is a single JSON object on stdout (`out_dir` + each transcript's absolute `path`); all progress goes to stderr.

## Where it lives

The code and toolchain live at one home — this skill's own folder, under your home directory:

```
~/markdown_voodoo/skills/yt-transcript-extractor/
```

Run it from that folder with the project's own venv python, and pass `--out-dir` to put the results in the user's workspace (see **Output location** below). `~` is unquoted so the shell expands it:

```bash
cd ~/markdown_voodoo/skills/yt-transcript-extractor
PY=".venv/Scripts/python.exe"
"$PY" -m ytx --out-dir "<WORKSPACE>/YT-Transcripts" "https://www.youtube.com/watch?v=VIDEO_ID"
```

If `.venv` / `tools/` / `cookies/cookies.txt` aren't there yet (a fresh clone), set them up once via [docs/Setup.md](docs/Setup.md). Confirm the toolchain with `"$PY" -m ytx.config` (no network).

## Output location — decide before downloading

Outputs go to the **user's current workspace**, never this skill folder. Resolve the destination first:

- **If you already know it** — the user named a folder, or it's clear from context — use that as `--out-dir`.
- **Otherwise** default to `<WORKSPACE>/YT-Transcripts` (the convention). Glob for that folder first: if it already exists, you're on firm ground; if not, propose creating it. Either way **confirm with the user** — and fold that into the same permission prompt you already owe them before any YouTube contact (next section), so it's one question, not two.

Pass the resolved absolute path as `--out-dir`. The clean transcript lands at that root; the `raw/` and `meta/` caches sit in subfolders beside it.

## ⛔ Hard rule — ask before any YouTube contact

yt-dlp hitting YouTube gets rate-limited / bot-walled fast. **Before** running anything that touches YouTube — `ytx`, `ytx.extract`, `ytx.list_subs`, `ytx.download_subs` — you MUST ask the user via **AskUserQuestion** and get a yes. Local-only stages (`ytx.clean`, `ytx.config`) need no permission.

Bundle the **output destination** into that same question: confirm both "OK to fetch from YouTube?" and "save to `<WORKSPACE>/YT-Transcripts`?" in one `AskUserQuestion`.

## Phase 1 — get the transcript, then check it's actually good

Run `"$PY" -m ytx --out-dir DIR "<url>"`. It prints JSON with `out_dir` and each transcript's absolute `path`, `lang`, `kind` (manual/auto), `format`, `lines`, and `words`. The cross-check listing is cached at `<out-dir>/meta/<id>.subs.json` (carries `original_lang`, `duration_s`, and which langs are truly `manual` vs `auto`).

YouTube routinely mislabels tracks, so **don't trust the labels — read the file** and confirm:

- **Language is what it claims.** The text should actually read as the chosen `lang`, and that lang should line up with `original_lang` in the cached listing. A track tagged `en` that reads as another language is mislabeled — re-run with `--prefer <lang>`.
- **"Manual" really is human-made.** A `kind=manual` track should read like edited prose — punctuation, capitalization, no caption run-ons. If it reads like raw ASR, the human-made label is wrong; prefer the auto-captions or another track instead.
- **Length is plausible.** `words` should be sane for `duration_s` (rough speech is ~120–160 wpm). A tiny word count on a long video means an empty or wrong track.
- **It's coherent, not garbage.** Skim the produced `.md` — real sentences, not truncated, empty, or endlessly repeated lines.

If a check fails, re-pick: `--prefer <lang>`, `--also-translation`, `--refresh` (ignore the cache), or drive the stages directly. The decision logic and per-stage commands are in [docs/AGENTS.md](docs/AGENTS.md).

## Phase 2 — fact-check (on request)

When the user wants the video's claims verified, apply the prompt in [docs/Fact_check_prompt.md](docs/Fact_check_prompt.md) (read it on demand) to the Phase-1 transcript, and write a companion file next to the transcript, in the same `--out-dir`: `<channel> - <title> [<id>].fact-check.md` (the transcript's base name with a `.fact-check.md` suffix).

For the shape of the finished artifact (method note, verdict-at-a-glance table, corrections with primary sources), see the worked example in [docs/example/](docs/example/).

## Full reference

- [docs/AGENTS.md](docs/AGENTS.md) — the complete operating guide: decision rules, every flag, individual stages, troubleshooting.
- [docs/Setup.md](docs/Setup.md) — one-time install of the venv, deno, the PO-token server, and cookies.
- [docs/Fact_check_prompt.md](docs/Fact_check_prompt.md) — the Phase-2 fact-check prompt (deliberately terse).
- [docs/example/](docs/example/) — a finished transcript + its fact-check, as a reference for the output.

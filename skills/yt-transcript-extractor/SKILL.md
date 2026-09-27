---
name: yt-transcript-extractor
description: Pull a clean, de-duplicated transcript from a YouTube video, then optionally fact-check its claims. Use when the user wants the transcript or captions of a YouTube video, wants a video turned into readable text/markdown, or wants to verify or fact-check the claims made in a video. Wraps the local `ytx` Python toolchain (yt-dlp, with optional PO-token and cookie escalation) that lists the source tracks, probes the candidates you pick, and cleans the chosen one into a markdown transcript saved in the user's current workspace.
---

# YouTube Transcript Extractor (ytx)

`ytx` turns a YouTube URL into a clean transcript. YouTube's track labels are unreliable, so `ytx` gathers the evidence and you decide: it lists the source tracks with their context, downloads the 1–2 candidates you name and shows a sample of each, then cleans the chosen track into a tidy markdown file at a destination you choose (the user's workspace). Every stage prints one JSON object on stdout; all progress goes to stderr.

## Where it lives

The code and toolchain live at one home — this skill's own folder, under your home directory:

```
~/markdown_voodoo/skills/yt-transcript-extractor/
```

Run it from that folder with the project's own venv python, and pass `--out-dir` to put the results in the user's workspace (see **Output location** below). `~` is unquoted so the shell expands it:

```bash
cd ~/markdown_voodoo/skills/yt-transcript-extractor
PY=".venv/Scripts/python.exe"
"$PY" -m ytx.list_subs --out-dir "<WORKSPACE>/YT-Transcripts" "https://www.youtube.com/watch?v=VIDEO_ID"
```

If `.venv` isn't there yet (a fresh clone), set up the toolchain once via [docs/Setup.md](docs/Setup.md) — cookies and the PO-token server are optional escalation, not part of the core install. Confirm with `"$PY" -m ytx.config` (no network).

## Output location — decide before downloading

Outputs go to the **user's current workspace**, never this skill folder. Resolve the destination first:

- **If you already know it** — the user named a folder, or it's clear from context — use that as `--out-dir`.
- **Otherwise** default to `<WORKSPACE>/YT-Transcripts` (the convention). Glob for that folder first: if it already exists, you're on firm ground; if not, propose creating it. Either way **confirm with the user** — and fold that into the same question you already owe them before any YouTube contact (next section), so it's one question, not two.

Pass the resolved absolute path as `--out-dir`, and the same one to every stage. The clean transcript lands at that root; the `raw/` and `meta/` caches sit in subfolders beside it.

## ⛔ Hard rule — ask before any YouTube contact

yt-dlp hitting YouTube gets rate-limited / bot-walled fast, and every request counts. **Before** running anything that touches YouTube — `ytx.list_subs`, `ytx.probe`, `ytx`, `ytx.extract`, `ytx.download_subs` — ask the user **in chat** (not via `AskUserQuestion`) and get a yes. Local-only stages (`ytx.clean`, `ytx.config`) need no permission.

- **One question covers the start:** the listing, the first probe call, and the output destination — e.g. "OK to fetch from YouTube and save to `<WORKSPACE>/YT-Transcripts`?".
- **Every further probe call needs a new OK.**
- **The `ytx --track` run after a probe is local** (cached listing, probed raw file) and needs no new OK.

## Phase 1 — get the transcript

Use the explicit flow below. The one-shot `"$PY" -m ytx --out-dir DIR "<url>"` (list, take the recommended track, download, clean — all in one run) is a shortcut: use it only when the user asks for it.

### Step 1 — list

```bash
"$PY" -m ytx.list_subs --out-dir DIR "<url>"
```

One extraction, no caption downloads. The report (also cached as `<out-dir>/meta/<id>.subs.json`):

- `title`, `channel`, `description_head`, `duration_s` — the context for judging which language the video is spoken in.
- `original_audio_lang` — the audio track YouTube flags as original. Present only on multi-audio (e.g. auto-dubbed) videos, and often `null`.
- `source_tracks` — every manual track and every ASR track. Each has `track` (the id you pass on, `<lang>.<kind>`), `kind` (`manual`/`auto`), YouTube's `name`, and `source_lang` (the language the track was made in, read from its URL). Machine translations are never listed; `machine_translations` only counts them.
- `recommended` — the automatic pick and its `reason`. `ambiguous: true` means the pick is not backed by spoken-language evidence.

### Step 2 — probe

Decide which track(s) to look at: usually one, two for a real toss-up. Judge from title, channel, description and the track list — `recommended` is a suggestion, not the decision.

```bash
"$PY" -m ytx.probe --out-dir DIR <id> --tracks en-orig.auto[,en.manual]
```

At most 2 tracks per call. Each track is downloaded into `raw/` (download-once, so this is also the final download) and reported with `words`, `words_per_minute`, `sample_start` and `sample_middle`. Read the samples. Probe right after listing: the cached caption URLs expire after some hours (`ytx` then stops and says so; re-run `ytx.list_subs`).

### Step 3 — extract

```bash
"$PY" -m ytx --out-dir DIR --track <track> "<url>"
```

Local after a probe. Prints JSON with `out_dir` and, per transcript, `path`, `track`, `name`, `source_lang`, `translated_to`, `selection`, `lines` and `words`. The transcript header records the same:

- `Source` — YouTube's name, `source_lang`, `translated_to`.
- `Selection` — `explicit · recommended=<track> · match=yes|no` for `--track`; `recommended` or `recommended (ambiguous)` for the one-shot.

Mention a `match=no` to the user: those mismatches are the evidence for whether the one-shot can be trusted.

### Check the result

Don't trust the labels — read the file and confirm:

- **Language is what it should be.** The text reads as its `source_lang`, and that is the language the video is spoken in (title, channel, description). If not, see the failure modes below and re-run Step 3 with another `--track`.
- **"Manual" really is human-made.** A `manual` track should read like edited prose — punctuation, capitalization, no caption run-ons. If it reads like raw ASR, the label is wrong.
- **Length is plausible.** Speech runs roughly 120–220 words per minute; lively conversations sit at the top of that range. Far fewer means an empty or partial track.
- **It's coherent, not garbage.** Real sentences, not truncated, empty, or endlessly repeated lines.

## YouTube failure modes

| What you see | Cause | What to do |
|---|---|---|
| Several `-orig` tracks, each named "(Original)" | Auto-dubbing: every dub audio track gets its own ASR track. Only one is the spoken original. | Pick by `original_audio_lang`, else by title, channel and description. Probe when unsure. |
| The only ASR track reads as nonsense in a language that doesn't fit title and channel | ASR ran in the wrong language (the uploader's "video language" setting). Its machine translations are translations of that nonsense. | Use a manual track in the spoken language if one exists. Otherwise tell the user YouTube has no faithful transcript for this video. |
| A manual track's text is not in its labelled language | The uploader mislabelled the upload. | Choose by content, not label. Mention it to the user. |
| Only a machine translation is in the user's language | Machine translations are never listed as source tracks. | Fine as a reading aid (`--also-translation`), never as a faithful source. Say so. |

## Phase 2 — fact-check (on request)

When the user wants the video's claims verified, apply the prompt in [docs/Fact_check_prompt.md](docs/Fact_check_prompt.md) (read it on demand) to the Phase-1 transcript, and write a companion file next to the transcript, in the same `--out-dir`: `<channel> - <title> [<id>].fact-check.md` (the transcript's base name with a `.fact-check.md` suffix).

For the shape of the finished artifact (method note, verdict-at-a-glance table, corrections with primary sources), see the worked example in [docs/example/](docs/example/).

## Full reference

- [docs/AGENTS.md](docs/AGENTS.md) — the complete operating guide: report fields, recommendation rules, every flag, individual stages, troubleshooting.
- [docs/Setup.md](docs/Setup.md) — one-time install of the core toolchain (venv, yt-dlp, deno); the PO-token server and cookies are optional escalation.
- [docs/Fact_check_prompt.md](docs/Fact_check_prompt.md) — the Phase-2 fact-check prompt (deliberately terse).
- [docs/example/](docs/example/) — a finished transcript + its fact-check, as a reference for the output.

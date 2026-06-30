# YT-Transcript-Extractor — agent guide

Pull a clean transcript from a YouTube video. **One command does everything** —
list tracks, decide which to use, download, clean.

## TL;DR

Run from the project root with the project venv python, and tell it **where outputs
go** via `--out-dir` (the user's workspace — never this skill folder):

```bash
PY=".venv/Scripts/python.exe"
"$PY" -m ytx --out-dir "/path/to/WORKSPACE/YT-Transcripts" "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Output contract:** a single machine-readable **JSON object on stdout** telling you
where the finished files are (`out_dir` + each transcript's absolute `path`); all
human progress goes to **stderr**. The clean transcript lands at the `--out-dir`
root, named `<channel> - <title> [<id>].<lang>.md` (yt-dlp-sanitized for Windows,
≤200 chars), with a metadata header + the de-duplicated transcript.

## Where output goes — `--out-dir` (always pass it)

Everything is written under the `--out-dir` base, which belongs in the user's
current workspace, never this skill folder:

```
<out-dir>/                                   e.g.  <workspace>/YT-Transcripts/
  <channel> - <title> [<id>].<lang>.md           the clean transcript (deliverable)
  <channel> - <title> [<id>].fact-check.md       the phase-2 companion (if produced)
  raw/   <id>.<lang>.<kind>.<fmt>                 download-once captions (kept pristine)
  meta/  <id>.info.json · <id>.subs.json         the listing cache
```

Omitting `--out-dir` falls back to `$YTX_OUT`, then `<cwd>/YT-Transcripts` — so pass
it explicitly to be sure. The default folder name is `YT-Transcripts`. **Every stage
must share the same `--out-dir`** so they find each other's cached files.

## File naming

| File | Pattern | Example |
|---|---|---|
| Clean transcript (deliverable) | `<channel> - <title> [<id>].<lang>.md` | `Barry's Economics - … [ApSH0fCIjTY].en-orig.md` |
| Fact-check companion | `<channel> - <title> [<id>].fact-check.md` | `… [ApSH0fCIjTY].fact-check.md` |
| Raw caption (download-once) | `<id>.<lang>.<kind>.<fmt>` | `ApSH0fCIjTY.en-orig.auto.json3` |
| Listing metadata | `<id>.info.json` · `<id>.subs.json` | `ApSH0fCIjTY.subs.json` |
| Standalone clean (debug only) | `<id>.<lang>.<kind>.<fmt>.txt` | `ApSH0fCIjTY.en-orig.auto.json3.txt` |

`kind` ∈ {`manual`, `auto`}; `fmt` ∈ {`json3`, `vtt`, `srv3`, `ttml`, `srt`}; `lang`
may carry the `-orig` ASR marker. The standalone-clean name (last row) deliberately
differs from the deliverable — it's a debug artifact of running `ytx.clean` alone.

## Inspect first, then choose (optional)

To see what's on offer before downloading, list first — it prints clean JSON
(id, title, channel, `original_lang`, `formats_available`, manual/auto langs):

```bash
"$PY" -m ytx.list_subs --out-dir DIR "<url>"   # 1 network hit; caches <out-dir>/meta/<id>.info.json
```

Then `"$PY" -m ytx <url>` (or `ytx.extract`) **reuses that cache** — no second
extraction. The expensive (bot-walled) listing happens once; downloading more
formats/langs afterwards is just cheap caption GETs, and already-downloaded files
are skipped. Pick langs/formats with `--prefer`, `--also-translation`, or run the
stages directly (below).

## ⛔ HARD RULE — ask before any YouTube contact

yt-dlp hitting YouTube gets rate-limited / bot-walled fast. **BEFORE** running
anything that contacts YouTube — `ytx`, `ytx.extract`, `ytx.list_subs`,
`ytx.download_subs` — you MUST ask the user via **AskUserQuestion** and get a yes.
Local-only stages (`ytx.clean`, `ytx.config`) need no permission.

Keep `<out-dir>/raw/` pristine (download once); the clean `.md` is derived
non-destructively into the `--out-dir` root.

## What the one command decides for you

1. **manual subtitles > auto-captions** (human > ASR)
   - **Skip live chat** unless user explicitly requests it (live chat replay is rarely useful for transcripts)
2. **original language > translations** (`-orig` marker, else detected language)
3. **json3 format** (cleanest; falls back to srv3/vtt/ttml/srt)
   - json3 is clean at the source. vtt is YouTube's *rolling* auto-caption format — each cue repeats the tail of the one before it. The cleaner salvages vtt anyway (strip inline `<...>` tags → drop lines identical to the previous emitted line → `html.unescape`), recovering text identical to json3 — but json3 sidesteps the whole mess, so it wins by default. (`download_subs` keeps both as `DEFAULT_FORMATS` so the two can be compared.)

Overrides: `--prefer de,en` · `--also-translation` (adds a preferred-lang
translation) · `--cookies FILE` · `--verbose`.

To force a fresh listing, delete the cache file: `rm "<out-dir>/meta/<id>.info.json"` then re-run.

**Transcript layout** — `--flow` (default `sentences`). Auto-captions have no
chapters or usable pauses, so reflow uses the ASR's sentence punctuation:
`sentences` (one per line) · `paragraphs` (~4 sentences) · `wrapped` (continuous,
~88 cols) · `oneline` · `lines` (raw caption breaks).

## Cookies (required on this network)

YouTube returns `LOGIN_REQUIRED` for anonymous requests here, and a PO token
can't fix it (it gates media, not playability). So cookies are needed.
Default file `cookies/cookies.txt` is auto-used if present (gitignored — never committed).

If it's expired (LOGIN_REQUIRED returns): log a **throwaway/alt** account into
YouTube in a Firefox **private** window, export with a "Get cookies.txt LOCALLY"
extension, overwrite that file, then close the window **without logging out**.
Use **Firefox, not Chrome** (App-Bound Encryption breaks Chrome cookie reads on Windows).

## Setup — see [Setup.md](Setup.md) for a fresh clone; skip if already done

- yt-dlp + `bgutil-ytdlp-pot-provider` in the project `.venv`
- deno at `~/.deno/bin` (JS runtime); bgutil provider built at `tools/bgutil-provider/server`
- `"$PY" -m ytx.config` → no-network health check (run this to confirm it's wired up)

## Individual stages (only if you need one alone)

All stages take `--out-dir DIR` and **must share the same one** so they find each other's cached files.

| Command | Stage | Network? |
|---|---|---|
| `"$PY" -m ytx.list_subs --out-dir DIR <url>` | 1: list tracks → `<out-dir>/meta/` | ✅ |
| `"$PY" -m ytx.download_subs --out-dir DIR <id> --langs en-orig --formats json3` | 2: download → `<out-dir>/raw/` | ✅ |
| `"$PY" -m ytx.clean --out-dir DIR <id>` | 3+4: clean + compare → `<out-dir>/` | ❌ |

**Note on `ytx.clean` output:** When run standalone, it produces a raw `<id>.<lang>.<kind>.<fmt>.txt` file in the `--out-dir` root — no metadata header, no proper channel/title filename. To get the properly named `<channel> - <title> [<id>].<lang>.md` output, run `"$PY" -m ytx --out-dir DIR <url>` after stages 1+2 — it reuses the cache and any already-downloaded raw files.

## If web/mweb/tv clients miss auto-captions

The default player clients (`web`, `mweb`, `tv`) sometimes fail to discover auto-generated captions (the listing shows only `live_chat` or nothing in `auto`). If you can see captions in the YouTube UI but `list_subs` reports none, re-list with default yt-dlp clients and explicit cookies:

```bash
rm "<out-dir>/meta/<id>.info.json"
"$PY" -m ytx.list_subs --out-dir DIR --client default --cookies "cookies/cookies.txt" "<url>"
```

The cache will then have the correct track list for subsequent stages.

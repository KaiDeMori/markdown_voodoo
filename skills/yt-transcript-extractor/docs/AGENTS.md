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

## Cookies — opt-in escalation (off by default)

Most videos need no cookies. They are the fix for the *walled* case only:
`LOGIN_REQUIRED` / "Sign in to confirm you're not a bot" / age-restricted. A PO
token can't help there (it gates formats, not playability) — only cookies lift
that wall.

Cookies are **off by default** and never used silently: a cookie YouTube
dislikes can get the underlying account throttled or temporarily banned. Turn
them on only when a run is actually walled, and only with the user's OK:

- **One run:** add `--use-cookies` (or `--cookies FILE` for an explicit path).
- **Always on:** copy `settings.local.json.example` → `settings.local.json` and
  set `"use_cookies": true` (gitignored).

Either way `cookies/cookies.txt` is used when present. To (re-)create it: log a
**throwaway/alt** account into YouTube in a Firefox **private** window, export
with a "Get cookies.txt **LOCALLY**" extension, save as `cookies/cookies.txt`,
then close the window **without logging out**. Use **Firefox, not Chrome**
(App-Bound Encryption breaks Chrome cookie reads on Windows), and never combine
`--cookies` with `--cookies-from-browser`. The file is gitignored — never commit it.

## Setup — see [Setup.md](Setup.md) for a fresh clone; skip if already done

- **Core (all most videos need):** yt-dlp + `bgutil-ytdlp-pot-provider` plugin
  in the project `.venv`; deno at `~/.deno/bin` (JS runtime).
- **Optional escalation:** the bgutil provider *server* built at
  `tools/bgutil-provider/server` (token-gated formats); cookies (off by default).
- `"$PY" -m ytx.config` → no-network health check, split into `core` and
  `optional_escalation` (a missing optional piece is fine until you need it).

## Individual stages (only if you need one alone)

All stages take `--out-dir DIR` and **must share the same one** so they find each other's cached files. They also accept the escalation flags `--client web,mweb,tv` and `--use-cookies` (see the ladder above); keep the client consistent across stages 1 and 2.

| Command | Stage | Network? |
|---|---|---|
| `"$PY" -m ytx.list_subs --out-dir DIR <url>` | 1: list tracks → `<out-dir>/meta/` | ✅ |
| `"$PY" -m ytx.download_subs --out-dir DIR <id> --langs en-orig --formats json3` | 2: download → `<out-dir>/raw/` | ✅ |
| `"$PY" -m ytx.clean --out-dir DIR <id>` | 3+4: clean + compare → `<out-dir>/` | ❌ |

**Note on `ytx.clean` output:** When run standalone, it produces a raw `<id>.<lang>.<kind>.<fmt>.txt` file in the `--out-dir` root — no metadata header, no proper channel/title filename. To get the properly named `<channel> - <title> [<id>].<lang>.md` output, run `"$PY" -m ytx --out-dir DIR <url>` after stages 1+2 — it reuses the cache and any already-downloaded raw files.

## When a pull comes back empty — the escalation ladder

The baseline lets yt-dlp choose the client (no forced list — its maintainers pick better than any snapshot could) and uses no cookies. That is right for most videos. When a pull returns nothing, **read stderr first** — the failures look alike but have different fixes:

**A quiet empty result** — the JSON shows `manual.langs: []` and `auto.total_langs: 0`, and stderr carries `Sign in to confirm you're not a bot` / `LOGIN_REQUIRED`. That is the **bot/login wall**, not "no captions exist", and a PO token will NOT fix it. The fix is **cookies** (see the cookies section): with the user's OK, re-run with `--use-cookies`.

**No tracks, but the video is plainly playable and unrestricted** — try a specific **client**. yt-dlp's default is usually best, but in the days right after a YouTube change a particular client can expose tracks the default misses:

```bash
rm "<out-dir>/meta/<id>.info.json"
"$PY" -m ytx.list_subs --out-dir DIR --client web,mweb,tv "<url>"
```

**Which client to try is a moving target — never hardcode it.** If an obvious client doesn't help, check the current per-client situation on the yt-dlp wiki (PO-Token-Guide / Extractors, linked in Setup.md) and pass what it recommends via `--client`.

**A track exists but its format won't download** — that's the token-gated case; build the bgutil server (Setup.md, escalation B), then retry.

**Benign warnings — don't mistake these for failure.** Messages about missing *video formats* (`Requested format is not available`, `Only images are available`, `n challenge solving failed` / the EJS "remote components" hint) are about media, which this tool never fetches. If a subtitle track was still listed, downloaded, and cleaned, the pull succeeded — ignore them.

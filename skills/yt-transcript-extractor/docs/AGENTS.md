# YT-Transcript-Extractor — agent guide

Pull a clean transcript from a YouTube video. YouTube's track labels are unreliable, so the tool gathers evidence and the agent decides: **list → probe → extract**. The step-by-step flow lives in [SKILL.md](../SKILL.md); this guide is the reference.

## TL;DR

Run from the project root with the project venv python, and tell every stage **where outputs go** via the same `--out-dir` (the user's workspace — never this skill folder):

```bash
PY=".venv/Scripts/python.exe"
DIR="/path/to/WORKSPACE/YT-Transcripts"
"$PY" -m ytx.list_subs --out-dir "$DIR" "https://www.youtube.com/watch?v=VIDEO_ID"   # 1 extraction, report
"$PY" -m ytx.probe     --out-dir "$DIR" VIDEO_ID --tracks en-orig.auto               # ≤2 caption GETs, samples
"$PY" -m ytx           --out-dir "$DIR" --track en-orig.auto "https://www.youtube.com/watch?v=VIDEO_ID"   # local
```

**Output contract:** every stage prints a single machine-readable **JSON object on stdout**; all human progress goes to **stderr**. The clean transcript lands at the `--out-dir` root, named `<channel> - <title> [<id>].<lang>.md` (yt-dlp-sanitized for Windows, ≤200 chars), with a metadata header + the de-duplicated transcript.

The one-shot `"$PY" -m ytx --out-dir "$DIR" "<url>"` (no `--track`) runs all three steps and takes the recommended track. It is a shortcut — use it only when the user asks for it.

## Where output goes — `--out-dir` (always pass it)

Everything is written under the `--out-dir` base, which belongs in the user's current workspace, never this skill folder:

```
<out-dir>/                                   e.g.  <workspace>/YT-Transcripts/
  <channel> - <title> [<id>].<lang>.md           the clean transcript (deliverable)
  <channel> - <title> [<id>].fact-check.md       the phase-2 companion (if produced)
  raw/   <id>.<lang>.<kind>.<fmt>                 download-once captions (kept pristine)
  meta/  <id>.info.json · <id>.subs.json         the listing cache + track report
```

Omitting `--out-dir` falls back to `$YTX_OUT`, then `<cwd>/YT-Transcripts` — so pass it explicitly to be sure. The default folder name is `YT-Transcripts`. **Every stage must share the same `--out-dir`** so they find each other's cached files.

## File naming and track ids

| File | Pattern | Example |
|---|---|---|
| Clean transcript (deliverable) | `<channel> - <title> [<id>].<lang>.md` | `Barry's Economics - … [ApSH0fCIjTY].en-orig.md` |
| Fact-check companion | `<channel> - <title> [<id>].fact-check.md` | `… [ApSH0fCIjTY].fact-check.md` |
| Raw caption (download-once) | `<id>.<lang>.<kind>.<fmt>` | `ApSH0fCIjTY.en-orig.auto.json3` |
| Listing metadata | `<id>.info.json` · `<id>.subs.json` | `ApSH0fCIjTY.subs.json` |
| Standalone clean (debug only) | `<id>.<lang>.<kind>.<fmt>.txt` | `ApSH0fCIjTY.en-orig.auto.json3.txt` |

`kind` ∈ {`manual`, `auto`}; `fmt` ∈ {`json3`, `vtt`, `srv3`, `ttml`, `srt`}; `lang` may carry the `-orig` ASR marker. The standalone-clean name (last row) deliberately differs from the deliverable — it's a debug artifact of running `ytx.clean` alone.

A **track id** is `<lang>.<kind>` — the middle part of the raw file name, e.g. `en-orig.auto` or `en.manual`. `--track` and `--tracks` take track ids.

## ⛔ HARD RULE — ask before any YouTube contact

yt-dlp hitting YouTube gets rate-limited / bot-walled fast, and every request counts. **BEFORE** running anything that contacts YouTube — `ytx.list_subs`, `ytx.probe`, `ytx`, `ytx.extract`, `ytx.download_subs` — ask the user **in chat** (not via `AskUserQuestion`) and get a yes. One question covers the listing, the first probe call and the output destination; every further probe call needs a new OK. Local-only stages (`ytx.clean`, `ytx.config`) and the `ytx --track` run after a probe need no permission.

Keep `<out-dir>/raw/` pristine (download once); the clean `.md` is derived non-destructively into the `--out-dir` root.

## The list report

`ytx.list_subs` prints the report and caches it as `<out-dir>/meta/<id>.subs.json`; the full yt-dlp info lands in `<out-dir>/meta/<id>.info.json`. `ytx.list_subs` always fetches fresh; `ytx` and `ytx.extract` reuse the cached info unless `--refresh` is given.

| Field | Meaning |
|---|---|
| `id`, `title`, `channel`, `duration_s` | The video. |
| `description_head` | The first 300 characters of the description. |
| `original_audio_lang` | Language of the audio track YouTube flags as original. Only on multi-audio (e.g. auto-dubbed) videos whose formats were extracted; otherwise `null`. |
| `source_tracks` | Every track YouTube produced directly: manual uploads, then ASR tracks, in YouTube's order. Each has `track`, `kind`, `lang`, `name` and `source_lang`. |
| `machine_translations` | How many languages exist only as machine translations. They are never listed. |
| `recommended` | `track`, `reason`, `ambiguous` — the pick of the recommendation rules below. |

`source_lang` is the `lang` parameter of the track's own URL. For an ASR track it is the language the ASR ran in; for a manual track it is the uploader's declaration. A machine translation additionally carries `tlang` (reported as `translated_to`). yt-dlp names every ASR track "(Original)" and tags it `-orig` — on an auto-dubbed video that includes the dubs.

## The probe

`ytx.probe` downloads at most 2 tracks of one video per call from the cached listing into `raw/` and prints, per track: `track`, `format`, `path`, `lines`, `words`, `words_per_minute`, `sample_start` (the first 5 caption lines) and `sample_middle` (5 lines from the middle). Tracks already in `raw/` cost no request. The cached caption URLs expire after some hours; an expired URL stops the run before any request, with the hint to refresh the listing.

## The recommendation rules

`list_subs.recommend_track` feeds both the report's `recommended` field and the one-shot. Best first:

1. **The spoken language** comes from `--prefer` (explicit), else `original_audio_lang`, else the only ASR track. With several ASR tracks and no other evidence it takes the first in YouTube's order and marks the pick `ambiguous`.
2. **manual subtitles > auto-captions** (human > ASR). Among manual tracks: the spoken language, else a reading language (`config.DEFAULT_READING_LANGS`), else the first — the latter two marked `ambiguous`. Languages match on their base (`en-GB` and `en-orig` count as `en`).
3. **json3 format** (cleanest; falls back to srv3/vtt/ttml/srt). json3 is clean at the source. vtt is YouTube's *rolling* auto-caption format — each cue repeats the tail of the one before it. The cleaner salvages vtt anyway (strip inline `<...>` tags → drop lines identical to the previous emitted line → `html.unescape`), recovering text identical to json3 — but json3 sidesteps the whole mess, so it wins by default. (`download_subs` keeps both as `DEFAULT_FORMATS` so the two can be compared.)
4. **Live chat is never a source track.** yt-dlp files the chat replay of a past livestream as `live_chat` under the manual subtitles; it is skipped. Fetch it only on the user's explicit request (`--track live_chat.manual`).

## Flags of `ytx` / `ytx.extract`

- `--track <lang>.<kind>` — the primary track, skipping the recommendation. Wins over `--prefer`. The header records `Selection: explicit · recommended=<track> · match=yes|no`.
- `--prefer en,de` — the language(s) the video is spoken in, overriding the detection in rule 1.
- `--also-translation` — adds a translation into the first reading language (`config.DEFAULT_READING_LANGS`) that differs from the primary.
- `--refresh` — ignore the cached listing and fetch a fresh one.
- `--flow` — transcript layout (default `sentences`). Auto-captions have no chapters or usable pauses, so reflow uses the ASR's sentence punctuation: `sentences` (one per line) · `paragraphs` (~4 sentences) · `wrapped` (continuous, ~88 cols) · `oneline` · `lines` (raw caption breaks).
- `--cookies FILE` · `--use-cookies` · `--client` — escalation, see below.
- `--verbose` — yt-dlp's own diagnostics on stderr.

## Cookies — opt-in escalation (off by default)

Most videos need no cookies. They are the fix for the *walled* case only: `LOGIN_REQUIRED` / "Sign in to confirm you're not a bot" / age-restricted. A PO token can't help there (it gates formats, not playability) — only cookies lift that wall.

Cookies are **off by default** and never used silently: a cookie YouTube dislikes can get the underlying account throttled or temporarily banned. Turn them on only when a run is actually walled, and only with the user's OK:

- **One run:** add `--use-cookies` (or `--cookies FILE` for an explicit path).
- **Always on:** copy `settings.local.json.example` → `settings.local.json` and set `"use_cookies": true` (gitignored).

Either way `cookies/cookies.txt` is used when present. To (re-)create it: log a **throwaway/alt** account into YouTube in a Firefox **private** window, export with a "Get cookies.txt **LOCALLY**" extension, save as `cookies/cookies.txt`, then close the window **without logging out**. Use **Firefox, not Chrome** (App-Bound Encryption breaks Chrome cookie reads on Windows), and never combine `--cookies` with `--cookies-from-browser`. The file is gitignored — never commit it.

## Setup — see [Setup.md](Setup.md) for a fresh clone; skip if already done

- **Core (all most videos need):** yt-dlp + `bgutil-ytdlp-pot-provider` plugin in the project `.venv`; deno at `~/.deno/bin` (JS runtime).
- **Optional escalation:** the bgutil provider *server* built at `tools/bgutil-provider/server` (token-gated formats); cookies (off by default).
- `"$PY" -m ytx.config` → no-network health check, split into `core` and `optional_escalation` (a missing optional piece is fine until you need it).

## Individual stages

All stages take `--out-dir DIR` and **must share the same one** so they find each other's cached files. The network stages also accept the escalation flags `--client web,mweb,tv` and `--use-cookies` (see the ladder below); keep the client consistent across stages.

| Command | Stage | Network? |
|---|---|---|
| `"$PY" -m ytx.list_subs --out-dir DIR <url>` | 1: list tracks → report + `<out-dir>/meta/` | ✅ |
| `"$PY" -m ytx.probe --out-dir DIR <id> --tracks en-orig.auto[,en.manual]` | 2b: download ≤2 tracks → `<out-dir>/raw/` + samples | ✅ (per track not yet in `raw/`) |
| `"$PY" -m ytx.download_subs --out-dir DIR <id> --langs en-orig --formats json3` | 2: download lang × format → `<out-dir>/raw/` | ✅ |
| `"$PY" -m ytx.clean --out-dir DIR <id>` | 3+4: clean + compare → `<out-dir>/` | ❌ |
| `"$PY" -m ytx --out-dir DIR --track <track> <url>` | 1–3 with cache reuse → the clean `.md` | only for what isn't cached |

**Note on `ytx.clean` output:** When run standalone, it produces a raw `<id>.<lang>.<kind>.<fmt>.txt` file in the `--out-dir` root — no metadata header, no proper channel/title filename. To get the properly named `<channel> - <title> [<id>].<lang>.md` output, run `"$PY" -m ytx --out-dir DIR --track <track> <url>` after stages 1+2 — it reuses the cache and any already-downloaded raw files.

## When a pull comes back empty — the escalation ladder

The baseline lets yt-dlp choose the client (no forced list — its maintainers pick better than any snapshot could) and uses no cookies. That is right for most videos. When a pull returns nothing, **read stderr first** — the failures look alike but have different fixes:

**A quiet empty result** — the report shows `source_tracks: []` and `machine_translations: 0`, and stderr carries `Sign in to confirm you're not a bot` / `LOGIN_REQUIRED`. That is the **bot/login wall**, not "no captions exist", and a PO token will NOT fix it. The fix is **cookies** (see the cookies section): with the user's OK, re-run with `--use-cookies`.

**No tracks, but the video is plainly playable and unrestricted** — try a specific **client**. yt-dlp's default is usually best, but in the days right after a YouTube change a particular client can expose tracks the default misses:

```bash
"$PY" -m ytx.list_subs --out-dir DIR --client web,mweb,tv "<url>"
```

**Which client to try is a moving target — never hardcode it.** If an obvious client doesn't help, check the current per-client situation on the yt-dlp wiki (PO-Token-Guide / Extractors, linked in Setup.md) and pass what it recommends via `--client`.

**A track exists but its format won't download** — that's the token-gated case; build the bgutil server (Setup.md, escalation B), then retry.

**Benign warnings — don't mistake these for failure.** Messages about missing *video formats* (`Requested format is not available`, `Only images are available`, `n challenge solving failed` / the EJS "remote components" hint) are about media, which this tool never fetches. If a subtitle track was still listed, downloaded, and cleaned, the pull succeeded — ignore them.

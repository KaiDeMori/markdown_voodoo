# Setup

One-time install of the parts that aren't committed. Run everything from this folder:

```
~/markdown_voodoo/skills/yt-transcript-extractor/
```

**The short version:** on a machine that normally browses YouTube, pulling a transcript usually needs nothing beyond the *core install* below — no PO token, no cookies. yt-dlp already picks clients that avoid a Proof-of-Origin token, and captions are public. What actually gets you blocked is **request rate and IP reputation** (downloading too fast or too parallel, or from a datacenter/VPN address), not a missing token. So set up the core, and only reach for the escalation steps when a *specific* video is walled.

YouTube and yt-dlp change constantly, so nothing version-specific is pinned here — the concrete, always-current details live upstream (links at the bottom). Follow those rather than trusting a snapshot. When you're done, `python -m ytx.config` is a no-network health check that reports exactly which piece is present.

This folder holds only code and toolchain — **transcripts are written to your own workspace** via `--out-dir` (default `<workspace>/YT-Transcripts`), never here. So `ytx.config` reporting `output_base … false` is expected: that directory is created per run in the workspace you point it at. See [AGENTS.md](AGENTS.md) for running the tool.

## Prerequisites

- **Python 3.10+** and **git** on PATH.
- **Node.js** and/or **deno** — a JavaScript runtime. yt-dlp increasingly needs one even for default clients, so treat it as core.

## Core install (this is usually all you need)

### 1. Python venv + dependencies

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# .venv/bin/python   -m pip install -r requirements.txt   # macOS/Linux
```

This installs `yt-dlp` and the `bgutil-ytdlp-pot-provider` plugin. **Keep `yt-dlp` current** — it breaks against YouTube often and updates are the fix; updating first resolves most problems.

### 2. deno (JS runtime)

Install deno user-scoped so it lands at `~/.deno/bin` (where `ytx.config` looks):

- Windows (PowerShell): `irm https://deno.land/install.ps1 | iex`
- macOS/Linux: `curl -fsSL https://deno.land/install.sh | sh`
- Reference: <https://deno.land/>

### 3. Verify

```bash
.venv/Scripts/python -m ytx.config
```

A network-free report split into **core** (needed always) and **optional_escalation** (only when a video is walled). Green on `core` means you're ready for ordinary videos; then see [AGENTS.md](AGENTS.md).

## Staying unblocked (before reaching for escalation)

Most "it stopped working" cases are environment, not missing credentials:

- **Keep yt-dlp current** (`pip install -U yt-dlp`) — YouTube changes and yt-dlp catches up within days.
- **Run from a residential connection** — datacenter/VPN addresses get flagged fast.
- **Don't hammer it** — the tool already throttles between requests; avoid running many pulls in parallel. Excessive rate can get the whole IP temporarily blocked.

## Escalation — only when a specific video is walled

Escalate in order, cheapest first. Each rung fixes a *different* failure, and none of this is needed for ordinary videos.

### A. Try a different client (video plays, but the tool finds no tracks)

The baseline lets yt-dlp choose the client, which is almost always right. If a video plays fine in a browser but the tool reports no subtitle tracks, a specific client may expose them:

```bash
.venv/Scripts/python -m ytx --client web,mweb,tv --refresh "<url>"
```

**Which client works is a moving target** — don't trust any fixed list (including this example). When the default and an obvious client both fail, check the current per-client situation on the yt-dlp wiki (links below) and pass the recommended one via `--client`.

### B. PO-token server (token-gated formats/subtitles)

Some clients need a Proof-of-Origin token before YouTube hands over certain formats or subtitle tracks. The `bgutil-ytdlp-pot-provider` plugin (installed in step 1) mints one — but in "script mode" it needs its server built locally:

```bash
git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git tools/bgutil-provider
cd tools/bgutil-provider/server
npm install
npx tsc
cd ../../..
```

Match the server version to the installed plugin, and prefer the server/HTTP or Docker mode for heavier use — the upstream README is the source of truth: <https://github.com/Brainicism/bgutil-ytdlp-pot-provider>. Once built, `ytx.config` shows `bgutil_server_build … true`, and the tool advertises it automatically to any client that needs a token.

**A PO token does not lift a "Sign in to confirm you're not a bot" / `LOGIN_REQUIRED` wall** — that's playability, not formats. For that, use cookies (next).

### C. Cookies — for LOGIN_REQUIRED / "not a bot" / age-restricted

When YouTube walls a video for anonymous access (the listing comes back empty with a *"Sign in to confirm you're not a bot"* warning) or the video is age-restricted, cookies from a logged-in session are the fix. **Cookies are off by default and must be opted into**, because a cookie YouTube decides it dislikes can get the underlying account throttled or temporarily banned.

Enable them one of two ways:

- **Per run:** add `--use-cookies` (or point at a specific file with `--cookies path/to/cookies.txt`).
- **Persistently:** copy `settings.local.json.example` to `settings.local.json` and set `"use_cookies": true`. It's gitignored; flipping that boolean is the whole configuration.

Either way, `cookies/cookies.txt` is used when present. To create it:

```bash
cp cookies/cookies.txt.example cookies/cookies.txt   # then replace with a real export
```

Export it the way yt-dlp recommends (links below). The version that survives YouTube's churn best: use a **throwaway/alt** account, log into YouTube in a **Firefox private** window, export with a "Get cookies.txt **LOCALLY**" extension, save as `cookies/cookies.txt`, then close the window **without logging out**. Use Firefox, not Chrome (App-Bound Encryption breaks Chrome cookie reads on Windows), and never combine `--cookies` with `--cookies-from-browser`.

`cookies/cookies.txt` is gitignored — it is a live credential for that account and must never be committed.

## The single source of truth (this all changes often)

Everything version-specific — which client works today, exactly when a PO token is required, how to export cookies safely — lives here and is kept current by the yt-dlp maintainers:

- **PO tokens & per-client requirements:** <https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide>
- **When cookies are needed + safe export:** <https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies>
- **Passing cookies / rate-limit (429·403) tips:** <https://github.com/yt-dlp/yt-dlp/wiki/FAQ>
- **The PO-token provider:** <https://github.com/Brainicism/bgutil-ytdlp-pot-provider>

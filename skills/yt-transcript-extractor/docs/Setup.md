# Setup

One-time install of the parts that aren't committed (the venv, the JS runtime, the PO-token server, and your cookies). Run everything from the project root:

```
~/markdown_voodoo/skills/yt-transcript-extractor/
```

YouTube and yt-dlp change constantly, so the version-specific details below live with their upstreams — follow those links rather than trusting a snapshot here. When you're done, `python -m ytx.config` is a no-network health check that tells you exactly which piece is still missing.

This folder holds only the code and toolchain — **transcripts are written to your own workspace** via `--out-dir` (default `<workspace>/YT-Transcripts`), never here. So `ytx.config` reporting `output_base … false` is expected: that directory is created per run in the workspace you point it at. See [AGENTS.md](AGENTS.md) for running the tool.

## Prerequisites

- **Python 3.10+** and **git** on PATH.
- **Node.js** (with `npm`/`npx`) — needed to build the PO-token server.

## 1. Python venv + dependencies

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# .venv/bin/python   -m pip install -r requirements.txt   # macOS/Linux
```

This installs `yt-dlp` and the `bgutil-ytdlp-pot-provider` plugin. Keep `yt-dlp` current — it breaks against YouTube often and updates fix it.

## 2. deno (JS runtime for the PO token)

Install deno user-scoped so it lands at `~/.deno/bin` (where `ytx.config` looks):

- Windows (PowerShell): `irm https://deno.land/install.ps1 | iex`
- macOS/Linux: `curl -fsSL https://deno.land/install.sh | sh`
- Reference: <https://deno.land/>

## 3. bgutil PO-token provider (built locally, "script mode")

Modern YouTube refuses anonymous requests; the cookie-free half of the fix is a Proof-of-Origin token minted by this server. Clone it into `tools/` and build it:

```bash
git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git tools/bgutil-provider
cd tools/bgutil-provider/server
npm install
npx tsc
cd ../../..
```

Check out a **server version that matches the `bgutil-ytdlp-pot-provider` plugin** installed in step 1 (the two are released in lockstep) — see the upstream README: <https://github.com/Brainicism/bgutil-ytdlp-pot-provider>. A successful build leaves `tools/bgutil-provider/server/build/generate_once.js`, which `ytx.config` verifies.

## 4. Cookies (usually required)

PO tokens gate media, not playability — so on many networks YouTube still returns `LOGIN_REQUIRED` and you also need cookies from a logged-in session:

```bash
cp cookies/cookies.txt.example cookies/cookies.txt
```

Then replace `cookies/cookies.txt` with a real export. How to export is documented on the yt-dlp pages (search: *yt-dlp how do I pass cookies*). The short version, which survives YouTube's churn best: log a **throwaway/alt** account into YouTube in a **Firefox private** window, export with a "Get cookies.txt LOCALLY" extension, save it as `cookies/cookies.txt`, then close the window **without logging out**. Use Firefox, not Chrome (App-Bound Encryption breaks Chrome cookie reads on Windows).

`cookies/cookies.txt` is gitignored — it is a live credential for that account and must never be committed.

## 5. Verify

```bash
.venv/Scripts/python -m ytx.config
```

A network-free report of every piece (deno, node, the bgutil build, the data dirs). Green across the board means you're ready; then see [AGENTS.md](AGENTS.md) for operating the tool.

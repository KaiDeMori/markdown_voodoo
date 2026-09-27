# Relay fetch

The relay fetch keeps the machine that runs `ytx` off YouTube entirely. Your own machine fetches with `ytx_relay.bat` and packs a **bundle** (`<id>.ytx.zip`); you hand the bundle over, and `ytx` works offline from it.

Use it when the `ytx` machine's IP cannot be changed: there, a YouTube block would be permanent.

## Install

1. Copy [`relay/ytx_relay.bat`](../relay/ytx_relay.bat) into the folder that holds your `yt-dlp.exe`.
2. Make sure 7-Zip is on PATH (`7z` must run in a console).

Nothing else changes: your `yt-dlp.conf` keeps applying (JS runtime such as deno, cookies, …). The script only overrides the settings that would cause extra YouTube contact or break the bundle.

The file uses Windows line endings (CRLF). Copy it as a file; git keeps its line endings byte-exact.

## Round 1 — `ytx_relay.bat "URL"`

```bat
ytx_relay.bat "https://www.youtube.com/watch?v=VIDEO_ID"
```

Always quote the URL: an unquoted `&` cuts it off.

1. **Listing** — the one heavy request to YouTube.
2. **Counting** — without downloading, the script lets yt-dlp select the source tracks: the ASR `-orig` tracks, plus the manual tracks in English, German and each ASR language.
3. **Fetching** — at most 8 tracks, 2 seconds apart. With more than 8, the bundle holds the listing only, and Claude names the tracks for round 2.
4. **Bundle** — `ytx_relay\<id>.ytx.zip` next to the script. Explorer opens with the bundle selected; hand it over to Claude.

## Round 2 — `ytx_relay.bat VIDEO_ID TRACK [TRACK ...]`

Only when Claude asks for it, with the exact line Claude gives, e.g.:

```bat
ytx_relay.bat VIDEO_ID fr-orig.auto en.manual
```

- Fetches exactly the named tracks, at most 8, from the round-1 listing — no new heavy request.
- The listing's caption URLs expire after some hours. If round 2 fails for that reason, run round 1 again.
- The new bundle contains everything fetched so far; hand it over like the first one.

## What the script protects against

- **Silent re-extraction.** yt-dlp re-extracts the whole video when a download from a saved listing fails. `--ignore-errors` turns that failure into a warning instead.
- **Extra YouTube contact from your config.** Comments, mark-watched, waiting for premieres, live-from-start and the download archive are switched off for these runs.
- **Broken bundles.** Subtitle conversion and embedding are switched off, and the output templates and the home/temp paths are set explicitly, so the captions land where the bundle expects them. One gap: a per-type path in your config (`-P "subtitle:…"`) still applies — then the bundle misses the captions, and the script's file list shows it.
- **Rate.** 2 seconds between requests; at most 8 caption downloads per round.

## Where files land

```
<yt-dlp folder>\ytx_relay\<id>\          work folder: listing + captions (round 2 needs it)
<yt-dlp folder>\ytx_relay\<id>.ytx.zip   the bundle
```

Both can be deleted any time after Claude has imported the bundle.

## Troubleshooting

| Message | Meaning |
|---|---|
| `No listing was written` | The listing failed; yt-dlp's message above says why. Update yt-dlp first; a bot wall needs cookies in your config. |
| `yt-dlp.exe not found next to this script` | The script sits in the wrong folder. |
| `7-Zip is not on PATH` | Install 7-Zip or add its folder to PATH. |
| `No listing for … - run round 1 first` | Round 2 needs the work folder from round 1. |
| `Invalid track id` | Track ids look like `en.manual` or `fr-orig.auto` — copy them from Claude's line. |
| `Refusing video id` | The video id may only hold letters, digits, `_` and `-`. It becomes part of folder names the script deletes, so anything else stops the script before it touches a file. |

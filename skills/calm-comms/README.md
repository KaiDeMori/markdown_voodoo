# calm-comms: the builders' doc

calm-comms in Go, Rabenschnack 2.0, and the why behind the code.
The users' doc is [SKILL.md](SKILL.md).

The Go version keeps the bash version's verbs, mail format and markers; what it changes on purpose is listed below.
calm-comms is for ravens: every line it prints is for a raven to read.
It runs in the live `C:/haven`; a test names a haven of its own in `calm_comms_haven_location`.
`calm_comms.sh` runs `calm_comms.exe` beside it, with Git Bash's path conversion off, so every caller of `calm_comms.sh` keeps working.

## How the watcher waits

`on` waits for whichever comes first: new mail, the timer, or a stop request.
In Go that is one `select`, in `watch_seat`.

- fsnotify brings the notifications: ReadDirectoryChangesW on Windows, inotify on Linux, kqueue on macOS.
- A notification is only a hint to look now, never the mail itself.
  The hint and the 10-second poll run the same rescan of the seat, against the files known at the start.
  A lost notification costs at most 10 seconds, a duplicate costs nothing, and hints never pile up.
- The poll stays as a safety net, because notifications get lost when their buffer overflows.
  So the worst case is the bash version's behavior; if fsnotify can't start at all, the poll alone carries on.
- A new file counts as mail once it still exists a second later: a writer's temp file is gone by then.
- After a wake, the watcher leaves `watching.md` saying `awake` for the grace minutes.

### Who is watching: the lock

- A watcher holds an exclusive lock on its seat's `watching.md` for its whole life.
- The system releases a lock when its holder ends, even in a crash or a hard kill, so no lock outlives its watcher.
- `overview` asks the lock, not a process ID: a moment's shared lock fails only while a watcher lives.
- A hard kill skips the cleanup: `watching.md` keeps its `until` line, but without the lock, `overview` shows the door closed.
- On Windows a lock binds every process, so it sits on one byte at 1 GiB, far beyond the file's end, as SQLite's locks do.
  Reading and writing `watching.md` never meet it.
- On Linux and macOS it is `flock` on the whole file, which binds only those who ask.

### Stopping: a request, not a kill

- `off` and a newer `on` empty `watching.md`.
- The watcher hears of it through fsnotify at once, or at its next look at the latest, and leaves with `stopped` and 143.
- Meanwhile the caller waits for the lock, up to 15 seconds, then refuses with 1.
- The `pid` line in `watching.md` only says whose marker it is: nobody kills by it, and nobody trusts it for liveness.
- Ctrl+C and SIGTERM end a watcher the same way, with `stopped` and 143.

## Bash and Go

### Kept as is

- The verbs, their arguments and every output line, word for word, except the changes below.
- The mail: its header lines, and never overwriting one.
- `watching.md`: `until` with `pid`, and `awake` after a wake.
- The layout: a `README.md` makes a seat, read mail moves into `already_read/`, and a group's `members/` holds one empty file per member.
- The settings and their values, at the top of `calm_comms.go`; only the jitter's are gone.
- The exit codes: 0 done, 1 refused, 143 stopped, and 5040 for a missing seat.

### Changed on purpose

- Waiting: fsnotify, with the poll as a safety net; bash only polled.
- No wake jitter: a watcher wakes its raven as soon as a mail has settled; bash waited a random 1 to 5 seconds more.
- `overview`: one line per seat, its name and its mailbox, such as `huginn 📭`; bash showed the timer's end, `present`, `awake` or `-`, padded for eyes.
- `send` answers with the target's line, such as `muninn 📬`; bash printed nothing.
- A mail's name starts with its moment, such as `2026-10-16_141523_from_tool_builder.md`, so mail sorted by name is sorted by time; bash put the sender first.
- `overview groups [group_name]`: the groups, and a group's members with their mailboxes; bash had no way to list them.
- Terminal mode is gone, and the bell with it: calm-comms is for ravens, and Wally's terminal brings its own watcher.
- Liveness: the lock; bash trusted a process ID and checked its command line in `/proc`.
- Stopping: a request through `watching.md`; bash sent SIGTERM.
- The timer runs exactly; bash counted it in 10-second steps.
- No MSYS or GNU tools: no `/proc`, `mkfifo`, `kill`, `date -d` or `find -printf`.
- An unknown verb gets a line and 1; bash said nothing and exited 0.
- A mail limit that is no number gets a line and 1; bash read it as 0, a peek.
- If the old watcher doesn't stop within 15 seconds, `on` and `off` refuse with 1; bash printed a line and went on.
- The line `watching.md named process …, which is no watcher of …` is gone: with the lock, that case can't happen.
- The haven: `C:/haven`, as in bash, unless a test names its own in `calm_comms_haven_location`.

### Exit codes

Callers only tell zero from not zero, and the line says why.
2 belongs to Go: the tool itself broke.

| Code | Means |
|---|---|
| 0 | done |
| 1 | refused, or the system refused a file; the line says why |
| 143 | stopped: no mail, nothing to do |
| 5040 | no such seat; bash sees 176 |

## Build, test, deploy

### Build

Go 1.27, with two dependencies in `go.mod`: fsnotify v1.10.1 and golang.org/x/sys v0.49.0.

```bash
cd skills/calm-comms
gofmt -l .
go vet ./...
GOOS=linux go vet ./...
go build -o calm_comms.exe .
```

- `gofmt -l` names every file it would change, so it should name none.
- Only the lock differs by system: `lock_windows.go`, and `lock_unix.go` for Linux and macOS.
- Without `calm_comms_haven_location`, the exe works in the live hall; a manual test sets it to this folder's `test_haven`.
- The exe and `test_haven/` stay out of git, through the `.gitignore` beside this README.

### Test

The tests run against a haven of their own, never against the live hall.
The tool never creates a haven: a seat is a folder in `test_haven/Hall/thing/Hrafnsmal` with a `README.md`, and a group is a folder in `test_haven/Hall/thing/group_chat` with a `members/` folder.
It started with the seats `huginn`, `muninn` and `corvus`, and the group `ravens` with huginn and muninn.

The first smoke run, on 2026-10-26, passed all 10 tests.
The second, on 2026-10-27, after the jitter went, passed all 10 again.
The third, the same night, after terminal mode went and the mailboxes came, passed all 11.
The fourth, after the move into `skills/calm-comms/`, passed all 13, every call through `calm_comms.sh`; the table shows the third, with 12 and 13 from the fourth.
The fifth, after `overview groups` came, passed all 14.
The sixth, after the mail names turned around, passed all 14 again.
Since the second, the runs come from `run_test.sh` beside this README: it builds a haven of its own in the scratchpad, so the live hall and this folder's `test_haven` never see a run.
The watcher tests run `on` in the background, as ravens do.

| Test | What it showed |
|---|---|
| 1 `send` | `huginn 📫`, exit 0, and the mail in the bash format |
| 2 `inbox` | the mail under its `---` line, then moved into `already_read/` |
| 3 `join` | a third seat joined: `… joined ravens: 3 members.` |
| 4 `group` | copies for the other members and the thread, none for the sender |
| 5 `leave` | `… left ravens: 2 members.` |
| 6 `overview` | `corvus 📫`, `huginn 📪` and `muninn 📫`, as clean UTF-8 through the pipe |
| 7 wake | `send` to the watched seat said `huginn 📬`; the mail woke `on short` 1.03 seconds later, the settle second, and the watcher left right after its line; an older unread mail woke nobody; `overview` then showed `huginn 📬` |
| 8 `off` | `overview` showed `corvus 📭` during the watch; the watcher left 25 ms after `off` began, with `stopped` and 143; `off` said `cleanup done`, and `overview` then showed `corvus 📪` |
| 9 takeover | a second `on` made the first leave within 22 ms, with 143, and held the seat: `muninn 📬` |
| 10 no seat | the raven's line, and bash saw 176 |
| 11 refusals | an unknown verb, a mail limit that is no number, no such group, a group as `send`'s target, a sender who is no member, and an unknown watcher length: each its line, and 1 |
| 12 beyond ASCII | umlauts, Ⓦ, 📬 and a second line starting with `/` arrived exactly as sent; straight into the exe, without `calm_comms.sh`, `/ok` became `C:/Program Files/Git/ok` |
| 13 `inbox` limits | three mails, then `2 more waiting`; the fourth alone, since the 12 KB one would cross the size limit; then the big one alone |
| 14 `overview groups` | `ravens`; with its name, `huginn 📬` and `muninn 📫`; an unknown group, and `overview ravens` without `groups`, each their line and 1 |

### Not tested yet

- Linux and macOS: the code vets there, but has never run.

### Deploy

- `deploy.bat` copies `SKILL.md`, `calm_comms.sh` and `calm_comms.exe` into `~/.claude/skills/calm-comms/`, so the exe is built first.
- Windows keeps a running exe locked, so a deploy needs every watcher off: a schnackout first, or `deploy.bat` says `FAILED  calm_comms.exe`.

## Callers outside the skill

### calm-email's forward

- `forward` runs the deployed `calm_comms.sh` by its path, through `bash`, as `send postmaster <seat_name> <text>`.
- The text is one argument of several lines: `An email from Ⓦ, subject: …`, the date, and up to 8000 characters of plain text, plus the attachment lines.
  So every forward carries text beyond ASCII.
- It relies on one thing, and the port keeps it: a refusal exits with a code other than 0.
  `send`'s answer, such as `muninn 📬`, passes through to the postmaster.
  `calm_email.sh` runs under `set -e`, so a refusal ends `forward`, and the refusal's line is what the postmaster sees.

### The fernschreiber

- It used terminal mode, which is gone: Wally's terminal brings its own watcher.

## Known limits

- With notifications, a NOTAR reaches every watcher at the same instant, so their ravens wake together; the bash version's polls and jitter spread them.
  Whether the hall minds is still to be seen.
- Bash and Go watchers don't see each other: bash trusts process IDs, Go trusts the lock, so a hall runs one version at a time.
- A missing seat exits with 5040: bash shows it as 176, as SKILL.md says, but a caller outside bash sees 5040.
- Git Bash rewrites arguments that look like POSIX paths, such as a text starting with `/`, before a native exe sees them; `calm_comms.sh` turns that off with `MSYS_NO_PATHCONV=1`, and a caller that runs the exe directly has to do the same.

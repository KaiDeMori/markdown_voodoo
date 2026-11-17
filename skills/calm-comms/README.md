# calm-comms: the builders' doc

The reasons behind the code of calm-comms.

## The watcher

- A notification from fsnotify is a hint to rescan the seat, and the rescan decides what is new mail.
- A lost notification delays a wake by at most one poll interval, and a duplicate triggers one more rescan.
- The watcher also polls, because notifications get lost when their buffer overflows, and because fsnotify can fail to start.

### The lock

- A watcher holds an exclusive lock on its seat's `watching.md` as long as it runs.
- The system releases the lock when the process ends, also after a crash or a hard kill.
- `overview` tests the lock instead of a process ID: a shared lock fails only while a watcher runs.
- After a hard kill, `watching.md` keeps its `until` line, and the free lock marks the seat as unwatched.
- On Windows, a lock blocks every other process, so the lock covers one byte at 1 GiB, beyond the end of the file, as SQLite's locks do.
  Reading and writing `watching.md` stay possible.
- On Linux and macOS, the lock is `flock` on the whole file, which affects only processes that call `flock` too.

### Stopping

- A stop is a request: `off` and a newer `on` empty `watching.md`, and the watcher exits once `watching.md` no longer holds its process ID.
- The `pid` line names the owner of `watching.md`; only the lock tells whether a watcher runs.

## The archive

- The archive moves only read mail: mail at the top of a seat is unread, and it stays there until `inbox` prints it.
- `group` writes the thread message after every member's copy, so `archive_read_messages` sees a thread message only once all its copies exist.
- A file whose move fails stays where it is: the next call tries again, and the verb that called `archive_read_messages` continues.
- Old archive folders are deleted by hand.

## Build

```bash
cd skills/calm-comms
gofmt -l .
go vet ./...
GOOS=linux go vet ./...
go build -o calm_comms.exe .
```

- `gofmt -l` names no file.
- The lock is the only code that differs by system, and `GOOS=linux go vet` checks `lock_unix.go`.
- An exe started in this folder reads this folder's `calm_comms_settings.json`, which names the live haven.

## Deploy

- The `calm_comms_settings.json` in this folder holds the live values.

## Callers outside the skill

- calm-email's `forward` runs the deployed `calm_comms.sh` as `send postmaster <seat_name> <text>`, with text of several lines and beyond ASCII.
- `forward` reads exit code 0 as delivered and any other code as a refusal, and shows the refusal's line to the postmaster.

## Known limits

- A group mail wakes every watching member at the same moment.
- A missing seat exits with 5040, which bash reports as 176 (5040 modulo 256); a caller outside bash sees 5040.
- Exit code 2 is Go's exit code after a panic: the tool itself failed.
- Git Bash rewrites arguments that look like POSIX paths, such as a text starting with `/`.
  `calm_comms.sh` sets `MSYS_NO_PATHCONV=1`, and a caller that runs the exe directly sets it too.
- The code passes `go vet` for Linux and macOS and has never run there.

package main

import (
	"os"

	"golang.org/x/sys/windows"
)

// On Windows a lock binds every process, so it sits on a single byte far beyond the end of watching.md, as SQLite's locks do:
// reading and writing what the file says never meet it.
var locked_byte = windows.Overlapped{Offset: 0x40000000}

// try_lock takes the lock on watching.md without waiting: exclusive for a watcher, shared for a look.
func try_lock(file *os.File, exclusive bool) bool {
	flags := uint32(windows.LOCKFILE_FAIL_IMMEDIATELY)
	if exclusive {
		flags |= windows.LOCKFILE_EXCLUSIVE_LOCK
	}
	overlapped := locked_byte
	return windows.LockFileEx(windows.Handle(file.Fd()), flags, 0, 1, 0, &overlapped) == nil
}

func unlock(file *os.File) {
	overlapped := locked_byte
	windows.UnlockFileEx(windows.Handle(file.Fd()), 0, 1, 0, &overlapped)
}

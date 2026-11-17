package main

import (
	"os"

	"golang.org/x/sys/windows"
)

var locked_byte = windows.Overlapped{Offset: 0x40000000}

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

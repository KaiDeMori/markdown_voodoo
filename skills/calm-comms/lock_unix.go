//go:build linux || darwin

package main

import (
	"os"
	"syscall"
)

// Elsewhere flock locks the whole file, and binds only those who ask, so reading and writing what the file says go on as usual.

// try_lock takes the lock on watching.md without waiting: exclusive for a watcher, shared for a look.
func try_lock(file *os.File, exclusive bool) bool {
	operation := syscall.LOCK_SH
	if exclusive {
		operation = syscall.LOCK_EX
	}
	return syscall.Flock(int(file.Fd()), operation|syscall.LOCK_NB) == nil
}

func unlock(file *os.File) {
	syscall.Flock(int(file.Fd()), syscall.LOCK_UN)
}

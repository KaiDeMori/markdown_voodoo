//go:build linux || darwin

package main

import (
	"os"
	"syscall"
)

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

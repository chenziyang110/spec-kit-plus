//go:build !windows

package runtime

import "syscall"

func commandProcessExistsForTest(pid int) bool {
	return syscall.Kill(pid, 0) == nil
}

func terminateCommandProcessForTest(pid int) error {
	return syscall.Kill(pid, syscall.SIGKILL)
}

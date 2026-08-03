//go:build !windows

package runcontrol

import "syscall"

func processTreeProcessExistsForTest(pid int) bool {
	return syscall.Kill(pid, 0) == nil
}

func terminateProcessTreePIDForTest(pid int) error {
	return syscall.Kill(pid, syscall.SIGKILL)
}

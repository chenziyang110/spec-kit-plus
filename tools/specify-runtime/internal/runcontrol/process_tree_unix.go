//go:build unix

package runcontrol

import (
	"errors"
	"fmt"
	"os/exec"
	"syscall"
)

type unixProcessTree struct {
	processGroupID int
}

func newProcessTreePlatform() processTreePlatform {
	return &unixProcessTree{}
}

func (tree *unixProcessTree) configure(command *exec.Cmd) error {
	attr := &syscall.SysProcAttr{}
	if command.SysProcAttr != nil {
		*attr = *command.SysProcAttr
	}
	attr.Setpgid = true
	command.SysProcAttr = attr
	return nil
}

func (tree *unixProcessTree) afterStart(command *exec.Cmd) error {
	if command.Process == nil {
		return fmt.Errorf("%w: started command is missing process metadata", ErrInvalidArgument)
	}
	tree.processGroupID = command.Process.Pid
	return nil
}

func (tree *unixProcessTree) terminate() error {
	if tree.processGroupID == 0 {
		return nil
	}
	err := syscall.Kill(-tree.processGroupID, syscall.SIGKILL)
	if err == nil || errors.Is(err, syscall.ESRCH) {
		return nil
	}
	return err
}

func (tree *unixProcessTree) close() error {
	tree.processGroupID = 0
	return nil
}

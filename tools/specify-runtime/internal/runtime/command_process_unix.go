//go:build unix

package runtime

import (
	"errors"
	"fmt"
	"os/exec"
	"syscall"
)

type unixCommandProcessTree struct {
	processGroupID int
}

func newCommandProcessTreePlatform() commandProcessTreePlatform {
	return &unixCommandProcessTree{}
}

func (tree *unixCommandProcessTree) configure(command *exec.Cmd) error {
	attributes := &syscall.SysProcAttr{}
	if command.SysProcAttr != nil {
		*attributes = *command.SysProcAttr
	}
	attributes.Setpgid = true
	command.SysProcAttr = attributes
	return nil
}

func (tree *unixCommandProcessTree) afterStart(command *exec.Cmd) error {
	if command.Process == nil {
		return fmt.Errorf("started command is missing process metadata")
	}
	tree.processGroupID = command.Process.Pid
	return nil
}

func (tree *unixCommandProcessTree) terminate() error {
	if tree.processGroupID == 0 {
		return nil
	}
	err := syscall.Kill(-tree.processGroupID, syscall.SIGKILL)
	if err == nil || errors.Is(err, syscall.ESRCH) {
		return nil
	}
	return err
}

func (tree *unixCommandProcessTree) close() error {
	tree.processGroupID = 0
	return nil
}

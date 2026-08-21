//go:build !windows && !unix

package runtime

import "os/exec"

type fallbackCommandProcessTree struct {
	command *exec.Cmd
}

func newCommandProcessTreePlatform() commandProcessTreePlatform {
	return &fallbackCommandProcessTree{}
}

func (tree *fallbackCommandProcessTree) configure(*exec.Cmd) error {
	return nil
}

func (tree *fallbackCommandProcessTree) afterStart(command *exec.Cmd) error {
	tree.command = command
	return nil
}

func (tree *fallbackCommandProcessTree) terminate() error {
	if tree.command != nil && tree.command.Process != nil {
		return tree.command.Process.Kill()
	}
	return nil
}

func (tree *fallbackCommandProcessTree) close() error {
	tree.command = nil
	return nil
}

package runtime

import (
	"errors"
	"fmt"
	"os/exec"
)

type commandProcessTree struct {
	platform commandProcessTreePlatform
}

type commandProcessTreePlatform interface {
	configure(*exec.Cmd) error
	afterStart(*exec.Cmd) error
	terminate() error
	close() error
}

func newCommandProcessTree() *commandProcessTree {
	return &commandProcessTree{platform: newCommandProcessTreePlatform()}
}

func (tree *commandProcessTree) configure(command *exec.Cmd) error {
	if command == nil {
		return errors.New("process tree configure requires a command")
	}
	return tree.platform.configure(command)
}

func (tree *commandProcessTree) start(command *exec.Cmd) error {
	if command == nil {
		return errors.New("process tree start requires a command")
	}
	if err := command.Start(); err != nil {
		return err
	}
	if err := tree.platform.afterStart(command); err != nil {
		return errors.Join(
			fmt.Errorf("bind child process tree: %w", err),
			tree.platform.terminate(),
			command.Wait(),
			tree.platform.close(),
		)
	}
	return nil
}

func (tree *commandProcessTree) terminate() error {
	return tree.platform.terminate()
}

func (tree *commandProcessTree) close() error {
	return tree.platform.close()
}

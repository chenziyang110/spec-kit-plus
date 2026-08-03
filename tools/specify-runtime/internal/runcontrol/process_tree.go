package runcontrol

import (
	"errors"
	"fmt"
	"os/exec"
	"sync"
)

// processTree encapsulates the minimum lifecycle needed to bind an exec.Cmd to
// a platform-owned process tree. Callers configure the command before Start,
// then use start/terminate/close around the child lifecycle.
type processTree struct {
	mu       sync.Mutex
	platform processTreePlatform
}

type processTreePlatform interface {
	configure(*exec.Cmd) error
	afterStart(*exec.Cmd) error
	terminate() error
	close() error
}

func newProcessTree() *processTree {
	return &processTree{platform: newProcessTreePlatform()}
}

func (tree *processTree) configure(command *exec.Cmd) error {
	if command == nil {
		return fmt.Errorf("%w: process tree configure requires a command", ErrInvalidArgument)
	}
	tree.mu.Lock()
	defer tree.mu.Unlock()
	return tree.platform.configure(command)
}

func (tree *processTree) start(command *exec.Cmd) error {
	if command == nil {
		return fmt.Errorf("%w: process tree start requires a command", ErrInvalidArgument)
	}
	tree.mu.Lock()
	defer tree.mu.Unlock()

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

func (tree *processTree) terminate() error {
	tree.mu.Lock()
	defer tree.mu.Unlock()
	return tree.platform.terminate()
}

func (tree *processTree) close() error {
	tree.mu.Lock()
	defer tree.mu.Unlock()
	return tree.platform.close()
}

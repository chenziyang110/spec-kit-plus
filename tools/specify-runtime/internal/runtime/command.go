package runtime

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"os/exec"
	"sync"
	"time"
)

const (
	DefaultExternalCommandTimeout = 30 * time.Second
	externalCommandWaitDelay      = 2 * time.Second
)

func CommandOutput(dir string, stdin io.Reader, name string, args ...string) ([]byte, error) {
	ctx, cancel := context.WithTimeout(context.Background(), DefaultExternalCommandTimeout)
	defer cancel()
	return CommandOutputContext(ctx, dir, stdin, name, args...)
}

func CommandOutputContext(ctx context.Context, dir string, stdin io.Reader, name string, args ...string) ([]byte, error) {
	stdout, stderr, err := CommandOutputsContext(ctx, dir, stdin, name, args...)
	if exitErr, ok := err.(*exec.ExitError); ok {
		exitErr.Stderr = stderr
	}
	return stdout, err
}

func CommandOutputsContext(ctx context.Context, dir string, stdin io.Reader, name string, args ...string) ([]byte, []byte, error) {
	return CommandOutputsWithTimeoutContext(ctx, DefaultExternalCommandTimeout, dir, stdin, name, args...)
}

func CommandOutputsWithTimeoutContext(
	ctx context.Context,
	timeout time.Duration,
	dir string,
	stdin io.Reader,
	name string,
	args ...string,
) ([]byte, []byte, error) {
	boundedCtx, cancel := commandContextWithBudget(ctx, timeout)
	defer cancel()
	var stdout, stderr synchronizedBuffer
	err := runExternalCommand(boundedCtx, dir, stdin, nil, &stdout, &stderr, name, args...)
	return stdout.bytes(), stderr.bytes(), err
}

func CommandCombinedOutput(dir string, stdin io.Reader, name string, args ...string) ([]byte, error) {
	ctx, cancel := context.WithTimeout(context.Background(), DefaultExternalCommandTimeout)
	defer cancel()
	return CommandCombinedOutputContext(ctx, dir, stdin, name, args...)
}

func CommandCombinedOutputContext(ctx context.Context, dir string, stdin io.Reader, name string, args ...string) ([]byte, error) {
	boundedCtx, cancel := commandContextWithBudget(ctx, DefaultExternalCommandTimeout)
	defer cancel()
	var output synchronizedBuffer
	err := runExternalCommand(boundedCtx, dir, stdin, nil, &output, &output, name, args...)
	return output.bytes(), err
}

func CommandCombinedOutputEnvironmentContext(
	ctx context.Context,
	dir string,
	stdin io.Reader,
	environment []string,
	name string,
	args ...string,
) ([]byte, error) {
	boundedCtx, cancel := commandContextWithBudget(ctx, DefaultExternalCommandTimeout)
	defer cancel()
	var output synchronizedBuffer
	err := runExternalCommand(boundedCtx, dir, stdin, environment, &output, &output, name, args...)
	return output.bytes(), err
}

func CommandRun(dir string, stdin io.Reader, name string, args ...string) error {
	ctx, cancel := context.WithTimeout(context.Background(), DefaultExternalCommandTimeout)
	defer cancel()
	return CommandRunContext(ctx, dir, stdin, name, args...)
}

func CommandRunContext(ctx context.Context, dir string, stdin io.Reader, name string, args ...string) error {
	boundedCtx, cancel := commandContextWithBudget(ctx, DefaultExternalCommandTimeout)
	defer cancel()
	return runExternalCommand(boundedCtx, dir, stdin, nil, nil, nil, name, args...)
}

func commandContextWithBudget(parent context.Context, timeout time.Duration) (context.Context, context.CancelFunc) {
	if timeout <= 0 {
		timeout = DefaultExternalCommandTimeout
	}
	if deadline, ok := parent.Deadline(); ok && time.Until(deadline) <= timeout {
		return context.WithCancel(parent)
	}
	return context.WithTimeout(parent, timeout)
}

type synchronizedBuffer struct {
	mu sync.Mutex
	bytes.Buffer
}

func (buffer *synchronizedBuffer) Write(value []byte) (int, error) {
	buffer.mu.Lock()
	defer buffer.mu.Unlock()
	return buffer.Buffer.Write(value)
}

func (buffer *synchronizedBuffer) bytes() []byte {
	buffer.mu.Lock()
	defer buffer.mu.Unlock()
	return append([]byte(nil), buffer.Buffer.Bytes()...)
}

func runExternalCommand(
	ctx context.Context,
	dir string,
	stdin io.Reader,
	environment []string,
	stdout, stderr io.Writer,
	name string,
	args ...string,
) error {
	if err := ctx.Err(); err != nil {
		return commandDeadlineError(name, err, nil)
	}
	command := exec.Command(name, args...)
	command.Dir = dir
	command.Stdin = stdin
	if environment != nil {
		command.Env = environment
	}
	command.Stdout = stdout
	command.Stderr = stderr
	command.WaitDelay = externalCommandWaitDelay
	processes := newCommandProcessTree()
	if err := processes.configure(command); err != nil {
		return fmt.Errorf("configure %s process tree: %w", name, err)
	}
	if err := processes.start(command); err != nil {
		_ = processes.close()
		return err
	}
	waited := make(chan error, 1)
	go func() { waited <- command.Wait() }()

	select {
	case err := <-waited:
		if closeErr := processes.close(); closeErr != nil {
			return errors.Join(err, closeErr)
		}
		return err
	case <-ctx.Done():
	}

	terminateErr := processes.terminate()
	waitTimer := time.NewTimer(externalCommandWaitDelay)
	defer waitTimer.Stop()
	select {
	case <-waited:
	case <-waitTimer.C:
		if command.Process != nil {
			_ = command.Process.Kill()
		}
	}
	closeErr := processes.close()
	return commandDeadlineError(name, ctx.Err(), errors.Join(terminateErr, closeErr))
}

func commandDeadlineError(name string, deadlineErr, cleanupErr error) error {
	if deadlineErr == nil {
		deadlineErr = context.DeadlineExceeded
	}
	message := fmt.Errorf("%s command did not finish before its deadline: %w", name, deadlineErr)
	return errors.Join(message, cleanupErr)
}

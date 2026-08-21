package runtime

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"testing"
	"time"
)

func TestCommandOutputContextReturnsAtDeadline(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Millisecond)
	defer cancel()
	started := time.Now()

	output, err := CommandOutputContext(
		ctx,
		"",
		nil,
		os.Args[0],
		"-test.run=^TestBoundedCommandHelperProcess$",
		"--",
		"sleep",
	)

	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("bounded command error = %v, want context deadline; output=%q", err, output)
	}
	if elapsed := time.Since(started); elapsed > 3*time.Second {
		t.Fatalf("bounded command returned after %s, want under 3s", elapsed)
	}
}

func TestCommandOutputContextKillsProcessTree(t *testing.T) {
	pidPath := filepath.Join(t.TempDir(), "grandchild.pid")
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	type commandResult struct {
		output []byte
		err    error
	}
	done := make(chan commandResult, 1)
	go func() {
		output, err := CommandOutputContext(
			ctx,
			"",
			nil,
			os.Args[0],
			"-test.run=^TestBoundedCommandHelperProcess$",
			"--",
			"spawn-grandchild",
			pidPath,
		)
		done <- commandResult{output: output, err: err}
	}()
	waitForCommandPIDFile(t, pidPath)
	started := time.Now()
	cancel()
	var result commandResult
	select {
	case result = <-done:
	case <-time.After(3 * time.Second):
		t.Fatal("process-tree command did not return within 3s of cancellation")
	}
	if !errors.Is(result.err, context.Canceled) {
		t.Fatalf("process-tree command error = %v, want context canceled; output=%q", result.err, result.output)
	}
	if elapsed := time.Since(started); elapsed > 3*time.Second {
		t.Fatalf("process-tree command returned after %s, want under 3s", elapsed)
	}
	rawPID, readErr := os.ReadFile(pidPath)
	if readErr != nil {
		t.Fatalf("read grandchild pid: %v; output=%q", readErr, result.output)
	}
	grandchildPID, parseErr := strconv.Atoi(string(rawPID))
	if parseErr != nil || grandchildPID <= 0 {
		t.Fatalf("grandchild pid = %q: %v", rawPID, parseErr)
	}
	t.Cleanup(func() {
		if commandProcessExistsForTest(grandchildPID) {
			_ = terminateCommandProcessForTest(grandchildPID)
		}
	})
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if !commandProcessExistsForTest(grandchildPID) {
			return
		}
		time.Sleep(25 * time.Millisecond)
	}
	t.Fatalf("grandchild process %d survived the command deadline", grandchildPID)
}

func waitForCommandPIDFile(t *testing.T, path string) {
	t.Helper()
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		if _, err := os.Stat(path); err == nil {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("command helper did not create pid file %q", path)
}

func TestBoundedCommandHelperProcess(t *testing.T) {
	arguments := commandHelperArgumentsAfterSeparator(os.Args)
	if len(arguments) == 0 {
		return
	}
	switch arguments[0] {
	case "sleep", "grandchild":
		fmt.Print("started")
		time.Sleep(time.Hour)
	case "spawn-grandchild":
		if len(arguments) != 2 {
			os.Exit(120)
		}
		command := exec.Command(os.Args[0], "-test.run=^TestBoundedCommandHelperProcess$", "--", "grandchild")
		command.Stdout = os.Stdout
		command.Stderr = os.Stderr
		if err := command.Start(); err != nil {
			os.Exit(121)
		}
		if err := os.WriteFile(arguments[1], []byte(strconv.Itoa(command.Process.Pid)), 0o644); err != nil {
			os.Exit(122)
		}
		fmt.Print("started")
		time.Sleep(time.Hour)
	default:
		os.Exit(123)
	}
}

func commandHelperArgumentsAfterSeparator(arguments []string) []string {
	for index, argument := range arguments {
		if argument == "--" {
			return arguments[index+1:]
		}
	}
	return nil
}

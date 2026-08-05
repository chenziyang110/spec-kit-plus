package runcontrol

import (
	"context"
	"errors"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"
)

const processTreeHelperEnvironment = "SPECIFY_RUNTIME_PROCESS_TREE_HELPER"

func TestForegroundSupervisorCancellationKillsEntireProcessTree(t *testing.T) {
	t.Setenv(processTreeHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	queued := enqueueForegroundTestRun(t, repository, "process_tree_cancel")
	readyPath := filepath.Join(t.TempDir(), "process-tree-ready")
	pidPath := filepath.Join(t.TempDir(), "process-tree-grandchild.pid")
	ctx, cancel := context.WithCancel(context.Background())
	t.Cleanup(cancel)

	type completion struct {
		result SupervisedRun
		err    error
	}
	done := make(chan completion, 1)
	go func() {
		result, runErr := SuperviseRun(ctx, repository, processTreeTestParams(
			queued.RunID,
			"spawn-grandchild",
			readyPath,
			pidPath,
		))
		done <- completion{result: result, err: runErr}
	}()

	waitForFileForTest(t, readyPath)
	grandchildPID := waitForPIDForTest(t, pidPath)
	t.Cleanup(func() {
		if processTreeProcessExistsForTest(grandchildPID) {
			_ = terminateProcessTreePIDForTest(grandchildPID)
		}
	})

	cancel()
	select {
	case finished := <-done:
		if !errors.Is(finished.err, context.Canceled) {
			t.Fatalf("cancelled process-tree supervision error = %v, want context.Canceled", finished.err)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("cancelled process-tree supervision did not stop")
	}

	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if !processTreeProcessExistsForTest(grandchildPID) {
			return
		}
		time.Sleep(25 * time.Millisecond)
	}
	t.Fatalf("grandchild process %d survived cancellation; want full process-tree termination", grandchildPID)
}

func TestProcessTreeHelperProcess(t *testing.T) {
	if os.Getenv(processTreeHelperEnvironment) != "1" {
		return
	}
	arguments := processTreeHelperArgumentsAfterSeparator(os.Args)
	if len(arguments) < 1 {
		os.Exit(110)
	}
	switch arguments[0] {
	case "spawn-grandchild":
		if len(arguments) != 3 {
			os.Exit(111)
		}
		pidFile := arguments[2]
		command := exec.Command(os.Args[0], "-test.run=^TestProcessTreeHelperProcess$", "--", "grandchild", pidFile)
		command.Env = append(os.Environ(), processTreeHelperEnvironment+"=1")
		command.Stdout = io.Discard
		command.Stderr = io.Discard
		if err := command.Start(); err != nil {
			os.Exit(112)
		}
		cwd, err := os.Getwd()
		if err != nil {
			os.Exit(113)
		}
		ready := strings.Join([]string{cwd, strconv.Itoa(command.Process.Pid)}, "\n")
		if err := os.WriteFile(arguments[1], []byte(ready), 0o644); err != nil {
			os.Exit(114)
		}
		for {
			time.Sleep(time.Hour)
		}
	case "grandchild":
		if len(arguments) != 2 {
			os.Exit(115)
		}
		if err := os.WriteFile(arguments[1], []byte(strconv.Itoa(os.Getpid())), 0o644); err != nil {
			os.Exit(116)
		}
		for {
			time.Sleep(time.Hour)
		}
	default:
		os.Exit(117)
	}
}

func processTreeTestParams(runID string, helperArguments ...string) SuperviseRunParams {
	argv := []string{os.Args[0], "-test.run=^TestProcessTreeHelperProcess$", "--"}
	argv = append(argv, helperArguments...)
	return SuperviseRunParams{
		RunID:                runID,
		AdapterID:            "process-tree-helper",
		Argv:                 argv,
		ChildStdout:          io.Discard,
		ChildStderr:          io.Discard,
		HeartbeatInterval:    500 * time.Millisecond,
		LeaseDuration:        10 * time.Second,
		SupervisorStaleAfter: 10 * time.Second,
	}
}

func processTreeHelperArgumentsAfterSeparator(arguments []string) []string {
	for index, argument := range arguments {
		if argument == "--" {
			return arguments[index+1:]
		}
	}
	return nil
}

func waitForFileForTest(t *testing.T, path string) {
	t.Helper()
	deadline := time.Now().Add(10 * time.Second)
	for time.Now().Before(deadline) {
		if _, err := os.Stat(path); err == nil {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("expected file was not created: %q", path)
}

func waitForPIDForTest(t *testing.T, path string) int {
	t.Helper()
	waitForFileForTest(t, path)
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read pid file %q: %v", path, err)
	}
	pid, err := strconv.Atoi(strings.TrimSpace(string(data)))
	if err != nil || pid <= 0 {
		t.Fatalf("pid file %q contained %q, want a positive integer: %v", path, data, err)
	}
	return pid
}

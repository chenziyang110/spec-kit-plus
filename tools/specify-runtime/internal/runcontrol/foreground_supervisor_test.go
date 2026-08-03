package runcontrol

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"
)

const foregroundHelperEnvironment = "SPECIFY_RUNTIME_FOREGROUND_HELPER"

func TestInitialAttemptLeaseCoversSerializedLaunchOperations(t *testing.T) {
	activeLease := 10 * time.Second
	want := activeLease + attemptLaunchDatabaseOperations*time.Duration(sqliteBusyTimeoutMS)*time.Millisecond
	if got := initialAttemptLeaseDuration(activeLease); got != want {
		t.Fatalf("initial attempt lease duration = %s, want %s", got, want)
	}
}

func TestSuperviseRunRejectsLivenessWindowsBelowSQLiteContention(t *testing.T) {
	contentionWindow := time.Duration(sqliteBusyTimeoutMS) * time.Millisecond
	valid := SuperviseRunParams{
		RunID:                "validated_run",
		AdapterID:            "test",
		Argv:                 []string{"test-helper"},
		HeartbeatInterval:    500 * time.Millisecond,
		LeaseDuration:        2 * contentionWindow,
		SupervisorStaleAfter: 2 * contentionWindow,
	}
	repository := Repository{Root: "repository", DatabasePath: "run-control.sqlite"}

	shortLease := valid
	shortLease.LeaseDuration = contentionWindow
	if err := validateSuperviseRunParams(repository, shortLease); !errors.Is(err, ErrInvalidArgument) {
		t.Fatalf("short lease validation error = %v, want ErrInvalidArgument", err)
	}

	shortStaleWindow := valid
	shortStaleWindow.SupervisorStaleAfter = contentionWindow
	if err := validateSuperviseRunParams(repository, shortStaleWindow); !errors.Is(err, ErrInvalidArgument) {
		t.Fatalf("short stale window validation error = %v, want ErrInvalidArgument", err)
	}
}

func TestForegroundSupervisorForcesRecordedWorkspaceAndLiteralArgv(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	enqueueForegroundTestRun(t, repository, "foreground_cwd")

	result, err := SuperviseRun(context.Background(), repository, foregroundTestParams(
		"foreground_cwd",
		"write",
		"agent-marker.txt",
		"semi;colon",
		"two words",
	))
	if err != nil {
		t.Fatal(err)
	}
	if result.ExitCode != 0 || result.Run.Status != RunSealed || result.Attempt.Status != AttemptFinished ||
		result.Activity.Status != ActivitySucceeded || result.Workspace.Status != WorkspaceSealed {
		t.Fatalf("supervised result = %#v, want successful sealed execution", result)
	}
	marker, err := os.ReadFile(filepath.Join(result.Workspace.RootPath, "agent-marker.txt"))
	if err != nil {
		t.Fatal(err)
	}
	want := result.Workspace.RootPath + "\nsemi;colon\ntwo words"
	if string(marker) != want {
		t.Fatalf("agent marker = %q, want %q", marker, want)
	}
	if _, err := os.Stat(filepath.Join(mainRoot, "agent-marker.txt")); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("primary worktree was modified by supervised child: %v", err)
	}
}

func TestForegroundSupervisorSupportsFiveParallelRuns(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	for index := 1; index <= 5; index++ {
		enqueueForegroundTestRun(t, repository, "foreground_parallel_"+strconv.Itoa(index))
	}

	type supervision struct {
		result SupervisedRun
		err    error
	}
	start := make(chan struct{})
	results := make(chan supervision, 5)
	var workers sync.WaitGroup
	for index := 1; index <= 5; index++ {
		runID := "foreground_parallel_" + strconv.Itoa(index)
		marker := "parallel-" + strconv.Itoa(index) + ".txt"
		workers.Add(1)
		go func() {
			defer workers.Done()
			<-start
			result, runErr := SuperviseRun(
				context.Background(),
				repository,
				foregroundTestParams(runID, "write", marker, runID),
			)
			results <- supervision{result: result, err: runErr}
		}()
	}
	close(start)
	workers.Wait()
	close(results)

	workspaceRoots := map[string]struct{}{}
	for completed := range results {
		if completed.err != nil || completed.result.Run.Status != RunSealed {
			t.Fatalf("parallel supervision = %#v err=%v", completed.result, completed.err)
		}
		if _, duplicate := workspaceRoots[completed.result.Workspace.RootPath]; duplicate {
			t.Fatalf("parallel Runs shared workspace %q", completed.result.Workspace.RootPath)
		}
		workspaceRoots[completed.result.Workspace.RootPath] = struct{}{}
	}
	if len(workspaceRoots) != 5 {
		t.Fatalf("parallel workspace count = %d, want 5", len(workspaceRoots))
	}
}

func TestForegroundSupervisorCancellationQuarantinesAndRetriesInNextGeneration(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	queued := enqueueForegroundTestRun(t, repository, "foreground_retry")
	firstPlan, err := PlanGitWorkspace(context.Background(), repository, queued, 1)
	if err != nil {
		t.Fatal(err)
	}
	readyPath := filepath.Join(t.TempDir(), "child-ready")
	ctx, cancel := context.WithCancel(context.Background())
	type completion struct {
		result SupervisedRun
		err    error
	}
	done := make(chan completion, 1)
	go func() {
		result, runErr := SuperviseRun(ctx, repository, foregroundTestParams(
			"foreground_retry",
			"block",
			readyPath,
		))
		done <- completion{result: result, err: runErr}
	}()
	waitForForegroundHelper(t, readyPath)
	cancel()
	interrupted := <-done
	if !errors.Is(interrupted.err, context.Canceled) {
		t.Fatalf("cancelled supervision error = %v, want context.Canceled", interrupted.err)
	}

	observer := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("foreground_retry_observer"))
	interruptedRun, err := observer.GetRun(context.Background(), queued.RunID)
	if err != nil {
		t.Fatal(err)
	}
	firstWorkspace, err := observer.GetWorkspace(context.Background(), firstPlan.WorkspaceID)
	if err != nil {
		t.Fatal(err)
	}
	if interruptedRun.Status != RunInterrupted || firstWorkspace.Status != WorkspaceQuarantined {
		t.Fatalf("cancelled execution = %#v / %#v, want interrupted and quarantined", interruptedRun, firstWorkspace)
	}

	retried, err := SuperviseRun(
		context.Background(),
		repository,
		foregroundTestParams("foreground_retry", "write", "retried.txt", "generation-2"),
	)
	if err != nil {
		t.Fatal(err)
	}
	if retried.Run.Status != RunSealed || retried.Workspace.Generation != 2 ||
		retried.Workspace.RootPath == firstWorkspace.RootPath {
		t.Fatalf("retried execution = %#v, want sealed generation 2", retried)
	}
}

func TestForegroundSupervisorRecordsNonzeroExitAsFailedExecution(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	enqueueForegroundTestRun(t, repository, "foreground_failure")

	result, err := SuperviseRun(
		context.Background(),
		repository,
		foregroundTestParams("foreground_failure", "fail", "7"),
	)
	if err != nil {
		t.Fatal(err)
	}
	if result.ExitCode != 7 || result.Run.Status != RunFailed || result.Attempt.Status != AttemptFailed ||
		result.Activity.Status != ActivityFailed || result.Workspace.Status != WorkspaceQuarantined {
		t.Fatalf("failed supervised result = %#v", result)
	}
}

func TestForegroundSupervisorHelperProcess(t *testing.T) {
	if os.Getenv(foregroundHelperEnvironment) != "1" {
		return
	}
	arguments := helperArgumentsAfterSeparator(os.Args)
	if len(arguments) < 1 {
		os.Exit(90)
	}
	switch arguments[0] {
	case "write-exact":
		if len(arguments) != 3 {
			os.Exit(90)
		}
		cwd, err := os.Getwd()
		if err != nil || os.WriteFile(filepath.Join(cwd, arguments[1]), []byte(arguments[2]), 0o644) != nil {
			os.Exit(89)
		}
		os.Exit(0)
	case "write":
		if len(arguments) < 2 {
			os.Exit(91)
		}
		cwd, err := os.Getwd()
		if err != nil {
			os.Exit(92)
		}
		content := append([]string{cwd}, arguments[2:]...)
		if err := os.WriteFile(filepath.Join(cwd, arguments[1]), []byte(strings.Join(content, "\n")), 0o644); err != nil {
			os.Exit(93)
		}
		os.Exit(0)
	case "block":
		if len(arguments) != 2 {
			os.Exit(94)
		}
		cwd, err := os.Getwd()
		if err != nil || os.WriteFile(arguments[1], []byte(cwd), 0o644) != nil {
			os.Exit(95)
		}
		for {
			time.Sleep(time.Hour)
		}
	case "fail":
		if len(arguments) != 2 {
			os.Exit(96)
		}
		code, err := strconv.Atoi(arguments[1])
		if err != nil || code <= 0 {
			os.Exit(97)
		}
		os.Exit(code)
	default:
		os.Exit(98)
	}
}

func foregroundTestParams(runID string, helperArguments ...string) SuperviseRunParams {
	argv := []string{os.Args[0], "-test.run=^TestForegroundSupervisorHelperProcess$", "--"}
	argv = append(argv, helperArguments...)
	return SuperviseRunParams{
		RunID:                runID,
		AdapterID:            "test-helper",
		Argv:                 argv,
		ChildStdout:          io.Discard,
		ChildStderr:          io.Discard,
		HeartbeatInterval:    500 * time.Millisecond,
		LeaseDuration:        10 * time.Second,
		SupervisorStaleAfter: 10 * time.Second,
	}
}

func enqueueForegroundTestRun(t *testing.T, repository Repository, runID string) Run {
	t.Helper()
	store, err := Open(
		context.Background(),
		repository.DatabasePath,
		WithOwnerEpoch("submit_"+runID),
	)
	if err != nil {
		t.Fatal(err)
	}
	run, operationErr := store.EnqueueRun(context.Background(), CreateRunParams{
		RunID:        runID,
		Kind:         "sp-quick",
		SubjectType:  "quick",
		SubjectID:    runID,
		TargetRef:    "HEAD",
		IntentSHA256: digestForTest("intent:" + runID),
	})
	closeErr := store.Close()
	if operationErr != nil {
		t.Fatal(operationErr)
	}
	if closeErr != nil {
		t.Fatal(closeErr)
	}
	return run
}

func helperArgumentsAfterSeparator(arguments []string) []string {
	for index, argument := range arguments {
		if argument == "--" {
			return arguments[index+1:]
		}
	}
	return nil
}

func waitForForegroundHelper(t *testing.T, path string) {
	t.Helper()
	deadline := time.Now().Add(10 * time.Second)
	for time.Now().Before(deadline) {
		if _, err := os.Stat(path); err == nil {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("foreground helper did not become ready at %q", path)
}

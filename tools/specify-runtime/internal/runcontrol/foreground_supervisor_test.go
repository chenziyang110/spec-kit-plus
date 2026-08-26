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

func TestModifyingExecutionRunKindsRequireConfirmedScopeBeforeClaim(t *testing.T) {
	for _, kind := range []string{
		"fast", "sp-fast", "spx-fast",
		"debug", "sp-debug", "spx-debug",
		"implement", "sp-implement", "spx-implement",
		"quick", "sp-quick", "spx-quick",
	} {
		t.Run(kind, func(t *testing.T) {
			if _, err := supervisedRunWriteIntents(Run{Kind: kind}, nil); !errors.Is(err, ErrInvalidArgument) {
				t.Fatalf("unscoped %s run error = %v, want ErrInvalidArgument", kind, err)
			}
			intents, err := supervisedRunWriteIntents(Run{Kind: kind}, []WriteIntentSpec{{
				Path: "src/owned.go", Operation: WriteModify, Confidence: IntentConfirmed,
			}})
			if err != nil || len(intents) != 1 || intents[0].Path != "src/owned.go" {
				t.Fatalf("confirmed %s run intents = %#v err=%v", kind, intents, err)
			}
		})
	}
	if intents, err := supervisedRunWriteIntents(Run{Kind: "review"}, nil); err != nil || len(intents) != 0 {
		t.Fatalf("non-modifying run gate = %#v err=%v", intents, err)
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

	result, err := SuperviseRun(context.Background(), repository, foregroundIsolatedTestParams(
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
		result, runErr := SuperviseRun(ctx, repository, foregroundIsolatedTestParams(
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
		foregroundIsolatedTestParams("foreground_retry", "write", "retried.txt", "generation-2"),
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

func TestForegroundSupervisorCompletesAutomaticWorkBoardItemForSuccessfulRun(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	store := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("work_success_submit"))
	if _, err := store.EnqueueRun(context.Background(), CreateRunParams{
		RunID:        "foreground_work_success",
		Kind:         "sp-quick",
		SubjectType:  "file",
		SubjectID:    "work-success.txt",
		TargetRef:    "HEAD",
		IntentSHA256: digestForTest("foreground work success"),
	}); err != nil {
		t.Fatal(err)
	}

	result, err := SuperviseRun(context.Background(), repository, foregroundIsolatedTestParams(
		"foreground_work_success",
		"write",
		"work-success.txt",
		"completed",
	))
	if err != nil {
		t.Fatal(err)
	}
	work, intents := requireSingleWorkForRun(t, repository, result.Run.RunID, WorkCompleted)
	if work.TaskRef != "file:work-success.txt" || work.WorkspaceRoot != result.Workspace.RootPath ||
		work.BaseCommit != result.Workspace.BaseCommit {
		t.Fatalf("completed automatic work = %#v, want exact run workspace binding", work)
	}
	if len(intents) != 1 || intents[0].Path != "work-success.txt" ||
		intents[0].Status != WriteIntentReleased {
		t.Fatalf("completed automatic intents = %#v, want released run subject path", intents)
	}
}

func TestAutomaticRunWriteIntentsBindFeatureSubjectToExactFeatureDirectory(t *testing.T) {
	intents := automaticRunWriteIntents(Run{
		SubjectType: "feature",
		SubjectID:   "001-shared-board",
	})
	if len(intents) != 1 || intents[0].Path != ".specify/features/001-shared-board" ||
		intents[0].Operation != WriteCreate || intents[0].Confidence != IntentConfirmed {
		t.Fatalf("feature automatic write intents = %#v", intents)
	}

	for _, unsafeID := range []string{"../escape", "nested/feature", `.specify\\features\\001-other`} {
		if got := automaticRunWriteIntents(Run{SubjectType: "feature", SubjectID: unsafeID}); len(got) != 0 {
			t.Fatalf("unsafe feature subject %q produced intents %#v", unsafeID, got)
		}
	}
}

func TestForegroundSupervisorBlocksRunWhenAutomaticWorkBoardIntentConflicts(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	owner := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("work_conflict_owner"))
	if _, _, err := owner.BeginWork(context.Background(), BeginWorkParams{
		WorkID:        "manual_conflict_owner",
		Summary:       "manual owner edits conflict.txt",
		AgentID:       "manual-agent",
		AdapterID:     "manual-adapter",
		WorkspaceRoot: mainRoot,
		LeaseUntil:    time.Now().UTC().Add(10 * time.Minute),
		WriteIntents: []WriteIntentSpec{{
			Path:       "conflict.txt",
			Operation:  WriteModify,
			Confidence: IntentConfirmed,
		}},
	}); err != nil {
		t.Fatal(err)
	}
	enqueue := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("work_conflict_submit"))
	if _, err := enqueue.EnqueueRun(context.Background(), CreateRunParams{
		RunID:        "foreground_work_conflict",
		Kind:         "sp-quick",
		SubjectType:  "file",
		SubjectID:    "conflict.txt",
		TargetRef:    "HEAD",
		IntentSHA256: digestForTest("foreground work conflict"),
	}); err != nil {
		t.Fatal(err)
	}

	result, err := SuperviseRun(context.Background(), repository, foregroundIsolatedTestParams(
		"foreground_work_conflict",
		"write",
		"conflict.txt",
		"should-not-run",
	))
	if !errors.Is(err, ErrWorkIntentConflict) {
		t.Fatalf("conflicting automatic work error = %#v result=%#v, want ErrWorkIntentConflict", err, result)
	}
	items, err := owner.ListWork(context.Background(), ListWorkParams{})
	if err != nil {
		t.Fatal(err)
	}
	if len(items) != 1 || items[0].WorkID != "manual_conflict_owner" {
		t.Fatalf("conflicting run registered work = %#v, want only manual owner", items)
	}
}

func TestForegroundSupervisorInterruptsAutomaticWorkBoardItemWhenRunIsCancelled(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	store := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("work_cancel_submit"))
	if _, err := store.EnqueueRun(context.Background(), CreateRunParams{
		RunID:        "foreground_work_cancel",
		Kind:         "sp-quick",
		SubjectType:  "file",
		SubjectID:    "cancelled.txt",
		TargetRef:    "HEAD",
		IntentSHA256: digestForTest("foreground work cancel"),
	}); err != nil {
		t.Fatal(err)
	}

	readyPath := filepath.Join(t.TempDir(), "child-ready")
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() {
		_, runErr := SuperviseRun(ctx, repository, foregroundIsolatedTestParams(
			"foreground_work_cancel",
			"block-after-write",
			"cancelled.txt",
			readyPath,
		))
		done <- runErr
	}()
	waitForForegroundHelper(t, readyPath)
	cancel()
	if err := <-done; !errors.Is(err, context.Canceled) {
		t.Fatalf("cancelled supervision error = %v, want context.Canceled", err)
	}

	work, intents := requireSingleWorkForRun(t, repository, "foreground_work_cancel", WorkInterrupted)
	if !work.RecoveryHold || work.LastReason == "" || len(work.ObservedPaths) != 1 ||
		work.ObservedPaths[0] != "cancelled.txt" {
		t.Fatalf("interrupted automatic work = %#v, want dirty path recovery hold", work)
	}
	if len(intents) != 1 || intents[0].Path != "cancelled.txt" ||
		intents[0].Status != WriteIntentRecovery {
		t.Fatalf("interrupted automatic intents = %#v, want recovery-held run subject path", intents)
	}
}

func TestForegroundSupervisorKeepsAutomaticWorkBlockedAfterChildFailure(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	store := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("work_failure_submit"))
	if _, err := store.EnqueueRun(context.Background(), CreateRunParams{
		RunID:        "foreground_work_failure",
		Kind:         "sp-quick",
		SubjectType:  "file",
		SubjectID:    "failed.txt",
		TargetRef:    "HEAD",
		IntentSHA256: digestForTest("foreground work failure"),
	}); err != nil {
		t.Fatal(err)
	}

	result, err := SuperviseRun(context.Background(), repository, foregroundIsolatedTestParams(
		"foreground_work_failure",
		"fail",
		"7",
	))
	if err != nil {
		t.Fatal(err)
	}
	if result.ExitCode != 7 {
		t.Fatalf("failed supervised exit code = %d, want 7", result.ExitCode)
	}
	work, intents := requireSingleWorkForRun(t, repository, result.Run.RunID, WorkBlocked)
	if work.RecoveryHold || !strings.Contains(work.LastReason, "code 7") {
		t.Fatalf("failed automatic work = %#v, want blocked without recovery hold", work)
	}
	if len(intents) != 1 || intents[0].Status != WriteIntentActive {
		t.Fatalf("failed automatic intents = %#v, want retained active intent", intents)
	}
}

func TestForegroundSupervisorHeartbeatSurvivesChildScopeExpansion(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	store := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("work_scope_submit"))
	if _, err := store.EnqueueRun(context.Background(), CreateRunParams{
		RunID:        "foreground_work_scope",
		Kind:         "sp-quick",
		SubjectType:  "file",
		SubjectID:    "initial.txt",
		TargetRef:    "HEAD",
		IntentSHA256: digestForTest("foreground work scope expansion"),
	}); err != nil {
		t.Fatal(err)
	}

	readyPath := filepath.Join(t.TempDir(), "child-ready")
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() {
		_, runErr := SuperviseRun(ctx, repository, foregroundIsolatedTestParams(
			"foreground_work_scope",
			"block",
			readyPath,
		))
		done <- runErr
	}()
	waitForForegroundHelper(t, readyPath)

	observer := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("work_scope_observer"))
	work := waitForRunWork(t, observer, "foreground_work_scope", WorkActive)
	work, _, err = observer.AddWorkIntent(context.Background(), AddWorkIntentParams{
		WorkID:           work.WorkID,
		ExpectedRevision: work.Revision,
		Fence:            work.Fence,
		Spec: WriteIntentSpec{
			Path:       "discovered.txt",
			Operation:  WriteModify,
			Confidence: IntentConfirmed,
		},
	})
	if err != nil {
		cancel()
		t.Fatal(err)
	}
	time.Sleep(2 * foregroundTestParams("unused").HeartbeatInterval)
	select {
	case runErr := <-done:
		cancel()
		t.Fatalf("supervisor stopped after child scope expansion: %v", runErr)
	default:
	}
	checkpointed, _, err := observer.GetWork(context.Background(), work.WorkID)
	if err != nil {
		cancel()
		t.Fatal(err)
	}
	if checkpointed.Revision <= work.Revision || checkpointed.HeartbeatAtMS <= work.HeartbeatAtMS ||
		checkpointed.LeaseUntilMS < work.LeaseUntilMS {
		cancel()
		<-done
		t.Fatalf("automatic work heartbeat = %#v, want monotonic lease and renewed heartbeat after scope expansion %#v", checkpointed, work)
	}

	cancel()
	if err := <-done; !errors.Is(err, context.Canceled) {
		t.Fatalf("cancelled supervision error = %v, want context.Canceled", err)
	}
}

func TestForegroundSupervisorReconcilesExpiredWorkBeforeRegisteringAutomaticScope(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	owner := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("expired_work_owner"))
	expired, _, err := owner.BeginWork(context.Background(), BeginWorkParams{
		WorkID:        "expired_work",
		Summary:       "stale task from stopped computer",
		AgentID:       "stopped-agent",
		AdapterID:     "test-helper",
		WorkspaceRoot: mainRoot,
		LeaseUntil:    time.Now().UTC().Add(time.Minute),
		WriteIntents: []WriteIntentSpec{{
			Path:       "reclaimed.txt",
			Operation:  WriteModify,
			Confidence: IntentConfirmed,
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := owner.db.ExecContext(context.Background(),
		`UPDATE work_items SET lease_until_ms = 1 WHERE work_id = ?`, expired.WorkID); err != nil {
		t.Fatal(err)
	}
	if _, err := owner.EnqueueRun(context.Background(), CreateRunParams{
		RunID:        "foreground_work_reclaim",
		Kind:         "sp-quick",
		SubjectType:  "file",
		SubjectID:    "reclaimed.txt",
		TargetRef:    "HEAD",
		IntentSHA256: digestForTest("foreground work reclaim"),
	}); err != nil {
		t.Fatal(err)
	}

	result, err := SuperviseRun(context.Background(), repository, foregroundIsolatedTestParams(
		"foreground_work_reclaim",
		"write",
		"reclaimed.txt",
		"reclaimed",
	))
	if err != nil {
		t.Fatal(err)
	}
	if result.Run.Status != RunSealed {
		t.Fatalf("reclaimed run = %#v, want sealed", result.Run)
	}
	staleWork, staleIntents, err := owner.GetWork(context.Background(), expired.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if staleWork.Status != WorkInterrupted || staleWork.RecoveryHold ||
		len(staleIntents) != 1 || staleIntents[0].Status != WriteIntentReleased {
		t.Fatalf("reconciled expired work = %#v intents=%#v", staleWork, staleIntents)
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
	case "block-after-write":
		if len(arguments) != 3 {
			os.Exit(99)
		}
		cwd, err := os.Getwd()
		if err != nil {
			os.Exit(100)
		}
		target := filepath.Join(cwd, filepath.FromSlash(arguments[1]))
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			os.Exit(101)
		}
		if err := os.WriteFile(target, []byte("partial"), 0o644); err != nil {
			os.Exit(102)
		}
		if err := os.WriteFile(arguments[2], []byte(cwd), 0o644); err != nil {
			os.Exit(103)
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

func requireSingleWorkForRun(t *testing.T, repository Repository, runID string, status WorkStatus) (WorkItem, []WriteIntent) {
	t.Helper()
	observer := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("work_observer_"+runID))
	items, err := observer.ListWork(context.Background(), ListWorkParams{Statuses: []WorkStatus{status}})
	if err != nil {
		t.Fatal(err)
	}
	matches := make([]WorkItem, 0, 1)
	for _, item := range items {
		if item.RunID == runID {
			matches = append(matches, item)
		}
	}
	if len(matches) != 1 {
		t.Fatalf("work items for run %q status %q = %#v, want one", runID, status, items)
	}
	work, intents, err := observer.GetWork(context.Background(), matches[0].WorkID)
	if err != nil {
		t.Fatal(err)
	}
	return work, intents
}

func waitForRunWork(t *testing.T, store *Store, runID string, status WorkStatus) WorkItem {
	t.Helper()
	deadline := time.Now().Add(10 * time.Second)
	for time.Now().Before(deadline) {
		items, err := store.ListWork(context.Background(), ListWorkParams{Statuses: []WorkStatus{status}})
		if err != nil {
			t.Fatal(err)
		}
		for _, item := range items {
			if item.RunID == runID {
				return item
			}
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("work item for run %q did not reach %q", runID, status)
	return WorkItem{}
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

func foregroundIsolatedTestParams(runID string, helperArguments ...string) SuperviseRunParams {
	params := foregroundTestParams(runID, helperArguments...)
	params.WorkspacePolicy = WorkspacePolicyIsolated
	return params
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

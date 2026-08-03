package runcontrol

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestPrimaryWorkspaceRoutingElectsExactlyOnePrimaryWinnerForConcurrentModifyingRuns(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	for _, runID := range []string{"routing_concurrent_a", "routing_concurrent_b"} {
		enqueueForegroundTestRun(t, repository, runID)
	}

	type completion struct {
		result SupervisedRun
		err    error
	}
	start := make(chan struct{})
	results := make(chan completion, 2)
	var wait sync.WaitGroup
	for index, runID := range []string{"routing_concurrent_a", "routing_concurrent_b"} {
		wait.Add(1)
		go func(index int, runID string) {
			defer wait.Done()
			<-start
			result, runErr := SuperviseRun(
				context.Background(),
				repository,
				foregroundTestParams(runID, "write", "routing-marker-"+string(rune('a'+index))+".txt", runID),
			)
			results <- completion{result: result, err: runErr}
		}(index, runID)
	}
	close(start)
	wait.Wait()
	close(results)

	primaryWinners := 0
	isolated := 0
	for completed := range results {
		if completed.err != nil {
			t.Fatalf("concurrent supervision error = %v", completed.err)
		}
		if completed.result.Workspace.RootPath == mainRoot {
			primaryWinners++
		} else {
			isolated++
		}
	}
	if primaryWinners != 1 || isolated != 1 {
		t.Fatalf("concurrent routing winners = %d primary / %d isolated, want exactly one primary winner and one isolated overlap", primaryWinners, isolated)
	}
}

func TestPrimaryWorkspaceRoutingReleasesPrimaryAfterTerminalLifecycle(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	t.Run("success", func(t *testing.T) {
		assertPrimarySlotReleasedAfterTerminalRun(t, "success", func(t *testing.T, repository Repository, runID string) (SupervisedRun, error) {
			return SuperviseRun(context.Background(), repository, foregroundTestParams(runID, "write", runID+"-marker.txt", runID))
		})
	})
	t.Run("failure", func(t *testing.T) {
		assertPrimarySlotReleasedAfterTerminalRun(t, "failure", func(t *testing.T, repository Repository, runID string) (SupervisedRun, error) {
			return SuperviseRun(context.Background(), repository, foregroundTestParams(runID, "fail", "7"))
		})
	})
	t.Run("cancel", func(t *testing.T) {
		mainRoot, _ := createLinkedRepository(t)
		repository, err := ResolveRepository(context.Background(), mainRoot)
		if err != nil {
			t.Fatal(err)
		}
		blocking := enqueueForegroundTestRun(t, repository, "routing_cancel_primary")
		cancelReady := filepath.Join(t.TempDir(), "cancel-ready")
		blocked := startBlockingRoutingRun(t, repository, blocking.RunID, cancelReady, "")
		if got := blocked.cwd(t); got != mainRoot {
			t.Fatalf("cancelled primary cwd = %q, want %q", got, mainRoot)
		}
		blocked.cancel()
		if finished := blocked.wait(t); !errors.Is(finished.err, context.Canceled) {
			t.Fatalf("cancelled primary run error = %v, want context.Canceled", finished.err)
		}

		follower := enqueueForegroundTestRun(t, repository, "routing_cancel_followup")
		next, err := SuperviseRun(context.Background(), repository, foregroundTestParams(follower.RunID, "write", "routing-cancel-followup.txt", follower.RunID))
		if err != nil {
			t.Fatal(err)
		}
		if next.Workspace.RootPath != mainRoot {
			t.Fatalf("post-cancel routing root = %q, want released primary root %q", next.Workspace.RootPath, mainRoot)
		}
	})
}

func TestPrimaryWorkspaceRoutingReleasesPrimaryAfterStaleSupervisorReconciliation(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	blocking := enqueueForegroundTestRun(t, repository, "routing_stale_primary")
	readyPath := filepath.Join(t.TempDir(), "stale-ready")
	ownerEpoch := "routing_stale_owner"
	blocked := startBlockingRoutingRun(t, repository, blocking.RunID, readyPath, ownerEpoch)
	defer blocked.stop(t)
	if got := blocked.cwd(t); got != mainRoot {
		t.Fatalf("stale-primary cwd = %q, want %q", got, mainRoot)
	}

	sweeper := openTestStore(t, repository.DatabasePath, WithOwnerEpoch("routing_stale_sweeper"))
	interrupted, err := reconcileStaleOwnerForTest(t, context.Background(), sweeper, ownerEpoch, time.Now().UTC())
	if err != nil {
		t.Fatal(err)
	}
	if len(interrupted) != 1 || interrupted[0].RunID != blocking.RunID || interrupted[0].Status != RunInterrupted {
		t.Fatalf("stale reconciliation = %#v, want one interrupted run for %q", interrupted, blocking.RunID)
	}

	follower := enqueueForegroundTestRun(t, repository, "routing_stale_followup")
	next, err := SuperviseRun(context.Background(), repository, foregroundTestParams(follower.RunID, "write", "routing-stale-followup.txt", follower.RunID))
	if err != nil {
		t.Fatal(err)
	}
	if next.Workspace.RootPath != mainRoot {
		t.Fatalf("post-stale routing root = %q, want released primary root %q", next.Workspace.RootPath, mainRoot)
	}
}

func TestPrimaryWorkspaceRoutingIsolatedOverlapUsesPrelaunchSnapshotNotInProgressPrimaryEdits(t *testing.T) {
	t.Setenv(foregroundHelperEnvironment, "1")
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	const prelaunchAmbient = "prelaunch ambient from primary source\n"
	const duringPrimaryAmbient = "in-progress primary edit\n"
	if err := os.WriteFile(filepath.Join(mainRoot, "README.md"), []byte(prelaunchAmbient), 0o644); err != nil {
		t.Fatal(err)
	}

	primary := enqueueForegroundTestRun(t, repository, "routing_overlay_primary")
	follower := enqueueForegroundTestRun(t, repository, "routing_overlay_follower")
	readyPath := filepath.Join(t.TempDir(), "overlay-ready")
	blocked := startBlockingRoutingRun(t, repository, primary.RunID, readyPath, "")
	defer blocked.stop(t)
	if got := blocked.cwd(t); got != mainRoot {
		t.Fatalf("overlay primary cwd = %q, want %q", got, mainRoot)
	}

	if err := os.WriteFile(filepath.Join(mainRoot, "README.md"), []byte(duringPrimaryAmbient), 0o644); err != nil {
		t.Fatal(err)
	}
	next, err := SuperviseRun(context.Background(), repository, foregroundTestParams(follower.RunID, "write", "routing-overlay-followup.txt", follower.RunID))
	if err != nil {
		t.Fatal(err)
	}
	if next.Workspace.RootPath == mainRoot {
		t.Fatalf("overlapping follower reused primary root %q, want isolated workspace", next.Workspace.RootPath)
	}
	content, err := os.ReadFile(filepath.Join(next.Workspace.RootPath, "README.md"))
	if err != nil {
		t.Fatal(err)
	}
	if got := string(content); got != prelaunchAmbient {
		t.Fatalf("isolated overlap README = %q, want prelaunch snapshot %q and never in-progress edit %q", got, prelaunchAmbient, duringPrimaryAmbient)
	}
}

type routingCompletion struct {
	result SupervisedRun
	err    error
}

type blockingRoutingRun struct {
	cancel    context.CancelFunc
	done      chan routingCompletion
	readyPath string
}

func startBlockingRoutingRun(t *testing.T, repository Repository, runID, readyPath, ownerEpoch string) blockingRoutingRun {
	t.Helper()
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan routingCompletion, 1)
	params := foregroundTestParams(runID, "block", readyPath)
	params.OwnerEpoch = ownerEpoch
	go func() {
		result, runErr := SuperviseRun(ctx, repository, params)
		done <- routingCompletion{result: result, err: runErr}
	}()
	waitForForegroundHelper(t, readyPath)
	return blockingRoutingRun{
		cancel:    cancel,
		done:      done,
		readyPath: readyPath,
	}
}

func (run blockingRoutingRun) cwd(t *testing.T) string {
	t.Helper()
	bytes, err := os.ReadFile(run.readyPath)
	if err != nil {
		t.Fatal(err)
	}
	return strings.TrimSpace(string(bytes))
}

func (run blockingRoutingRun) wait(t *testing.T) routingCompletion {
	t.Helper()
	select {
	case finished := <-run.done:
		return finished
	case <-time.After(10 * time.Second):
		t.Fatal("blocking routing run did not finish")
		return routingCompletion{}
	}
}

func (run blockingRoutingRun) stop(t *testing.T) {
	t.Helper()
	run.cancel()
	select {
	case <-run.done:
	case <-time.After(10 * time.Second):
		t.Fatal("blocking routing cleanup did not finish")
	}
}

func assertPrimarySlotReleasedAfterTerminalRun(
	t *testing.T,
	name string,
	runTerminal func(t *testing.T, repository Repository, runID string) (SupervisedRun, error),
) {
	t.Helper()
	mainRoot, _ := createLinkedRepository(t)
	repository, err := ResolveRepository(context.Background(), mainRoot)
	if err != nil {
		t.Fatal(err)
	}
	first := enqueueForegroundTestRun(t, repository, "routing_"+name+"_first")
	finished, err := runTerminal(t, repository, first.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if finished.Workspace.RootPath != mainRoot {
		t.Fatalf("%s primary root = %q, want %q", name, finished.Workspace.RootPath, mainRoot)
	}

	second := enqueueForegroundTestRun(t, repository, "routing_"+name+"_second")
	next, err := SuperviseRun(context.Background(), repository, foregroundTestParams(second.RunID, "write", "routing-"+name+"-followup.txt", second.RunID))
	if err != nil {
		t.Fatal(err)
	}
	if next.Workspace.RootPath != mainRoot {
		t.Fatalf("post-%s routing root = %q, want released primary root %q", name, next.Workspace.RootPath, mainRoot)
	}
}

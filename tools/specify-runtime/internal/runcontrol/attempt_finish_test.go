package runcontrol

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
	"time"
)

func TestFinishAttemptSealsSuccessfulExecutionAndFencesHeartbeat(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	run, attempt := activeManagedExecutionForFinishTest(t, store, "finish_success")

	finished, err := store.FinishAttempt(ctx, FinishAttemptParams{
		AttemptID: attempt.AttemptID,
		Fence:     attempt.Fence,
		Outcome:   AttemptOutcomeSucceeded,
		Reason:    "managed process exited successfully",
	})
	if err != nil {
		t.Fatal(err)
	}
	if finished.Run.Status != RunSealed || finished.Run.CurrentFence != attempt.Fence+1 || finished.Run.Revision != run.Revision+1 {
		t.Fatalf("finished run = %#v, want sealed with advanced fence and revision", finished.Run)
	}
	if finished.Attempt.Status != AttemptFinished || finished.Attempt.Revision != attempt.Revision+1 {
		t.Fatalf("finished attempt = %#v, want finished", finished.Attempt)
	}
	if finished.Activity.Status != ActivitySucceeded {
		t.Fatalf("finished activity = %#v, want succeeded", finished.Activity)
	}
	if finished.Workspace.Status != WorkspaceSealed {
		t.Fatalf("finished workspace = %#v, want sealed", finished.Workspace)
	}
	if _, err := store.Heartbeat(
		ctx,
		attempt.AttemptID,
		attempt.Fence,
		time.Now().UTC().Add(20*time.Minute),
	); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("heartbeat after finish error = %v, want ErrStaleFence", err)
	}

	replayed, err := store.FinishAttempt(ctx, FinishAttemptParams{
		AttemptID: attempt.AttemptID,
		Fence:     attempt.Fence,
		Outcome:   AttemptOutcomeSucceeded,
		Reason:    "managed process exited successfully",
	})
	if err != nil || replayed != finished {
		t.Fatalf("finish replay = %#v err=%v, want %#v", replayed, err, finished)
	}
}

func TestFinishAttemptFailureQuarantinesWorkspace(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	_, attempt := activeManagedExecutionForFinishTest(t, store, "finish_failure")

	finished, err := store.FinishAttempt(ctx, FinishAttemptParams{
		AttemptID: attempt.AttemptID,
		Fence:     attempt.Fence,
		Outcome:   AttemptOutcomeFailed,
		Reason:    "managed process exited with code 7",
	})
	if err != nil {
		t.Fatal(err)
	}
	if finished.Run.Status != RunFailed || finished.Run.CurrentFence != attempt.Fence+1 {
		t.Fatalf("failed run = %#v, want failed with advanced fence", finished.Run)
	}
	if finished.Attempt.Status != AttemptFailed || finished.Activity.Status != ActivityFailed {
		t.Fatalf("failed attempt/activity = %#v / %#v", finished.Attempt, finished.Activity)
	}
	if finished.Workspace.Status != WorkspaceQuarantined {
		t.Fatalf("failed workspace = %#v, want quarantined", finished.Workspace)
	}
	if _, err := store.FinishAttempt(ctx, FinishAttemptParams{
		AttemptID: attempt.AttemptID,
		Fence:     attempt.Fence,
		Outcome:   AttemptOutcomeSucceeded,
		Reason:    "conflicting retry",
	}); !errors.Is(err, ErrInvalidTransition) {
		t.Fatalf("conflicting finish retry error = %v, want ErrInvalidTransition", err)
	}
}

func TestFinishAttemptRejectsStaleSupervisor(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	owner := openTestStore(t, databasePath, WithOwnerEpoch("finish_owner"))
	_, attempt := activeManagedExecutionForFinishTest(t, owner, "finish_stale")
	other := openTestStore(t, databasePath, WithOwnerEpoch("finish_other"))

	if _, err := other.FinishAttempt(ctx, FinishAttemptParams{
		AttemptID: attempt.AttemptID,
		Fence:     attempt.Fence,
		Outcome:   AttemptOutcomeSucceeded,
		Reason:    "stale supervisor completion",
	}); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("stale supervisor finish error = %v, want ErrStaleFence", err)
	}
}

func activeManagedExecutionForFinishTest(t *testing.T, store *Store, suffix string) (Run, Attempt) {
	t.Helper()
	ctx := context.Background()
	_, attempt := issueManagedAttemptForLaunchTest(t, store, suffix)
	confirmManagedAttemptLaunchForTest(t, store, attempt)
	activeAttempt, err := store.ActivateAttempt(
		ctx,
		attempt.AttemptID,
		attempt.Fence,
		time.Now().UTC().Add(10*time.Minute),
	)
	if err != nil {
		t.Fatal(err)
	}
	activeRun, err := store.GetRun(ctx, attempt.RunID)
	if err != nil {
		t.Fatal(err)
	}
	return activeRun, activeAttempt
}

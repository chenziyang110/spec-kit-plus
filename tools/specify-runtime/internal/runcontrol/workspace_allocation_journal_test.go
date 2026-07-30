package runcontrol

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
	"time"
)

func TestWorkspaceAllocationJournalIsIdempotentBeforeAttemptIssuance(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	run, _, workspace := createAllocatingExecution(t, store, "allocation_journal", 1)
	request := BeginWorkspaceAllocationParams{
		AllocationID:              "allocation_journal_1",
		RunID:                     run.RunID,
		WorkspaceID:               workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedWorkspaceRevision: workspace.Revision,
		IdempotencyKey:            "allocate:" + run.RunID + ":1",
		RequestSHA256:             digestForTest("allocation journal request"),
	}

	created, replayed, err := store.BeginWorkspaceAllocation(ctx, request)
	if err != nil {
		t.Fatal(err)
	}
	if replayed || created.Status != WorkspaceAllocationPrepared || created.WorkspaceGeneration != 1 {
		t.Fatalf("created allocation = %#v replayed=%v", created, replayed)
	}
	if created.AttemptID != "" || created.Fence != 0 {
		t.Fatalf("pre-attempt allocation unexpectedly has attempt authority: %#v", created)
	}

	replayedAllocation, replayed, err := store.BeginWorkspaceAllocation(ctx, request)
	if err != nil {
		t.Fatal(err)
	}
	if !replayed || replayedAllocation != created {
		t.Fatalf("allocation replay = %#v replayed=%v, want %#v", replayedAllocation, replayed, created)
	}

	conflict := request
	conflict.RequestSHA256 = digestForTest("different allocation request")
	if _, _, err := store.BeginWorkspaceAllocation(ctx, conflict); !errors.Is(err, ErrIdempotencyConflict) {
		t.Fatalf("conflicting allocation replay error = %v, want ErrIdempotencyConflict", err)
	}
}

func TestCompleteWorkspaceAllocationAtomicallyReadiesExecution(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	run, activity, workspace := createAllocatingExecution(t, store, "allocation_complete", 1)
	allocation, _, err := store.BeginWorkspaceAllocation(ctx, BeginWorkspaceAllocationParams{
		AllocationID:              "allocation_complete_1",
		RunID:                     run.RunID,
		WorkspaceID:               workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedWorkspaceRevision: workspace.Revision,
		IdempotencyKey:            "allocate:" + run.RunID + ":1",
		RequestSHA256:             digestForTest("allocation complete request"),
	})
	if err != nil {
		t.Fatal(err)
	}
	allocation, err = store.StartWorkspaceAllocation(ctx, allocation.AllocationID, allocation.Revision)
	if err != nil {
		t.Fatal(err)
	}

	_, _, err = store.CompleteWorkspaceAllocation(ctx, CompleteWorkspaceAllocationParams{
		AllocationID:               allocation.AllocationID,
		ExpectedAllocationRevision: allocation.Revision,
		Execution: PrepareExecutionParams{
			RunID:                     run.RunID,
			ActivityID:                activity.ActivityID,
			WorkspaceID:               workspace.WorkspaceID,
			ExpectedRunRevision:       run.Revision,
			ExpectedActivityRevision:  activity.Revision,
			ExpectedWorkspaceRevision: workspace.Revision + 1,
		},
	})
	if !errors.Is(err, ErrRevisionConflict) {
		t.Fatalf("stale allocation completion error = %v, want ErrRevisionConflict", err)
	}
	unchanged, err := store.GetWorkspaceAllocation(ctx, allocation.AllocationID)
	if err != nil {
		t.Fatal(err)
	}
	if unchanged.Status != WorkspaceAllocationExecuting || unchanged.Revision != allocation.Revision {
		t.Fatalf("failed atomic completion changed allocation: %#v", unchanged)
	}
	assertExecutionStatuses(t, store, run.RunID, activity.ActivityID, workspace.WorkspaceID,
		RunAllocating, ActivityPlanned, WorkspaceAllocating)

	completed, prepared, err := store.CompleteWorkspaceAllocation(ctx, CompleteWorkspaceAllocationParams{
		AllocationID:               allocation.AllocationID,
		ExpectedAllocationRevision: allocation.Revision,
		Execution: PrepareExecutionParams{
			RunID:                     run.RunID,
			ActivityID:                activity.ActivityID,
			WorkspaceID:               workspace.WorkspaceID,
			ExpectedRunRevision:       run.Revision,
			ExpectedActivityRevision:  activity.Revision,
			ExpectedWorkspaceRevision: workspace.Revision,
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if completed.Status != WorkspaceAllocationSucceeded || completed.Revision != allocation.Revision+1 {
		t.Fatalf("completed allocation = %#v", completed)
	}
	if prepared.Run.Status != RunReady || prepared.Activity.Status != ActivityReady || prepared.Workspace.Status != WorkspaceReady {
		t.Fatalf("prepared execution = %#v", prepared)
	}
}

func TestClosingSupervisorMarksAllocationOutcomeUnknownAndQuarantinesWorkspace(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	store, err := Open(ctx, databasePath, WithOwnerEpoch("allocation_owner"))
	if err != nil {
		t.Fatal(err)
	}
	run, activity, workspace := createAllocatingExecution(t, store, "allocation_close", 1)
	allocation, _, err := store.BeginWorkspaceAllocation(ctx, BeginWorkspaceAllocationParams{
		AllocationID:              "allocation_close_1",
		RunID:                     run.RunID,
		WorkspaceID:               workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedWorkspaceRevision: workspace.Revision,
		IdempotencyKey:            "allocate:" + run.RunID + ":1",
		RequestSHA256:             digestForTest("allocation close request"),
	})
	if err != nil {
		t.Fatal(err)
	}
	allocation, err = store.StartWorkspaceAllocation(ctx, allocation.AllocationID, allocation.Revision)
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Close(); err != nil {
		t.Fatal(err)
	}

	reopened := openTestStore(t, databasePath, WithOwnerEpoch("allocation_recovery"))
	recovered, err := reopened.GetWorkspaceAllocation(ctx, allocation.AllocationID)
	if err != nil {
		t.Fatal(err)
	}
	if recovered.Status != WorkspaceAllocationOutcomeUnknown {
		t.Fatalf("recovered allocation status = %q, want outcome_unknown", recovered.Status)
	}
	assertExecutionStatuses(t, reopened, run.RunID, activity.ActivityID, workspace.WorkspaceID,
		RunInterrupted, ActivityInterrupted, WorkspaceQuarantined)
}

func TestWorkspaceAllocationCannotBeStartedByDifferentSupervisor(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	owner := openTestStore(t, databasePath, WithOwnerEpoch("allocation_original_owner"))
	run, _, workspace := createAllocatingExecution(t, owner, "allocation_owner", 1)
	allocation, _, err := owner.BeginWorkspaceAllocation(ctx, BeginWorkspaceAllocationParams{
		AllocationID:              "allocation_owner_1",
		RunID:                     run.RunID,
		WorkspaceID:               workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedWorkspaceRevision: workspace.Revision,
		IdempotencyKey:            "allocate:" + run.RunID + ":1",
		RequestSHA256:             digestForTest("allocation owner request"),
	})
	if err != nil {
		t.Fatal(err)
	}

	other := openTestStore(t, databasePath, WithOwnerEpoch("allocation_other_owner"))
	if _, err := other.StartWorkspaceAllocation(ctx, allocation.AllocationID, allocation.Revision); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("different supervisor start error = %v, want ErrStaleFence", err)
	}
}

func TestWorkspaceAllocationJournalSurvivesOwnerReconciliation(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	owner := openTestStore(t, databasePath, WithOwnerEpoch("allocation_stale_owner"))
	run, _, workspace := createAllocatingExecution(t, owner, "allocation_reconcile", 1)
	allocation, _, err := owner.BeginWorkspaceAllocation(ctx, BeginWorkspaceAllocationParams{
		AllocationID:              "allocation_reconcile_1",
		RunID:                     run.RunID,
		WorkspaceID:               workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedWorkspaceRevision: workspace.Revision,
		IdempotencyKey:            "allocate:" + run.RunID + ":1",
		RequestSHA256:             digestForTest("allocation reconcile request"),
	})
	if err != nil {
		t.Fatal(err)
	}
	allocation, err = owner.StartWorkspaceAllocation(ctx, allocation.AllocationID, allocation.Revision)
	if err != nil {
		t.Fatal(err)
	}

	takeover := openTestStore(t, databasePath, WithOwnerEpoch("allocation_takeover"))
	if _, err := takeover.ReconcileOwnerEpoch(ctx, time.Now().UTC()); err != nil {
		t.Fatal(err)
	}
	reconciled, err := takeover.GetWorkspaceAllocation(ctx, allocation.AllocationID)
	if err != nil {
		t.Fatal(err)
	}
	if reconciled.Status != WorkspaceAllocationOutcomeUnknown {
		t.Fatalf("reconciled allocation status = %q, want outcome_unknown", reconciled.Status)
	}
}

package runcontrol

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
	"time"
)

func TestReconcileStaleSupervisorsPreservesLiveParallelOwner(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	staleOwner := openTestStore(t, databasePath, WithOwnerEpoch("parallel_stale_owner"))
	staleRun, staleAttempt := createAuthorityActiveRun(t, staleOwner, "run_parallel_stale", time.Now().UTC())
	liveOwner := openTestStore(t, databasePath, WithOwnerEpoch("parallel_live_owner"))
	liveRun, liveAttempt := createAuthorityActiveRun(t, liveOwner, "run_parallel_live", time.Now().UTC())

	now := time.Now().UTC()
	staleBefore := now.Add(-30 * time.Second)
	if _, err := liveOwner.db.ExecContext(ctx, `
		UPDATE supervisor_instances
		SET heartbeat_at_ms = CASE owner_epoch
			WHEN ? THEN ?
			WHEN ? THEN ?
			ELSE heartbeat_at_ms
		END
		WHERE owner_epoch IN (?, ?)
	`, staleOwner.ownerEpoch, staleBefore.Add(-time.Second).UnixMilli(),
		liveOwner.ownerEpoch, now.UnixMilli(),
		staleOwner.ownerEpoch, liveOwner.ownerEpoch); err != nil {
		t.Fatal(err)
	}

	interrupted, err := liveOwner.ReconcileStaleSupervisors(ctx, now, staleBefore)
	if err != nil {
		t.Fatal(err)
	}
	if len(interrupted) != 1 || interrupted[0].RunID != staleRun.RunID || interrupted[0].Status != RunInterrupted {
		t.Fatalf("stale reconciliation = %#v, want only %q interrupted", interrupted, staleRun.RunID)
	}
	loadedLive, err := liveOwner.GetRun(ctx, liveRun.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if loadedLive.Status != RunActive || loadedLive.CurrentFence != liveAttempt.Fence {
		t.Fatalf("live parallel run changed during stale sweep: %#v", loadedLive)
	}
	if err := staleOwner.HeartbeatSupervisor(ctx, now.Add(time.Second)); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("superseded owner heartbeat error = %v, want ErrStaleFence", err)
	}
	if _, err := staleOwner.Heartbeat(
		ctx,
		staleAttempt.AttemptID,
		staleAttempt.Fence,
		now.Add(20*time.Minute),
	); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("superseded attempt heartbeat error = %v, want ErrStaleFence", err)
	}
	if err := liveOwner.HeartbeatSupervisor(ctx, now.Add(time.Second)); err != nil {
		t.Fatalf("live owner heartbeat failed after stale sweep: %v", err)
	}
	loadedStale, err := liveOwner.GetRun(ctx, staleRun.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := staleOwner.TransitionRun(
		ctx,
		loadedStale.RunID,
		loadedStale.Revision,
		RunReady,
		"superseded owner resume",
	); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("superseded owner resume error = %v, want ErrStaleFence", err)
	}
	queued, err := liveOwner.EnqueueRun(ctx, CreateRunParams{
		RunID:        "run_parallel_queued",
		Kind:         "sp-quick",
		SubjectType:  "quick",
		SubjectID:    "parallel-queued",
		TargetRef:    "main",
		IntentSHA256: digestForTest("parallel queued"),
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := staleOwner.ClaimRun(ctx, queued.RunID, queued.Revision); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("superseded owner claim error = %v, want ErrStaleFence", err)
	}
}

func TestReconcileStaleSupervisorInterruptsAllocatingRun(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	staleOwner := openTestStore(t, databasePath, WithOwnerEpoch("allocating_stale_owner"))
	queued, err := staleOwner.EnqueueRun(ctx, CreateRunParams{
		RunID:        "run_allocating_stale",
		Kind:         "sp-quick",
		SubjectType:  "quick",
		SubjectID:    "allocating-stale",
		TargetRef:    "main",
		IntentSHA256: digestForTest("allocating stale"),
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := staleOwner.ClaimRun(ctx, queued.RunID, queued.Revision); err != nil {
		t.Fatal(err)
	}
	sweeper := openTestStore(t, databasePath, WithOwnerEpoch("allocating_sweeper"))
	now := time.Now().UTC()
	staleBefore := now.Add(-30 * time.Second)
	if _, err := sweeper.db.ExecContext(ctx, `
		UPDATE supervisor_instances SET heartbeat_at_ms = ? WHERE owner_epoch = ?
	`, staleBefore.Add(-time.Second).UnixMilli(), staleOwner.ownerEpoch); err != nil {
		t.Fatal(err)
	}

	interrupted, err := sweeper.ReconcileStaleSupervisors(ctx, now, staleBefore)
	if err != nil {
		t.Fatal(err)
	}
	if len(interrupted) != 1 || interrupted[0].RunID != queued.RunID || interrupted[0].Status != RunInterrupted {
		t.Fatalf("allocating stale reconciliation = %#v", interrupted)
	}
	if interrupted[0].CurrentFence != 1 {
		t.Fatalf("interrupted allocating run fence = %d, want 1", interrupted[0].CurrentFence)
	}
}

func TestSupervisorHeartbeatIsMonotonic(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"), WithOwnerEpoch("heartbeat_owner"))
	later := time.Now().UTC().Add(time.Minute)
	if err := store.HeartbeatSupervisor(ctx, later); err != nil {
		t.Fatal(err)
	}
	if err := store.HeartbeatSupervisor(ctx, later.Add(-time.Minute)); err != nil {
		t.Fatal(err)
	}
	var heartbeatMS int64
	if err := store.db.QueryRowContext(ctx, `
		SELECT heartbeat_at_ms FROM supervisor_instances WHERE owner_epoch = ?
	`, store.ownerEpoch).Scan(&heartbeatMS); err != nil {
		t.Fatal(err)
	}
	if heartbeatMS != later.UnixMilli() {
		t.Fatalf("supervisor heartbeat = %d, want monotonic %d", heartbeatMS, later.UnixMilli())
	}
}

func TestSupersededSupervisorCannotIssueOrActivateAttempt(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	staleOwner := openTestStore(t, databasePath, WithOwnerEpoch("attempt_stale_owner"))
	liveOwner := openTestStore(t, databasePath, WithOwnerEpoch("attempt_live_owner"))
	prepared := createPreparedExecution(t, liveOwner, "attempt_stale_issue", 1)
	now := time.Now().UTC()
	if _, err := reconcileStaleOwnerForTest(t, ctx, liveOwner, staleOwner.ownerEpoch, now); err != nil {
		t.Fatal(err)
	}
	if _, err := staleOwner.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 "attempt_stale_issue_1",
		RunID:                     prepared.Run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       prepared.Run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "test",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(10 * time.Minute),
	}); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("superseded owner issue error = %v, want ErrStaleFence", err)
	}

	activationOwner := openTestStore(t, databasePath, WithOwnerEpoch("attempt_activation_owner"))
	_, attempt := issueManagedAttemptForLaunchTest(t, activationOwner, "stale_activation")
	confirmManagedAttemptLaunchForTest(t, activationOwner, attempt)
	if _, err := activationOwner.db.ExecContext(ctx, `
		UPDATE supervisor_instances SET status = 'superseded' WHERE owner_epoch = ?
	`, activationOwner.ownerEpoch); err != nil {
		t.Fatal(err)
	}
	if _, err := activationOwner.ActivateAttempt(
		ctx,
		attempt.AttemptID,
		attempt.Fence,
		now.Add(10*time.Minute),
	); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("superseded owner activation error = %v, want ErrStaleFence", err)
	}
}

func TestClosingSupervisorInterruptsReadyPreparationWithoutAttempt(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	owner, err := Open(ctx, databasePath, WithOwnerEpoch("ready_close_owner"))
	if err != nil {
		t.Fatal(err)
	}
	prepared := createPreparedExecution(t, owner, "ready_close", 1)
	if err := owner.Close(); err != nil {
		t.Fatal(err)
	}

	observer := openTestStore(t, databasePath, WithOwnerEpoch("ready_close_observer"))
	loadedRun, err := observer.GetRun(ctx, prepared.Run.RunID)
	if err != nil {
		t.Fatal(err)
	}
	loadedActivity, err := observer.GetActivity(ctx, prepared.Activity.ActivityID)
	if err != nil {
		t.Fatal(err)
	}
	loadedWorkspace, err := observer.GetWorkspace(ctx, prepared.Workspace.WorkspaceID)
	if err != nil {
		t.Fatal(err)
	}
	if loadedRun.Status != RunInterrupted || loadedRun.CurrentFence != 1 {
		t.Fatalf("ready run after owner close = %#v, want interrupted fence 1", loadedRun)
	}
	if loadedActivity.Status != ActivityInterrupted || loadedWorkspace.Status != WorkspaceQuarantined {
		t.Fatalf("ready execution after owner close = %#v / %#v", loadedActivity, loadedWorkspace)
	}
}

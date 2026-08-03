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
			heartbeat_at_ms
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

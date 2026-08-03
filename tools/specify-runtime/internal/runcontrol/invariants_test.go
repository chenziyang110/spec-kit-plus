package runcontrol

import (
	"context"
	"errors"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

func TestCanonicalLifecycleStatusValues(t *testing.T) {
	tests := map[string]string{
		"run active":          string(RunActive),
		"run parked":          string(RunParked),
		"attempt failed":      string(AttemptFailed),
		"operation executing": string(OperationExecuting),
	}
	wants := map[string]string{
		"run active":          "active",
		"run parked":          "parked",
		"attempt failed":      "failed",
		"operation executing": "executing",
	}
	for name, got := range tests {
		if got != wants[name] {
			t.Errorf("%s = %q, want %q", name, got, wants[name])
		}
	}
}

func TestSealingAttemptPreventsAnotherAttempt(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	prepared := createPreparedExecution(t, store, "sealing_live", 1)
	run := prepared.Run
	now := time.Now().UTC()

	if _, err := store.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 "att_sealing",
		RunID:                     run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(time.Minute),
	}); err != nil {
		t.Fatal(err)
	}
	if _, err := store.db.ExecContext(ctx, `
		UPDATE attempts SET status = ? WHERE attempt_id = ?
	`, AttemptSealing, "att_sealing"); err != nil {
		t.Fatal(err)
	}

	current, err := store.GetRun(ctx, run.RunID)
	if err != nil {
		t.Fatal(err)
	}
	_, err = store.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 "att_must_not_start",
		RunID:                     run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       current.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(time.Minute),
	})
	if !errors.Is(err, ErrLiveAttempt) {
		t.Fatalf("issue while sealing error = %v, want ErrLiveAttempt", err)
	}
}

func TestHeartbeatCannotResurrectExpiredLease(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	prepared := createPreparedExecution(t, store, "expired_heartbeat", 1)
	run := prepared.Run
	now := time.Now().UTC()
	attempt, err := store.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 "att_expired_heartbeat",
		RunID:                     run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(time.Minute),
	})
	if err != nil {
		t.Fatal(err)
	}
	confirmManagedAttemptLaunchForTest(t, store, attempt)
	if _, err := store.ActivateAttempt(ctx, attempt.AttemptID, attempt.Fence, now.Add(time.Minute)); err != nil {
		t.Fatal(err)
	}
	if _, err := store.db.ExecContext(ctx, `
		UPDATE attempts SET lease_until_ms = ? WHERE attempt_id = ?
	`, now.Add(-time.Minute).UnixMilli(), attempt.AttemptID); err != nil {
		t.Fatal(err)
	}
	if _, err := store.Heartbeat(ctx, attempt.AttemptID, attempt.Fence, time.Now().UTC().Add(time.Minute)); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("expired lease heartbeat error = %v, want ErrStaleFence", err)
	}
}

func TestActivateCannotResurrectExpiredIssuedLease(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	prepared := createPreparedExecution(t, store, "expired_activation", 1)
	run := prepared.Run
	now := time.Now().UTC()
	attempt, err := store.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 "att_expired_activation",
		RunID:                     run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(time.Minute),
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := store.db.ExecContext(ctx, `
		UPDATE attempts SET lease_until_ms = ? WHERE attempt_id = ?
	`, now.Add(-time.Minute).UnixMilli(), attempt.AttemptID); err != nil {
		t.Fatal(err)
	}
	if _, err := store.ActivateAttempt(ctx, attempt.AttemptID, attempt.Fence, now.Add(time.Minute)); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("expired lease activation error = %v, want ErrStaleFence", err)
	}
}

func TestConcurrentOperationRetryReturnsReplay(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	store := openTestStore(t, databasePath)
	active, attempt := createAuthorityActiveRun(t, store, "run_concurrent_operation", time.Now().UTC())
	stores := []*Store{store, store}
	request := BeginOperationParams{
		OperationID:         "op_concurrent",
		Kind:                "command.execute",
		AggregateType:       "run",
		AggregateID:         active.RunID,
		RunID:               active.RunID,
		AttemptID:           attempt.AttemptID,
		Fence:               attempt.Fence,
		ExpectedRunRevision: active.Revision,
		IdempotencyKey:      "command/run_concurrent_operation/1",
		RequestSHA256:       digestForTest("concurrent-operation"),
	}

	type result struct {
		replayed bool
		err      error
	}
	start := make(chan struct{})
	results := make(chan result, len(stores))
	var wait sync.WaitGroup
	for _, store := range stores {
		wait.Add(1)
		go func(store *Store) {
			defer wait.Done()
			<-start
			_, replayed, err := store.BeginOperation(ctx, request)
			results <- result{replayed: replayed, err: err}
		}(store)
	}
	close(start)
	wait.Wait()
	close(results)

	created, replayed := 0, 0
	for result := range results {
		if result.err != nil {
			t.Fatalf("concurrent operation error = %v, want an idempotent replay", result.err)
		}
		if result.replayed {
			replayed++
		} else {
			created++
		}
	}
	if created != 1 || replayed != 1 {
		t.Fatalf("concurrent operation results: created=%d replayed=%d, want 1 and 1", created, replayed)
	}
}

func TestOperationRetryMayProposeDifferentOperationID(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	active, attempt := createAuthorityActiveRun(t, store, "run_operation_identity", time.Now().UTC())
	request := BeginOperationParams{
		OperationID:         "op_original",
		Kind:                "command.execute",
		AggregateType:       "run",
		AggregateID:         active.RunID,
		RunID:               active.RunID,
		AttemptID:           attempt.AttemptID,
		Fence:               attempt.Fence,
		ExpectedRunRevision: active.Revision,
		IdempotencyKey:      "command/run_operation_identity/1",
		RequestSHA256:       digestForTest("same-request"),
	}
	first, replayed, err := store.BeginOperation(ctx, request)
	if err != nil || replayed {
		t.Fatalf("first operation = %#v replayed=%v err=%v", first, replayed, err)
	}

	request.OperationID = "op_retry_generated_id"
	second, replayed, err := store.BeginOperation(ctx, request)
	if err != nil {
		t.Fatal(err)
	}
	if !replayed || second.OperationID != first.OperationID {
		t.Fatalf("retry = %#v replayed=%v, want original operation replay", second, replayed)
	}
}

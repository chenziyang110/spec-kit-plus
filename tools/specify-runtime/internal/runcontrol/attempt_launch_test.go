package runcontrol

import (
	"context"
	"database/sql"
	"path/filepath"
	"testing"
	"time"
)

func TestAttemptLaunchOperationHasOneLiveClaimPerAttempt(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	run, attempt := issueManagedAttemptForLaunchTest(t, store, "launch_unique")

	insertAttemptLaunchOperation(t, store, run, attempt, "launch_unique_a", OperationExecuting)
	_, err := store.db.ExecContext(ctx, `
		INSERT INTO operations (
			operation_id, kind, aggregate_type, aggregate_id,
			run_id, attempt_id, activity_id, workspace_id,
			owner_epoch, fence, run_revision,
			idempotency_key, request_sha256, status, revision,
			created_at_ms, updated_at_ms
		) VALUES (?, 'attempt.launch', 'workspace', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
	`, "launch_unique_b", attempt.WorkspaceID, run.RunID, attempt.AttemptID,
		attempt.ActivityID, attempt.WorkspaceID, store.ownerEpoch, attempt.Fence,
		run.Revision, "launch:unique:b", digestForTest("launch unique b"),
		OperationExecuting, time.Now().UTC().UnixMilli(), time.Now().UTC().UnixMilli())
	if err == nil {
		t.Fatal("second live attempt.launch operation unexpectedly succeeded")
	}
}

func TestClosingSupervisorMarksAttemptLaunchOutcomeUnknown(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	store, err := Open(ctx, databasePath, WithOwnerEpoch("launch_close_owner"))
	if err != nil {
		t.Fatal(err)
	}
	run, attempt := issueManagedAttemptForLaunchTest(t, store, "launch_close")
	insertAttemptLaunchOperation(t, store, run, attempt, "launch_close_operation", OperationSucceeded)

	if err := store.Close(); err != nil {
		t.Fatal(err)
	}
	database, err := sql.Open("sqlite", databasePath)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = database.Close() }()
	var status OperationStatus
	if err := database.QueryRowContext(ctx, `
		SELECT status FROM operations WHERE operation_id = 'launch_close_operation'
	`).Scan(&status); err != nil {
		t.Fatal(err)
	}
	if status != OperationOutcomeUnknown {
		t.Fatalf("launch operation status after supervisor close = %q, want %q", status, OperationOutcomeUnknown)
	}
}

func TestClosingActiveAttemptPreservesConfirmedLaunchOutcome(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	store, err := Open(ctx, databasePath, WithOwnerEpoch("launch_active_close_owner"))
	if err != nil {
		t.Fatal(err)
	}
	run, attempt := issueManagedAttemptForLaunchTest(t, store, "launch_active_close")
	insertAttemptLaunchOperation(t, store, run, attempt, "launch_active_close_operation", OperationSucceeded)
	if _, err := store.ActivateAttempt(
		ctx,
		attempt.AttemptID,
		attempt.Fence,
		time.Now().UTC().Add(10*time.Minute),
	); err != nil {
		t.Fatal(err)
	}
	if err := store.Close(); err != nil {
		t.Fatal(err)
	}

	database, err := sql.Open("sqlite", databasePath)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = database.Close() }()
	var status OperationStatus
	if err := database.QueryRowContext(ctx, `
		SELECT status FROM operations WHERE operation_id = 'launch_active_close_operation'
	`).Scan(&status); err != nil {
		t.Fatal(err)
	}
	if status != OperationSucceeded {
		t.Fatalf("confirmed launch operation after active shutdown = %q, want %q", status, OperationSucceeded)
	}
}

func issueManagedAttemptForLaunchTest(t *testing.T, store *Store, suffix string) (Run, Attempt) {
	t.Helper()
	ctx := context.Background()
	prepared := createPreparedExecution(t, store, suffix, 1)
	attempt, err := store.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 "attempt_" + suffix,
		RunID:                     prepared.Run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       prepared.Run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                time.Now().UTC().Add(10 * time.Minute),
	})
	if err != nil {
		t.Fatal(err)
	}
	run, err := store.GetRun(ctx, prepared.Run.RunID)
	if err != nil {
		t.Fatal(err)
	}
	return run, attempt
}

func insertAttemptLaunchOperation(
	t *testing.T,
	store *Store,
	run Run,
	attempt Attempt,
	operationID string,
	status OperationStatus,
) {
	t.Helper()
	nowMS := time.Now().UTC().UnixMilli()
	_, err := store.db.Exec(`
		INSERT INTO operations (
			operation_id, kind, aggregate_type, aggregate_id,
			run_id, attempt_id, activity_id, workspace_id,
			owner_epoch, fence, run_revision,
			idempotency_key, request_sha256, status, revision,
			created_at_ms, updated_at_ms
		) VALUES (?, 'attempt.launch', 'workspace', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
	`, operationID, attempt.WorkspaceID, run.RunID, attempt.AttemptID,
		attempt.ActivityID, attempt.WorkspaceID, store.ownerEpoch, attempt.Fence,
		run.Revision, "launch:"+operationID, digestForTest(operationID), status, nowMS, nowMS)
	if err != nil {
		t.Fatal(err)
	}
}

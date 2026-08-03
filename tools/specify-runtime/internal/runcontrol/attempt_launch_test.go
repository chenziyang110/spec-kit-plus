package runcontrol

import (
	"context"
	"database/sql"
	"errors"
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

func TestManagedAttemptActivationRequiresSucceededLaunchJournal(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	_, attempt := issueManagedAttemptForLaunchTest(t, store, "launch_activation_gate")

	if _, err := store.ActivateAttempt(
		ctx,
		attempt.AttemptID,
		attempt.Fence,
		time.Now().UTC().Add(10*time.Minute),
	); !errors.Is(err, ErrInvalidTransition) {
		t.Fatalf("activation without launch journal error = %v, want ErrInvalidTransition", err)
	}

	failed, replayed, err := store.BeginAttemptLaunch(ctx, BeginAttemptLaunchParams{
		OperationID:    "launch_activation_failed",
		AttemptID:      attempt.AttemptID,
		Fence:          attempt.Fence,
		IdempotencyKey: "launch:activation:failed",
		RequestSHA256:  digestForTest("launch activation failed"),
	})
	if err != nil || replayed {
		t.Fatalf("begin failed launch = %#v replayed=%v err=%v", failed, replayed, err)
	}
	replayedLaunch, replayed, err := store.BeginAttemptLaunch(ctx, BeginAttemptLaunchParams{
		OperationID:    "launch_activation_failed",
		AttemptID:      attempt.AttemptID,
		Fence:          attempt.Fence,
		IdempotencyKey: "launch:activation:failed",
		RequestSHA256:  digestForTest("launch activation failed"),
	})
	if err != nil || !replayed || replayedLaunch != failed {
		t.Fatalf("launch replay = %#v replayed=%v err=%v, want %#v", replayedLaunch, replayed, err, failed)
	}
	failed, err = store.CompleteAttemptLaunch(ctx, CompleteAttemptLaunchParams{
		OperationID:      failed.OperationID,
		Fence:            attempt.Fence,
		ExpectedRevision: failed.Revision,
		Succeeded:        false,
	})
	if err != nil || failed.Status != OperationFailed {
		t.Fatalf("failed launch completion = %#v err=%v", failed, err)
	}
	if _, err := store.ActivateAttempt(
		ctx,
		attempt.AttemptID,
		attempt.Fence,
		time.Now().UTC().Add(10*time.Minute),
	); !errors.Is(err, ErrInvalidTransition) {
		t.Fatalf("activation after failed launch error = %v, want ErrInvalidTransition", err)
	}

	succeeded, _, err := store.BeginAttemptLaunch(ctx, BeginAttemptLaunchParams{
		OperationID:    "launch_activation_succeeded",
		AttemptID:      attempt.AttemptID,
		Fence:          attempt.Fence,
		IdempotencyKey: "launch:activation:succeeded",
		RequestSHA256:  digestForTest("launch activation succeeded"),
	})
	if err != nil {
		t.Fatal(err)
	}
	succeeded, err = store.CompleteAttemptLaunch(ctx, CompleteAttemptLaunchParams{
		OperationID:      succeeded.OperationID,
		Fence:            attempt.Fence,
		ExpectedRevision: succeeded.Revision,
		Succeeded:        true,
	})
	if err != nil || succeeded.Status != OperationSucceeded {
		t.Fatalf("succeeded launch completion = %#v err=%v", succeeded, err)
	}
	active, err := store.ActivateAttempt(
		ctx,
		attempt.AttemptID,
		attempt.Fence,
		time.Now().UTC().Add(10*time.Minute),
	)
	if err != nil || active.Status != AttemptActive {
		t.Fatalf("managed activation after launch = %#v err=%v", active, err)
	}
}

func TestAttemptLaunchClaimRejectsConcurrentAndStaleSupervisor(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	owner := openTestStore(t, databasePath, WithOwnerEpoch("launch_api_owner"))
	_, attempt := issueManagedAttemptForLaunchTest(t, owner, "launch_api_authority")
	claim, _, err := owner.BeginAttemptLaunch(ctx, BeginAttemptLaunchParams{
		OperationID:    "launch_api_claim",
		AttemptID:      attempt.AttemptID,
		Fence:          attempt.Fence,
		IdempotencyKey: "launch:api:claim",
		RequestSHA256:  digestForTest("launch api claim"),
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, _, err := owner.BeginAttemptLaunch(ctx, BeginAttemptLaunchParams{
		OperationID:    "launch_api_duplicate",
		AttemptID:      attempt.AttemptID,
		Fence:          attempt.Fence,
		IdempotencyKey: "launch:api:duplicate",
		RequestSHA256:  digestForTest("launch api duplicate"),
	}); !errors.Is(err, ErrAlreadyExists) {
		t.Fatalf("concurrent launch claim error = %v, want ErrAlreadyExists", err)
	}

	other := openTestStore(t, databasePath, WithOwnerEpoch("launch_api_other"))
	if _, err := other.CompleteAttemptLaunch(ctx, CompleteAttemptLaunchParams{
		OperationID:      claim.OperationID,
		Fence:            attempt.Fence,
		ExpectedRevision: claim.Revision,
		Succeeded:        true,
	}); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("stale supervisor launch completion error = %v, want ErrStaleFence", err)
	}
}

func TestAttemptLaunchCompletionReplaySurvivesActivation(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	_, attempt := issueManagedAttemptForLaunchTest(t, store, "launch_completion_replay")
	claim, _, err := store.BeginAttemptLaunch(ctx, BeginAttemptLaunchParams{
		OperationID:    "launch_completion_replay_claim",
		AttemptID:      attempt.AttemptID,
		Fence:          attempt.Fence,
		IdempotencyKey: "launch:completion:replay",
		RequestSHA256:  digestForTest("launch completion replay"),
	})
	if err != nil {
		t.Fatal(err)
	}
	completed, err := store.CompleteAttemptLaunch(ctx, CompleteAttemptLaunchParams{
		OperationID:      claim.OperationID,
		Fence:            attempt.Fence,
		ExpectedRevision: claim.Revision,
		Succeeded:        true,
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := store.ActivateAttempt(
		ctx,
		attempt.AttemptID,
		attempt.Fence,
		time.Now().UTC().Add(10*time.Minute),
	); err != nil {
		t.Fatal(err)
	}

	replayed, err := store.CompleteAttemptLaunch(ctx, CompleteAttemptLaunchParams{
		OperationID:      claim.OperationID,
		Fence:            attempt.Fence,
		ExpectedRevision: claim.Revision,
		Succeeded:        true,
	})
	if err != nil || replayed != completed {
		t.Fatalf("completion replay after activation = %#v err=%v, want %#v", replayed, err, completed)
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

func confirmManagedAttemptLaunchForTest(t *testing.T, store *Store, attempt Attempt) Operation {
	t.Helper()
	ctx := context.Background()
	operation, replayed, err := store.BeginAttemptLaunch(ctx, BeginAttemptLaunchParams{
		OperationID:    "launch_for_" + attempt.AttemptID,
		AttemptID:      attempt.AttemptID,
		Fence:          attempt.Fence,
		IdempotencyKey: "launch:for:" + attempt.AttemptID,
		RequestSHA256:  digestForTest("launch for " + attempt.AttemptID),
	})
	if err != nil || replayed {
		t.Fatalf("begin managed launch for %q = %#v replayed=%v err=%v", attempt.AttemptID, operation, replayed, err)
	}
	operation, err = store.CompleteAttemptLaunch(ctx, CompleteAttemptLaunchParams{
		OperationID:      operation.OperationID,
		Fence:            attempt.Fence,
		ExpectedRevision: operation.Revision,
		Succeeded:        true,
	})
	if err != nil || operation.Status != OperationSucceeded {
		t.Fatalf("complete managed launch for %q = %#v err=%v", attempt.AttemptID, operation, err)
	}
	return operation
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

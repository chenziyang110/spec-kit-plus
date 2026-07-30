package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestGenericTransitionsCannotExerciseAttemptAuthority(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.db"))

	ready := createReadyRun(t, store, "run_transition_authority_ready")
	if _, err := store.TransitionRun(ctx, ready.RunID, ready.Revision, RunActive, "bypass attempt activation"); !errors.Is(err, ErrInvalidTransition) {
		t.Fatalf("ready -> active error = %v, want ErrInvalidTransition", err)
	}

	active, _ := createAuthorityActiveRun(t, store, "run_transition_authority_active", time.Now().UTC())
	if _, err := store.TransitionRun(ctx, active.RunID, active.Revision, RunFailed, "bypass attempt failure"); !errors.Is(err, ErrInvalidTransition) {
		t.Fatalf("active -> failed error = %v, want ErrInvalidTransition", err)
	}
}

func TestBeginOperationRequiresCurrentAttemptAuthority(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.db"))
	active, attempt := createAuthorityActiveRun(t, store, "run_operation_authority", time.Now().UTC())

	request := BeginOperationParams{
		OperationID:         "op_authorized",
		Kind:                "workspace.create",
		AggregateType:       "run",
		AggregateID:         active.RunID,
		IdempotencyKey:      "idem_authorized",
		RequestSHA256:       digestForTest("authorized operation"),
		RunID:               active.RunID,
		AttemptID:           attempt.AttemptID,
		Fence:               attempt.Fence,
		ExpectedRunRevision: active.Revision,
	}
	if _, replayed, err := store.BeginOperation(ctx, request); err != nil || replayed {
		t.Fatalf("authorized BeginOperation() = replayed %v, error %v", replayed, err)
	}

	cancelled, err := store.CancelRun(ctx, active.RunID, active.Revision, "cancel before next side effect")
	if err != nil {
		t.Fatalf("CancelRun() error = %v", err)
	}
	if cancelled.CurrentFence <= attempt.Fence {
		t.Fatalf("cancelled fence = %d, want greater than %d", cancelled.CurrentFence, attempt.Fence)
	}

	request.OperationID = "op_stale"
	request.IdempotencyKey = "idem_stale"
	request.RequestSHA256 = digestForTest("stale operation")
	if _, _, err := store.BeginOperation(ctx, request); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("stale BeginOperation() error = %v, want ErrStaleFence", err)
	}
}

func TestDuplicateLiveOwnerEpochIsRejected(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.db")
	first := openTestStore(t, databasePath, WithOwnerEpoch("supervisor_duplicate"))
	if first == nil {
		t.Fatal("first Open() returned nil store")
	}

	second, err := Open(ctx, databasePath, WithOwnerEpoch("supervisor_duplicate"))
	if second != nil {
		_ = second.Close()
	}
	if !errors.Is(err, ErrOwnerEpochConflict) {
		t.Fatalf("second Open() error = %v, want ErrOwnerEpochConflict", err)
	}
}

func TestReconcileOwnerEpochInterruptsStaleAllocatingRun(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.db")
	first := openTestStore(t, databasePath, WithOwnerEpoch("supervisor_allocating_old"))
	created, err := first.CreateRun(ctx, CreateRunParams{
		RunID:        "run_stale_allocating",
		Kind:         "sp-quick",
		SubjectType:  "feature",
		SubjectID:    "stale-allocating",
		TargetRef:    "main",
		IntentSHA256: digestForTest("stale allocating"),
	})
	if err != nil {
		t.Fatalf("CreateRun() error = %v", err)
	}

	second := openTestStore(t, databasePath, WithOwnerEpoch("supervisor_allocating_new"))
	interrupted, err := second.ReconcileOwnerEpoch(ctx, time.Now().UTC())
	if err != nil {
		t.Fatalf("ReconcileOwnerEpoch() error = %v", err)
	}
	if len(interrupted) != 1 || interrupted[0].RunID != created.RunID {
		t.Fatalf("interrupted = %+v, want only %q", interrupted, created.RunID)
	}
	if interrupted[0].Status != RunInterrupted || interrupted[0].CurrentFence != created.CurrentFence+1 {
		t.Fatalf("reconciled run = %+v, want interrupted with bumped fence", interrupted[0])
	}
}

func TestCloseInterruptsAndFencesOwnedActiveAttempt(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.db")
	first, err := Open(ctx, databasePath, WithOwnerEpoch("supervisor_closing"))
	if err != nil {
		t.Fatalf("Open(first) error = %v", err)
	}
	active, attempt := createAuthorityActiveRun(t, first, "run_close_fence", time.Now().UTC())
	if err := first.Close(); err != nil {
		t.Fatalf("Close(first) error = %v", err)
	}

	second := openTestStore(t, databasePath, WithOwnerEpoch("supervisor_after_close"))
	reopened, err := second.GetRun(ctx, active.RunID)
	if err != nil {
		t.Fatalf("GetRun() after reopen error = %v", err)
	}
	if reopened.Status != RunInterrupted || reopened.CurrentFence <= attempt.Fence {
		t.Fatalf("run after owner close = %+v, want interrupted with fence greater than %d", reopened, attempt.Fence)
	}
}

func TestOpenRejectsUnsupportedSchemaVersion(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.db")
	db, err := sql.Open("sqlite", databasePath)
	if err != nil {
		t.Fatalf("sql.Open() error = %v", err)
	}
	if _, err := db.Exec(`CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)`); err != nil {
		t.Fatalf("create metadata error = %v", err)
	}
	if _, err := db.Exec(`INSERT INTO metadata (key, value) VALUES ('schema_version', '999')`); err != nil {
		t.Fatalf("insert schema version error = %v", err)
	}
	if err := db.Close(); err != nil {
		t.Fatalf("close fixture database error = %v", err)
	}

	store, err := Open(ctx, databasePath, WithOwnerEpoch("supervisor_unsupported_schema"))
	if store != nil {
		_ = store.Close()
	}
	if !errors.Is(err, ErrUnsupportedSchema) {
		t.Fatalf("Open() error = %v, want ErrUnsupportedSchema", err)
	}
}

func TestSQLiteSynchronousModeIsFull(t *testing.T) {
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.db"))
	var synchronous int
	if err := store.db.QueryRow(`PRAGMA synchronous`).Scan(&synchronous); err != nil {
		t.Fatalf("read PRAGMA synchronous error = %v", err)
	}
	if synchronous != 2 {
		t.Fatalf("PRAGMA synchronous = %d, want 2 (FULL)", synchronous)
	}
}

func TestHeartbeatCannotShortenLease(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.db"))
	now := time.Now().UTC()
	_, attempt := createAuthorityActiveRun(t, store, "run_lease_monotonic", now)

	shorter := time.UnixMilli(attempt.LeaseUntilMS).UTC().Add(-time.Minute)
	if _, err := store.Heartbeat(ctx, attempt.AttemptID, attempt.Fence, shorter); !errors.Is(err, ErrInvalidArgument) {
		t.Fatalf("shortening Heartbeat() error = %v, want ErrInvalidArgument", err)
	}
}

func TestCancelRacesHeartbeatWithoutUntypedFailure(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.db"))
	now := time.Now().UTC()
	active, attempt := createAuthorityActiveRun(t, store, "run_cancel_heartbeat_race", now)

	start := make(chan struct{})
	errorsByOperation := make(chan error, 2)
	var workers sync.WaitGroup
	workers.Add(2)
	go func() {
		defer workers.Done()
		<-start
		_, err := store.CancelRun(ctx, active.RunID, active.Revision, "race cancellation")
		errorsByOperation <- err
	}()
	go func() {
		defer workers.Done()
		<-start
		_, err := store.Heartbeat(ctx, attempt.AttemptID, attempt.Fence, now.Add(20*time.Minute))
		errorsByOperation <- err
	}()
	close(start)
	workers.Wait()
	close(errorsByOperation)

	for err := range errorsByOperation {
		if err != nil && !errors.Is(err, ErrStaleFence) {
			t.Fatalf("race error = %v, want nil or ErrStaleFence", err)
		}
	}
	finalRun, err := store.GetRun(ctx, active.RunID)
	if err != nil {
		t.Fatalf("GetRun() error = %v", err)
	}
	if finalRun.Status != RunCancelled {
		t.Fatalf("final run status = %q, want %q", finalRun.Status, RunCancelled)
	}
}

func createAuthorityActiveRun(t *testing.T, store *Store, runID string, now time.Time) (Run, Attempt) {
	t.Helper()
	ctx := context.Background()
	prepared := createPreparedExecution(t, store, strings.TrimPrefix(runID, "run_"), 1)
	attempt, err := store.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 runID + "_attempt",
		RunID:                     prepared.Run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       prepared.Run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(10 * time.Minute),
	})
	if err != nil {
		t.Fatalf("IssueAttempt() error = %v", err)
	}
	attempt, err = store.ActivateAttempt(ctx, attempt.AttemptID, attempt.Fence, now.Add(10*time.Minute))
	if err != nil {
		t.Fatalf("ActivateAttempt() error = %v", err)
	}
	active, err := store.GetRun(ctx, prepared.Run.RunID)
	if err != nil {
		t.Fatalf("GetRun(active) error = %v", err)
	}
	return active, attempt
}

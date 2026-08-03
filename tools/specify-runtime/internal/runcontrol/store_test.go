package runcontrol

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

func TestRunTransitionsRequireExpectedRevision(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))

	run, err := store.CreateRun(ctx, CreateRunParams{
		RunID:        "run_revision",
		Kind:         "feature",
		SubjectType:  "feature",
		SubjectID:    "001-revision",
		TargetRef:    "refs/heads/main",
		IntentSHA256: digestForTest("revision"),
	})
	if err != nil {
		t.Fatal(err)
	}
	if run.Status != RunAllocating || run.Revision != 1 || run.CurrentFence != 0 {
		t.Fatalf("created run = %#v, want allocating revision 1 fence 0", run)
	}

	if _, err := store.TransitionRun(ctx, run.RunID, 1, RunSealed, "skip readiness"); !errors.Is(err, ErrInvalidTransition) {
		t.Fatalf("allocating -> sealed error = %v, want ErrInvalidTransition", err)
	}

	ready, err := store.TransitionRun(ctx, run.RunID, 1, RunReady, "snapshot ready")
	if err != nil {
		t.Fatal(err)
	}
	if ready.Status != RunReady || ready.Revision != 2 {
		t.Fatalf("ready run = %#v, want ready revision 2", ready)
	}

	if _, err := store.TransitionRun(ctx, run.RunID, 1, RunCancelled, "stale writer"); !errors.Is(err, ErrRevisionConflict) {
		t.Fatalf("stale transition error = %v, want ErrRevisionConflict", err)
	}
	if _, err := store.TransitionRun(ctx, run.RunID, 2, RunStatus("invented"), "unknown state"); !errors.Is(err, ErrInvalidTransition) {
		t.Fatalf("unknown transition error = %v, want ErrInvalidTransition", err)
	}
}

func TestCancelInvalidatesTheLiveAttemptFenceBeforeHeartbeat(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	prepared := createPreparedExecution(t, store, "cancel", 1)
	run := prepared.Run
	now := time.Now().UTC()

	attempt, err := store.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 "att_cancel_1",
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
	if attempt.Fence != 1 || attempt.Status != AttemptIssued {
		t.Fatalf("issued attempt = %#v, want fence 1 issued", attempt)
	}
	confirmManagedAttemptLaunchForTest(t, store, attempt)
	if _, err := store.ActivateAttempt(ctx, attempt.AttemptID, attempt.Fence, now.Add(time.Minute)); err != nil {
		t.Fatal(err)
	}

	cancelled, err := store.CancelRun(ctx, run.RunID, run.Revision+2, "user cancelled")
	if err != nil {
		t.Fatal(err)
	}
	if cancelled.Status != RunCancelled || cancelled.CurrentFence != 2 {
		t.Fatalf("cancelled run = %#v, want cancelled fence 2", cancelled)
	}
	if _, err := store.Heartbeat(ctx, attempt.AttemptID, attempt.Fence, now.Add(2*time.Minute)); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("old-fence heartbeat error = %v, want ErrStaleFence", err)
	}
}

func TestOnlyOneConcurrentAttemptCanBecomeLive(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	firstStore := openTestStore(t, databasePath)
	prepared := createPreparedExecution(t, firstStore, "concurrent", 1)
	run := prepared.Run
	secondStore := openTestStore(t, databasePath)
	now := time.Now().UTC()

	start := make(chan struct{})
	results := make(chan error, 2)
	var wait sync.WaitGroup
	for index, store := range []*Store{firstStore, secondStore} {
		wait.Add(1)
		go func(index int, store *Store) {
			defer wait.Done()
			<-start
			_, err := store.IssueAttempt(ctx, IssueAttemptParams{
				AttemptID:                 []string{"att_concurrent_a", "att_concurrent_b"}[index],
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
			results <- err
		}(index, store)
	}
	close(start)
	wait.Wait()
	close(results)

	successes := 0
	conflicts := 0
	for err := range results {
		switch {
		case err == nil:
			successes++
		case errors.Is(err, ErrLiveAttempt), errors.Is(err, ErrRevisionConflict):
			conflicts++
		default:
			t.Fatalf("concurrent issue error = %v, want nil or a typed conflict", err)
		}
	}
	if successes != 1 || conflicts != 1 {
		t.Fatalf("concurrent issue results: successes=%d conflicts=%d, want 1 and 1", successes, conflicts)
	}
}

func TestExpiredLeaseInterruptsRunAndInvalidatesFence(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	prepared := createPreparedExecution(t, store, "expiry", 1)
	run := prepared.Run
	now := time.Now().UTC()
	attempt, err := store.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 "att_expiry_1",
		RunID:                     run.RunID,
		ActivityID:                prepared.Activity.ActivityID,
		WorkspaceID:               prepared.Workspace.WorkspaceID,
		ExpectedRunRevision:       run.Revision,
		ExpectedActivityRevision:  prepared.Activity.Revision,
		ExpectedWorkspaceRevision: prepared.Workspace.Revision,
		AdapterID:                 "codex",
		ExecutionMode:             ExecutionManaged,
		LeaseUntil:                now.Add(time.Second),
	})
	if err != nil {
		t.Fatal(err)
	}
	confirmManagedAttemptLaunchForTest(t, store, attempt)
	if _, err := store.ActivateAttempt(ctx, attempt.AttemptID, attempt.Fence, now.Add(time.Second)); err != nil {
		t.Fatal(err)
	}

	interrupted, err := store.ExpireLeases(ctx, now.Add(2*time.Second))
	if err != nil {
		t.Fatal(err)
	}
	if len(interrupted) != 1 || interrupted[0].RunID != run.RunID || interrupted[0].Status != RunInterrupted {
		t.Fatalf("expired runs = %#v, want one interrupted run", interrupted)
	}
	if interrupted[0].CurrentFence != attempt.Fence+1 {
		t.Fatalf("expired run fence = %d, want %d", interrupted[0].CurrentFence, attempt.Fence+1)
	}
	if _, err := store.Heartbeat(ctx, attempt.AttemptID, attempt.Fence, now.Add(time.Minute)); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("expired heartbeat error = %v, want ErrStaleFence", err)
	}
}

func TestSupervisorEpochTakeoverInterruptsAnOwnedAttempt(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	firstStore := openTestStore(t, databasePath, WithOwnerEpoch("supervisor_first"))
	prepared := createPreparedExecution(t, firstStore, "takeover", 1)
	run := prepared.Run
	now := time.Now().UTC()
	attempt, err := firstStore.IssueAttempt(ctx, IssueAttemptParams{
		AttemptID:                 "att_takeover_1",
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
	confirmManagedAttemptLaunchForTest(t, firstStore, attempt)
	if _, err := firstStore.ActivateAttempt(ctx, attempt.AttemptID, attempt.Fence, now.Add(time.Minute)); err != nil {
		t.Fatal(err)
	}

	secondStore := openTestStore(t, databasePath, WithOwnerEpoch("supervisor_second"))
	interrupted, err := secondStore.ReconcileOwnerEpoch(ctx, now)
	if err != nil {
		t.Fatal(err)
	}
	if len(interrupted) != 1 || interrupted[0].RunID != run.RunID || interrupted[0].Status != RunInterrupted {
		t.Fatalf("takeover reconciliation = %#v, want interrupted run", interrupted)
	}
	if interrupted[0].CurrentFence != attempt.Fence+1 {
		t.Fatalf("takeover fence = %d, want %d", interrupted[0].CurrentFence, attempt.Fence+1)
	}
	if _, err := firstStore.Heartbeat(ctx, attempt.AttemptID, attempt.Fence, now.Add(2*time.Minute)); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("old owner heartbeat error = %v, want ErrStaleFence", err)
	}
}

func TestOperationIdempotencyRejectsAConflictingPayload(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	run, attempt := createAuthorityActiveRun(t, store, "run_operation", time.Now().UTC())
	request := BeginOperationParams{
		OperationID:         "op_snapshot_1",
		Kind:                "command.execute",
		AggregateType:       "run",
		AggregateID:         run.RunID,
		RunID:               run.RunID,
		AttemptID:           attempt.AttemptID,
		Fence:               attempt.Fence,
		ExpectedRunRevision: run.Revision,
		IdempotencyKey:      "command/run_operation/1",
		RequestSHA256:       digestForTest("request-a"),
	}

	first, replayed, err := store.BeginOperation(ctx, request)
	if err != nil {
		t.Fatal(err)
	}
	if replayed || first.Status != OperationPrepared {
		t.Fatalf("first operation = %#v replayed=%v, want prepared non-replay", first, replayed)
	}
	second, replayed, err := store.BeginOperation(ctx, request)
	if err != nil {
		t.Fatal(err)
	}
	if !replayed || second.OperationID != first.OperationID {
		t.Fatalf("idempotent retry = %#v replayed=%v, want original replay", second, replayed)
	}

	request.OperationID = "op_snapshot_2"
	request.RequestSHA256 = digestForTest("request-b")
	if _, _, err := store.BeginOperation(ctx, request); !errors.Is(err, ErrIdempotencyConflict) {
		t.Fatalf("conflicting idempotency error = %v, want ErrIdempotencyConflict", err)
	}
}

func TestRunAndEventsSurviveDatabaseReopen(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	store := openTestStore(t, databasePath)
	run := createReadyRun(t, store, "run_reopen")
	if err := store.Close(); err != nil {
		t.Fatal(err)
	}

	reopened := openTestStore(t, databasePath)
	loaded, err := reopened.GetRun(ctx, run.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.Status != RunReady || loaded.Revision != run.Revision {
		t.Fatalf("reopened run = %#v, want %#v", loaded, run)
	}
	events, err := reopened.ListRunEvents(ctx, run.RunID)
	if err != nil {
		t.Fatal(err)
	}
	if len(events) != 2 {
		t.Fatalf("reopened events = %#v, want create and transition", events)
	}
	if events[0].AggregateRevision != 1 || events[1].AggregateRevision != 2 {
		t.Fatalf("event revisions = %d, %d, want 1, 2", events[0].AggregateRevision, events[1].AggregateRevision)
	}
}

func createReadyRun(t *testing.T, store *Store, runID string) Run {
	t.Helper()
	ctx := context.Background()
	created, err := store.CreateRun(ctx, CreateRunParams{
		RunID:        runID,
		Kind:         "feature",
		SubjectType:  "feature",
		SubjectID:    "001-test",
		TargetRef:    "refs/heads/main",
		IntentSHA256: digestForTest(runID),
	})
	if err != nil {
		t.Fatal(err)
	}
	ready, err := store.TransitionRun(ctx, created.RunID, created.Revision, RunReady, "snapshot ready")
	if err != nil {
		t.Fatal(err)
	}
	return ready
}

func openTestStore(t *testing.T, databasePath string, options ...OpenOption) *Store {
	t.Helper()
	store, err := Open(context.Background(), databasePath, options...)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = store.Close() })
	return store
}

func digestForTest(seed string) string {
	digest := sha256.Sum256([]byte(seed))
	return hex.EncodeToString(digest[:])
}

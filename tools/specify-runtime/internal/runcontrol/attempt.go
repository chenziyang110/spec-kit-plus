package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
)

var liveAttemptStatuses = []AttemptStatus{AttemptIssued, AttemptActive, AttemptSealing}

// IssueAttempt allocates the next fencing token for a run and records the
// supervisor epoch which owns the new attempt. The run revision and fence are
// advanced in the same transaction as the attempt insert, so a concurrent
// issuer can never observe a successfully issued attempt with an old fence.
func (store *Store) IssueAttempt(ctx context.Context, params IssueAttemptParams) (Attempt, error) {
	if err := validateIssueAttemptParams(params); err != nil {
		return Attempt{}, err
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Attempt{}, fmt.Errorf("begin issue attempt transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	run, err := readRunTx(ctx, tx, params.RunID)
	if err != nil {
		return Attempt{}, err
	}
	if run.Revision != params.ExpectedRunRevision {
		return Attempt{}, fmt.Errorf("%w: run %q revision is %d, expected %d", ErrRevisionConflict, run.RunID, run.Revision, params.ExpectedRunRevision)
	}
	if run.Status != RunReady {
		return Attempt{}, fmt.Errorf("%w: cannot issue an attempt while run %q is %q", ErrInvalidTransition, run.RunID, run.Status)
	}
	activity, err := readActivityTx(ctx, tx, params.ActivityID)
	if err != nil {
		return Attempt{}, err
	}
	workspace, err := readWorkspaceTx(ctx, tx, params.WorkspaceID)
	if err != nil {
		return Attempt{}, err
	}
	if activity.RunID != run.RunID || workspace.RunID != run.RunID {
		return Attempt{}, fmt.Errorf("%w: activity and workspace must belong to run %q", ErrInvalidArgument, run.RunID)
	}
	if activity.Revision != params.ExpectedActivityRevision || workspace.Revision != params.ExpectedWorkspaceRevision {
		return Attempt{}, fmt.Errorf("%w: activity or workspace revision changed", ErrRevisionConflict)
	}
	if activity.Status != ActivityReady {
		return Attempt{}, fmt.Errorf("%w: activity %q is %q", ErrInvalidTransition, activity.ActivityID, activity.Status)
	}
	if workspace.Status != WorkspaceReady {
		return Attempt{}, fmt.Errorf("%w: workspace %q is %q", ErrWorkspaceNotUsable, workspace.WorkspaceID, workspace.Status)
	}

	hasLiveAttempt, err := runHasLiveAttemptTx(ctx, tx, run.RunID)
	if err != nil {
		return Attempt{}, err
	}
	if hasLiveAttempt {
		return Attempt{}, fmt.Errorf("%w: run %q already has a live attempt", ErrLiveAttempt, run.RunID)
	}

	nowMS := time.Now().UTC().UnixMilli()
	nextFence := run.CurrentFence + 1
	result, err := tx.ExecContext(ctx, `
		UPDATE runs
		SET current_fence = ?, owner_epoch = ?, revision = revision + 1, updated_at_ms = ?
		WHERE run_id = ? AND revision = ? AND current_fence = ? AND status = ?
		  AND NOT EXISTS (
			SELECT 1 FROM attempts
			WHERE run_id = ? AND status IN (?, ?, ?)
		  )
	`, nextFence, store.ownerEpoch, nowMS, run.RunID, run.Revision, run.CurrentFence, run.Status,
		run.RunID, AttemptIssued, AttemptActive, AttemptSealing)
	if err != nil {
		if isSQLiteContention(err) {
			return Attempt{}, fmt.Errorf("%w: concurrent attempt issuance for run %q", ErrRevisionConflict, run.RunID)
		}
		return Attempt{}, fmt.Errorf("advance run fence for attempt: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "issue attempt"); err != nil {
		return Attempt{}, err
	}
	run.CurrentFence = nextFence
	run.OwnerEpoch = store.ownerEpoch
	run.Revision++
	run.UpdatedAtMS = nowMS

	attempt := Attempt{
		AttemptID:           params.AttemptID,
		RunID:               params.RunID,
		ActivityID:          params.ActivityID,
		WorkspaceID:         params.WorkspaceID,
		WorkspaceGeneration: workspace.Generation,
		Status:              AttemptIssued,
		AdapterID:           params.AdapterID,
		ExecutionMode:       params.ExecutionMode,
		OwnerEpoch:          store.ownerEpoch,
		Fence:               nextFence,
		LeaseUntilMS:        params.LeaseUntil.UTC().UnixMilli(),
		HeartbeatAtMS:       0,
		Revision:            1,
		CreatedAtMS:         nowMS,
		UpdatedAtMS:         nowMS,
	}
	_, err = tx.ExecContext(ctx, `
		INSERT INTO attempts (
			attempt_id, run_id, activity_id, workspace_id, workspace_generation,
			status, adapter_id, execution_mode,
			owner_epoch, fence, lease_until_ms, heartbeat_at_ms,
			revision, created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, attempt.AttemptID, attempt.RunID, attempt.ActivityID, attempt.WorkspaceID,
		attempt.WorkspaceGeneration, attempt.Status, attempt.AdapterID,
		attempt.ExecutionMode, attempt.OwnerEpoch, attempt.Fence,
		attempt.LeaseUntilMS, attempt.HeartbeatAtMS, attempt.Revision,
		attempt.CreatedAtMS, attempt.UpdatedAtMS)
	if err != nil {
		return Attempt{}, fmt.Errorf("insert attempt: %w", err)
	}
	if err := appendRunEventTx(ctx, tx, run, "attempt.issued", attempt.AttemptID); err != nil {
		return Attempt{}, err
	}
	if err := tx.Commit(); err != nil {
		return Attempt{}, fmt.Errorf("commit issue attempt: %w", err)
	}
	return attempt, nil
}

// ActivateAttempt marks an issued attempt live. Both the run revision/fence and
// the attempt revision/fence/owner epoch participate in the compare-and-swap.
func (store *Store) ActivateAttempt(ctx context.Context, attemptID string, fence int64, leaseUntil time.Time) (Attempt, error) {
	if strings.TrimSpace(attemptID) == "" {
		return Attempt{}, errors.New("attempt_id is required")
	}
	if fence <= 0 {
		return Attempt{}, errors.New("fence must be positive")
	}
	if leaseUntil.IsZero() {
		return Attempt{}, errors.New("lease_until is required")
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Attempt{}, fmt.Errorf("begin activate attempt transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	attempt, err := readAttemptTx(ctx, tx, attemptID)
	if err != nil {
		return Attempt{}, err
	}
	run, err := readRunTx(ctx, tx, attempt.RunID)
	if err != nil {
		return Attempt{}, err
	}
	activity, err := readActivityTx(ctx, tx, attempt.ActivityID)
	if err != nil {
		return Attempt{}, err
	}
	workspace, err := readWorkspaceTx(ctx, tx, attempt.WorkspaceID)
	if err != nil {
		return Attempt{}, err
	}
	if err := validateAttemptAuthority(attempt, run, fence, store.ownerEpoch); err != nil {
		return Attempt{}, err
	}
	if attempt.Status != AttemptIssued {
		return Attempt{}, fmt.Errorf("%w: attempt %q is %q, expected %q", ErrInvalidTransition, attempt.AttemptID, attempt.Status, AttemptIssued)
	}
	if run.Status != RunReady || activity.Status != ActivityReady || workspace.Status != WorkspaceReady {
		return Attempt{}, fmt.Errorf("%w: cannot activate an attempt while run %q is %q", ErrInvalidTransition, run.RunID, run.Status)
	}
	if activity.RunID != run.RunID || workspace.RunID != run.RunID || workspace.Generation != attempt.WorkspaceGeneration {
		return Attempt{}, fmt.Errorf("%w: attempt %q execution bindings are inconsistent", ErrStaleFence, attempt.AttemptID)
	}

	nowMS := time.Now().UTC().UnixMilli()
	if attempt.LeaseUntilMS <= nowMS {
		return Attempt{}, fmt.Errorf("%w: attempt %q lease expired before activation", ErrStaleFence, attempt.AttemptID)
	}
	if leaseUntil.UTC().UnixMilli() <= nowMS {
		return Attempt{}, fmt.Errorf("%w: lease_until must be in the future", ErrInvalidArgument)
	}
	if attempt.ExecutionMode == ExecutionManaged {
		var confirmedLaunches int
		if err := tx.QueryRowContext(ctx, `
			SELECT COUNT(*)
			FROM operations
			WHERE kind = ? AND status = ?
			  AND aggregate_type = 'workspace' AND aggregate_id = ?
			  AND run_id = ? AND attempt_id = ?
			  AND activity_id = ? AND workspace_id = ?
			  AND owner_epoch = ? AND fence = ? AND run_revision = ?
		`, attemptLaunchOperationKind, OperationSucceeded, attempt.WorkspaceID,
			run.RunID, attempt.AttemptID, attempt.ActivityID, attempt.WorkspaceID,
			store.ownerEpoch, fence, run.Revision).Scan(&confirmedLaunches); err != nil {
			return Attempt{}, fmt.Errorf("read managed attempt launch gate: %w", err)
		}
		if confirmedLaunches != 1 {
			return Attempt{}, fmt.Errorf(
				"%w: managed attempt %q requires exactly one confirmed launch, found %d",
				ErrInvalidTransition,
				attempt.AttemptID,
				confirmedLaunches,
			)
		}
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE runs
		SET status = ?, owner_epoch = ?, revision = revision + 1, updated_at_ms = ?
		WHERE run_id = ? AND revision = ? AND current_fence = ? AND status = ?
	`, RunActive, store.ownerEpoch, nowMS, run.RunID, run.Revision, fence, run.Status)
	if err != nil {
		return Attempt{}, fmt.Errorf("activate attempt run: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "activate attempt run"); err != nil {
		return Attempt{}, err
	}
	run.Status = RunActive
	run.OwnerEpoch = store.ownerEpoch
	run.Revision++
	run.UpdatedAtMS = nowMS

	result, err = tx.ExecContext(ctx, `
		UPDATE activities
		SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE activity_id = ? AND run_id = ? AND revision = ? AND status = ?
	`, ActivityActive, nowMS, activity.ActivityID, run.RunID, activity.Revision, ActivityReady)
	if err != nil {
		return Attempt{}, fmt.Errorf("activate activity: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "activate activity"); err != nil {
		return Attempt{}, err
	}
	activity.Status = ActivityActive
	activity.Revision++
	activity.UpdatedAtMS = nowMS

	result, err = tx.ExecContext(ctx, `
		UPDATE workspaces
		SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE workspace_id = ? AND run_id = ? AND generation = ?
		  AND revision = ? AND status = ?
	`, WorkspaceInUse, nowMS, workspace.WorkspaceID, run.RunID,
		workspace.Generation, workspace.Revision, WorkspaceReady)
	if err != nil {
		return Attempt{}, fmt.Errorf("activate workspace: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "activate workspace"); err != nil {
		return Attempt{}, err
	}
	workspace.Status = WorkspaceInUse
	workspace.Revision++
	workspace.UpdatedAtMS = nowMS

	result, err = tx.ExecContext(ctx, `
		UPDATE attempts
		SET status = ?, lease_until_ms = ?, heartbeat_at_ms = ?,
		    revision = revision + 1, updated_at_ms = ?
		WHERE attempt_id = ? AND run_id = ? AND revision = ? AND fence = ?
		  AND owner_epoch = ? AND status = ?
	`, AttemptActive, leaseUntil.UTC().UnixMilli(), nowMS, nowMS,
		attempt.AttemptID, attempt.RunID, attempt.Revision, fence,
		store.ownerEpoch, AttemptIssued)
	if err != nil {
		return Attempt{}, fmt.Errorf("activate attempt: %w", err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "activate attempt"); err != nil {
		return Attempt{}, err
	}
	attempt.Status = AttemptActive
	attempt.LeaseUntilMS = leaseUntil.UTC().UnixMilli()
	attempt.HeartbeatAtMS = nowMS
	attempt.Revision++
	attempt.UpdatedAtMS = nowMS

	if err := appendRunEventTx(ctx, tx, run, "attempt.activated", attempt.AttemptID); err != nil {
		return Attempt{}, err
	}
	if err := appendActivityEventTx(ctx, tx, activity, "activity.activated", attempt.AttemptID); err != nil {
		return Attempt{}, err
	}
	if err := appendWorkspaceEventTx(ctx, tx, workspace, "workspace.in-use", attempt.AttemptID); err != nil {
		return Attempt{}, err
	}
	if err := tx.Commit(); err != nil {
		return Attempt{}, fmt.Errorf("commit activate attempt: %w", err)
	}
	return attempt, nil
}

// Heartbeat renews an active attempt only while its supervisor epoch and fence
// still own the run. It deliberately does not advance the run revision: the
// attempt revision is the CAS token for lease renewal, while the observed run
// revision and fence are included in the UPDATE predicate.
func (store *Store) Heartbeat(ctx context.Context, attemptID string, fence int64, leaseUntil time.Time) (Attempt, error) {
	if strings.TrimSpace(attemptID) == "" {
		return Attempt{}, errors.New("attempt_id is required")
	}
	if fence <= 0 {
		return Attempt{}, errors.New("fence must be positive")
	}
	if leaseUntil.IsZero() {
		return Attempt{}, errors.New("lease_until is required")
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Attempt{}, fmt.Errorf("begin heartbeat transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	attempt, err := readAttemptTx(ctx, tx, attemptID)
	if err != nil {
		return Attempt{}, err
	}
	run, err := readRunTx(ctx, tx, attempt.RunID)
	if err != nil {
		return Attempt{}, err
	}
	activity, err := readActivityTx(ctx, tx, attempt.ActivityID)
	if err != nil {
		return Attempt{}, err
	}
	workspace, err := readWorkspaceTx(ctx, tx, attempt.WorkspaceID)
	if err != nil {
		return Attempt{}, err
	}
	if err := validateAttemptAuthority(attempt, run, fence, store.ownerEpoch); err != nil {
		return Attempt{}, err
	}
	if attempt.Status != AttemptActive {
		return Attempt{}, fmt.Errorf("%w: attempt %q is not active", ErrInvalidTransition, attempt.AttemptID)
	}
	if run.Status != RunActive {
		return Attempt{}, fmt.Errorf("%w: run %q is %q", ErrStaleFence, run.RunID, run.Status)
	}
	if activity.Status != ActivityActive || workspace.Status != WorkspaceInUse ||
		activity.RunID != run.RunID || workspace.RunID != run.RunID || workspace.Generation != attempt.WorkspaceGeneration {
		return Attempt{}, fmt.Errorf("%w: attempt %q execution bindings are no longer active", ErrStaleFence, attempt.AttemptID)
	}

	nowMS := time.Now().UTC().UnixMilli()
	if attempt.LeaseUntilMS <= nowMS {
		return Attempt{}, fmt.Errorf("%w: attempt %q lease has expired", ErrStaleFence, attempt.AttemptID)
	}
	if leaseUntil.UTC().UnixMilli() <= nowMS {
		return Attempt{}, fmt.Errorf("%w: lease_until must be in the future", ErrInvalidArgument)
	}
	if leaseUntil.UTC().UnixMilli() <= attempt.LeaseUntilMS {
		return Attempt{}, fmt.Errorf("%w: heartbeat must extend the current lease", ErrInvalidArgument)
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE attempts
		SET lease_until_ms = ?, heartbeat_at_ms = ?, revision = revision + 1, updated_at_ms = ?
		WHERE attempt_id = ? AND run_id = ? AND revision = ? AND fence = ?
		  AND owner_epoch = ? AND status = ? AND lease_until_ms > ? AND lease_until_ms < ?
		  AND EXISTS (
			SELECT 1 FROM runs
			WHERE run_id = ? AND revision = ? AND current_fence = ? AND status = ?
		  )
	`, leaseUntil.UTC().UnixMilli(), nowMS, nowMS,
		attempt.AttemptID, attempt.RunID, attempt.Revision, fence,
		store.ownerEpoch, AttemptActive, nowMS, leaseUntil.UTC().UnixMilli(),
		run.RunID, run.Revision, fence, RunActive)
	if err != nil {
		return Attempt{}, fmt.Errorf("heartbeat attempt: %w", err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "heartbeat attempt"); err != nil {
		return Attempt{}, err
	}
	attempt.LeaseUntilMS = leaseUntil.UTC().UnixMilli()
	attempt.HeartbeatAtMS = nowMS
	attempt.Revision++
	attempt.UpdatedAtMS = nowMS

	if err := tx.Commit(); err != nil {
		return Attempt{}, fmt.Errorf("commit heartbeat: %w", err)
	}
	return attempt, nil
}

// CancelRun invalidates the run fence before revoking any live attempt. The
// caller must hold the exact run revision that it intends to cancel.
func (store *Store) CancelRun(ctx context.Context, runID string, expectedRevision int64, reason string) (Run, error) {
	if strings.TrimSpace(runID) == "" {
		return Run{}, errors.New("run_id is required")
	}
	if expectedRevision <= 0 {
		return Run{}, errors.New("expected_revision must be positive")
	}
	if strings.TrimSpace(reason) == "" {
		return Run{}, errors.New("reason is required")
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Run{}, fmt.Errorf("begin cancel run transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	run, err := readRunTx(ctx, tx, runID)
	if err != nil {
		return Run{}, err
	}
	if run.Revision != expectedRevision {
		return Run{}, fmt.Errorf("%w: run %q revision is %d, expected %d", ErrRevisionConflict, run.RunID, run.Revision, expectedRevision)
	}
	if !runCanBeCancelled(run.Status) {
		return Run{}, fmt.Errorf("%w: cannot cancel run %q from %q", ErrInvalidTransition, run.RunID, run.Status)
	}

	liveAttempt, hasLiveAttempt, err := readLiveAttemptForFenceTx(ctx, tx, run.RunID, run.CurrentFence)
	if err != nil {
		return Run{}, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	oldFence := run.CurrentFence
	if hasLiveAttempt {
		if err := markAttemptLaunchOutcomeUnknownTx(ctx, tx, liveAttempt, nowMS); err != nil {
			return Run{}, err
		}
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE runs
		SET status = ?, current_fence = current_fence + 1,
		    owner_epoch = ?, revision = revision + 1, updated_at_ms = ?
		WHERE run_id = ? AND revision = ? AND current_fence = ? AND status = ?
	`, RunCancelled, store.ownerEpoch, nowMS, run.RunID, run.Revision, oldFence, run.Status)
	if err != nil {
		return Run{}, fmt.Errorf("cancel run: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "cancel run"); err != nil {
		return Run{}, err
	}
	run.Status = RunCancelled
	run.CurrentFence++
	run.OwnerEpoch = store.ownerEpoch
	run.Revision++
	run.UpdatedAtMS = nowMS

	if hasLiveAttempt {
		if err := updateAttemptTerminalTx(ctx, tx, liveAttempt, AttemptRevoked, nowMS); err != nil {
			return Run{}, err
		}
		if err := updateAttemptExecutionTx(ctx, tx, liveAttempt, ActivityCancelled, WorkspaceQuarantined, nowMS, reason); err != nil {
			return Run{}, err
		}
	} else if err := updateOpenExecutionForRunTx(ctx, tx, run.RunID, ActivityCancelled, WorkspaceQuarantined, nowMS, reason); err != nil {
		return Run{}, err
	}
	if err := appendRunEventTx(ctx, tx, run, "run.cancelled", reason); err != nil {
		return Run{}, err
	}
	if err := tx.Commit(); err != nil {
		return Run{}, fmt.Errorf("commit cancel run: %w", err)
	}
	return run, nil
}

// ExpireLeases interrupts every run whose current issued/active attempt has an
// expired lease. Each run fence is advanced before its attempt is marked lost.
func (store *Store) ExpireLeases(ctx context.Context, now time.Time) ([]Run, error) {
	if now.IsZero() {
		return nil, errors.New("now is required")
	}
	return store.interruptMatchingAttempts(ctx, now.UTC().UnixMilli(), `a.lease_until_ms <= ?`, []any{now.UTC().UnixMilli()}, "attempt lease expired", AttemptLost)
}

// ReconcileOwnerEpoch fences attempts left behind by another supervisor
// incarnation. A process with an old epoch cannot renew the attempt after this
// transaction commits, even if its PID has been reused.
func (store *Store) ReconcileOwnerEpoch(ctx context.Context, now time.Time) ([]Run, error) {
	if now.IsZero() {
		return nil, errors.New("now is required")
	}
	nowMS := now.UTC().UnixMilli()
	interrupted, err := store.interruptMatchingAttempts(ctx, nowMS, `a.owner_epoch <> ?`, []any{store.ownerEpoch}, "supervisor owner epoch changed", AttemptLost)
	if err != nil {
		return nil, err
	}
	allocating, err := store.interruptMatchingAllocatingRuns(ctx, nowMS, `owner_epoch <> ?`, []any{store.ownerEpoch}, "supervisor owner epoch changed during allocation")
	if err != nil {
		return nil, err
	}
	if _, err := store.db.ExecContext(ctx, `
		UPDATE supervisor_instances
		SET status = 'superseded', stopped_at_ms = COALESCE(stopped_at_ms, ?)
		WHERE owner_epoch <> ? AND status = 'active'
	`, nowMS, store.ownerEpoch); err != nil {
		return nil, fmt.Errorf("mark prior supervisor epochs superseded: %w", err)
	}
	return append(interrupted, allocating...), nil
}

func (store *Store) interruptMatchingAttempts(
	ctx context.Context,
	nowMS int64,
	extraPredicate string,
	extraArgs []any,
	reason string,
	terminalStatus AttemptStatus,
) ([]Run, error) {
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin attempt reconciliation transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	query := `
		SELECT a.attempt_id, a.run_id, a.activity_id, a.workspace_id,
		       a.workspace_generation, a.status, a.adapter_id,
		       a.execution_mode, a.owner_epoch, a.fence,
		       a.lease_until_ms, a.heartbeat_at_ms, a.revision,
		       a.created_at_ms, a.updated_at_ms
		FROM attempts AS a
		JOIN runs AS r ON r.run_id = a.run_id AND r.current_fence = a.fence
		WHERE a.status IN (?, ?, ?)
		  AND r.status IN (?, ?)
		  AND ` + extraPredicate + `
		ORDER BY a.run_id, a.attempt_id
	`
	args := []any{AttemptIssued, AttemptActive, AttemptSealing, RunReady, RunActive}
	args = append(args, extraArgs...)
	rows, err := tx.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("query attempts to interrupt: %w", err)
	}
	var attempts []Attempt
	for rows.Next() {
		attempt, scanErr := scanAttempt(rows)
		if scanErr != nil {
			_ = rows.Close()
			return nil, scanErr
		}
		attempts = append(attempts, attempt)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, fmt.Errorf("iterate attempts to interrupt: %w", err)
	}
	if err := rows.Close(); err != nil {
		return nil, fmt.Errorf("close attempts to interrupt: %w", err)
	}

	interrupted := make([]Run, 0, len(attempts))
	for _, attempt := range attempts {
		run, err := readRunTx(ctx, tx, attempt.RunID)
		if err != nil {
			return nil, err
		}
		if run.CurrentFence != attempt.Fence {
			continue
		}
		if run.Status != RunReady && run.Status != RunActive {
			continue
		}
		if err := markAttemptLaunchOutcomeUnknownTx(ctx, tx, attempt, nowMS); err != nil {
			return nil, err
		}

		result, err := tx.ExecContext(ctx, `
			UPDATE runs
			SET status = ?, current_fence = current_fence + 1,
			    owner_epoch = ?, revision = revision + 1, updated_at_ms = ?
			WHERE run_id = ? AND revision = ? AND current_fence = ? AND status = ?
		`, RunInterrupted, store.ownerEpoch, nowMS, run.RunID, run.Revision, run.CurrentFence, run.Status)
		if err != nil {
			return nil, fmt.Errorf("interrupt run %q: %w", run.RunID, err)
		}
		if err := requireOneCASRow(result, ErrRevisionConflict, "interrupt run"); err != nil {
			return nil, err
		}
		run.Status = RunInterrupted
		run.CurrentFence++
		run.OwnerEpoch = store.ownerEpoch
		run.Revision++
		run.UpdatedAtMS = nowMS

		if err := updateAttemptTerminalTx(ctx, tx, attempt, terminalStatus, nowMS); err != nil {
			return nil, err
		}
		if err := updateAttemptExecutionTx(ctx, tx, attempt, ActivityInterrupted, WorkspaceQuarantined, nowMS, reason); err != nil {
			return nil, err
		}
		if err := appendRunEventTx(ctx, tx, run, "run.interrupted", reason+": "+attempt.AttemptID); err != nil {
			return nil, err
		}
		interrupted = append(interrupted, run)
	}

	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit attempt reconciliation: %w", err)
	}
	return interrupted, nil
}

func (store *Store) interruptMatchingAllocatingRuns(
	ctx context.Context,
	nowMS int64,
	extraPredicate string,
	extraArgs []any,
	reason string,
) ([]Run, error) {
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin allocating run reconciliation: %w", err)
	}
	defer func() { _ = tx.Rollback() }()

	query := `SELECT run_id FROM runs WHERE status = ? AND ` + extraPredicate + ` ORDER BY run_id`
	args := []any{RunAllocating}
	args = append(args, extraArgs...)
	rows, err := tx.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("query allocating runs to interrupt: %w", err)
	}
	runIDs := make([]string, 0)
	for rows.Next() {
		var runID string
		if err := rows.Scan(&runID); err != nil {
			_ = rows.Close()
			return nil, fmt.Errorf("scan allocating run to interrupt: %w", err)
		}
		runIDs = append(runIDs, runID)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, fmt.Errorf("iterate allocating runs to interrupt: %w", err)
	}
	if err := rows.Close(); err != nil {
		return nil, fmt.Errorf("close allocating runs query: %w", err)
	}

	interrupted := make([]Run, 0, len(runIDs))
	for _, runID := range runIDs {
		run, err := readRunTx(ctx, tx, runID)
		if err != nil {
			return nil, err
		}
		if run.Status != RunAllocating {
			continue
		}
		if err := markWorkspaceAllocationsOutcomeUnknownForRunTx(ctx, tx, run.RunID, reason, nowMS); err != nil {
			return nil, err
		}
		result, err := tx.ExecContext(ctx, `
			UPDATE runs
			SET status = ?, current_fence = current_fence + 1,
			    owner_epoch = ?, revision = revision + 1, updated_at_ms = ?
			WHERE run_id = ? AND revision = ? AND current_fence = ?
			  AND status = ? AND owner_epoch = ?
		`, RunInterrupted, store.ownerEpoch, nowMS, run.RunID, run.Revision,
			run.CurrentFence, RunAllocating, run.OwnerEpoch)
		if err != nil {
			return nil, fmt.Errorf("interrupt allocating run %q: %w", run.RunID, err)
		}
		if err := requireOneCASRow(result, ErrRevisionConflict, "interrupt allocating run"); err != nil {
			return nil, err
		}
		run.Status = RunInterrupted
		run.CurrentFence++
		run.OwnerEpoch = store.ownerEpoch
		run.Revision++
		run.UpdatedAtMS = nowMS
		if err := appendRunEventTx(ctx, tx, run, "run.interrupted", reason); err != nil {
			return nil, err
		}
		if err := updateOpenExecutionForRunTx(ctx, tx, run.RunID, ActivityInterrupted, WorkspaceQuarantined, nowMS, reason); err != nil {
			return nil, err
		}
		interrupted = append(interrupted, run)
	}
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit allocating run reconciliation: %w", err)
	}
	return interrupted, nil
}

func (store *Store) shutdownOwnedState(ctx context.Context, now time.Time) error {
	nowMS := now.UTC().UnixMilli()
	if _, err := store.interruptMatchingAttempts(
		ctx,
		nowMS,
		`a.owner_epoch = ?`,
		[]any{store.ownerEpoch},
		"supervisor stopped",
		AttemptRevoked,
	); err != nil {
		return err
	}
	_, err := store.interruptMatchingAllocatingRuns(
		ctx,
		nowMS,
		`owner_epoch = ?`,
		[]any{store.ownerEpoch},
		"supervisor stopped during allocation",
	)
	return err
}

func validateIssueAttemptParams(params IssueAttemptParams) error {
	if strings.TrimSpace(params.AttemptID) == "" {
		return errors.New("attempt_id is required")
	}
	if strings.TrimSpace(params.RunID) == "" {
		return errors.New("run_id is required")
	}
	if strings.TrimSpace(params.ActivityID) == "" || strings.TrimSpace(params.WorkspaceID) == "" {
		return fmt.Errorf("%w: activity_id and workspace_id are required", ErrInvalidArgument)
	}
	if params.ExpectedRunRevision <= 0 {
		return errors.New("expected_run_revision must be positive")
	}
	if params.ExpectedActivityRevision <= 0 || params.ExpectedWorkspaceRevision <= 0 {
		return fmt.Errorf("%w: expected activity and workspace revisions must be positive", ErrInvalidArgument)
	}
	if strings.TrimSpace(params.AdapterID) == "" {
		return errors.New("adapter_id is required")
	}
	if strings.TrimSpace(string(params.ExecutionMode)) == "" {
		return errors.New("execution_mode is required")
	}
	if params.LeaseUntil.IsZero() {
		return errors.New("lease_until is required")
	}
	if !params.LeaseUntil.After(time.Now().UTC()) {
		return fmt.Errorf("%w: lease_until must be in the future", ErrInvalidArgument)
	}
	return nil
}

func runHasLiveAttemptTx(ctx context.Context, tx *sql.Tx, runID string) (bool, error) {
	var exists int
	err := tx.QueryRowContext(ctx, `
		SELECT EXISTS (
			SELECT 1 FROM attempts WHERE run_id = ? AND status IN (?, ?, ?)
		)
	`, runID, liveAttemptStatuses[0], liveAttemptStatuses[1], liveAttemptStatuses[2]).Scan(&exists)
	if err != nil {
		return false, fmt.Errorf("query live attempt for run %q: %w", runID, err)
	}
	return exists != 0, nil
}

func (store *Store) GetAttempt(ctx context.Context, attemptID string) (Attempt, error) {
	if strings.TrimSpace(attemptID) == "" {
		return Attempt{}, fmt.Errorf("%w: attempt_id is required", ErrInvalidArgument)
	}
	return readAttemptTx(ctx, store.db, attemptID)
}

func readAttemptTx(ctx context.Context, querier rowQuerier, attemptID string) (Attempt, error) {
	row := querier.QueryRowContext(ctx, `
		SELECT attempt_id, run_id, activity_id, workspace_id,
		       workspace_generation, status, adapter_id, execution_mode,
		       owner_epoch, fence, lease_until_ms, heartbeat_at_ms,
		       revision, created_at_ms, updated_at_ms
		FROM attempts
		WHERE attempt_id = ?
	`, attemptID)
	attempt, err := scanAttempt(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Attempt{}, fmt.Errorf("%w: attempt %q", ErrNotFound, attemptID)
	}
	return attempt, err
}

type attemptScanner interface {
	Scan(...any) error
}

func scanAttempt(scanner attemptScanner) (Attempt, error) {
	var attempt Attempt
	err := scanner.Scan(
		&attempt.AttemptID,
		&attempt.RunID,
		&attempt.ActivityID,
		&attempt.WorkspaceID,
		&attempt.WorkspaceGeneration,
		&attempt.Status,
		&attempt.AdapterID,
		&attempt.ExecutionMode,
		&attempt.OwnerEpoch,
		&attempt.Fence,
		&attempt.LeaseUntilMS,
		&attempt.HeartbeatAtMS,
		&attempt.Revision,
		&attempt.CreatedAtMS,
		&attempt.UpdatedAtMS,
	)
	if err != nil {
		return Attempt{}, err
	}
	return attempt, nil
}

func readLiveAttemptForFenceTx(ctx context.Context, tx *sql.Tx, runID string, fence int64) (Attempt, bool, error) {
	row := tx.QueryRowContext(ctx, `
		SELECT attempt_id, run_id, activity_id, workspace_id,
		       workspace_generation, status, adapter_id, execution_mode,
		       owner_epoch, fence, lease_until_ms, heartbeat_at_ms,
		       revision, created_at_ms, updated_at_ms
		FROM attempts
		WHERE run_id = ? AND fence = ? AND status IN (?, ?, ?)
		ORDER BY revision DESC
		LIMIT 1
	`, runID, fence, AttemptIssued, AttemptActive, AttemptSealing)
	attempt, err := scanAttempt(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Attempt{}, false, nil
	}
	if err != nil {
		return Attempt{}, false, fmt.Errorf("read live attempt for run %q: %w", runID, err)
	}
	return attempt, true, nil
}

func validateAttemptAuthority(attempt Attempt, run Run, fence int64, ownerEpoch string) error {
	if attempt.Fence != fence || run.CurrentFence != fence {
		return fmt.Errorf("%w: attempt %q fence %d does not own run fence %d", ErrStaleFence, attempt.AttemptID, fence, run.CurrentFence)
	}
	if attempt.OwnerEpoch != ownerEpoch {
		return fmt.Errorf("%w: attempt %q belongs to a different supervisor epoch", ErrStaleFence, attempt.AttemptID)
	}
	return nil
}

func updateAttemptTerminalTx(ctx context.Context, tx *sql.Tx, attempt Attempt, status AttemptStatus, nowMS int64) error {
	result, err := tx.ExecContext(ctx, `
		UPDATE attempts
		SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE attempt_id = ? AND run_id = ? AND revision = ? AND fence = ?
		  AND owner_epoch = ? AND status = ?
	`, status, nowMS, attempt.AttemptID, attempt.RunID, attempt.Revision,
		attempt.Fence, attempt.OwnerEpoch, attempt.Status)
	if err != nil {
		return fmt.Errorf("mark attempt %q %s: %w", attempt.AttemptID, status, err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "finish live attempt"); err != nil {
		return err
	}
	return nil
}

func requireOneCASRow(result sql.Result, conflict error, action string) error {
	rows, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("read %s result: %w", action, err)
	}
	if rows != 1 {
		return fmt.Errorf("%w: %s compare-and-swap affected %d rows", conflict, action, rows)
	}
	return nil
}

func runCanBeCancelled(status RunStatus) bool {
	switch status {
	case RunQueued, RunAllocating, RunReady, RunActive, RunParked, RunInterrupted:
		return true
	default:
		return false
	}
}

func isSQLiteContention(err error) bool {
	message := strings.ToLower(err.Error())
	return strings.Contains(message, "database is locked") ||
		strings.Contains(message, "database table is locked") ||
		strings.Contains(message, "sqlite_busy")
}

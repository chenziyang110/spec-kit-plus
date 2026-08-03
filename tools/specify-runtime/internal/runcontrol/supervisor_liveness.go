package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"
)

// HeartbeatSupervisor advances the current owner epoch's durable liveness
// timestamp without allowing a delayed clock observation to move it backward.
func (store *Store) HeartbeatSupervisor(ctx context.Context, observedAt time.Time) error {
	if observedAt.IsZero() {
		return fmt.Errorf("%w: observed_at is required", ErrInvalidArgument)
	}
	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin supervisor heartbeat: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := heartbeatSupervisorTx(ctx, transaction, store.ownerEpoch, observedAt.UTC().UnixMilli()); err != nil {
		return err
	}
	if err := transaction.Commit(); err != nil {
		return fmt.Errorf("commit supervisor heartbeat: %w", err)
	}
	return nil
}

// ReconcileStaleSupervisors fences only owner epochs whose durable heartbeat
// is at or before staleBefore. Live parallel supervisors remain authoritative.
// Stale-owner selection, Run interruption, workspace quarantine, and epoch
// supersession commit in one SQLite transaction.
func (store *Store) ReconcileStaleSupervisors(
	ctx context.Context,
	now time.Time,
	staleBefore time.Time,
) ([]Run, error) {
	if now.IsZero() || staleBefore.IsZero() {
		return nil, fmt.Errorf("%w: now and stale_before are required", ErrInvalidArgument)
	}
	now = now.UTC()
	staleBefore = staleBefore.UTC()
	if !staleBefore.Before(now) {
		return nil, fmt.Errorf("%w: stale_before must be before now", ErrInvalidArgument)
	}

	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin stale supervisor reconciliation: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := heartbeatSupervisorTx(ctx, transaction, store.ownerEpoch, now.UnixMilli()); err != nil {
		return nil, err
	}

	staleAttemptOwner := `a.owner_epoch IN (
		SELECT owner_epoch FROM supervisor_instances
		WHERE owner_epoch <> ? AND status = 'active' AND heartbeat_at_ms <= ?
	)`
	arguments := []any{store.ownerEpoch, staleBefore.UnixMilli()}
	interrupted, err := store.interruptMatchingAttemptsTx(
		ctx,
		transaction,
		now.UnixMilli(),
		staleAttemptOwner,
		arguments,
		"supervisor heartbeat expired",
		AttemptLost,
	)
	if err != nil {
		return nil, err
	}
	stalePreparationOwner := `owner_epoch IN (
		SELECT owner_epoch FROM supervisor_instances
		WHERE owner_epoch <> ? AND status = 'active' AND heartbeat_at_ms <= ?
	)`
	preparationRuns, err := store.interruptMatchingPreparationRunsTx(
		ctx,
		transaction,
		now.UnixMilli(),
		stalePreparationOwner,
		arguments,
		"supervisor heartbeat expired during preparation",
	)
	if err != nil {
		return nil, err
	}
	if _, err := transaction.ExecContext(ctx, `
		UPDATE supervisor_instances
		SET status = 'superseded', heartbeat_at_ms = MAX(heartbeat_at_ms, ?),
		    stopped_at_ms = COALESCE(stopped_at_ms, ?)
		WHERE owner_epoch <> ? AND status = 'active' AND heartbeat_at_ms <= ?
	`, now.UnixMilli(), now.UnixMilli(), store.ownerEpoch, staleBefore.UnixMilli()); err != nil {
		return nil, fmt.Errorf("mark stale supervisor epochs superseded: %w", err)
	}
	if err := transaction.Commit(); err != nil {
		return nil, fmt.Errorf("commit stale supervisor reconciliation: %w", err)
	}
	return append(interrupted, preparationRuns...), nil
}

func heartbeatSupervisorTx(
	ctx context.Context,
	transaction *sql.Tx,
	ownerEpoch string,
	heartbeatAtMS int64,
) error {
	var status string
	var currentHeartbeatMS int64
	if err := transaction.QueryRowContext(ctx, `
		SELECT status, heartbeat_at_ms
		FROM supervisor_instances
		WHERE owner_epoch = ?
	`, ownerEpoch).Scan(&status, &currentHeartbeatMS); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return fmt.Errorf("%w: supervisor epoch %q is not registered", ErrStaleFence, ownerEpoch)
		}
		return fmt.Errorf("read supervisor heartbeat authority: %w", err)
	}
	if status != "active" {
		return fmt.Errorf("%w: supervisor epoch %q is %q", ErrStaleFence, ownerEpoch, status)
	}
	if heartbeatAtMS <= currentHeartbeatMS {
		return nil
	}
	result, err := transaction.ExecContext(ctx, `
		UPDATE supervisor_instances
		SET heartbeat_at_ms = ?
		WHERE owner_epoch = ? AND status = 'active' AND heartbeat_at_ms = ?
	`, heartbeatAtMS, ownerEpoch, currentHeartbeatMS)
	if err != nil {
		return fmt.Errorf("heartbeat supervisor epoch %q: %w", ownerEpoch, err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "heartbeat supervisor"); err != nil {
		return err
	}
	return nil
}

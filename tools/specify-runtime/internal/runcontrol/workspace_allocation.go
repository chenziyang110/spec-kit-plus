package runcontrol

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"
)

// BeginWorkspaceAllocation records idempotent intent for Git mutations that
// happen before an Attempt and its fence exist.
func (store *Store) BeginWorkspaceAllocation(
	ctx context.Context,
	params BeginWorkspaceAllocationParams,
) (WorkspaceAllocation, bool, error) {
	if err := validateBeginWorkspaceAllocationParams(params); err != nil {
		return WorkspaceAllocation{}, false, err
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return WorkspaceAllocation{}, false, fmt.Errorf("begin workspace allocation journal: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, tx, store.ownerEpoch); err != nil {
		return WorkspaceAllocation{}, false, err
	}
	if existing, readErr := readWorkspaceAllocationByIdempotencyKey(ctx, tx, params.IdempotencyKey); readErr == nil {
		if !workspaceAllocationMatchesRequest(existing, params) {
			return WorkspaceAllocation{}, false, fmt.Errorf("%w: key %q identifies a different workspace allocation", ErrIdempotencyConflict, params.IdempotencyKey)
		}
		if err := tx.Commit(); err != nil {
			return WorkspaceAllocation{}, false, fmt.Errorf("commit workspace allocation replay: %w", err)
		}
		return existing, true, nil
	} else if !errors.Is(readErr, ErrNotFound) {
		return WorkspaceAllocation{}, false, fmt.Errorf("inspect workspace allocation replay: %w", readErr)
	}

	run, err := readRunTx(ctx, tx, params.RunID)
	if err != nil {
		return WorkspaceAllocation{}, false, err
	}
	workspace, err := readWorkspaceTx(ctx, tx, params.WorkspaceID)
	if err != nil {
		return WorkspaceAllocation{}, false, err
	}
	if workspace.RunID != run.RunID {
		return WorkspaceAllocation{}, false, fmt.Errorf("%w: workspace %q does not belong to run %q", ErrInvalidArgument, workspace.WorkspaceID, run.RunID)
	}
	if run.OwnerEpoch != store.ownerEpoch {
		return WorkspaceAllocation{}, false, fmt.Errorf("%w: run %q is owned by another supervisor", ErrStaleFence, run.RunID)
	}
	if run.Revision != params.ExpectedRunRevision || workspace.Revision != params.ExpectedWorkspaceRevision {
		return WorkspaceAllocation{}, false, fmt.Errorf("%w: run or workspace revision changed", ErrRevisionConflict)
	}
	if run.Status != RunAllocating || workspace.Status != WorkspaceAllocating {
		return WorkspaceAllocation{}, false, fmt.Errorf("%w: run and workspace must both be allocating", ErrInvalidTransition)
	}

	nowMS := time.Now().UTC().UnixMilli()
	allocation := WorkspaceAllocation{
		AllocationID:        params.AllocationID,
		RunID:               run.RunID,
		WorkspaceID:         workspace.WorkspaceID,
		WorkspaceGeneration: workspace.Generation,
		OwnerEpoch:          store.ownerEpoch,
		RunRevision:         run.Revision,
		WorkspaceRevision:   workspace.Revision,
		IdempotencyKey:      params.IdempotencyKey,
		RequestSHA256:       params.RequestSHA256,
		Status:              WorkspaceAllocationPrepared,
		Revision:            1,
		CreatedAtMS:         nowMS,
		UpdatedAtMS:         nowMS,
	}
	result, err := tx.ExecContext(ctx, `
		INSERT INTO workspace_allocations (
			allocation_id, run_id, workspace_id, workspace_generation,
			owner_epoch, run_revision, workspace_revision,
			idempotency_key, request_sha256, status, reason, revision,
			created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?)
		ON CONFLICT(idempotency_key) DO NOTHING
	`, allocation.AllocationID, allocation.RunID, allocation.WorkspaceID,
		allocation.WorkspaceGeneration, allocation.OwnerEpoch, allocation.RunRevision,
		allocation.WorkspaceRevision, allocation.IdempotencyKey,
		allocation.RequestSHA256, allocation.Status, allocation.Revision,
		allocation.CreatedAtMS, allocation.UpdatedAtMS)
	if err != nil {
		if isUniqueConstraintError(err) {
			return WorkspaceAllocation{}, false, fmt.Errorf("%w: allocation %q or workspace %q", ErrAlreadyExists, allocation.AllocationID, allocation.WorkspaceID)
		}
		return WorkspaceAllocation{}, false, fmt.Errorf("insert workspace allocation: %w", err)
	}
	inserted, err := result.RowsAffected()
	if err != nil {
		return WorkspaceAllocation{}, false, fmt.Errorf("count inserted workspace allocations: %w", err)
	}
	if inserted == 0 {
		existing, err := readWorkspaceAllocationByIdempotencyKey(ctx, tx, params.IdempotencyKey)
		if err != nil {
			return WorkspaceAllocation{}, false, fmt.Errorf("read workspace allocation replay: %w", err)
		}
		if !workspaceAllocationMatchesRequest(existing, params) {
			return WorkspaceAllocation{}, false, fmt.Errorf("%w: key %q identifies a different workspace allocation", ErrIdempotencyConflict, params.IdempotencyKey)
		}
		if err := tx.Commit(); err != nil {
			return WorkspaceAllocation{}, false, fmt.Errorf("commit workspace allocation replay: %w", err)
		}
		return existing, true, nil
	}
	if inserted != 1 {
		return WorkspaceAllocation{}, false, fmt.Errorf("insert workspace allocation affected %d rows", inserted)
	}
	if err := appendWorkspaceAllocationEventTx(ctx, tx, allocation, "workspace-allocation.prepared", "allocation intent recorded"); err != nil {
		return WorkspaceAllocation{}, false, err
	}
	if err := tx.Commit(); err != nil {
		return WorkspaceAllocation{}, false, fmt.Errorf("commit workspace allocation journal: %w", err)
	}
	return allocation, false, nil
}

func (store *Store) GetWorkspaceAllocation(ctx context.Context, allocationID string) (WorkspaceAllocation, error) {
	if strings.TrimSpace(allocationID) == "" {
		return WorkspaceAllocation{}, fmt.Errorf("%w: allocation id is required", ErrInvalidArgument)
	}
	return readWorkspaceAllocationTx(ctx, store.db, allocationID)
}

// StartWorkspaceAllocation marks the boundary immediately before Git mutation.
func (store *Store) StartWorkspaceAllocation(ctx context.Context, allocationID string, expectedRevision int64) (WorkspaceAllocation, error) {
	if strings.TrimSpace(allocationID) == "" || expectedRevision <= 0 {
		return WorkspaceAllocation{}, fmt.Errorf("%w: allocation id and positive expected revision are required", ErrInvalidArgument)
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return WorkspaceAllocation{}, fmt.Errorf("begin start workspace allocation: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, tx, store.ownerEpoch); err != nil {
		return WorkspaceAllocation{}, err
	}

	allocation, err := readWorkspaceAllocationTx(ctx, tx, allocationID)
	if err != nil {
		return WorkspaceAllocation{}, err
	}
	if allocation.Revision != expectedRevision {
		return WorkspaceAllocation{}, fmt.Errorf("%w: workspace allocation revision is %d, expected %d", ErrRevisionConflict, allocation.Revision, expectedRevision)
	}
	if allocation.OwnerEpoch != store.ownerEpoch {
		return WorkspaceAllocation{}, fmt.Errorf("%w: workspace allocation %q is owned by another supervisor", ErrStaleFence, allocation.AllocationID)
	}
	run, err := readRunTx(ctx, tx, allocation.RunID)
	if err != nil {
		return WorkspaceAllocation{}, err
	}
	workspace, err := readWorkspaceTx(ctx, tx, allocation.WorkspaceID)
	if err != nil {
		return WorkspaceAllocation{}, err
	}
	if run.OwnerEpoch != store.ownerEpoch || run.Status != RunAllocating || workspace.Status != WorkspaceAllocating {
		return WorkspaceAllocation{}, fmt.Errorf("%w: allocation execution authority is no longer current", ErrStaleFence)
	}
	if run.Revision != allocation.RunRevision || workspace.Revision != allocation.WorkspaceRevision {
		return WorkspaceAllocation{}, fmt.Errorf("%w: allocation aggregate revisions changed", ErrRevisionConflict)
	}
	if allocation.Status != WorkspaceAllocationPrepared && allocation.Status != WorkspaceAllocationOutcomeUnknown {
		return WorkspaceAllocation{}, fmt.Errorf("%w: cannot start allocation %q from %q", ErrInvalidTransition, allocation.AllocationID, allocation.Status)
	}
	if err := updateWorkspaceAllocationStatusTx(ctx, tx, &allocation, WorkspaceAllocationExecuting, "Git mutation starting", time.Now().UTC().UnixMilli()); err != nil {
		return WorkspaceAllocation{}, err
	}
	if err := tx.Commit(); err != nil {
		return WorkspaceAllocation{}, fmt.Errorf("commit start workspace allocation: %w", err)
	}
	return allocation, nil
}

// CompleteWorkspaceAllocation makes the journal outcome and the executable
// Run/Activity/Workspace state visible atomically.
func (store *Store) CompleteWorkspaceAllocation(
	ctx context.Context,
	params CompleteWorkspaceAllocationParams,
) (WorkspaceAllocation, PreparedExecution, error) {
	if strings.TrimSpace(params.AllocationID) == "" || params.ExpectedAllocationRevision <= 0 {
		return WorkspaceAllocation{}, PreparedExecution{}, fmt.Errorf("%w: allocation id and positive expected revision are required", ErrInvalidArgument)
	}
	if err := validatePrepareExecutionParams(params.Execution); err != nil {
		return WorkspaceAllocation{}, PreparedExecution{}, err
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return WorkspaceAllocation{}, PreparedExecution{}, fmt.Errorf("begin complete workspace allocation: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, tx, store.ownerEpoch); err != nil {
		return WorkspaceAllocation{}, PreparedExecution{}, err
	}

	allocation, err := readWorkspaceAllocationTx(ctx, tx, params.AllocationID)
	if err != nil {
		return WorkspaceAllocation{}, PreparedExecution{}, err
	}
	if allocation.Revision != params.ExpectedAllocationRevision {
		return WorkspaceAllocation{}, PreparedExecution{}, fmt.Errorf("%w: workspace allocation revision is %d, expected %d", ErrRevisionConflict, allocation.Revision, params.ExpectedAllocationRevision)
	}
	if allocation.OwnerEpoch != store.ownerEpoch {
		return WorkspaceAllocation{}, PreparedExecution{}, fmt.Errorf("%w: workspace allocation %q is owned by another supervisor", ErrStaleFence, allocation.AllocationID)
	}
	if allocation.Status != WorkspaceAllocationExecuting && allocation.Status != WorkspaceAllocationOutcomeUnknown {
		return WorkspaceAllocation{}, PreparedExecution{}, fmt.Errorf("%w: cannot complete allocation %q from %q", ErrInvalidTransition, allocation.AllocationID, allocation.Status)
	}
	if allocation.RunID != params.Execution.RunID || allocation.WorkspaceID != params.Execution.WorkspaceID {
		return WorkspaceAllocation{}, PreparedExecution{}, fmt.Errorf("%w: allocation and execution bindings differ", ErrWorkspaceBinding)
	}
	run, err := readRunTx(ctx, tx, allocation.RunID)
	if err != nil {
		return WorkspaceAllocation{}, PreparedExecution{}, err
	}
	workspace, err := readWorkspaceTx(ctx, tx, allocation.WorkspaceID)
	if err != nil {
		return WorkspaceAllocation{}, PreparedExecution{}, err
	}
	if run.OwnerEpoch != store.ownerEpoch || run.Status != RunAllocating || workspace.Status != WorkspaceAllocating {
		return WorkspaceAllocation{}, PreparedExecution{}, fmt.Errorf("%w: allocation completion authority is no longer current", ErrStaleFence)
	}
	if run.Revision != allocation.RunRevision || workspace.Revision != allocation.WorkspaceRevision {
		return WorkspaceAllocation{}, PreparedExecution{}, fmt.Errorf("%w: allocation aggregate revisions changed", ErrRevisionConflict)
	}
	prepared, err := prepareExecutionTx(ctx, tx, store.ownerEpoch, params.Execution)
	if err != nil {
		return WorkspaceAllocation{}, PreparedExecution{}, err
	}
	if err := updateWorkspaceAllocationStatusTx(ctx, tx, &allocation, WorkspaceAllocationSucceeded, "Git workspace materialized", time.Now().UTC().UnixMilli()); err != nil {
		return WorkspaceAllocation{}, PreparedExecution{}, err
	}
	if err := tx.Commit(); err != nil {
		return WorkspaceAllocation{}, PreparedExecution{}, fmt.Errorf("commit complete workspace allocation: %w", err)
	}
	return allocation, prepared, nil
}

func validateBeginWorkspaceAllocationParams(params BeginWorkspaceAllocationParams) error {
	required := map[string]string{
		"allocation_id":   params.AllocationID,
		"run_id":          params.RunID,
		"workspace_id":    params.WorkspaceID,
		"idempotency_key": params.IdempotencyKey,
		"request_sha256":  params.RequestSHA256,
	}
	for name, value := range required {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%w: %s is required", ErrInvalidArgument, name)
		}
	}
	if params.ExpectedRunRevision <= 0 || params.ExpectedWorkspaceRevision <= 0 {
		return fmt.Errorf("%w: expected revisions must be positive", ErrInvalidArgument)
	}
	if !validSHA256(params.RequestSHA256) {
		return fmt.Errorf("%w: request_sha256 must be a lowercase sha256 digest", ErrInvalidArgument)
	}
	return nil
}

func readWorkspaceAllocationTx(ctx context.Context, querier rowQuerier, allocationID string) (WorkspaceAllocation, error) {
	row := querier.QueryRowContext(ctx, `
		SELECT allocation_id, run_id, workspace_id, workspace_generation,
		       owner_epoch, run_revision, workspace_revision,
		       idempotency_key, request_sha256, status, reason, revision,
		       created_at_ms, updated_at_ms
		FROM workspace_allocations WHERE allocation_id = ?
	`, allocationID)
	return scanWorkspaceAllocation(row, allocationID)
}

func readWorkspaceAllocationByIdempotencyKey(ctx context.Context, querier rowQuerier, idempotencyKey string) (WorkspaceAllocation, error) {
	row := querier.QueryRowContext(ctx, `
		SELECT allocation_id, run_id, workspace_id, workspace_generation,
		       owner_epoch, run_revision, workspace_revision,
		       idempotency_key, request_sha256, status, reason, revision,
		       created_at_ms, updated_at_ms
		FROM workspace_allocations WHERE idempotency_key = ?
	`, idempotencyKey)
	return scanWorkspaceAllocation(row, idempotencyKey)
}

func scanWorkspaceAllocation(row *sql.Row, identity string) (WorkspaceAllocation, error) {
	var allocation WorkspaceAllocation
	err := row.Scan(
		&allocation.AllocationID, &allocation.RunID, &allocation.WorkspaceID,
		&allocation.WorkspaceGeneration, &allocation.OwnerEpoch,
		&allocation.RunRevision, &allocation.WorkspaceRevision,
		&allocation.IdempotencyKey, &allocation.RequestSHA256,
		&allocation.Status, &allocation.Reason, &allocation.Revision,
		&allocation.CreatedAtMS, &allocation.UpdatedAtMS,
	)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return WorkspaceAllocation{}, fmt.Errorf("%w: workspace allocation %q", ErrNotFound, identity)
		}
		return WorkspaceAllocation{}, fmt.Errorf("read workspace allocation %q: %w", identity, err)
	}
	return allocation, nil
}

func workspaceAllocationMatchesRequest(allocation WorkspaceAllocation, params BeginWorkspaceAllocationParams) bool {
	return allocation.AllocationID == params.AllocationID &&
		allocation.RunID == params.RunID &&
		allocation.WorkspaceID == params.WorkspaceID &&
		allocation.RunRevision == params.ExpectedRunRevision &&
		allocation.WorkspaceRevision == params.ExpectedWorkspaceRevision &&
		allocation.RequestSHA256 == params.RequestSHA256
}

func updateWorkspaceAllocationStatusTx(
	ctx context.Context,
	tx *sql.Tx,
	allocation *WorkspaceAllocation,
	status WorkspaceAllocationStatus,
	reason string,
	nowMS int64,
) error {
	result, err := tx.ExecContext(ctx, `
		UPDATE workspace_allocations
		SET status = ?, reason = ?, revision = revision + 1, updated_at_ms = ?
		WHERE allocation_id = ? AND revision = ? AND status = ? AND owner_epoch = ?
	`, status, reason, nowMS, allocation.AllocationID, allocation.Revision, allocation.Status, allocation.OwnerEpoch)
	if err != nil {
		return fmt.Errorf("update workspace allocation %q: %w", allocation.AllocationID, err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "update workspace allocation"); err != nil {
		return err
	}
	allocation.Status = status
	allocation.Reason = reason
	allocation.Revision++
	allocation.UpdatedAtMS = nowMS
	return appendWorkspaceAllocationEventTx(ctx, tx, *allocation, "workspace-allocation."+string(status), reason)
}

func markWorkspaceAllocationsOutcomeUnknownForRunTx(ctx context.Context, tx *sql.Tx, runID, reason string, nowMS int64) error {
	rows, err := tx.QueryContext(ctx, `
		SELECT allocation_id FROM workspace_allocations
		WHERE run_id = ? AND status IN (?, ?)
		ORDER BY allocation_id
	`, runID, WorkspaceAllocationPrepared, WorkspaceAllocationExecuting)
	if err != nil {
		return fmt.Errorf("query live workspace allocations for run %q: %w", runID, err)
	}
	var allocationIDs []string
	for rows.Next() {
		var allocationID string
		if err := rows.Scan(&allocationID); err != nil {
			_ = rows.Close()
			return fmt.Errorf("scan live workspace allocation: %w", err)
		}
		allocationIDs = append(allocationIDs, allocationID)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return fmt.Errorf("iterate live workspace allocations: %w", err)
	}
	if err := rows.Close(); err != nil {
		return fmt.Errorf("close live workspace allocations query: %w", err)
	}
	for _, allocationID := range allocationIDs {
		allocation, err := readWorkspaceAllocationTx(ctx, tx, allocationID)
		if err != nil {
			return err
		}
		if err := updateWorkspaceAllocationStatusTx(ctx, tx, &allocation, WorkspaceAllocationOutcomeUnknown, reason, nowMS); err != nil {
			return err
		}
	}
	return nil
}

func appendWorkspaceAllocationEventTx(
	ctx context.Context,
	tx *sql.Tx,
	allocation WorkspaceAllocation,
	eventType, reason string,
) error {
	payload, err := json.Marshal(struct {
		RunID       string                    `json:"run_id"`
		WorkspaceID string                    `json:"workspace_id"`
		Generation  int64                     `json:"generation"`
		Status      WorkspaceAllocationStatus `json:"status"`
	}{
		RunID:       allocation.RunID,
		WorkspaceID: allocation.WorkspaceID,
		Generation:  allocation.WorkspaceGeneration,
		Status:      allocation.Status,
	})
	if err != nil {
		return fmt.Errorf("encode workspace allocation event: %w", err)
	}
	_, err = tx.ExecContext(ctx, `
		INSERT INTO events (
			aggregate_type, aggregate_id, aggregate_revision,
			event_type, reason, payload_json, created_at_ms
		) VALUES ('workspace_allocation', ?, ?, ?, ?, ?, ?)
	`, allocation.AllocationID, allocation.Revision, eventType, reason, string(payload), allocation.UpdatedAtMS)
	if err != nil {
		return fmt.Errorf("append workspace allocation event: %w", err)
	}
	return nil
}

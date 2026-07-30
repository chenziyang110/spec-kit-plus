package runcontrol

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"
)

// BeginOperation records the durable intent for an action that cannot be
// completed entirely inside one SQLite transaction. Reusing a key is safe only
// when it names the exact same request identity.
func (store *Store) BeginOperation(ctx context.Context, params BeginOperationParams) (Operation, bool, error) {
	if err := validateBeginOperationParams(params); err != nil {
		return Operation{}, false, err
	}

	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Operation{}, false, fmt.Errorf("begin operation transaction: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()

	now := time.Now().UTC().UnixMilli()
	run, err := readRunTx(ctx, transaction, params.RunID)
	if err != nil {
		return Operation{}, false, err
	}
	attempt, err := readAttemptTx(ctx, transaction, params.AttemptID)
	if err != nil {
		return Operation{}, false, err
	}
	if attempt.RunID != run.RunID {
		return Operation{}, false, fmt.Errorf("%w: attempt %q does not belong to run %q", ErrStaleFence, attempt.AttemptID, run.RunID)
	}
	if err := validateAttemptAuthority(attempt, run, params.Fence, store.ownerEpoch); err != nil {
		return Operation{}, false, err
	}
	if run.Revision != params.ExpectedRunRevision {
		return Operation{}, false, fmt.Errorf("%w: run %q revision is %d, expected %d", ErrRevisionConflict, run.RunID, run.Revision, params.ExpectedRunRevision)
	}
	if run.Status != RunActive || (attempt.Status != AttemptActive && attempt.Status != AttemptSealing) {
		return Operation{}, false, fmt.Errorf("%w: attempt %q does not hold active execution authority", ErrStaleFence, attempt.AttemptID)
	}
	if attempt.LeaseUntilMS <= now {
		return Operation{}, false, fmt.Errorf("%w: attempt %q lease has expired", ErrStaleFence, attempt.AttemptID)
	}
	switch params.AggregateType {
	case "run":
		if params.AggregateID != run.RunID {
			return Operation{}, false, fmt.Errorf("%w: run aggregate does not match attempt authority", ErrStaleFence)
		}
	case "activity":
		if params.AggregateID != attempt.ActivityID {
			return Operation{}, false, fmt.Errorf("%w: activity aggregate does not match attempt authority", ErrStaleFence)
		}
	case "workspace":
		if params.AggregateID != attempt.WorkspaceID {
			return Operation{}, false, fmt.Errorf("%w: workspace aggregate does not match attempt authority", ErrStaleFence)
		}
	}
	operation := Operation{
		OperationID:    params.OperationID,
		Kind:           params.Kind,
		AggregateType:  params.AggregateType,
		AggregateID:    params.AggregateID,
		RunID:          params.RunID,
		AttemptID:      params.AttemptID,
		ActivityID:     attempt.ActivityID,
		WorkspaceID:    attempt.WorkspaceID,
		OwnerEpoch:     store.ownerEpoch,
		Fence:          params.Fence,
		RunRevision:    params.ExpectedRunRevision,
		IdempotencyKey: params.IdempotencyKey,
		RequestSHA256:  params.RequestSHA256,
		Status:         OperationPrepared,
		Revision:       1,
		CreatedAtMS:    now,
		UpdatedAtMS:    now,
	}
	result, err := transaction.ExecContext(ctx, `
		INSERT INTO operations (
			operation_id, kind, aggregate_type, aggregate_id,
			run_id, attempt_id, activity_id, workspace_id,
			owner_epoch, fence, run_revision,
			idempotency_key, request_sha256, status, revision,
			created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(idempotency_key) DO NOTHING
	`, operation.OperationID, operation.Kind, operation.AggregateType, operation.AggregateID,
		operation.RunID, operation.AttemptID, operation.ActivityID, operation.WorkspaceID,
		operation.OwnerEpoch, operation.Fence, operation.RunRevision,
		operation.IdempotencyKey, operation.RequestSHA256, operation.Status, operation.Revision,
		operation.CreatedAtMS, operation.UpdatedAtMS)
	if err != nil {
		if isUniqueConstraintError(err) {
			return Operation{}, false, fmt.Errorf("%w: operation %q", ErrAlreadyExists, params.OperationID)
		}
		return Operation{}, false, fmt.Errorf("insert operation: %w", err)
	}
	inserted, err := result.RowsAffected()
	if err != nil {
		return Operation{}, false, fmt.Errorf("count inserted operations: %w", err)
	}
	if inserted == 0 {
		existing, err := readOperationByIdempotencyKey(ctx, transaction, params.IdempotencyKey)
		if err != nil {
			return Operation{}, false, fmt.Errorf("read idempotent operation replay: %w", err)
		}
		if !operationMatchesRequest(existing, params) ||
			existing.ActivityID != attempt.ActivityID || existing.WorkspaceID != attempt.WorkspaceID {
			return Operation{}, false, fmt.Errorf("%w: key %q identifies a different request", ErrIdempotencyConflict, params.IdempotencyKey)
		}
		if err := transaction.Commit(); err != nil {
			return Operation{}, false, fmt.Errorf("commit operation replay: %w", err)
		}
		return existing, true, nil
	}
	if inserted != 1 {
		return Operation{}, false, fmt.Errorf("insert operation affected %d rows", inserted)
	}
	if err := transaction.Commit(); err != nil {
		return Operation{}, false, fmt.Errorf("commit operation: %w", err)
	}
	return operation, false, nil
}

func validateBeginOperationParams(params BeginOperationParams) error {
	required := map[string]string{
		"operation_id":    params.OperationID,
		"kind":            params.Kind,
		"aggregate_type":  params.AggregateType,
		"aggregate_id":    params.AggregateID,
		"run_id":          params.RunID,
		"attempt_id":      params.AttemptID,
		"idempotency_key": params.IdempotencyKey,
		"request_sha256":  params.RequestSHA256,
	}
	for name, value := range required {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%w: %s is required", ErrInvalidArgument, name)
		}
	}
	if !validSHA256(params.RequestSHA256) {
		return fmt.Errorf("%w: request_sha256 must be a lowercase sha256 digest", ErrInvalidArgument)
	}
	if params.Fence <= 0 {
		return fmt.Errorf("%w: fence must be positive", ErrInvalidArgument)
	}
	if params.ExpectedRunRevision <= 0 {
		return fmt.Errorf("%w: expected_run_revision must be positive", ErrInvalidArgument)
	}
	return nil
}

func readOperationByIdempotencyKey(ctx context.Context, querier interface {
	QueryRowContext(context.Context, string, ...any) *sql.Row
}, idempotencyKey string) (Operation, error) {
	row := querier.QueryRowContext(ctx, `
		SELECT operation_id, kind, aggregate_type, aggregate_id,
		       run_id, attempt_id, activity_id, workspace_id,
		       owner_epoch, fence, run_revision,
		       idempotency_key, request_sha256, status, revision,
		       created_at_ms, updated_at_ms
		FROM operations
		WHERE idempotency_key = ?
	`, idempotencyKey)
	var operation Operation
	err := row.Scan(
		&operation.OperationID,
		&operation.Kind,
		&operation.AggregateType,
		&operation.AggregateID,
		&operation.RunID,
		&operation.AttemptID,
		&operation.ActivityID,
		&operation.WorkspaceID,
		&operation.OwnerEpoch,
		&operation.Fence,
		&operation.RunRevision,
		&operation.IdempotencyKey,
		&operation.RequestSHA256,
		&operation.Status,
		&operation.Revision,
		&operation.CreatedAtMS,
		&operation.UpdatedAtMS,
	)
	if err != nil {
		return Operation{}, err
	}
	return operation, nil
}

func operationMatchesRequest(operation Operation, params BeginOperationParams) bool {
	return operation.Kind == params.Kind &&
		operation.AggregateType == params.AggregateType &&
		operation.AggregateID == params.AggregateID &&
		operation.RunID == params.RunID &&
		operation.AttemptID == params.AttemptID &&
		operation.Fence == params.Fence &&
		operation.RunRevision == params.ExpectedRunRevision &&
		operation.RequestSHA256 == params.RequestSHA256
}

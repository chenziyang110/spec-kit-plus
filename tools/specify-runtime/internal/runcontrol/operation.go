package runcontrol

import (
	"context"
	"database/sql"
	"errors"
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

	existing, err := readOperationByIdempotencyKey(ctx, transaction, params.IdempotencyKey)
	if err == nil {
		if !operationMatchesRequest(existing, params) {
			return Operation{}, false, fmt.Errorf("%w: key %q identifies a different request", ErrIdempotencyConflict, params.IdempotencyKey)
		}
		if err := transaction.Commit(); err != nil {
			return Operation{}, false, fmt.Errorf("commit operation replay: %w", err)
		}
		return existing, true, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return Operation{}, false, err
	}

	now := time.Now().UTC().UnixMilli()
	operation := Operation{
		OperationID:    params.OperationID,
		Kind:           params.Kind,
		AggregateType:  params.AggregateType,
		AggregateID:    params.AggregateID,
		IdempotencyKey: params.IdempotencyKey,
		RequestSHA256:  params.RequestSHA256,
		Status:         OperationPrepared,
		Revision:       1,
		CreatedAtMS:    now,
		UpdatedAtMS:    now,
	}
	_, err = transaction.ExecContext(ctx, `
		INSERT INTO operations (
			operation_id, kind, aggregate_type, aggregate_id,
			idempotency_key, request_sha256, status, revision,
			created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, operation.OperationID, operation.Kind, operation.AggregateType, operation.AggregateID,
		operation.IdempotencyKey, operation.RequestSHA256, operation.Status, operation.Revision,
		operation.CreatedAtMS, operation.UpdatedAtMS)
	if err != nil {
		return Operation{}, false, fmt.Errorf("insert operation: %w", err)
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
		"idempotency_key": params.IdempotencyKey,
		"request_sha256":  params.RequestSHA256,
	}
	for name, value := range required {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%s is required", name)
		}
	}
	if !validSHA256(params.RequestSHA256) {
		return fmt.Errorf("request_sha256 must be a lowercase sha256 digest")
	}
	return nil
}

func readOperationByIdempotencyKey(ctx context.Context, querier interface {
	QueryRowContext(context.Context, string, ...any) *sql.Row
}, idempotencyKey string) (Operation, error) {
	row := querier.QueryRowContext(ctx, `
		SELECT operation_id, kind, aggregate_type, aggregate_id,
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
	return operation.OperationID == params.OperationID &&
		operation.Kind == params.Kind &&
		operation.AggregateType == params.AggregateType &&
		operation.AggregateID == params.AggregateID &&
		operation.RequestSHA256 == params.RequestSHA256
}

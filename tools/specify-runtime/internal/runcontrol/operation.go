package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
)

const attemptLaunchOperationKind = "attempt.launch"

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
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return Operation{}, false, err
	}

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

// BeginAttemptLaunch atomically claims the one permitted process launch for a
// managed Attempt. The executing operation is committed before the caller may
// spawn, so concurrent supervisors cannot both cross the side-effect boundary.
func (store *Store) BeginAttemptLaunch(
	ctx context.Context,
	params BeginAttemptLaunchParams,
) (Operation, bool, error) {
	if err := validateBeginAttemptLaunchParams(params); err != nil {
		return Operation{}, false, err
	}

	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Operation{}, false, fmt.Errorf("begin attempt launch transaction: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return Operation{}, false, err
	}

	attempt, err := readAttemptTx(ctx, transaction, params.AttemptID)
	if err != nil {
		return Operation{}, false, err
	}
	run, err := readRunTx(ctx, transaction, attempt.RunID)
	if err != nil {
		return Operation{}, false, err
	}
	if err := validateAttemptAuthority(attempt, run, params.Fence, store.ownerEpoch); err != nil {
		return Operation{}, false, err
	}

	existing, err := readOperationByIdempotencyKey(ctx, transaction, params.IdempotencyKey)
	switch {
	case err == nil:
		if !attemptLaunchMatchesRequest(existing, attempt, params, store.ownerEpoch) {
			return Operation{}, false, fmt.Errorf(
				"%w: key %q identifies a different attempt launch",
				ErrIdempotencyConflict,
				params.IdempotencyKey,
			)
		}
		if err := transaction.Commit(); err != nil {
			return Operation{}, false, fmt.Errorf("commit attempt launch replay: %w", err)
		}
		return existing, true, nil
	case !errors.Is(err, sql.ErrNoRows):
		return Operation{}, false, fmt.Errorf("read attempt launch replay: %w", err)
	}

	activity, err := readActivityTx(ctx, transaction, attempt.ActivityID)
	if err != nil {
		return Operation{}, false, err
	}
	workspace, err := readWorkspaceTx(ctx, transaction, attempt.WorkspaceID)
	if err != nil {
		return Operation{}, false, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	if err := validateAttemptLaunchReady(attempt, run, activity, workspace, nowMS); err != nil {
		return Operation{}, false, err
	}

	operation := Operation{
		OperationID:    params.OperationID,
		Kind:           attemptLaunchOperationKind,
		AggregateType:  "workspace",
		AggregateID:    attempt.WorkspaceID,
		RunID:          run.RunID,
		AttemptID:      attempt.AttemptID,
		ActivityID:     attempt.ActivityID,
		WorkspaceID:    attempt.WorkspaceID,
		OwnerEpoch:     store.ownerEpoch,
		Fence:          params.Fence,
		RunRevision:    run.Revision,
		IdempotencyKey: params.IdempotencyKey,
		RequestSHA256:  params.RequestSHA256,
		Status:         OperationExecuting,
		Revision:       1,
		CreatedAtMS:    nowMS,
		UpdatedAtMS:    nowMS,
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
			return Operation{}, false, fmt.Errorf(
				"%w: attempt %q already has a live launch claim",
				ErrAlreadyExists,
				attempt.AttemptID,
			)
		}
		return Operation{}, false, fmt.Errorf("insert attempt launch: %w", err)
	}
	inserted, err := result.RowsAffected()
	if err != nil {
		return Operation{}, false, fmt.Errorf("count inserted attempt launches: %w", err)
	}
	if inserted == 0 {
		existing, err := readOperationByIdempotencyKey(ctx, transaction, params.IdempotencyKey)
		if err != nil {
			return Operation{}, false, fmt.Errorf("read concurrent attempt launch replay: %w", err)
		}
		if !attemptLaunchMatchesRequest(existing, attempt, params, store.ownerEpoch) {
			return Operation{}, false, fmt.Errorf(
				"%w: key %q identifies a different attempt launch",
				ErrIdempotencyConflict,
				params.IdempotencyKey,
			)
		}
		if err := transaction.Commit(); err != nil {
			return Operation{}, false, fmt.Errorf("commit concurrent attempt launch replay: %w", err)
		}
		return existing, true, nil
	}
	if inserted != 1 {
		return Operation{}, false, fmt.Errorf("insert attempt launch affected %d rows", inserted)
	}
	if err := transaction.Commit(); err != nil {
		return Operation{}, false, fmt.Errorf("commit attempt launch: %w", err)
	}
	return operation, false, nil
}

// CompleteAttemptLaunch records whether the claimed spawn definitely
// succeeded. A failed claim leaves the Attempt eligible for a fresh claim with
// a new idempotency key; a succeeded claim becomes the activation gate.
func (store *Store) CompleteAttemptLaunch(
	ctx context.Context,
	params CompleteAttemptLaunchParams,
) (Operation, error) {
	if err := validateCompleteAttemptLaunchParams(params); err != nil {
		return Operation{}, err
	}

	transaction, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Operation{}, fmt.Errorf("begin complete attempt launch transaction: %w", err)
	}
	defer func() { _ = transaction.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, transaction, store.ownerEpoch); err != nil {
		return Operation{}, err
	}

	operation, err := readOperationTx(ctx, transaction, params.OperationID)
	if err != nil {
		return Operation{}, err
	}
	if operation.Kind != attemptLaunchOperationKind {
		return Operation{}, fmt.Errorf(
			"%w: operation %q is %q, expected %q",
			ErrInvalidTransition,
			operation.OperationID,
			operation.Kind,
			attemptLaunchOperationKind,
		)
	}
	if operation.OwnerEpoch != store.ownerEpoch || operation.Fence != params.Fence {
		return Operation{}, fmt.Errorf(
			"%w: operation %q belongs to a different supervisor authority",
			ErrStaleFence,
			operation.OperationID,
		)
	}
	targetStatus := OperationFailed
	if params.Succeeded {
		targetStatus = OperationSucceeded
	}
	// A completion retry reports the durable historical spawn outcome even if
	// activation has since advanced the Run revision. The operation's own owner,
	// fence, revision, and target status are the idempotency authority here.
	if operation.Revision == params.ExpectedRevision+1 && operation.Status == targetStatus {
		if err := transaction.Commit(); err != nil {
			return Operation{}, fmt.Errorf("commit attempt launch completion replay: %w", err)
		}
		return operation, nil
	}

	attempt, err := readAttemptTx(ctx, transaction, operation.AttemptID)
	if err != nil {
		return Operation{}, err
	}
	run, err := readRunTx(ctx, transaction, operation.RunID)
	if err != nil {
		return Operation{}, err
	}
	if err := validateAttemptAuthority(attempt, run, params.Fence, store.ownerEpoch); err != nil {
		return Operation{}, err
	}
	if !attemptLaunchMatchesAuthority(operation, attempt, run) {
		return Operation{}, fmt.Errorf(
			"%w: operation %q no longer matches attempt execution bindings",
			ErrStaleFence,
			operation.OperationID,
		)
	}

	if operation.Revision != params.ExpectedRevision {
		return Operation{}, fmt.Errorf(
			"%w: operation %q revision is %d, expected %d",
			ErrRevisionConflict,
			operation.OperationID,
			operation.Revision,
			params.ExpectedRevision,
		)
	}
	if operation.Status != OperationExecuting {
		return Operation{}, fmt.Errorf(
			"%w: operation %q is %q, expected %q",
			ErrInvalidTransition,
			operation.OperationID,
			operation.Status,
			OperationExecuting,
		)
	}

	activity, err := readActivityTx(ctx, transaction, attempt.ActivityID)
	if err != nil {
		return Operation{}, err
	}
	workspace, err := readWorkspaceTx(ctx, transaction, attempt.WorkspaceID)
	if err != nil {
		return Operation{}, err
	}
	if err := validateAttemptLaunchReady(
		attempt,
		run,
		activity,
		workspace,
		time.Now().UTC().UnixMilli(),
	); err != nil {
		return Operation{}, err
	}

	nowMS := time.Now().UTC().UnixMilli()
	result, err := transaction.ExecContext(ctx, `
		UPDATE operations
		SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE operation_id = ? AND revision = ? AND status = ?
		  AND owner_epoch = ? AND fence = ?
	`, targetStatus, nowMS, operation.OperationID, operation.Revision,
		OperationExecuting, store.ownerEpoch, params.Fence)
	if err != nil {
		return Operation{}, fmt.Errorf("complete attempt launch: %w", err)
	}
	if err := requireOneCASRow(result, ErrStaleFence, "complete attempt launch"); err != nil {
		return Operation{}, err
	}
	operation.Status = targetStatus
	operation.Revision++
	operation.UpdatedAtMS = nowMS
	if err := transaction.Commit(); err != nil {
		return Operation{}, fmt.Errorf("commit attempt launch completion: %w", err)
	}
	return operation, nil
}

func validateBeginAttemptLaunchParams(params BeginAttemptLaunchParams) error {
	required := map[string]string{
		"operation_id":    params.OperationID,
		"attempt_id":      params.AttemptID,
		"idempotency_key": params.IdempotencyKey,
		"request_sha256":  params.RequestSHA256,
	}
	for name, value := range required {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%w: %s is required", ErrInvalidArgument, name)
		}
	}
	if params.Fence <= 0 {
		return fmt.Errorf("%w: fence must be positive", ErrInvalidArgument)
	}
	if !validSHA256(params.RequestSHA256) {
		return fmt.Errorf("%w: request_sha256 must be a lowercase sha256 digest", ErrInvalidArgument)
	}
	return nil
}

func validateCompleteAttemptLaunchParams(params CompleteAttemptLaunchParams) error {
	if strings.TrimSpace(params.OperationID) == "" {
		return fmt.Errorf("%w: operation_id is required", ErrInvalidArgument)
	}
	if params.Fence <= 0 {
		return fmt.Errorf("%w: fence must be positive", ErrInvalidArgument)
	}
	if params.ExpectedRevision <= 0 {
		return fmt.Errorf("%w: expected_revision must be positive", ErrInvalidArgument)
	}
	return nil
}

func validateAttemptLaunchReady(
	attempt Attempt,
	run Run,
	activity Activity,
	workspace Workspace,
	nowMS int64,
) error {
	if attempt.Status != AttemptIssued || attempt.ExecutionMode != ExecutionManaged {
		return fmt.Errorf(
			"%w: attempt %q is not an issued managed attempt",
			ErrInvalidTransition,
			attempt.AttemptID,
		)
	}
	if run.Status != RunReady || activity.Status != ActivityReady || workspace.Status != WorkspaceReady {
		return fmt.Errorf(
			"%w: attempt %q execution resources are not ready",
			ErrInvalidTransition,
			attempt.AttemptID,
		)
	}
	if activity.RunID != run.RunID || workspace.RunID != run.RunID ||
		attempt.RunID != run.RunID || attempt.ActivityID != activity.ActivityID ||
		attempt.WorkspaceID != workspace.WorkspaceID ||
		workspace.Generation != attempt.WorkspaceGeneration {
		return fmt.Errorf(
			"%w: attempt %q execution bindings are inconsistent",
			ErrStaleFence,
			attempt.AttemptID,
		)
	}
	if attempt.LeaseUntilMS <= nowMS {
		return fmt.Errorf("%w: attempt %q lease has expired", ErrStaleFence, attempt.AttemptID)
	}
	return nil
}

func attemptLaunchMatchesRequest(
	operation Operation,
	attempt Attempt,
	params BeginAttemptLaunchParams,
	ownerEpoch string,
) bool {
	return operation.OperationID == params.OperationID &&
		operation.Kind == attemptLaunchOperationKind &&
		operation.AggregateType == "workspace" &&
		operation.AggregateID == attempt.WorkspaceID &&
		operation.RunID == attempt.RunID &&
		operation.AttemptID == attempt.AttemptID &&
		operation.ActivityID == attempt.ActivityID &&
		operation.WorkspaceID == attempt.WorkspaceID &&
		operation.OwnerEpoch == ownerEpoch &&
		operation.Fence == params.Fence &&
		operation.IdempotencyKey == params.IdempotencyKey &&
		operation.RequestSHA256 == params.RequestSHA256
}

func attemptLaunchMatchesAuthority(operation Operation, attempt Attempt, run Run) bool {
	return operation.AggregateType == "workspace" &&
		operation.AggregateID == attempt.WorkspaceID &&
		operation.RunID == run.RunID &&
		operation.AttemptID == attempt.AttemptID &&
		operation.ActivityID == attempt.ActivityID &&
		operation.WorkspaceID == attempt.WorkspaceID &&
		operation.OwnerEpoch == attempt.OwnerEpoch &&
		operation.Fence == attempt.Fence &&
		operation.RunRevision == run.Revision
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
	return scanOperation(row)
}

func readOperationTx(ctx context.Context, querier interface {
	QueryRowContext(context.Context, string, ...any) *sql.Row
}, operationID string) (Operation, error) {
	row := querier.QueryRowContext(ctx, `
		SELECT operation_id, kind, aggregate_type, aggregate_id,
		       run_id, attempt_id, activity_id, workspace_id,
		       owner_epoch, fence, run_revision,
		       idempotency_key, request_sha256, status, revision,
		       created_at_ms, updated_at_ms
		FROM operations
		WHERE operation_id = ?
	`, operationID)
	operation, err := scanOperation(row)
	if errors.Is(err, sql.ErrNoRows) {
		return Operation{}, fmt.Errorf("%w: operation %q", ErrNotFound, operationID)
	}
	return operation, err
}

type operationScanner interface {
	Scan(...any) error
}

func scanOperation(row operationScanner) (Operation, error) {
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

func markAttemptLaunchOutcomeUnknownTx(
	ctx context.Context,
	tx *sql.Tx,
	attempt Attempt,
	nowMS int64,
) error {
	statuses := []OperationStatus{OperationPrepared, OperationExecuting}
	// A succeeded spawn is uncertain only until the Attempt activation
	// handshake completes. Once active or sealing, succeeded remains the known
	// historical launch outcome even if the Attempt is later fenced.
	if attempt.Status == AttemptIssued {
		statuses = append(statuses, OperationSucceeded)
	}
	arguments := []any{OperationOutcomeUnknown, nowMS, attempt.RunID, attempt.AttemptID}
	placeholders := make([]string, 0, len(statuses))
	for _, status := range statuses {
		placeholders = append(placeholders, "?")
		arguments = append(arguments, status)
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE operations
		SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE run_id = ? AND attempt_id = ? AND kind = 'attempt.launch'
		  AND status IN (`+strings.Join(placeholders, ", ")+`)
	`, arguments...)
	if err != nil {
		return fmt.Errorf("mark attempt launch outcome unknown: %w", err)
	}
	if _, err := result.RowsAffected(); err != nil {
		return fmt.Errorf("count attempt launch recovery updates: %w", err)
	}
	return nil
}

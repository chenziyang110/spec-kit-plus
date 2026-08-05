package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
)

var (
	ErrResourceClaimConflict = errors.New("resource claim conflicts with a live claim")
	ErrResourceClaimNotFound = ErrNotFound
	ErrResourceConflict      = ErrResourceClaimConflict
)

type ResourceType string

const (
	ResourceFilesystem     ResourceType = "filesystem"
	ResourceTCPPort        ResourceType = "tcp-port"
	ResourceDatabase       ResourceType = "database"
	ResourceSchema         ResourceType = "schema"
	ResourceService        ResourceType = "service"
	ResourceComposeProject ResourceType = "compose-project"
	ResourceTemp           ResourceType = "temp"
	ResourceCache          ResourceType = "cache"
	ResourceExternalEffect ResourceType = "external-effect"
)

type ResourceClaimMode string

const (
	ResourceClaimShared    ResourceClaimMode = "shared"
	ResourceClaimExclusive ResourceClaimMode = "exclusive"
	ResourceShared         ResourceClaimMode = ResourceClaimShared
	ResourceExclusive      ResourceClaimMode = ResourceClaimExclusive
)

type ResourceClaimStatus string

const (
	ResourceClaimActive   ResourceClaimStatus = "active"
	ResourceClaimed       ResourceClaimStatus = ResourceClaimActive
	ResourceClaimReleased ResourceClaimStatus = "released"
	ResourceReleased      ResourceClaimStatus = ResourceClaimReleased
)

type ResourceClaim struct {
	ClaimID      string
	ResourceType ResourceType
	ResourceKey  string
	RunID        string
	AttemptID    string
	ActivityID   string
	WorkspaceID  string
	OwnerEpoch   string
	Fence        int64
	Mode         ResourceClaimMode
	Status       ResourceClaimStatus
	Reason       string
	BindingJSON  string
	Revision     int64
	CreatedAtMS  int64
	UpdatedAtMS  int64
	LeaseUntilMS int64
	ReleasedAtMS int64
}

type AcquireResourceClaimParams struct {
	ClaimID       string
	ResourceType  ResourceType
	ResourceKind  ResourceType
	ResourceKey   string
	AttemptID     string
	Fence         int64
	Mode          ResourceClaimMode
	BindingJSON   string
	LeaseUntil    time.Time
	ExpectedRunID string
}

type ListResourceClaimsParams struct {
	AttemptID     string
	ResourceType  ResourceType
	ResourceKey   string
	OwnerEpoch    string
	LiveOnly      bool
	ExpectedRunID string
}

const resourceClaimSchemaSQL = `
CREATE TABLE IF NOT EXISTS resource_claims (
    claim_id TEXT PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    attempt_id TEXT NOT NULL REFERENCES attempts(attempt_id) ON DELETE RESTRICT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE RESTRICT,
    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    owner_epoch TEXT NOT NULL REFERENCES supervisor_instances(owner_epoch) ON DELETE RESTRICT,
    fence INTEGER NOT NULL CHECK (fence > 0),
    mode TEXT NOT NULL CHECK (mode IN ('shared', 'exclusive')),
    status TEXT NOT NULL CHECK (status IN ('active', 'released')),
    reason TEXT NOT NULL DEFAULT '',
    binding_json TEXT NOT NULL DEFAULT '{}',
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    lease_until_ms INTEGER NOT NULL,
    released_at_ms INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS resource_claims_attempt_lookup
    ON resource_claims(attempt_id, status, resource_type, resource_key, created_at_ms, claim_id);

CREATE INDEX IF NOT EXISTS resource_claims_resource_lookup
    ON resource_claims(resource_type, resource_key, status, mode, created_at_ms, claim_id);
`

func (store *Store) AcquireResourceClaim(
	ctx context.Context,
	params AcquireResourceClaimParams,
) (ResourceClaim, error) {
	params = normalizeAcquireResourceClaimParams(params)
	if err := validateAcquireResourceClaimParams(params); err != nil {
		return ResourceClaim{}, err
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return ResourceClaim{}, fmt.Errorf("begin resource claim transaction: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, tx, store.ownerEpoch); err != nil {
		return ResourceClaim{}, err
	}

	attempt, run, nowMS, err := requireClaimableAttemptTx(ctx, tx, store.ownerEpoch, params.AttemptID, params.Fence, params.ExpectedRunID)
	if err != nil {
		return ResourceClaim{}, err
	}

	if existing, found, err := readActiveResourceClaimForAttemptTx(
		ctx,
		tx,
		attempt.AttemptID,
		params.ResourceType,
		params.ResourceKey,
		params.Mode,
	); err != nil {
		return ResourceClaim{}, err
	} else if found {
		if err := tx.Commit(); err != nil {
			return ResourceClaim{}, fmt.Errorf("commit resource claim replay: %w", err)
		}
		return existing, nil
	}

	conflict, found, err := readConflictingResourceClaimTx(
		ctx,
		tx,
		params.ResourceType,
		params.ResourceKey,
		params.Mode,
	)
	if err != nil {
		return ResourceClaim{}, err
	}
	if found {
		return ResourceClaim{}, fmt.Errorf(
			"%w: %s/%s is held by claim %q in %s mode",
			ErrResourceClaimConflict,
			params.ResourceType,
			params.ResourceKey,
			conflict.ClaimID,
			conflict.Mode,
		)
	}

	claim := ResourceClaim{
		ClaimID:      params.ClaimID,
		ResourceType: params.ResourceType,
		ResourceKey:  params.ResourceKey,
		RunID:        run.RunID,
		AttemptID:    attempt.AttemptID,
		ActivityID:   attempt.ActivityID,
		WorkspaceID:  attempt.WorkspaceID,
		OwnerEpoch:   store.ownerEpoch,
		Fence:        attempt.Fence,
		Mode:         params.Mode,
		Status:       ResourceClaimActive,
		Reason:       "",
		BindingJSON:  params.BindingJSON,
		Revision:     1,
		CreatedAtMS:  nowMS,
		UpdatedAtMS:  nowMS,
		LeaseUntilMS: params.LeaseUntil.UTC().UnixMilli(),
		ReleasedAtMS: 0,
	}
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO resource_claims (
			claim_id, resource_type, resource_key,
			run_id, attempt_id, activity_id, workspace_id,
			owner_epoch, fence, mode, status, reason, binding_json, revision,
			created_at_ms, updated_at_ms, lease_until_ms, released_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`,
		claim.ClaimID,
		claim.ResourceType,
		claim.ResourceKey,
		claim.RunID,
		claim.AttemptID,
		claim.ActivityID,
		claim.WorkspaceID,
		claim.OwnerEpoch,
		claim.Fence,
		claim.Mode,
		claim.Status,
		claim.Reason,
		claim.BindingJSON,
		claim.Revision,
		claim.CreatedAtMS,
		claim.UpdatedAtMS,
		claim.LeaseUntilMS,
		claim.ReleasedAtMS,
	); err != nil {
		if isUniqueConstraintError(err) {
			return ResourceClaim{}, fmt.Errorf("%w: resource claim %q", ErrAlreadyExists, claim.ClaimID)
		}
		return ResourceClaim{}, fmt.Errorf("insert resource claim: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return ResourceClaim{}, fmt.Errorf("commit resource claim: %w", err)
	}
	return claim, nil
}

func (store *Store) ListResourceClaims(
	ctx context.Context,
	params ListResourceClaimsParams,
) ([]ResourceClaim, error) {
	where := make([]string, 0, 5)
	args := make([]any, 0, 5)
	if attemptID := strings.TrimSpace(params.AttemptID); attemptID != "" {
		where = append(where, "attempt_id = ?")
		args = append(args, attemptID)
	}
	if resourceType := strings.TrimSpace(string(params.ResourceType)); resourceType != "" {
		where = append(where, "resource_type = ?")
		args = append(args, resourceType)
	}
	if resourceKey := strings.TrimSpace(params.ResourceKey); resourceKey != "" {
		where = append(where, "resource_key = ?")
		args = append(args, resourceKey)
	}
	if ownerEpoch := strings.TrimSpace(params.OwnerEpoch); ownerEpoch != "" {
		where = append(where, "owner_epoch = ?")
		args = append(args, ownerEpoch)
	}
	if params.LiveOnly {
		where = append(where, "status = ?")
		args = append(args, ResourceClaimActive)
	}
	if expectedRunID := strings.TrimSpace(params.ExpectedRunID); expectedRunID != "" {
		where = append(where, "run_id = ?")
		args = append(args, expectedRunID)
	}

	query := `
		SELECT claim_id, resource_type, resource_key,
		       run_id, attempt_id, activity_id, workspace_id,
		       owner_epoch, fence, mode, status, reason, binding_json, revision,
		       created_at_ms, updated_at_ms, lease_until_ms, released_at_ms
		FROM resource_claims`
	if len(where) != 0 {
		query += ` WHERE ` + strings.Join(where, ` AND `)
	}
	query += ` ORDER BY created_at_ms, claim_id`

	rows, err := store.db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list resource claims: %w", err)
	}
	defer rows.Close()

	claims := make([]ResourceClaim, 0)
	for rows.Next() {
		claim, err := scanResourceClaim(rows)
		if err != nil {
			return nil, err
		}
		claims = append(claims, claim)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate resource claims: %w", err)
	}
	return claims, nil
}

func (store *Store) ListResourceClaimsForAttempt(
	ctx context.Context,
	attemptID string,
) ([]ResourceClaim, error) {
	if strings.TrimSpace(attemptID) == "" {
		return nil, fmt.Errorf("%w: attempt_id is required", ErrInvalidArgument)
	}
	return store.ListResourceClaims(ctx, ListResourceClaimsParams{
		AttemptID: attemptID,
	})
}

func releaseResourceClaimTx(
	ctx context.Context,
	tx *sql.Tx,
	claim ResourceClaim,
	reason string,
	nowMS int64,
) error {
	if claim.Status != ResourceClaimActive {
		return nil
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE resource_claims
		SET status = ?, reason = ?, revision = revision + 1,
		    updated_at_ms = ?, released_at_ms = ?
		WHERE claim_id = ? AND revision = ? AND status = ?
	`,
		ResourceClaimReleased,
		reason,
		nowMS,
		nowMS,
		claim.ClaimID,
		claim.Revision,
		ResourceClaimActive,
	)
	if err != nil {
		return fmt.Errorf("release resource claim %q: %w", claim.ClaimID, err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "release resource claim"); err != nil {
		return err
	}
	return nil
}

func releaseAttemptResourceClaimsTx(
	ctx context.Context,
	tx *sql.Tx,
	attempt Attempt,
	reason string,
	nowMS int64,
) error {
	rows, err := tx.QueryContext(ctx, `
		SELECT claim_id, resource_type, resource_key,
		       run_id, attempt_id, activity_id, workspace_id,
		       owner_epoch, fence, mode, status, reason, binding_json, revision,
		       created_at_ms, updated_at_ms, lease_until_ms, released_at_ms
		FROM resource_claims
		WHERE attempt_id = ? AND owner_epoch = ? AND fence = ? AND status = ?
		ORDER BY created_at_ms, claim_id
	`, attempt.AttemptID, attempt.OwnerEpoch, attempt.Fence, ResourceClaimActive)
	if err != nil {
		return fmt.Errorf("query active resource claims for attempt %q: %w", attempt.AttemptID, err)
	}
	claims := make([]ResourceClaim, 0)
	for rows.Next() {
		claim, scanErr := scanResourceClaim(rows)
		if scanErr != nil {
			_ = rows.Close()
			return scanErr
		}
		claims = append(claims, claim)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return fmt.Errorf("iterate active resource claims for attempt %q: %w", attempt.AttemptID, err)
	}
	if err := rows.Close(); err != nil {
		return fmt.Errorf("close active resource claims for attempt %q: %w", attempt.AttemptID, err)
	}
	for _, claim := range claims {
		if err := releaseResourceClaimTx(ctx, tx, claim, reason, nowMS); err != nil {
			return err
		}
	}
	return nil
}

func validateAcquireResourceClaimParams(params AcquireResourceClaimParams) error {
	required := map[string]string{
		"claim_id":      params.ClaimID,
		"resource_type": string(params.ResourceType),
		"resource_key":  params.ResourceKey,
		"attempt_id":    params.AttemptID,
	}
	for name, value := range required {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%w: %s is required", ErrInvalidArgument, name)
		}
	}
	if params.Fence <= 0 {
		return fmt.Errorf("%w: fence must be positive", ErrInvalidArgument)
	}
	if params.LeaseUntil.IsZero() || !params.LeaseUntil.After(time.Now().UTC()) {
		return fmt.Errorf("%w: lease_until must be in the future", ErrInvalidArgument)
	}
	if strings.TrimSpace(params.BindingJSON) == "" {
		return fmt.Errorf("%w: binding_json is required", ErrInvalidArgument)
	}
	switch params.Mode {
	case ResourceClaimShared, ResourceClaimExclusive:
	default:
		return fmt.Errorf("%w: resource claim mode %q is unsupported", ErrInvalidArgument, params.Mode)
	}
	return nil
}

func normalizeAcquireResourceClaimParams(params AcquireResourceClaimParams) AcquireResourceClaimParams {
	if params.ResourceType == "" {
		params.ResourceType = params.ResourceKind
	}
	if params.ResourceKind == "" {
		params.ResourceKind = params.ResourceType
	}
	if strings.TrimSpace(params.BindingJSON) == "" {
		params.BindingJSON = "{}"
	}
	if params.LeaseUntil.IsZero() {
		params.LeaseUntil = time.Now().UTC().Add(defaultAttemptLeaseDuration)
	}
	return params
}

func requireClaimableAttemptTx(
	ctx context.Context,
	tx *sql.Tx,
	ownerEpoch string,
	attemptID string,
	fence int64,
	expectedRunID string,
) (Attempt, Run, int64, error) {
	attempt, err := readAttemptTx(ctx, tx, attemptID)
	if err != nil {
		return Attempt{}, Run{}, 0, err
	}
	run, err := readRunTx(ctx, tx, attempt.RunID)
	if err != nil {
		return Attempt{}, Run{}, 0, err
	}
	if expectedRunID = strings.TrimSpace(expectedRunID); expectedRunID != "" && run.RunID != expectedRunID {
		return Attempt{}, Run{}, 0, fmt.Errorf("%w: attempt %q does not belong to run %q", ErrStaleFence, attempt.AttemptID, expectedRunID)
	}
	if err := validateAttemptAuthority(attempt, run, fence, ownerEpoch); err != nil {
		return Attempt{}, Run{}, 0, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	if attempt.Status != AttemptIssued && attempt.Status != AttemptActive && attempt.Status != AttemptSealing {
		return Attempt{}, Run{}, 0, fmt.Errorf("%w: attempt %q does not hold live execution authority", ErrInvalidTransition, attempt.AttemptID)
	}
	if run.Status != RunReady && run.Status != RunActive {
		return Attempt{}, Run{}, 0, fmt.Errorf("%w: run %q is %q", ErrStaleFence, run.RunID, run.Status)
	}
	if attempt.LeaseUntilMS <= nowMS {
		return Attempt{}, Run{}, 0, fmt.Errorf("%w: attempt %q lease has expired", ErrStaleFence, attempt.AttemptID)
	}
	return attempt, run, nowMS, nil
}

func readActiveResourceClaimForAttemptTx(
	ctx context.Context,
	tx *sql.Tx,
	attemptID string,
	resourceType ResourceType,
	resourceKey string,
	mode ResourceClaimMode,
) (ResourceClaim, bool, error) {
	row := tx.QueryRowContext(ctx, `
		SELECT claim_id, resource_type, resource_key,
		       run_id, attempt_id, activity_id, workspace_id,
		       owner_epoch, fence, mode, status, reason, binding_json, revision,
		       created_at_ms, updated_at_ms, lease_until_ms, released_at_ms
		FROM resource_claims
		WHERE attempt_id = ? AND resource_type = ? AND resource_key = ? AND mode = ? AND status = ?
		ORDER BY created_at_ms, claim_id
		LIMIT 1
	`, attemptID, string(resourceType), resourceKey, mode, ResourceClaimActive)
	claim, err := scanResourceClaim(row)
	if errors.Is(err, sql.ErrNoRows) {
		return ResourceClaim{}, false, nil
	}
	if err != nil {
		return ResourceClaim{}, false, fmt.Errorf("read active resource claim replay: %w", err)
	}
	return claim, true, nil
}

func readConflictingResourceClaimTx(
	ctx context.Context,
	tx *sql.Tx,
	resourceType ResourceType,
	resourceKey string,
	mode ResourceClaimMode,
) (ResourceClaim, bool, error) {
	query := `
		SELECT claim_id, resource_type, resource_key,
		       run_id, attempt_id, activity_id, workspace_id,
		       owner_epoch, fence, mode, status, reason, binding_json, revision,
		       created_at_ms, updated_at_ms, lease_until_ms, released_at_ms
		FROM resource_claims
		WHERE resource_type = ? AND resource_key = ? AND status = ?`
	args := []any{string(resourceType), resourceKey, ResourceClaimActive}
	if mode == ResourceClaimShared {
		query += ` AND mode = ?`
		args = append(args, ResourceClaimExclusive)
	}
	query += ` ORDER BY created_at_ms, claim_id LIMIT 1`

	row := tx.QueryRowContext(ctx, query, args...)
	claim, err := scanResourceClaim(row)
	if errors.Is(err, sql.ErrNoRows) {
		return ResourceClaim{}, false, nil
	}
	if err != nil {
		return ResourceClaim{}, false, fmt.Errorf("read conflicting resource claim: %w", err)
	}
	return claim, true, nil
}

type resourceClaimScanner interface {
	Scan(...any) error
}

func scanResourceClaim(scanner resourceClaimScanner) (ResourceClaim, error) {
	var claim ResourceClaim
	err := scanner.Scan(
		&claim.ClaimID,
		&claim.ResourceType,
		&claim.ResourceKey,
		&claim.RunID,
		&claim.AttemptID,
		&claim.ActivityID,
		&claim.WorkspaceID,
		&claim.OwnerEpoch,
		&claim.Fence,
		&claim.Mode,
		&claim.Status,
		&claim.Reason,
		&claim.BindingJSON,
		&claim.Revision,
		&claim.CreatedAtMS,
		&claim.UpdatedAtMS,
		&claim.LeaseUntilMS,
		&claim.ReleasedAtMS,
	)
	if err != nil {
		return ResourceClaim{}, err
	}
	return claim, nil
}

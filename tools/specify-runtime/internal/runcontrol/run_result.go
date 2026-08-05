package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"
)

type ResultEligibility string

const (
	ResultEligibilityReady                  ResultEligibility = "ready"
	ResultEligibilityBlocked                ResultEligibility = "blocked"
	ResultEligibilityFailed                 ResultEligibility = "failed"
	ResultEligibilityOverlayDependent       ResultEligibility = "overlay_dependent"
	ResultEligibilityRequiresEffectApproval ResultEligibility = "requires_effect_approval"
)

// RunResultSnapshot is computed by the runtime from an attested workspace.
// FinishAttempt persists it in the same transaction that seals the Run.
type RunResultSnapshot struct {
	ResultID                   string
	ResultRevision             int64
	SnapshotID                 string
	TargetRef                  string
	BaseCommitOID              string
	ResultTreeOID              string
	ResultCommitOID            string
	HiddenRef                  string
	ManifestSHA256             string
	WorkspaceAttestationSHA256 string
	ResourceAttestationSHA256  string
	Eligibility                ResultEligibility
	ChangedPaths               []string
	ValidationEvidenceJSON     string
	WorkerResultDigestsJSON    string
	ExternalEffectsJSON        string
}

// RunResult is an append-only, runtime-derived delivery unit. It is distinct
// from a worker's narrative report and from a multi-Result Candidate.
type RunResult struct {
	ResultID                   string
	RunID                      string
	ResultRevision             int64
	AttemptID                  string
	ActivityID                 string
	WorkspaceID                string
	WorkspaceGeneration        int64
	Fence                      int64
	SnapshotID                 string
	TargetRef                  string
	BaseCommitOID              string
	ResultTreeOID              string
	ResultCommitOID            string
	HiddenRef                  string
	ManifestSHA256             string
	WorkspaceAttestationSHA256 string
	ResourceAttestationSHA256  string
	Eligibility                ResultEligibility
	ValidationEvidenceJSON     string
	WorkerResultDigestsJSON    string
	ExternalEffectsJSON        string
	CreatedAtMS                int64
}

type ResultSupersession struct {
	OldResultID string
	NewResultID string
	RunID       string
	Reason      string
	CreatedAtMS int64
}

type ReopenRunParams struct {
	RunID            string
	BasisResultID    string
	ExpectedRevision int64
	Reason           string
}

const runResultSchemaSQL = `
CREATE TABLE IF NOT EXISTS run_results (
    result_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    result_revision INTEGER NOT NULL CHECK (result_revision > 0),
    attempt_id TEXT NOT NULL UNIQUE REFERENCES attempts(attempt_id) ON DELETE RESTRICT,
    activity_id TEXT NOT NULL REFERENCES activities(activity_id) ON DELETE RESTRICT,
    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id) ON DELETE RESTRICT,
    workspace_generation INTEGER NOT NULL CHECK (workspace_generation > 0),
    fence INTEGER NOT NULL CHECK (fence > 0),
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id) ON DELETE RESTRICT,
    target_ref TEXT NOT NULL,
    base_commit_oid TEXT NOT NULL,
    result_tree_oid TEXT NOT NULL,
    result_commit_oid TEXT NOT NULL,
    hidden_ref TEXT NOT NULL UNIQUE,
    manifest_sha256 TEXT NOT NULL CHECK (
        length(manifest_sha256) = 64 AND manifest_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    workspace_attestation_sha256 TEXT NOT NULL CHECK (
        length(workspace_attestation_sha256) = 64 AND workspace_attestation_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    resource_attestation_sha256 TEXT NOT NULL CHECK (
        length(resource_attestation_sha256) = 64 AND resource_attestation_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    eligibility TEXT NOT NULL CHECK (
        eligibility IN ('ready', 'blocked', 'failed', 'overlay_dependent', 'requires_effect_approval')
    ),
    validation_evidence_json TEXT NOT NULL DEFAULT '[]',
    worker_result_digests_json TEXT NOT NULL DEFAULT '[]',
    external_effects_json TEXT NOT NULL DEFAULT '[]',
    created_at_ms INTEGER NOT NULL,
    UNIQUE (run_id, result_revision)
);

CREATE INDEX IF NOT EXISTS run_results_run_history
    ON run_results(run_id, result_revision, created_at_ms);

CREATE INDEX IF NOT EXISTS run_results_ready_queue
    ON run_results(target_ref, eligibility, created_at_ms, result_id);

CREATE TABLE IF NOT EXISTS run_result_paths (
    result_id TEXT NOT NULL REFERENCES run_results(result_id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    relative_path TEXT NOT NULL,
    PRIMARY KEY (result_id, ordinal),
    UNIQUE (result_id, relative_path)
);

CREATE TABLE IF NOT EXISTS run_reopen_intents (
    run_id TEXT PRIMARY KEY REFERENCES runs(run_id) ON DELETE RESTRICT,
    basis_result_id TEXT NOT NULL REFERENCES run_results(result_id) ON DELETE RESTRICT,
    new_result_id TEXT REFERENCES run_results(result_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL,
    created_at_ms INTEGER NOT NULL,
    consumed_at_ms INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS result_supersessions (
    old_result_id TEXT PRIMARY KEY REFERENCES run_results(result_id) ON DELETE RESTRICT,
    new_result_id TEXT NOT NULL UNIQUE REFERENCES run_results(result_id) ON DELETE RESTRICT,
    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL,
    created_at_ms INTEGER NOT NULL
);
`

func (store *Store) ListRunResults(ctx context.Context, runID string) ([]RunResult, error) {
	if strings.TrimSpace(runID) == "" {
		return nil, fmt.Errorf("%w: run id is required", ErrInvalidArgument)
	}
	rows, err := store.db.QueryContext(ctx, runResultSelectSQL+`
		WHERE run_id = ? ORDER BY result_revision, created_at_ms, result_id
	`, runID)
	if err != nil {
		return nil, fmt.Errorf("list Run Results for %q: %w", runID, err)
	}
	defer rows.Close()
	results := make([]RunResult, 0)
	for rows.Next() {
		result, err := scanRunResult(rows)
		if err != nil {
			return nil, err
		}
		results = append(results, result)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate Run Results for %q: %w", runID, err)
	}
	return results, nil
}

func (store *Store) GetRunResult(ctx context.Context, resultID string) (RunResult, error) {
	if strings.TrimSpace(resultID) == "" {
		return RunResult{}, fmt.Errorf("%w: result id is required", ErrInvalidArgument)
	}
	result, err := readRunResultTx(ctx, store.db, resultID)
	if err != nil {
		return RunResult{}, err
	}
	return result, nil
}

func (store *Store) ListRunResultPaths(ctx context.Context, resultID string) ([]string, error) {
	if strings.TrimSpace(resultID) == "" {
		return nil, fmt.Errorf("%w: result id is required", ErrInvalidArgument)
	}
	if _, err := readRunResultTx(ctx, store.db, resultID); err != nil {
		return nil, err
	}
	return listRunResultPaths(ctx, store.db, resultID)
}

func (store *Store) nextRunResultRevision(ctx context.Context, runID string) (int64, error) {
	var revision int64
	if err := store.db.QueryRowContext(ctx, `
		SELECT COALESCE(MAX(result_revision), 0) + 1 FROM run_results WHERE run_id = ?
	`, runID).Scan(&revision); err != nil {
		return 0, fmt.Errorf("derive next Run Result revision for %q: %w", runID, err)
	}
	return revision, nil
}

func insertRunResultTx(
	ctx context.Context,
	tx *sql.Tx,
	run Run,
	attempt Attempt,
	activity Activity,
	workspace Workspace,
	snapshot RunResultSnapshot,
	nowMS int64,
) (RunResult, error) {
	if err := validateRunResultSnapshot(run, attempt, activity, workspace, snapshot); err != nil {
		return RunResult{}, err
	}
	result := RunResult{
		ResultID:                   snapshot.ResultID,
		RunID:                      run.RunID,
		ResultRevision:             snapshot.ResultRevision,
		AttemptID:                  attempt.AttemptID,
		ActivityID:                 activity.ActivityID,
		WorkspaceID:                workspace.WorkspaceID,
		WorkspaceGeneration:        workspace.Generation,
		Fence:                      attempt.Fence,
		SnapshotID:                 snapshot.SnapshotID,
		TargetRef:                  snapshot.TargetRef,
		BaseCommitOID:              snapshot.BaseCommitOID,
		ResultTreeOID:              snapshot.ResultTreeOID,
		ResultCommitOID:            snapshot.ResultCommitOID,
		HiddenRef:                  snapshot.HiddenRef,
		ManifestSHA256:             snapshot.ManifestSHA256,
		WorkspaceAttestationSHA256: snapshot.WorkspaceAttestationSHA256,
		ResourceAttestationSHA256:  snapshot.ResourceAttestationSHA256,
		Eligibility:                snapshot.Eligibility,
		ValidationEvidenceJSON:     defaultJSONArray(snapshot.ValidationEvidenceJSON),
		WorkerResultDigestsJSON:    defaultJSONArray(snapshot.WorkerResultDigestsJSON),
		ExternalEffectsJSON:        defaultJSONArray(snapshot.ExternalEffectsJSON),
		CreatedAtMS:                nowMS,
	}
	_, err := tx.ExecContext(ctx, `
		INSERT INTO run_results (
			result_id, run_id, result_revision, attempt_id, activity_id,
			workspace_id, workspace_generation, fence, snapshot_id, target_ref,
			base_commit_oid, result_tree_oid, result_commit_oid, hidden_ref,
			manifest_sha256, workspace_attestation_sha256, resource_attestation_sha256,
			eligibility, validation_evidence_json, worker_result_digests_json,
			external_effects_json, created_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, result.ResultID, result.RunID, result.ResultRevision, result.AttemptID,
		result.ActivityID, result.WorkspaceID, result.WorkspaceGeneration, result.Fence,
		result.SnapshotID, result.TargetRef, result.BaseCommitOID, result.ResultTreeOID,
		result.ResultCommitOID, result.HiddenRef, result.ManifestSHA256,
		result.WorkspaceAttestationSHA256, result.ResourceAttestationSHA256,
		result.Eligibility, result.ValidationEvidenceJSON, result.WorkerResultDigestsJSON,
		result.ExternalEffectsJSON, result.CreatedAtMS)
	if err != nil {
		if isUniqueConstraintError(err) {
			existing, readErr := readRunResultTx(ctx, tx, result.ResultID)
			if readErr == nil && runResultImmutableFieldsEqual(existing, result) {
				return existing, nil
			}
			return RunResult{}, fmt.Errorf("%w: Run Result %q", ErrAlreadyExists, result.ResultID)
		}
		return RunResult{}, fmt.Errorf("insert Run Result: %w", err)
	}
	for index, path := range snapshot.ChangedPaths {
		if _, err := tx.ExecContext(ctx, `
			INSERT INTO run_result_paths (result_id, ordinal, relative_path) VALUES (?, ?, ?)
		`, result.ResultID, index+1, path); err != nil {
			return RunResult{}, fmt.Errorf("insert Run Result path %q: %w", path, err)
		}
	}
	if err := consumeRunReopenIntentTx(ctx, tx, result, nowMS); err != nil {
		return RunResult{}, err
	}
	return result, nil
}

func validateRunResultSnapshot(run Run, attempt Attempt, activity Activity, workspace Workspace, result RunResultSnapshot) error {
	required := map[string]string{
		"result_id": result.ResultID, "snapshot_id": result.SnapshotID,
		"target_ref": result.TargetRef, "base_commit_oid": result.BaseCommitOID,
		"result_tree_oid": result.ResultTreeOID, "result_commit_oid": result.ResultCommitOID,
		"hidden_ref": result.HiddenRef, "manifest_sha256": result.ManifestSHA256,
		"workspace_attestation_sha256": result.WorkspaceAttestationSHA256,
		"resource_attestation_sha256":  result.ResourceAttestationSHA256,
	}
	for name, value := range required {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%w: %s is required", ErrInvalidArgument, name)
		}
	}
	if result.ResultRevision <= 0 || !validGitObjectID(result.BaseCommitOID) ||
		!validGitObjectID(result.ResultTreeOID) || !validGitObjectID(result.ResultCommitOID) ||
		!validSHA256(result.ManifestSHA256) || !validSHA256(result.WorkspaceAttestationSHA256) ||
		!validSHA256(result.ResourceAttestationSHA256) {
		return fmt.Errorf("%w: Run Result identity is invalid", ErrCandidateBinding)
	}
	if !strings.HasPrefix(result.HiddenRef, "refs/specify/results/") ||
		result.TargetRef != workspace.BaseRef || result.BaseCommitOID != workspace.BaseCommit ||
		attempt.RunID != run.RunID || activity.RunID != run.RunID || workspace.RunID != run.RunID ||
		attempt.ActivityID != activity.ActivityID || attempt.WorkspaceID != workspace.WorkspaceID ||
		attempt.WorkspaceGeneration != workspace.Generation {
		return fmt.Errorf("%w: Run Result does not match its execution", ErrCandidateBinding)
	}
	switch result.Eligibility {
	case ResultEligibilityReady, ResultEligibilityBlocked, ResultEligibilityFailed,
		ResultEligibilityOverlayDependent, ResultEligibilityRequiresEffectApproval:
	default:
		return fmt.Errorf("%w: unsupported Result eligibility %q", ErrInvalidArgument, result.Eligibility)
	}
	seen := make(map[string]struct{}, len(result.ChangedPaths))
	for _, path := range result.ChangedPaths {
		path, err := normalizeSnapshotRelativePath(path)
		if err != nil {
			return err
		}
		if _, exists := seen[path]; exists {
			return fmt.Errorf("%w: duplicate Result path %q", ErrInvalidArgument, path)
		}
		seen[path] = struct{}{}
	}
	return nil
}

func (store *Store) ReopenRun(ctx context.Context, params ReopenRunParams) (Run, error) {
	if strings.TrimSpace(params.RunID) == "" || strings.TrimSpace(params.BasisResultID) == "" ||
		params.ExpectedRevision <= 0 || strings.TrimSpace(params.Reason) == "" {
		return Run{}, fmt.Errorf("%w: run, basis Result, expected revision, and reason are required", ErrInvalidArgument)
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Run{}, fmt.Errorf("begin reopen Run: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, tx, store.ownerEpoch); err != nil {
		return Run{}, err
	}
	run, err := readRunTx(ctx, tx, params.RunID)
	if err != nil {
		return Run{}, err
	}
	if run.Revision != params.ExpectedRevision {
		return Run{}, fmt.Errorf("%w: run %q is revision %d, expected %d", ErrRevisionConflict, run.RunID, run.Revision, params.ExpectedRevision)
	}
	if run.Status != RunSealed {
		return Run{}, fmt.Errorf("%w: only a sealed Run can reopen", ErrInvalidTransition)
	}
	basis, err := readRunResultTx(ctx, tx, params.BasisResultID)
	if err != nil {
		return Run{}, err
	}
	if basis.RunID != run.RunID {
		return Run{}, fmt.Errorf("%w: basis Result belongs to another Run", ErrCandidateBinding)
	}
	var latestID string
	if err := tx.QueryRowContext(ctx, `
		SELECT result_id FROM run_results WHERE run_id = ? ORDER BY result_revision DESC LIMIT 1
	`, run.RunID).Scan(&latestID); err != nil {
		return Run{}, fmt.Errorf("read latest Run Result: %w", err)
	}
	if latestID != basis.ResultID {
		return Run{}, fmt.Errorf("%w: basis Result is not the latest Run Result", ErrRevisionConflict)
	}
	nowMS := time.Now().UTC().UnixMilli()
	update, err := tx.ExecContext(ctx, `
		UPDATE runs SET status = ?, owner_epoch = ?, revision = revision + 1, updated_at_ms = ?
		WHERE run_id = ? AND revision = ? AND status = ?
	`, RunQueued, store.ownerEpoch, nowMS, run.RunID, run.Revision, RunSealed)
	if err != nil {
		return Run{}, fmt.Errorf("reopen Run: %w", err)
	}
	if err := requireOneCASRow(update, ErrRevisionConflict, "reopen Run"); err != nil {
		return Run{}, err
	}
	run.Status = RunQueued
	run.OwnerEpoch = store.ownerEpoch
	run.Revision++
	run.UpdatedAtMS = nowMS
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO run_reopen_intents (run_id, basis_result_id, new_result_id, reason, created_at_ms, consumed_at_ms)
		VALUES (?, ?, NULL, ?, ?, 0)
		ON CONFLICT(run_id) DO UPDATE SET basis_result_id = excluded.basis_result_id,
			new_result_id = NULL, reason = excluded.reason, created_at_ms = excluded.created_at_ms,
			consumed_at_ms = 0
	`, run.RunID, basis.ResultID, params.Reason, nowMS); err != nil {
		return Run{}, fmt.Errorf("record Run reopen intent: %w", err)
	}
	if err := appendRunEventTx(ctx, tx, run, "run.reopened", params.Reason); err != nil {
		return Run{}, err
	}
	if err := tx.Commit(); err != nil {
		return Run{}, fmt.Errorf("commit Run reopen: %w", err)
	}
	return run, nil
}

func (store *Store) GetResultSupersession(ctx context.Context, oldResultID string) (ResultSupersession, error) {
	if strings.TrimSpace(oldResultID) == "" {
		return ResultSupersession{}, fmt.Errorf("%w: old Result id is required", ErrInvalidArgument)
	}
	var edge ResultSupersession
	err := store.db.QueryRowContext(ctx, `
		SELECT old_result_id, new_result_id, run_id, reason, created_at_ms
		FROM result_supersessions WHERE old_result_id = ?
	`, oldResultID).Scan(&edge.OldResultID, &edge.NewResultID, &edge.RunID, &edge.Reason, &edge.CreatedAtMS)
	if errors.Is(err, sql.ErrNoRows) {
		return ResultSupersession{}, fmt.Errorf("%w: Result supersession for %q", ErrNotFound, oldResultID)
	}
	if err != nil {
		return ResultSupersession{}, fmt.Errorf("read Result supersession: %w", err)
	}
	return edge, nil
}

func consumeRunReopenIntentTx(ctx context.Context, tx *sql.Tx, result RunResult, nowMS int64) error {
	var basisID, reason string
	err := tx.QueryRowContext(ctx, `
		SELECT basis_result_id, reason FROM run_reopen_intents
		WHERE run_id = ? AND new_result_id IS NULL
	`, result.RunID).Scan(&basisID, &reason)
	if errors.Is(err, sql.ErrNoRows) {
		return nil
	}
	if err != nil {
		return fmt.Errorf("read Run reopen intent: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO result_supersessions (old_result_id, new_result_id, run_id, reason, created_at_ms)
		VALUES (?, ?, ?, ?, ?)
	`, basisID, result.ResultID, result.RunID, reason, nowMS); err != nil {
		return fmt.Errorf("insert Result supersession: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE run_reopen_intents SET new_result_id = ?, consumed_at_ms = ?
		WHERE run_id = ? AND basis_result_id = ? AND new_result_id IS NULL
	`, result.ResultID, nowMS, result.RunID, basisID); err != nil {
		return fmt.Errorf("consume Run reopen intent: %w", err)
	}
	return nil
}

const runResultSelectSQL = `
	SELECT result_id, run_id, result_revision, attempt_id, activity_id,
	       workspace_id, workspace_generation, fence, snapshot_id, target_ref,
	       base_commit_oid, result_tree_oid, result_commit_oid, hidden_ref,
	       manifest_sha256, workspace_attestation_sha256, resource_attestation_sha256,
	       eligibility, validation_evidence_json, worker_result_digests_json,
	       external_effects_json, created_at_ms
	FROM run_results
`

func readRunResultTx(ctx context.Context, querier rowQuerier, resultID string) (RunResult, error) {
	result, err := scanRunResult(querier.QueryRowContext(ctx, runResultSelectSQL+` WHERE result_id = ?`, resultID))
	if errors.Is(err, sql.ErrNoRows) {
		return RunResult{}, fmt.Errorf("%w: Run Result %q", ErrResultNotFound, resultID)
	}
	if err != nil {
		return RunResult{}, fmt.Errorf("read Run Result %q: %w", resultID, err)
	}
	return result, nil
}

func readRunResultForAttemptTx(ctx context.Context, querier rowQuerier, attemptID string) (RunResult, error) {
	result, err := scanRunResult(querier.QueryRowContext(ctx, runResultSelectSQL+` WHERE attempt_id = ?`, attemptID))
	if errors.Is(err, sql.ErrNoRows) {
		return RunResult{}, fmt.Errorf("%w: Run Result for attempt %q", ErrResultNotFound, attemptID)
	}
	if err != nil {
		return RunResult{}, fmt.Errorf("read Run Result for attempt %q: %w", attemptID, err)
	}
	return result, nil
}

type runResultScanner interface{ Scan(...any) error }

func scanRunResult(scanner runResultScanner) (RunResult, error) {
	var result RunResult
	err := scanner.Scan(
		&result.ResultID, &result.RunID, &result.ResultRevision, &result.AttemptID,
		&result.ActivityID, &result.WorkspaceID, &result.WorkspaceGeneration, &result.Fence,
		&result.SnapshotID, &result.TargetRef, &result.BaseCommitOID, &result.ResultTreeOID,
		&result.ResultCommitOID, &result.HiddenRef, &result.ManifestSHA256,
		&result.WorkspaceAttestationSHA256, &result.ResourceAttestationSHA256,
		&result.Eligibility, &result.ValidationEvidenceJSON, &result.WorkerResultDigestsJSON,
		&result.ExternalEffectsJSON, &result.CreatedAtMS,
	)
	return result, err
}

func listRunResultPaths(ctx context.Context, querier interface {
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
}, resultID string) ([]string, error) {
	rows, err := querier.QueryContext(ctx, `
		SELECT relative_path FROM run_result_paths WHERE result_id = ? ORDER BY ordinal
	`, resultID)
	if err != nil {
		return nil, fmt.Errorf("list Run Result paths: %w", err)
	}
	defer rows.Close()
	paths := make([]string, 0)
	for rows.Next() {
		var path string
		if err := rows.Scan(&path); err != nil {
			return nil, err
		}
		paths = append(paths, path)
	}
	return paths, rows.Err()
}

func defaultJSONArray(value string) string {
	if strings.TrimSpace(value) == "" {
		return "[]"
	}
	return value
}

func runResultImmutableFieldsEqual(left, right RunResult) bool {
	return left.ResultID == right.ResultID && left.RunID == right.RunID &&
		left.ResultRevision == right.ResultRevision && left.AttemptID == right.AttemptID &&
		left.ActivityID == right.ActivityID && left.WorkspaceID == right.WorkspaceID &&
		left.WorkspaceGeneration == right.WorkspaceGeneration && left.Fence == right.Fence &&
		left.SnapshotID == right.SnapshotID && left.TargetRef == right.TargetRef &&
		left.BaseCommitOID == right.BaseCommitOID && left.ResultTreeOID == right.ResultTreeOID &&
		left.ResultCommitOID == right.ResultCommitOID && left.HiddenRef == right.HiddenRef &&
		left.ManifestSHA256 == right.ManifestSHA256 &&
		left.WorkspaceAttestationSHA256 == right.WorkspaceAttestationSHA256 &&
		left.ResourceAttestationSHA256 == right.ResourceAttestationSHA256 &&
		left.Eligibility == right.Eligibility
}

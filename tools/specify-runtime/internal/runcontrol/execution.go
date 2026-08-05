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

// CreateActivity records the next unit of work for a run. The ordinal and the
// open-activity invariant are decided while holding the Store's immediate
// SQLite transaction, so two supervisors cannot both create an open activity.
func (store *Store) CreateActivity(ctx context.Context, params CreateActivityParams) (Activity, error) {
	if err := validateCreateActivityParams(params); err != nil {
		return Activity{}, err
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Activity{}, fmt.Errorf("begin create activity: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, tx, store.ownerEpoch); err != nil {
		return Activity{}, err
	}

	if _, err := readRunTx(ctx, tx, params.RunID); err != nil {
		return Activity{}, err
	}
	if exists, err := aggregateIDExistsTx(ctx, tx, "activities", "activity_id", params.ActivityID); err != nil {
		return Activity{}, err
	} else if exists {
		return Activity{}, fmt.Errorf("%w: activity %q", ErrAlreadyExists, params.ActivityID)
	}

	var ordinal int64
	if err := tx.QueryRowContext(ctx, `
		SELECT COALESCE(MAX(ordinal), 0) + 1
		FROM activities
		WHERE run_id = ?
	`, params.RunID).Scan(&ordinal); err != nil {
		return Activity{}, fmt.Errorf("allocate activity ordinal for run %q: %w", params.RunID, err)
	}

	nowMS := time.Now().UTC().UnixMilli()
	activity := Activity{
		ActivityID:  params.ActivityID,
		RunID:       params.RunID,
		Kind:        params.Kind,
		Ordinal:     ordinal,
		InputSHA256: params.InputSHA256,
		Status:      ActivityPlanned,
		Revision:    1,
		CreatedAtMS: nowMS,
		UpdatedAtMS: nowMS,
	}
	_, err = tx.ExecContext(ctx, `
		INSERT INTO activities (
			activity_id, run_id, kind, ordinal, input_sha256,
			status, revision, created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, activity.ActivityID, activity.RunID, activity.Kind, activity.Ordinal,
		activity.InputSHA256, activity.Status, activity.Revision,
		activity.CreatedAtMS, activity.UpdatedAtMS)
	if err != nil {
		if isUniqueConstraintError(err) {
			if strings.Contains(strings.ToLower(err.Error()), "activities.run_id") {
				return Activity{}, fmt.Errorf("%w: run %q", ErrOpenActivity, activity.RunID)
			}
			return Activity{}, fmt.Errorf("%w: activity %q", ErrAlreadyExists, activity.ActivityID)
		}
		return Activity{}, fmt.Errorf("insert activity: %w", err)
	}
	if err := appendActivityEventTx(ctx, tx, activity, "activity.created", "activity created"); err != nil {
		return Activity{}, err
	}
	if err := tx.Commit(); err != nil {
		return Activity{}, fmt.Errorf("commit create activity: %w", err)
	}
	return activity, nil
}

func (store *Store) GetActivity(ctx context.Context, activityID string) (Activity, error) {
	if strings.TrimSpace(activityID) == "" {
		return Activity{}, fmt.Errorf("%w: activity id is required", ErrInvalidArgument)
	}
	return readActivityTx(ctx, store.db, activityID)
}

// CreateWorkspace allocates a monotonically increasing workspace generation.
// A quarantined/released workspace remains durable history but no longer blocks
// the next usable generation.
func (store *Store) CreateWorkspace(ctx context.Context, params CreateWorkspaceParams) (Workspace, error) {
	if err := validateCreateWorkspaceParams(params); err != nil {
		return Workspace{}, err
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return Workspace{}, fmt.Errorf("begin create workspace: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, tx, store.ownerEpoch); err != nil {
		return Workspace{}, err
	}

	if _, err := readRunTx(ctx, tx, params.RunID); err != nil {
		return Workspace{}, err
	}
	if exists, err := aggregateIDExistsTx(ctx, tx, "workspaces", "workspace_id", params.WorkspaceID); err != nil {
		return Workspace{}, err
	} else if exists {
		return Workspace{}, fmt.Errorf("%w: workspace %q", ErrAlreadyExists, params.WorkspaceID)
	}

	var maximumGeneration int64
	if err := tx.QueryRowContext(ctx, `
		SELECT COALESCE(MAX(generation), 0)
		FROM workspaces
		WHERE run_id = ?
	`, params.RunID).Scan(&maximumGeneration); err != nil {
		return Workspace{}, fmt.Errorf("read workspace generation for run %q: %w", params.RunID, err)
	}
	if params.Generation <= maximumGeneration {
		return Workspace{}, fmt.Errorf("%w: run %q has generation %d, requested %d", ErrWorkspaceGeneration, params.RunID, maximumGeneration, params.Generation)
	}

	nowMS := time.Now().UTC().UnixMilli()
	mode := normalizeWorkspaceMode(params.Mode)
	workspace := Workspace{
		WorkspaceID:   params.WorkspaceID,
		RunID:         params.RunID,
		Generation:    params.Generation,
		Kind:          params.Kind,
		Mode:          mode,
		SourceRunID:   strings.TrimSpace(params.SourceRunID),
		RootPath:      params.RootPath,
		RepoCommonDir: params.RepoCommonDir,
		BaseRef:       params.BaseRef,
		BaseCommit:    params.BaseCommit,
		PrivateRef:    params.PrivateRef,
		Status:        WorkspaceAllocating,
		Revision:      1,
		CreatedAtMS:   nowMS,
		UpdatedAtMS:   nowMS,
	}
	_, err = tx.ExecContext(ctx, `
		INSERT INTO workspaces (
			workspace_id, run_id, generation, kind, root_path, repo_common_dir,
			base_ref, base_commit, private_ref, status, revision,
			created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, workspace.WorkspaceID, workspace.RunID, workspace.Generation, workspace.Kind,
		workspace.RootPath, workspace.RepoCommonDir, workspace.BaseRef,
		workspace.BaseCommit, workspace.PrivateRef, workspace.Status,
		workspace.Revision, workspace.CreatedAtMS, workspace.UpdatedAtMS)
	if err != nil {
		if isUniqueConstraintError(err) {
			message := strings.ToLower(err.Error())
			switch {
			case strings.Contains(message, "workspaces.run_id, workspaces.generation"):
				return Workspace{}, fmt.Errorf("%w: run %q generation %d", ErrWorkspaceGeneration, workspace.RunID, workspace.Generation)
			case strings.Contains(message, "workspaces.run_id"):
				return Workspace{}, fmt.Errorf("%w: run %q", ErrUsableWorkspace, workspace.RunID)
			default:
				return Workspace{}, fmt.Errorf("%w: workspace %q", ErrAlreadyExists, workspace.WorkspaceID)
			}
		}
		return Workspace{}, fmt.Errorf("insert workspace: %w", err)
	}
	var sourceRunID any
	if workspace.SourceRunID != "" {
		sourceRunID = workspace.SourceRunID
	}
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO workspace_routes (workspace_id, mode, source_run_id, created_at_ms)
		VALUES (?, ?, ?, ?)
	`, workspace.WorkspaceID, workspace.Mode, sourceRunID, nowMS); err != nil {
		return Workspace{}, fmt.Errorf("insert workspace route: %w", err)
	}
	if err := appendWorkspaceEventTx(ctx, tx, workspace, "workspace.created", "workspace allocation recorded"); err != nil {
		return Workspace{}, err
	}
	if err := tx.Commit(); err != nil {
		return Workspace{}, fmt.Errorf("commit create workspace: %w", err)
	}
	return workspace, nil
}

func (store *Store) GetWorkspace(ctx context.Context, workspaceID string) (Workspace, error) {
	if strings.TrimSpace(workspaceID) == "" {
		return Workspace{}, fmt.Errorf("%w: workspace id is required", ErrInvalidArgument)
	}
	return readWorkspaceTx(ctx, store.db, workspaceID)
}

// PrepareExecution publishes a run, activity, and workspace as one executable
// unit. All revision and status predicates are checked before the first write;
// each write then repeats those predicates as a database compare-and-swap.
func (store *Store) PrepareExecution(ctx context.Context, params PrepareExecutionParams) (PreparedExecution, error) {
	if err := validatePrepareExecutionParams(params); err != nil {
		return PreparedExecution{}, err
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return PreparedExecution{}, fmt.Errorf("begin prepare execution: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if err := requireActiveSupervisorTx(ctx, tx, store.ownerEpoch); err != nil {
		return PreparedExecution{}, err
	}
	prepared, err := prepareExecutionTx(ctx, tx, store.ownerEpoch, params)
	if err != nil {
		return PreparedExecution{}, err
	}
	if err := tx.Commit(); err != nil {
		return PreparedExecution{}, fmt.Errorf("commit prepare execution: %w", err)
	}
	return prepared, nil
}

func prepareExecutionTx(
	ctx context.Context,
	tx *sql.Tx,
	ownerEpoch string,
	params PrepareExecutionParams,
) (PreparedExecution, error) {
	run, err := readRunTx(ctx, tx, params.RunID)
	if err != nil {
		return PreparedExecution{}, err
	}
	activity, err := readActivityTx(ctx, tx, params.ActivityID)
	if err != nil {
		return PreparedExecution{}, err
	}
	workspace, err := readWorkspaceTx(ctx, tx, params.WorkspaceID)
	if err != nil {
		return PreparedExecution{}, err
	}
	if activity.RunID != run.RunID || workspace.RunID != run.RunID {
		return PreparedExecution{}, fmt.Errorf("%w: run, activity, and workspace must belong to the same run", ErrInvalidArgument)
	}
	if run.Revision != params.ExpectedRunRevision ||
		activity.Revision != params.ExpectedActivityRevision ||
		workspace.Revision != params.ExpectedWorkspaceRevision {
		return PreparedExecution{}, fmt.Errorf(
			"%w: execution revisions are run %d, activity %d, workspace %d; expected %d, %d, %d",
			ErrRevisionConflict,
			run.Revision, activity.Revision, workspace.Revision,
			params.ExpectedRunRevision, params.ExpectedActivityRevision, params.ExpectedWorkspaceRevision,
		)
	}
	if !runCanBePrepared(run.Status) {
		return PreparedExecution{}, fmt.Errorf("%w: cannot prepare run %q from %q", ErrInvalidTransition, run.RunID, run.Status)
	}
	if activity.Status != ActivityPlanned && activity.Status != ActivityInterrupted {
		return PreparedExecution{}, fmt.Errorf("%w: cannot prepare activity %q from %q", ErrInvalidTransition, activity.ActivityID, activity.Status)
	}
	if workspace.Status != WorkspaceAllocating {
		return PreparedExecution{}, fmt.Errorf("%w: cannot prepare workspace %q from %q", ErrInvalidTransition, workspace.WorkspaceID, workspace.Status)
	}

	nowMS := time.Now().UTC().UnixMilli()
	runResult, err := tx.ExecContext(ctx, `
		UPDATE runs
		SET status = ?, owner_epoch = ?, revision = revision + 1, updated_at_ms = ?
		WHERE run_id = ? AND revision = ? AND status = ?
	`, RunReady, ownerEpoch, nowMS, run.RunID, run.Revision, run.Status)
	if err != nil {
		return PreparedExecution{}, fmt.Errorf("prepare run: %w", err)
	}
	if err := requireOneCASRow(runResult, ErrRevisionConflict, "prepare run"); err != nil {
		return PreparedExecution{}, err
	}
	run.Status = RunReady
	run.OwnerEpoch = ownerEpoch
	run.Revision++
	run.UpdatedAtMS = nowMS
	if err := appendRunEventTx(ctx, tx, run, "execution.prepared", activity.ActivityID+":"+workspace.WorkspaceID); err != nil {
		return PreparedExecution{}, err
	}

	if err := updateActivityStatusTx(ctx, tx, &activity, ActivityReady, nowMS, "execution prepared"); err != nil {
		return PreparedExecution{}, err
	}
	if err := updateWorkspaceStatusTx(ctx, tx, &workspace, WorkspaceReady, nowMS, "execution prepared"); err != nil {
		return PreparedExecution{}, err
	}

	return PreparedExecution{Run: run, Activity: activity, Workspace: workspace}, nil
}

func readActivityTx(ctx context.Context, querier rowQuerier, activityID string) (Activity, error) {
	row := querier.QueryRowContext(ctx, `
		SELECT activity_id, run_id, kind, ordinal, input_sha256,
		       status, revision, created_at_ms, updated_at_ms
		FROM activities
		WHERE activity_id = ?
	`, activityID)
	var activity Activity
	if err := row.Scan(
		&activity.ActivityID,
		&activity.RunID,
		&activity.Kind,
		&activity.Ordinal,
		&activity.InputSHA256,
		&activity.Status,
		&activity.Revision,
		&activity.CreatedAtMS,
		&activity.UpdatedAtMS,
	); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Activity{}, fmt.Errorf("%w: activity %q", ErrNotFound, activityID)
		}
		return Activity{}, fmt.Errorf("read activity %q: %w", activityID, err)
	}
	return activity, nil
}

func readWorkspaceTx(ctx context.Context, querier rowQuerier, workspaceID string) (Workspace, error) {
	row := querier.QueryRowContext(ctx, `
		SELECT w.workspace_id, w.run_id, w.generation, w.kind,
		       COALESCE(r.mode, 'isolated'), COALESCE(r.source_run_id, ''),
		       w.root_path, w.repo_common_dir, w.base_ref, w.base_commit,
		       w.private_ref, w.status, w.revision, w.created_at_ms, w.updated_at_ms
		FROM workspaces AS w
		LEFT JOIN workspace_routes AS r ON r.workspace_id = w.workspace_id
		WHERE w.workspace_id = ?
	`, workspaceID)
	var workspace Workspace
	if err := row.Scan(
		&workspace.WorkspaceID,
		&workspace.RunID,
		&workspace.Generation,
		&workspace.Kind,
		&workspace.Mode,
		&workspace.SourceRunID,
		&workspace.RootPath,
		&workspace.RepoCommonDir,
		&workspace.BaseRef,
		&workspace.BaseCommit,
		&workspace.PrivateRef,
		&workspace.Status,
		&workspace.Revision,
		&workspace.CreatedAtMS,
		&workspace.UpdatedAtMS,
	); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return Workspace{}, fmt.Errorf("%w: workspace %q", ErrNotFound, workspaceID)
		}
		return Workspace{}, fmt.Errorf("read workspace %q: %w", workspaceID, err)
	}
	return workspace, nil
}

func updateActivityStatusTx(ctx context.Context, tx *sql.Tx, activity *Activity, status ActivityStatus, nowMS int64, reason string) error {
	result, err := tx.ExecContext(ctx, `
		UPDATE activities
		SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE activity_id = ? AND run_id = ? AND revision = ? AND status = ?
	`, status, nowMS, activity.ActivityID, activity.RunID, activity.Revision, activity.Status)
	if err != nil {
		return fmt.Errorf("update activity %q status: %w", activity.ActivityID, err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "update activity status"); err != nil {
		return err
	}
	activity.Status = status
	activity.Revision++
	activity.UpdatedAtMS = nowMS
	return appendActivityEventTx(ctx, tx, *activity, "activity."+string(status), reason)
}

func updateWorkspaceStatusTx(ctx context.Context, tx *sql.Tx, workspace *Workspace, status WorkspaceStatus, nowMS int64, reason string) error {
	result, err := tx.ExecContext(ctx, `
		UPDATE workspaces
		SET status = ?, revision = revision + 1, updated_at_ms = ?
		WHERE workspace_id = ? AND run_id = ? AND generation = ?
		  AND revision = ? AND status = ?
	`, status, nowMS, workspace.WorkspaceID, workspace.RunID, workspace.Generation,
		workspace.Revision, workspace.Status)
	if err != nil {
		return fmt.Errorf("update workspace %q status: %w", workspace.WorkspaceID, err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "update workspace status"); err != nil {
		return err
	}
	workspace.Status = status
	workspace.Revision++
	workspace.UpdatedAtMS = nowMS
	return appendWorkspaceEventTx(ctx, tx, *workspace, "workspace."+string(status), reason)
}

func updateAttemptExecutionTx(
	ctx context.Context,
	tx *sql.Tx,
	attempt Attempt,
	activityStatus ActivityStatus,
	workspaceStatus WorkspaceStatus,
	nowMS int64,
	reason string,
) error {
	activity, err := readActivityTx(ctx, tx, attempt.ActivityID)
	if err != nil {
		return err
	}
	workspace, err := readWorkspaceTx(ctx, tx, attempt.WorkspaceID)
	if err != nil {
		return err
	}
	if activity.RunID != attempt.RunID || workspace.RunID != attempt.RunID || workspace.Generation != attempt.WorkspaceGeneration {
		return fmt.Errorf("%w: attempt %q execution bindings are inconsistent", ErrStaleFence, attempt.AttemptID)
	}
	if !isOpenActivityStatus(activity.Status) || !isUsableWorkspaceStatus(workspace.Status) {
		return fmt.Errorf("%w: attempt %q execution aggregates are not live", ErrStaleFence, attempt.AttemptID)
	}
	if err := updateActivityStatusTx(ctx, tx, &activity, activityStatus, nowMS, reason); err != nil {
		return err
	}
	return updateWorkspaceStatusTx(ctx, tx, &workspace, workspaceStatus, nowMS, reason)
}

func updateOpenExecutionForRunTx(
	ctx context.Context,
	tx *sql.Tx,
	runID string,
	activityStatus ActivityStatus,
	workspaceStatus WorkspaceStatus,
	nowMS int64,
	reason string,
) error {
	var activityID string
	err := tx.QueryRowContext(ctx, `
		SELECT activity_id FROM activities
		WHERE run_id = ? AND status IN (?, ?, ?, ?, ?)
		ORDER BY ordinal DESC LIMIT 1
	`, runID, ActivityPlanned, ActivityReady, ActivityActive, ActivityBlocked, ActivityInterrupted).Scan(&activityID)
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return fmt.Errorf("read open activity for run %q: %w", runID, err)
	}
	if err == nil {
		activity, readErr := readActivityTx(ctx, tx, activityID)
		if readErr != nil {
			return readErr
		}
		if err := updateActivityStatusTx(ctx, tx, &activity, activityStatus, nowMS, reason); err != nil {
			return err
		}
	}

	var workspaceID string
	err = tx.QueryRowContext(ctx, `
		SELECT workspace_id FROM workspaces
		WHERE run_id = ? AND status IN (?, ?, ?)
		ORDER BY generation DESC LIMIT 1
	`, runID, WorkspaceAllocating, WorkspaceReady, WorkspaceInUse).Scan(&workspaceID)
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return fmt.Errorf("read usable workspace for run %q: %w", runID, err)
	}
	if err == nil {
		workspace, readErr := readWorkspaceTx(ctx, tx, workspaceID)
		if readErr != nil {
			return readErr
		}
		if err := updateWorkspaceStatusTx(ctx, tx, &workspace, workspaceStatus, nowMS, reason); err != nil {
			return err
		}
	}
	return nil
}

func isOpenActivityStatus(status ActivityStatus) bool {
	switch status {
	case ActivityPlanned, ActivityReady, ActivityActive, ActivityBlocked, ActivityInterrupted:
		return true
	default:
		return false
	}
}

func isUsableWorkspaceStatus(status WorkspaceStatus) bool {
	switch status {
	case WorkspaceAllocating, WorkspaceReady, WorkspaceInUse:
		return true
	default:
		return false
	}
}

func appendActivityEventTx(ctx context.Context, tx *sql.Tx, activity Activity, eventType, reason string) error {
	payload, err := json.Marshal(struct {
		RunID   string         `json:"run_id"`
		Ordinal int64          `json:"ordinal"`
		Status  ActivityStatus `json:"status"`
	}{RunID: activity.RunID, Ordinal: activity.Ordinal, Status: activity.Status})
	if err != nil {
		return fmt.Errorf("encode activity event: %w", err)
	}
	_, err = tx.ExecContext(ctx, `
		INSERT INTO events (
			aggregate_type, aggregate_id, aggregate_revision,
			event_type, reason, payload_json, created_at_ms
		) VALUES ('activity', ?, ?, ?, ?, ?, ?)
	`, activity.ActivityID, activity.Revision, eventType, reason, string(payload), activity.UpdatedAtMS)
	if err != nil {
		return fmt.Errorf("append activity event: %w", err)
	}
	return nil
}

func appendWorkspaceEventTx(ctx context.Context, tx *sql.Tx, workspace Workspace, eventType, reason string) error {
	payload, err := json.Marshal(struct {
		RunID      string          `json:"run_id"`
		Generation int64           `json:"generation"`
		Status     WorkspaceStatus `json:"status"`
	}{RunID: workspace.RunID, Generation: workspace.Generation, Status: workspace.Status})
	if err != nil {
		return fmt.Errorf("encode workspace event: %w", err)
	}
	_, err = tx.ExecContext(ctx, `
		INSERT INTO events (
			aggregate_type, aggregate_id, aggregate_revision,
			event_type, reason, payload_json, created_at_ms
		) VALUES ('workspace', ?, ?, ?, ?, ?, ?)
	`, workspace.WorkspaceID, workspace.Revision, eventType, reason, string(payload), workspace.UpdatedAtMS)
	if err != nil {
		return fmt.Errorf("append workspace event: %w", err)
	}
	return nil
}

func validateCreateActivityParams(params CreateActivityParams) error {
	if strings.TrimSpace(params.ActivityID) == "" ||
		strings.TrimSpace(params.RunID) == "" ||
		strings.TrimSpace(params.Kind) == "" {
		return fmt.Errorf("%w: activity id, run id, and kind are required", ErrInvalidArgument)
	}
	if params.InputSHA256 != "" && !validSHA256(params.InputSHA256) {
		return fmt.Errorf("%w: input_sha256 must be empty or a lowercase sha256 digest", ErrInvalidArgument)
	}
	return nil
}

func validateCreateWorkspaceParams(params CreateWorkspaceParams) error {
	required := map[string]string{
		"workspace_id":    params.WorkspaceID,
		"run_id":          params.RunID,
		"kind":            params.Kind,
		"root_path":       params.RootPath,
		"repo_common_dir": params.RepoCommonDir,
		"base_ref":        params.BaseRef,
		"base_commit":     params.BaseCommit,
		"private_ref":     params.PrivateRef,
	}
	for name, value := range required {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("%w: %s is required", ErrInvalidArgument, name)
		}
	}
	if params.Generation <= 0 {
		return fmt.Errorf("%w: workspace generation must be positive", ErrInvalidArgument)
	}
	if params.Kind != "git_worktree" {
		return fmt.Errorf("%w: unsupported workspace kind %q", ErrInvalidArgument, params.Kind)
	}
	mode := normalizeWorkspaceMode(params.Mode)
	if mode != WorkspaceModeIsolated && mode != WorkspaceModePrimary {
		return fmt.Errorf("%w: unsupported workspace mode %q", ErrInvalidArgument, params.Mode)
	}
	if mode == WorkspaceModePrimary && strings.TrimSpace(params.SourceRunID) != params.RunID {
		return fmt.Errorf("%w: primary workspace must source its own Run", ErrWorkspaceBinding)
	}
	return nil
}

func validatePrepareExecutionParams(params PrepareExecutionParams) error {
	if strings.TrimSpace(params.RunID) == "" ||
		strings.TrimSpace(params.ActivityID) == "" ||
		strings.TrimSpace(params.WorkspaceID) == "" {
		return fmt.Errorf("%w: run id, activity id, and workspace id are required", ErrInvalidArgument)
	}
	if params.ExpectedRunRevision <= 0 ||
		params.ExpectedActivityRevision <= 0 ||
		params.ExpectedWorkspaceRevision <= 0 {
		return fmt.Errorf("%w: all expected revisions must be positive", ErrInvalidArgument)
	}
	return nil
}

func runCanBePrepared(status RunStatus) bool {
	switch status {
	case RunAllocating, RunInterrupted, RunParked:
		return true
	default:
		return false
	}
}

func aggregateIDExistsTx(ctx context.Context, tx *sql.Tx, table, column, id string) (bool, error) {
	// Table and column come only from the two fixed call sites above. Keeping the
	// helper private prevents external input from reaching this SQL identifier.
	var exists int
	query := fmt.Sprintf("SELECT EXISTS (SELECT 1 FROM %s WHERE %s = ?)", table, column)
	if err := tx.QueryRowContext(ctx, query, id).Scan(&exists); err != nil {
		return false, fmt.Errorf("check existing %s record: %w", table, err)
	}
	return exists != 0, nil
}

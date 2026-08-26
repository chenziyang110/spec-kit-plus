package runcontrol

import (
	"context"
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"path"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"
)

// The Work Board is repository-scoped durable coordination state. It is not
// owned by the short-lived supervisor epoch used by an individual CLI call.
// A WorkItem owns its authority through revision, fence, and lease fields.
const workBoardSchemaSQL = `
CREATE TABLE IF NOT EXISTS work_items (
    work_id TEXT PRIMARY KEY,
    parent_work_id TEXT NOT NULL DEFAULT '',
    run_id TEXT NOT NULL DEFAULT '',
    task_ref TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    adapter_id TEXT NOT NULL,
    workspace_root TEXT NOT NULL,
    base_commit TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (
        status IN ('active', 'blocked', 'interrupted', 'completed', 'abandoned')
    ),
    next_action TEXT NOT NULL DEFAULT '',
    last_reason TEXT NOT NULL DEFAULT '',
    fence INTEGER NOT NULL CHECK (fence > 0),
    revision INTEGER NOT NULL CHECK (revision > 0),
    lease_until_ms INTEGER NOT NULL,
    heartbeat_at_ms INTEGER NOT NULL,
    recovery_hold INTEGER NOT NULL DEFAULT 0 CHECK (recovery_hold IN (0, 1)),
    observed_paths_json TEXT NOT NULL DEFAULT '[]',
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS work_items_status_lease
    ON work_items(status, lease_until_ms, updated_at_ms, work_id);

CREATE TABLE IF NOT EXISTS write_intents (
    intent_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL REFERENCES work_items(work_id) ON DELETE RESTRICT,
    path TEXT NOT NULL,
    path_key TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('create', 'modify', 'delete', 'rename')),
    reason TEXT NOT NULL DEFAULT '',
    confidence TEXT NOT NULL CHECK (confidence IN ('candidate', 'confirmed')),
    status TEXT NOT NULL CHECK (status IN ('active', 'recovery', 'released')),
    revision INTEGER NOT NULL CHECK (revision > 0),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    released_at_ms INTEGER NOT NULL DEFAULT 0,
    UNIQUE (work_id, path_key)
);

CREATE INDEX IF NOT EXISTS write_intents_conflict_lookup
    ON write_intents(confidence, status, path_key, work_id);

CREATE INDEX IF NOT EXISTS write_intents_work_history
    ON write_intents(work_id, created_at_ms, intent_id);
`

var ErrWorkIntentConflict = errors.New("work board write intent conflict")

type WorkStatus string

const (
	WorkActive      WorkStatus = "active"
	WorkBlocked     WorkStatus = "blocked"
	WorkInterrupted WorkStatus = "interrupted"
	WorkCompleted   WorkStatus = "completed"
	WorkAbandoned   WorkStatus = "abandoned"
)

type FeatureBranchPolicy string

const (
	FeatureBranchPolicyDefault     FeatureBranchPolicy = "default"
	FeatureBranchPolicyKeepCurrent FeatureBranchPolicy = "keep-current"
)

type FeatureBranchDecision struct {
	Policy         FeatureBranchPolicy
	ConcurrentWork []WorkItem
}

type WriteOperation string

const (
	WriteCreate WriteOperation = "create"
	WriteModify WriteOperation = "modify"
	WriteDelete WriteOperation = "delete"
	WriteRename WriteOperation = "rename"
)

type WriteIntentConfidence string

const (
	IntentCandidate WriteIntentConfidence = "candidate"
	IntentConfirmed WriteIntentConfidence = "confirmed"
)

type WriteIntentStatus string

const (
	WriteIntentActive   WriteIntentStatus = "active"
	WriteIntentRecovery WriteIntentStatus = "recovery"
	WriteIntentReleased WriteIntentStatus = "released"
)

type WorkItem struct {
	WorkID            string
	ParentWorkID      string
	RunID             string
	TaskRef           string
	Summary           string
	AgentID           string
	AdapterID         string
	WorkspaceRoot     string
	BaseCommit        string
	Status            WorkStatus
	NextAction        string
	LastReason        string
	Fence             int64
	Revision          int64
	LeaseUntilMS      int64
	HeartbeatAtMS     int64
	RecoveryHold      bool
	ObservedPaths     []string
	ObservedPathsJSON string
	CreatedAtMS       int64
	UpdatedAtMS       int64
}

type WriteIntent struct {
	IntentID     string
	WorkID       string
	Path         string
	PathKey      string
	Operation    WriteOperation
	Reason       string
	Confidence   WriteIntentConfidence
	Status       WriteIntentStatus
	Revision     int64
	CreatedAtMS  int64
	UpdatedAtMS  int64
	ReleasedAtMS int64
}

type WriteIntentSpec struct {
	Path       string
	Operation  WriteOperation
	Reason     string
	Confidence WriteIntentConfidence
}

type BeginWorkParams struct {
	WorkID        string
	ParentWorkID  string
	RunID         string
	TaskRef       string
	Summary       string
	AgentID       string
	AdapterID     string
	WorkspaceRoot string
	BaseCommit    string
	NextAction    string
	LeaseUntil    time.Time
	WriteIntents  []WriteIntentSpec
}

type AddWorkIntentParams struct {
	WorkID           string
	ExpectedRevision int64
	Fence            int64
	Spec             WriteIntentSpec
}

type ClaimWorkIntentsParams struct {
	WorkID           string
	ExpectedRevision int64
	Fence            int64
	Specs            []WriteIntentSpec
}

type CheckpointWorkParams struct {
	WorkID           string
	ExpectedRevision int64
	Fence            int64
	LeaseUntil       time.Time
	NextAction       string
	ObservedPaths    []string
}

type RenewWorkLeaseParams struct {
	WorkID     string
	Fence      int64
	LeaseUntil time.Time
}

type TransitionWorkParams struct {
	WorkID           string
	ExpectedRevision int64
	Fence            int64
	Target           WorkStatus
	Reason           string
	NextAction       string
}

type InterruptWorkParams struct {
	WorkID           string
	ExpectedRevision int64
	Fence            int64
	Reason           string
	NextAction       string
	ObservedPaths    []string
}

type ReconcileWorkParams struct {
	Now                   time.Time
	DirtyPathsByWorkspace map[string][]string
}

type WorkInspectionWarning struct {
	WorkspaceRoot string
	Reason        string
	Fallback      string
}

type RepositoryWorkReconciliation struct {
	Interrupted        []WorkItem
	InspectionWarnings []WorkInspectionWarning
}

type ResumeWorkParams struct {
	WorkID           string
	ExpectedRevision int64
	AgentID          string
	AdapterID        string
	WorkspaceRoot    string
	BaseCommit       string
	NextAction       string
	LeaseUntil       time.Time
}

type ListWorkParams struct {
	Statuses []WorkStatus
}

type WorkIntentConflict struct {
	RequestedPath string            `json:"requested_path"`
	OwnerPath     string            `json:"owner_path"`
	OwnerWorkID   string            `json:"owner_work_id"`
	OwnerAgentID  string            `json:"owner_agent_id"`
	OwnerSummary  string            `json:"owner_summary"`
	OwnerStatus   WriteIntentStatus `json:"owner_status"`
}

type WorkIntentConflictError struct {
	Conflicts []WorkIntentConflict `json:"conflicts"`
}

type WorkIntentOwner struct {
	Work   WorkItem
	Intent WriteIntent
}

func (err *WorkIntentConflictError) Error() string {
	if err == nil || len(err.Conflicts) == 0 {
		return ErrWorkIntentConflict.Error()
	}
	conflict := err.Conflicts[0]
	return fmt.Sprintf(
		"%s: %q overlaps %q owned by work %q",
		ErrWorkIntentConflict,
		conflict.RequestedPath,
		conflict.OwnerPath,
		conflict.OwnerWorkID,
	)
}

func (err *WorkIntentConflictError) Unwrap() error { return ErrWorkIntentConflict }

func (store *Store) BeginWork(ctx context.Context, params BeginWorkParams) (WorkItem, []WriteIntent, error) {
	normalized, specs, err := normalizeBeginWorkParams(params)
	if err != nil {
		return WorkItem{}, nil, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	work := WorkItem{
		WorkID:            normalized.WorkID,
		ParentWorkID:      normalized.ParentWorkID,
		RunID:             normalized.RunID,
		TaskRef:           normalized.TaskRef,
		Summary:           normalized.Summary,
		AgentID:           normalized.AgentID,
		AdapterID:         normalized.AdapterID,
		WorkspaceRoot:     normalized.WorkspaceRoot,
		BaseCommit:        normalized.BaseCommit,
		Status:            WorkActive,
		NextAction:        normalized.NextAction,
		Fence:             1,
		Revision:          1,
		LeaseUntilMS:      normalized.LeaseUntil.UTC().UnixMilli(),
		HeartbeatAtMS:     nowMS,
		ObservedPaths:     []string{},
		ObservedPathsJSON: "[]",
		CreatedAtMS:       nowMS,
		UpdatedAtMS:       nowMS,
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return WorkItem{}, nil, fmt.Errorf("begin work board registration: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if conflicts, err := findWorkIntentConflictsTx(ctx, tx, work.WorkID, specs); err != nil {
		return WorkItem{}, nil, err
	} else if len(conflicts) != 0 {
		return WorkItem{}, nil, &WorkIntentConflictError{Conflicts: conflicts}
	}
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO work_items (
			work_id, parent_work_id, run_id, task_ref, summary, agent_id, adapter_id,
			workspace_root, base_commit, status, next_action, last_reason,
			fence, revision, lease_until_ms, heartbeat_at_ms, recovery_hold,
			observed_paths_json, created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, 0, '[]', ?, ?)
	`, work.WorkID, work.ParentWorkID, work.RunID, work.TaskRef, work.Summary,
		work.AgentID, work.AdapterID, work.WorkspaceRoot, work.BaseCommit, work.Status,
		work.NextAction, work.Fence, work.Revision, work.LeaseUntilMS,
		work.HeartbeatAtMS, work.CreatedAtMS, work.UpdatedAtMS); err != nil {
		if isUniqueConstraintError(err) {
			return WorkItem{}, nil, fmt.Errorf("%w: work item %q", ErrAlreadyExists, work.WorkID)
		}
		return WorkItem{}, nil, fmt.Errorf("insert work item %q: %w", work.WorkID, err)
	}
	intents := make([]WriteIntent, 0, len(specs))
	for _, spec := range specs {
		intentID, err := newWorkBoardID("intent")
		if err != nil {
			return WorkItem{}, nil, err
		}
		intent := WriteIntent{
			IntentID: intentID, WorkID: work.WorkID, Path: spec.Path, PathKey: spec.pathKey,
			Operation: spec.Operation, Reason: spec.Reason, Confidence: spec.Confidence,
			Status: WriteIntentActive, Revision: 1, CreatedAtMS: nowMS, UpdatedAtMS: nowMS,
		}
		if err := insertWriteIntentTx(ctx, tx, intent); err != nil {
			return WorkItem{}, nil, err
		}
		intents = append(intents, intent)
	}
	if err := appendWorkEventTx(ctx, tx, work, "work.created", "work registered on shared board"); err != nil {
		return WorkItem{}, nil, err
	}
	if err := tx.Commit(); err != nil {
		return WorkItem{}, nil, fmt.Errorf("commit work board registration: %w", err)
	}
	return work, intents, nil
}

func (store *Store) GetWork(ctx context.Context, workID string) (WorkItem, []WriteIntent, error) {
	return getWork(ctx, store.db, workID)
}

func (view *View) GetWork(ctx context.Context, workID string) (WorkItem, []WriteIntent, error) {
	return getWork(ctx, view.db, workID)
}

func getWork(ctx context.Context, querier workBoardQuerier, workID string) (WorkItem, []WriteIntent, error) {
	workID = strings.TrimSpace(workID)
	if workID == "" {
		return WorkItem{}, nil, fmt.Errorf("%w: work_id is required", ErrInvalidArgument)
	}
	work, err := readWorkTx(ctx, querier, workID)
	if err != nil {
		return WorkItem{}, nil, err
	}
	intents, err := readWorkIntentsTx(ctx, querier, workID)
	if err != nil {
		return WorkItem{}, nil, err
	}
	return work, intents, nil
}

func (store *Store) ListWork(ctx context.Context, params ListWorkParams) ([]WorkItem, error) {
	return listWork(ctx, store.db, params)
}

func (view *View) ListWork(ctx context.Context, params ListWorkParams) ([]WorkItem, error) {
	return listWork(ctx, view.db, params)
}

// ResolveFeatureBranchPolicy preserves the historical feature-branch behavior
// unless another live task or dirty recovery hold is visible on the shared
// repository board. The current managed Work item is excluded from the test.
func (store *Store) ResolveFeatureBranchPolicy(
	ctx context.Context,
	currentWorkID string,
	now time.Time,
) (FeatureBranchDecision, error) {
	if now.IsZero() {
		now = time.Now().UTC()
	} else {
		now = now.UTC()
	}
	items, err := store.ListWork(ctx, ListWorkParams{Statuses: []WorkStatus{
		WorkActive,
		WorkBlocked,
		WorkInterrupted,
	}})
	if err != nil {
		return FeatureBranchDecision{}, err
	}
	currentWorkID = strings.TrimSpace(currentWorkID)
	concurrent := make([]WorkItem, 0)
	for _, work := range items {
		if work.WorkID == currentWorkID {
			continue
		}
		live := (work.Status == WorkActive || work.Status == WorkBlocked) &&
			work.LeaseUntilMS > now.UnixMilli()
		recovery := work.Status == WorkInterrupted && work.RecoveryHold
		if live || recovery {
			concurrent = append(concurrent, work)
		}
	}
	policy := FeatureBranchPolicyDefault
	if len(concurrent) != 0 {
		policy = FeatureBranchPolicyKeepCurrent
	}
	return FeatureBranchDecision{Policy: policy, ConcurrentWork: concurrent}, nil
}

func listWork(ctx context.Context, querier workRowsQuerier, params ListWorkParams) ([]WorkItem, error) {
	query := workSelectSQL
	args := make([]any, 0, len(params.Statuses))
	if len(params.Statuses) != 0 {
		placeholders := make([]string, 0, len(params.Statuses))
		for _, status := range params.Statuses {
			if !validWorkStatus(status) {
				return nil, fmt.Errorf("%w: unsupported work status %q", ErrInvalidArgument, status)
			}
			placeholders = append(placeholders, "?")
			args = append(args, status)
		}
		query += " WHERE status IN (" + strings.Join(placeholders, ",") + ")"
	}
	query += " ORDER BY updated_at_ms DESC, work_id"
	rows, err := querier.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list work board items: %w", err)
	}
	defer rows.Close()
	items := make([]WorkItem, 0)
	for rows.Next() {
		work, err := scanWork(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, work)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate work board items: %w", err)
	}
	return items, nil
}

func (store *Store) FindWorkOwners(ctx context.Context, requestedPath string) ([]WorkIntentOwner, error) {
	return findWorkOwners(ctx, store.db, requestedPath)
}

func (view *View) FindWorkOwners(ctx context.Context, requestedPath string) ([]WorkIntentOwner, error) {
	return findWorkOwners(ctx, view.db, requestedPath)
}

func findWorkOwners(ctx context.Context, querier workBoardQuerier, requestedPath string) ([]WorkIntentOwner, error) {
	_, pathKey, err := normalizeWorkPath(requestedPath, runtime.GOOS == "windows")
	if err != nil {
		return nil, err
	}
	items, err := listWork(ctx, querier, ListWorkParams{
		Statuses: []WorkStatus{WorkActive, WorkBlocked, WorkInterrupted},
	})
	if err != nil {
		return nil, err
	}
	owners := make([]WorkIntentOwner, 0)
	for _, work := range items {
		intents, err := readWorkIntentsTx(ctx, querier, work.WorkID)
		if err != nil {
			return nil, err
		}
		for _, intent := range intents {
			if intent.Confidence != IntentConfirmed ||
				(intent.Status != WriteIntentActive && intent.Status != WriteIntentRecovery) ||
				!workPathsOverlap(pathKey, intent.PathKey) {
				continue
			}
			owners = append(owners, WorkIntentOwner{Work: work, Intent: intent})
		}
	}
	sort.Slice(owners, func(left, right int) bool {
		if owners[left].Work.WorkID == owners[right].Work.WorkID {
			return owners[left].Intent.PathKey < owners[right].Intent.PathKey
		}
		return owners[left].Work.WorkID < owners[right].Work.WorkID
	})
	return owners, nil
}

func (store *Store) AddWorkIntent(ctx context.Context, params AddWorkIntentParams) (WorkItem, WriteIntent, error) {
	if strings.TrimSpace(params.WorkID) == "" || params.ExpectedRevision < 1 || params.Fence < 1 {
		return WorkItem{}, WriteIntent{}, fmt.Errorf("%w: work_id, expected_revision, and fence are required", ErrInvalidArgument)
	}
	spec, err := normalizeWriteIntentSpec(params.Spec)
	if err != nil {
		return WorkItem{}, WriteIntent{}, err
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return WorkItem{}, WriteIntent{}, fmt.Errorf("begin work scope expansion: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	work, err := readWorkTx(ctx, tx, params.WorkID)
	if err != nil {
		return WorkItem{}, WriteIntent{}, err
	}
	if _, registered, readErr := readExecutionActivityByWorkTx(ctx, tx, work.WorkID); readErr != nil {
		return WorkItem{}, WriteIntent{}, readErr
	} else if registered {
		return WorkItem{}, WriteIntent{}, fmt.Errorf("%w: Work %q", ErrExecutionGuardRequired, work.WorkID)
	}
	if err := requireWorkAuthority(work, params.ExpectedRevision, params.Fence, time.Now().UTC().UnixMilli()); err != nil {
		return WorkItem{}, WriteIntent{}, err
	}
	if work.Status != WorkActive && work.Status != WorkBlocked {
		return WorkItem{}, WriteIntent{}, fmt.Errorf("%w: cannot expand %q work", ErrInvalidTransition, work.Status)
	}
	existing, exists, err := readWriteIntentByWorkPathTx(ctx, tx, work.WorkID, spec.pathKey)
	if err != nil {
		return WorkItem{}, WriteIntent{}, err
	}
	if exists {
		if existing.Status == WriteIntentReleased {
			return WorkItem{}, WriteIntent{}, fmt.Errorf("%w: cannot reactivate released write intent %q outside work resume", ErrInvalidTransition, spec.Path)
		}
		if existing.Confidence == IntentConfirmed && spec.Confidence == IntentCandidate {
			return WorkItem{}, WriteIntent{}, fmt.Errorf("%w: cannot downgrade confirmed write intent %q to candidate", ErrInvalidTransition, spec.Path)
		}
	}
	if conflicts, err := findWorkIntentConflictsTx(ctx, tx, work.WorkID, []normalizedWriteIntentSpec{spec}); err != nil {
		return WorkItem{}, WriteIntent{}, err
	} else if len(conflicts) != 0 {
		return WorkItem{}, WriteIntent{}, &WorkIntentConflictError{Conflicts: conflicts}
	}
	nowMS := time.Now().UTC().UnixMilli()
	intent := existing
	eventType := "work.scope_updated"
	if exists {
		result, err := tx.ExecContext(ctx, `
			UPDATE write_intents
			SET path = ?, operation = ?, reason = ?, confidence = ?, status = ?,
			    revision = revision + 1, updated_at_ms = ?, released_at_ms = 0
			WHERE intent_id = ? AND revision = ? AND status IN (?, ?)
		`, spec.Path, spec.Operation, spec.Reason, spec.Confidence, WriteIntentActive,
			nowMS, existing.IntentID, existing.Revision, WriteIntentActive, WriteIntentRecovery)
		if err != nil {
			return WorkItem{}, WriteIntent{}, fmt.Errorf("update write intent %q: %w", spec.Path, err)
		}
		if err := requireOneCASRow(result, ErrRevisionConflict, "update work scope"); err != nil {
			return WorkItem{}, WriteIntent{}, err
		}
		intent.Path = spec.Path
		intent.Operation = spec.Operation
		intent.Reason = spec.Reason
		intent.Confidence = spec.Confidence
		intent.Status = WriteIntentActive
		intent.Revision++
		intent.UpdatedAtMS = nowMS
		intent.ReleasedAtMS = 0
	} else {
		intentID, err := newWorkBoardID("intent")
		if err != nil {
			return WorkItem{}, WriteIntent{}, err
		}
		intent = WriteIntent{
			IntentID: intentID, WorkID: work.WorkID, Path: spec.Path, PathKey: spec.pathKey,
			Operation: spec.Operation, Reason: spec.Reason, Confidence: spec.Confidence,
			Status: WriteIntentActive, Revision: 1, CreatedAtMS: nowMS, UpdatedAtMS: nowMS,
		}
		if err := insertWriteIntentTx(ctx, tx, intent); err != nil {
			return WorkItem{}, WriteIntent{}, err
		}
		eventType = "work.scope_added"
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE work_items SET revision = revision + 1, updated_at_ms = ?
		WHERE work_id = ? AND revision = ? AND fence = ?
	`, nowMS, work.WorkID, work.Revision, work.Fence)
	if err != nil {
		return WorkItem{}, WriteIntent{}, fmt.Errorf("update work after scope expansion: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "expand work scope"); err != nil {
		return WorkItem{}, WriteIntent{}, err
	}
	work.Revision++
	work.UpdatedAtMS = nowMS
	if err := appendWorkEventTx(ctx, tx, work, eventType, spec.Path); err != nil {
		return WorkItem{}, WriteIntent{}, err
	}
	if err := tx.Commit(); err != nil {
		return WorkItem{}, WriteIntent{}, fmt.Errorf("commit work scope expansion: %w", err)
	}
	return work, intent, nil
}

// ClaimWorkIntents adds or promotes one complete scope batch under a single
// Work revision. Conflicts are checked for the whole batch before any intent
// is mutated, so callers never retain a partial claim after a rejected batch.
func (store *Store) ClaimWorkIntents(ctx context.Context, params ClaimWorkIntentsParams) (WorkItem, []WriteIntent, error) {
	if strings.TrimSpace(params.WorkID) == "" || params.ExpectedRevision < 1 || params.Fence < 1 {
		return WorkItem{}, nil, fmt.Errorf("%w: work_id, expected_revision, and fence are required", ErrInvalidArgument)
	}
	normalized := make([]normalizedWriteIntentSpec, 0, len(params.Specs))
	seen := make(map[string]struct{}, len(params.Specs))
	for _, raw := range params.Specs {
		spec, err := normalizeWriteIntentSpec(raw)
		if err != nil {
			return WorkItem{}, nil, err
		}
		if _, exists := seen[spec.pathKey]; exists {
			return WorkItem{}, nil, fmt.Errorf("%w: duplicate write intent path %q", ErrInvalidArgument, spec.Path)
		}
		seen[spec.pathKey] = struct{}{}
		normalized = append(normalized, spec)
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return WorkItem{}, nil, fmt.Errorf("begin work scope claim: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	work, err := readWorkTx(ctx, tx, params.WorkID)
	if err != nil {
		return WorkItem{}, nil, err
	}
	if _, registered, readErr := readExecutionActivityByWorkTx(ctx, tx, work.WorkID); readErr != nil {
		return WorkItem{}, nil, readErr
	} else if registered {
		return WorkItem{}, nil, fmt.Errorf("%w: Work %q", ErrExecutionGuardRequired, work.WorkID)
	}
	if err := requireWorkAuthority(work, params.ExpectedRevision, params.Fence, time.Now().UTC().UnixMilli()); err != nil {
		return WorkItem{}, nil, err
	}
	if work.Status != WorkActive && work.Status != WorkBlocked {
		return WorkItem{}, nil, fmt.Errorf("%w: cannot claim scope for %q work", ErrInvalidTransition, work.Status)
	}
	if len(normalized) == 0 {
		return work, []WriteIntent{}, nil
	}

	type existingIntent struct {
		intent WriteIntent
		exists bool
	}
	existing := make([]existingIntent, len(normalized))
	for index, spec := range normalized {
		intent, exists, readErr := readWriteIntentByWorkPathTx(ctx, tx, work.WorkID, spec.pathKey)
		if readErr != nil {
			return WorkItem{}, nil, readErr
		}
		if exists {
			if intent.Status == WriteIntentReleased {
				return WorkItem{}, nil, fmt.Errorf("%w: cannot reactivate released write intent %q outside work resume", ErrInvalidTransition, spec.Path)
			}
			if intent.Confidence == IntentConfirmed && spec.Confidence == IntentCandidate {
				return WorkItem{}, nil, fmt.Errorf("%w: cannot downgrade confirmed write intent %q to candidate", ErrInvalidTransition, spec.Path)
			}
		}
		existing[index] = existingIntent{intent: intent, exists: exists}
	}
	if conflicts, conflictErr := findWorkIntentConflictsTx(ctx, tx, work.WorkID, normalized); conflictErr != nil {
		return WorkItem{}, nil, conflictErr
	} else if len(conflicts) != 0 {
		return WorkItem{}, nil, &WorkIntentConflictError{Conflicts: conflicts}
	}

	nowMS := time.Now().UTC().UnixMilli()
	claimed := make([]WriteIntent, 0, len(normalized))
	claimedPaths := make([]string, 0, len(normalized))
	for index, spec := range normalized {
		intent := existing[index].intent
		if existing[index].exists {
			result, updateErr := tx.ExecContext(ctx, `
				UPDATE write_intents
				SET path = ?, operation = ?, reason = ?, confidence = ?, status = ?,
				    revision = revision + 1, updated_at_ms = ?, released_at_ms = 0
				WHERE intent_id = ? AND revision = ? AND status IN (?, ?)
			`, spec.Path, spec.Operation, spec.Reason, spec.Confidence, WriteIntentActive,
				nowMS, intent.IntentID, intent.Revision, WriteIntentActive, WriteIntentRecovery)
			if updateErr != nil {
				return WorkItem{}, nil, fmt.Errorf("update claimed write intent %q: %w", spec.Path, updateErr)
			}
			if err := requireOneCASRow(result, ErrRevisionConflict, "claim work scope"); err != nil {
				return WorkItem{}, nil, err
			}
			intent.Path = spec.Path
			intent.Operation = spec.Operation
			intent.Reason = spec.Reason
			intent.Confidence = spec.Confidence
			intent.Status = WriteIntentActive
			intent.Revision++
			intent.UpdatedAtMS = nowMS
			intent.ReleasedAtMS = 0
		} else {
			intentID, idErr := newWorkBoardID("intent")
			if idErr != nil {
				return WorkItem{}, nil, idErr
			}
			intent = WriteIntent{
				IntentID: intentID, WorkID: work.WorkID, Path: spec.Path, PathKey: spec.pathKey,
				Operation: spec.Operation, Reason: spec.Reason, Confidence: spec.Confidence,
				Status: WriteIntentActive, Revision: 1, CreatedAtMS: nowMS, UpdatedAtMS: nowMS,
			}
			if err := insertWriteIntentTx(ctx, tx, intent); err != nil {
				return WorkItem{}, nil, err
			}
		}
		claimed = append(claimed, intent)
		claimedPaths = append(claimedPaths, spec.Path)
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE work_items SET revision = revision + 1, updated_at_ms = ?
		WHERE work_id = ? AND revision = ? AND fence = ?
	`, nowMS, work.WorkID, work.Revision, work.Fence)
	if err != nil {
		return WorkItem{}, nil, fmt.Errorf("update work after scope claim: %w", err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "claim work scope"); err != nil {
		return WorkItem{}, nil, err
	}
	work.Revision++
	work.UpdatedAtMS = nowMS
	if err := appendWorkEventTx(ctx, tx, work, "work.scope_claimed", strings.Join(claimedPaths, ", ")); err != nil {
		return WorkItem{}, nil, err
	}
	if err := tx.Commit(); err != nil {
		return WorkItem{}, nil, fmt.Errorf("commit work scope claim: %w", err)
	}
	return work, claimed, nil
}

func (store *Store) CheckpointWork(ctx context.Context, params CheckpointWorkParams) (WorkItem, error) {
	if strings.TrimSpace(params.WorkID) == "" || params.ExpectedRevision < 1 || params.Fence < 1 {
		return WorkItem{}, fmt.Errorf("%w: work_id, expected_revision, and fence are required", ErrInvalidArgument)
	}
	if params.LeaseUntil.IsZero() || !params.LeaseUntil.After(time.Now().UTC()) {
		return WorkItem{}, fmt.Errorf("%w: lease_until must be in the future", ErrInvalidArgument)
	}
	observed, observedJSON, err := normalizeWorkPathsJSON(params.ObservedPaths)
	if err != nil {
		return WorkItem{}, err
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return WorkItem{}, fmt.Errorf("begin work checkpoint: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	work, err := readWorkTx(ctx, tx, params.WorkID)
	if err != nil {
		return WorkItem{}, err
	}
	if _, registered, readErr := readExecutionActivityByWorkTx(ctx, tx, work.WorkID); readErr != nil {
		return WorkItem{}, readErr
	} else if registered {
		return WorkItem{}, fmt.Errorf("%w: Work %q", ErrExecutionCheckpointRequired, work.WorkID)
	}
	nowMS := time.Now().UTC().UnixMilli()
	if err := requireWorkAuthority(work, params.ExpectedRevision, params.Fence, nowMS); err != nil {
		return WorkItem{}, err
	}
	if work.Status != WorkActive && work.Status != WorkBlocked {
		return WorkItem{}, fmt.Errorf("%w: cannot checkpoint %q work", ErrInvalidTransition, work.Status)
	}
	if params.LeaseUntil.UTC().UnixMilli() <= work.LeaseUntilMS {
		return WorkItem{}, fmt.Errorf("%w: checkpoint must extend the work lease", ErrInvalidArgument)
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE work_items
		SET next_action = ?, observed_paths_json = ?, lease_until_ms = ?, heartbeat_at_ms = ?,
		    revision = revision + 1, updated_at_ms = ?
		WHERE work_id = ? AND revision = ? AND fence = ?
	`, strings.TrimSpace(params.NextAction), observedJSON, params.LeaseUntil.UTC().UnixMilli(),
		nowMS, nowMS, work.WorkID, work.Revision, work.Fence)
	if err != nil {
		return WorkItem{}, fmt.Errorf("checkpoint work %q: %w", work.WorkID, err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "checkpoint work"); err != nil {
		return WorkItem{}, err
	}
	work.NextAction = strings.TrimSpace(params.NextAction)
	work.ObservedPaths = observed
	work.ObservedPathsJSON = observedJSON
	work.LeaseUntilMS = params.LeaseUntil.UTC().UnixMilli()
	work.HeartbeatAtMS = nowMS
	work.Revision++
	work.UpdatedAtMS = nowMS
	if err := appendWorkEventTx(ctx, tx, work, "work.checkpointed", work.NextAction); err != nil {
		return WorkItem{}, err
	}
	if err := tx.Commit(); err != nil {
		return WorkItem{}, fmt.Errorf("commit work checkpoint: %w", err)
	}
	return work, nil
}

// RenewWorkLease is the supervisor-owned heartbeat path. It deliberately does
// not require an expected revision because a managed child may add scope or
// record a checkpoint between heartbeats. The fence and live lease remain the
// authority boundary, and renewal never overwrites child-authored progress.
func (store *Store) RenewWorkLease(ctx context.Context, params RenewWorkLeaseParams) (WorkItem, error) {
	if strings.TrimSpace(params.WorkID) == "" || params.Fence < 1 {
		return WorkItem{}, fmt.Errorf("%w: work_id and fence are required", ErrInvalidArgument)
	}
	nowMS := time.Now().UTC().UnixMilli()
	leaseUntilMS := params.LeaseUntil.UTC().UnixMilli()
	if params.LeaseUntil.IsZero() || leaseUntilMS <= nowMS {
		return WorkItem{}, fmt.Errorf("%w: lease_until must be in the future", ErrInvalidArgument)
	}
	result, err := store.db.ExecContext(ctx, `
		UPDATE work_items
		SET lease_until_ms = CASE WHEN lease_until_ms < ? THEN ? ELSE lease_until_ms END,
		    heartbeat_at_ms = ?, revision = revision + 1, updated_at_ms = ?
		WHERE work_id = ? AND fence = ? AND status IN (?, ?) AND lease_until_ms > ?
	`, leaseUntilMS, leaseUntilMS, nowMS, nowMS, strings.TrimSpace(params.WorkID), params.Fence,
		WorkActive, WorkBlocked, nowMS)
	if err != nil {
		return WorkItem{}, fmt.Errorf("renew work lease %q: %w", params.WorkID, err)
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return WorkItem{}, fmt.Errorf("inspect work lease renewal %q: %w", params.WorkID, err)
	}
	if affected != 1 {
		work, _, readErr := store.GetWork(ctx, params.WorkID)
		if readErr != nil {
			return WorkItem{}, readErr
		}
		if work.Fence != params.Fence {
			return WorkItem{}, fmt.Errorf("%w: work %q holds fence %d, received %d", ErrStaleFence, work.WorkID, work.Fence, params.Fence)
		}
		if work.Status != WorkActive && work.Status != WorkBlocked {
			return WorkItem{}, fmt.Errorf("%w: cannot renew %q work", ErrInvalidTransition, work.Status)
		}
		return WorkItem{}, fmt.Errorf("%w: work %q lease has expired", ErrStaleFence, work.WorkID)
	}
	work, _, err := store.GetWork(ctx, params.WorkID)
	return work, err
}

func (store *Store) TransitionWork(ctx context.Context, params TransitionWorkParams) (WorkItem, error) {
	if strings.TrimSpace(params.WorkID) == "" || params.ExpectedRevision < 1 || params.Fence < 1 {
		return WorkItem{}, fmt.Errorf("%w: work_id, expected_revision, and fence are required", ErrInvalidArgument)
	}
	if strings.TrimSpace(params.Reason) == "" {
		return WorkItem{}, fmt.Errorf("%w: transition reason is required", ErrInvalidArgument)
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return WorkItem{}, fmt.Errorf("begin work transition: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	work, err := readWorkTx(ctx, tx, params.WorkID)
	if err != nil {
		return WorkItem{}, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	authorityErr := requireWorkAuthority(work, params.ExpectedRevision, params.Fence, nowMS)
	if work.Status == WorkInterrupted && params.Target == WorkAbandoned {
		authorityErr = requireWorkFence(work, params.ExpectedRevision, params.Fence)
	}
	if authorityErr != nil {
		return WorkItem{}, authorityErr
	}
	if !canTransitionWork(work.Status, params.Target) {
		return WorkItem{}, fmt.Errorf("%w: %s -> %s", ErrInvalidTransition, work.Status, params.Target)
	}
	_, executionRegistered, err := readExecutionActivityByWorkTx(ctx, tx, work.WorkID)
	if err != nil {
		return WorkItem{}, err
	}
	if executionRegistered && params.Target == WorkCompleted {
		return WorkItem{}, fmt.Errorf("%w: Work %q", ErrExecutionCompletionRequired, work.WorkID)
	}
	if params.Target == WorkCompleted || params.Target == WorkAbandoned {
		if _, err := tx.ExecContext(ctx, `
			UPDATE write_intents
			SET status = ?, revision = revision + 1, updated_at_ms = ?, released_at_ms = ?
			WHERE work_id = ? AND status IN (?, ?)
		`, WriteIntentReleased, nowMS, nowMS, work.WorkID, WriteIntentActive, WriteIntentRecovery); err != nil {
			return WorkItem{}, fmt.Errorf("release write intents for work %q: %w", work.WorkID, err)
		}
		if err := markExecutionResourcesForWorkTx(
			ctx, tx, work.WorkID, WriteIntentReleased, false, nowMS,
		); err != nil {
			return WorkItem{}, err
		}
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE work_items
		SET status = ?, next_action = ?, last_reason = ?, revision = revision + 1, updated_at_ms = ?
		WHERE work_id = ? AND revision = ? AND fence = ?
	`, params.Target, strings.TrimSpace(params.NextAction), strings.TrimSpace(params.Reason),
		nowMS, work.WorkID, work.Revision, work.Fence)
	if err != nil {
		return WorkItem{}, fmt.Errorf("transition work %q: %w", work.WorkID, err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "transition work"); err != nil {
		return WorkItem{}, err
	}
	work.Status = params.Target
	work.NextAction = strings.TrimSpace(params.NextAction)
	work.LastReason = strings.TrimSpace(params.Reason)
	work.Revision++
	work.UpdatedAtMS = nowMS
	if executionRegistered {
		var executionPhase ExecutionPhase
		var executionEvent string
		switch params.Target {
		case WorkAbandoned:
			executionPhase, executionEvent = ExecutionPhaseAbandoned, "execution.abandoned"
		case WorkBlocked:
			executionPhase, executionEvent = ExecutionPhaseBlocked, "execution.blocked"
		case WorkActive:
			executionPhase, executionEvent = ExecutionPhaseSelected, "execution.resumed_from_block"
		}
		if executionEvent != "" {
			if err := transitionExecutionActivityForWorkTx(
				ctx, tx, work.WorkID, executionPhase, executionEvent, work.LastReason, nowMS,
			); err != nil {
				return WorkItem{}, err
			}
		}
	}
	if err := appendWorkEventTx(ctx, tx, work, "work.transitioned", work.LastReason); err != nil {
		return WorkItem{}, err
	}
	if err := tx.Commit(); err != nil {
		return WorkItem{}, fmt.Errorf("commit work transition: %w", err)
	}
	return work, nil
}

func (store *Store) InterruptWork(ctx context.Context, params InterruptWorkParams) (WorkItem, error) {
	if strings.TrimSpace(params.WorkID) == "" || params.ExpectedRevision < 1 || params.Fence < 1 {
		return WorkItem{}, fmt.Errorf("%w: work_id, expected_revision, and fence are required", ErrInvalidArgument)
	}
	if strings.TrimSpace(params.Reason) == "" {
		return WorkItem{}, fmt.Errorf("%w: interruption reason is required", ErrInvalidArgument)
	}
	observed, observedJSON, err := normalizeWorkPathsJSON(params.ObservedPaths)
	if err != nil {
		return WorkItem{}, err
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return WorkItem{}, fmt.Errorf("begin work interruption: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	work, err := readWorkTx(ctx, tx, params.WorkID)
	if err != nil {
		return WorkItem{}, err
	}
	if err := requireWorkFence(work, params.ExpectedRevision, params.Fence); err != nil {
		return WorkItem{}, err
	}
	if work.Status != WorkActive && work.Status != WorkBlocked {
		return WorkItem{}, fmt.Errorf("%w: cannot interrupt %q work", ErrInvalidTransition, work.Status)
	}
	intents, err := readWorkIntentsTx(ctx, tx, work.WorkID)
	if err != nil {
		return WorkItem{}, err
	}
	relevantDirty := overlappingDirtyPaths(intents, observed)
	intentStatus := WriteIntentReleased
	recoveryHold := false
	nextAction := strings.TrimSpace(params.NextAction)
	if len(relevantDirty) != 0 {
		intentStatus = WriteIntentRecovery
		recoveryHold = true
		if nextAction == "" {
			nextAction = "resume or abandon interrupted work after inspecting dirty paths"
		}
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE write_intents
		SET status = ?, revision = revision + 1, updated_at_ms = ?, released_at_ms = CASE WHEN ? = ? THEN ? ELSE released_at_ms END
		WHERE work_id = ? AND status IN (?, ?)
	`, intentStatus, time.Now().UTC().UnixMilli(), intentStatus, WriteIntentReleased, time.Now().UTC().UnixMilli(),
		work.WorkID, WriteIntentActive, WriteIntentRecovery); err != nil {
		return WorkItem{}, fmt.Errorf("mark interrupted write intents for work %q: %w", work.WorkID, err)
	}
	nowMS := time.Now().UTC().UnixMilli()
	if err := markExecutionResourcesForWorkTx(
		ctx, tx, work.WorkID, intentStatus, false, nowMS,
	); err != nil {
		return WorkItem{}, err
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE work_items
		SET status = ?, next_action = ?, last_reason = ?, fence = fence + 1,
		    revision = revision + 1, recovery_hold = ?, observed_paths_json = ?, updated_at_ms = ?
		WHERE work_id = ? AND revision = ? AND fence = ? AND status IN (?, ?)
	`, WorkInterrupted, nextAction, strings.TrimSpace(params.Reason), boolAsInt(recoveryHold), observedJSON,
		nowMS, work.WorkID, work.Revision, work.Fence, WorkActive, WorkBlocked)
	if err != nil {
		return WorkItem{}, fmt.Errorf("interrupt work %q: %w", work.WorkID, err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "interrupt work"); err != nil {
		return WorkItem{}, err
	}
	work.Status = WorkInterrupted
	work.NextAction = nextAction
	work.LastReason = strings.TrimSpace(params.Reason)
	work.Fence++
	work.Revision++
	work.RecoveryHold = recoveryHold
	work.ObservedPaths = observed
	work.ObservedPathsJSON = observedJSON
	work.UpdatedAtMS = nowMS
	if err := transitionExecutionActivityForWorkTx(
		ctx, tx, work.WorkID, ExecutionPhaseInterrupted,
		"execution.interrupted", work.LastReason, nowMS,
	); err != nil {
		return WorkItem{}, err
	}
	if err := appendWorkEventTx(ctx, tx, work, "work.interrupted", work.LastReason); err != nil {
		return WorkItem{}, err
	}
	if err := tx.Commit(); err != nil {
		return WorkItem{}, fmt.Errorf("commit work interruption: %w", err)
	}
	return work, nil
}

func (store *Store) ReconcileExpiredWork(ctx context.Context, params ReconcileWorkParams) ([]WorkItem, error) {
	now := params.Now.UTC()
	if now.IsZero() {
		now = time.Now().UTC()
	}
	dirtyByWorkspace, err := normalizeDirtyWorkspacePaths(params.DirtyPathsByWorkspace)
	if err != nil {
		return nil, err
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin work board reconciliation: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	rows, err := tx.QueryContext(ctx, workSelectSQL+`
		WHERE status IN (?, ?) AND lease_until_ms <= ?
		ORDER BY lease_until_ms, work_id
	`, WorkActive, WorkBlocked, now.UnixMilli())
	if err != nil {
		return nil, fmt.Errorf("query expired work: %w", err)
	}
	expired := make([]WorkItem, 0)
	for rows.Next() {
		work, scanErr := scanWork(rows)
		if scanErr != nil {
			_ = rows.Close()
			return nil, scanErr
		}
		expired = append(expired, work)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, fmt.Errorf("iterate expired work: %w", err)
	}
	if err := rows.Close(); err != nil {
		return nil, fmt.Errorf("close expired work rows: %w", err)
	}

	interrupted := make([]WorkItem, 0, len(expired))
	for _, work := range expired {
		intents, err := readWorkIntentsTx(ctx, tx, work.WorkID)
		if err != nil {
			return nil, err
		}
		relevantDirty := overlappingDirtyPaths(intents, dirtyByWorkspace[work.WorkspaceRoot])
		recoveryHold := len(relevantDirty) != 0
		intentStatus := WriteIntentReleased
		releasedAtMS := now.UnixMilli()
		nextAction := "resume the interrupted task or start replacement work"
		if recoveryHold {
			intentStatus = WriteIntentRecovery
			releasedAtMS = 0
			nextAction = "inspect preserved workspace changes, then resume or abandon this work"
		}
		if _, err := tx.ExecContext(ctx, `
			UPDATE write_intents
			SET status = ?, revision = revision + 1, updated_at_ms = ?, released_at_ms = ?
			WHERE work_id = ? AND status = ?
		`, intentStatus, now.UnixMilli(), releasedAtMS, work.WorkID, WriteIntentActive); err != nil {
			return nil, fmt.Errorf("reconcile write intents for work %q: %w", work.WorkID, err)
		}
		if err := markExecutionResourcesForWorkTx(
			ctx, tx, work.WorkID, intentStatus, false, now.UnixMilli(),
		); err != nil {
			return nil, err
		}
		observed, observedJSON, err := normalizeWorkPathsJSON(relevantDirty)
		if err != nil {
			return nil, err
		}
		result, err := tx.ExecContext(ctx, `
			UPDATE work_items
			SET status = ?, next_action = ?, last_reason = ?, fence = fence + 1,
			    revision = revision + 1, recovery_hold = ?, observed_paths_json = ?, updated_at_ms = ?
			WHERE work_id = ? AND revision = ? AND fence = ? AND status IN (?, ?)
		`, WorkInterrupted, nextAction, "lease expired during reconciliation", recoveryHold,
			observedJSON, now.UnixMilli(), work.WorkID, work.Revision, work.Fence,
			WorkActive, WorkBlocked)
		if err != nil {
			return nil, fmt.Errorf("interrupt expired work %q: %w", work.WorkID, err)
		}
		if err := requireOneCASRow(result, ErrRevisionConflict, "reconcile expired work"); err != nil {
			return nil, err
		}
		work.Status = WorkInterrupted
		work.NextAction = nextAction
		work.LastReason = "lease expired during reconciliation"
		work.Fence++
		work.Revision++
		work.RecoveryHold = recoveryHold
		work.ObservedPaths = observed
		work.ObservedPathsJSON = observedJSON
		work.UpdatedAtMS = now.UnixMilli()
		if err := transitionExecutionActivityForWorkTx(
			ctx, tx, work.WorkID, ExecutionPhaseInterrupted,
			"execution.interrupted", work.LastReason, now.UnixMilli(),
		); err != nil {
			return nil, err
		}
		if err := appendWorkEventTx(ctx, tx, work, "work.interrupted", work.LastReason); err != nil {
			return nil, err
		}
		interrupted = append(interrupted, work)
	}
	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit work board reconciliation: %w", err)
	}
	return interrupted, nil
}

// ReconcileRepositoryWork inspects expired workspaces and applies the same
// conservative recovery policy used by the public board command. An
// unavailable workspace is never treated as clean: its declared scopes are
// preserved behind a recovery hold.
func (store *Store) ReconcileRepositoryWork(ctx context.Context, now time.Time) (RepositoryWorkReconciliation, error) {
	now = now.UTC()
	if now.IsZero() {
		now = time.Now().UTC()
	}
	live, err := store.ListWork(ctx, ListWorkParams{Statuses: []WorkStatus{WorkActive, WorkBlocked}})
	if err != nil {
		return RepositoryWorkReconciliation{}, err
	}
	declaredByWorkspace := make(map[string][]string)
	for _, work := range live {
		if work.LeaseUntilMS > now.UnixMilli() {
			continue
		}
		_, intents, err := store.GetWork(ctx, work.WorkID)
		if err != nil {
			return RepositoryWorkReconciliation{}, err
		}
		for _, intent := range intents {
			if intent.Status == WriteIntentActive || intent.Status == WriteIntentRecovery {
				declaredByWorkspace[work.WorkspaceRoot] = append(declaredByWorkspace[work.WorkspaceRoot], intent.Path)
			}
		}
	}
	dirtyByWorkspace := make(map[string][]string, len(declaredByWorkspace))
	warnings := make([]WorkInspectionWarning, 0)
	for workspaceRoot, declaredPaths := range declaredByWorkspace {
		dirtyPaths, inspectErr := InspectWorkspaceChanges(ctx, workspaceRoot)
		if inspectErr != nil {
			dirtyByWorkspace[workspaceRoot] = append([]string(nil), declaredPaths...)
			warnings = append(warnings, WorkInspectionWarning{
				WorkspaceRoot: workspaceRoot,
				Reason:        inspectErr.Error(),
				Fallback:      "declared_scopes_preserved",
			})
			continue
		}
		dirtyByWorkspace[workspaceRoot] = dirtyPaths
	}
	interrupted, err := store.ReconcileExpiredWork(ctx, ReconcileWorkParams{
		Now: now, DirtyPathsByWorkspace: dirtyByWorkspace,
	})
	if err != nil {
		return RepositoryWorkReconciliation{}, err
	}
	return RepositoryWorkReconciliation{Interrupted: interrupted, InspectionWarnings: warnings}, nil
}

func (store *Store) ResumeWork(ctx context.Context, params ResumeWorkParams) (WorkItem, error) {
	if strings.TrimSpace(params.WorkID) == "" || params.ExpectedRevision < 1 {
		return WorkItem{}, fmt.Errorf("%w: work_id and expected_revision are required", ErrInvalidArgument)
	}
	if strings.TrimSpace(params.AgentID) == "" || strings.TrimSpace(params.AdapterID) == "" {
		return WorkItem{}, fmt.Errorf("%w: agent_id and adapter_id are required", ErrInvalidArgument)
	}
	if params.LeaseUntil.IsZero() || !params.LeaseUntil.After(time.Now().UTC()) {
		return WorkItem{}, fmt.Errorf("%w: lease_until must be in the future", ErrInvalidArgument)
	}
	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return WorkItem{}, fmt.Errorf("begin resume work: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	work, err := readWorkTx(ctx, tx, params.WorkID)
	if err != nil {
		return WorkItem{}, err
	}
	if work.Revision != params.ExpectedRevision {
		return WorkItem{}, fmt.Errorf("%w: work %q is revision %d, expected %d", ErrRevisionConflict, work.WorkID, work.Revision, params.ExpectedRevision)
	}
	if work.Status != WorkInterrupted {
		return WorkItem{}, fmt.Errorf("%w: cannot resume %q work", ErrInvalidTransition, work.Status)
	}
	intents, err := readWorkIntentsTx(ctx, tx, work.WorkID)
	if err != nil {
		return WorkItem{}, err
	}
	specs := make([]normalizedWriteIntentSpec, 0, len(intents))
	for _, intent := range intents {
		specs = append(specs, normalizedWriteIntentSpec{WriteIntentSpec: WriteIntentSpec{
			Path: intent.Path, Operation: intent.Operation, Reason: intent.Reason, Confidence: intent.Confidence,
		}, pathKey: intent.PathKey})
	}
	if conflicts, err := findWorkIntentConflictsTx(ctx, tx, work.WorkID, specs); err != nil {
		return WorkItem{}, err
	} else if len(conflicts) != 0 {
		return WorkItem{}, &WorkIntentConflictError{Conflicts: conflicts}
	}
	executionActivity, executionRegistered, err := readExecutionActivityByWorkTx(ctx, tx, work.WorkID)
	if err != nil {
		return WorkItem{}, err
	}
	if executionRegistered {
		resourceSpecs, readErr := executionResourceSpecsForResumeTx(ctx, tx, executionActivity)
		if readErr != nil {
			return WorkItem{}, readErr
		}
		resourceConflicts, conflictErr := findExecutionResourceConflictsTx(
			ctx, tx, executionActivity.ActivityID, resourceSpecs,
		)
		if conflictErr != nil {
			return WorkItem{}, conflictErr
		}
		if len(resourceConflicts) != 0 {
			return WorkItem{}, &ExecutionResourceConflictError{Conflicts: resourceConflicts}
		}
	}
	workspaceRoot := strings.TrimSpace(params.WorkspaceRoot)
	if workspaceRoot == "" {
		workspaceRoot = work.WorkspaceRoot
	} else if workspaceRoot, err = normalizeWorkspaceRoot(workspaceRoot); err != nil {
		return WorkItem{}, err
	}
	baseCommit := strings.TrimSpace(params.BaseCommit)
	if baseCommit == "" {
		baseCommit = work.BaseCommit
	}
	nowMS := time.Now().UTC().UnixMilli()
	if _, err := tx.ExecContext(ctx, `
		UPDATE write_intents
		SET status = ?, revision = revision + 1, updated_at_ms = ?, released_at_ms = 0
		WHERE work_id = ?
	`, WriteIntentActive, nowMS, work.WorkID); err != nil {
		return WorkItem{}, fmt.Errorf("reactivate write intents for work %q: %w", work.WorkID, err)
	}
	if err := markExecutionResourcesForWorkTx(
		ctx, tx, work.WorkID, WriteIntentActive, true, nowMS,
	); err != nil {
		return WorkItem{}, err
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE work_items
		SET status = ?, agent_id = ?, adapter_id = ?, workspace_root = ?, base_commit = ?,
		    next_action = ?, last_reason = '', fence = fence + 1, revision = revision + 1,
		    lease_until_ms = ?, heartbeat_at_ms = ?, recovery_hold = 0, updated_at_ms = ?
		WHERE work_id = ? AND revision = ? AND status = ?
	`, WorkActive, strings.TrimSpace(params.AgentID), strings.TrimSpace(params.AdapterID), workspaceRoot,
		baseCommit, strings.TrimSpace(params.NextAction), params.LeaseUntil.UTC().UnixMilli(),
		nowMS, nowMS, work.WorkID, work.Revision, WorkInterrupted)
	if err != nil {
		return WorkItem{}, fmt.Errorf("resume work %q: %w", work.WorkID, err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "resume work"); err != nil {
		return WorkItem{}, err
	}
	work.Status = WorkActive
	work.AgentID = strings.TrimSpace(params.AgentID)
	work.AdapterID = strings.TrimSpace(params.AdapterID)
	work.WorkspaceRoot = workspaceRoot
	work.BaseCommit = baseCommit
	work.NextAction = strings.TrimSpace(params.NextAction)
	work.LastReason = ""
	work.Fence++
	work.Revision++
	work.LeaseUntilMS = params.LeaseUntil.UTC().UnixMilli()
	work.HeartbeatAtMS = nowMS
	work.RecoveryHold = false
	work.UpdatedAtMS = nowMS
	if executionRegistered {
		if err := transitionExecutionActivityForWorkTx(
			ctx, tx, work.WorkID, ExecutionPhaseSelected,
			"execution.resumed", "interrupted execution resumed under a new fence", nowMS,
		); err != nil {
			return WorkItem{}, err
		}
	}
	if err := appendWorkEventTx(ctx, tx, work, "work.resumed", "interrupted work resumed under a new fence"); err != nil {
		return WorkItem{}, err
	}
	if err := tx.Commit(); err != nil {
		return WorkItem{}, fmt.Errorf("commit resume work: %w", err)
	}
	return work, nil
}

type normalizedWriteIntentSpec struct {
	WriteIntentSpec
	pathKey string
}

func normalizeBeginWorkParams(params BeginWorkParams) (BeginWorkParams, []normalizedWriteIntentSpec, error) {
	params.WorkID = strings.TrimSpace(params.WorkID)
	if params.WorkID == "" {
		workID, err := newWorkBoardID("work")
		if err != nil {
			return BeginWorkParams{}, nil, err
		}
		params.WorkID = workID
	}
	params.ParentWorkID = strings.TrimSpace(params.ParentWorkID)
	params.RunID = strings.TrimSpace(params.RunID)
	params.TaskRef = strings.TrimSpace(params.TaskRef)
	params.Summary = strings.TrimSpace(params.Summary)
	params.AgentID = strings.TrimSpace(params.AgentID)
	params.AdapterID = strings.TrimSpace(params.AdapterID)
	params.BaseCommit = strings.TrimSpace(params.BaseCommit)
	params.NextAction = strings.TrimSpace(params.NextAction)
	if params.Summary == "" || params.AgentID == "" || params.AdapterID == "" {
		return BeginWorkParams{}, nil, fmt.Errorf("%w: summary, agent_id, and adapter_id are required", ErrInvalidArgument)
	}
	workspaceRoot, err := normalizeWorkspaceRoot(params.WorkspaceRoot)
	if err != nil {
		return BeginWorkParams{}, nil, err
	}
	params.WorkspaceRoot = workspaceRoot
	if params.LeaseUntil.IsZero() || !params.LeaseUntil.After(time.Now().UTC()) {
		return BeginWorkParams{}, nil, fmt.Errorf("%w: lease_until must be in the future", ErrInvalidArgument)
	}
	specs := make([]normalizedWriteIntentSpec, 0, len(params.WriteIntents))
	seen := make(map[string]struct{}, len(params.WriteIntents))
	for _, raw := range params.WriteIntents {
		spec, err := normalizeWriteIntentSpec(raw)
		if err != nil {
			return BeginWorkParams{}, nil, err
		}
		if _, exists := seen[spec.pathKey]; exists {
			return BeginWorkParams{}, nil, fmt.Errorf("%w: duplicate write intent path %q", ErrInvalidArgument, spec.Path)
		}
		seen[spec.pathKey] = struct{}{}
		specs = append(specs, spec)
	}
	return params, specs, nil
}

func normalizeWriteIntentSpec(spec WriteIntentSpec) (normalizedWriteIntentSpec, error) {
	pathValue, pathKey, err := normalizeWorkPath(spec.Path, runtime.GOOS == "windows")
	if err != nil {
		return normalizedWriteIntentSpec{}, err
	}
	spec.Path = pathValue
	spec.Reason = strings.TrimSpace(spec.Reason)
	if spec.Operation == "" {
		spec.Operation = WriteModify
	}
	if spec.Confidence == "" {
		spec.Confidence = IntentConfirmed
	}
	switch spec.Operation {
	case WriteCreate, WriteModify, WriteDelete, WriteRename:
	default:
		return normalizedWriteIntentSpec{}, fmt.Errorf("%w: unsupported write operation %q", ErrInvalidArgument, spec.Operation)
	}
	switch spec.Confidence {
	case IntentCandidate, IntentConfirmed:
	default:
		return normalizedWriteIntentSpec{}, fmt.Errorf("%w: unsupported write intent confidence %q", ErrInvalidArgument, spec.Confidence)
	}
	return normalizedWriteIntentSpec{WriteIntentSpec: spec, pathKey: pathKey}, nil
}

func normalizeWorkPath(value string, caseInsensitive bool) (string, string, error) {
	value = strings.TrimSpace(strings.ReplaceAll(value, `\`, "/"))
	if value == "" || strings.ContainsRune(value, '\x00') || path.IsAbs(value) || filepath.IsAbs(value) || filepath.VolumeName(value) != "" {
		return "", "", fmt.Errorf("%w: write intent path must be repository-relative", ErrInvalidArgument)
	}
	cleaned := path.Clean(value)
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, "../") {
		return "", "", fmt.Errorf("%w: write intent path escapes the repository", ErrInvalidArgument)
	}
	key := cleaned
	if caseInsensitive {
		key = strings.ToLower(key)
	}
	return cleaned, key, nil
}

func workPathsOverlap(left, right string) bool {
	left = strings.TrimSuffix(left, "/")
	right = strings.TrimSuffix(right, "/")
	return left == right || strings.HasPrefix(left, right+"/") || strings.HasPrefix(right, left+"/")
}

// WritePathsOverlap applies the Work Board's repository-relative path
// normalization and same/ancestor/descendant overlap semantics.
func WritePathsOverlap(left, right string) (bool, error) {
	_, leftKey, err := normalizeWorkPath(left, runtime.GOOS == "windows")
	if err != nil {
		return false, err
	}
	_, rightKey, err := normalizeWorkPath(right, runtime.GOOS == "windows")
	if err != nil {
		return false, err
	}
	return workPathsOverlap(leftKey, rightKey), nil
}

func findWorkIntentConflictsTx(
	ctx context.Context,
	tx *sql.Tx,
	requesterWorkID string,
	requested []normalizedWriteIntentSpec,
) ([]WorkIntentConflict, error) {
	confirmed := make([]normalizedWriteIntentSpec, 0, len(requested))
	for _, spec := range requested {
		if spec.Confidence == IntentConfirmed {
			confirmed = append(confirmed, spec)
		}
	}
	if len(confirmed) == 0 {
		return nil, nil
	}
	rows, err := tx.QueryContext(ctx, `
		SELECT i.work_id, w.agent_id, w.summary, i.path, i.path_key, i.status
		FROM write_intents AS i
		JOIN work_items AS w ON w.work_id = i.work_id
		WHERE i.work_id <> ? AND i.confidence = ? AND i.status IN (?, ?)
		ORDER BY i.work_id, i.path_key
	`, requesterWorkID, IntentConfirmed, WriteIntentActive, WriteIntentRecovery)
	if err != nil {
		return nil, fmt.Errorf("query work intent conflicts: %w", err)
	}
	defer rows.Close()
	type ownerIntent struct {
		workID, agentID, summary, path, pathKey string
		status                                  WriteIntentStatus
	}
	owners := make([]ownerIntent, 0)
	for rows.Next() {
		var owner ownerIntent
		if err := rows.Scan(&owner.workID, &owner.agentID, &owner.summary, &owner.path, &owner.pathKey, &owner.status); err != nil {
			return nil, fmt.Errorf("scan work intent conflict: %w", err)
		}
		owners = append(owners, owner)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate work intent conflicts: %w", err)
	}
	conflicts := make([]WorkIntentConflict, 0)
	for _, spec := range confirmed {
		for _, owner := range owners {
			if workPathsOverlap(spec.pathKey, owner.pathKey) {
				conflicts = append(conflicts, WorkIntentConflict{
					RequestedPath: spec.Path, OwnerPath: owner.path, OwnerWorkID: owner.workID,
					OwnerAgentID: owner.agentID, OwnerSummary: owner.summary, OwnerStatus: owner.status,
				})
			}
		}
	}
	return conflicts, nil
}

func insertWriteIntentTx(ctx context.Context, tx *sql.Tx, intent WriteIntent) error {
	_, err := tx.ExecContext(ctx, `
		INSERT INTO write_intents (
			intent_id, work_id, path, path_key, operation, reason, confidence, status,
			revision, created_at_ms, updated_at_ms, released_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, intent.IntentID, intent.WorkID, intent.Path, intent.PathKey, intent.Operation,
		intent.Reason, intent.Confidence, intent.Status, intent.Revision,
		intent.CreatedAtMS, intent.UpdatedAtMS, intent.ReleasedAtMS)
	if err != nil {
		if isUniqueConstraintError(err) {
			return fmt.Errorf("%w: write intent %q for work %q", ErrAlreadyExists, intent.Path, intent.WorkID)
		}
		return fmt.Errorf("insert write intent %q: %w", intent.Path, err)
	}
	return nil
}

const workSelectSQL = `
	SELECT work_id, parent_work_id, run_id, task_ref, summary, agent_id, adapter_id,
	       workspace_root, base_commit, status, next_action, last_reason,
	       fence, revision, lease_until_ms, heartbeat_at_ms, recovery_hold,
	       observed_paths_json, created_at_ms, updated_at_ms
	FROM work_items`

func readWorkTx(ctx context.Context, querier rowQuerier, workID string) (WorkItem, error) {
	work, err := scanWork(querier.QueryRowContext(ctx, workSelectSQL+" WHERE work_id = ?", workID))
	if errors.Is(err, sql.ErrNoRows) {
		return WorkItem{}, fmt.Errorf("%w: work item %q", ErrNotFound, workID)
	}
	if err != nil {
		return WorkItem{}, fmt.Errorf("read work item %q: %w", workID, err)
	}
	return work, nil
}

type workScanner interface {
	Scan(...any) error
}

func scanWork(scanner workScanner) (WorkItem, error) {
	var work WorkItem
	var recoveryHold int
	if err := scanner.Scan(
		&work.WorkID, &work.ParentWorkID, &work.RunID, &work.TaskRef, &work.Summary,
		&work.AgentID, &work.AdapterID, &work.WorkspaceRoot, &work.BaseCommit, &work.Status,
		&work.NextAction, &work.LastReason, &work.Fence, &work.Revision, &work.LeaseUntilMS,
		&work.HeartbeatAtMS, &recoveryHold, &work.ObservedPathsJSON, &work.CreatedAtMS,
		&work.UpdatedAtMS,
	); err != nil {
		return WorkItem{}, err
	}
	work.RecoveryHold = recoveryHold != 0
	if err := json.Unmarshal([]byte(work.ObservedPathsJSON), &work.ObservedPaths); err != nil {
		return WorkItem{}, fmt.Errorf("decode observed paths for work %q: %w", work.WorkID, err)
	}
	if work.ObservedPaths == nil {
		work.ObservedPaths = []string{}
	}
	return work, nil
}

type workRowsQuerier interface {
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
}

type workBoardQuerier interface {
	rowQuerier
	workRowsQuerier
}

func readWriteIntentByWorkPathTx(
	ctx context.Context,
	querier rowQuerier,
	workID string,
	pathKey string,
) (WriteIntent, bool, error) {
	var intent WriteIntent
	err := querier.QueryRowContext(ctx, `
		SELECT intent_id, work_id, path, path_key, operation, reason, confidence, status,
		       revision, created_at_ms, updated_at_ms, released_at_ms
		FROM write_intents
		WHERE work_id = ? AND path_key = ?
	`, workID, pathKey).Scan(
		&intent.IntentID, &intent.WorkID, &intent.Path, &intent.PathKey, &intent.Operation,
		&intent.Reason, &intent.Confidence, &intent.Status, &intent.Revision,
		&intent.CreatedAtMS, &intent.UpdatedAtMS, &intent.ReleasedAtMS,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return WriteIntent{}, false, nil
	}
	if err != nil {
		return WriteIntent{}, false, fmt.Errorf("read write intent %q for work %q: %w", pathKey, workID, err)
	}
	return intent, true, nil
}

func readWorkIntentsTx(ctx context.Context, querier workRowsQuerier, workID string) ([]WriteIntent, error) {
	rows, err := querier.QueryContext(ctx, `
		SELECT intent_id, work_id, path, path_key, operation, reason, confidence, status,
		       revision, created_at_ms, updated_at_ms, released_at_ms
		FROM write_intents
		WHERE work_id = ?
		ORDER BY created_at_ms, intent_id
	`, workID)
	if err != nil {
		return nil, fmt.Errorf("list write intents for work %q: %w", workID, err)
	}
	defer rows.Close()
	intents := make([]WriteIntent, 0)
	for rows.Next() {
		var intent WriteIntent
		if err := rows.Scan(
			&intent.IntentID, &intent.WorkID, &intent.Path, &intent.PathKey, &intent.Operation,
			&intent.Reason, &intent.Confidence, &intent.Status, &intent.Revision,
			&intent.CreatedAtMS, &intent.UpdatedAtMS, &intent.ReleasedAtMS,
		); err != nil {
			return nil, fmt.Errorf("scan write intent for work %q: %w", workID, err)
		}
		intents = append(intents, intent)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate write intents for work %q: %w", workID, err)
	}
	return intents, nil
}

func requireWorkAuthority(work WorkItem, expectedRevision, fence, nowMS int64) error {
	if err := requireWorkFence(work, expectedRevision, fence); err != nil {
		return err
	}
	if work.LeaseUntilMS <= nowMS {
		return fmt.Errorf("%w: work %q lease has expired", ErrStaleFence, work.WorkID)
	}
	return nil
}

func requireWorkFence(work WorkItem, expectedRevision, fence int64) error {
	if work.Revision != expectedRevision {
		return fmt.Errorf("%w: work %q is revision %d, expected %d", ErrRevisionConflict, work.WorkID, work.Revision, expectedRevision)
	}
	if work.Fence != fence {
		return fmt.Errorf("%w: work %q holds fence %d, received %d", ErrStaleFence, work.WorkID, work.Fence, fence)
	}
	return nil
}

func canTransitionWork(from, to WorkStatus) bool {
	switch from {
	case WorkActive:
		return to == WorkBlocked || to == WorkCompleted || to == WorkAbandoned
	case WorkBlocked:
		return to == WorkActive || to == WorkCompleted || to == WorkAbandoned
	case WorkInterrupted:
		return to == WorkAbandoned
	default:
		return false
	}
}

func validWorkStatus(status WorkStatus) bool {
	switch status {
	case WorkActive, WorkBlocked, WorkInterrupted, WorkCompleted, WorkAbandoned:
		return true
	default:
		return false
	}
}

func boolAsInt(value bool) int {
	if value {
		return 1
	}
	return 0
}

func appendWorkEventTx(ctx context.Context, tx *sql.Tx, work WorkItem, eventType, reason string) error {
	payload, err := json.Marshal(struct {
		Status       WorkStatus `json:"status"`
		Fence        int64      `json:"fence"`
		RecoveryHold bool       `json:"recovery_hold"`
	}{Status: work.Status, Fence: work.Fence, RecoveryHold: work.RecoveryHold})
	if err != nil {
		return fmt.Errorf("encode work event: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO events (
			aggregate_type, aggregate_id, aggregate_revision,
			event_type, reason, payload_json, created_at_ms
		) VALUES ('work', ?, ?, ?, ?, ?, ?)
	`, work.WorkID, work.Revision, eventType, strings.TrimSpace(reason), string(payload), work.UpdatedAtMS); err != nil {
		return fmt.Errorf("append work event for %q: %w", work.WorkID, err)
	}
	return nil
}

func normalizeWorkspaceRoot(value string) (string, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return "", fmt.Errorf("%w: workspace_root is required", ErrInvalidArgument)
	}
	absolute, err := filepath.Abs(value)
	if err != nil {
		return "", fmt.Errorf("resolve workspace_root: %w", err)
	}
	return filepath.Clean(absolute), nil
}

func normalizeWorkPathsJSON(values []string) ([]string, string, error) {
	seen := make(map[string]string, len(values))
	for _, value := range values {
		pathValue, pathKey, err := normalizeWorkPath(value, runtime.GOOS == "windows")
		if err != nil {
			return nil, "", err
		}
		seen[pathKey] = pathValue
	}
	keys := make([]string, 0, len(seen))
	for key := range seen {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	paths := make([]string, 0, len(keys))
	for _, key := range keys {
		paths = append(paths, seen[key])
	}
	encoded, err := json.Marshal(paths)
	if err != nil {
		return nil, "", fmt.Errorf("encode work paths: %w", err)
	}
	return paths, string(encoded), nil
}

func normalizeDirtyWorkspacePaths(values map[string][]string) (map[string][]string, error) {
	normalized := make(map[string][]string, len(values))
	for workspace, paths := range values {
		workspaceRoot, err := normalizeWorkspaceRoot(workspace)
		if err != nil {
			return nil, err
		}
		cleaned, _, err := normalizeWorkPathsJSON(paths)
		if err != nil {
			return nil, err
		}
		normalized[workspaceRoot] = cleaned
	}
	return normalized, nil
}

func overlappingDirtyPaths(intents []WriteIntent, dirtyPaths []string) []string {
	overlaps := make([]string, 0)
	seen := make(map[string]struct{})
	for _, dirty := range dirtyPaths {
		_, dirtyKey, err := normalizeWorkPath(dirty, runtime.GOOS == "windows")
		if err != nil {
			continue
		}
		for _, intent := range intents {
			if intent.Status == WriteIntentReleased {
				continue
			}
			if workPathsOverlap(intent.PathKey, dirtyKey) {
				if _, exists := seen[dirtyKey]; !exists {
					overlaps = append(overlaps, dirty)
					seen[dirtyKey] = struct{}{}
				}
				break
			}
		}
	}
	sort.Strings(overlaps)
	return overlaps
}

func newWorkBoardID(prefix string) (string, error) {
	buffer := make([]byte, 12)
	if _, err := rand.Read(buffer); err != nil {
		return "", fmt.Errorf("generate work board id: %w", err)
	}
	return prefix + "_" + hex.EncodeToString(buffer), nil
}

package runcontrol

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"runtime"
	"sort"
	"strings"
	"time"
)

const executionActivitySchemaSQL = `
CREATE TABLE IF NOT EXISTS execution_activities (
    activity_id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL UNIQUE REFERENCES work_items(work_id) ON DELETE RESTRICT,
    workflow TEXT NOT NULL CHECK (workflow IN ('fast', 'debug', 'implement', 'quick')),
    subject_id TEXT NOT NULL,
    item_id TEXT NOT NULL DEFAULT '',
    task_ref TEXT NOT NULL,
    source_ref TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (
        phase IN ('announced', 'selected', 'claimed', 'executing', 'validating',
                  'blocked', 'interrupted', 'completed', 'abandoned')
    ),
    baseline_json TEXT NOT NULL DEFAULT '{}',
    guarded_overview_revision INTEGER NOT NULL DEFAULT 0 CHECK (guarded_overview_revision >= 0),
    guarded_overview_sha256 TEXT NOT NULL DEFAULT '' CHECK (
        guarded_overview_sha256 = '' OR (
            length(guarded_overview_sha256) = 64 AND
            guarded_overview_sha256 NOT GLOB '*[^0-9a-f]*'
        )
    ),
    validation_json TEXT NOT NULL DEFAULT '[]',
    completion_sha256 TEXT NOT NULL DEFAULT '' CHECK (
        completion_sha256 = '' OR (
            length(completion_sha256) = 64 AND
            completion_sha256 NOT GLOB '*[^0-9a-f]*'
        )
    ),
    revision INTEGER NOT NULL CHECK (revision > 0),
    completed_at_ms INTEGER NOT NULL DEFAULT 0,
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS execution_activities_open_lookup
    ON execution_activities(phase, workflow, subject_id, item_id, updated_at_ms, activity_id);

CREATE INDEX IF NOT EXISTS execution_activities_task_lookup
    ON execution_activities(task_ref, phase, activity_id);

CREATE TABLE IF NOT EXISTS execution_resource_intents (
    resource_intent_id TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL REFERENCES execution_activities(activity_id) ON DELETE RESTRICT,
    work_id TEXT NOT NULL REFERENCES work_items(work_id) ON DELETE RESTRICT,
    resource_type TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    resource_key_normalized TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('shared', 'exclusive')),
    confidence TEXT NOT NULL CHECK (confidence IN ('candidate', 'confirmed')),
    status TEXT NOT NULL CHECK (status IN ('active', 'recovery', 'released')),
    reason TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL CHECK (revision > 0),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    released_at_ms INTEGER NOT NULL DEFAULT 0,
    UNIQUE (activity_id, resource_type, resource_key_normalized)
);

CREATE INDEX IF NOT EXISTS execution_resource_conflict_lookup
    ON execution_resource_intents(
        resource_type, resource_key_normalized, confidence, status, mode, activity_id
    );

CREATE INDEX IF NOT EXISTS execution_resource_activity_history
    ON execution_resource_intents(activity_id, created_at_ms, resource_intent_id);
`

var (
	ErrExecutionSnapshotStale      = errors.New("execution overview snapshot is stale")
	ErrExecutionResourceConflict   = errors.New("execution semantic resource conflict")
	ErrExecutionTaskConflict       = errors.New("execution task already has another live owner")
	ErrExecutionCompletionGate     = errors.New("execution completion audit failed")
	ErrExecutionGuardRequired      = errors.New("registered execution activity must claim scope through execution guard")
	ErrExecutionCheckpointRequired = errors.New("registered execution activity must checkpoint through execution lifecycle")
	ErrExecutionCompletionRequired = errors.New("registered execution activity must complete through execution audit")
)

type ExecutionWorkflow string

const (
	ExecutionWorkflowFast      ExecutionWorkflow = "fast"
	ExecutionWorkflowDebug     ExecutionWorkflow = "debug"
	ExecutionWorkflowImplement ExecutionWorkflow = "implement"
	ExecutionWorkflowQuick     ExecutionWorkflow = "quick"
)

type ExecutionPhase string

const (
	ExecutionPhaseAnnounced   ExecutionPhase = "announced"
	ExecutionPhaseSelected    ExecutionPhase = "selected"
	ExecutionPhaseClaimed     ExecutionPhase = "claimed"
	ExecutionPhaseExecuting   ExecutionPhase = "executing"
	ExecutionPhaseValidating  ExecutionPhase = "validating"
	ExecutionPhaseBlocked     ExecutionPhase = "blocked"
	ExecutionPhaseInterrupted ExecutionPhase = "interrupted"
	ExecutionPhaseCompleted   ExecutionPhase = "completed"
	ExecutionPhaseAbandoned   ExecutionPhase = "abandoned"
)

type ExecutionActivity struct {
	ActivityID              string
	WorkID                  string
	Workflow                ExecutionWorkflow
	SubjectID               string
	ItemID                  string
	TaskRef                 string
	SourceRef               string
	Title                   string
	Phase                   ExecutionPhase
	BaselineJSON            string
	GuardedOverviewRevision int64
	GuardedOverviewSHA256   string
	ValidationJSON          string
	CompletionSHA256        string
	Revision                int64
	CompletedAtMS           int64
	CreatedAtMS             int64
	UpdatedAtMS             int64
}

type ExecutionResourceIntent struct {
	ResourceIntentID      string
	ActivityID            string
	WorkID                string
	ResourceType          ResourceType
	ResourceKey           string
	ResourceKeyNormalized string
	Mode                  ResourceClaimMode
	Confidence            WriteIntentConfidence
	Status                WriteIntentStatus
	Reason                string
	Revision              int64
	CreatedAtMS           int64
	UpdatedAtMS           int64
	ReleasedAtMS          int64
}

type ExecutionResourceIntentSpec struct {
	ResourceType ResourceType
	ResourceKey  string
	Mode         ResourceClaimMode
	Confidence   WriteIntentConfidence
	Reason       string
}

type AnnounceExecutionParams struct {
	ActivityID          string
	WorkID              string
	ParentWorkID        string
	RunID               string // Optional historical metadata; never execution authority.
	TaskRef             string
	Workflow            ExecutionWorkflow
	SubjectID           string
	ItemID              string
	SourceRef           string
	Summary             string
	AgentID             string
	AdapterID           string
	WorkspaceRoot       string
	BaseCommit          string
	NextAction          string
	LeaseUntil          time.Time
	BaselineJSON        string
	PlannedWriteIntents []WriteIntentSpec
	Resources           []ExecutionResourceIntentSpec
}

type ExecutionRegistration struct {
	Activity     ExecutionActivity
	Work         WorkItem
	WriteIntents []WriteIntent
	Resources    []ExecutionResourceIntent
}

type ListExecutionActivitiesParams struct {
	Phases []ExecutionPhase
}

type ExecutionResourceConflict struct {
	ResourceType    ResourceType
	ResourceKey     string
	OwnerActivityID string
	OwnerWorkID     string
	OwnerMode       ResourceClaimMode
}

type ExecutionResourceConflictError struct {
	Conflicts []ExecutionResourceConflict
}

func (err *ExecutionResourceConflictError) Error() string {
	if err == nil || len(err.Conflicts) == 0 {
		return ErrExecutionResourceConflict.Error()
	}
	conflict := err.Conflicts[0]
	return fmt.Sprintf(
		"%s: %s/%s is held by activity %q",
		ErrExecutionResourceConflict,
		conflict.ResourceType,
		conflict.ResourceKey,
		conflict.OwnerActivityID,
	)
}

func (err *ExecutionResourceConflictError) Unwrap() error { return ErrExecutionResourceConflict }

type ExecutionTaskConflictError struct {
	TaskRef         string
	OwnerActivityID string
	OwnerWorkID     string
}

func (err *ExecutionTaskConflictError) Error() string {
	if err == nil {
		return ErrExecutionTaskConflict.Error()
	}
	return fmt.Sprintf(
		"%s: task %q is already announced by activity %q",
		ErrExecutionTaskConflict,
		err.TaskRef,
		err.OwnerActivityID,
	)
}

func (err *ExecutionTaskConflictError) Unwrap() error { return ErrExecutionTaskConflict }

type GuardExecutionParams struct {
	ActivityID                   string
	ExpectedWorkRevision         int64
	Fence                        int64
	ExpectedCoordinationRevision int64
	OverviewSHA256               string
	WriteIntents                 []WriteIntentSpec
	Resources                    []ExecutionResourceIntentSpec
	ScopeAmendments              []ExecutionScopeAmendmentSpec
	Reason                       string
}

type GuardedExecution struct {
	ExecutionRegistration
	CoordinationRevision int64
}

type CheckpointExecutionParams struct {
	ActivityID           string
	ExpectedWorkRevision int64
	Fence                int64
	TargetPhase          ExecutionPhase
	NextAction           string
	ObservedPaths        []string
	LeaseUntil           time.Time
	Reason               string
}

type CheckpointedExecution struct {
	ExecutionRegistration
	CoordinationRevision int64
}

type CompleteExecutionParams struct {
	ActivityID           string
	ExpectedWorkRevision int64
	Fence                int64
	ChangedPaths         []string
	ControlPlaneFiles    []ExecutionFileDigestExpectation
	ValidationJSON       string
	Reason               string
}

type ExecutionFileDigestExpectation struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
}

type CompletedExecution struct {
	ExecutionRegistration
	ChangedPaths         []string
	CoordinationRevision int64
}

type ExecutionScopeAuditError struct {
	UnclaimedPaths []string
}

func (err *ExecutionScopeAuditError) Error() string {
	if err == nil || len(err.UnclaimedPaths) == 0 {
		return ErrExecutionCompletionGate.Error()
	}
	return fmt.Sprintf(
		"%s: actual changed paths are outside confirmed scope: %s",
		ErrExecutionCompletionGate,
		strings.Join(err.UnclaimedPaths, ", "),
	)
}

func (err *ExecutionScopeAuditError) Unwrap() error { return ErrExecutionCompletionGate }

type ExecutionControlPlaneDriftError struct {
	Paths []string
}

func (err *ExecutionControlPlaneDriftError) Error() string {
	if err == nil || len(err.Paths) == 0 {
		return ErrExecutionCompletionGate.Error()
	}
	return fmt.Sprintf(
		"%s: workflow control-plane files changed after validation: %s",
		ErrExecutionCompletionGate,
		strings.Join(err.Paths, ", "),
	)
}

func (err *ExecutionControlPlaneDriftError) Unwrap() error { return ErrExecutionCompletionGate }

func (store *Store) GuardExecution(ctx context.Context, params GuardExecutionParams) (GuardedExecution, error) {
	params.ActivityID = strings.TrimSpace(params.ActivityID)
	params.OverviewSHA256 = strings.TrimSpace(params.OverviewSHA256)
	params.Reason = strings.TrimSpace(params.Reason)
	if params.ActivityID == "" || params.ExpectedWorkRevision < 1 || params.Fence < 1 ||
		params.ExpectedCoordinationRevision < 0 || !validSHA256(params.OverviewSHA256) {
		return GuardedExecution{}, fmt.Errorf(
			"%w: activity_id, expected work revision, fence, overview revision, and overview sha256 are required",
			ErrInvalidArgument,
		)
	}
	if params.Reason == "" {
		return GuardedExecution{}, fmt.Errorf("%w: guard reason is required", ErrInvalidArgument)
	}
	writes := make([]normalizedWriteIntentSpec, 0, len(params.WriteIntents))
	seenWrites := make(map[string]struct{}, len(params.WriteIntents))
	for _, raw := range params.WriteIntents {
		spec, err := normalizeWriteIntentSpec(raw)
		if err != nil {
			return GuardedExecution{}, err
		}
		if spec.Confidence != IntentConfirmed {
			return GuardedExecution{}, fmt.Errorf("%w: guarded write scope must be confirmed", ErrInvalidArgument)
		}
		if _, exists := seenWrites[spec.pathKey]; exists {
			return GuardedExecution{}, fmt.Errorf("%w: duplicate guarded write path %q", ErrInvalidArgument, spec.Path)
		}
		seenWrites[spec.pathKey] = struct{}{}
		writes = append(writes, spec)
	}
	resources, err := normalizeExecutionResourceSpecs(params.Resources, IntentConfirmed)
	if err != nil {
		return GuardedExecution{}, err
	}
	for _, resource := range resources {
		if resource.Confidence != IntentConfirmed {
			return GuardedExecution{}, fmt.Errorf("%w: guarded semantic resources must be confirmed", ErrInvalidArgument)
		}
	}
	if len(writes) == 0 && len(resources) == 0 {
		return GuardedExecution{}, fmt.Errorf("%w: guard requires write scope or semantic resources", ErrInvalidArgument)
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return GuardedExecution{}, fmt.Errorf("begin execution guard: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	currentCoordinationRevision, err := coordinationRevision(ctx, tx)
	if err != nil {
		return GuardedExecution{}, err
	}
	if currentCoordinationRevision != params.ExpectedCoordinationRevision {
		return GuardedExecution{}, fmt.Errorf(
			"%w: current coordination revision is %d, observed %d",
			ErrExecutionSnapshotStale,
			currentCoordinationRevision,
			params.ExpectedCoordinationRevision,
		)
	}
	activity, err := readExecutionActivity(ctx, tx, params.ActivityID)
	if err != nil {
		return GuardedExecution{}, err
	}
	amendments, err := normalizeExecutionScopeAmendmentSpecs(activity, params.ScopeAmendments)
	if err != nil {
		return GuardedExecution{}, err
	}
	for _, amendment := range amendments {
		_, amendmentKey, _ := normalizeWorkPath(amendment.Path, runtime.GOOS == "windows")
		claimedExactly := false
		for _, spec := range writes {
			if spec.pathKey == amendmentKey {
				claimedExactly = true
				break
			}
		}
		if !claimedExactly {
			return GuardedExecution{}, fmt.Errorf("%w: scope amendment %q must be claimed exactly by the same guard", ErrExecutionGuardRequired, amendment.Path)
		}
	}
	paths := make([]string, 0, len(writes))
	for _, spec := range writes {
		paths = append(paths, spec.Path)
	}
	if err := verifyExecutionPacketScopeWithPending(activity, paths, amendments); err != nil {
		return GuardedExecution{}, err
	}
	work, err := readWorkTx(ctx, tx, activity.WorkID)
	if err != nil {
		return GuardedExecution{}, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	amendedBaseline, err := appendExecutionScopeAmendments(activity.BaselineJSON, amendments, nowMS)
	if err != nil {
		return GuardedExecution{}, err
	}
	if err := requireWorkAuthority(work, params.ExpectedWorkRevision, params.Fence, nowMS); err != nil {
		return GuardedExecution{}, err
	}
	if work.Status != WorkActive && work.Status != WorkBlocked {
		return GuardedExecution{}, fmt.Errorf("%w: cannot guard %q work", ErrInvalidTransition, work.Status)
	}
	if activity.Phase == ExecutionPhaseValidating && len(params.ScopeAmendments) == 0 {
		return GuardedExecution{}, fmt.Errorf("%w: validating execution may re-enter guard only for an audited scope amendment", ErrInvalidTransition)
	}
	switch activity.Phase {
	case ExecutionPhaseAnnounced, ExecutionPhaseSelected, ExecutionPhaseClaimed,
		ExecutionPhaseExecuting, ExecutionPhaseValidating, ExecutionPhaseBlocked:
	default:
		return GuardedExecution{}, fmt.Errorf("%w: cannot guard execution in %q phase", ErrInvalidTransition, activity.Phase)
	}
	if conflict, found, conflictErr := findExecutionTaskConflictTx(ctx, tx, activity, work, nowMS); conflictErr != nil {
		return GuardedExecution{}, conflictErr
	} else if found {
		return GuardedExecution{}, &ExecutionTaskConflictError{
			TaskRef: activity.TaskRef, OwnerActivityID: conflict.ActivityID, OwnerWorkID: conflict.WorkID,
		}
	}
	if conflicts, conflictErr := findWorkIntentConflictsTx(ctx, tx, work.WorkID, writes); conflictErr != nil {
		return GuardedExecution{}, conflictErr
	} else if len(conflicts) != 0 {
		return GuardedExecution{}, &WorkIntentConflictError{Conflicts: conflicts}
	}
	resourceConflicts, err := findExecutionResourceConflictsTx(ctx, tx, activity.ActivityID, resources)
	if err != nil {
		return GuardedExecution{}, err
	}
	if len(resourceConflicts) != 0 {
		return GuardedExecution{}, &ExecutionResourceConflictError{Conflicts: resourceConflicts}
	}

	for _, spec := range writes {
		intent, exists, readErr := readWriteIntentByWorkPathTx(ctx, tx, work.WorkID, spec.pathKey)
		if readErr != nil {
			return GuardedExecution{}, readErr
		}
		if exists {
			if intent.Status == WriteIntentReleased {
				return GuardedExecution{}, fmt.Errorf("%w: cannot reactivate released write intent %q", ErrInvalidTransition, spec.Path)
			}
			result, updateErr := tx.ExecContext(ctx, `
				UPDATE write_intents
				SET path = ?, operation = ?, reason = ?, confidence = ?, status = ?,
				    revision = revision + 1, updated_at_ms = ?, released_at_ms = 0
				WHERE intent_id = ? AND revision = ? AND status IN (?, ?)
			`, spec.Path, spec.Operation, spec.Reason, IntentConfirmed, WriteIntentActive,
				nowMS, intent.IntentID, intent.Revision, WriteIntentActive, WriteIntentRecovery)
			if updateErr != nil {
				return GuardedExecution{}, fmt.Errorf("promote guarded write intent %q: %w", spec.Path, updateErr)
			}
			if err := requireOneCASRow(result, ErrRevisionConflict, "promote guarded write intent"); err != nil {
				return GuardedExecution{}, err
			}
		} else {
			intentID, idErr := newWorkBoardID("intent")
			if idErr != nil {
				return GuardedExecution{}, idErr
			}
			intent = WriteIntent{
				IntentID: intentID, WorkID: work.WorkID, Path: spec.Path, PathKey: spec.pathKey,
				Operation: spec.Operation, Reason: spec.Reason, Confidence: IntentConfirmed,
				Status: WriteIntentActive, Revision: 1, CreatedAtMS: nowMS, UpdatedAtMS: nowMS,
			}
			if err := insertWriteIntentTx(ctx, tx, intent); err != nil {
				return GuardedExecution{}, err
			}
		}
	}
	for _, spec := range resources {
		resource, exists, readErr := readExecutionResourceByIdentityTx(
			ctx, tx, activity.ActivityID, spec.ResourceType, normalizeExecutionResourceKey(spec.ResourceKey),
		)
		if readErr != nil {
			return GuardedExecution{}, readErr
		}
		if exists {
			if resource.Status == WriteIntentReleased {
				return GuardedExecution{}, fmt.Errorf("%w: cannot reactivate released semantic resource %s/%s", ErrInvalidTransition, spec.ResourceType, spec.ResourceKey)
			}
			result, updateErr := tx.ExecContext(ctx, `
				UPDATE execution_resource_intents
				SET resource_key = ?, mode = ?, confidence = ?, status = ?, reason = ?,
				    revision = revision + 1, updated_at_ms = ?, released_at_ms = 0
				WHERE resource_intent_id = ? AND revision = ? AND status IN (?, ?)
			`, spec.ResourceKey, spec.Mode, IntentConfirmed, WriteIntentActive, spec.Reason,
				nowMS, resource.ResourceIntentID, resource.Revision,
				WriteIntentActive, WriteIntentRecovery)
			if updateErr != nil {
				return GuardedExecution{}, fmt.Errorf("promote guarded semantic resource: %w", updateErr)
			}
			if err := requireOneCASRow(result, ErrRevisionConflict, "promote guarded semantic resource"); err != nil {
				return GuardedExecution{}, err
			}
		} else {
			resource, createErr := newExecutionResourceIntent(activity, spec, nowMS)
			if createErr != nil {
				return GuardedExecution{}, createErr
			}
			resource.Confidence = IntentConfirmed
			if err := insertExecutionResourceIntentTx(ctx, tx, resource); err != nil {
				return GuardedExecution{}, err
			}
		}
	}

	workResult, err := tx.ExecContext(ctx, `
		UPDATE work_items
		SET status = ?, revision = revision + 1, updated_at_ms = ?, heartbeat_at_ms = ?
		WHERE work_id = ? AND revision = ? AND fence = ?
	`, WorkActive, nowMS, nowMS, work.WorkID, work.Revision, work.Fence)
	if err != nil {
		return GuardedExecution{}, fmt.Errorf("update guarded Work: %w", err)
	}
	if err := requireOneCASRow(workResult, ErrRevisionConflict, "guard execution Work"); err != nil {
		return GuardedExecution{}, err
	}
	work.Status = WorkActive
	work.Revision++
	work.HeartbeatAtMS = nowMS
	work.UpdatedAtMS = nowMS
	if activity.Phase == ExecutionPhaseAnnounced || activity.Phase == ExecutionPhaseBlocked {
		if err := setExecutionActivityPhaseTx(
			ctx, tx, &activity, ExecutionPhaseSelected,
			"execution.selected", "task selected before atomic claim", nowMS,
		); err != nil {
			return GuardedExecution{}, err
		}
	}
	if activity.Phase == ExecutionPhaseSelected {
		if err := setExecutionActivityPhaseTx(
			ctx, tx, &activity, ExecutionPhaseClaimed,
			"execution.claimed", "file and semantic authority claimed atomically", nowMS,
		); err != nil {
			return GuardedExecution{}, err
		}
	}

	activityResult, err := tx.ExecContext(ctx, `
		UPDATE execution_activities
		SET phase = ?, baseline_json = ?, guarded_overview_revision = ?, guarded_overview_sha256 = ?,
		    revision = revision + 1, updated_at_ms = ?
		WHERE activity_id = ? AND revision = ?
	`, ExecutionPhaseExecuting, amendedBaseline, params.ExpectedCoordinationRevision, params.OverviewSHA256,
		nowMS, activity.ActivityID, activity.Revision)
	if err != nil {
		return GuardedExecution{}, fmt.Errorf("update guarded execution activity: %w", err)
	}
	if err := requireOneCASRow(activityResult, ErrRevisionConflict, "guard execution activity"); err != nil {
		return GuardedExecution{}, err
	}
	activity.Phase = ExecutionPhaseExecuting
	activity.BaselineJSON = amendedBaseline
	activity.GuardedOverviewRevision = params.ExpectedCoordinationRevision
	activity.GuardedOverviewSHA256 = params.OverviewSHA256
	activity.Revision++
	activity.UpdatedAtMS = nowMS
	workEvent := "work.execution_guarded"
	activityEvent := "execution.guarded"
	if len(amendments) > 0 {
		workEvent = "work.execution_scope_amended"
		activityEvent = "execution.scope_amended"
	}
	if err := appendWorkEventTx(ctx, tx, work, workEvent, params.Reason); err != nil {
		return GuardedExecution{}, err
	}
	if err := appendExecutionActivityEventTx(ctx, tx, activity, activityEvent, params.Reason); err != nil {
		return GuardedExecution{}, err
	}
	coordinationRevision, err := coordinationRevision(ctx, tx)
	if err != nil {
		return GuardedExecution{}, err
	}
	claimedWrites, err := readWorkIntentsTx(ctx, tx, work.WorkID)
	if err != nil {
		return GuardedExecution{}, err
	}
	claimedResources, err := readExecutionResourceIntents(ctx, tx, activity.ActivityID)
	if err != nil {
		return GuardedExecution{}, err
	}
	if err := tx.Commit(); err != nil {
		return GuardedExecution{}, fmt.Errorf("commit execution guard: %w", err)
	}
	return GuardedExecution{
		ExecutionRegistration: ExecutionRegistration{
			Activity: activity, Work: work, WriteIntents: claimedWrites, Resources: claimedResources,
		},
		CoordinationRevision: coordinationRevision,
	}, nil
}

func (store *Store) CheckpointExecution(
	ctx context.Context,
	params CheckpointExecutionParams,
) (CheckpointedExecution, error) {
	params.ActivityID = strings.TrimSpace(params.ActivityID)
	params.NextAction = strings.TrimSpace(params.NextAction)
	params.Reason = strings.TrimSpace(params.Reason)
	if params.ActivityID == "" || params.ExpectedWorkRevision < 1 || params.Fence < 1 ||
		!validExecutionPhase(params.TargetPhase) {
		return CheckpointedExecution{}, fmt.Errorf(
			"%w: activity_id, expected work revision, fence, and target phase are required",
			ErrInvalidArgument,
		)
	}
	if params.TargetPhase == ExecutionPhaseCompleted || params.TargetPhase == ExecutionPhaseAbandoned ||
		params.TargetPhase == ExecutionPhaseInterrupted {
		return CheckpointedExecution{}, fmt.Errorf(
			"%w: phase %q is owned by complete, abandon, or interruption handling",
			ErrInvalidTransition,
			params.TargetPhase,
		)
	}
	if params.NextAction == "" {
		return CheckpointedExecution{}, fmt.Errorf("%w: next_action is required", ErrInvalidArgument)
	}
	if params.Reason == "" {
		params.Reason = "execution checkpoint " + string(params.TargetPhase)
	}
	if params.LeaseUntil.IsZero() || !params.LeaseUntil.After(time.Now().UTC()) {
		return CheckpointedExecution{}, fmt.Errorf("%w: lease_until must be in the future", ErrInvalidArgument)
	}
	observed, observedJSON, err := normalizeWorkPathsJSON(params.ObservedPaths)
	if err != nil {
		return CheckpointedExecution{}, err
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return CheckpointedExecution{}, fmt.Errorf("begin execution checkpoint: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	activity, err := readExecutionActivity(ctx, tx, params.ActivityID)
	if err != nil {
		return CheckpointedExecution{}, err
	}
	work, err := readWorkTx(ctx, tx, activity.WorkID)
	if err != nil {
		return CheckpointedExecution{}, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	if err := requireWorkAuthority(work, params.ExpectedWorkRevision, params.Fence, nowMS); err != nil {
		return CheckpointedExecution{}, err
	}
	if work.Status != WorkActive {
		return CheckpointedExecution{}, fmt.Errorf("%w: execution checkpoint requires active Work", ErrInvalidTransition)
	}
	if params.LeaseUntil.UTC().UnixMilli() <= work.LeaseUntilMS {
		return CheckpointedExecution{}, fmt.Errorf("%w: checkpoint must extend the work lease", ErrInvalidArgument)
	}
	if !canCheckpointExecutionPhase(activity.Phase, params.TargetPhase) {
		return CheckpointedExecution{}, fmt.Errorf(
			"%w: execution checkpoint cannot move %s -> %s",
			ErrInvalidTransition,
			activity.Phase,
			params.TargetPhase,
		)
	}
	if (params.TargetPhase == ExecutionPhaseClaimed || params.TargetPhase == ExecutionPhaseExecuting) && !hasExecutionGuard(activity) {
		return CheckpointedExecution{}, fmt.Errorf("%w: checkpoint cannot acquire execution authority", ErrExecutionGuardRequired)
	}
	workResult, err := tx.ExecContext(ctx, `
		UPDATE work_items
		SET next_action = ?, observed_paths_json = ?, lease_until_ms = ?, heartbeat_at_ms = ?,
		    last_reason = ?, revision = revision + 1, updated_at_ms = ?
		WHERE work_id = ? AND revision = ? AND fence = ? AND status = ?
	`, params.NextAction, observedJSON, params.LeaseUntil.UTC().UnixMilli(), nowMS,
		params.Reason, nowMS, work.WorkID, work.Revision, work.Fence, WorkActive)
	if err != nil {
		return CheckpointedExecution{}, fmt.Errorf("checkpoint execution Work: %w", err)
	}
	if err := requireOneCASRow(workResult, ErrRevisionConflict, "checkpoint execution Work"); err != nil {
		return CheckpointedExecution{}, err
	}
	work.NextAction = params.NextAction
	work.ObservedPaths = observed
	work.ObservedPathsJSON = observedJSON
	work.LeaseUntilMS = params.LeaseUntil.UTC().UnixMilli()
	work.HeartbeatAtMS = nowMS
	work.LastReason = params.Reason
	work.Revision++
	work.UpdatedAtMS = nowMS
	activityResult, err := tx.ExecContext(ctx, `
		UPDATE execution_activities
		SET phase = ?, revision = revision + 1, updated_at_ms = ?
		WHERE activity_id = ? AND revision = ?
	`, params.TargetPhase, nowMS, activity.ActivityID, activity.Revision)
	if err != nil {
		return CheckpointedExecution{}, fmt.Errorf("checkpoint execution activity: %w", err)
	}
	if err := requireOneCASRow(activityResult, ErrRevisionConflict, "checkpoint execution activity"); err != nil {
		return CheckpointedExecution{}, err
	}
	activity.Phase = params.TargetPhase
	activity.Revision++
	activity.UpdatedAtMS = nowMS
	if err := appendWorkEventTx(ctx, tx, work, "work.execution_checkpointed", params.Reason); err != nil {
		return CheckpointedExecution{}, err
	}
	if err := appendExecutionActivityEventTx(ctx, tx, activity, "execution.checkpointed", params.Reason); err != nil {
		return CheckpointedExecution{}, err
	}
	coordinationRevision, err := coordinationRevision(ctx, tx)
	if err != nil {
		return CheckpointedExecution{}, err
	}
	writes, err := readWorkIntentsTx(ctx, tx, work.WorkID)
	if err != nil {
		return CheckpointedExecution{}, err
	}
	resources, err := readExecutionResourceIntents(ctx, tx, activity.ActivityID)
	if err != nil {
		return CheckpointedExecution{}, err
	}
	if err := tx.Commit(); err != nil {
		return CheckpointedExecution{}, fmt.Errorf("commit execution checkpoint: %w", err)
	}
	return CheckpointedExecution{
		ExecutionRegistration: ExecutionRegistration{
			Activity: activity, Work: work, WriteIntents: writes, Resources: resources,
		},
		CoordinationRevision: coordinationRevision,
	}, nil
}

func (store *Store) CompleteExecution(ctx context.Context, params CompleteExecutionParams) (CompletedExecution, error) {
	params.ActivityID = strings.TrimSpace(params.ActivityID)
	params.Reason = strings.TrimSpace(params.Reason)
	if params.ActivityID == "" || params.ExpectedWorkRevision < 1 || params.Fence < 1 || params.Reason == "" {
		return CompletedExecution{}, fmt.Errorf("%w: activity_id, expected revision, fence, and reason are required", ErrInvalidArgument)
	}
	changedPaths, observedJSON, err := normalizeWorkPathsJSON(params.ChangedPaths)
	if err != nil {
		return CompletedExecution{}, err
	}
	validationJSON, err := normalizeExecutionValidationJSON(params.ValidationJSON)
	if err != nil {
		return CompletedExecution{}, err
	}
	controlPlaneFiles, err := normalizeExecutionFileDigestExpectations(params.ControlPlaneFiles)
	if err != nil {
		return CompletedExecution{}, err
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return CompletedExecution{}, fmt.Errorf("begin execution completion: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	activity, err := readExecutionActivity(ctx, tx, params.ActivityID)
	if err != nil {
		return CompletedExecution{}, err
	}
	work, err := readWorkTx(ctx, tx, activity.WorkID)
	if err != nil {
		return CompletedExecution{}, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	if err := requireWorkAuthority(work, params.ExpectedWorkRevision, params.Fence, nowMS); err != nil {
		return CompletedExecution{}, err
	}
	if work.Status != WorkActive || (activity.Phase != ExecutionPhaseExecuting && activity.Phase != ExecutionPhaseValidating) {
		return CompletedExecution{}, fmt.Errorf("%w: execution must be active and executing or validating before completion", ErrInvalidTransition)
	}
	if !hasExecutionGuard(activity) {
		return CompletedExecution{}, fmt.Errorf("%w: execution completion requires a recorded guard", ErrExecutionGuardRequired)
	}
	if err := requireExecutionScopeAmendmentReview(activity, work, validationJSON); err != nil {
		return CompletedExecution{}, err
	}
	if err := verifyExecutionPacketScope(activity, changedPaths); err != nil {
		return CompletedExecution{}, err
	}
	writes, err := readWorkIntentsTx(ctx, tx, work.WorkID)
	if err != nil {
		return CompletedExecution{}, err
	}
	unclaimed := executionUnclaimedChangedPaths(changedPaths, writes)
	if len(unclaimed) != 0 {
		return CompletedExecution{}, &ExecutionScopeAuditError{UnclaimedPaths: unclaimed}
	}
	if err := verifyExecutionFileDigestExpectations(work.WorkspaceRoot, controlPlaneFiles); err != nil {
		return CompletedExecution{}, err
	}
	resources, err := readExecutionResourceIntents(ctx, tx, activity.ActivityID)
	if err != nil {
		return CompletedExecution{}, err
	}
	if activity.Phase == ExecutionPhaseExecuting {
		if err := setExecutionActivityPhaseTx(
			ctx, tx, &activity, ExecutionPhaseValidating,
			"execution.validating", "passing validation evidence accepted for completion audit", nowMS,
		); err != nil {
			return CompletedExecution{}, err
		}
	}
	completionSHA256, err := executionCompletionSHA256(activity, work, changedPaths, controlPlaneFiles, validationJSON, params.Reason)
	if err != nil {
		return CompletedExecution{}, err
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE write_intents
		SET status = ?, revision = revision + 1, updated_at_ms = ?, released_at_ms = ?
		WHERE work_id = ? AND status IN (?, ?)
	`, WriteIntentReleased, nowMS, nowMS, work.WorkID, WriteIntentActive, WriteIntentRecovery); err != nil {
		return CompletedExecution{}, fmt.Errorf("release completed write intents: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `
		UPDATE execution_resource_intents
		SET status = ?, revision = revision + 1, updated_at_ms = ?, released_at_ms = ?
		WHERE activity_id = ? AND status IN (?, ?)
	`, WriteIntentReleased, nowMS, nowMS, activity.ActivityID,
		WriteIntentActive, WriteIntentRecovery); err != nil {
		return CompletedExecution{}, fmt.Errorf("release completed semantic resources: %w", err)
	}
	workResult, err := tx.ExecContext(ctx, `
		UPDATE work_items
		SET status = ?, next_action = '', last_reason = ?, observed_paths_json = ?,
		    revision = revision + 1, updated_at_ms = ?
		WHERE work_id = ? AND revision = ? AND fence = ?
	`, WorkCompleted, params.Reason, observedJSON, nowMS,
		work.WorkID, work.Revision, work.Fence)
	if err != nil {
		return CompletedExecution{}, fmt.Errorf("complete execution Work: %w", err)
	}
	if err := requireOneCASRow(workResult, ErrRevisionConflict, "complete execution Work"); err != nil {
		return CompletedExecution{}, err
	}
	work.Status = WorkCompleted
	work.NextAction = ""
	work.LastReason = params.Reason
	work.ObservedPaths = changedPaths
	work.ObservedPathsJSON = observedJSON
	work.Revision++
	work.UpdatedAtMS = nowMS
	activityResult, err := tx.ExecContext(ctx, `
		UPDATE execution_activities
		SET phase = ?, validation_json = ?, completion_sha256 = ?,
		    revision = revision + 1, completed_at_ms = ?, updated_at_ms = ?
		WHERE activity_id = ? AND revision = ?
	`, ExecutionPhaseCompleted, validationJSON, completionSHA256,
		nowMS, nowMS, activity.ActivityID, activity.Revision)
	if err != nil {
		return CompletedExecution{}, fmt.Errorf("complete execution activity: %w", err)
	}
	if err := requireOneCASRow(activityResult, ErrRevisionConflict, "complete execution activity"); err != nil {
		return CompletedExecution{}, err
	}
	activity.Phase = ExecutionPhaseCompleted
	activity.ValidationJSON = validationJSON
	activity.CompletionSHA256 = completionSHA256
	activity.Revision++
	activity.CompletedAtMS = nowMS
	activity.UpdatedAtMS = nowMS
	if err := appendWorkEventTx(ctx, tx, work, "work.execution_completed", params.Reason); err != nil {
		return CompletedExecution{}, err
	}
	if err := appendExecutionActivityEventTx(ctx, tx, activity, "execution.completed", params.Reason); err != nil {
		return CompletedExecution{}, err
	}
	coordinationRevision, err := coordinationRevision(ctx, tx)
	if err != nil {
		return CompletedExecution{}, err
	}
	for index := range writes {
		if writes[index].Status == WriteIntentActive || writes[index].Status == WriteIntentRecovery {
			writes[index].Status = WriteIntentReleased
			writes[index].Revision++
			writes[index].UpdatedAtMS = nowMS
			writes[index].ReleasedAtMS = nowMS
		}
	}
	for index := range resources {
		if resources[index].Status == WriteIntentActive || resources[index].Status == WriteIntentRecovery {
			resources[index].Status = WriteIntentReleased
			resources[index].Revision++
			resources[index].UpdatedAtMS = nowMS
			resources[index].ReleasedAtMS = nowMS
		}
	}
	if err := tx.Commit(); err != nil {
		return CompletedExecution{}, fmt.Errorf("commit execution completion: %w", err)
	}
	return CompletedExecution{
		ExecutionRegistration: ExecutionRegistration{
			Activity: activity, Work: work, WriteIntents: writes, Resources: resources,
		},
		ChangedPaths: changedPaths, CoordinationRevision: coordinationRevision,
	}, nil
}

func normalizeExecutionFileDigestExpectations(values []ExecutionFileDigestExpectation) ([]ExecutionFileDigestExpectation, error) {
	result := make([]ExecutionFileDigestExpectation, 0, len(values))
	seen := make(map[string]struct{}, len(values))
	for _, value := range values {
		pathValue, pathKey, err := normalizeWorkPath(value.Path, runtime.GOOS == "windows")
		if err != nil {
			return nil, err
		}
		digest := strings.ToLower(strings.TrimSpace(value.SHA256))
		if digest != "missing" && (len(digest) != 64 || strings.IndexFunc(digest, func(char rune) bool {
			return (char < '0' || char > '9') && (char < 'a' || char > 'f')
		}) >= 0) {
			return nil, fmt.Errorf("%w: control-plane file %q requires a lower-case SHA-256 or missing", ErrInvalidArgument, pathValue)
		}
		if _, exists := seen[pathKey]; exists {
			return nil, fmt.Errorf("%w: duplicate control-plane file expectation %q", ErrInvalidArgument, pathValue)
		}
		seen[pathKey] = struct{}{}
		result = append(result, ExecutionFileDigestExpectation{Path: pathValue, SHA256: digest})
	}
	sort.Slice(result, func(left, right int) bool { return result[left].Path < result[right].Path })
	return result, nil
}

func verifyExecutionFileDigestExpectations(workspaceRoot string, values []ExecutionFileDigestExpectation) error {
	drifted := make([]string, 0)
	for _, value := range values {
		current, err := workspacePathDigest(workspaceRoot, value.Path)
		if err != nil {
			return fmt.Errorf("inspect workflow control-plane file %q: %w", value.Path, err)
		}
		if current != value.SHA256 {
			drifted = append(drifted, value.Path)
		}
	}
	if len(drifted) > 0 {
		return &ExecutionControlPlaneDriftError{Paths: drifted}
	}
	return nil
}

func findExecutionTaskConflictTx(
	ctx context.Context,
	tx *sql.Tx,
	activity ExecutionActivity,
	work WorkItem,
	nowMS int64,
) (ExecutionActivity, bool, error) {
	row := tx.QueryRowContext(ctx, `
		SELECT a.activity_id, a.work_id, a.workflow, a.subject_id, a.item_id,
		       a.task_ref, a.source_ref, a.title, a.phase, a.baseline_json,
		       a.guarded_overview_revision, a.guarded_overview_sha256,
		       a.validation_json, a.completion_sha256, a.revision,
		       a.completed_at_ms, a.created_at_ms, a.updated_at_ms
		FROM execution_activities AS a
		JOIN work_items AS w ON w.work_id = a.work_id
		WHERE lower(a.task_ref) = lower(?)
		  AND a.activity_id <> ?
		  AND a.phase NOT IN (?, ?)
		  AND (
		        (w.status IN (?, ?) AND w.lease_until_ms > ?)
		        OR (w.status = ? AND w.recovery_hold = 1)
		      )
		ORDER BY a.created_at_ms, a.activity_id
		LIMIT 1
	`, activity.TaskRef, activity.ActivityID,
		ExecutionPhaseCompleted, ExecutionPhaseAbandoned,
		WorkActive, WorkBlocked, nowMS, WorkInterrupted)
	conflict, err := scanExecutionActivity(row)
	if errors.Is(err, sql.ErrNoRows) {
		return ExecutionActivity{}, false, nil
	}
	if err != nil {
		return ExecutionActivity{}, false, fmt.Errorf("inspect duplicate execution task for work %q: %w", work.WorkID, err)
	}
	return conflict, true, nil
}

func findExecutionResourceConflictsTx(
	ctx context.Context,
	tx *sql.Tx,
	activityID string,
	requested []ExecutionResourceIntentSpec,
) ([]ExecutionResourceConflict, error) {
	conflicts := make([]ExecutionResourceConflict, 0)
	for _, spec := range requested {
		query := `
			SELECT r.resource_type, r.resource_key, r.activity_id, r.work_id, r.mode
			FROM execution_resource_intents AS r
			JOIN execution_activities AS a ON a.activity_id = r.activity_id
			JOIN work_items AS w ON w.work_id = r.work_id
			WHERE r.activity_id <> ?
			  AND r.resource_type = ?
			  AND r.resource_key_normalized = ?
			  AND r.confidence = ?
			  AND r.status IN (?, ?)
			  AND a.phase NOT IN (?, ?)`
		args := []any{
			activityID, spec.ResourceType, normalizeExecutionResourceKey(spec.ResourceKey),
			IntentConfirmed, WriteIntentActive, WriteIntentRecovery,
			ExecutionPhaseCompleted, ExecutionPhaseAbandoned,
		}
		if spec.Mode == ResourceClaimShared {
			query += ` AND r.mode = ?`
			args = append(args, ResourceClaimExclusive)
		}
		query += ` ORDER BY r.created_at_ms, r.resource_intent_id LIMIT 1`
		var conflict ExecutionResourceConflict
		err := tx.QueryRowContext(ctx, query, args...).Scan(
			&conflict.ResourceType, &conflict.ResourceKey,
			&conflict.OwnerActivityID, &conflict.OwnerWorkID, &conflict.OwnerMode,
		)
		if errors.Is(err, sql.ErrNoRows) {
			continue
		}
		if err != nil {
			return nil, fmt.Errorf("inspect semantic resource conflict: %w", err)
		}
		conflicts = append(conflicts, conflict)
	}
	return conflicts, nil
}

func readExecutionResourceByIdentityTx(
	ctx context.Context,
	tx *sql.Tx,
	activityID string,
	resourceType ResourceType,
	resourceKeyNormalized string,
) (ExecutionResourceIntent, bool, error) {
	resource, err := scanExecutionResourceIntent(tx.QueryRowContext(ctx, `
		SELECT resource_intent_id, activity_id, work_id, resource_type, resource_key,
		       resource_key_normalized, mode, confidence, status, reason, revision,
		       created_at_ms, updated_at_ms, released_at_ms
		FROM execution_resource_intents
		WHERE activity_id = ? AND resource_type = ? AND resource_key_normalized = ?
	`, activityID, resourceType, resourceKeyNormalized))
	if errors.Is(err, sql.ErrNoRows) {
		return ExecutionResourceIntent{}, false, nil
	}
	if err != nil {
		return ExecutionResourceIntent{}, false, fmt.Errorf("read execution resource intent: %w", err)
	}
	return resource, true, nil
}

func normalizeExecutionValidationJSON(raw string) (string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", fmt.Errorf("%w: validation_json is required", ErrExecutionCompletionGate)
	}
	var evidence []map[string]any
	if err := json.Unmarshal([]byte(raw), &evidence); err != nil || len(evidence) == 0 {
		return "", fmt.Errorf("%w: validation_json must be a non-empty array", ErrExecutionCompletionGate)
	}
	passing := false
	for _, item := range evidence {
		result := strings.ToLower(strings.TrimSpace(fmt.Sprint(item["result"])))
		if result == "passed" || result == "pass" || result == "ok" {
			passing = true
		}
	}
	if !passing {
		return "", fmt.Errorf("%w: validation_json contains no passing evidence", ErrExecutionCompletionGate)
	}
	canonical, err := json.Marshal(evidence)
	if err != nil {
		return "", fmt.Errorf("encode execution validation evidence: %w", err)
	}
	return string(canonical), nil
}

func executionUnclaimedChangedPaths(changedPaths []string, intents []WriteIntent) []string {
	confirmed := make([]string, 0, len(intents))
	for _, intent := range intents {
		if intent.Confidence == IntentConfirmed &&
			(intent.Status == WriteIntentActive || intent.Status == WriteIntentRecovery) {
			confirmed = append(confirmed, intent.PathKey)
		}
	}
	unclaimed := make([]string, 0)
	for _, changed := range changedPaths {
		_, changedKey, err := normalizeWorkPath(changed, runtime.GOOS == "windows")
		if err != nil {
			unclaimed = append(unclaimed, changed)
			continue
		}
		covered := false
		for _, ownerKey := range confirmed {
			if changedKey == ownerKey || strings.HasPrefix(changedKey, strings.TrimSuffix(ownerKey, "/")+"/") {
				covered = true
				break
			}
		}
		if !covered {
			unclaimed = append(unclaimed, changed)
		}
	}
	sort.Strings(unclaimed)
	return unclaimed
}

func executionCompletionSHA256(
	activity ExecutionActivity,
	work WorkItem,
	changedPaths []string,
	controlPlaneFiles []ExecutionFileDigestExpectation,
	validationJSON string,
	reason string,
) (string, error) {
	payload, err := json.Marshal(map[string]any{
		"activity_id":               activity.ActivityID,
		"activity_revision":         activity.Revision,
		"work_id":                   work.WorkID,
		"work_revision":             work.Revision,
		"fence":                     work.Fence,
		"task_ref":                  activity.TaskRef,
		"guarded_overview_revision": activity.GuardedOverviewRevision,
		"guarded_overview_sha256":   activity.GuardedOverviewSHA256,
		"changed_paths":             changedPaths,
		"control_plane_files":       controlPlaneFiles,
		"validation_json":           json.RawMessage(validationJSON),
		"reason":                    strings.TrimSpace(reason),
	})
	if err != nil {
		return "", fmt.Errorf("encode execution completion receipt: %w", err)
	}
	digest := sha256.Sum256(payload)
	return hex.EncodeToString(digest[:]), nil
}

func (store *Store) AnnounceExecution(ctx context.Context, params AnnounceExecutionParams) (ExecutionRegistration, error) {
	normalized, workParams, writeSpecs, resourceSpecs, err := normalizeAnnounceExecutionParams(params)
	if err != nil {
		return ExecutionRegistration{}, err
	}
	nowMS := time.Now().UTC().UnixMilli()
	work := WorkItem{
		WorkID:            workParams.WorkID,
		ParentWorkID:      workParams.ParentWorkID,
		RunID:             workParams.RunID,
		TaskRef:           workParams.TaskRef,
		Summary:           workParams.Summary,
		AgentID:           workParams.AgentID,
		AdapterID:         workParams.AdapterID,
		WorkspaceRoot:     workParams.WorkspaceRoot,
		BaseCommit:        workParams.BaseCommit,
		Status:            WorkActive,
		NextAction:        workParams.NextAction,
		Fence:             1,
		Revision:          1,
		LeaseUntilMS:      workParams.LeaseUntil.UTC().UnixMilli(),
		HeartbeatAtMS:     nowMS,
		ObservedPaths:     []string{},
		ObservedPathsJSON: "[]",
		CreatedAtMS:       nowMS,
		UpdatedAtMS:       nowMS,
	}
	activity := ExecutionActivity{
		ActivityID:     normalized.ActivityID,
		WorkID:         work.WorkID,
		Workflow:       normalized.Workflow,
		SubjectID:      normalized.SubjectID,
		ItemID:         normalized.ItemID,
		TaskRef:        work.TaskRef,
		SourceRef:      normalized.SourceRef,
		Title:          work.Summary,
		Phase:          ExecutionPhaseAnnounced,
		BaselineJSON:   normalized.BaselineJSON,
		ValidationJSON: "[]",
		Revision:       1,
		CreatedAtMS:    nowMS,
		UpdatedAtMS:    nowMS,
	}

	tx, err := store.db.BeginTx(ctx, nil)
	if err != nil {
		return ExecutionRegistration{}, fmt.Errorf("begin execution announcement: %w", err)
	}
	defer func() { _ = tx.Rollback() }()
	if conflicts, conflictErr := findWorkIntentConflictsTx(ctx, tx, work.WorkID, writeSpecs); conflictErr != nil {
		return ExecutionRegistration{}, conflictErr
	} else if len(conflicts) != 0 {
		return ExecutionRegistration{}, &WorkIntentConflictError{Conflicts: conflicts}
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
			return ExecutionRegistration{}, fmt.Errorf("%w: work item %q", ErrAlreadyExists, work.WorkID)
		}
		return ExecutionRegistration{}, fmt.Errorf("insert execution Work %q: %w", work.WorkID, err)
	}
	writes := make([]WriteIntent, 0, len(writeSpecs))
	for _, spec := range writeSpecs {
		intentID, idErr := newWorkBoardID("intent")
		if idErr != nil {
			return ExecutionRegistration{}, idErr
		}
		intent := WriteIntent{
			IntentID: intentID, WorkID: work.WorkID, Path: spec.Path, PathKey: spec.pathKey,
			Operation: spec.Operation, Reason: spec.Reason, Confidence: spec.Confidence,
			Status: WriteIntentActive, Revision: 1, CreatedAtMS: nowMS, UpdatedAtMS: nowMS,
		}
		if err := insertWriteIntentTx(ctx, tx, intent); err != nil {
			return ExecutionRegistration{}, err
		}
		writes = append(writes, intent)
	}
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO execution_activities (
			activity_id, work_id, workflow, subject_id, item_id, task_ref, source_ref,
			title, phase, baseline_json, guarded_overview_revision,
			guarded_overview_sha256, validation_json, completion_sha256,
			revision, completed_at_ms, created_at_ms, updated_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '', '[]', '', 1, 0, ?, ?)
	`, activity.ActivityID, activity.WorkID, activity.Workflow, activity.SubjectID,
		activity.ItemID, activity.TaskRef, activity.SourceRef, activity.Title,
		activity.Phase, activity.BaselineJSON, activity.CreatedAtMS, activity.UpdatedAtMS); err != nil {
		if isUniqueConstraintError(err) {
			return ExecutionRegistration{}, fmt.Errorf("%w: execution activity %q", ErrAlreadyExists, activity.ActivityID)
		}
		return ExecutionRegistration{}, fmt.Errorf("insert execution activity %q: %w", activity.ActivityID, err)
	}
	resources := make([]ExecutionResourceIntent, 0, len(resourceSpecs))
	for _, spec := range resourceSpecs {
		resource, insertErr := newExecutionResourceIntent(activity, spec, nowMS)
		if insertErr != nil {
			return ExecutionRegistration{}, insertErr
		}
		if err := insertExecutionResourceIntentTx(ctx, tx, resource); err != nil {
			return ExecutionRegistration{}, err
		}
		resources = append(resources, resource)
	}
	if err := appendWorkEventTx(ctx, tx, work, "work.created", "execution activity announced"); err != nil {
		return ExecutionRegistration{}, err
	}
	if err := appendExecutionActivityEventTx(ctx, tx, activity, "execution.announced", "execution activity announced"); err != nil {
		return ExecutionRegistration{}, err
	}
	if err := tx.Commit(); err != nil {
		return ExecutionRegistration{}, fmt.Errorf("commit execution announcement: %w", err)
	}
	return ExecutionRegistration{Activity: activity, Work: work, WriteIntents: writes, Resources: resources}, nil
}

func (store *Store) GetExecutionActivity(ctx context.Context, activityID string) (ExecutionRegistration, error) {
	activity, err := readExecutionActivity(ctx, store.db, activityID)
	if err != nil {
		return ExecutionRegistration{}, err
	}
	work, writes, err := getWork(ctx, store.db, activity.WorkID)
	if err != nil {
		return ExecutionRegistration{}, err
	}
	resources, err := readExecutionResourceIntents(ctx, store.db, activity.ActivityID)
	if err != nil {
		return ExecutionRegistration{}, err
	}
	return ExecutionRegistration{Activity: activity, Work: work, WriteIntents: writes, Resources: resources}, nil
}

func (view *View) GetExecutionActivity(ctx context.Context, activityID string) (ExecutionRegistration, error) {
	if strings.TrimSpace(activityID) == "" {
		return ExecutionRegistration{}, fmt.Errorf("%w: activity_id is required", ErrInvalidArgument)
	}
	if !view.hasExecutionActivities {
		return ExecutionRegistration{}, fmt.Errorf("%w: execution activity %q", ErrNotFound, activityID)
	}
	activity, err := readExecutionActivity(ctx, view.db, activityID)
	if err != nil {
		return ExecutionRegistration{}, err
	}
	work, writes, err := getWork(ctx, view.db, activity.WorkID)
	if err != nil {
		return ExecutionRegistration{}, err
	}
	resources, err := readExecutionResourceIntents(ctx, view.db, activity.ActivityID)
	if err != nil {
		return ExecutionRegistration{}, err
	}
	return ExecutionRegistration{Activity: activity, Work: work, WriteIntents: writes, Resources: resources}, nil
}

func (store *Store) ListExecutionActivities(ctx context.Context, params ListExecutionActivitiesParams) ([]ExecutionActivity, error) {
	return listExecutionActivities(ctx, store.db, params)
}

func (view *View) ListExecutionActivities(ctx context.Context, params ListExecutionActivitiesParams) ([]ExecutionActivity, error) {
	if !view.hasExecutionActivities {
		for _, phase := range params.Phases {
			if !validExecutionPhase(phase) {
				return nil, fmt.Errorf("%w: unsupported execution phase %q", ErrInvalidArgument, phase)
			}
		}
		return []ExecutionActivity{}, nil
	}
	return listExecutionActivities(ctx, view.db, params)
}

func (store *Store) CoordinationRevision(ctx context.Context) (int64, error) {
	return coordinationRevision(ctx, store.db)
}

func (view *View) CoordinationRevision(ctx context.Context) (int64, error) {
	return coordinationRevision(ctx, view.db)
}

func (store *Store) ListCoordinationChanges(ctx context.Context, sinceRevision int64, limit int) ([]Event, error) {
	return listCoordinationChanges(ctx, store.db, sinceRevision, limit)
}

func (view *View) ListCoordinationChanges(ctx context.Context, sinceRevision int64, limit int) ([]Event, error) {
	return listCoordinationChanges(ctx, view.db, sinceRevision, limit)
}

func listCoordinationChanges(ctx context.Context, querier workRowsQuerier, sinceRevision int64, limit int) ([]Event, error) {
	if sinceRevision < 0 {
		return nil, fmt.Errorf("%w: since revision cannot be negative", ErrInvalidArgument)
	}
	if limit <= 0 || limit > 1000 {
		limit = 100
	}
	rows, err := querier.QueryContext(ctx, `
		SELECT event_id, aggregate_type, aggregate_id, aggregate_revision,
		       event_type, reason, payload_json, created_at_ms
		FROM events
		WHERE event_id > ? AND aggregate_type IN ('work', 'execution_activity')
		ORDER BY event_id
		LIMIT ?
	`, sinceRevision, limit)
	if err != nil {
		return nil, fmt.Errorf("list coordination changes: %w", err)
	}
	defer rows.Close()
	changes := make([]Event, 0)
	for rows.Next() {
		var event Event
		if err := rows.Scan(
			&event.EventID, &event.AggregateType, &event.AggregateID,
			&event.AggregateRevision, &event.EventType, &event.Reason,
			&event.PayloadJSON, &event.CreatedAtMS,
		); err != nil {
			return nil, fmt.Errorf("scan coordination change: %w", err)
		}
		changes = append(changes, event)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate coordination changes: %w", err)
	}
	return changes, nil
}

func normalizeAnnounceExecutionParams(
	params AnnounceExecutionParams,
) (AnnounceExecutionParams, BeginWorkParams, []normalizedWriteIntentSpec, []ExecutionResourceIntentSpec, error) {
	params.ActivityID = strings.TrimSpace(params.ActivityID)
	if params.ActivityID == "" {
		activityID, err := newWorkBoardID("activity")
		if err != nil {
			return AnnounceExecutionParams{}, BeginWorkParams{}, nil, nil, err
		}
		params.ActivityID = activityID
	}
	params.WorkID = strings.TrimSpace(params.WorkID)
	if params.WorkID == "" {
		params.WorkID = params.ActivityID
	}
	params.SubjectID = strings.TrimSpace(params.SubjectID)
	params.ItemID = strings.TrimSpace(params.ItemID)
	params.SourceRef = strings.TrimSpace(params.SourceRef)
	params.TaskRef = strings.TrimSpace(params.TaskRef)
	params.BaselineJSON = strings.TrimSpace(params.BaselineJSON)
	if !validExecutionWorkflow(params.Workflow) || params.SubjectID == "" {
		return AnnounceExecutionParams{}, BeginWorkParams{}, nil, nil, fmt.Errorf("%w: workflow and subject_id are required", ErrInvalidArgument)
	}
	if params.TaskRef == "" {
		params.TaskRef = string(params.Workflow) + ":" + params.SubjectID
		if params.ItemID != "" {
			params.TaskRef += "#" + params.ItemID
		}
	}
	if params.BaselineJSON == "" {
		params.BaselineJSON = "{}"
	}
	var baseline map[string]any
	if err := json.Unmarshal([]byte(params.BaselineJSON), &baseline); err != nil || baseline == nil {
		return AnnounceExecutionParams{}, BeginWorkParams{}, nil, nil, fmt.Errorf("%w: baseline_json must be an object", ErrInvalidArgument)
	}
	canonicalBaseline, err := json.Marshal(baseline)
	if err != nil {
		return AnnounceExecutionParams{}, BeginWorkParams{}, nil, nil, fmt.Errorf("encode execution baseline: %w", err)
	}
	params.BaselineJSON = string(canonicalBaseline)
	if _, err := executionWorkerPacket(params.BaselineJSON); err != nil {
		return AnnounceExecutionParams{}, BeginWorkParams{}, nil, nil, err
	}
	workParams, writeSpecs, err := normalizeBeginWorkParams(BeginWorkParams{
		WorkID:        params.WorkID,
		ParentWorkID:  params.ParentWorkID,
		RunID:         params.RunID,
		TaskRef:       params.TaskRef,
		Summary:       params.Summary,
		AgentID:       params.AgentID,
		AdapterID:     params.AdapterID,
		WorkspaceRoot: params.WorkspaceRoot,
		BaseCommit:    params.BaseCommit,
		NextAction:    params.NextAction,
		LeaseUntil:    params.LeaseUntil,
		WriteIntents:  params.PlannedWriteIntents,
	})
	if err != nil {
		return AnnounceExecutionParams{}, BeginWorkParams{}, nil, nil, err
	}
	for _, spec := range writeSpecs {
		if spec.Confidence != IntentCandidate {
			return AnnounceExecutionParams{}, BeginWorkParams{}, nil, nil, fmt.Errorf("%w: announced write intents must be candidate scope", ErrInvalidArgument)
		}
	}
	resources, err := normalizeExecutionResourceSpecs(params.Resources, IntentCandidate)
	if err != nil {
		return AnnounceExecutionParams{}, BeginWorkParams{}, nil, nil, err
	}
	return params, workParams, writeSpecs, resources, nil
}

func normalizeExecutionResourceSpecs(
	raw []ExecutionResourceIntentSpec,
	defaultConfidence WriteIntentConfidence,
) ([]ExecutionResourceIntentSpec, error) {
	result := make([]ExecutionResourceIntentSpec, 0, len(raw))
	seen := make(map[string]struct{}, len(raw))
	for _, spec := range raw {
		spec.ResourceKey = strings.TrimSpace(spec.ResourceKey)
		spec.Reason = strings.TrimSpace(spec.Reason)
		if spec.Mode == "" {
			spec.Mode = ResourceClaimExclusive
		}
		if spec.Confidence == "" {
			spec.Confidence = defaultConfidence
		}
		if !validExecutionResourceType(spec.ResourceType) || spec.ResourceKey == "" {
			return nil, fmt.Errorf("%w: execution resource type and key are required", ErrInvalidArgument)
		}
		if spec.Mode != ResourceClaimShared && spec.Mode != ResourceClaimExclusive {
			return nil, fmt.Errorf("%w: unsupported execution resource mode %q", ErrInvalidArgument, spec.Mode)
		}
		if spec.Confidence != IntentCandidate && spec.Confidence != IntentConfirmed {
			return nil, fmt.Errorf("%w: unsupported execution resource confidence %q", ErrInvalidArgument, spec.Confidence)
		}
		identity := string(spec.ResourceType) + "\x00" + normalizeExecutionResourceKey(spec.ResourceKey)
		if _, exists := seen[identity]; exists {
			return nil, fmt.Errorf("%w: duplicate execution resource %s/%s", ErrInvalidArgument, spec.ResourceType, spec.ResourceKey)
		}
		seen[identity] = struct{}{}
		result = append(result, spec)
	}
	sort.Slice(result, func(i, j int) bool {
		left := string(result[i].ResourceType) + ":" + normalizeExecutionResourceKey(result[i].ResourceKey)
		right := string(result[j].ResourceType) + ":" + normalizeExecutionResourceKey(result[j].ResourceKey)
		return left < right
	})
	return result, nil
}

func validExecutionWorkflow(workflow ExecutionWorkflow) bool {
	switch workflow {
	case ExecutionWorkflowFast, ExecutionWorkflowDebug, ExecutionWorkflowImplement, ExecutionWorkflowQuick:
		return true
	default:
		return false
	}
}

func validExecutionResourceType(resourceType ResourceType) bool {
	switch resourceType {
	case ResourceFilesystem, ResourceTCPPort, ResourceDatabase, ResourceSchema,
		ResourceService, ResourceComposeProject, ResourceTemp, ResourceCache,
		ResourceExternalEffect, ResourceCapability, ResourceFeature, ResourceAPI,
		ResourceUISurface, ResourceConfig:
		return true
	default:
		return false
	}
}

func normalizeExecutionResourceKey(value string) string {
	return strings.ToLower(strings.Join(strings.Fields(strings.TrimSpace(value)), " "))
}

func newExecutionResourceIntent(
	activity ExecutionActivity,
	spec ExecutionResourceIntentSpec,
	nowMS int64,
) (ExecutionResourceIntent, error) {
	id, err := newWorkBoardID("resource")
	if err != nil {
		return ExecutionResourceIntent{}, err
	}
	return ExecutionResourceIntent{
		ResourceIntentID:      id,
		ActivityID:            activity.ActivityID,
		WorkID:                activity.WorkID,
		ResourceType:          spec.ResourceType,
		ResourceKey:           spec.ResourceKey,
		ResourceKeyNormalized: normalizeExecutionResourceKey(spec.ResourceKey),
		Mode:                  spec.Mode,
		Confidence:            spec.Confidence,
		Status:                WriteIntentActive,
		Reason:                spec.Reason,
		Revision:              1,
		CreatedAtMS:           nowMS,
		UpdatedAtMS:           nowMS,
	}, nil
}

func insertExecutionResourceIntentTx(ctx context.Context, tx *sql.Tx, resource ExecutionResourceIntent) error {
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO execution_resource_intents (
			resource_intent_id, activity_id, work_id, resource_type, resource_key,
			resource_key_normalized, mode, confidence, status, reason, revision,
			created_at_ms, updated_at_ms, released_at_ms
		) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	`, resource.ResourceIntentID, resource.ActivityID, resource.WorkID,
		resource.ResourceType, resource.ResourceKey, resource.ResourceKeyNormalized,
		resource.Mode, resource.Confidence, resource.Status, resource.Reason,
		resource.Revision, resource.CreatedAtMS, resource.UpdatedAtMS,
		resource.ReleasedAtMS); err != nil {
		if isUniqueConstraintError(err) {
			return fmt.Errorf("%w: execution resource %s/%s", ErrAlreadyExists, resource.ResourceType, resource.ResourceKey)
		}
		return fmt.Errorf("insert execution resource intent: %w", err)
	}
	return nil
}

const executionActivitySelectSQL = `
	SELECT activity_id, work_id, workflow, subject_id, item_id, task_ref, source_ref,
	       title, phase, baseline_json, guarded_overview_revision,
	       guarded_overview_sha256, validation_json, completion_sha256,
	       revision, completed_at_ms, created_at_ms, updated_at_ms
	FROM execution_activities`

func readExecutionActivity(ctx context.Context, querier rowQuerier, activityID string) (ExecutionActivity, error) {
	activityID = strings.TrimSpace(activityID)
	if activityID == "" {
		return ExecutionActivity{}, fmt.Errorf("%w: activity_id is required", ErrInvalidArgument)
	}
	activity, err := scanExecutionActivity(querier.QueryRowContext(ctx, executionActivitySelectSQL+" WHERE activity_id = ?", activityID))
	if errors.Is(err, sql.ErrNoRows) {
		return ExecutionActivity{}, fmt.Errorf("%w: execution activity %q", ErrNotFound, activityID)
	}
	if err != nil {
		return ExecutionActivity{}, fmt.Errorf("read execution activity %q: %w", activityID, err)
	}
	return activity, nil
}

func listExecutionActivities(
	ctx context.Context,
	querier workBoardQuerier,
	params ListExecutionActivitiesParams,
) ([]ExecutionActivity, error) {
	query := executionActivitySelectSQL
	args := make([]any, 0, len(params.Phases))
	if len(params.Phases) > 0 {
		placeholders := make([]string, 0, len(params.Phases))
		for _, phase := range params.Phases {
			if !validExecutionPhase(phase) {
				return nil, fmt.Errorf("%w: unsupported execution phase %q", ErrInvalidArgument, phase)
			}
			placeholders = append(placeholders, "?")
			args = append(args, phase)
		}
		query += " WHERE phase IN (" + strings.Join(placeholders, ",") + ")"
	}
	query += " ORDER BY updated_at_ms, activity_id"
	rows, err := querier.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("list execution activities: %w", err)
	}
	defer rows.Close()
	activities := make([]ExecutionActivity, 0)
	for rows.Next() {
		activity, scanErr := scanExecutionActivity(rows)
		if scanErr != nil {
			return nil, scanErr
		}
		activities = append(activities, activity)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate execution activities: %w", err)
	}
	return activities, nil
}

func readExecutionResourceIntents(
	ctx context.Context,
	querier workBoardQuerier,
	activityID string,
) ([]ExecutionResourceIntent, error) {
	rows, err := querier.QueryContext(ctx, `
		SELECT resource_intent_id, activity_id, work_id, resource_type, resource_key,
		       resource_key_normalized, mode, confidence, status, reason, revision,
		       created_at_ms, updated_at_ms, released_at_ms
		FROM execution_resource_intents
		WHERE activity_id = ?
		ORDER BY resource_type, resource_key_normalized, resource_intent_id
	`, strings.TrimSpace(activityID))
	if err != nil {
		return nil, fmt.Errorf("list execution resources for %q: %w", activityID, err)
	}
	defer rows.Close()
	resources := make([]ExecutionResourceIntent, 0)
	for rows.Next() {
		resource, scanErr := scanExecutionResourceIntent(rows)
		if scanErr != nil {
			return nil, scanErr
		}
		resources = append(resources, resource)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate execution resources for %q: %w", activityID, err)
	}
	return resources, nil
}

type executionActivityScanner interface{ Scan(...any) error }

func scanExecutionActivity(scanner executionActivityScanner) (ExecutionActivity, error) {
	var activity ExecutionActivity
	err := scanner.Scan(
		&activity.ActivityID, &activity.WorkID, &activity.Workflow,
		&activity.SubjectID, &activity.ItemID, &activity.TaskRef, &activity.SourceRef,
		&activity.Title, &activity.Phase, &activity.BaselineJSON,
		&activity.GuardedOverviewRevision, &activity.GuardedOverviewSHA256,
		&activity.ValidationJSON, &activity.CompletionSHA256, &activity.Revision,
		&activity.CompletedAtMS, &activity.CreatedAtMS, &activity.UpdatedAtMS,
	)
	return activity, err
}

func scanExecutionResourceIntent(scanner executionActivityScanner) (ExecutionResourceIntent, error) {
	var resource ExecutionResourceIntent
	err := scanner.Scan(
		&resource.ResourceIntentID, &resource.ActivityID, &resource.WorkID,
		&resource.ResourceType, &resource.ResourceKey, &resource.ResourceKeyNormalized,
		&resource.Mode, &resource.Confidence, &resource.Status, &resource.Reason,
		&resource.Revision, &resource.CreatedAtMS, &resource.UpdatedAtMS,
		&resource.ReleasedAtMS,
	)
	return resource, err
}

func coordinationRevision(ctx context.Context, querier rowQuerier) (int64, error) {
	// Preserve the watermark of historical events too: lowering it during
	// retirement could make an old overview revision appear current again.
	var revision int64
	if err := querier.QueryRowContext(ctx, `SELECT COALESCE(MAX(event_id), 0) FROM events`).Scan(&revision); err != nil {
		return 0, fmt.Errorf("read coordination revision: %w", err)
	}
	return revision, nil
}

func validExecutionPhase(phase ExecutionPhase) bool {
	switch phase {
	case ExecutionPhaseAnnounced, ExecutionPhaseSelected, ExecutionPhaseClaimed,
		ExecutionPhaseExecuting, ExecutionPhaseValidating, ExecutionPhaseBlocked,
		ExecutionPhaseInterrupted, ExecutionPhaseCompleted, ExecutionPhaseAbandoned:
		return true
	default:
		return false
	}
}

func readExecutionActivityByWorkTx(
	ctx context.Context,
	tx *sql.Tx,
	workID string,
) (ExecutionActivity, bool, error) {
	activity, err := scanExecutionActivity(tx.QueryRowContext(
		ctx,
		executionActivitySelectSQL+" WHERE work_id = ?",
		strings.TrimSpace(workID),
	))
	if errors.Is(err, sql.ErrNoRows) {
		return ExecutionActivity{}, false, nil
	}
	if err != nil {
		return ExecutionActivity{}, false, fmt.Errorf("read execution activity for Work %q: %w", workID, err)
	}
	return activity, true, nil
}

func transitionExecutionActivityForWorkTx(
	ctx context.Context,
	tx *sql.Tx,
	workID string,
	target ExecutionPhase,
	eventType string,
	reason string,
	nowMS int64,
) error {
	activity, exists, err := readExecutionActivityByWorkTx(ctx, tx, workID)
	if err != nil || !exists {
		return err
	}
	if activity.Phase == ExecutionPhaseCompleted || activity.Phase == ExecutionPhaseAbandoned {
		return fmt.Errorf("%w: cannot move terminal execution activity %q", ErrInvalidTransition, activity.ActivityID)
	}
	return setExecutionActivityPhaseTx(ctx, tx, &activity, target, eventType, reason, nowMS)
}

func setExecutionActivityPhaseTx(
	ctx context.Context,
	tx *sql.Tx,
	activity *ExecutionActivity,
	target ExecutionPhase,
	eventType string,
	reason string,
	nowMS int64,
) error {
	// Interruption revokes the fence. Resume must also clear pre-retirement
	// receipts that older stores retained on interrupted activities.
	guardRevision, guardSHA256 := activity.GuardedOverviewRevision, activity.GuardedOverviewSHA256
	if target == ExecutionPhaseInterrupted || eventType == "execution.resumed" {
		guardRevision, guardSHA256 = 0, ""
	}
	result, err := tx.ExecContext(ctx, `
		UPDATE execution_activities
		SET phase = ?, guarded_overview_revision = ?, guarded_overview_sha256 = ?,
		    revision = revision + 1, updated_at_ms = ?
		WHERE activity_id = ? AND revision = ?
	`, target, guardRevision, guardSHA256, nowMS, activity.ActivityID, activity.Revision)
	if err != nil {
		return fmt.Errorf("transition execution activity %q: %w", activity.ActivityID, err)
	}
	if err := requireOneCASRow(result, ErrRevisionConflict, "transition execution activity"); err != nil {
		return err
	}
	activity.Phase = target
	activity.GuardedOverviewRevision, activity.GuardedOverviewSHA256 = guardRevision, guardSHA256
	activity.Revision++
	activity.UpdatedAtMS = nowMS
	return appendExecutionActivityEventTx(ctx, tx, *activity, eventType, reason)
}

func markExecutionResourcesForWorkTx(
	ctx context.Context,
	tx *sql.Tx,
	workID string,
	target WriteIntentStatus,
	includeReleased bool,
	nowMS int64,
) error {
	releasedAtMS := int64(0)
	if target == WriteIntentReleased {
		releasedAtMS = nowMS
	}
	query := `
		UPDATE execution_resource_intents
		SET status = ?, revision = revision + 1, updated_at_ms = ?, released_at_ms = ?
		WHERE work_id = ?`
	args := []any{target, nowMS, releasedAtMS, strings.TrimSpace(workID)}
	if !includeReleased {
		query += " AND status IN (?, ?)"
		args = append(args, WriteIntentActive, WriteIntentRecovery)
	}
	if _, err := tx.ExecContext(ctx, query, args...); err != nil {
		return fmt.Errorf("mark semantic resources for Work %q as %q: %w", workID, target, err)
	}
	return nil
}

func executionResourceSpecsForResumeTx(
	ctx context.Context,
	tx *sql.Tx,
	activity ExecutionActivity,
) ([]ExecutionResourceIntentSpec, error) {
	resources, err := readExecutionResourceIntents(ctx, tx, activity.ActivityID)
	if err != nil {
		return nil, err
	}
	specs := make([]ExecutionResourceIntentSpec, 0, len(resources))
	for _, resource := range resources {
		if resource.Confidence != IntentConfirmed {
			continue
		}
		specs = append(specs, ExecutionResourceIntentSpec{
			ResourceType: resource.ResourceType,
			ResourceKey:  resource.ResourceKey,
			Mode:         resource.Mode,
			Confidence:   resource.Confidence,
			Reason:       resource.Reason,
		})
	}
	return specs, nil
}

func canCheckpointExecutionPhase(from, to ExecutionPhase) bool {
	if from == to {
		return from == ExecutionPhaseSelected || from == ExecutionPhaseExecuting ||
			from == ExecutionPhaseValidating || from == ExecutionPhaseBlocked
	}
	switch to {
	case ExecutionPhaseSelected:
		return from == ExecutionPhaseAnnounced || from == ExecutionPhaseBlocked
	case ExecutionPhaseClaimed:
		return from == ExecutionPhaseAnnounced || from == ExecutionPhaseSelected
	case ExecutionPhaseExecuting:
		return from == ExecutionPhaseClaimed || from == ExecutionPhaseSelected
	case ExecutionPhaseValidating:
		return from == ExecutionPhaseExecuting
	case ExecutionPhaseBlocked:
		return from == ExecutionPhaseAnnounced || from == ExecutionPhaseSelected ||
			from == ExecutionPhaseClaimed || from == ExecutionPhaseExecuting ||
			from == ExecutionPhaseValidating
	default:
		return false
	}
}

func appendExecutionActivityEventTx(
	ctx context.Context,
	tx *sql.Tx,
	activity ExecutionActivity,
	eventType string,
	reason string,
) error {
	payload, err := json.Marshal(map[string]any{
		"phase": activity.Phase, "workflow": activity.Workflow, "work_id": activity.WorkID,
	})
	if err != nil {
		return fmt.Errorf("encode execution activity event: %w", err)
	}
	if _, err := tx.ExecContext(ctx, `
		INSERT INTO events (
			aggregate_type, aggregate_id, aggregate_revision,
			event_type, reason, payload_json, created_at_ms
		) VALUES ('execution_activity', ?, ?, ?, ?, ?, ?)
	`, activity.ActivityID, activity.Revision, eventType, strings.TrimSpace(reason),
		string(payload), activity.UpdatedAtMS); err != nil {
		return fmt.Errorf("append execution activity event for %q: %w", activity.ActivityID, err)
	}
	return nil
}

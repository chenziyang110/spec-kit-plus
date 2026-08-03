package runcontrol

import (
	"errors"
	"time"
)

// Sentinel errors are deliberately stable so callers can classify failures
// with errors.Is without depending on SQLite error strings.
var (
	ErrNotFound            = errors.New("run control record not found")
	ErrAlreadyExists       = errors.New("run control record already exists")
	ErrInvalidArgument     = errors.New("invalid run control argument")
	ErrRevisionConflict    = errors.New("run revision conflict")
	ErrInvalidTransition   = errors.New("invalid run state transition")
	ErrLiveAttempt         = errors.New("run already has a live attempt")
	ErrStaleFence          = errors.New("stale attempt fence")
	ErrIdempotencyConflict = errors.New("idempotency key identifies a different request")
	ErrOwnerEpochConflict  = errors.New("supervisor owner epoch already exists")
	ErrUnsupportedSchema   = errors.New("unsupported run control schema")
	ErrOpenActivity        = errors.New("run already has an open activity")
	ErrUsableWorkspace     = errors.New("run already has a usable workspace")
	ErrWorkspaceGeneration = errors.New("workspace generation must increase")
	ErrWorkspaceNotUsable  = errors.New("workspace is not usable")
	ErrWorkspaceBinding    = errors.New("workspace binding is not authoritative")
	ErrWorkspaceConflict   = errors.New("workspace path or ref conflicts with recorded allocation")
	ErrWorkspaceEscape     = errors.New("workspace path escapes the runtime-owned root")
)

// More specific names are aliases of ErrNotFound so both broad and
// aggregate-specific errors.Is checks remain useful.
var (
	ErrRunNotFound       = ErrNotFound
	ErrAttemptNotFound   = ErrNotFound
	ErrOperationNotFound = ErrNotFound
)

type RunStatus string

const (
	RunQueued      RunStatus = "queued"
	RunAllocating  RunStatus = "allocating"
	RunReady       RunStatus = "ready"
	RunActive      RunStatus = "active"
	RunParked      RunStatus = "parked"
	RunInterrupted RunStatus = "interrupted"
	RunSealed      RunStatus = "sealed"
	RunCancelled   RunStatus = "cancelled"
	RunFailed      RunStatus = "failed"
)

type Run struct {
	RunID        string
	Kind         string
	SubjectType  string
	SubjectID    string
	TargetRef    string
	IntentSHA256 string
	OwnerEpoch   string
	Status       RunStatus
	Revision     int64
	CurrentFence int64
	CreatedAtMS  int64
	UpdatedAtMS  int64
}

type CreateRunParams struct {
	RunID        string
	Kind         string
	SubjectType  string
	SubjectID    string
	TargetRef    string
	IntentSHA256 string
}

type ExecutionMode string

const (
	ExecutionManaged      ExecutionMode = "managed"
	ExecutionManualAttach ExecutionMode = "manual_attach"
	ExecutionPromptOnly   ExecutionMode = "prompt_only"
)

type ActivityStatus string

const (
	ActivityPlanned     ActivityStatus = "planned"
	ActivityReady       ActivityStatus = "ready"
	ActivityActive      ActivityStatus = "active"
	ActivityBlocked     ActivityStatus = "blocked"
	ActivityInterrupted ActivityStatus = "interrupted"
	ActivitySucceeded   ActivityStatus = "succeeded"
	ActivityCancelled   ActivityStatus = "cancelled"
	ActivityFailed      ActivityStatus = "failed"
)

type Activity struct {
	ActivityID  string
	RunID       string
	Kind        string
	Ordinal     int64
	InputSHA256 string
	Status      ActivityStatus
	Revision    int64
	CreatedAtMS int64
	UpdatedAtMS int64
}

type CreateActivityParams struct {
	ActivityID  string
	RunID       string
	Kind        string
	InputSHA256 string
}

type WorkspaceStatus string

const (
	WorkspaceAllocating  WorkspaceStatus = "allocating"
	WorkspaceReady       WorkspaceStatus = "ready"
	WorkspaceInUse       WorkspaceStatus = "in_use"
	WorkspaceQuarantined WorkspaceStatus = "quarantined"
	WorkspaceSealed      WorkspaceStatus = "sealed"
	WorkspaceReleased    WorkspaceStatus = "released"
	WorkspaceFailed      WorkspaceStatus = "failed"
)

type Workspace struct {
	WorkspaceID   string
	RunID         string
	Generation    int64
	Kind          string
	RootPath      string
	RepoCommonDir string
	BaseRef       string
	BaseCommit    string
	PrivateRef    string
	Status        WorkspaceStatus
	Revision      int64
	CreatedAtMS   int64
	UpdatedAtMS   int64
}

type WorkspaceAllocationStatus string

const (
	WorkspaceAllocationPrepared       WorkspaceAllocationStatus = "prepared"
	WorkspaceAllocationExecuting      WorkspaceAllocationStatus = "executing"
	WorkspaceAllocationSucceeded      WorkspaceAllocationStatus = "succeeded"
	WorkspaceAllocationFailed         WorkspaceAllocationStatus = "failed"
	WorkspaceAllocationOutcomeUnknown WorkspaceAllocationStatus = "outcome_unknown"
)

// WorkspaceAllocation is the durable journal for Git mutations performed
// before an Attempt exists. AttemptID and Fence intentionally remain empty and
// zero: execution authority is issued only after allocation completes.
type WorkspaceAllocation struct {
	AllocationID        string
	RunID               string
	WorkspaceID         string
	WorkspaceGeneration int64
	OwnerEpoch          string
	AttemptID           string
	Fence               int64
	RunRevision         int64
	WorkspaceRevision   int64
	IdempotencyKey      string
	RequestSHA256       string
	Status              WorkspaceAllocationStatus
	Reason              string
	Revision            int64
	CreatedAtMS         int64
	UpdatedAtMS         int64
}

type BeginWorkspaceAllocationParams struct {
	AllocationID              string
	RunID                     string
	WorkspaceID               string
	ExpectedRunRevision       int64
	ExpectedWorkspaceRevision int64
	IdempotencyKey            string
	RequestSHA256             string
}

type CompleteWorkspaceAllocationParams struct {
	AllocationID               string
	ExpectedAllocationRevision int64
	Execution                  PrepareExecutionParams
}

type CreateWorkspaceParams struct {
	WorkspaceID   string
	RunID         string
	Generation    int64
	Kind          string
	RootPath      string
	RepoCommonDir string
	BaseRef       string
	BaseCommit    string
	PrivateRef    string
}

type PrepareExecutionParams struct {
	RunID                     string
	ActivityID                string
	WorkspaceID               string
	ExpectedRunRevision       int64
	ExpectedActivityRevision  int64
	ExpectedWorkspaceRevision int64
}

type PreparedExecution struct {
	Run       Run
	Activity  Activity
	Workspace Workspace
}

type AttemptStatus string

const (
	AttemptIssued   AttemptStatus = "issued"
	AttemptActive   AttemptStatus = "active"
	AttemptSealing  AttemptStatus = "sealing"
	AttemptFinished AttemptStatus = "finished"
	AttemptRevoked  AttemptStatus = "revoked"
	AttemptLost     AttemptStatus = "lost"
	AttemptFailed   AttemptStatus = "failed"
)

type Attempt struct {
	AttemptID           string
	RunID               string
	ActivityID          string
	WorkspaceID         string
	WorkspaceGeneration int64
	Status              AttemptStatus
	AdapterID           string
	ExecutionMode       ExecutionMode
	OwnerEpoch          string
	Fence               int64
	LeaseUntilMS        int64
	HeartbeatAtMS       int64
	Revision            int64
	CreatedAtMS         int64
	UpdatedAtMS         int64
}

type IssueAttemptParams struct {
	AttemptID                 string
	RunID                     string
	ActivityID                string
	WorkspaceID               string
	ExpectedRunRevision       int64
	ExpectedActivityRevision  int64
	ExpectedWorkspaceRevision int64
	AdapterID                 string
	ExecutionMode             ExecutionMode
	LeaseUntil                time.Time
}

type OperationStatus string

const (
	OperationPrepared       OperationStatus = "prepared"
	OperationExecuting      OperationStatus = "executing"
	OperationSucceeded      OperationStatus = "succeeded"
	OperationFailed         OperationStatus = "failed"
	OperationOutcomeUnknown OperationStatus = "outcome_unknown"
)

type Operation struct {
	OperationID    string
	Kind           string
	AggregateType  string
	AggregateID    string
	RunID          string
	AttemptID      string
	ActivityID     string
	WorkspaceID    string
	OwnerEpoch     string
	Fence          int64
	RunRevision    int64
	IdempotencyKey string
	RequestSHA256  string
	Status         OperationStatus
	Revision       int64
	CreatedAtMS    int64
	UpdatedAtMS    int64
}

type BeginOperationParams struct {
	OperationID         string
	Kind                string
	AggregateType       string
	AggregateID         string
	RunID               string
	AttemptID           string
	Fence               int64
	ExpectedRunRevision int64
	IdempotencyKey      string
	RequestSHA256       string
}

type Event struct {
	EventID           int64
	AggregateType     string
	AggregateID       string
	AggregateRevision int64
	EventType         string
	Reason            string
	PayloadJSON       string
	CreatedAtMS       int64
}

const (
	RunEventCreated      = "run.created"
	RunEventClaimed      = "run.claimed"
	RunEventTransitioned = "run.transitioned"
)

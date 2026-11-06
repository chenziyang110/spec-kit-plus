package main

const doSessionSchema = "spec-kit-do-session-v2"
const doLegacySessionSchema = "spec-kit-do-session-v1"
const doSessionSizeLimit = 8 * 1024 * 1024

type DoMethodBinding struct {
	ID            string `json:"id"`
	Revision      int    `json:"revision"`
	ContentDigest string `json:"content_digest"`
}

// DoSession records native-tool observations. It is not a process executor and
// never turns a recorded observation into runtime-executed or human evidence.
type DoSession struct {
	SchemaVersion      string                     `json:"schema_version"`
	ID                 string                     `json:"id"`
	Revision           int                        `json:"revision"`
	Goal               string                     `json:"goal"`
	Definition         PlaybookDefinition         `json:"definition"`
	DefinitionDigest   string                     `json:"definition_digest"`
	TemplateDefinition *PlaybookDefinition        `json:"template_definition,omitempty"`
	TemplateDigest     string                     `json:"template_digest,omitempty"`
	Parameters         map[string]string          `json:"parameters,omitempty"`
	DefinitionEpoch    int                        `json:"definition_epoch,omitempty"`
	DefinitionHistory  []DoDefinitionEpoch        `json:"definition_history,omitempty"`
	ReplanReceipts     map[string]DoReplanReceipt `json:"replan_receipts,omitempty"`
	MethodBinding      *DoMethodBinding           `json:"method_binding,omitempty"`
	Context            map[string]string          `json:"context"`
	InitialSources     map[string]string          `json:"initial_sources"`
	BaselineJSON       string                     `json:"baseline_json,omitempty"`
	BaselineRef        string                     `json:"baseline_ref,omitempty"`
	BaselineSHA256     string                     `json:"baseline_sha256,omitempty"`
	WriteScope         []string                   `json:"write_scope"`
	OutputScope        []string                   `json:"output_scope"`
	MetadataWriteScope []string                   `json:"metadata_write_scope,omitempty"`
	WorkID             string                     `json:"work_id"`
	WorkFence          int64                      `json:"work_fence"`
	ExecutionOutcome   string                     `json:"execution_outcome"`
	KnowledgeStatus    string                     `json:"knowledge_status"`
	Attempts           []DoAttempt                `json:"attempts"`
	Requests           map[string]string          `json:"requests"`
	ResumeReceipts     map[string]string          `json:"resume_receipts,omitempty"`
	ExternalChanges    []DoExternalChangeAudit    `json:"external_changes,omitempty"`
	Validation         *DoValidation              `json:"validation,omitempty"`
	Knowledge          *DoKnowledgeReceipt        `json:"knowledge,omitempty"`
	Blocker            *DoBlocker                 `json:"blocker,omitempty"`
	BlockerHistory     []DoBlocker                `json:"blocker_history,omitempty"`
	CreatedAt          string                     `json:"created_at"`
	UpdatedAt          string                     `json:"updated_at"`
}

type DoAttempt struct {
	NativeAction            *PlaybookNativeAction `json:"native_action,omitempty"`
	NativeObservationRef    string                `json:"native_observation_ref,omitempty"`
	NativeObservationSHA256 string                `json:"native_observation_sha256,omitempty"`
	ID                      string                `json:"id"`
	TargetID                string                `json:"target_id"`
	Kind                    string                `json:"kind"`
	Status                  string                `json:"status"`
	DefinitionDigest        string                `json:"definition_digest"`
	DefinitionEpoch         int                   `json:"definition_epoch,omitempty"`
	SourceFingerprint       string                `json:"source_fingerprint"`
	Sources                 map[string]string     `json:"sources"`
	AfterSourceFingerprint  string                `json:"after_source_fingerprint,omitempty"`
	AfterSources            map[string]string     `json:"after_sources"`
	AfterDirtyPaths         []string              `json:"after_dirty_paths"`
	SourceChangedPaths      []string              `json:"source_changed_paths,omitempty"`
	SourceRevision          string                `json:"source_revision"`
	DirtyPaths              []string              `json:"dirty_paths"`
	RegisteredAt            string                `json:"registered_at"`
	DependencyAttempts      map[string]string     `json:"dependency_attempts"`
	EvidenceOrigin          string                `json:"evidence_origin,omitempty"`
	ToolCallID              string                `json:"tool_call_id,omitempty"`
	Argv                    []string              `json:"argv"`
	Cwd                     string                `json:"cwd"`
	StartedAt               string                `json:"started_at,omitempty"`
	FinishedAt              string                `json:"finished_at,omitempty"`
	ElapsedMS               int64                 `json:"elapsed_ms,omitempty"`
	ExitCode                *int                  `json:"exit_code,omitempty"`
	TimedOut                bool                  `json:"timed_out,omitempty"`
	Cancelled               bool                  `json:"cancelled,omitempty"`
	Summary                 string                `json:"summary,omitempty"`
	Results                 []DoResultRef         `json:"result_refs,omitempty"`
	Recovery                *DoRecovery           `json:"recovery,omitempty"`
}

type DoResultRef struct {
	Path           string `json:"path"`
	SHA256         string `json:"sha256,omitempty"`
	SnapshotRef    string `json:"snapshot_ref,omitempty"`
	SnapshotSHA256 string `json:"snapshot_sha256,omitempty"`
	Kind           string `json:"kind"`
	Size           int64  `json:"size,omitempty"`
}

type DoRecovery struct {
	NativeActionSettled  bool   `json:"native_action_settled,omitempty"`
	Reason               string `json:"reason"`
	EvidenceRef          string `json:"evidence_ref,omitempty"`
	EvidenceText         string `json:"evidence_text,omitempty"`
	EvidenceSHA256       string `json:"evidence_sha256,omitempty"`
	ProcessesStopped     bool   `json:"processes_stopped,omitempty"`
	SideEffectsInspected bool   `json:"side_effects_inspected"`
}

type DoValidation struct {
	Status             string   `json:"status"`
	EvidenceOrigin     string   `json:"evidence_origin"`
	DefinitionDigest   string   `json:"definition_digest"`
	SourceFingerprint  string   `json:"source_fingerprint"`
	EvidenceDigest     string   `json:"evidence_digest"`
	RequiredSteps      int      `json:"required_steps"`
	RequiredChecks     int      `json:"required_checks"`
	ChangedSourcePaths []string `json:"changed_source_paths"`
	CognitionCloseout  string   `json:"cognition_closeout"`
	VerifiedAt         string   `json:"verified_at"`
	Blockers           []string `json:"blockers"`
}

type DoKnowledgeReceipt struct {
	Path     string `json:"path"`
	SHA256   string `json:"sha256"`
	MethodID string `json:"method_id"`
	Revision int    `json:"revision"`
}

type DoBlocker struct {
	Category          string            `json:"category"`
	Owner             string            `json:"owner"`
	Cause             string            `json:"cause"`
	NextAction        string            `json:"next_action"`
	UnblockCriteria   string            `json:"unblock_criteria"`
	ResumePoint       string            `json:"resume_point"`
	AttemptedRecovery []string          `json:"attempted_recovery"`
	EvidenceRefs      []string          `json:"evidence_refs"`
	EvidenceDigests   map[string]string `json:"evidence_digests,omitempty"`
}

type DoPlaybookValidationReceipt struct {
	InstanceDigest    string            `json:"instance_digest,omitempty"`
	Parameters        map[string]string `json:"parameters,omitempty"`
	SessionID         string            `json:"session_id"`
	MethodID          string            `json:"method_id"`
	BaseRevision      int               `json:"base_revision"`
	BaseDigest        string            `json:"base_digest"`
	DefinitionDigest  string            `json:"definition_digest"`
	SourceFingerprint string            `json:"source_fingerprint"`
	Sources           map[string]string `json:"sources"`
	EvidenceDigest    string            `json:"evidence_digest"`
	Outcome           string            `json:"outcome"`
	VerifiedAt        string            `json:"verified_at"`
}

type doStartInput struct {
	Command       *doCommandInput    `json:"command,omitempty"`
	Parameters    map[string]string  `json:"parameters,omitempty"`
	SessionID     string             `json:"session_id,omitempty"`
	Goal          string             `json:"goal"`
	Definition    PlaybookDefinition `json:"definition"`
	MethodBinding *DoMethodBinding   `json:"method_binding,omitempty"`
	Context       map[string]string  `json:"context,omitempty"`
	SourceFiles   []string           `json:"source_files,omitempty"`
	WriteScope    []string           `json:"write_scope,omitempty"`
	OutputScope   []string           `json:"output_scope,omitempty"`
	AgentID       string             `json:"agent_id"`
	AdapterID     string             `json:"adapter_id"`
}

type doRecordInput struct {
	ExpectedRevision int             `json:"expected_revision"`
	RequestID        string          `json:"request_id"`
	Events           []doRecordEvent `json:"events"`
}

type doRecordEvent struct {
	NativeAction      *PlaybookNativeAction `json:"native_action,omitempty"`
	NativeObservation *DoNativeObservation  `json:"native_observation,omitempty"`
	AttemptID         string                `json:"attempt_id"`
	TargetID          string                `json:"target_id"`
	Kind              string                `json:"kind"`
	Event             string                `json:"event"`
	Status            string                `json:"status,omitempty"`
	EvidenceOrigin    string                `json:"evidence_origin,omitempty"`
	ToolCallID        string                `json:"tool_call_id,omitempty"`
	Argv              []string              `json:"argv,omitempty"`
	Cwd               string                `json:"cwd,omitempty"`
	StartedAt         string                `json:"started_at,omitempty"`
	FinishedAt        string                `json:"finished_at,omitempty"`
	ExitCode          *int                  `json:"exit_code,omitempty"`
	TimedOut          bool                  `json:"timed_out,omitempty"`
	Cancelled         bool                  `json:"cancelled,omitempty"`
	Summary           string                `json:"summary,omitempty"`
	ResultRefs        []DoResultRef         `json:"result_refs,omitempty"`
}

type doFinishInput struct {
	ExpectedRevision int                 `json:"expected_revision"`
	KnowledgeStatus  string              `json:"knowledge_status,omitempty"`
	Knowledge        *DoKnowledgeReceipt `json:"knowledge,omitempty"`
	Blocker          *DoBlocker          `json:"blocker,omitempty"`
}

type doResumeInput struct {
	ExpectedRevision int                     `json:"expected_revision"`
	AttemptID        string                  `json:"attempt_id"`
	WorkFence        int64                   `json:"work_fence,omitempty"`
	Recovery         DoRecovery              `json:"recovery"`
	Replan           *doReplanInput          `json:"replan,omitempty"`
	ExternalChanges  *DoExternalChangesInput `json:"external_changes,omitempty"`
}

// Replanning appends an immutable definition epoch. Attempts remain in the
// session, but only observations from the active epoch can satisfy its checks.
type DoDefinitionEpoch struct {
	TemplateDefinition *PlaybookDefinition `json:"template_definition,omitempty"`
	TemplateDigest     string              `json:"template_digest,omitempty"`
	Parameters         map[string]string   `json:"parameters,omitempty"`
	Epoch              int                 `json:"epoch"`
	Definition         PlaybookDefinition  `json:"definition"`
	DefinitionDigest   string              `json:"definition_digest"`
	Sources            map[string]string   `json:"sources"`
	SourceFingerprint  string              `json:"source_fingerprint,omitempty"`
	SourceRevision     string              `json:"source_revision,omitempty"`
	DirtyPaths         []string            `json:"dirty_paths"`
	WriteScope         []string            `json:"write_scope"`
	OutputScope        []string            `json:"output_scope"`
	FrozenAt           string              `json:"frozen_at"`
	BasisOrigin        string              `json:"basis_origin"`
	ReplanRequestID    string              `json:"replan_request_id,omitempty"`
	FailedAttemptID    string              `json:"failed_attempt_id,omitempty"`
	Recovery           *DoRecovery         `json:"recovery,omitempty"`
	RetainedAttempts   []DoRetainedAttempt `json:"retained_attempts,omitempty"`
}

type DoReplanReceipt struct {
	RequestDigest    string `json:"request_digest"`
	DefinitionEpoch  int    `json:"definition_epoch"`
	DefinitionDigest string `json:"definition_digest"`
	EvidenceRef      string `json:"evidence_ref"`
	EvidenceSHA256   string `json:"evidence_sha256"`
}

type doReplanInput struct {
	Mode           string             `json:"mode,omitempty"`
	RetainVerified bool               `json:"retain_verified,omitempty"`
	RequestID      string             `json:"request_id"`
	Definition     PlaybookDefinition `json:"definition"`
	WriteScope     []string           `json:"write_scope,omitempty"`
	OutputScope    []string           `json:"output_scope,omitempty"`
}

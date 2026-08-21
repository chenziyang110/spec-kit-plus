package closeout

import (
	"encoding/json"
	"path/filepath"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes"
	changemodel "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/changes/model"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workflowregistry"
)

const (
	statusOK      = "ok"
	statusBlocked = "blocked"

	modeInlineJSON   = "inline_json"
	modeDeltaSession = "delta_session"

	closeoutReason = "workflow-finalize"
)

type Input struct {
	Workflow           string   `json:"workflow"`
	Reason             string   `json:"reason,omitempty"`
	Intent             string   `json:"intent,omitempty"`
	Since              string   `json:"since,omitempty"`
	Head               string   `json:"head,omitempty"`
	IncludeWorkingTree bool     `json:"include_working_tree"`
	IncludeUntracked   bool     `json:"include_untracked"`
	ExplicitPaths      []string `json:"explicit_paths,omitempty"`
	DeltaSessionID     string   `json:"delta_session_id,omitempty"`
	ScopeDir           string   `json:"scope_dir,omitempty"`
	ScopeMode          string   `json:"scope_mode,omitempty"`
}

type Payload struct {
	Status                  string                   `json:"status"`
	Workflow                string                   `json:"workflow,omitempty"`
	WorkflowCanonical       string                   `json:"workflow_canonical,omitempty"`
	ScopeMode               string                   `json:"scope_mode,omitempty"`
	UpdateMode              string                   `json:"update_mode,omitempty"`
	DeltaSessionID          *string                  `json:"delta_session_id,omitempty"`
	CommandSafetyNote       string                   `json:"command_safety_note,omitempty"`
	UpdateCommand           string                   `json:"update_command,omitempty"`
	UpdateArgv              []string                 `json:"update_argv"`
	ApplyCommand            string                   `json:"apply_command,omitempty"`
	ApplyArgv               []string                 `json:"apply_argv"`
	DeltaAppendCommand      string                   `json:"delta_append_command,omitempty"`
	DeltaAppendDraft        *DeltaAppendDraft        `json:"delta_append_draft,omitempty"`
	RecommendedNextCommand  string                   `json:"recommended_next_command,omitempty"`
	RequiredAgentFields     []string                 `json:"required_agent_fields"`
	KnownPaths              []string                 `json:"known_paths"`
	UnknownPaths            []string                 `json:"unknown_paths"`
	UnknownPathDispositions []UnknownPathDisposition `json:"unknown_path_dispositions"`
	Changes                 []changes.Change         `json:"changes"`
	ChangeSummary           changes.Summary          `json:"change_summary"`
	PayloadDraft            *PayloadDraft            `json:"payload_draft,omitempty"`
	Warnings                []string                 `json:"warnings"`
	Errors                  []string                 `json:"errors"`
}

type UnknownPathDisposition struct {
	Path                  string   `json:"path"`
	ChangeLevel           string   `json:"change_level"`
	AllowedDispositions   []string `json:"allowed_dispositions"`
	AgentDisposition      *string  `json:"agent_disposition"`
	RequiredAgentDecision bool     `json:"required_agent_decision"`
	PlannerReason         []string `json:"planner_reason"`
}

type PayloadDraft struct {
	Workflow                string                   `json:"workflow"`
	Reason                  string                   `json:"reason"`
	ChangedPaths            []string                 `json:"changed_paths"`
	PathChanges             []changemodel.PathChange `json:"path_changes"`
	UnknownPathDispositions []UnknownPathDisposition `json:"unknown_path_dispositions"`
	ScopePaths              []string                 `json:"scope_paths"`
	BehaviorSurfaces        []string                 `json:"behavior_surfaces"`
	GeneratedSurfaces       []string                 `json:"generated_surfaces"`
	GeneratedSurfaceNote    []string                 `json:"generated_surface_notes"`
	StateContracts          []string                 `json:"state_contracts"`
	Verification            []VerificationRecord     `json:"verification"`
	VerificationEvidence    []VerificationRecord     `json:"verification_evidence"`
	KnownUnknowns           []string                 `json:"known_unknowns"`
	ConfidenceNotes         []string                 `json:"confidence_notes"`
	UserDecisions           []string                 `json:"user_decisions"`
	Boundary                BoundaryDraft            `json:"boundary"`
}

type DeltaAppendDraft struct {
	EventType              string                   `json:"event_type"`
	OriginCommand          string                   `json:"origin_command"`
	Phase                  string                   `json:"phase"`
	ChangedPaths           []string                 `json:"changed_paths"`
	PathChanges            []changemodel.PathChange `json:"path_changes"`
	RequiredAgentFields    []string                 `json:"required_agent_fields"`
	RequiredEvidenceResult string                   `json:"required_evidence_result"`
	ArgvPrefix             []string                 `json:"argv_prefix"`
	ArgvPlaceholders       []string                 `json:"argv_placeholders"`
}

type VerificationRecord struct {
	Command  string `json:"command"`
	Result   string `json:"result"`
	Artifact string `json:"artifact,omitempty"`
}

type BoundaryDraft struct {
	CommitRange        string   `json:"commit_range,omitempty"`
	InitialDirtyPaths  []string `json:"initial_dirty_paths"`
	WorkflowOwnedPaths []string `json:"workflow_owned_paths"`
	ScopeMode          string   `json:"scope_mode"`
}

func Run(paths rt.Paths, input Input) (Payload, error) {
	workflow, err := CanonicalWorkflow(input.Workflow)
	if err != nil {
		return Payload{
			Status:                  statusBlocked,
			Workflow:                strings.TrimSpace(input.Workflow),
			UpdateArgv:              []string{},
			ApplyArgv:               []string{},
			RequiredAgentFields:     []string{},
			KnownPaths:              []string{},
			UnknownPaths:            []string{},
			UnknownPathDispositions: []UnknownPathDisposition{},
			Changes:                 []changes.Change{},
			Warnings:                []string{},
			Errors:                  []string{err.Error()},
		}, nil
	}
	reason := closeoutReason
	if strings.TrimSpace(input.Reason) != "" {
		reason = strings.TrimSpace(input.Reason)
	}
	intent := workflow
	if strings.TrimSpace(input.Intent) != "" {
		intent = strings.TrimSpace(input.Intent)
	}
	scopeMode := strings.ToLower(strings.TrimSpace(input.ScopeMode))
	if scopeMode == "" {
		if len(input.ExplicitPaths) > 0 {
			scopeMode = "explicit"
		} else {
			scopeMode = "repository_diff"
		}
	}
	if scopeMode != "explicit" && scopeMode != "repository_diff" {
		return Payload{
			Status: statusBlocked, Workflow: workflow, WorkflowCanonical: workflow,
			UpdateArgv: []string{}, ApplyArgv: []string{}, RequiredAgentFields: []string{}, KnownPaths: []string{}, UnknownPaths: []string{},
			UnknownPathDispositions: []UnknownPathDisposition{}, Changes: []changes.Change{}, Warnings: []string{}, Errors: []string{"scope mode must be explicit or repository_diff"},
		}, nil
	}
	if scopeMode == "explicit" && len(input.ExplicitPaths) == 0 {
		return Payload{
			Status: statusBlocked, Workflow: workflow, WorkflowCanonical: workflow, ScopeMode: scopeMode,
			UpdateArgv: []string{}, ApplyArgv: []string{}, RequiredAgentFields: []string{}, KnownPaths: []string{}, UnknownPaths: []string{},
			UnknownPathDispositions: []UnknownPathDisposition{}, Changes: []changes.Change{}, Warnings: []string{}, Errors: []string{"explicit closeout scope requires at least one --changed-path"},
		}, nil
	}

	includeWorkingTree := input.IncludeWorkingTree
	includeUntracked := input.IncludeUntracked
	if scopeMode == "explicit" {
		includeWorkingTree = false
		includeUntracked = false
	}

	changePayload, err := changes.Run(paths, changes.Input{
		Since:              input.Since,
		Head:               input.Head,
		IncludeWorkingTree: includeWorkingTree,
		IncludeUntracked:   includeUntracked,
		ExplicitPaths:      input.ExplicitPaths,
		Intent:             intent,
	})
	if err != nil {
		return Payload{}, err
	}

	dispositions := unknownPathDispositions(changePayload.Changes)
	payload := Payload{
		Status:                  changePayload.Status,
		Workflow:                workflow,
		WorkflowCanonical:       workflow,
		ScopeMode:               scopeMode,
		UpdateArgv:              []string{},
		ApplyArgv:               []string{},
		RequiredAgentFields:     requiredAgentFields(changePayload.UnknownPaths),
		KnownPaths:              knownPaths(changePayload.Changes),
		UnknownPaths:            append([]string{}, changePayload.UnknownPaths...),
		UnknownPathDispositions: dispositions,
		Changes:                 append([]changes.Change{}, changePayload.Changes...),
		ChangeSummary:           changePayload.Summary,
		Warnings:                append([]string{}, changePayload.Warnings...),
		Errors:                  append([]string{}, changePayload.Errors...),
	}

	if payload.Status != statusOK {
		return payload, nil
	}

	changedPaths := changedPaths(changePayload.Changes)
	scopeDir := strings.TrimSpace(input.ScopeDir)
	if scopeDir == "" {
		scopeDir = "<feature-or-scope>"
	}
	if strings.TrimSpace(input.DeltaSessionID) != "" {
		sessionID := strings.TrimSpace(input.DeltaSessionID)
		payload.UpdateMode = modeDeltaSession
		payload.DeltaSessionID = &sessionID
		payload.CommandSafetyNote = "command strings are display-only; fill delta_append_draft, then execute apply_argv after recording the required agent-owned evidence; update_argv is low-level compatibility/debug only"
		payload.DeltaAppendCommand = "display only: specify-runtime cognition delta append --session <delta_session_id> --event-type workflow_closeout ...agent evidence flags... --format json"
		payload.DeltaAppendDraft = deltaAppendDraft(sessionID, workflow, changedPaths, pathChanges(changePayload.Changes), dispositions, payload.RequiredAgentFields)
		payload.UpdateCommand = "display only: specify-runtime cognition update --delta-session <delta_session_id> --reason <reason> --format json"
		payload.UpdateArgv = []string{"specify-runtime", "cognition", "update", "--delta-session", sessionID, "--reason", reason, "--format", "json"}
		payload.ApplyCommand = "display only: specify-runtime cognition closeout apply --workflow <workflow> --scope-dir <feature-or-scope> --delta-session <delta_session_id> --reason <reason> --format json"
		payload.ApplyArgv = []string{"specify-runtime", "cognition", "closeout", "apply", "--workflow", workflow, "--scope-dir", scopeDir, "--delta-session", sessionID, "--reason", reason, "--format", "json"}
		payload.RecommendedNextCommand = "fill_delta_append_draft_then_closeout_apply"
		return payload, nil
	}

	updateArgv := []string{"specify-runtime", "cognition", "update", "--payload-json", "<inline-json>", "--reason", reason, "--format", "json"}
	payload.UpdateMode = modeInlineJSON
	payload.CommandSafetyNote = "fill payload_draft in memory, JSON-encode it to apply_argv stdin, and execute argv directly without shell interpolation or creating an agent-authored payload file; update_argv is low-level compatibility/debug only"
	payload.UpdateCommand = "display only: specify-runtime cognition update --payload-json '<inline-json>' --reason <reason> --format json"
	payload.UpdateArgv = updateArgv
	payload.ApplyCommand = "display only: JSON-encode the filled payload_draft to stdin, then run specify-runtime cognition closeout apply --workflow <workflow> --scope-dir <feature-or-scope> --payload-json - --reason <reason> --format json"
	payload.ApplyArgv = []string{"specify-runtime", "cognition", "closeout", "apply", "--workflow", workflow, "--scope-dir", scopeDir, "--payload-json", "-", "--reason", reason, "--format", "json"}
	payload.RecommendedNextCommand = "fill_payload_draft_then_closeout_apply"
	payload.PayloadDraft = &PayloadDraft{
		Workflow:                workflow,
		Reason:                  reason,
		ChangedPaths:            changedPaths,
		PathChanges:             pathChanges(changePayload.Changes),
		UnknownPathDispositions: append([]UnknownPathDisposition{}, dispositions...),
		ScopePaths:              append([]string{}, changedPaths...),
		BehaviorSurfaces:        []string{},
		GeneratedSurfaces:       []string{},
		GeneratedSurfaceNote:    []string{},
		StateContracts:          []string{},
		Verification:            []VerificationRecord{},
		VerificationEvidence:    []VerificationRecord{},
		KnownUnknowns:           []string{},
		ConfidenceNotes:         []string{},
		UserDecisions:           []string{},
		Boundary: BoundaryDraft{
			InitialDirtyPaths:  []string{},
			WorkflowOwnedPaths: append([]string{}, changedPaths...),
			ScopeMode:          scopeMode,
		},
	}
	return payload, nil
}

func CanonicalWorkflow(value string) (string, error) {
	return workflowregistry.CanonicalCloseoutWorkflow(value)
}

func knownPaths(items []changes.Change) []string {
	out := make([]string, 0, len(items))
	for _, item := range items {
		if item.KnownToRuntime {
			out = append(out, item.Path)
		}
	}
	return sortedUnique(out)
}

func changedPaths(items []changes.Change) []string {
	out := make([]string, 0, len(items)*2)
	for _, item := range items {
		out = append(out, item.Path)
		if strings.TrimSpace(item.OldPath) != "" {
			out = append(out, item.OldPath)
		}
	}
	return sortedUnique(out)
}

func pathChanges(items []changes.Change) []changemodel.PathChange {
	out := make([]changemodel.PathChange, 0, len(items))
	for _, item := range items {
		change := item.PathChange
		change.EvidenceRefs = append([]string{}, item.EvidenceRefs...)
		if item.KnownToRuntime {
			disposition := changemodel.DispositionAdoptable
			change.Disposition = &disposition
		}
		out = append(out, change)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Path == out[j].Path {
			return out[i].OldPath < out[j].OldPath
		}
		return out[i].Path < out[j].Path
	})
	return out
}

func unknownPathDispositions(items []changes.Change) []UnknownPathDisposition {
	out := []UnknownPathDisposition{}
	for _, item := range items {
		if item.KnownToRuntime {
			continue
		}
		out = append(out, UnknownPathDisposition{
			Path:                  item.Path,
			ChangeLevel:           item.ChangeLevel,
			AllowedDispositions:   []string{"adoptable", "review_only", "ignored", "blocking_known_unknown"},
			AgentDisposition:      nil,
			RequiredAgentDecision: true,
			PlannerReason:         plannerReason(item),
		})
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].Path < out[j].Path
	})
	return out
}

func plannerReason(item changes.Change) []string {
	reasons := append([]string{}, item.Reason...)
	if len(reasons) == 0 {
		reasons = append(reasons, "changed path lacks active runtime path_index coverage")
	}
	return reasons
}

func requiredAgentFields(unknownPaths []string) []string {
	fields := []string{
		"behavior_surfaces",
		"generated_surfaces",
		"state_contracts",
		"verification",
		"confidence_notes",
		"user_decisions",
	}
	if len(unknownPaths) > 0 {
		fields = append(fields, "unknown_path_dispositions")
	}
	return fields
}

func deltaAppendDraft(sessionID string, workflow string, paths []string, changes []changemodel.PathChange, dispositions []UnknownPathDisposition, requiredFields []string) *DeltaAppendDraft {
	prefix := []string{
		"specify-runtime", "cognition", "delta", "append",
		"--session", sessionID,
		"--event-type", "workflow_closeout",
		"--origin-command", workflow,
		"--phase", "closeout",
	}
	for _, path := range paths {
		prefix = append(prefix, "--changed-path", path)
	}
	for _, change := range changes {
		encoded, _ := json.Marshal(change)
		prefix = append(prefix, "--path-change", string(encoded))
	}
	placeholders := []string{
		"--behavior-surface", "<agent-owned behavior surface>",
		"--generated-surface", "<agent-owned generated surface if applicable>",
		"--known-unknown", "<agent-owned known unknown if applicable>",
	}
	for _, disposition := range dispositions {
		encoded, _ := json.Marshal(map[string]string{
			"path":              disposition.Path,
			"agent_disposition": "<adoptable|review_only|ignored|blocking_known_unknown>",
		})
		placeholders = append(placeholders, "--path-disposition", string(encoded))
	}
	placeholders = append(placeholders,
		"--verification", `{"command":"<agent-owned verification command>","result":"passed","artifact":"<optional evidence artifact>"}`,
		"--confidence", "<agent-owned confidence note>",
		"--format", "json",
	)
	return &DeltaAppendDraft{
		EventType:              "workflow_closeout",
		OriginCommand:          workflow,
		Phase:                  "closeout",
		ChangedPaths:           append([]string{}, paths...),
		PathChanges:            append([]changemodel.PathChange{}, changes...),
		RequiredAgentFields:    append([]string{}, requiredFields...),
		RequiredEvidenceResult: "passed",
		ArgvPrefix:             prefix,
		ArgvPlaceholders:       placeholders,
	}
}

func sortedUnique(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = filepath.ToSlash(strings.TrimSpace(value))
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

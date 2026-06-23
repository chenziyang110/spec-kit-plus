package closeout

import (
	"fmt"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/changes"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

const (
	statusOK      = "ok"
	statusBlocked = "blocked"

	modePayloadFile  = "payload_file"
	modeDeltaSession = "delta_session"

	closeoutReason = "workflow-finalize"
)

var knownWorkflows = map[string]struct{}{
	"sp-analyze":         {},
	"sp-auto":            {},
	"sp-checklist":       {},
	"sp-clarify":         {},
	"sp-constitution":    {},
	"sp-debug":           {},
	"sp-deep-research":   {},
	"sp-discussion":      {},
	"sp-explain":         {},
	"sp-fast":            {},
	"sp-implement":       {},
	"sp-implement-teams": {},
	"sp-integrate":       {},
	"sp-map-build":       {},
	"sp-map-scan":        {},
	"sp-map-update":      {},
	"sp-plan":            {},
	"sp-prd":             {},
	"sp-prd-build":       {},
	"sp-prd-scan":        {},
	"sp-quick":           {},
	"sp-research":        {},
	"sp-specify":         {},
	"sp-tasks":           {},
	"sp-taskstoissues":   {},
	"sp-team":            {},
}

type Input struct {
	Workflow           string   `json:"workflow"`
	Since              string   `json:"since,omitempty"`
	Head               string   `json:"head,omitempty"`
	IncludeWorkingTree bool     `json:"include_working_tree"`
	IncludeUntracked   bool     `json:"include_untracked"`
	ExplicitPaths      []string `json:"explicit_paths,omitempty"`
	DeltaSessionID     string   `json:"delta_session_id,omitempty"`
	PayloadPath        string   `json:"payload_path,omitempty"`
}

type Payload struct {
	Status                  string                   `json:"status"`
	Workflow                string                   `json:"workflow,omitempty"`
	WorkflowCanonical       string                   `json:"workflow_canonical,omitempty"`
	UpdateMode              string                   `json:"update_mode,omitempty"`
	DeltaSessionID          *string                  `json:"delta_session_id,omitempty"`
	PayloadPath             string                   `json:"payload_path,omitempty"`
	UpdateCommand           string                   `json:"update_command,omitempty"`
	DeltaAppendCommand      string                   `json:"delta_append_command,omitempty"`
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
	Workflow             string               `json:"workflow"`
	Reason               string               `json:"reason"`
	ChangedPaths         []string             `json:"changed_paths"`
	ScopePaths           []string             `json:"scope_paths"`
	BehaviorSurfaces     []string             `json:"behavior_surfaces"`
	GeneratedSurfaces    []string             `json:"generated_surfaces"`
	GeneratedSurfaceNote []string             `json:"generated_surface_notes"`
	StateContracts       []string             `json:"state_contracts"`
	Verification         []VerificationRecord `json:"verification"`
	VerificationEvidence []VerificationRecord `json:"verification_evidence"`
	KnownUnknowns        []string             `json:"known_unknowns"`
	ConfidenceNotes      []string             `json:"confidence_notes"`
	UserDecisions        []string             `json:"user_decisions"`
	Boundary             BoundaryDraft        `json:"boundary"`
	PayloadPath          string               `json:"payload_path"`
	UpdateCommand        string               `json:"update_command"`
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
}

func Run(paths rt.Paths, input Input) (Payload, error) {
	workflow, err := CanonicalWorkflow(input.Workflow)
	if err != nil {
		return Payload{
			Status:              statusBlocked,
			Workflow:            strings.TrimSpace(input.Workflow),
			RequiredAgentFields: []string{},
			KnownPaths:          []string{},
			UnknownPaths:        []string{},
			Errors:              []string{err.Error()},
			Warnings:            []string{},
		}, nil
	}

	changePayload, err := changes.Run(paths, changes.Input{
		Since:              input.Since,
		Head:               input.Head,
		IncludeWorkingTree: input.IncludeWorkingTree,
		IncludeUntracked:   input.IncludeUntracked,
		ExplicitPaths:      input.ExplicitPaths,
		Intent:             workflow,
	})
	if err != nil {
		return Payload{}, err
	}

	payload := Payload{
		Status:                  changePayload.Status,
		Workflow:                workflow,
		WorkflowCanonical:       workflow,
		RequiredAgentFields:     requiredAgentFields(changePayload.UnknownPaths),
		KnownPaths:              knownPaths(changePayload.Changes),
		UnknownPaths:            append([]string{}, changePayload.UnknownPaths...),
		UnknownPathDispositions: unknownPathDispositions(changePayload.Changes),
		Changes:                 append([]changes.Change{}, changePayload.Changes...),
		ChangeSummary:           changePayload.Summary,
		Warnings:                append([]string{}, changePayload.Warnings...),
		Errors:                  append([]string{}, changePayload.Errors...),
	}

	if payload.Status != statusOK {
		return payload, nil
	}

	changedPaths := changedPaths(changePayload.Changes)
	if strings.TrimSpace(input.DeltaSessionID) != "" {
		sessionID := strings.TrimSpace(input.DeltaSessionID)
		payload.UpdateMode = modeDeltaSession
		payload.DeltaSessionID = &sessionID
		payload.DeltaAppendCommand = deltaAppendCommand(sessionID, workflow, changedPaths)
		payload.UpdateCommand = fmt.Sprintf("project-cognition update --delta-session %s --reason %s --format json", quoteArg(sessionID), closeoutReason)
		payload.RecommendedNextCommand = "append_delta_then_update"
		return payload, nil
	}

	payloadPath := normalizePayloadPath(input.PayloadPath, workflow)
	updateCommand := fmt.Sprintf("project-cognition update --payload-file %s --reason %s --format json", quoteArg(payloadPath), closeoutReason)
	payload.UpdateMode = modePayloadFile
	payload.PayloadPath = payloadPath
	payload.UpdateCommand = updateCommand
	payload.RecommendedNextCommand = "write_payload_then_update"
	payload.PayloadDraft = &PayloadDraft{
		Workflow:             workflow,
		Reason:               closeoutReason,
		ChangedPaths:         changedPaths,
		ScopePaths:           append([]string{}, changedPaths...),
		BehaviorSurfaces:     []string{},
		GeneratedSurfaces:    []string{},
		GeneratedSurfaceNote: []string{},
		StateContracts:       []string{},
		Verification:         []VerificationRecord{},
		VerificationEvidence: []VerificationRecord{},
		KnownUnknowns:        []string{},
		ConfidenceNotes:      []string{},
		UserDecisions:        []string{},
		Boundary: BoundaryDraft{
			InitialDirtyPaths:  []string{},
			WorkflowOwnedPaths: []string{},
		},
		PayloadPath:   payloadPath,
		UpdateCommand: updateCommand,
	}
	return payload, nil
}

func CanonicalWorkflow(value string) (string, error) {
	normalized := strings.ToLower(strings.TrimSpace(value))
	normalized = strings.TrimPrefix(normalized, "/")
	normalized = strings.ReplaceAll(normalized, ".", "-")
	normalized = strings.ReplaceAll(normalized, "_", "-")
	if normalized == "" {
		return "", fmt.Errorf("unknown workflow %q: expected a supported sp-* workflow such as sp-implement or sp-quick", value)
	}
	if !strings.HasPrefix(normalized, "sp-") {
		normalized = "sp-" + normalized
	}
	if _, ok := knownWorkflows[normalized]; !ok {
		return "", fmt.Errorf("unknown workflow %q: expected a supported sp-* workflow such as sp-implement or sp-quick", value)
	}
	return normalized, nil
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
	out := make([]string, 0, len(items))
	for _, item := range items {
		out = append(out, item.Path)
	}
	return sortedUnique(out)
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

func normalizePayloadPath(value string, workflow string) string {
	value = filepath.ToSlash(strings.TrimSpace(value))
	if value != "" {
		return value
	}
	return ".specify/project-cognition/updates/" + workflow + "-closeout.json"
}

func deltaAppendCommand(sessionID string, workflow string, paths []string) string {
	parts := []string{
		"project-cognition",
		"delta",
		"append",
		"--session",
		quoteArg(sessionID),
		"--event-type",
		"workflow_closeout",
		"--origin-command",
		quoteArg(workflow),
		"--phase",
		"closeout",
	}
	for _, path := range paths {
		parts = append(parts, "--changed-path", quoteArg(path))
	}
	parts = append(parts, "--format", "json")
	return strings.Join(parts, " ")
}

func quoteArg(value string) string {
	return strconv.Quote(value)
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

package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

const workflowStateSchemaVersion = 1

var workflowStageOrder = []string{"discussion", "specify", "plan", "tasks", "implement", "review", "accept"}

var workflowStateKeys = []string{
	"acceptance_sha256",
	"blocker",
	"feature_id",
	"last_blocker_resolution",
	"last_reopen",
	"last_resolution_evidence",
	"revision",
	"schema_version",
	"stage",
	"status",
	"summary",
}

type WorkflowService struct {
	projectRoot                string
	beforeCloseoutStateWrite   func() error
	beforeWorkflowStateWrite   func() error
	workflowArtifactGateRunner func(workflowFeature, string) Envelope
}

type WorkflowEnterRequest struct {
	FeatureDir       string
	FeatureID        string
	Command          string
	ExpectedRevision int
	Summary          string
}

type WorkflowShowRequest struct {
	FeatureDir string
	FeatureID  string
}

type WorkflowCompleteStageRequest struct {
	FeatureDir       string
	FeatureID        string
	ExpectedRevision int
	Summary          string
}

type WorkflowTransitionRequest struct {
	FeatureDir       string
	FeatureID        string
	To               string
	ExpectedRevision int
	Summary          string
}

type WorkflowReopenRequest struct {
	FeatureDir           string
	FeatureID            string
	To                   string
	ExpectedRevision     int
	Reason               string
	Evidence             []string
	InvalidatedArtifacts []string
	RepairRoute          string
	FindingID            string
}

type WorkflowResolveRequest struct {
	FeatureDir         string
	FeatureID          string
	ExpectedRevision   int
	ResolutionEvidence []string
	Summary            string
}

type WorkflowCloseoutRequest struct {
	FeatureDir       string
	FeatureID        string
	ExpectedRevision int
	Summary          string
}

type workflowFeature struct {
	ID  string
	Abs string
	Rel string
}

type workflowState struct {
	SchemaVersion          int            `json:"schema_version"`
	FeatureID              string         `json:"feature_id"`
	Revision               int            `json:"revision"`
	Stage                  string         `json:"stage"`
	Status                 string         `json:"status"`
	Summary                string         `json:"summary"`
	Blocker                map[string]any `json:"blocker"`
	LastResolutionEvidence []string       `json:"last_resolution_evidence"`
	LastReopen             map[string]any `json:"last_reopen"`
	LastBlockerResolution  map[string]any `json:"last_blocker_resolution"`
	AcceptanceSHA256       *string        `json:"acceptance_sha256"`
}

func NewWorkflowService(projectRoot string) *WorkflowService {
	return &WorkflowService{projectRoot: projectRoot}
}

func (service *WorkflowService) Enter(request WorkflowEnterRequest) Envelope {
	feature, err := service.resolveFeature(request.FeatureDir, request.FeatureID)
	if err != nil {
		return workflowInvalid("workflow feature directory is invalid", "invalid-feature-dir", err)
	}
	command := strings.ToLower(strings.TrimSpace(request.Command))
	if command == "" {
		command = "specify"
	}
	if command != "discussion" && command != "specify" {
		return workflowInvalid("workflow entry stage is invalid", "invalid-entry-stage", fmt.Errorf("entry command must be discussion or specify"))
	}
	if request.ExpectedRevision != 0 {
		return workflowRevisionConflict(feature, request.ExpectedRevision, 0)
	}

	release, env, ok := service.acquireWorkflowLock(feature)
	if !ok {
		return env
	}
	defer release()

	state, err := service.readState(feature)
	if err == nil {
		env := workflowBlocked("workflow state already exists", "workflow-already-entered", "read the current state instead of resetting its revision")
		addWorkflowStateData(&env, state)
		env.ShowArgv = workflowShowArgv(feature)
		env.NextArgv = workflowNextArgv(feature)
		return env
	}
	if !os.IsNotExist(err) {
		return service.stateReadFailure(feature, err)
	}

	summary := strings.TrimSpace(request.Summary)
	if summary == "" {
		summary = fmt.Sprintf("Entered workflow at %s.", command)
	}
	state = workflowState{
		SchemaVersion:          workflowStateSchemaVersion,
		FeatureID:              feature.ID,
		Revision:               1,
		Stage:                  command,
		Status:                 "active",
		Summary:                summary,
		Blocker:                nil,
		LastResolutionEvidence: []string{},
		LastReopen:             nil,
		LastBlockerResolution:  nil,
		AcceptanceSHA256:       nil,
	}
	if err := service.writeState(feature, state); err != nil {
		return workflowError("failed to write workflow state", err)
	}
	env = NewEnvelope("ok", "workflow entered")
	addWorkflowStateData(&env, state)
	env.ShowArgv = workflowShowArgv(feature)
	env.NextArgv = workflowCompleteArgv(feature, state.Revision)
	return env
}

func (service *WorkflowService) Show(request WorkflowShowRequest) Envelope {
	feature, err := service.resolveFeature(request.FeatureDir, request.FeatureID)
	if err != nil {
		return workflowInvalid("workflow feature directory is invalid", "invalid-feature-dir", err)
	}
	state, err := service.readState(feature)
	if err != nil {
		return service.stateReadFailure(feature, err)
	}
	env := NewEnvelope("ok", "workflow state read")
	addWorkflowStateData(&env, state)
	env.ShowArgv = workflowShowArgv(feature)
	if state.Status == "blocked" {
		env.Status = "blocked"
		env.Summary = state.Summary
		env.Blockers = append(env.Blockers, cloneMap(state.Blocker))
		env.Data["resolution_action"] = workflowResolutionAction(feature, state.Revision)
		return env
	}
	if !isTerminalWorkflowState(state) {
		env.NextArgv = workflowNextArgv(feature)
	}
	return env
}

func (service *WorkflowService) Next(request WorkflowShowRequest) Envelope {
	feature, err := service.resolveFeature(request.FeatureDir, request.FeatureID)
	if err != nil {
		return workflowInvalid("workflow feature directory is invalid", "invalid-feature-dir", err)
	}
	state, err := service.readState(feature)
	if err != nil {
		return service.stateReadFailure(feature, err)
	}
	env := NewEnvelope("ok", "workflow next action resolved")
	addWorkflowStateData(&env, state)
	env.ShowArgv = workflowShowArgv(feature)
	if state.Status == "blocked" {
		env.Status = "blocked"
		env.Summary = state.Summary
		env.Blockers = append(env.Blockers, cloneMap(state.Blocker))
		env.Data["resolution_action"] = workflowResolutionAction(feature, state.Revision)
		return env
	}
	nextStage := nextWorkflowStage(state.Stage)
	if nextStage != "" {
		env.Data["next_stage"] = nextStage
	}
	switch state.Status {
	case "active":
		if state.Stage == "accept" {
			env.NextArgv = workflowCloseoutArgv(feature, state.Revision)
		} else {
			env.NextArgv = workflowCompleteArgv(feature, state.Revision)
		}
	case "completed":
		if state.Stage != "accept" {
			env.NextArgv = workflowTransitionArgv(feature, nextStage, state.Revision)
		}
	}
	return env
}

func (service *WorkflowService) CompleteStage(request WorkflowCompleteStageRequest) Envelope {
	feature, err := service.resolveFeature(request.FeatureDir, request.FeatureID)
	if err != nil {
		return workflowInvalid("workflow feature directory is invalid", "invalid-feature-dir", err)
	}
	release, env, ok := service.acquireWorkflowLock(feature)
	if !ok {
		return env
	}
	defer release()
	state, err := service.readState(feature)
	if err != nil {
		return service.stateReadFailure(feature, err)
	}
	if request.ExpectedRevision != state.Revision {
		return workflowRevisionConflictWithState(feature, request.ExpectedRevision, state)
	}
	if isTerminalWorkflowState(state) {
		return workflowStateBlocked(feature, state, "terminal workflow is immutable", "terminal-workflow-immutable")
	}
	if state.Status == "blocked" {
		return workflowPersistedBlock(feature, state)
	}
	if state.Status == "completed" {
		env = NewEnvelope("ok", "workflow stage is already completed")
		addWorkflowStateData(&env, state)
		env.ShowArgv = workflowShowArgv(feature)
		env.NextArgv = workflowTransitionArgv(feature, nextWorkflowStage(state.Stage), state.Revision)
		return env
	}
	if state.Stage == "accept" {
		env = workflowStateBlocked(feature, state, "accept may only be completed through workflow closeout", "terminal-stage-requires-closeout")
		env.NextArgv = workflowCloseoutArgv(feature, state.Revision)
		return env
	}
	if state.Stage != "discussion" {
		gate := service.validateStageArtifacts(feature, state.Stage)
		if gate.Status != "ok" && gate.Status != "warn" && gate.Status != "repaired" {
			addWorkflowStateData(&gate, state)
			return gate
		}
	}
	state.Revision++
	state.Status = "completed"
	if summary := strings.TrimSpace(request.Summary); summary != "" {
		state.Summary = summary
	} else {
		state.Summary = fmt.Sprintf("Completed workflow stage %s.", state.Stage)
	}
	if err := service.writeState(feature, state); err != nil {
		return workflowError("failed to write workflow state", err)
	}
	env = NewEnvelope("ok", "workflow stage completed")
	addWorkflowStateData(&env, state)
	env.ShowArgv = workflowShowArgv(feature)
	env.NextArgv = workflowTransitionArgv(feature, nextWorkflowStage(state.Stage), state.Revision)
	return env
}

func (service *WorkflowService) Transition(request WorkflowTransitionRequest) Envelope {
	feature, err := service.resolveFeature(request.FeatureDir, request.FeatureID)
	if err != nil {
		return workflowInvalid("workflow feature directory is invalid", "invalid-feature-dir", err)
	}
	target := strings.ToLower(strings.TrimSpace(request.To))
	if !validWorkflowStage(target) {
		return workflowInvalid("workflow transition target is invalid", "invalid-transition", fmt.Errorf("unknown stage %q", request.To))
	}
	release, env, ok := service.acquireWorkflowLock(feature)
	if !ok {
		return env
	}
	defer release()
	state, err := service.readState(feature)
	if err != nil {
		return service.stateReadFailure(feature, err)
	}
	if request.ExpectedRevision != state.Revision {
		return workflowRevisionConflictWithState(feature, request.ExpectedRevision, state)
	}
	if isTerminalWorkflowState(state) {
		return workflowStateBlocked(feature, state, "terminal workflow is immutable", "terminal-workflow-immutable")
	}
	if state.Status == "blocked" {
		return workflowPersistedBlock(feature, state)
	}
	if state.Status != "completed" {
		env = workflowStateBlocked(feature, state, "source workflow stage is not completed", "source-stage-not-completed")
		env.NextArgv = workflowCompleteArgv(feature, state.Revision)
		return env
	}
	expectedTarget := nextWorkflowStage(state.Stage)
	if target != expectedTarget {
		env = workflowStateBlocked(feature, state, fmt.Sprintf("cannot transition from %s to %s", state.Stage, target), "invalid-transition")
		if expectedTarget != "" {
			env.NextArgv = workflowTransitionArgv(feature, expectedTarget, state.Revision)
		}
		return env
	}
	if state.Stage != "discussion" {
		gate := service.validateStageArtifacts(feature, state.Stage)
		if gate.Status != "ok" && gate.Status != "warn" && gate.Status != "repaired" {
			addWorkflowStateData(&gate, state)
			return gate
		}
	}
	state.Revision++
	state.Stage = target
	state.Status = "active"
	state.Blocker = nil
	state.AcceptanceSHA256 = nil
	if summary := strings.TrimSpace(request.Summary); summary != "" {
		state.Summary = summary
	} else {
		state.Summary = fmt.Sprintf("Entered workflow stage %s.", target)
	}
	if err := service.writeState(feature, state); err != nil {
		return workflowError("failed to write workflow state", err)
	}
	env = NewEnvelope("ok", "workflow state advanced")
	addWorkflowStateData(&env, state)
	env.ShowArgv = workflowShowArgv(feature)
	if state.Stage == "accept" {
		env.NextArgv = workflowCloseoutArgv(feature, state.Revision)
	} else {
		env.NextArgv = workflowCompleteArgv(feature, state.Revision)
	}
	return env
}

func (service *WorkflowService) Reopen(request WorkflowReopenRequest) Envelope {
	feature, err := service.resolveFeature(request.FeatureDir, request.FeatureID)
	if err != nil {
		return workflowInvalid("workflow feature directory is invalid", "invalid-feature-dir", err)
	}
	target := strings.ToLower(strings.TrimSpace(request.To))
	repairMode := strings.TrimSpace(request.RepairRoute) != "" || strings.TrimSpace(request.FindingID) != ""
	if repairMode {
		if target != "review" {
			return workflowInvalid("acceptance repair target is invalid", "invalid-acceptance-repair-target", fmt.Errorf("acceptance repair target must be review"))
		}
		route := strings.TrimSpace(request.RepairRoute)
		if route != "sp-review" && route != "spx-review" {
			return workflowInvalid("acceptance repair route is invalid", "invalid-acceptance-repair-route", fmt.Errorf("repair route must be sp-review or spx-review"))
		}
		if strings.TrimSpace(request.FindingID) == "" {
			return workflowInvalid("acceptance repair finding is invalid", "invalid-acceptance-repair-finding", fmt.Errorf("finding-id is required"))
		}
		if _, err := requiredWorkflowStrings(request.Evidence, "evidence"); err != nil {
			return workflowInvalid("acceptance repair evidence is invalid", "invalid-acceptance-repair-evidence", err)
		}
	} else {
		if !reopenableWorkflowStage(target) {
			return workflowInvalid("workflow reopen target is invalid", "invalid-reopen-target", fmt.Errorf("target must be specify, plan, tasks, implement, or review"))
		}
		if strings.TrimSpace(request.Reason) == "" {
			return workflowInvalid("workflow reopen reason is invalid", "invalid-reopen-reason", fmt.Errorf("reason is required"))
		}
		if _, err := requiredWorkflowStrings(request.Evidence, "evidence"); err != nil {
			return workflowInvalid("workflow reopen evidence is invalid", "invalid-reopen-evidence", err)
		}
		if _, err := requiredWorkflowStrings(request.InvalidatedArtifacts, "invalidated-artifacts"); err != nil {
			return workflowInvalid("workflow invalidated artifacts are invalid", "invalid-reopen-artifacts", err)
		}
	}

	release, env, ok := service.acquireWorkflowLock(feature)
	if !ok {
		return env
	}
	defer release()
	state, err := service.readState(feature)
	if err != nil {
		return service.stateReadFailure(feature, err)
	}
	if request.ExpectedRevision != state.Revision {
		return workflowRevisionConflictWithState(feature, request.ExpectedRevision, state)
	}
	if isTerminalWorkflowState(state) {
		return workflowStateBlocked(feature, state, "terminal workflow is immutable", "terminal-workflow-immutable")
	}
	if state.Status == "blocked" {
		return workflowPersistedBlock(feature, state)
	}
	if repairMode {
		return service.reopenAcceptanceRepairLocked(feature, state, request)
	}
	if state.Stage == "accept" {
		return workflowStateBlocked(feature, state, "acceptance may only reopen through the acceptance repair transaction", "acceptance-repair-required")
	}
	sourceIndex := workflowStageIndex(state.Stage)
	targetIndex := workflowStageIndex(target)
	if targetIndex > sourceIndex || (targetIndex == sourceIndex && state.Status != "completed") {
		return workflowStateBlocked(feature, state, fmt.Sprintf("cannot reopen %s with %s status to %s", state.Stage, state.Status, target), "invalid-reopen-target")
	}
	evidence, _ := requiredWorkflowStrings(request.Evidence, "evidence")
	invalidated, _ := requiredWorkflowStrings(request.InvalidatedArtifacts, "invalidated-artifacts")
	reason := strings.TrimSpace(request.Reason)
	sourceStage := state.Stage
	sourceStatus := state.Status
	state.Revision++
	state.Stage = target
	state.Status = "active"
	state.Summary = reason
	state.Blocker = nil
	state.AcceptanceSHA256 = nil
	state.LastResolutionEvidence = append(state.LastResolutionEvidence,
		fmt.Sprintf("reopened %s to %s: %s", sourceStage, target, reason))
	state.LastResolutionEvidence = append(state.LastResolutionEvidence, evidence...)
	state.LastReopen = map[string]any{
		"source_stage":          sourceStage,
		"source_status":         sourceStatus,
		"target_stage":          target,
		"reason":                reason,
		"evidence":              evidence,
		"invalidated_artifacts": invalidated,
	}
	if err := service.writeState(feature, state); err != nil {
		return workflowError("failed to write workflow state", err)
	}
	env = NewEnvelope("ok", "workflow stage reopened")
	addWorkflowStateData(&env, state)
	env.ShowArgv = workflowShowArgv(feature)
	env.NextArgv = workflowCompleteArgv(feature, state.Revision)
	return env
}

func (service *WorkflowService) Resolve(request WorkflowResolveRequest) Envelope {
	feature, err := service.resolveFeature(request.FeatureDir, request.FeatureID)
	if err != nil {
		return workflowInvalid("workflow feature directory is invalid", "invalid-feature-dir", err)
	}
	evidence, err := requiredWorkflowStrings(request.ResolutionEvidence, "resolution-evidence")
	if err != nil {
		return workflowInvalid("workflow resolution evidence is invalid", "invalid-resolution-evidence", err)
	}
	release, env, ok := service.acquireWorkflowLock(feature)
	if !ok {
		return env
	}
	defer release()
	state, err := service.readState(feature)
	if err != nil {
		return service.stateReadFailure(feature, err)
	}
	if request.ExpectedRevision != state.Revision {
		return workflowRevisionConflictWithState(feature, request.ExpectedRevision, state)
	}
	if state.Status != "blocked" || state.Blocker == nil {
		return workflowStateBlocked(feature, state, "workflow resolve requires a persisted blocker", "no-blocker-to-resolve")
	}
	summary := strings.TrimSpace(request.Summary)
	if summary == "" {
		summary = fmt.Sprintf("Resolved blocker %v.", state.Blocker["blocker_id"])
	}
	oldBlocker := cloneMap(state.Blocker)
	state.Revision++
	state.Status = "active"
	state.Summary = summary
	state.Blocker = nil
	state.LastResolutionEvidence = append(state.LastResolutionEvidence, evidence...)
	state.LastBlockerResolution = map[string]any{
		"blocker":             oldBlocker,
		"stage":               state.Stage,
		"summary":             summary,
		"resolved_revision":   state.Revision,
		"resolution_evidence": evidence,
	}
	if err := service.writeState(feature, state); err != nil {
		return workflowError("failed to write workflow state", err)
	}
	env = NewEnvelope("ok", "workflow blocker resolved")
	addWorkflowStateData(&env, state)
	env.ShowArgv = workflowShowArgv(feature)
	if state.Stage == "accept" {
		env.NextArgv = workflowCloseoutArgv(feature, state.Revision)
	} else {
		env.NextArgv = workflowCompleteArgv(feature, state.Revision)
	}
	return env
}

func (service *WorkflowService) reopenAcceptanceRepairLocked(feature workflowFeature, state workflowState, request WorkflowReopenRequest) Envelope {
	if state.Stage != "accept" || state.Status != "active" {
		return workflowStateBlocked(feature, state, "acceptance repair requires active accept", "invalid-acceptance-repair-stage")
	}
	if err := service.validateAcceptanceRepairTransaction(feature, state.Revision, strings.TrimSpace(request.RepairRoute), strings.TrimSpace(request.FindingID)); err != nil {
		return workflowStateBlocked(feature, state, "acceptance repair transaction is not ready", "acceptance-repair-transaction-invalid", err.Error())
	}
	evidence, _ := requiredWorkflowStrings(request.Evidence, "evidence")
	sourceStatus := state.Status
	state.Revision++
	state.Stage = "review"
	state.Status = "active"
	state.Summary = fmt.Sprintf("Acceptance finding %s reopened review.", strings.TrimSpace(request.FindingID))
	state.Blocker = nil
	state.AcceptanceSHA256 = nil
	state.LastResolutionEvidence = append(state.LastResolutionEvidence,
		fmt.Sprintf("acceptance finding %s routed to %s", strings.TrimSpace(request.FindingID), strings.TrimSpace(request.RepairRoute)))
	state.LastResolutionEvidence = append(state.LastResolutionEvidence, evidence...)
	state.LastReopen = map[string]any{
		"source_stage":          "accept",
		"source_status":         sourceStatus,
		"target_stage":          "review",
		"repair_route":          strings.TrimSpace(request.RepairRoute),
		"finding_id":            strings.TrimSpace(request.FindingID),
		"reason":                fmt.Sprintf("Acceptance finding %s routed to %s", strings.TrimSpace(request.FindingID), strings.TrimSpace(request.RepairRoute)),
		"evidence":              evidence,
		"invalidated_artifacts": []string{"human-acceptance.json verdict", "review and downstream artifacts"},
	}
	if err := service.writeState(feature, state); err != nil {
		return workflowError("failed to write workflow state", err)
	}
	env := NewEnvelope("ok", "acceptance repair routed")
	addWorkflowStateData(&env, state)
	env.Data["reopened_from"] = "accept"
	env.Data["repair_route"] = strings.TrimSpace(request.RepairRoute)
	env.Data["finding_id"] = strings.TrimSpace(request.FindingID)
	env.Data["handoff_command"] = strings.TrimSpace(request.RepairRoute)
	env.ShowArgv = workflowShowArgv(feature)
	return env
}

func (service *WorkflowService) validateAcceptanceRepairTransaction(feature workflowFeature, revision int, route, findingID string) error {
	acceptancePath, err := secureProjectPath(service.projectRoot, feature.Rel+"/human-acceptance.json")
	if err != nil {
		return err
	}
	acceptanceRaw, err := os.ReadFile(acceptancePath)
	if err != nil {
		return fmt.Errorf("read invalidated acceptance: %w", err)
	}
	var acceptance map[string]any
	if err := json.Unmarshal(acceptanceRaw, &acceptance); err != nil {
		return fmt.Errorf("parse invalidated acceptance: %w", err)
	}
	if acceptance["status"] != "draft" {
		return fmt.Errorf("human-acceptance status must be draft")
	}
	repairResume, ok := acceptance["repair_resume"].(map[string]any)
	if !ok || repairResume["finding_id"] != findingID {
		return fmt.Errorf("repair_resume.finding_id does not match")
	}
	overall, ok := acceptance["overall"].(map[string]any)
	if !ok || overall["verdict"] != "pending" || overall["next_command"] != route {
		return fmt.Errorf("overall verdict or next_command does not match")
	}

	journalPath, err := secureProjectPath(service.projectRoot, feature.Rel+"/.human-acceptance-repair.json")
	if err != nil {
		return err
	}
	journalRaw, err := os.ReadFile(journalPath)
	if err != nil {
		return fmt.Errorf("read acceptance transaction journal: %w", err)
	}
	var journal map[string]any
	if err := json.Unmarshal(journalRaw, &journal); err != nil {
		return fmt.Errorf("parse acceptance transaction journal: %w", err)
	}
	if journal["version"] != float64(1) || journal["phase"] != "acceptance-invalidated" || journal["route"] != route || journal["finding_id"] != findingID || journal["target_stage"] != "review" || journal["acceptance_file"] != "human-acceptance.json" {
		return fmt.Errorf("acceptance transaction journal does not match repair request")
	}
	expectedRevision, ok := jsonInteger(journal["expected_revision"])
	if !ok || expectedRevision != revision {
		return fmt.Errorf("acceptance transaction revision does not match")
	}
	wantDigest, _ := journal["invalidated_acceptance_sha256"].(string)
	actualDigest := fmt.Sprintf("%x", sha256.Sum256(acceptanceRaw))
	if wantDigest != actualDigest {
		return fmt.Errorf("invalidated acceptance digest does not match journal")
	}
	return nil
}

func (service *WorkflowService) resolveFeature(featureDir, featureID string) (workflowFeature, error) {
	var feature workflowFeature
	root, err := filepath.Abs(service.projectRoot)
	if err != nil {
		return feature, err
	}
	root, err = filepath.EvalSymlinks(root)
	if err != nil {
		return feature, fmt.Errorf("resolve project root: %w", err)
	}
	featuresRoot := filepath.Join(root, ".specify", "features")
	requested := strings.TrimSpace(featureDir)
	if requested == "" {
		if !safeSegment(featureID) {
			return feature, fmt.Errorf("feature id %q must be a safe path segment", featureID)
		}
		requested = filepath.Join(featuresRoot, featureID)
	} else if filepath.IsAbs(requested) || filepath.VolumeName(requested) != "" {
		requested, err = filepath.Abs(requested)
		if err != nil {
			return feature, err
		}
	} else {
		requested = filepath.Join(root, filepath.FromSlash(requested))
	}
	requested = filepath.Clean(requested)
	relToFeatures, err := filepath.Rel(featuresRoot, requested)
	if err != nil || relToFeatures == "." || relToFeatures == ".." || strings.HasPrefix(relToFeatures, ".."+string(filepath.Separator)) || strings.Contains(relToFeatures, string(filepath.Separator)) {
		return feature, fmt.Errorf("feature directory must be a direct child of .specify/features")
	}
	id := filepath.Base(relToFeatures)
	if !safeSegment(id) {
		return feature, fmt.Errorf("feature id %q must be a safe path segment", id)
	}
	if strings.TrimSpace(featureID) != "" && !samePathSegment(featureID, id) {
		return feature, fmt.Errorf("feature id %q does not match feature directory %q", featureID, id)
	}
	rel := filepath.ToSlash(filepath.Join(".specify", "features", id))
	secure, err := secureProjectPath(root, rel)
	if err != nil {
		return feature, err
	}
	if !sameFilesystemPath(secure, requested) {
		return feature, fmt.Errorf("feature directory does not resolve to the canonical project feature path")
	}
	info, err := os.Stat(secure)
	if err != nil {
		return feature, fmt.Errorf("feature directory is unavailable: %w", err)
	}
	if !info.IsDir() {
		return feature, fmt.Errorf("feature path is not a directory")
	}
	feature.ID = id
	feature.Abs = secure
	feature.Rel = rel
	return feature, nil
}

func samePathSegment(left, right string) bool {
	if filepath.Separator == '\\' {
		return strings.EqualFold(left, right)
	}
	return left == right
}

func sameFilesystemPath(left, right string) bool {
	rel, err := filepath.Rel(left, right)
	return err == nil && rel == "."
}

func (service *WorkflowService) statePath(feature workflowFeature) (string, error) {
	return secureProjectPath(service.projectRoot, feature.Rel+"/workflow.json")
}

func (service *WorkflowService) workflowLockPath(feature workflowFeature) (string, error) {
	return secureProjectPath(service.projectRoot, feature.Rel+"/.workflow.lock")
}

func (service *WorkflowService) acquireWorkflowLock(feature workflowFeature) (func(), Envelope, bool) {
	path, err := service.workflowLockPath(feature)
	if err != nil {
		return nil, workflowBlocked("workflow lock path is unavailable", "workflow-lock-unavailable", err.Error()), false
	}
	release, err := filelock.Acquire(path)
	if err != nil {
		return nil, workflowError("failed to acquire workflow lock", err), false
	}
	return release, Envelope{}, true
}

func (service *WorkflowService) readState(feature workflowFeature) (workflowState, error) {
	var state workflowState
	path, err := service.statePath(feature)
	if err != nil {
		return state, err
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return state, err
	}
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(raw, &fields); err != nil {
		return state, fmt.Errorf("parse workflow state: %w", err)
	}
	keys := make([]string, 0, len(fields))
	for key := range fields {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	if !equalStrings(keys, workflowStateKeys) {
		return state, fmt.Errorf("workflow state fields are invalid: got %v", keys)
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&state); err != nil {
		return state, fmt.Errorf("decode workflow state: %w", err)
	}
	if err := ensureJSONEOF(decoder); err != nil {
		return state, err
	}
	if err := validateWorkflowState(feature, state); err != nil {
		return state, err
	}
	return state, nil
}

func validateWorkflowState(feature workflowFeature, state workflowState) error {
	if state.SchemaVersion != workflowStateSchemaVersion {
		return fmt.Errorf("unsupported schema_version %d", state.SchemaVersion)
	}
	if !samePathSegment(state.FeatureID, feature.ID) {
		return fmt.Errorf("feature_id %q does not match directory %q", state.FeatureID, feature.ID)
	}
	if state.Revision < 1 {
		return fmt.Errorf("revision must be a positive integer")
	}
	if !validWorkflowStage(state.Stage) {
		return fmt.Errorf("invalid workflow stage %q", state.Stage)
	}
	if state.Status != "active" && state.Status != "blocked" && state.Status != "completed" {
		return fmt.Errorf("invalid workflow status %q", state.Status)
	}
	if strings.TrimSpace(state.Summary) == "" {
		return fmt.Errorf("workflow summary must be a non-empty string")
	}
	if state.LastResolutionEvidence == nil {
		return fmt.Errorf("last_resolution_evidence must be an array")
	}
	for index, value := range state.LastResolutionEvidence {
		if strings.TrimSpace(value) == "" {
			return fmt.Errorf("last_resolution_evidence[%d] must be non-empty", index)
		}
	}
	if state.Status == "blocked" {
		if err := validatePersistedWorkflowBlocker(feature, state); err != nil {
			return err
		}
	} else if state.Blocker != nil {
		return fmt.Errorf("non-blocked workflow state must have null blocker")
	}
	if state.AcceptanceSHA256 != nil {
		digest := *state.AcceptanceSHA256
		if !isLowerSHA256(digest) || !isTerminalWorkflowState(state) {
			return fmt.Errorf("acceptance_sha256 is only valid for completed accept")
		}
	} else if isTerminalWorkflowState(state) {
		return fmt.Errorf("completed accept requires acceptance_sha256")
	}
	return nil
}

func (service *WorkflowService) writeState(feature workflowFeature, state workflowState) error {
	if err := validateWorkflowState(feature, state); err != nil {
		return err
	}
	if service.beforeWorkflowStateWrite != nil {
		if err := service.beforeWorkflowStateWrite(); err != nil {
			return err
		}
	}
	path, err := service.statePath(feature)
	if err != nil {
		return err
	}
	raw, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}
	return atomicWriteFile(path, append(raw, '\n'), 0o644)
}

func (service *WorkflowService) stateReadFailure(feature workflowFeature, err error) Envelope {
	if os.IsNotExist(err) {
		env := workflowBlocked("workflow state is missing", "missing-workflow-state", feature.Rel+"/workflow.json does not exist")
		env.Data["path"] = feature.Rel + "/workflow.json"
		env.NextArgv = workflowEnterArgv(feature, "specify")
		return env
	}
	env := workflowBlocked("workflow state is invalid", "invalid-workflow-runtime", err.Error())
	env.ShowArgv = workflowShowArgv(feature)
	return env
}

func addWorkflowStateData(env *Envelope, state workflowState) {
	env.Data["schema_version"] = state.SchemaVersion
	env.Data["feature_id"] = state.FeatureID
	env.Data["revision"] = state.Revision
	env.Data["stage"] = state.Stage
	env.Data["status"] = state.Status
	env.Data["summary"] = state.Summary
	if state.Blocker == nil {
		env.Data["blocker"] = nil
	} else {
		env.Data["blocker"] = cloneMap(state.Blocker)
	}
	env.Data["last_resolution_evidence"] = append([]string{}, state.LastResolutionEvidence...)
	if state.LastReopen == nil {
		env.Data["last_reopen"] = nil
	} else {
		env.Data["last_reopen"] = cloneMap(state.LastReopen)
	}
	if state.LastBlockerResolution == nil {
		env.Data["last_blocker_resolution"] = nil
	} else {
		env.Data["last_blocker_resolution"] = cloneMap(state.LastBlockerResolution)
	}
	if state.AcceptanceSHA256 == nil {
		env.Data["acceptance_sha256"] = nil
	} else {
		env.Data["acceptance_sha256"] = *state.AcceptanceSHA256
	}
}

func workflowInvalid(summary, code string, err error) Envelope {
	env := NewEnvelope("invalid", summary)
	env.Data["error_code"] = code
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}

func workflowBlocked(summary, code string, details ...string) Envelope {
	env := NewEnvelope("blocked", summary)
	env.Data["error_code"] = code
	for _, detail := range details {
		if strings.TrimSpace(detail) != "" {
			env.Blockers = append(env.Blockers, detail)
		}
	}
	return env
}

func workflowError(summary string, err error) Envelope {
	env := NewEnvelope("error", summary)
	env.Data["error_code"] = "workflow-runtime-error"
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}

func workflowRevisionConflict(feature workflowFeature, expected, actual int) Envelope {
	env := workflowBlocked("workflow revision is stale", "revision-conflict", fmt.Sprintf("expected revision %d but current revision is %d", expected, actual))
	env.Data["expected_revision"] = expected
	env.Data["actual_revision"] = actual
	env.ShowArgv = workflowShowArgv(feature)
	return env
}

func workflowRevisionConflictWithState(feature workflowFeature, expected int, state workflowState) Envelope {
	env := workflowRevisionConflict(feature, expected, state.Revision)
	addWorkflowStateData(&env, state)
	env.Data["error_code"] = "revision-conflict"
	if state.Status == "blocked" && state.Blocker != nil {
		env.Blockers = []any{cloneMap(state.Blocker)}
		env.Data["resolution_action"] = workflowResolutionAction(feature, state.Revision)
		env.NextArgv = []string{}
	}
	return env
}

func workflowStateBlocked(feature workflowFeature, state workflowState, summary, code string, details ...string) Envelope {
	env := workflowBlocked(summary, code, details...)
	addWorkflowStateData(&env, state)
	env.Data["error_code"] = code
	env.ShowArgv = workflowShowArgv(feature)
	if state.Status == "blocked" && state.Blocker != nil {
		env.Blockers = []any{cloneMap(state.Blocker)}
		env.Data["resolution_action"] = workflowResolutionAction(feature, state.Revision)
		env.NextArgv = []string{}
	}
	return env
}

func workflowPersistedBlock(feature workflowFeature, state workflowState) Envelope {
	env := workflowStateBlocked(feature, state, state.Summary, "blocked-stage-requires-resolution")
	env.Data["error_code"] = "blocked-stage-requires-resolution"
	return env
}

func workflowArgv(feature workflowFeature, command string, args ...string) []string {
	argv := []string{"specify-runtime", "workflow", command, "--feature-dir", feature.Rel}
	argv = append(argv, args...)
	argv = append(argv, "--format", "json")
	return argv
}

func workflowShowArgv(feature workflowFeature) []string {
	return workflowArgv(feature, "show")
}

func workflowNextArgv(feature workflowFeature) []string {
	return workflowArgv(feature, "next")
}

func workflowEnterArgv(feature workflowFeature, command string) []string {
	return workflowArgv(feature, "enter", "--command", command, "--expected-revision", "0")
}

func workflowCompleteArgv(feature workflowFeature, revision int) []string {
	return workflowArgv(feature, "complete-stage", "--expected-revision", strconv.Itoa(revision))
}

func workflowTransitionArgv(feature workflowFeature, target string, revision int) []string {
	if target == "" {
		return []string{}
	}
	return workflowArgv(feature, "transition", "--to", target, "--expected-revision", strconv.Itoa(revision))
}

func workflowCloseoutArgv(feature workflowFeature, revision int) []string {
	return workflowArgv(feature, "closeout", "--expected-revision", strconv.Itoa(revision))
}

func workflowResolutionAction(feature workflowFeature, revision int) map[string]any {
	return map[string]any{
		"capability_id": "workflow.resolve",
		"base_argv":     stringValuesAsAny(workflowArgv(feature, "resolve", "--expected-revision", strconv.Itoa(revision))),
		"required_inputs": []any{
			map[string]any{
				"field":      "resolution_evidence",
				"flag":       "--resolution-evidence",
				"repeatable": true,
				"min_items":  1,
				"source":     "sanitized evidence satisfying unblock_criteria",
			},
		},
	}
}

func validWorkflowStage(stage string) bool {
	return workflowStageIndex(stage) >= 0
}

func workflowStageIndex(stage string) int {
	for index, known := range workflowStageOrder {
		if stage == known {
			return index
		}
	}
	return -1
}

func reopenableWorkflowStage(stage string) bool {
	return stage == "specify" || stage == "plan" || stage == "tasks" || stage == "implement" || stage == "review"
}

func nextWorkflowStage(stage string) string {
	index := workflowStageIndex(stage)
	if index < 0 || index+1 >= len(workflowStageOrder) {
		return ""
	}
	return workflowStageOrder[index+1]
}

func isTerminalWorkflowState(state workflowState) bool {
	return state.Stage == "accept" && state.Status == "completed"
}

func requiredWorkflowStrings(values []string, field string) ([]string, error) {
	normalized := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" {
			normalized = append(normalized, value)
		}
	}
	if len(normalized) == 0 {
		return nil, fmt.Errorf("%s must contain at least one value", field)
	}
	return normalized, nil
}

func cloneMap(value map[string]any) map[string]any {
	if value == nil {
		return nil
	}
	raw, err := json.Marshal(value)
	if err != nil {
		return value
	}
	var cloned map[string]any
	if err := json.Unmarshal(raw, &cloned); err != nil {
		return value
	}
	return cloned
}

func equalStrings(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func ensureJSONEOF(decoder *json.Decoder) error {
	var extra any
	if err := decoder.Decode(&extra); err == io.EOF {
		return nil
	} else if err != nil {
		return err
	}
	return fmt.Errorf("unexpected trailing JSON value")
}

func jsonInteger(value any) (int, bool) {
	switch number := value.(type) {
	case float64:
		integer := int(number)
		return integer, number == float64(integer)
	case json.Number:
		integer, err := strconv.Atoi(number.String())
		return integer, err == nil
	case int:
		return number, true
	default:
		return 0, false
	}
}

func isLowerSHA256(value string) bool {
	if len(value) != 64 {
		return false
	}
	for _, char := range value {
		if (char < '0' || char > '9') && (char < 'a' || char > 'f') {
			return false
		}
	}
	return true
}

func validatePersistedWorkflowBlocker(feature workflowFeature, state workflowState) error {
	blocker := state.Blocker
	if blocker == nil {
		return fmt.Errorf("blocked workflow state requires a blocker object")
	}
	required := []string{
		"version", "blocker_id", "workflow", "stage", "category", "owner", "summary", "details",
		"evidence", "attempted_recovery", "exact_next_action", "unblock_criteria", "affected_scope",
		"can_continue", "human_action_required", "human_action_guide", "resume",
	}
	keys := make([]string, 0, len(blocker))
	for key := range blocker {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	sort.Strings(required)
	if !equalStrings(keys, required) {
		return fmt.Errorf("persisted blocker fields are invalid")
	}
	if version, ok := jsonInteger(blocker["version"]); !ok || version != 1 {
		return fmt.Errorf("persisted blocker version is invalid")
	}
	category, categoryOK := blocker["category"].(string)
	owner, ownerOK := blocker["owner"].(string)
	if !categoryOK || !workflowBlockerCategories[category] || !ownerOK || !workflowBlockerOwners[owner] {
		return fmt.Errorf("persisted blocker category or owner is invalid")
	}
	expectedID := fmt.Sprintf("workflow-%s-%s-r%d", workflowSlug(state.Stage), workflowSlug(category), state.Revision)
	if blocker["blocker_id"] != expectedID || blocker["workflow"] != state.Stage || blocker["stage"] != state.Stage || blocker["can_continue"] != false {
		return fmt.Errorf("persisted blocker stage or continuation flag is invalid")
	}
	for _, key := range []string{"blocker_id", "workflow", "stage", "category", "owner", "summary", "details", "exact_next_action", "unblock_criteria"} {
		value, ok := blocker[key].(string)
		if !ok || strings.TrimSpace(value) == "" {
			return fmt.Errorf("persisted blocker %s is invalid", key)
		}
	}
	for _, key := range []string{"evidence", "affected_scope"} {
		values, ok := blocker[key].([]any)
		if !ok || len(values) == 0 || !nonEmptyStringValues(values) {
			return fmt.Errorf("persisted blocker %s is invalid", key)
		}
	}
	attempts, ok := blocker["attempted_recovery"].([]any)
	if !ok {
		return fmt.Errorf("persisted blocker attempted_recovery is invalid")
	}
	for _, rawAttempt := range attempts {
		attempt, ok := rawAttempt.(map[string]any)
		if !ok || len(attempt) != 2 {
			return fmt.Errorf("persisted blocker recovery attempt is invalid")
		}
		for _, key := range []string{"action", "result"} {
			value, ok := attempt[key].(string)
			if !ok || strings.TrimSpace(value) == "" {
				return fmt.Errorf("persisted blocker recovery attempt %s is invalid", key)
			}
		}
	}
	humanRequired, ok := blocker["human_action_required"].(bool)
	if !ok || ((owner == "user" || owner == "maintainer") && !humanRequired) {
		return fmt.Errorf("persisted blocker human_action_required is invalid")
	}
	humanGuide := blocker["human_action_guide"]
	if !humanRequired && humanGuide != nil {
		return fmt.Errorf("persisted blocker without human action must have a null guide")
	}
	if humanRequired {
		guide, ok := humanGuide.(map[string]any)
		if !ok {
			return fmt.Errorf("persisted blocker human action guide is invalid")
		}
		if err := validateWorkflowHumanAction(guide); err != nil {
			return fmt.Errorf("persisted blocker human action guide is invalid: %w", err)
		}
	}
	resume, ok := blocker["resume"].(map[string]any)
	if !ok || len(resume) != 3 {
		return fmt.Errorf("persisted blocker resume is invalid")
	}
	argv, ok := anyStringValues(resume["argv"])
	expectedArgv := workflowShowArgv(feature)
	if !ok || !equalStrings(argv, expectedArgv) {
		return fmt.Errorf("persisted blocker resume argv is invalid")
	}
	if resume["command"] != "use resume.argv" || resume["instruction"] != "Execute the structured resume.argv array exactly; do not reconstruct a shell command." {
		return fmt.Errorf("persisted blocker resume command is invalid")
	}
	return nil
}

func nonEmptyStringValues(values []any) bool {
	for _, raw := range values {
		value, ok := raw.(string)
		if !ok || strings.TrimSpace(value) == "" {
			return false
		}
	}
	return true
}

func anyStringValues(value any) ([]string, bool) {
	switch values := value.(type) {
	case []any:
		result := make([]string, 0, len(values))
		for _, raw := range values {
			text, ok := raw.(string)
			if !ok || strings.TrimSpace(text) == "" {
				return nil, false
			}
			result = append(result, text)
		}
		return result, true
	case []string:
		for _, text := range values {
			if strings.TrimSpace(text) == "" {
				return nil, false
			}
		}
		return append([]string{}, values...), true
	default:
		return nil, false
	}
}

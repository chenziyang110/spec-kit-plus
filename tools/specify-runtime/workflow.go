package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

type WorkflowService struct {
	projectRoot string
}

type WorkflowStartRequest struct {
	FeatureID string
	Stage     string
}

type WorkflowTransitionRequest struct {
	FeatureID        string
	To               string
	ExpectedRevision int
}

type workflowState struct {
	FeatureID string `json:"feature_id"`
	Revision  int    `json:"revision"`
	Stage     string `json:"stage"`
	Status    string `json:"status"`
}

var workflowStageOrder = []string{"specify", "plan", "tasks", "implement", "review", "accept"}

func NewWorkflowService(projectRoot string) *WorkflowService {
	return &WorkflowService{projectRoot: projectRoot}
}

func (service *WorkflowService) Start(request WorkflowStartRequest) Envelope {
	if !safeSegment(request.FeatureID) {
		env := NewEnvelope("invalid", "invalid workflow feature id")
		env.Blockers = append(env.Blockers, "feature id must be a safe path segment")
		return env
	}
	if !validWorkflowStage(request.Stage) {
		env := NewEnvelope("invalid", "invalid workflow stage")
		env.Blockers = append(env.Blockers, fmt.Sprintf("unknown stage %q", request.Stage))
		return env
	}
	state := workflowState{
		FeatureID: request.FeatureID,
		Revision:  1,
		Stage:     request.Stage,
		Status:    "active",
	}
	if err := service.createState(state); err != nil {
		if os.IsExist(err) {
			env := NewEnvelope("blocked", "workflow state already exists")
			env.Blockers = append(env.Blockers, "read the current state instead of resetting its revision")
			env.ShowArgv = []string{"specify-runtime", "workflow", "status", "--feature", request.FeatureID}
			return env
		}
		env := NewEnvelope("error", "failed to write workflow state")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	env := NewEnvelope("ok", "workflow state started")
	env.Data["revision"] = state.Revision
	env.Data["stage"] = state.Stage
	env.ShowArgv = []string{"specify-runtime", "workflow", "status", "--feature", request.FeatureID}
	return env
}

func (service *WorkflowService) createState(state workflowState) error {
	path, err := service.statePath(state.FeatureID)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if err != nil {
		return err
	}
	succeeded := false
	defer func() {
		_ = file.Close()
		if !succeeded {
			_ = os.Remove(path)
		}
	}()
	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(state); err != nil {
		return err
	}
	if err := file.Sync(); err != nil {
		return err
	}
	if err := file.Close(); err != nil {
		return err
	}
	succeeded = true
	return nil
}

func (service *WorkflowService) Transition(request WorkflowTransitionRequest) Envelope {
	state, err := service.readState(request.FeatureID)
	if err != nil {
		env := NewEnvelope("blocked", "workflow state is unavailable")
		env.Blockers = append(env.Blockers, err.Error())
		env.NextArgv = []string{"specify-runtime", "workflow", "start", "--feature", request.FeatureID, "--stage", "specify"}
		return env
	}
	if request.ExpectedRevision != state.Revision {
		env := NewEnvelope("blocked", "workflow revision is stale")
		env.Blockers = append(env.Blockers, fmt.Sprintf("expected revision %d but current revision is %d", request.ExpectedRevision, state.Revision))
		env.ShowArgv = []string{"specify-runtime", "workflow", "status", "--feature", request.FeatureID}
		return env
	}
	if !validNextStage(state.Stage, request.To) {
		env := NewEnvelope("blocked", "workflow transition is not allowed")
		env.Blockers = append(env.Blockers, fmt.Sprintf("cannot transition from %q to %q", state.Stage, request.To))
		env.NextArgv = []string{"specify-runtime", "workflow", "transition", "--feature", request.FeatureID, "--to", nextWorkflowStage(state.Stage), "--expected-revision", fmt.Sprint(state.Revision)}
		return env
	}
	state.Stage = request.To
	state.Revision++
	if err := service.writeState(state); err != nil {
		env := NewEnvelope("error", "failed to write workflow state")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	env := NewEnvelope("ok", "workflow state advanced")
	env.Data["revision"] = state.Revision
	env.Data["stage"] = state.Stage
	return env
}

func (service *WorkflowService) Status(featureID string) Envelope {
	state, err := service.readState(featureID)
	if err != nil {
		env := NewEnvelope("blocked", "workflow state is unavailable")
		env.Blockers = append(env.Blockers, err.Error())
		return env
	}
	env := NewEnvelope("ok", "workflow state read")
	env.Data["feature_id"] = state.FeatureID
	env.Data["revision"] = state.Revision
	env.Data["stage"] = state.Stage
	env.Data["status"] = state.Status
	return env
}

func (service *WorkflowService) statePath(featureID string) (string, error) {
	if !safeSegment(featureID) {
		return "", fmt.Errorf("feature id %q must be a safe path segment", featureID)
	}
	return secureProjectPath(service.projectRoot, filepath.ToSlash(filepath.Join(".specify", "features", featureID, "workflow.json")))
}

func (service *WorkflowService) writeState(state workflowState) error {
	path, err := service.statePath(state.FeatureID)
	if err != nil {
		return err
	}
	raw, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return atomicWriteFile(path, append(raw, '\n'), 0o644)
}

func (service *WorkflowService) readState(featureID string) (workflowState, error) {
	var state workflowState
	path, err := service.statePath(featureID)
	if err != nil {
		return state, err
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return state, err
	}
	if err := json.Unmarshal(raw, &state); err != nil {
		return state, err
	}
	return state, nil
}

func validWorkflowStage(stage string) bool {
	for _, known := range workflowStageOrder {
		if stage == known {
			return true
		}
	}
	return false
}

func validNextStage(from, to string) bool {
	for index, stage := range workflowStageOrder {
		if stage == from {
			return index+1 < len(workflowStageOrder) && workflowStageOrder[index+1] == to
		}
	}
	return false
}

func nextWorkflowStage(from string) string {
	for index, stage := range workflowStageOrder {
		if stage == from && index+1 < len(workflowStageOrder) {
			return workflowStageOrder[index+1]
		}
	}
	return ""
}

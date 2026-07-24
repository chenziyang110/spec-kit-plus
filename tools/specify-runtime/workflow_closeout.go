package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

func (service *WorkflowService) Closeout(request WorkflowCloseoutRequest) Envelope {
	feature, err := service.resolveFeature(request.FeatureDir, request.FeatureID)
	if err != nil {
		return workflowInvalid("workflow feature directory is invalid", "invalid-feature-dir", err)
	}
	acceptanceLockPath, err := secureProjectPath(service.projectRoot, feature.Rel+"/.human-acceptance.lock")
	if err != nil {
		return workflowBlocked("human acceptance lock path is unavailable", "acceptance-lock-unavailable", err.Error())
	}
	releaseAcceptance, err := filelock.Acquire(acceptanceLockPath)
	if err != nil {
		return workflowError("failed to acquire human acceptance lock", err)
	}
	defer releaseAcceptance()

	releaseWorkflow, env, ok := service.acquireWorkflowLock(feature)
	if !ok {
		return env
	}
	defer releaseWorkflow()
	state, err := service.readState(feature)
	if err != nil {
		return service.stateReadFailure(feature, err)
	}
	if request.ExpectedRevision != state.Revision {
		return workflowRevisionConflictWithState(feature, request.ExpectedRevision, state)
	}
	if state.Stage != "accept" || state.Status != "active" {
		if isTerminalWorkflowState(state) {
			return workflowStateBlocked(feature, state, "terminal workflow is immutable", "terminal-workflow-immutable")
		}
		return workflowStateBlocked(feature, state, "workflow closeout requires active accept", "invalid-closeout-stage")
	}

	acceptancePath, err := secureProjectPath(service.projectRoot, feature.Rel+"/human-acceptance.json")
	if err != nil {
		return workflowStateBlocked(feature, state, "human acceptance path is unsafe", "human-acceptance-invalid", err.Error())
	}
	acceptanceRaw, err := os.ReadFile(acceptancePath)
	if err != nil {
		return workflowStateBlocked(feature, state, "human acceptance is unavailable", "human-acceptance-required", err.Error())
	}
	if err := validateAcceptedHumanAcceptance(acceptanceRaw); err != nil {
		return workflowStateBlocked(feature, state, "human acceptance has not passed", "human-acceptance-not-passed", err.Error())
	}
	gate := service.validateStageArtifacts(feature, "accept")
	if gate.Status != "ok" && gate.Status != "warn" && gate.Status != "repaired" {
		addWorkflowStateData(&gate, state)
		return gate
	}
	digest := fmt.Sprintf("%x", sha256.Sum256(acceptanceRaw))
	snapshotPath, err := secureProjectPath(service.projectRoot, feature.Rel+"/.human-acceptance-terminal.json")
	if err != nil {
		return workflowStateBlocked(feature, state, "terminal acceptance snapshot path is unsafe", "acceptance-snapshot-conflict", err.Error())
	}
	snapshotCreated := false
	if existing, readErr := os.ReadFile(snapshotPath); readErr == nil {
		if !bytes.Equal(existing, acceptanceRaw) {
			return workflowStateBlocked(feature, state, "terminal acceptance snapshot conflicts with current acceptance", "acceptance-snapshot-conflict")
		}
	} else if !os.IsNotExist(readErr) {
		return workflowStateBlocked(feature, state, "terminal acceptance snapshot cannot be inspected", "acceptance-snapshot-conflict", readErr.Error())
	} else {
		if err := atomicWriteFile(snapshotPath, acceptanceRaw, 0o444); err != nil {
			return workflowError("failed to write terminal acceptance snapshot", err)
		}
		snapshotCreated = true
	}
	rollbackSnapshot := func() error {
		if !snapshotCreated {
			return nil
		}
		return os.Remove(snapshotPath)
	}

	currentAcceptance, err := os.ReadFile(acceptancePath)
	if err != nil || !bytes.Equal(currentAcceptance, acceptanceRaw) {
		rollbackErr := rollbackSnapshot()
		details := "human-acceptance.json changed while closeout locks were held"
		if err != nil {
			details = err.Error()
		}
		if rollbackErr != nil {
			details += "; snapshot rollback failed: " + rollbackErr.Error()
		}
		return workflowStateBlocked(feature, state, "human acceptance changed before terminal commit", "acceptance-snapshot-conflict", details)
	}

	state.Revision++
	state.Status = "completed"
	state.Blocker = nil
	state.AcceptanceSHA256 = &digest
	if summary := strings.TrimSpace(request.Summary); summary != "" {
		state.Summary = summary
	} else {
		state.Summary = "Human acceptance completed."
	}
	if service.beforeCloseoutStateWrite != nil {
		if err := service.beforeCloseoutStateWrite(); err != nil {
			if rollbackErr := rollbackSnapshot(); rollbackErr != nil {
				err = fmt.Errorf("%w; snapshot rollback failed: %v", err, rollbackErr)
			}
			return workflowError("failed to commit workflow closeout", err)
		}
	}
	if err := service.writeState(feature, state); err != nil {
		if rollbackErr := rollbackSnapshot(); rollbackErr != nil {
			err = fmt.Errorf("%w; snapshot rollback failed: %v", err, rollbackErr)
		}
		return workflowError("failed to commit workflow closeout", err)
	}
	env = NewEnvelope("ok", "workflow closeout completed")
	addWorkflowStateData(&env, state)
	env.ShowArgv = workflowShowArgv(feature)
	return env
}

func validateAcceptedHumanAcceptance(raw []byte) error {
	var acceptance map[string]any
	if err := json.Unmarshal(raw, &acceptance); err != nil {
		return fmt.Errorf("parse human-acceptance.json: %w", err)
	}
	if acceptance["status"] != "accepted" {
		return fmt.Errorf("top-level status must be accepted")
	}
	overall, ok := acceptance["overall"].(map[string]any)
	if !ok || overall["verdict"] != "pass" {
		return fmt.Errorf("overall.verdict must be pass")
	}
	return nil
}

package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestWorkflowUsesOneTypedStateAndOptimisticRevision(t *testing.T) {
	projectRoot := t.TempDir()
	service := NewWorkflowService(projectRoot)

	started := service.Start(WorkflowStartRequest{FeatureID: "001-runtime", Stage: "specify"})
	if started.Status != "ok" || started.Data["revision"] != 1 {
		t.Fatalf("start = %#v, want revision 1", started)
	}
	statePath := filepath.Join(projectRoot, ".specify", "features", "001-runtime", "workflow.json")
	raw, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatalf("read workflow state: %v", err)
	}
	var state map[string]any
	if err := json.Unmarshal(raw, &state); err != nil {
		t.Fatalf("decode workflow state: %v", err)
	}
	if state["stage"] != "specify" || state["status"] != "active" {
		t.Fatalf("workflow state = %#v", state)
	}
	for _, legacy := range []string{"workflow-runtime.json", "workflow-state.md"} {
		if _, err := os.Stat(filepath.Join(filepath.Dir(statePath), legacy)); !os.IsNotExist(err) {
			t.Fatalf("legacy dual state %s exists: %v", legacy, err)
		}
	}

	stale := service.Transition(WorkflowTransitionRequest{
		FeatureID:        "001-runtime",
		To:               "plan",
		ExpectedRevision: 0,
	})
	if stale.Status != "blocked" {
		t.Fatalf("stale transition = %#v, want blocked", stale)
	}
}

func TestWorkflowRejectsStageSkippingAndPublishesRecovery(t *testing.T) {
	service := NewWorkflowService(t.TempDir())
	started := service.Start(WorkflowStartRequest{FeatureID: "001-runtime", Stage: "specify"})
	revision := started.Data["revision"].(int)

	skipped := service.Transition(WorkflowTransitionRequest{
		FeatureID:        "001-runtime",
		To:               "tasks",
		ExpectedRevision: revision,
	})
	if skipped.Status != "blocked" {
		t.Fatalf("skip status = %q, want blocked: %#v", skipped.Status, skipped)
	}
	if len(skipped.Blockers) == 0 || len(skipped.NextArgv) == 0 {
		t.Fatalf("skip recovery is incomplete: %#v", skipped)
	}

	advanced := service.Transition(WorkflowTransitionRequest{
		FeatureID:        "001-runtime",
		To:               "plan",
		ExpectedRevision: revision,
	})
	if advanced.Status != "ok" || advanced.Data["revision"] != revision+1 {
		t.Fatalf("valid transition = %#v", advanced)
	}
}


package main

import (
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workflowregistry"
)

func TestClarifyWorkflowIsNotRegistered(t *testing.T) {
	if _, ok := hookExpectedWorkflowState["clarify"]; ok {
		t.Error("clarify remains registered as a hook workflow")
	}
	if _, ok := hookRequiredArtifacts("clarify"); ok {
		t.Error("clarify remains registered as a hook artifact contract")
	}
	if usesStageOwnedResultChannel("clarify") {
		t.Error("clarify remains registered as a stage-owned result channel")
	}
	if _, ok := workflowregistry.Policies()["clarify"]; ok {
		t.Error("clarify remains registered in the workflow policy registry")
	}
	for _, pattern := range artifactTypePatterns {
		if strings.Contains(strings.ToLower(pattern.metadata.TypeID), "clarif") {
			t.Errorf("clarify artifact type remains registered: %s", pattern.metadata.TypeID)
		}
	}
}

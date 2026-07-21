package workflowregistry

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

type templateRegistry struct {
	SchemaVersion int               `json:"schema_version"`
	Workflows     map[string]Policy `json:"workflows"`
}

func TestCompiledPoliciesMatchTemplateRegistry(t *testing.T) {
	path := filepath.Join("..", "..", "..", "..", "templates", "artifacts", "project-cognition-workflow-registry.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var registry templateRegistry
	if err := json.Unmarshal(data, &registry); err != nil {
		t.Fatal(err)
	}
	if registry.SchemaVersion != SchemaVersion {
		t.Fatalf("schema version = %d, want %d", registry.SchemaVersion, SchemaVersion)
	}
	if !reflect.DeepEqual(registry.Workflows, Policies()) {
		t.Fatalf("compiled workflow policies drifted from %s", path)
	}
}

func TestCanonicalCloseoutWorkflow(t *testing.T) {
	tests := map[string]string{
		"debug":           "sp-debug",
		"/sp.fast":        "sp-fast",
		"sp-implement":    "sp-implement",
		"implement-teams": "sp-implement",
		"integrate":       "sp-integrate",
		"quick":           "sp-quick",
		"review":          "sp-review",
		"map_update":      "sp-map-update",
	}
	for input, want := range tests {
		got, err := CanonicalCloseoutWorkflow(input)
		if err != nil {
			t.Fatalf("CanonicalCloseoutWorkflow(%q): %v", input, err)
		}
		if got != want {
			t.Fatalf("CanonicalCloseoutWorkflow(%q) = %q, want %q", input, got, want)
		}
	}
}

func TestCanonicalCloseoutWorkflowRejectsNonOwners(t *testing.T) {
	for _, input := range []string{"", "analyze", "map-build", "accept", "unknown"} {
		if _, err := CanonicalCloseoutWorkflow(input); err == nil {
			t.Fatalf("CanonicalCloseoutWorkflow(%q) unexpectedly succeeded", input)
		}
	}
}

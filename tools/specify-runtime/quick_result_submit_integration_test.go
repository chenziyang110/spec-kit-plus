package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// Uses the real result-submit route and Work/Quick fixtures in the full package.
// Result statuses are synthetic observations, not evidence of product checks.
func TestQuickDirectResultSubmitPreservesValidationFailure(t *testing.T) {
	id := "260915-result-roundtrip"
	root, workspace := stageConfirmedQuickExecutionTestWorkspace(t, id, quickExecutionSingleItemPayload("src/a.go"))
	previous, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := os.Chdir(previous); err != nil {
			t.Error(err)
		}
	})
	if err := os.WriteFile(filepath.Join(root, ".specify", "integration.json"), []byte(`{"integration":"codex"}`), 0o600); err != nil {
		t.Fatal(err)
	}
	started := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-start", id, "--item", "Q1", "--leader-direct"})
	if started.Status != "ok" {
		t.Fatal(started)
	}
	submit := func(raw string) Envelope {
		return runScriptDomainEnvelope(t, runResult, []string{"submit", "--command", "quick", "--workspace", workspace, "--lane-id", "Q1", "--result-json", raw})
	}
	accept := func() Envelope {
		return runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-accept", id, "--item", "Q1", "--evidence", "synthetic result transport test"})
	}
	path := filepath.Join(workspace, "worker-results", "Q1.json")
	bad := `{"task_id":"Q1","status":"success","changed_files":["src/a.go"],"validation_results":[{"command":"unit","status":"passed"},{"status":"failed","output":"integration failed"}]}`
	if got := submit(bad); got.Status != "invalid" || !strings.Contains(fmt.Sprint(got.Blockers), "validation_results[1]") {
		t.Fatalf("submit: %#v", got)
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("invalid submit wrote result: %v", err)
	}
	if got := accept(); got.Status == "ok" {
		t.Fatal("accepted rejected submission")
	}
	red := `{"task_id":"Q1","status":"success","changed_files":["src/a.go"],"validation_results":[{"command":"unit","status":"passed"},{"command":"integration","status":"failed"}]}`
	if got := submit(red); got.Status != "ok" {
		t.Fatal(got)
	}
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var persisted map[string]any
	if err := json.Unmarshal(before, &persisted); err != nil {
		t.Fatal(err)
	}
	checks := persisted["validation_results"].([]any)
	if len(checks) != 2 || checks[1].(map[string]any)["status"] != "failed" {
		t.Fatal(checks)
	}
	if got := accept(); got.Status == "ok" {
		t.Fatal("persisted failure passed direct acceptance")
	}
	if got := submit(bad); got.Status != "invalid" {
		t.Fatal(got)
	}
	after, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(before, after) {
		t.Fatal("invalid retry replaced existing result")
	}
	green := strings.Replace(red, `"command":"integration","status":"failed"`, `"command":"integration","status":"passed"`, 1)
	if got := submit(green); got.Status != "ok" {
		t.Fatal(got)
	}
	if got := accept(); got.Status != "ok" {
		t.Fatal(got)
	}
}

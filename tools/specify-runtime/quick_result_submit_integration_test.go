package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/workerdelta"
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
	rejected := readWorkerStored(t, path)
	firstHistory := rejected["submission_history"].([]any)
	if rejected["status"] != "pending" || rejected["cognition_result_binding"] != nil || len(firstHistory) != 1 || firstHistory[0].(map[string]any)["status"] != "rejected" || firstHistory[0].(map[string]any)["result_json"] != bad {
		t.Fatal("registered owner lost rejected input or minted a current proof", rejected)
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
	beforeStored, err := workerdelta.Decode(before)
	if err != nil {
		t.Fatal(err)
	}
	afterStored, err := workerdelta.Decode(after)
	if err != nil {
		t.Fatal(err)
	}
	beforeCurrent, err := workerdelta.CandidateFromStored(beforeStored)
	if err != nil {
		t.Fatal(err)
	}
	afterCurrent, err := workerdelta.CandidateFromStored(afterStored)
	if err != nil {
		t.Fatal(err)
	}
	if !workerdelta.Same(beforeCurrent, afterCurrent) || !workerdelta.Same(beforeStored["cognition_result_binding"], afterStored["cognition_result_binding"]) {
		t.Fatal("invalid retry replaced current result or proof")
	}
	history := afterStored["submission_history"].([]any)
	if len(history) != 3 || history[2].(map[string]any)["status"] != "rejected" || history[2].(map[string]any)["result_json"] != bad {
		t.Fatal("invalid retry discarded history")
	}
	green := strings.Replace(red, `"command":"integration","status":"failed"`, `"command":"integration","status":"passed"`, 1)
	if got := submit(green); got.Status != "ok" {
		t.Fatal(got)
	}
	if got := accept(); got.Status != "ok" {
		t.Fatal(got)
	}
}

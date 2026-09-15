package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// These use real Quick services and existing Work fixtures in a complete
// checkout. Passing standalone dispatch helpers does not execute these tests.
func TestQuickDirectLifecyclePreservesResultGates(t *testing.T) {
	id := "260915-direct"
	root, workspace := stageConfirmedQuickExecutionTestWorkspace(t, id, quickExecutionSingleItemPayload("src/a.go"))
	call := func(mode string, extra ...string) Envelope {
		return runScriptDomainEnvelope(t, runQuick, append([]string{"--project-root", root, mode, id, "--item", "Q1"}, extra...))
	}
	started := call("item-start", "--leader-direct")
	if started.Status != "ok" || started.Data["requires_worker"] != false || started.Data["execution_mode"] != quickLeaderDirectMode {
		t.Fatalf("start %#v", started)
	}
	if started.Data["work_claim"] == nil {
		t.Fatal("missing existing claim receipt")
	}
	packet := started.Data["packet"].(map[string]any)
	if packet["requires_worker"] != false || packet["requires_result_submit"] != true {
		t.Fatal(packet)
	}
	resumed := call("item-start")
	if resumed.Status != "ok" || resumed.Data["execution_mode"] != quickLeaderDirectMode || resumed.Data["requires_worker"] != false {
		t.Fatal(resumed)
	}
	if got := call("item-accept", "--evidence", "prose alone"); got.Status == "ok" {
		t.Fatal("accepted without result")
	}
	if got := call("allow-inline", "--reason", "spawn_failed: irrelevant"); got.Status == "ok" {
		t.Fatal("direct proof waived")
	}
	if got := call("item-accept", "--allow-inline", "--reason", "spawn_failed: irrelevant", "--evidence", "bypass"); got.Status == "ok" {
		t.Fatal("one-shot fallback waived proof")
	}
	for _, tc := range []struct {
		name, status, path string
		blockers           []any
	}{
		{"red check", "failed", "src/a.go", []any{}},
		{"skipped check", "skipped", "src/a.go", []any{}},
		{"out of scope", "passed", "outside.go", []any{}},
		{"blocker", "passed", "src/a.go", []any{"unfinished"}},
	} {
		mustWriteQuickWorkerResult(t, workspace, "Q1", map[string]any{
			"task_id": "Q1", "status": "success", "changed_files": []any{tc.path}, "blockers": tc.blockers,
			"validation_results": []any{map[string]any{"command": "fixture check", "status": tc.status}},
		})
		if got := call("item-accept", "--evidence", tc.name); got.Status == "ok" {
			t.Fatalf("accepted %s", tc.name)
		}
	}
	good := map[string]any{"task_id": "Q1", "status": "success", "changed_files": []any{"src/a.go"}, "blockers": []any{},
		"validation_results": []any{map[string]any{"command": "fixture check", "status": "passed"}}}
	mustWriteQuickWorkerResult(t, workspace, "Q1", good)
	accepted := call("item-accept", "--evidence", "fixture check passed")
	if accepted.Status != "ok" {
		t.Fatal(accepted)
	}
	proof := accepted.Data["worker_proof"].(map[string]any)
	if proof["mode"] != quickLeaderDirectMode || proof["result_path"] == "" {
		t.Fatal(proof)
	}
	service := quickService{projectRoot: root}
	if err := service.validateCloseAgainstConfirmation(workspace, "resolved"); err != nil {
		t.Fatal(err)
	}
	good["validation_results"] = []any{map[string]any{"command": "fixture check", "status": "failed"}}
	mustWriteQuickWorkerResult(t, workspace, "Q1", good)
	if err := service.validateCloseAgainstConfirmation(workspace, "resolved"); err == nil {
		t.Fatal("close ignored changed direct proof")
	}
	if got := call("item-accept", "--evidence", "replay"); got.Status == "ok" {
		t.Fatal("reaccept ignored changed direct proof")
	}
}

func TestQuickDirectCannotRelabelActiveWorker(t *testing.T) {
	id := "260915-worker"
	root, workspace := stageConfirmedQuickExecutionTestWorkspace(t, id, quickExecutionSingleItemPayload("src/a.go"))
	start := []string{"--project-root", root, "item-start", id, "--item", "Q1"}
	if got := runScriptDomainEnvelope(t, runQuick, start); got.Status != "ok" || got.Data["requires_worker"] != true {
		t.Fatal(got)
	}
	path := filepath.Join(workspace, "confirmation.json")
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	got := runScriptDomainEnvelope(t, runQuick, append(start, "--leader-direct"))
	if got.Status == "ok" || !strings.Contains(strings.Join(got.Blockers, " "), "before first start") {
		t.Fatal(got)
	}
	after, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(before) != string(after) {
		t.Fatal("failed selection changed canonical state")
	}
}

func TestQuickDirectStaleFenceStillBlocksWithoutStateMutation(t *testing.T) {
	id := "260915-fence"
	root, workspace := stageConfirmedQuickExecutionTestWorkspace(t, id, quickExecutionSingleItemPayload("src/a.go"))
	path := filepath.Join(workspace, "confirmation.json")
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Setenv("SPECIFY_WORK_FENCE", "999999")
	got := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-start", id, "--item", "Q1", "--leader-direct"})
	if got.Status == "ok" {
		t.Fatal("direct bypassed fence")
	}
	after, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(before) != string(after) {
		t.Fatal("failed claim persisted selection")
	}
	var doc map[string]any
	if err := json.Unmarshal(after, &doc); err != nil {
		t.Fatal(err)
	}
}

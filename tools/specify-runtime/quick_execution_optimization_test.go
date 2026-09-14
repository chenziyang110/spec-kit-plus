package main

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

// These tests exercise the real Quick CLI and Work fixture in the full runtime
// package. They are intentionally separate from the stdlib-only unit tests.
func newQuickOptimizationFixture(t *testing.T) (string, string, string) {
	t.Helper()
	root := initCoordinationCLIRepository(t)
	id := "260914-001"
	workspace := filepath.Join(root, ".planning", "quick", id+"-optimize")
	mustMkdirAllScriptDomainTest(t, workspace)
	mustWriteScriptDomainTest(t, filepath.Join(workspace, "STATUS.md"), `---
id: "260914-001"
slug: "optimize"
title: "Optimize"
status: gathering
understanding_confirmed: false
---

## Understanding Checkpoint

x

## Execution

y

## Summary Pointer

changed_code_paths: []
project_cognition_refresh:
  status: not-needed
  evidence: []
`)
	payload := map[string]any{
		"source": map[string]any{"kind": "prompt"},
		"decision": map[string]any{
			"goal": "ship bounded delivery", "user_visible_result": "Q1 done",
			"scope": map[string]any{"include": []any{"a"}, "exclude": []any{"b"}},
			"items": []any{map[string]any{
				"id": "Q1", "deliverable": "contract", "depends_on": []any{},
				"acceptance": "types match", "write_scope": []any{"src/a.go"},
			}},
			"reconfirmation_trigger": "scope change",
		},
	}
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	env := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "checkpoint-stage", id, "--input-json", string(raw)})
	if env.Status != "ok" {
		t.Fatalf("stage: %v", env.Blockers)
	}
	env = runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "checkpoint-confirm", id, "--digest", stringValue(env.Data["confirmation_digest"])})
	if env.Status != "ok" {
		t.Fatalf("confirm: %v", env.Blockers)
	}
	bindQuickExecutionWork(t, root, id)
	return root, workspace, id
}

func TestQuickCompactCLILeavesDefaultAndGatesIntact(t *testing.T) {
	root, _, id := newQuickOptimizationFixture(t)
	full := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-status", id})
	compact := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-status", id, "--compact"})
	if full.Status != "ok" || compact.Status != "ok" {
		t.Fatalf("status: %v / %v", full.Blockers, compact.Blockers)
	}
	if _, ok := full.Data["confirmation"]; !ok {
		t.Fatal("legacy response lost confirmation")
	}
	if _, ok := full.Data["response_schema"]; ok {
		t.Fatal("legacy output opted into compact unexpectedly")
	}
	if _, ok := compact.Data["confirmation"]; ok {
		t.Fatal("compact response retained full confirmation")
	}
	if compact.Data["response_schema"] != "quick-execution-compact-v1" {
		t.Fatal("missing compact schema")
	}
	for key, want := range full.Data {
		if key != "confirmation" && key != "pulse" && !reflect.DeepEqual(compact.Data[key], want) {
			t.Errorf("lost %s", key)
		}
	}
	started := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-start", id, "--item", "Q1", "--compact"})
	if started.Status != "ok" || started.Data["requires_worker"] != true || started.Data["work_claim"] == nil || started.Data["packet"] == nil {
		t.Fatalf("dispatch contract lost: %#v", started)
	}
	blocked := runScriptDomainEnvelope(t, runQuick, []string{"--project-root", root, "item-accept", id, "--item", "Q1", "--evidence", "not enough without worker proof", "--compact"})
	if blocked.Status == "ok" || len(blocked.Blockers) == 0 {
		t.Fatal("compact bypassed worker-result gate")
	}
	if _, ok := blocked.Data["response_schema"]; ok {
		t.Fatal("failure diagnostics were compacted")
	}
}

func TestQuickResumeProjectionFailureReturnsNoDispatchReceipt(t *testing.T) {
	root, workspace, id := newQuickOptimizationFixture(t)
	service := quickService{projectRoot: root}
	name := filepath.Base(workspace)
	if _, _, _, err := service.startWorkItem(workspace, name, id, "Q1", nil); err != nil {
		t.Fatal(err)
	}
	workID, fence := os.Getenv("SPECIFY_WORK_ID"), os.Getenv("SPECIFY_WORK_FENCE")
	path := filepath.Join(workspace, "STATUS.md")
	original, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	// A directory at STATUS.md fails consistently even when tests run as root;
	// permission-bit tricks do not. Call the service directly to reach the resume
	// persistence path rather than failing earlier in workspace discovery.
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(path, 0o755); err != nil {
		t.Fatal(err)
	}
	doc, packet, claim, err := service.startWorkItem(workspace, name, id, "Q1", nil)
	var typed *quickResumePersistenceError
	if !errors.As(err, &typed) || typed.phase != "status projection" {
		t.Fatalf("expected projection failure, got %v", err)
	}
	if doc != nil || packet != nil || claim != nil {
		t.Fatal("failed resume exposed a successful dispatch receipt")
	}
	persisted, err := service.loadConfirmation(workspace)
	if err != nil {
		t.Fatal(err)
	}
	if quickStatusMap(persisted)["Q1"].Status != "in_progress" {
		t.Fatal("failed resume discarded active task state")
	}
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, original, 0o644); err != nil {
		t.Fatal(err)
	}
	if _, _, _, err := service.startWorkItem(workspace, name, id, "Q1", nil); err != nil {
		t.Fatalf("resume after repair: %v", err)
	}
	if os.Getenv("SPECIFY_WORK_ID") != workID || os.Getenv("SPECIFY_WORK_FENCE") != fence {
		t.Fatal("recovery changed Work identity")
	}
}

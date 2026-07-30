package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestUnifiedTaskControlPlaneOwnsAuthoringAndLifecycle(t *testing.T) {
	root := t.TempDir()
	templates := filepath.Join(root, ".specify", "templates")
	feature := filepath.Join(root, ".specify", "features", "001-runtime-tasks")
	if err := os.MkdirAll(templates, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	writeTaskRuntimeFixture(t, filepath.Join(templates, "task-index-template.json"), map[string]any{
		"version": 2, "status": "draft", "source_contract": "plan-contract.json",
		"source_revision": nil, "policy_refs": []any{}, "user_confirmed_deferral_refs": []any{},
		"implementation_target_ref": nil, "acceptance_refs": []any{}, "official_entrypoints": []any{},
		"system_review_scenarios": []any{}, "review_obligations": []any{},
		"human_acceptance_obligations": []any{}, "human_acceptance_scenarios": []any{},
		"validation_policy": map[string]any{
			"mode": "feature_epochs", "max_epochs": 3, "budget_scope": "implement-review",
			"budget_ref": "implementation-review/validation-runs.json", "heavy_gate_owner": "leader",
		},
		"tasks": []any{}, "parallel_batches": []any{}, "join_points": []any{},
		"validation": []any{}, "transition": map[string]any{},
	})
	writeTaskRuntimeFixture(t, filepath.Join(templates, "task-packet-template.json"), map[string]any{
		"version": 2, "task_id": nil, "source_task_ref": nil, "source_revision": nil,
		"objective": nil, "policy_refs": []any{}, "user_confirmed_deferral_refs": []any{},
		"implementation_target_ref": nil, "authoritative_refs": []any{}, "read_scope": []any{},
		"write_scope": []any{}, "forbidden_drift": []any{}, "acceptance_refs": []any{},
		"must_preserve_refs": []any{}, "consequence_obligation_refs": []any{},
		"capability_operation_refs": []any{}, "fidelity_refs": []any{}, "ui_contract": map[string]any{
			"fidelity_level": "none", "required_states": []any{}, "required_evidence": []any{}, "must_not": []any{},
		},
		"validation_policy": map[string]any{}, "task_checks": []any{}, "required_validation": []any{},
		"required_consumer_evidence": []any{}, "done_condition": []any{},
		"stop_and_reopen_conditions": []any{}, "recovery": nil,
	})
	writeTaskRuntimeFixture(t, filepath.Join(templates, "task-lifecycle-template.json"), map[string]any{
		"version": 1, "revision": 0, "task_id": nil, "task_ref": nil, "source_revision": nil,
		"execution_mode": "leader-direct", "packet_ref": nil, "result_ref": nil, "status": "pending",
		"changed_paths": []any{}, "validation": []any{}, "review": nil,
		"ui_verification": map[string]any{"applicable": false}, "obligation_evidence": []any{},
		"blockers": []any{}, "recovery": nil,
	})

	oldCWD, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(oldCWD) })

	featureRef := filepath.ToSlash(filepath.Join(".specify", "features", "001-runtime-tasks"))
	definition := `{"title":"Runtime task","tasks":[{"id":"T001","objective":"Implement runtime ownership","dependencies":[],"expected_write_scope":["src/runtime.go"],"required_refs":["plan-contract.json#/acceptance_refs/0"],"acceptance":["Runtime owns state"],"verification":["go test ./..."],"task_checks":["gofmt check"],"ui_contract":{"fidelity_level":"high"}}]}`
	assertTaskRuntimeCommandOK(t, []string{"tasks", "build", "--feature-dir", featureRef, "--definition-json", definition, "--format", "json"})
	assertTaskRuntimeCommandOK(t, []string{"tasks", "finalize", "--feature-dir", featureRef, "--format", "json"})
	assertTaskRuntimeCommandOK(t, []string{"tasks", "handoff", "--feature-dir", featureRef, "--target", "tasks", "--format", "json"})
	assertTaskRuntimeCommandOK(t, []string{"tasks", "handoff", "--feature-dir", featureRef, "--target", "implement", "--format", "json"})

	index := readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))
	indexedTasks, _ := index["tasks"].([]any)
	indexedTask, _ := indexedTasks[0].(map[string]any)
	ui, _ := indexedTask["ui_contract"].(map[string]any)
	if ui["fidelity_level"] != "high" || ui["required_states"] == nil || ui["must_not"] == nil {
		t.Fatalf("CLI did not expand stable UI defaults: %#v", ui)
	}

	next := assertTaskRuntimeCommandOK(t, []string{"implement", "task-next", "--feature-dir", featureRef, "--format", "json"})
	task, ok := next["task"].(map[string]any)
	if !ok || task["task_id"] != "T001" {
		t.Fatalf("unexpected next task: %#v", next)
	}
	compiled := assertTaskRuntimeCommandOK(t, []string{"implement", "packet-compile", "--feature-dir", featureRef, "--task-id", "T001", "--format", "json"})
	packetRef, _ := compiled["packet_ref"].(string)
	if packetRef == "" {
		t.Fatalf("missing packet ref: %#v", compiled)
	}
	assertTaskRuntimeCommandOK(t, []string{"implement", "task-start", "--feature-dir", featureRef, "--task-id", "T001", "--execution-mode", "delegated", "--packet-ref", packetRef, "--format", "json"})
	result := `{"task_id":"T001","status":"success","changed_files":["src/runtime.go"],"validation_results":[{"command":"gofmt check","status":"passed","output":"PASS"}],"blockers":[],"suggested_recovery_actions":[]}`
	assertTaskRuntimeCommandOK(t, []string{"implement", "result-merge", "--feature-dir", featureRef, "--task-id", "T001", "--result-json", result, "--format", "json"})
	accepted := assertTaskRuntimeCommandOK(t, []string{"implement", "task-accept", "--feature-dir", featureRef, "--task-id", "T001", "--format", "json"})
	if accepted["task_status"] != "accepted" || accepted["next_task_id"] != nil {
		t.Fatalf("unexpected acceptance: %#v", accepted)
	}

	for _, ref := range []string{
		"task-index.json", "tasks.md", "handoff-to-tasks.json", "handoff-to-implement.json", "implement-tracker.md",
		"implementation-review/execution-state.json", "implementation-review/tasks/T001.json",
		"implementation-review/packets/T001.json", "worker-results/T001.json",
	} {
		if _, err := os.Stat(filepath.Join(feature, filepath.FromSlash(ref))); err != nil {
			t.Fatalf("expected CLI-owned artifact %s: %v", ref, err)
		}
	}
	projected, err := os.ReadFile(filepath.Join(feature, "tasks.md"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(projected), "- [x] T001") {
		t.Fatalf("task projection was not accepted:\n%s", projected)
	}
	if _, err := os.Stat(filepath.Join(root, "result.json")); !os.IsNotExist(err) {
		t.Fatal("inline result path unexpectedly created a temporary result file")
	}
}

func TestEvidenceVisualCompareDerivesStableReportFromTaskContract(t *testing.T) {
	root := t.TempDir()
	featureRef := filepath.ToSlash(filepath.Join(".specify", "features", "003-visual-report"))
	feature := filepath.Join(root, filepath.FromSlash(featureRef))
	templates := filepath.Join(root, ".specify", "templates")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(templates, 0o755); err != nil {
		t.Fatal(err)
	}
	templateRaw, err := os.ReadFile(filepath.Join("..", "..", "templates", "visual-comparison-template.json"))
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(templates, "visual-comparison-template.json"), templateRaw, 0o644); err != nil {
		t.Fatal(err)
	}
	writeTaskRuntimeFixture(t, filepath.Join(feature, "task-index.json"), map[string]any{
		"version": 2, "status": "ready",
		"tasks": []any{map[string]any{
			"id": "T001", "ui_contract": map[string]any{
				"fidelity_level": "high", "approved_visual_ref": ".specify/design/previews/round-01.html#direction-a",
				"approved_preview_sha256": strings.Repeat("a", 64), "approved_manifest_sha256": strings.Repeat("b", 64),
				"approved_handoff_ref": ".specify/design/handoffs/direction-a.json", "approved_handoff_sha256": strings.Repeat("c", 64),
				"design_decision_ids": []any{"DS-1", "DS-2"}, "handoff_contract_ids": []any{"DH-1"},
				"comparison_tolerance": map[string]any{"pixel_delta": 0.05}, "accepted_deviations": []any{},
			},
		}},
	})
	input := map[string]any{
		"entry_point": "EP-1", "implementation_revision": "git:abc123",
		"capture_refs":            []any{"evidence://capture/mobile"},
		"structure_snapshot_refs": []any{"evidence://structure/mobile"},
		"runtime_diagnostic_refs": []any{"evidence://runtime/mobile"},
		"matrix": []any{map[string]any{
			"viewport": "390x844", "color_mode": "light", "motion_mode": "reduced", "state": "default",
			"implementation_capture_ref": "evidence://capture/mobile",
			"covered_decision_ids":       []any{"DS-1", "DS-2"}, "covered_handoff_contract_ids": []any{"DH-1"},
			"structural_differences": []any{}, "visual_differences": []any{}, "result": "matched",
		}},
		"verdict": "passed", "reviewer": "agent:visual-reviewer",
	}
	inputRaw, _ := json.Marshal(input)
	exit, env := runTaskRuntimeCommand(t, []string{
		"evidence", "visual-compare", "--project-root", root, "--feature-dir", featureRef,
		"--task-id", "T001", "--input-json", string(inputRaw), "--format", "json",
	})
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("visual-compare failed: exit=%d env=%#v", exit, env)
	}
	reportRef := env.Data["comparison_report_ref"].(string)
	report := readImplementJSONFile(t, filepath.Join(feature, filepath.FromSlash(reportRef)))
	approved := report["approved"].(map[string]any)
	if report["schema"] != visualComparisonSchema || report["task_id"] != "T001" || report["verdict"] != "passed" || approved["preview_sha256"] != strings.Repeat("a", 64) {
		t.Fatalf("derived visual comparison report = %#v", report)
	}
	if env.Data["comparison_report_sha256"] != optionalFileSHA256(filepath.Join(feature, filepath.FromSlash(reportRef))) {
		t.Fatalf("visual comparison digest = %#v", env.Data)
	}
	input["schema"] = visualComparisonSchema
	invalidRaw, _ := json.Marshal(input)
	exit, invalid := runTaskRuntimeCommand(t, []string{
		"evidence", "visual-compare", "--project-root", root, "--feature-dir", featureRef,
		"--task-id", "T001", "--input-json", string(invalidRaw), "--format", "json",
	})
	if exit != 2 || !strings.Contains(invalid.Summary, "runtime-owned") {
		t.Fatalf("runtime-owned visual comparison input should block: exit=%d env=%#v", exit, invalid)
	}
	exit, generic := runTaskRuntimeCommand(t, []string{
		"artifact", "prepare", "--project-root", root, "--path", filepath.ToSlash(filepath.Join(featureRef, reportRef)), "--format", "json",
	})
	if exit != 2 || generic.Data["owner"] != "specify-runtime evidence visual-compare" {
		t.Fatalf("generic report mutation should block: exit=%d env=%#v", exit, generic)
	}
}

func TestUnifiedTaskControlPlaneRejectsDirectlyAuthoredReadinessAndUnvalidatedAcceptance(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify", "templates"), 0o755); err != nil {
		t.Fatal(err)
	}
	feature := filepath.Join(root, ".specify", "features", "002-guard")
	if err := os.MkdirAll(feature, 0o755); err != nil {
		t.Fatal(err)
	}
	writeTaskRuntimeFixture(t, filepath.Join(root, ".specify", "templates", "task-index-template.json"), map[string]any{
		"version": 2, "status": "draft", "acceptance_refs": []any{}, "tasks": []any{}, "transition": map[string]any{},
	})
	oldCWD, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(oldCWD) })
	featureRef := filepath.ToSlash(filepath.Join(".specify", "features", "002-guard"))
	exit, env := runTaskRuntimeCommand(t, []string{"tasks", "build", "--feature-dir", featureRef, "--definition-json", `{"status":"ready","tasks":[]}`})
	if exit == 0 || env.Status != "blocked" {
		t.Fatalf("CLI-owned readiness was not rejected: exit=%d env=%#v", exit, env)
	}
	exit, env = runTaskRuntimeCommand(t, []string{"tasks", "build", "--feature-dir", featureRef, "--definition-json", `{"tasks":[{"id":"T001","objective":"Bypass lifecycle","status":"accepted"}]}`})
	if exit == 0 || env.Status != "blocked" || !strings.Contains(env.Summary, "CLI-owned") {
		t.Fatalf("CLI-owned task lifecycle was not rejected: exit=%d env=%#v", exit, env)
	}
	exit, env = runTaskRuntimeCommand(t, []string{"tasks", "build", "--feature-dir", featureRef, "--definition-json", `{"tasks":[{"id":"T001","objective":"Inject payload","arbitrary_blob":{"value":"unexpected"}}]}`})
	if exit == 0 || env.Status != "blocked" || !strings.Contains(env.Summary, "unsupported field") {
		t.Fatalf("unsupported task field was not rejected: exit=%d env=%#v", exit, env)
	}
	exit, env = runTaskRuntimeCommand(t, []string{"tasks", "build", "--feature-dir", featureRef, "--definition-json", `{"tasks":[{"id":"T001","objective":"Read runtime storage","read_scope":[".specify/project-cognition/status.json"]}]}`})
	if exit == 0 || env.Status != "blocked" || !strings.Contains(env.Summary, "CLI-owned workflow artifact") {
		t.Fatalf("CLI-owned read scope was not rejected: exit=%d env=%#v", exit, env)
	}
	exit, env = runTaskRuntimeCommand(t, []string{"tasks", "build", "--feature-dir", featureRef, "--definition-json", `{"tasks":[{"id":"T001","objective":"Read canonical spec directly","read_scope":["SPEC.md"]}]}`})
	if exit == 0 || env.Status != "blocked" || !strings.Contains(env.Summary, "specify-runtime artifact") {
		t.Fatalf("feature-relative workflow read scope was not rejected: exit=%d env=%#v", exit, env)
	}
	exit, env = runTaskRuntimeCommand(t, []string{"tasks", "build", "--feature-dir", featureRef, "--definition-json", `{"tasks":[{"id":"T001","objective":"Write workflow state","expected_write_scope":["task-index.json"]}]}`})
	if exit == 0 || env.Status != "blocked" || !strings.Contains(env.Summary, "specify-runtime tasks") {
		t.Fatalf("CLI-owned write scope was not rejected: exit=%d env=%#v", exit, env)
	}
}

func TestImplementTaskResultRequiresRecoverableBlocksAndTaskCheckCoverage(t *testing.T) {
	result, _, err := normalizeImplementTaskResult(map[string]any{
		"task_id":                    "T001",
		"status":                     "blocked",
		"blockers":                   []any{"missing dependency"},
		"suggested_recovery_actions": []any{},
	}, "T001")
	if err != nil || len(anyStringSlice(result["suggested_recovery_actions"])) == 0 {
		t.Fatalf("blocked result did not receive deterministic recovery: result=%#v err=%v", result, err)
	}

	err = validateImplementTaskCheckCoverage(
		map[string]any{"task_checks": []any{"go test ./..."}},
		[]any{map[string]any{"command": "gofmt check", "status": "passed"}},
	)
	if err == nil || !strings.Contains(err.Error(), "go test ./...") {
		t.Fatalf("missing task check was accepted: %v", err)
	}
}

func assertTaskRuntimeCommandOK(t *testing.T, args []string) map[string]any {
	t.Helper()
	exit, env := runTaskRuntimeCommand(t, args)
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("command %v failed: exit=%d env=%#v", args, exit, env)
	}
	return env.Data
}

func runTaskRuntimeCommand(t *testing.T, args []string) (int, Envelope) {
	t.Helper()
	var stdout bytes.Buffer
	exit := Run(args, &stdout, &bytes.Buffer{}, "test")
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode runtime response for %v: %v\n%s", args, err, stdout.String())
	}
	return exit, env
}

func writeTaskRuntimeFixture(t *testing.T, path string, payload map[string]any) {
	t.Helper()
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(raw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

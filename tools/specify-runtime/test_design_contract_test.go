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

func TestTestDesignScaffoldKindsCreateCanonicalJSONArtifacts(t *testing.T) {
	projectRoot := t.TempDir()
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(projectRoot, "specs", "001-test-design", "test-design"), 0o755); err != nil {
		t.Fatal(err)
	}

	service := NewArtifactService(projectRoot)
	tests := []struct {
		kind string
		path string
	}{
		{kind: "test-universe", path: "specs/001-test-design/test-design/test-universe.json"},
		{kind: "test-catalog", path: "specs/001-test-design/test-design/test-catalog.json"},
		{kind: "test-data-manifest", path: "specs/001-test-design/test-design/test-data-manifest.json"},
		{kind: "coverage-matrix", path: "specs/001-test-design/test-design/coverage-matrix.json"},
	}
	for _, tc := range tests {
		env := service.Scaffold(ArtifactScaffoldRequest{
			Kind: tc.kind,
			Path: tc.path,
		})
		if env.Status != "ok" {
			t.Fatalf("scaffold %s status = %q, want ok: %#v", tc.kind, env.Status, env)
		}
		if env.Data["canonical_path"] != tc.path {
			t.Fatalf("scaffold %s canonical_path = %#v, want %q", tc.kind, env.Data["canonical_path"], tc.path)
		}
		raw, err := os.ReadFile(filepath.Join(projectRoot, filepath.FromSlash(tc.path)))
		if err != nil {
			t.Fatalf("read scaffolded %s: %v", tc.path, err)
		}
		if !json.Valid(raw) {
			t.Fatalf("scaffolded %s is not canonical JSON: %q", tc.path, raw)
		}
	}
}

func TestTestDesignArtifactsAreCanonicalPatchableAndRejectWholeFileSubmit(t *testing.T) {
	tests := []string{
		"specs/001-test-design/test-design/test-universe.json",
		"specs/001-test-design/test-design/test-catalog.json",
		"specs/001-test-design/test-design/test-data-manifest.json",
		"specs/001-test-design/test-design/coverage-matrix.json",
	}
	for _, path := range tests {
		metadata, ok := LookupArtifactType(path)
		if !ok {
			t.Fatalf("LookupArtifactType(%q) = not found, want canonical test-design artifact", path)
		}
		if metadata.Role != "canonical" {
			t.Fatalf("%s role = %q, want canonical", path, metadata.Role)
		}
		if !artifactTypeAllows(metadata, "prepare") || !artifactTypeAllows(metadata, "patch") {
			t.Fatalf("%s operations = %#v, want prepare+patch", path, metadata.Operations)
		}
		if artifactTypeAllows(metadata, "submit") {
			t.Fatalf("%s operations = %#v, want patch-only and no whole-file submit", path, metadata.Operations)
		}
	}
}

func TestTaskControlTestDesignBindingRejectsMalformedDigestContainer(t *testing.T) {
	payload := map[string]any{
		"test_design_handoff_ref":        nil,
		"test_design_handoff_sha256":     nil,
		"test_design_source_fingerprint": nil,
		"test_design_state_revision":     nil,
		"test_design_artifact_digests":   []any{},
	}
	if taskControlTestDesignBindingEmpty(payload) {
		t.Fatal("malformed array-valued test-design artifact digests were treated as an empty optional binding")
	}
}

func TestTestDesignPublishedHandoffRequiresExactAcceptedAuditBinding(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)
	publishValidTestDesignHandoff(t, projectRoot, featureRel)
	artifactRoot := filepath.Join(featureDir, "test-design")
	state, err := testDesignReadState(artifactRoot)
	if err != nil {
		t.Fatal(err)
	}
	manifest, err := testDesignReadManifest(artifactRoot)
	if err != nil {
		t.Fatal(err)
	}
	wrongState := state
	wrongLaneID := "AUDIT-999"
	wrongState.Audit.LaneID = &wrongLaneID
	if _, err := testDesignValidateStateAuditBinding(wrongState, manifest); err == nil {
		t.Fatal("mismatched state audit lane_id was accepted")
	}

	manifestPath := filepath.Join(artifactRoot, "lane-manifest.json")
	originalManifest, err := os.ReadFile(manifestPath)
	if err != nil {
		t.Fatal(err)
	}
	retained := make([]testDesignLane, 0, len(manifest.Lanes))
	for _, lane := range manifest.Lanes {
		if lane.Kind != "audit" {
			retained = append(retained, lane)
		}
	}
	manifest.Lanes = retained
	mutatedManifest, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(manifestPath, append(mutatedManifest, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := (testDesignService{projectRoot: projectRoot}).verifyPublishedHandoff(artifactRoot); err == nil {
		t.Fatal("published handoff verified after its accepted audit lane was removed")
	}
	if err := os.WriteFile(manifestPath, originalManifest, 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestTestDesignPublishedHandoffUsesFeatureQualifiedCanonicalRef(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)
	publishValidTestDesignHandoff(t, projectRoot, featureRel)

	artifactRoot := filepath.Join(featureDir, "test-design")
	binding, err := (testDesignService{projectRoot: projectRoot}).verifyPublishedHandoff(artifactRoot)
	if err != nil {
		t.Fatal(err)
	}
	wantRef := filepath.ToSlash(filepath.Join(featureRel, "test-design", "handoff-to-tasks.json"))
	if binding.Ref != wantRef {
		t.Fatalf("handoff ref=%q, want %q", binding.Ref, wantRef)
	}
}

func TestTestDesignTasksBuildPreservesRefsAndRendersThemInTasksMarkdown(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	templatesDir := filepath.Join(projectRoot, ".specify", "templates")
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(templatesDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(templatesDir, "task-index-template.json"), map[string]any{
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
		"test_design_handoff_ref": nil, "test_design_handoff_sha256": nil,
		"test_design_source_fingerprint": nil, "test_design_state_revision": nil,
		"test_design_artifact_digests": map[string]any{},
	}); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(templatesDir, "task-packet-template.json"), map[string]any{
		"version": 2, "task_id": nil, "source_task_ref": nil, "source_revision": nil,
		"objective": nil, "policy_refs": []any{}, "user_confirmed_deferral_refs": []any{},
		"implementation_target_ref": nil, "authoritative_refs": []any{}, "read_scope": []any{},
		"write_scope": []any{}, "forbidden_drift": []any{}, "acceptance_refs": []any{},
		"must_preserve_refs": []any{}, "consequence_obligation_refs": []any{},
		"capability_operation_refs": []any{}, "fidelity_refs": []any{},
		"ui_contract": map[string]any{
			"fidelity_level": "none", "interaction_matrix": []any{}, "editing_matrix": []any{}, "required_states": []any{}, "data_state_matrix": []any{}, "required_evidence": []any{}, "must_not": []any{},
		},
		"validation_policy": map[string]any{}, "task_checks": []any{}, "required_validation": []any{},
		"required_consumer_evidence": []any{}, "test_case_refs": []any{}, "test_data_refs": []any{},
		"done_condition": []any{}, "stop_and_reopen_conditions": []any{}, "recovery": nil,
		"test_design_handoff_ref": nil, "test_design_handoff_sha256": nil,
		"test_design_source_fingerprint": nil, "test_design_state_revision": nil,
		"test_design_artifact_digests": map[string]any{},
	}); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)
	publishValidTestDesignHandoff(t, projectRoot, featureRel)

	definitionRaw, err := json.Marshal(map[string]any{
		"title":           "Test design consumption",
		"source_revision": 7,
		"tasks": []any{
			map[string]any{
				"id":                   "T001",
				"objective":            "Implement the tested publish flow",
				"dependencies":         []any{},
				"expected_write_scope": []any{"src/publish.py"},
				"required_refs":        []any{"docs/test-design.md"},
				"acceptance":           []any{"Publish flow matches the authored test design"},
				"verification":         []any{"pytest tests/unit/test_publish.py -q"},
				"test_case_refs": []any{
					"test-catalog.json#/cases/TC-001",
				},
				"test_data_refs": []any{
					"test-data-manifest.json#/datasets/TD-001",
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	exit := Run([]string{
		"tasks", "build", "--feature-dir", featureRel, "--definition-json", string(definitionRaw), "--format", "json",
	}, &stdout, &stderr, "test")
	if exit != 0 {
		t.Fatalf("tasks build exit = %d stderr=%q stdout=%q", exit, stderr.String(), stdout.String())
	}

	taskIndex := readTestDesignJSONMap(t, filepath.Join(featureDir, "task-index.json"))
	tasks, _ := taskIndex["tasks"].([]any)
	if len(tasks) != 1 {
		t.Fatalf("task-index tasks = %#v, want one task", taskIndex["tasks"])
	}
	task, _ := tasks[0].(map[string]any)
	assertStringListEquals(t, task["test_case_refs"], []string{
		"test-catalog.json#/cases/TC-001",
	})
	assertStringListEquals(t, task["test_data_refs"], []string{
		"test-data-manifest.json#/datasets/TD-001",
	})

	rendered, err := os.ReadFile(filepath.Join(featureDir, "tasks.md"))
	if err != nil {
		t.Fatal(err)
	}
	text := string(rendered)
	for _, want := range []string{
		"| test_case_refs | `test-catalog.json#/cases/TC-001` |",
		"| test_data_refs | `test-data-manifest.json#/datasets/TD-001` |",
	} {
		if !strings.Contains(text, want) {
			t.Fatalf("tasks.md missing %q:\n%s", want, text)
		}
	}

	exit = Run([]string{
		"tasks", "finalize", "--feature-dir", featureRel, "--format", "json",
	}, &stdout, &stderr, "test")
	if exit != 0 {
		t.Fatalf("tasks finalize exit = %d stderr=%q stdout=%q", exit, stderr.String(), stdout.String())
	}
	exit = Run([]string{
		"implement", "packet-compile", "--feature-dir", featureRel, "--task-id", "T001", "--format", "json",
	}, &stdout, &stderr, "test")
	if exit != 0 {
		t.Fatalf("implement packet-compile exit = %d stderr=%q stdout=%q", exit, stderr.String(), stdout.String())
	}

	packet := readTestDesignJSONMap(t, filepath.Join(featureDir, "implementation-review", "packets", "T001.json"))
	assertStringListEquals(t, packet["test_case_refs"], []string{
		"test-catalog.json#/cases/TC-001",
	})
	assertStringListEquals(t, packet["test_data_refs"], []string{
		"test-data-manifest.json#/datasets/TD-001",
	})
	if packet["test_design_handoff_ref"] == nil || packet["test_design_handoff_sha256"] == nil || packet["test_design_source_fingerprint"] == nil || packet["test_design_state_revision"] == nil {
		t.Fatalf("compiled packet is missing test-design binding: %#v", packet)
	}
	if err := os.WriteFile(filepath.Join(projectRoot, "src", "approval.go"), []byte("package approval\n// stale after task handoff\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	stderr.Reset()
	exit = Run([]string{
		"implement", "packet-compile", "--feature-dir", featureRel, "--task-id", "T001", "--format", "json",
	}, &stdout, &stderr, "test")
	if exit == 0 || !strings.Contains(stdout.String()+stderr.String(), "test-design") {
		t.Fatalf("stale test-design packet compile exit=%d stderr=%q stdout=%q", exit, stderr.String(), stdout.String())
	}
}

func TestTestDesignImplementContinuesAfterExecutionStartsButStillRejectsArtifactTamper(t *testing.T) {
	fixture := setupValidatedTestDesignProjectionFixture(t, "feature", 2)
	requireTestDesignOK(t, fixture.command("handoff", "--format", "json"))
	templatesDir := filepath.Join(fixture.projectRoot, ".specify", "templates")
	if err := writeTestDesignJSONFixture(filepath.Join(templatesDir, "task-index-template.json"), map[string]any{
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
		"test_design_handoff_ref": nil, "test_design_handoff_sha256": nil,
		"test_design_source_fingerprint": nil, "test_design_state_revision": nil,
		"test_design_artifact_digests": map[string]any{},
	}); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(templatesDir, "task-packet-template.json"), map[string]any{
		"version": 2, "task_id": nil, "source_task_ref": nil, "source_revision": nil,
		"objective": nil, "policy_refs": []any{}, "user_confirmed_deferral_refs": []any{},
		"implementation_target_ref": nil, "authoritative_refs": []any{}, "read_scope": []any{},
		"write_scope": []any{}, "forbidden_drift": []any{}, "acceptance_refs": []any{},
		"must_preserve_refs": []any{}, "consequence_obligation_refs": []any{},
		"capability_operation_refs": []any{}, "fidelity_refs": []any{},
		"ui_contract": map[string]any{
			"fidelity_level": "none", "interaction_matrix": []any{}, "editing_matrix": []any{}, "required_states": []any{}, "data_state_matrix": []any{}, "required_evidence": []any{}, "must_not": []any{},
		},
		"validation_policy": map[string]any{}, "task_checks": []any{}, "required_validation": []any{},
		"required_consumer_evidence": []any{}, "test_case_refs": []any{}, "test_data_refs": []any{},
		"done_condition": []any{}, "stop_and_reopen_conditions": []any{}, "recovery": nil,
		"test_design_handoff_ref": nil, "test_design_handoff_sha256": nil,
		"test_design_source_fingerprint": nil, "test_design_state_revision": nil,
		"test_design_artifact_digests": map[string]any{},
	}); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(templatesDir, "task-lifecycle-template.json"), map[string]any{
		"version": 1, "revision": 0, "task_id": nil, "task_ref": nil, "source_revision": nil,
		"execution_mode": "leader-direct", "packet_ref": nil, "result_ref": nil, "status": "pending",
		"changed_paths": []any{}, "validation": []any{}, "review": nil,
		"ui_verification": map[string]any{"applicable": false}, "obligation_evidence": []any{},
		"blockers": []any{}, "recovery": nil,
	}); err != nil {
		t.Fatal(err)
	}

	definitionRaw, err := json.Marshal(map[string]any{
		"title": "Execution may implement a frozen test design", "source_revision": 8,
		"tasks": []any{
			map[string]any{
				"id": "T001", "objective": "Implement approval", "dependencies": []any{},
				"expected_write_scope": []any{"src/approval.go"}, "required_refs": []any{"docs/test-design.md"},
				"acceptance": []any{"Approval behavior matches TC-001"}, "verification": []any{"gofmt check"},
				"test_case_refs": []any{"test-catalog.json#/cases/TC-001"},
				"test_data_refs": []any{"test-data-manifest.json#/datasets/TD-001"},
			},
			map[string]any{
				"id": "T002", "objective": "Implement reversal", "dependencies": []any{"T001"},
				"expected_write_scope": []any{"src/reversal.go"}, "required_refs": []any{"docs/test-design.md"},
				"acceptance": []any{"Reversal behavior matches TC-002"}, "verification": []any{"go test ./..."},
				"test_case_refs": []any{"test-catalog.json#/cases/TC-002"},
				"test_data_refs": []any{"test-data-manifest.json#/datasets/TD-002"},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	assertTaskRuntimeCommandOK(t, []string{
		"tasks", "build", "--feature-dir", fixture.featureRel, "--definition-json", string(definitionRaw), "--format", "json",
	})
	assertTaskRuntimeCommandOK(t, []string{"tasks", "finalize", "--feature-dir", fixture.featureRel, "--format", "json"})
	taskIndexPath := filepath.Join(fixture.projectRoot, filepath.FromSlash(fixture.featureRel), "task-index.json")
	taskIndex := readTestDesignJSONMap(t, taskIndexPath)
	taskList, _ := taskIndex["tasks"].([]any)
	firstTask, _ := taskList[0].(map[string]any)
	originalTaskStatus := firstTask["status"]
	firstTask["status"] = "deferred"
	if err := writeTestDesignJSONFixture(taskIndexPath, taskIndex); err != nil {
		t.Fatal(err)
	}
	sourcePath := filepath.Join(fixture.projectRoot, "src", "approval.go")
	originalSource, err := os.ReadFile(sourcePath)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(sourcePath, []byte("package approval\n// deferred before execution\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	deferredExit, deferredEnv := runTaskRuntimeCommand(t, []string{
		"implement", "packet-compile", "--feature-dir", fixture.featureRel, "--task-id", "T001", "--format", "json",
	})
	if deferredExit == 0 || deferredEnv.Status == "ok" || !strings.Contains(testDesignProjectionEnvelopeText(deferredEnv), "sources are stale") {
		t.Fatalf("pre-execution deferred task bypassed live source freshness: exit=%d env=%#v", deferredExit, deferredEnv)
	}
	if err := os.WriteFile(sourcePath, originalSource, 0o644); err != nil {
		t.Fatal(err)
	}
	firstTask["status"] = originalTaskStatus
	if err := writeTestDesignJSONFixture(taskIndexPath, taskIndex); err != nil {
		t.Fatal(err)
	}
	compiled := assertTaskRuntimeCommandOK(t, []string{
		"implement", "packet-compile", "--feature-dir", fixture.featureRel, "--task-id", "T001", "--format", "json",
	})
	packetRef := strings.TrimSpace(asString(compiled["packet_ref"]))
	if packetRef == "" {
		t.Fatalf("T001 packet compile returned no packet_ref: %#v", compiled)
	}
	assertTaskRuntimeCommandOK(t, []string{
		"implement", "task-start", "--feature-dir", fixture.featureRel, "--task-id", "T001",
		"--execution-mode", "delegated", "--packet-ref", packetRef, "--format", "json",
	})
	if err := os.WriteFile(sourcePath, []byte("package approval\n// implementation started\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	result := `{"task_id":"T001","status":"success","changed_files":["src/approval.go"],"validation_results":[{"command":"gofmt check","status":"passed","output":"PASS"}],"blockers":[],"suggested_recovery_actions":[]}`
	assertTaskRuntimeCommandOK(t, []string{
		"implement", "result-merge", "--feature-dir", fixture.featureRel, "--task-id", "T001", "--result-json", result, "--format", "json",
	})
	assertTaskRuntimeCommandOK(t, []string{
		"implement", "task-accept", "--feature-dir", fixture.featureRel, "--task-id", "T001", "--format", "json",
	})
	assertTaskRuntimeCommandOK(t, []string{
		"implement", "packet-compile", "--feature-dir", fixture.featureRel, "--task-id", "T002", "--format", "json",
	})

	for _, tamper := range []struct {
		name string
		path string
	}{
		{name: "canonical catalog", path: filepath.Join(fixture.artifactRoot, "test-catalog.json")},
		{name: "published handoff", path: filepath.Join(fixture.artifactRoot, "handoff-to-tasks.json")},
	} {
		t.Run(tamper.name, func(t *testing.T) {
			original, readErr := os.ReadFile(tamper.path)
			if readErr != nil {
				t.Fatal(readErr)
			}
			if writeErr := os.WriteFile(tamper.path, append(append([]byte{}, original...), ' '), 0o644); writeErr != nil {
				t.Fatal(writeErr)
			}
			exit, env := runTaskRuntimeCommand(t, []string{
				"implement", "packet-compile", "--feature-dir", fixture.featureRel, "--task-id", "T002", "--format", "json",
			})
			if exit == 0 || env.Status == "ok" || !strings.Contains(testDesignProjectionEnvelopeText(env), "test-design") {
				t.Fatalf("Implement accepted %s tamper after execution started: exit=%d env=%#v", tamper.name, exit, env)
			}
			if writeErr := os.WriteFile(tamper.path, original, 0o644); writeErr != nil {
				t.Fatal(writeErr)
			}
		})
	}
}

func TestImplementTestDesignIntegrityModeStartsOnlyAfterExecution(t *testing.T) {
	for _, tc := range []struct {
		status  string
		started bool
	}{
		{status: "pending", started: false},
		{status: "ready", started: false},
		{status: "deferred", started: false},
		{status: "in_progress", started: true},
		{status: "implemented", started: true},
		{status: "accepted", started: true},
		{status: "blocked", started: true},
		{status: "failed", started: true},
	} {
		t.Run(tc.status, func(t *testing.T) {
			index := map[string]any{"tasks": []any{map[string]any{"id": "T001", "status": tc.status}}}
			if got := implementTaskIndexExecutionStarted(index); got != tc.started {
				t.Fatalf("execution-started(%s)=%t, want %t", tc.status, got, tc.started)
			}
		})
	}
}

func TestTestDesignTasksBuildFailsClosedWhenWorkspaceExistsWithoutHandoff(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	templatesDir := filepath.Join(projectRoot, ".specify", "templates")
	if err := os.MkdirAll(filepath.Join(featureDir, "test-design"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(templatesDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(featureDir, "test-design", "test-state.json"), map[string]any{"status": "active"}); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(templatesDir, "task-index-template.json"), map[string]any{
		"version": 2, "status": "draft", "tasks": []any{}, "transition": map[string]any{},
	}); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)
	definition, _ := json.Marshal(map[string]any{"tasks": []any{}})
	var stdout, stderr bytes.Buffer
	exit := Run([]string{"tasks", "build", "--feature-dir", featureRel, "--definition-json", string(definition), "--format", "json"}, &stdout, &stderr, "test")
	if exit == 0 || !strings.Contains(stdout.String()+stderr.String(), "no fresh handed-off bundle") {
		t.Fatalf("active workspace without handoff exit=%d stderr=%q stdout=%q", exit, stderr.String(), stdout.String())
	}
}

func TestTestDesignTasksBuildHonorsSelectedOrRequiredPlanGate(t *testing.T) {
	for _, decision := range []string{"selected", "required"} {
		t.Run(decision, func(t *testing.T) {
			projectRoot := t.TempDir()
			featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
			featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
			templatesDir := filepath.Join(projectRoot, ".specify", "templates")
			if err := os.MkdirAll(featureDir, 0o755); err != nil {
				t.Fatal(err)
			}
			if err := os.MkdirAll(templatesDir, 0o755); err != nil {
				t.Fatal(err)
			}
			templateRaw, err := os.ReadFile(filepath.Join("..", "..", "templates", "task-index-template.json"))
			if err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(filepath.Join(templatesDir, "task-index-template.json"), templateRaw, 0o644); err != nil {
				t.Fatal(err)
			}
			if err := writeTestDesignJSONFixture(filepath.Join(featureDir, "plan-contract.json"), map[string]any{
				"status": "ready", "source_revision": 7, "acceptance_refs": []any{},
				"test_design_gate": map[string]any{
					"decision": decision, "reason_refs": []any{"spec-contract.json#/acceptance/AC-001"},
					"projection_binding": map[string]any{
						"publication_ref": nil, "publication_sha256": nil,
						"projection_ref": nil, "projection_sha256": nil,
						"source_fingerprint": nil, "state_revision": nil,
					},
				},
			}); err != nil {
				t.Fatal(err)
			}
			definition, err := json.Marshal(map[string]any{
				"title": "Plan-selected Test Design", "source_revision": 7,
				"tasks": []any{map[string]any{
					"id": "T001", "objective": "Implement the selected design",
					"dependencies": []any{}, "expected_write_scope": []any{"src/feature.go"},
					"required_refs": []any{}, "acceptance": []any{"Selected design is implemented"},
					"verification": []any{"go test ./..."}, "test_case_refs": []any{}, "test_data_refs": []any{},
				}},
			})
			if err != nil {
				t.Fatal(err)
			}
			withTestDesignCWD(t, projectRoot)
			var stdout, stderr bytes.Buffer
			exit := Run([]string{
				"tasks", "build", "--feature-dir", featureRel,
				"--definition-json", string(definition), "--format", "json",
			}, &stdout, &stderr, "test")
			combined := strings.ToLower(stdout.String() + stderr.String())
			if exit == 0 || !strings.Contains(combined, decision) || !strings.Contains(combined, "handoff-to-tasks.json") {
				t.Fatalf("plan gate %s was bypassed: exit=%d stderr=%q stdout=%q", decision, exit, stderr.String(), stdout.String())
			}
		})
	}
}

func TestTestDesignTasksRejectConflictingPlanGatePaths(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(filepath.Join(featureDir, "plan"), 0o755); err != nil {
		t.Fatal(err)
	}
	gate := func(decision string) map[string]any {
		return map[string]any{
			"test_design_gate": map[string]any{
				"decision":    decision,
				"reason_refs": []any{},
				"projection_binding": map[string]any{
					"publication_ref": nil, "publication_sha256": nil,
					"projection_ref": nil, "projection_sha256": nil,
					"source_fingerprint": nil, "state_revision": nil,
				},
			},
		}
	}
	if err := writeTestDesignJSONFixture(filepath.Join(featureDir, "plan-contract.json"), gate("not_selected")); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(featureDir, "plan", "plan-contract.json"), gate("required")); err != nil {
		t.Fatal(err)
	}
	_, err := taskControlPlanTestDesignGateDecision(projectRoot, featureRel)
	if err == nil || !strings.Contains(err.Error(), "conflicting plan-contract test_design_gate decisions") {
		t.Fatalf("conflicting gate paths were accepted: %v", err)
	}
}

func TestTestDesignTasksRejectConflictingPlanProjectionBindingsAcrossPlanPaths(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(filepath.Join(featureDir, "plan"), 0o755); err != nil {
		t.Fatal(err)
	}
	gate := func(projectionRef, projectionSHA string) map[string]any {
		return map[string]any{
			"test_design_gate": map[string]any{
				"decision":    "selected",
				"reason_refs": []any{},
				"projection_binding": map[string]any{
					"publication_ref":    filepath.ToSlash(filepath.Join(featureRel, "test-design", "test-design-publication.json")),
					"publication_sha256": strings.Repeat("a", 64),
					"projection_ref":     projectionRef,
					"projection_sha256":  projectionSHA,
					"source_fingerprint": strings.Repeat("b", 64),
					"state_revision":     7,
				},
			},
		}
	}
	if err := writeTestDesignJSONFixture(filepath.Join(featureDir, "plan-contract.json"), gate(
		filepath.ToSlash(filepath.Join(featureRel, "test-design", "projections", "tdproj-a.json")),
		strings.Repeat("c", 64),
	)); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(featureDir, "plan", "plan-contract.json"), gate(
		filepath.ToSlash(filepath.Join(featureRel, "test-design", "projections", "tdproj-b.json")),
		strings.Repeat("d", 64),
	)); err != nil {
		t.Fatal(err)
	}
	_, err := taskControlPlanTestDesignGateDecision(projectRoot, featureRel)
	if err == nil || !strings.Contains(err.Error(), "conflicting plan-contract test_design_gate projection_binding") {
		t.Fatalf("conflicting projection bindings were accepted: %v", err)
	}
}

func TestTestDesignTasksRejectPartialPlanProjectionBinding(t *testing.T) {
	plan := map[string]any{
		"test_design_gate": map[string]any{
			"decision":    "selected",
			"reason_refs": []any{"spec-contract.json#/acceptance/AC-001"},
			"projection_binding": map[string]any{
				"publication_ref":    "specs/001-test-design/test-design/test-design-publication.json",
				"publication_sha256": nil,
				"projection_ref":     nil,
				"projection_sha256":  nil,
				"source_fingerprint": nil,
				"state_revision":     nil,
			},
		},
	}
	_, err := taskControlParsePlanTestDesignGate(plan, "plan-contract.json")
	if err == nil || !strings.Contains(err.Error(), "entirely null or entirely populated") {
		t.Fatalf("partial projection binding was accepted: %v", err)
	}
}

func TestTestDesignTasksRejectNonIntegerPlanProjectionRevision(t *testing.T) {
	for _, revision := range []any{1.5, "1", true} {
		plan := map[string]any{
			"test_design_gate": map[string]any{
				"decision":    "selected",
				"reason_refs": []any{},
				"projection_binding": map[string]any{
					"publication_ref":    "specs/001-test-design/test-design/test-design-publication.json",
					"publication_sha256": strings.Repeat("a", 64),
					"projection_ref":     "specs/001-test-design/test-design/projections/tdproj-plan.json",
					"projection_sha256":  strings.Repeat("b", 64),
					"source_fingerprint": strings.Repeat("c", 64),
					"state_revision":     revision,
				},
			},
		}
		_, err := taskControlParsePlanTestDesignGate(plan, "plan-contract.json")
		if err == nil || !strings.Contains(err.Error(), "state_revision must be a positive integer") {
			t.Fatalf("non-integer revision %#v was accepted: %v", revision, err)
		}
	}
}

func TestTestDesignTasksRequireFreshCanonicalPlanProjectionBinding(t *testing.T) {
	fixture := setupValidatedTestDesignProjectionFixture(t, "feature", 1)
	publishTestDesignProjectionFixture(t, fixture)
	requireTestDesignOK(t, fixture.command("handoff", "--format", "json"))

	state, err := testDesignReadState(fixture.artifactRoot)
	if err != nil {
		t.Fatal(err)
	}
	requireTestDesignOK(t, fixture.command(
		"publish", "--expected-revision", fmt.Sprint(state.Revision), "--format", "json",
	))
	specBasis := writeTestDesignProjectionBasis(
		t,
		fixture.projectRoot,
		filepath.ToSlash(filepath.Join(fixture.featureRel, "spec-contract.json")),
		map[string]any{"version": 1, "status": "planning-ready"},
	)
	_, projectionRef, projectionSHA := buildTestDesignProjection(t, fixture, "plan", specBasis, "")
	publicationRef := filepath.ToSlash(filepath.Join(fixture.featureRel, "test-design", testDesignPublicationFilename))
	publicationPath := filepath.Join(fixture.projectRoot, filepath.FromSlash(publicationRef))
	publicationRaw, err := os.ReadFile(publicationPath)
	if err != nil {
		t.Fatal(err)
	}
	currentState, err := testDesignReadState(fixture.artifactRoot)
	if err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(fixture.projectRoot, filepath.FromSlash(filepath.Join(fixture.featureRel, "plan-contract.json"))), map[string]any{
		"status":          "ready",
		"source_revision": 7,
		"acceptance_refs": []any{},
		"test_design_gate": map[string]any{
			"decision":    "selected",
			"reason_refs": []any{"spec-contract.json#/acceptance/AC-001"},
			"projection_binding": map[string]any{
				"publication_ref":    publicationRef,
				"publication_sha256": projectionDigest(publicationRaw),
				"projection_ref":     projectionRef,
				"projection_sha256":  projectionSHA,
				"source_fingerprint": currentState.Source.Fingerprint,
				"state_revision":     currentState.Revision,
			},
		},
	}); err != nil {
		t.Fatal(err)
	}

	payload := map[string]any{
		"tasks":                   []any{},
		"test_design_handoff_ref": nil, "test_design_handoff_sha256": nil,
		"test_design_source_fingerprint": nil, "test_design_state_revision": nil,
		"test_design_artifact_digests": map[string]any{},
	}
	if err := taskControlValidateTestDesignBinding(fixture.projectRoot, filepath.Join(fixture.projectRoot, filepath.FromSlash(fixture.featureRel)), payload, true, false); err != nil {
		t.Fatalf("fresh plan projection binding rejected: %v", err)
	}

	projectionPath := filepath.Join(fixture.projectRoot, filepath.FromSlash(projectionRef))
	originalProjection, err := os.ReadFile(projectionPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(projectionPath, append(originalProjection, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
	err = taskControlValidateTestDesignBinding(fixture.projectRoot, filepath.Join(fixture.projectRoot, filepath.FromSlash(fixture.featureRel)), payload, true, false)
	if err == nil || !strings.Contains(err.Error(), "plan-contract test_design_gate projection_binding is stale or invalid") {
		t.Fatalf("stale plan projection binding was accepted: %v", err)
	}
	if err := os.WriteFile(projectionPath, originalProjection, 0o644); err != nil {
		t.Fatal(err)
	}
}

func seedTestDesignScaffoldTemplates(projectRoot string) error {
	artifactDir := filepath.Join(projectRoot, ".specify", "templates", "artifacts")
	if err := os.MkdirAll(artifactDir, 0o755); err != nil {
		return err
	}
	templates := map[string]map[string]any{
		"test-universe.json": {
			"version": 1, "artifact": "test-universe", "feature_ref": "features/001-test-design",
			"obligations": []any{}, "capabilities": []any{}, "scenarios": []any{}, "test_cases": []any{},
		},
		"test-catalog.json": {
			"version": 1, "artifact": "test-catalog", "cases": []any{},
		},
		"test-data-manifest.json": {
			"version": 1, "artifact": "test-data-manifest", "datasets": []any{},
		},
		"coverage-matrix.json": {
			"version": 1, "artifact": "coverage-matrix", "rows": []any{},
		},
	}
	for name, payload := range templates {
		if err := writeTestDesignJSONFixture(filepath.Join(artifactDir, name), payload); err != nil {
			return err
		}
	}
	return nil
}

func writeTestDesignJSONFixture(path string, payload map[string]any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(raw, '\n'), 0o644)
}

func readTestDesignJSONMap(t *testing.T, path string) map[string]any {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		t.Fatal(err)
	}
	return payload
}

func assertStringListEquals(t *testing.T, value any, want []string) {
	t.Helper()
	got := anyStringSlice(value)
	if len(got) != len(want) {
		t.Fatalf("list = %#v, want %#v", got, want)
	}
	for index, item := range want {
		if got[index] != item {
			t.Fatalf("list = %#v, want %#v", got, want)
		}
	}
}

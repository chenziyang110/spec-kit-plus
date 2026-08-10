package main

import (
	"bytes"
	"encoding/json"
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

func TestTasksBuildPreservesTestDesignRefsAndRendersThemInTasksMarkdown(t *testing.T) {
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
	}); err != nil {
		t.Fatal(err)
	}

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
					"test-design-handoff.json#/test_cases/TC-001",
					"test-design-handoff.json#/test_cases/TC-002",
				},
				"test_data_refs": []any{
					"test-design-handoff.json#/test_data/TD-001",
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	oldCWD, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(projectRoot); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(oldCWD) })

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
		"test-design-handoff.json#/test_cases/TC-001",
		"test-design-handoff.json#/test_cases/TC-002",
	})
	assertStringListEquals(t, task["test_data_refs"], []string{
		"test-design-handoff.json#/test_data/TD-001",
	})

	rendered, err := os.ReadFile(filepath.Join(featureDir, "tasks.md"))
	if err != nil {
		t.Fatal(err)
	}
	text := string(rendered)
	for _, want := range []string{
		"| test_case_refs | [test-design-handoff.json#/test_cases/TC-001, test-design-handoff.json#/test_cases/TC-002] |",
		"| test_data_refs | [test-design-handoff.json#/test_data/TD-001] |",
	} {
		if !strings.Contains(text, want) {
			t.Fatalf("tasks.md missing %q:\n%s", want, text)
		}
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
			"capabilities": []any{}, "scenarios": []any{}, "test_cases": []any{},
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

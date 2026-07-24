package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestResultPathForQuickWorkspaceUsesCanonicalHandoffLocation(t *testing.T) {
	project := createResultProject(t, "claude")
	workspace := filepath.Join(project, ".planning", "quick", "001-fix")
	mkdirAll(t, workspace)

	code, payload := runResultInProject(t, project, []string{
		"path",
		"--command", "quick",
		"--workspace", workspace,
		"--lane-id", "lane-a",
	})

	if code != 0 {
		t.Fatalf("result path code = %d payload=%#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["command"] != "quick" {
		t.Fatalf("data.command = %#v, want quick", data["command"])
	}
	if data["integration"] != "claude" {
		t.Fatalf("data.integration = %#v, want claude", data["integration"])
	}
	path := slashPath(asString(data["path"]))
	if !strings.HasSuffix(path, ".planning/quick/001-fix/worker-results/lane-a.json") {
		t.Fatalf("path = %q, want canonical quick handoff suffix", path)
	}
}

func TestResultSubmitNormalizesAndAtomicallyWritesQuickResult(t *testing.T) {
	project := createResultProject(t, "cursor-agent")
	workspace := filepath.Join(project, ".planning", "quick", "001-fix")
	mkdirAll(t, workspace)
	resultFile := filepath.Join(project, "worker-result.json")
	writeJSONFile(t, resultFile, map[string]any{
		"taskId":        "T201",
		"status":        "DONE_WITH_CONCERNS",
		"files_changed": []any{"src/feature.py"},
		"message":       "done with concerns",
		"issues":        []any{"follow-up cleanup remains"},
		"validationResults": []any{
			map[string]any{"command": "pytest -q", "status": "passed", "output": "1 passed"},
		},
	})

	code, payload := runResultInProject(t, project, []string{
		"submit",
		"--command", "quick",
		"--workspace", workspace,
		"--lane-id", "lane-a",
		"--result-file", resultFile,
	})

	if code != 0 {
		t.Fatalf("result submit code = %d payload=%#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	target := asString(data["path"])
	stored := readJSONFile(t, target)
	if stored["status"] != "success" {
		t.Fatalf("stored.status = %#v, want success", stored["status"])
	}
	if stored["reported_status"] != "done_with_concerns" {
		t.Fatalf("stored.reported_status = %#v, want done_with_concerns", stored["reported_status"])
	}
	requireStringArrayEqual(t, stored["changed_files"], []string{"src/feature.py"})
	requireStringArrayEqual(t, stored["concerns"], []string{"follow-up cleanup remains"})
	results, ok := stored["validation_results"].([]any)
	if !ok || len(results) != 1 {
		t.Fatalf("validation_results = %#v, want one item", stored["validation_results"])
	}
	validation := requireObjectValue(t, results[0])
	if validation["status"] != "passed" {
		t.Fatalf("validation status = %#v, want passed", validation["status"])
	}
}

func TestResultSubmitRejectsObsoleteUIResultFields(t *testing.T) {
	project := createResultProject(t, "cursor-agent")
	workspace := filepath.Join(project, ".planning", "quick", "001-fix")
	mkdirAll(t, workspace)
	resultFile := filepath.Join(project, "worker-result.json")
	writeJSONFile(t, resultFile, map[string]any{
		"task_id": "lane-a",
		"status":  "success",
		"uiEvidence": []any{
			map[string]any{"kind": "visual_capture", "ref": "evidence/screen.png"},
		},
	})

	code, payload := runResultInProject(t, project, []string{
		"submit",
		"--command", "quick",
		"--workspace", workspace,
		"--lane-id", "lane-a",
		"--result-file", resultFile,
	})

	if code == 0 {
		t.Fatalf("result submit unexpectedly passed: %#v", payload)
	}
	if payload["status"] != "invalid" {
		t.Fatalf("status = %#v, want invalid", payload["status"])
	}
	if !strings.Contains(asString(payload["summary"]), "uiEvidence") {
		t.Fatalf("summary = %q, want obsolete field name", asString(payload["summary"]))
	}
	if _, err := os.Stat(filepath.Join(workspace, "worker-results", "lane-a.json")); !os.IsNotExist(err) {
		t.Fatalf("obsolete UI result should not write canonical handoff, stat err=%v", err)
	}
}

func TestResultSubmitRejectsCodexProjectsAndRedirectsToTeamSurface(t *testing.T) {
	project := createResultProject(t, "codex")
	resultFile := filepath.Join(project, "worker-result.json")
	writeJSONFile(t, resultFile, map[string]any{"task_id": "T001", "status": "success"})

	code, payload := runResultInProject(t, project, []string{
		"submit",
		"--command", "implement",
		"--feature-dir", ".specify/features/001-feature",
		"--task-id", "T001",
		"--result-file", resultFile,
	})

	if code == 0 {
		t.Fatalf("codex result submit unexpectedly passed: %#v", payload)
	}
	if !strings.Contains(asString(payload["summary"]), "sp-teams submit-result") {
		t.Fatalf("summary = %q, want teams redirect", asString(payload["summary"]))
	}
}

func TestResultPathForCodexRequiresRequestIDWithoutPanic(t *testing.T) {
	project := createResultProject(t, "codex")

	code, payload := runResultInProject(t, project, []string{
		"path",
		"--command", "implement",
		"--feature-dir", ".specify/features/001-feature",
		"--task-id", "T001",
	})

	if code == 0 {
		t.Fatalf("codex path unexpectedly passed: %#v", payload)
	}
	summary := asString(payload["summary"])
	if !strings.Contains(summary, "Codex result handoff paths are runtime-managed") || !strings.Contains(summary, "--request-id <id>") {
		t.Fatalf("summary = %q, want request-id guidance", summary)
	}
}

func TestResultPathForCodexRequestIDUsesRuntimeManagedPath(t *testing.T) {
	project := createResultProject(t, "codex")

	code, payload := runResultInProject(t, project, []string{
		"path",
		"--command", "implement",
		"--request-id", "req-t001",
	})

	if code != 0 {
		t.Fatalf("codex path code = %d payload=%#v", code, payload)
	}
	data := requireObject(t, payload, "data")
	if data["integration"] != "codex" {
		t.Fatalf("integration = %#v, want codex", data["integration"])
	}
	path := slashPath(asString(data["path"]))
	if !strings.HasSuffix(path, ".specify/teams/state/results/req-t001.json") {
		t.Fatalf("path = %q, want runtime-managed codex result path", path)
	}
}

func TestResultPathRejectsLaneTraversalBeforeCanonicalPathEscape(t *testing.T) {
	project := createResultProject(t, "claude")
	workspace := filepath.Join(project, ".planning", "quick", "001-fix")
	mkdirAll(t, workspace)

	code, payload := runResultInProject(t, project, []string{
		"path",
		"--command", "quick",
		"--workspace", workspace,
		"--lane-id", "../escape",
	})

	if code == 0 {
		t.Fatalf("traversal lane unexpectedly passed: %#v", payload)
	}
	if !strings.Contains(asString(payload["summary"]), "single path segment") {
		t.Fatalf("summary = %q, want path-segment rejection", asString(payload["summary"]))
	}
}

func createResultProject(t *testing.T, integration string) string {
	t.Helper()
	project := t.TempDir()
	specifyDir := filepath.Join(project, ".specify")
	mkdirAll(t, specifyDir)
	writeJSONFile(t, filepath.Join(specifyDir, "integration.json"), map[string]any{
		"integration": integration,
	})
	return project
}

func runResultInProject(t *testing.T, project string, args []string) (int, map[string]any) {
	t.Helper()
	oldCwd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(project); err != nil {
		t.Fatal(err)
	}
	defer func() {
		if err := os.Chdir(oldCwd); err != nil {
			t.Fatal(err)
		}
	}()
	var stdout bytes.Buffer
	code := runResult(args, &stdout)
	return code, decodeJSONObject(t, stdout.Bytes())
}

func mkdirAll(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatal(err)
	}
}

func writeJSONFile(t *testing.T, path string, payload map[string]any) {
	t.Helper()
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(raw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func readJSONFile(t *testing.T, path string) map[string]any {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return decodeJSONObject(t, raw)
}

func slashPath(path string) string {
	return strings.ReplaceAll(path, "\\", "/")
}

func requireStringArrayEqual(t *testing.T, raw any, want []string) {
	t.Helper()
	values, ok := raw.([]any)
	if !ok {
		t.Fatalf("value = %#v, want array", raw)
	}
	if len(values) != len(want) {
		t.Fatalf("value = %#v, want %#v", raw, want)
	}
	for index, value := range values {
		if value != want[index] {
			t.Fatalf("value[%d] = %#v, want %q", index, value, want[index])
		}
	}
}

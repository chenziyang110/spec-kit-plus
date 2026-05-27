package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestContractChecksPassForCurrentPlanningReadyPackage(t *testing.T) {
	results := runLintForTest(t, filepath.Join("testdata", "good-spec"), "standard")

	requireCheckStatus(t, results, "required-artifacts", statusPass)
	requireCheckStatus(t, results, "workflow-state-readiness", statusPass)
	requireCheckStatus(t, results, "handoff-json-schema", statusPass)
	requireCheckStatus(t, results, "planning-gate-ready", statusPass)
	requireCheckStatus(t, results, "source-signal-disposition", statusPass)
	requireCheckStatus(t, results, "must-preserve-coverage", statusPass)
	requireCheckStatus(t, results, "review-state-approved", statusPass)
	requireCheckStatus(t, results, "quality-gate-summary", statusPass)
}

func TestContractChecksRejectPlanningBlockers(t *testing.T) {
	tests := []struct {
		name      string
		mutate    func(t *testing.T, dir string)
		checkName string
	}{
		{
			name: "missing handoff json",
			mutate: func(t *testing.T, dir string) {
				t.Helper()
				if err := os.Remove(filepath.Join(dir, "brainstorming", "handoff-to-specify.json")); err != nil {
					t.Fatalf("remove handoff json: %v", err)
				}
			},
			checkName: "required-artifacts",
		},
		{
			name: "invalid handoff json",
			mutate: func(t *testing.T, dir string) {
				t.Helper()
				writeFileForTest(t, dir, filepath.Join("brainstorming", "handoff-to-specify.json"), "{not json")
			},
			checkName: "handoff-json-schema",
		},
		{
			name: "malformed handoff schema types",
			mutate: func(t *testing.T, dir string) {
				t.Helper()
				mutateHandoffForTest(t, dir, func(h map[string]any) {
					h["source_files_read"] = "spec.md"
				})
			},
			checkName: "handoff-json-schema",
		},
		{
			name: "non string handoff status",
			mutate: func(t *testing.T, dir string) {
				t.Helper()
				mutateHandoffForTest(t, dir, func(h map[string]any) {
					h["status"] = 123
				})
			},
			checkName: "handoff-json-schema",
		},
		{
			name: "blocked planning gate",
			mutate: func(t *testing.T, dir string) {
				t.Helper()
				mutateHandoffForTest(t, dir, func(h map[string]any) {
					h["planning_gate_status"] = "blocked_by_hard_unknowns"
				})
			},
			checkName: "planning-gate-ready",
		},
		{
			name: "hard unknowns",
			mutate: func(t *testing.T, dir string) {
				t.Helper()
				mutateHandoffForTest(t, dir, func(h map[string]any) {
					h["hard_unknown_count"] = 1
				})
			},
			checkName: "planning-gate-ready",
		},
		{
			name: "clarification blocker disposition",
			mutate: func(t *testing.T, dir string) {
				t.Helper()
				mutateHandoffForTest(t, dir, func(h map[string]any) {
					h["source_signal_disposition"] = []any{
						map[string]any{
							"id":          "SSD-001",
							"signal":      "ambiguous scope",
							"disposition": "clarification_blocker",
						},
					}
				})
			},
			checkName: "source-signal-disposition",
		},
		{
			name: "untraceable must preserve row",
			mutate: func(t *testing.T, dir string) {
				t.Helper()
				mutateHandoffForTest(t, dir, func(h map[string]any) {
					h["must_preserve"] = []any{map[string]any{"status": "mapped"}}
				})
			},
			checkName: "must-preserve-coverage",
		},
		{
			name: "missing user review state",
			mutate: func(t *testing.T, dir string) {
				t.Helper()
				path := filepath.Join(dir, "workflow-state.md")
				content := readFileForTest(t, path)
				content = strings.ReplaceAll(content, "last_user_reviewed_artifact_state: approved", "")
				if err := os.WriteFile(path, []byte(content), 0644); err != nil {
					t.Fatalf("write workflow-state.md: %v", err)
				}
			},
			checkName: "workflow-state-readiness",
		},
		{
			name: "routes away from plan",
			mutate: func(t *testing.T, dir string) {
				t.Helper()
				path := filepath.Join(dir, "workflow-state.md")
				content := readFileForTest(t, path)
				content = strings.ReplaceAll(content, "next_command: /sp.plan", "next_command: /sp.clarify")
				content = strings.ReplaceAll(content, "final_handoff_decision: /sp.plan", "final_handoff_decision: /sp.clarify")
				if err := os.WriteFile(path, []byte(content), 0644); err != nil {
					t.Fatalf("write workflow-state.md: %v", err)
				}
			},
			checkName: "workflow-state-readiness",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dir := copyGoodSpecForTest(t)
			tt.mutate(t, dir)

			results := runLintForTest(t, dir, "standard")

			requireCheckStatus(t, results, tt.checkName, statusFail)
		})
	}
}

func TestReviewRequestedWarnsWithoutBlocking(t *testing.T) {
	dir := copyGoodSpecForTest(t)
	path := filepath.Join(dir, "workflow-state.md")
	content := readFileForTest(t, path)
	content = strings.ReplaceAll(content, "last_user_reviewed_artifact_state: approved", "last_user_reviewed_artifact_state: requested")
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatalf("write workflow-state.md: %v", err)
	}

	results := runLintForTest(t, dir, "standard")

	requireCheckStatus(t, results, "workflow-state-readiness", statusPass)
	requireCheckStatus(t, results, "review-state-approved", statusWarn)
}

func runLintForTest(t *testing.T, dir string, tier string) map[string]checkResult {
	t.Helper()
	results := newRunner(tier).run(loadArtifacts(dir))
	byName := map[string]checkResult{}
	for _, result := range results {
		byName[result.name] = result
	}
	return byName
}

func requireCheckStatus(t *testing.T, results map[string]checkResult, name string, want status) {
	t.Helper()
	got, ok := results[name]
	if !ok {
		t.Fatalf("check %q not found; available checks: %v", name, checkNamesForTest(results))
	}
	if got.status != want {
		t.Fatalf("check %q status = %v (%s); want %v", name, got.status, got.message, want)
	}
}

func checkNamesForTest(results map[string]checkResult) []string {
	names := make([]string, 0, len(results))
	for name := range results {
		names = append(names, name)
	}
	return names
}

func copyGoodSpecForTest(t *testing.T) string {
	t.Helper()
	src := filepath.Join("testdata", "good-spec")
	dst := filepath.Join(t.TempDir(), "good-spec")
	copyDirForTest(t, src, dst)
	return dst
}

func copyDirForTest(t *testing.T, src string, dst string) {
	t.Helper()
	entries, err := os.ReadDir(src)
	if err != nil {
		t.Fatalf("read dir %s: %v", src, err)
	}
	if err := os.MkdirAll(dst, 0755); err != nil {
		t.Fatalf("make dir %s: %v", dst, err)
	}
	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())
		if entry.IsDir() {
			copyDirForTest(t, srcPath, dstPath)
			continue
		}
		data := []byte(readFileForTest(t, srcPath))
		if err := os.WriteFile(dstPath, data, 0644); err != nil {
			t.Fatalf("copy file %s: %v", srcPath, err)
		}
	}
}

func mutateHandoffForTest(t *testing.T, dir string, mutate func(map[string]any)) {
	t.Helper()
	path := filepath.Join(dir, "brainstorming", "handoff-to-specify.json")
	var handoff map[string]any
	if err := json.Unmarshal([]byte(readFileForTest(t, path)), &handoff); err != nil {
		t.Fatalf("parse handoff json: %v", err)
	}
	mutate(handoff)
	data, err := json.MarshalIndent(handoff, "", "  ")
	if err != nil {
		t.Fatalf("marshal handoff json: %v", err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0644); err != nil {
		t.Fatalf("write handoff json: %v", err)
	}
}

func readFileForTest(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read file %s: %v", path, err)
	}
	return string(data)
}

func writeFileForTest(t *testing.T, dir string, rel string, content string) {
	t.Helper()
	path := filepath.Join(dir, rel)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatalf("make parent for %s: %v", path, err)
	}
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatalf("write file %s: %v", path, err)
	}
}

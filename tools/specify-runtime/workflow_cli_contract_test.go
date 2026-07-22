package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestWorkflowCLIRecognizesExactlyNineCurrentSubcommands(t *testing.T) {
	projectRoot, _, featureRel := newWorkflowFeature(t, "001-cli")
	current := map[string][]string{
		"show":           {"workflow", "show", "--feature-dir", featureRel},
		"enter":          {"workflow", "enter", "--feature-dir", featureRel, "--command", "specify"},
		"next":           {"workflow", "next", "--feature-dir", featureRel},
		"complete-stage": {"workflow", "complete-stage", "--feature-dir", featureRel, "--expected-revision", "1"},
		"transition":     {"workflow", "transition", "--feature-dir", featureRel, "--to", "plan", "--expected-revision", "1"},
		"reopen":         {"workflow", "reopen", "--feature-dir", featureRel, "--to", "specify", "--expected-revision", "1", "--reason", "invalidated", "--evidence", "finding", "--invalidated-artifacts", "spec-contract.json"},
		"block":          {"workflow", "block", "--input", filepath.Join(projectRoot, "missing-block.json")},
		"resolve":        {"workflow", "resolve", "--feature-dir", featureRel, "--expected-revision", "1", "--resolution-evidence", "fixed"},
		"closeout":       {"workflow", "closeout", "--feature-dir", featureRel, "--expected-revision", "1"},
	}
	for name, args := range current {
		t.Run(name, func(t *testing.T) {
			args = append(args, "--project-root", projectRoot, "--format", "json")
			var stdout, stderr bytes.Buffer
			_ = Run(args, &stdout, &stderr, "test")
			payload := decodeJSONObject(t, stdout.Bytes())
			requireUnifiedEnvelope(t, payload)
			if strings.Contains(payload["summary"].(string), "unknown workflow subcommand") {
				t.Fatalf("current command was not recognized: %s", stdout.String())
			}
		})
	}

	for _, retired := range []string{"start", "status"} {
		t.Run("retired-"+retired, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run([]string{"workflow", retired, "--project-root", projectRoot, "--format", "json"}, &stdout, &stderr, "test")
			payload := decodeJSONObject(t, stdout.Bytes())
			if code != 2 || payload["status"] != "usage-error" {
				t.Fatalf("retired command = code %d payload %#v, want usage-error", code, payload)
			}
		})
	}
}

func TestWorkflowCLIHelpListsCurrentCommandsOnly(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"workflow", "--help"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("workflow help code = %d", code)
	}
	output := stdout.String()
	for _, command := range []string{"show", "enter", "next", "complete-stage", "transition", "reopen", "block", "resolve", "closeout"} {
		if !strings.Contains(output, "  "+command+"\n") {
			t.Fatalf("workflow help missing %q: %q", command, output)
		}
	}
	for _, retired := range []string{"  start\n", "  status\n"} {
		if strings.Contains(output, retired) {
			t.Fatalf("workflow help retained %q: %q", retired, output)
		}
	}
}

func TestWorkflowCLIBlockReadsStrictJSONFileAndRepeatedEvidence(t *testing.T) {
	projectRoot, _, featureRel := newWorkflowFeature(t, "002-cli-block")
	enter := runWorkflowCLI(t, projectRoot, "enter", "--feature-dir", featureRel, "--command", "specify")
	if enter["status"] != "ok" {
		t.Fatalf("enter = %#v", enter)
	}
	blockInput := map[string]any{
		"feature_dir":       featureRel,
		"expected_revision": 1,
		"category":          "technical-failure",
		"owner":             "agent",
		"cause":             "compiler failed",
		"evidence":          []string{"go test failed"},
		"attempted_recovery": []any{
			map[string]any{"action": "reran focused test", "result": "failure persisted"},
		},
		"affected_scope":    []string{"plan handoff"},
		"exact_next_action": "repair the compiler error",
		"unblock_criteria":  "focused test passes",
	}
	raw, err := json.Marshal(blockInput)
	if err != nil {
		t.Fatal(err)
	}
	inputPath := filepath.Join(projectRoot, "block.json")
	if err := os.WriteFile(inputPath, raw, 0o644); err != nil {
		t.Fatal(err)
	}
	blocked := runWorkflowCLI(t, projectRoot, "block", "--input", inputPath)
	if blocked["status"] != "blocked" || requireObject(t, blocked, "data")["revision"] != float64(2) {
		t.Fatalf("block = %#v", blocked)
	}
	resolved := runWorkflowCLI(t, projectRoot, "resolve", "--feature-dir", featureRel, "--expected-revision", "2", "--resolution-evidence", "compiler repaired", "--resolution-evidence", "focused test passed")
	if resolved["status"] != "ok" || requireObject(t, resolved, "data")["revision"] != float64(3) {
		t.Fatalf("resolve = %#v", resolved)
	}
}

func TestWorkflowCLIBlockInputIsConfinedStrictAndNonSymlinked(t *testing.T) {
	valid := map[string]any{
		"feature_dir":        ".specify/features/001-input",
		"expected_revision":  1,
		"category":           "technical-failure",
		"owner":              "agent",
		"cause":              "failure",
		"evidence":           []string{"evidence"},
		"attempted_recovery": []any{},
		"affected_scope":     []string{"scope"},
		"exact_next_action":  "repair",
		"unblock_criteria":   "passes",
	}
	tests := []struct {
		name      string
		configure func(t *testing.T, projectRoot string) string
	}{
		{name: "outside", configure: func(t *testing.T, _ string) string {
			path := filepath.Join(t.TempDir(), "block.json")
			writeJSONFixture(t, path, valid)
			return path
		}},
		{name: "symlink", configure: func(t *testing.T, projectRoot string) string {
			outside := filepath.Join(t.TempDir(), "block.json")
			writeJSONFixture(t, outside, valid)
			link := filepath.Join(projectRoot, ".specify", "block.json")
			if err := os.Symlink(outside, link); err != nil {
				t.Skipf("symlinks unavailable: %v", err)
			}
			return link
		}},
		{name: "unknown field", configure: func(t *testing.T, projectRoot string) string {
			payload := map[string]any{}
			for key, value := range valid {
				payload[key] = value
			}
			payload["legacy"] = true
			path := filepath.Join(projectRoot, ".specify", "unknown.json")
			writeJSONFixture(t, path, payload)
			return path
		}},
		{name: "type mismatch", configure: func(t *testing.T, projectRoot string) string {
			payload := map[string]any{}
			for key, value := range valid {
				payload[key] = value
			}
			payload["expected_revision"] = "one"
			path := filepath.Join(projectRoot, ".specify", "types.json")
			writeJSONFixture(t, path, payload)
			return path
		}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			projectRoot, _, _ := newWorkflowFeature(t, "001-input")
			path := test.configure(t, projectRoot)
			result := runWorkflowCLI(t, projectRoot, "block", "--input", path)
			if result["status"] != "invalid" && result["status"] != "blocked" && result["status"] != "usage-error" {
				t.Fatalf("unsafe block input = %#v, want fail closed", result)
			}
			if _, err := os.Stat(filepath.Join(projectRoot, ".specify", "features", "001-input", "workflow.json")); !os.IsNotExist(err) {
				t.Fatalf("unsafe block input mutated workflow: %v", err)
			}
		})
	}
}

func runWorkflowCLI(t *testing.T, projectRoot, command string, args ...string) map[string]any {
	t.Helper()
	argv := []string{"workflow", command}
	argv = append(argv, args...)
	argv = append(argv, "--project-root", projectRoot, "--format", "json")
	var stdout, stderr bytes.Buffer
	_ = Run(argv, &stdout, &stderr, "test")
	return decodeJSONObject(t, stdout.Bytes())
}

func writeJSONFixture(t *testing.T, path string, value any) {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		t.Fatal(err)
	}
}

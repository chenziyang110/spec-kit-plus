package cli

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestScanFormatPolicyCommandsGateAndFilterPreparation(t *testing.T) {
	root := t.TempDir()
	for _, rel := range []string{".specify/project-cognition/tmp", "src", "docs"} {
		if err := os.MkdirAll(filepath.Join(root, filepath.FromSlash(rel)), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package app\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "docs", "guide.md"), []byte("# Guide\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeCLIJSON(t, filepath.Join(root, ".specify", "project-cognition", "tmp", "scan-files.json"), map[string]any{
		"files": []string{"src/app.go", "docs/guide.md"},
	})

	old, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	run := func(args ...string) (int, map[string]any, string) {
		t.Helper()
		var stdout, stderr bytes.Buffer
		code := Run(args, &stdout, &stderr, "test")
		payload := map[string]any{}
		if strings.TrimSpace(stdout.String()) != "" {
			if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
				t.Fatalf("decode %v output: %v; stdout=%s stderr=%s", args, err, stdout.String(), stderr.String())
			}
		}
		return code, payload, stderr.String()
	}

	code, inventory, stderr := run("scan-formats", "--format", "json")
	if code != 0 {
		t.Fatalf("scan-formats code=%d stderr=%s payload=%#v", code, stderr, inventory)
	}
	cohorts, ok := inventory["cohorts"].([]any)
	if !ok || len(cohorts) != 2 || inventory["inventory_digest"] == "" {
		t.Fatalf("scan-formats payload = %#v", inventory)
	}
	idsByFormat := map[string]string{}
	for _, raw := range cohorts {
		cohort := raw.(map[string]any)
		idsByFormat[cohort["file_format"].(string)] = cohort["cohort_id"].(string)
	}
	proposal := map[string]any{
		"protocol":         "project_cognition_scan_policy_proposal.v1",
		"inventory_digest": inventory["inventory_digest"],
		"decision_groups": []map[string]any{
			{"cohort_ids": []string{idsByFormat["go"]}, "decision": "semantic_scan", "reason": "application code"},
			{"cohort_ids": []string{idsByFormat["markdown"]}, "decision": "exclude", "reason": "not required for this baseline"},
		},
	}
	proposalJSON, err := json.Marshal(proposal)
	if err != nil {
		t.Fatal(err)
	}
	code, staged, stderr := run("scan-policy-stage", "--proposal-json", string(proposalJSON), "--format", "json")
	if code != 0 || staged["proposal_digest"] == "" || staged["review_required"] != true {
		t.Fatalf("scan-policy-stage code=%d stderr=%s payload=%#v", code, stderr, staged)
	}

	code, blocked, _ := run("scan-prepare", "--format", "json")
	if code == 0 || !cliPayloadContainsError(blocked, "confirmed scan policy") {
		t.Fatalf("scan-prepare before confirmation code=%d payload=%#v", code, blocked)
	}
	code, wrong, _ := run("scan-policy-confirm", "--proposal-digest", "wrong", "--format", "json")
	if code == 0 || !cliPayloadContainsError(wrong, "proposal digest") {
		t.Fatalf("scan-policy-confirm wrong digest code=%d payload=%#v", code, wrong)
	}
	code, confirmed, stderr := run("scan-policy-confirm", "--proposal-digest", staged["proposal_digest"].(string), "--format", "json")
	if code != 0 || confirmed["status"] != "confirmed" || confirmed["policy_digest"] == "" {
		t.Fatalf("scan-policy-confirm code=%d stderr=%s payload=%#v", code, stderr, confirmed)
	}
	code, prepared, stderr := run("scan-prepare", "--format", "json")
	if code != 0 || prepared["status"] != "prepared" || prepared["path_count"] != float64(2) || prepared["packet_count"] != float64(1) || prepared["policy_digest"] != confirmed["policy_digest"] {
		t.Fatalf("scan-prepare code=%d stderr=%s payload=%#v", code, stderr, prepared)
	}
	targetsRaw, err := os.ReadFile(filepath.Join(root, ".specify", "project-cognition", "workbench", "scan-targets.json"))
	if err != nil {
		t.Fatal(err)
	}
	var targets map[string]any
	if err := json.Unmarshal(targetsRaw, &targets); err != nil {
		t.Fatal(err)
	}
	selected := targets["selected_paths"].([]any)
	if len(selected) != 1 || selected[0] != "src/app.go" {
		t.Fatalf("confirmed policy selected_paths = %#v", selected)
	}
}

func cliPayloadContainsError(payload map[string]any, fragment string) bool {
	errors, _ := payload["errors"].([]any)
	for _, raw := range errors {
		if message, ok := raw.(string); ok && strings.Contains(message, fragment) {
			return true
		}
	}
	return false
}

package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestImplementValidationReservesFinishesAndReportsSharedBudget(t *testing.T) {
	project, _, rel := newImplementFeatureProject(t)
	withCwd(t, project)

	var stdout bytes.Buffer
	exit := runImplement([]string{"validation-start", "--feature-dir", rel, "--stage", "implement", "--purpose", "convergence", "--command", "pytest -q", "--task-id", "T001"}, &stdout)
	if exit != 0 {
		t.Fatalf("validation-start exit=%d output=%s", exit, stdout.String())
	}
	started := decodeEnvelope(t, stdout.Bytes()).Data
	if started["run_id"] != "V1" || len(started["fingerprint"].(string)) != 64 || started["used_epochs"] != float64(1) {
		t.Fatalf("unexpected start payload: %#v", started)
	}

	stdout.Reset()
	exit = runImplement([]string{"validation-finish", "--feature-dir", rel, "--run-id", "V1", "--status", "passed", "--evidence-ref", "implementation-review/validation-evidence/V1.txt", "--summary", "Shared convergence passed"}, &stdout)
	if exit != 0 {
		t.Fatalf("validation-finish exit=%d output=%s", exit, stdout.String())
	}
	if decodeEnvelope(t, stdout.Bytes()).Data["status"] != "passed" {
		t.Fatalf("finish payload = %s", stdout.String())
	}

	stdout.Reset()
	exit = runImplement([]string{"validation-status", "--feature-dir", rel}, &stdout)
	if exit != 0 {
		t.Fatalf("validation-status exit=%d output=%s", exit, stdout.String())
	}
	status := decodeEnvelope(t, stdout.Bytes()).Data
	if status["used_epochs"] != float64(1) || status["remaining_epochs"] != float64(2) {
		t.Fatalf("unexpected budget status: %#v", status)
	}
}

func TestImplementValidationRecordsInterruptionAndReusesGate(t *testing.T) {
	project, _, rel := newImplementFeatureProject(t)
	withCwd(t, project)

	common := []string{"validation-start", "--feature-dir", rel, "--stage", "implement", "--purpose", "convergence", "--command", "pytest -q", "--task-id", "T001", "--fingerprint", "sha-a"}
	if exit := runImplement(common, &bytes.Buffer{}); exit != 0 {
		t.Fatalf("first start exit=%d", exit)
	}
	var stdout bytes.Buffer
	exit := runImplement([]string{"validation-finish", "--feature-dir", rel, "--run-id", "V1", "--status", "interrupted", "--failure-kind", "runner_timeout", "--evidence-ref", "implementation-review/validation-evidence/V1-timeout.txt", "--summary", "Execution host stopped the command before a verdict."}, &stdout)
	if exit != 0 {
		t.Fatalf("interrupt finish exit=%d output=%s", exit, stdout.String())
	}
	stdout.Reset()
	exit = runImplement(common, &stdout)
	if exit != 0 {
		t.Fatalf("retry start exit=%d output=%s", exit, stdout.String())
	}
	payload := decodeEnvelope(t, stdout.Bytes()).Data
	if payload["run_id"] != "V1" || payload["attempt_id"] != "V1-A2" || payload["used_attempts"] != float64(2) {
		t.Fatalf("unexpected retry payload: %#v", payload)
	}
}

func TestImplementDeferralRequiresExactConfirmationDigest(t *testing.T) {
	project, feature, rel := newImplementFeatureProject(t)
	withCwd(t, project)
	writeImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T001.json"), map[string]any{
		"task_id": "T001", "status": "blocked",
		"blockers": []any{map[string]any{
			"classification": "external", "owner": "user", "evidence": "Device is unavailable.",
			"exact_next_action": "Run the device check in Review.", "completion_impact": "mandatory_for_completion",
		}},
	})
	proposalPath := filepath.Join(project, "deferral-proposal.json")
	writeImplementJSONFile(t, proposalPath, validImplementDeferralProposal())

	var stdout bytes.Buffer
	exit := runImplement([]string{"deferral-propose", "--feature-dir", rel, "--input", "deferral-proposal.json"}, &stdout)
	if exit != 0 {
		t.Fatalf("propose exit=%d output=%s", exit, stdout.String())
	}
	proposal := decodeEnvelope(t, stdout.Bytes()).Data

	stdout.Reset()
	exit = runImplement([]string{"deferral-confirm", "--feature-dir", rel, "--deferral-id", proposal["deferral_id"].(string), "--proposal-sha256", strings.Repeat("0", 64), "--confirmation-source", "human-reply", "--statement", "Agree to transfer to Review; this is not a pass."}, &stdout)
	if exit != 10 {
		t.Fatalf("wrong digest should block: exit=%d output=%s", exit, stdout.String())
	}

	stdout.Reset()
	exit = runImplement([]string{"deferral-confirm", "--feature-dir", rel, "--deferral-id", proposal["deferral_id"].(string), "--proposal-sha256", proposal["proposal_sha256"].(string), "--confirmation-source", "human-reply", "--statement", "Agree to transfer to Review; this is not a pass."}, &stdout)
	if exit != 0 {
		t.Fatalf("confirm exit=%d output=%s", exit, stdout.String())
	}
	confirmed := decodeEnvelope(t, stdout.Bytes()).Data
	if confirmed["disposition"] != "transferred_to_review" {
		t.Fatalf("unexpected confirmation: %#v", confirmed)
	}
	lifecycle := readImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T001.json"))
	blocker := lifecycle["blockers"].([]any)[0].(map[string]any)
	if lifecycle["status"] != "deferred" || blocker["disposition"] != "user_confirmed_deferral" {
		t.Fatalf("task blocker not bound: %#v", lifecycle)
	}
}

func TestImplementResumeAuditAndCloseoutBlockWhenEvidenceIsMissing(t *testing.T) {
	project, _, rel := newImplementFeatureProject(t)
	withCwd(t, project)

	var stdout bytes.Buffer
	exit := runImplement([]string{"resume-audit", "--feature-dir", rel}, &stdout)
	if exit != 10 {
		t.Fatalf("resume audit should block: exit=%d output=%s", exit, stdout.String())
	}
	env := decodeEnvelope(t, stdout.Bytes())
	if env.Status != "blocked" || len(env.Blockers) == 0 {
		t.Fatalf("expected blockers: %#v", env)
	}

	stdout.Reset()
	exit = runImplement([]string{"closeout", "--feature-dir", rel}, &stdout)
	if exit != 10 {
		t.Fatalf("closeout should block: exit=%d output=%s", exit, stdout.String())
	}
}

func TestImplementCloseoutWritesSummaryAndHandoffWhenAuditIsTrusted(t *testing.T) {
	project, feature, rel := newImplementFeatureProject(t)
	withCwd(t, project)
	writeImplementJSONFile(t, filepath.Join(feature, "worker-results", "T001.json"), map[string]any{
		"task_id": "T001", "status": "success",
		"validation_results": []any{map[string]any{"command": "pytest -q", "status": "passed"}},
		"summary":            "Implemented task",
	})
	writeImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T001.json"), map[string]any{
		"version": 1, "task_id": "T001", "status": "accepted", "blockers": []any{},
	})
	var stdout bytes.Buffer
	if exit := runImplement([]string{"validation-start", "--feature-dir", rel, "--stage", "implement", "--purpose", "convergence", "--command", "pytest -q", "--task-id", "T001"}, &stdout); exit != 0 {
		t.Fatalf("validation start failed: %d %s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runImplement([]string{"validation-finish", "--feature-dir", rel, "--run-id", "V1", "--status", "passed", "--evidence-ref", "implementation-review/validation-evidence/V1.txt", "--summary", "passed"}, &stdout); exit != 0 {
		t.Fatalf("validation finish failed: %d %s", exit, stdout.String())
	}

	stdout.Reset()
	exit := runImplement([]string{"closeout", "--feature-dir", rel}, &stdout)
	if exit != 0 {
		t.Fatalf("closeout exit=%d output=%s", exit, stdout.String())
	}
	payload := decodeEnvelope(t, stdout.Bytes()).Data
	if payload["status"] != "ok" {
		t.Fatalf("unexpected closeout payload: %#v", payload)
	}
	if _, err := os.Stat(filepath.Join(feature, "implementation-summary.md")); err != nil {
		t.Fatalf("summary missing: %v", err)
	}
	if _, err := os.Stat(filepath.Join(feature, "implementation-handoff.json")); err != nil {
		t.Fatalf("handoff missing: %v", err)
	}
}

func newImplementFeatureProject(t *testing.T) (string, string, string) {
	t.Helper()
	project := t.TempDir()
	mustMkdir(t, filepath.Join(project, ".specify"))
	feature := filepath.Join(project, "specs", "001-budget")
	mustMkdir(t, feature)
	writeImplementJSONFile(t, filepath.Join(feature, "task-index.json"), map[string]any{
		"version": 2, "status": "ready",
		"validation_policy": map[string]any{
			"mode": "feature_epochs", "max_epochs": 3, "budget_scope": "implement-review",
			"budget_ref": "implementation-review/validation-runs.json", "heavy_gate_owner": "leader",
		},
		"tasks":           []any{map[string]any{"id": "T001"}},
		"acceptance_refs": []any{"FR-001"},
	})
	writeImplementJSONFile(t, filepath.Join(feature, "workflow.json"), map[string]any{
		"schema_version": 1, "feature_id": "001-budget", "stage": "implement", "status": "active", "revision": 5,
	})
	writeTextFile(t, filepath.Join(feature, "tasks.md"), "# Tasks\n\n- [X] T001 [US1] Update implementation in src/demo.go\n")
	writeTextFile(t, filepath.Join(feature, "implement-tracker.md"), "---\nstatus: resolved\nfeature: 001-budget\n---\n\n## Open Gaps\n\n")
	mustMkdir(t, filepath.Join(feature, "worker-results"))
	return project, feature, filepath.ToSlash(filepath.Join("specs", "001-budget"))
}

func validImplementDeferralProposal() map[string]any {
	return map[string]any{
		"blocker_refs":                 []any{"T001-B01"},
		"affected_task_ids":            []any{"T001"},
		"affected_acceptance_refs":     []any{"FR-001"},
		"deferred_validation_purposes": []any{},
		"exact_excluded_behavior":      "Device evidence is unavailable.",
		"residual_risk":                "Review may find device-specific drift.",
		"risk_severity":                "medium",
		"claims_withheld":              []any{"device verified"},
		"reopen_or_stop_condition":     "Review must obtain device evidence.",
		"downstream_artifact":          "implementation-handoff.json",
		"downstream_owner":             "review",
		"defer_until":                  "review",
	}
}

func writeImplementJSONFile(t *testing.T, path string, payload any) {
	t.Helper()
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	writeTextFile(t, path, string(raw)+"\n")
}

func readImplementJSONFile(t *testing.T, path string) map[string]any {
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

func writeTextFile(t *testing.T, path, content string) {
	t.Helper()
	mustMkdir(t, filepath.Dir(path))
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func mustMkdir(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(path, 0o755); err != nil {
		t.Fatal(err)
	}
}

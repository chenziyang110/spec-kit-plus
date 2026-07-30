package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestImplementValidationReservesFinishesAndReportsSharedBudget(t *testing.T) {
	project, _, rel := newImplementFeatureProject(t)
	withImplementCwd(t, project)

	var stdout bytes.Buffer
	exit := runImplement([]string{"validation-start", "--feature-dir", rel, "--stage", "implement", "--purpose", "convergence", "--command", "pytest -q", "--task-id", "T001"}, &stdout)
	if exit != 0 {
		t.Fatalf("validation-start exit=%d output=%s", exit, stdout.String())
	}
	started := decodeImplementEnvelope(t, stdout.Bytes()).Data
	if started["run_id"] != "V1" || len(started["fingerprint"].(string)) != 64 || started["used_epochs"] != float64(1) {
		t.Fatalf("unexpected start payload: %#v", started)
	}

	stdout.Reset()
	exit = runImplement([]string{"validation-finish", "--feature-dir", rel, "--run-id", "V1", "--status", "passed", "--evidence-ref", "implementation-review/validation-evidence/V1.txt", "--summary", "Shared convergence passed"}, &stdout)
	if exit != 0 {
		t.Fatalf("validation-finish exit=%d output=%s", exit, stdout.String())
	}
	if decodeImplementEnvelope(t, stdout.Bytes()).Data["status"] != "passed" {
		t.Fatalf("finish payload = %s", stdout.String())
	}

	stdout.Reset()
	exit = runImplement([]string{"validation-status", "--feature-dir", rel}, &stdout)
	if exit != 0 {
		t.Fatalf("validation-status exit=%d output=%s", exit, stdout.String())
	}
	status := decodeImplementEnvelope(t, stdout.Bytes()).Data
	if status["used_epochs"] != float64(1) || status["remaining_epochs"] != float64(2) {
		t.Fatalf("unexpected budget status: %#v", status)
	}
}

func TestImplementValidationRecordsInterruptionAndReusesGate(t *testing.T) {
	project, _, rel := newImplementFeatureProject(t)
	withImplementCwd(t, project)

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
	payload := decodeImplementEnvelope(t, stdout.Bytes()).Data
	if payload["run_id"] != "V1" || payload["attempt_id"] != "V1-A2" || payload["used_attempts"] != float64(2) {
		t.Fatalf("unexpected retry payload: %#v", payload)
	}
}

func TestImplementValidationExhaustedGateSlotsStillAllowDeliveryRetry(t *testing.T) {
	project, feature, _ := newImplementFeatureProject(t)
	writeTextFile(t, filepath.Join(project, "src", "demo.txt"), "before\n")
	fingerprint := implementSnapshotSHA256(project, feature)
	for _, gate := range []struct {
		stage, purpose, status string
	}{
		{"implement", "baseline", "passed"},
		{"implement", "convergence", "passed"},
		{"review", "delivery", "failed"},
	} {
		if gate.stage == "review" {
			workflow := readImplementJSONFile(t, filepath.Join(feature, "workflow.json"))
			workflow["stage"] = "review"
			writeImplementJSONFile(t, filepath.Join(feature, "workflow.json"), workflow)
		}
		started, err := reserveImplementValidationEpoch(project, feature, gate.stage, gate.purpose, fingerprint, []string{"pytest -q"}, []string{"T001"})
		if err != nil {
			t.Fatalf("start %s: %v", gate.purpose, err)
		}
		finish := implementValidationFinishRequest{
			RunID: started["run_id"].(string), Status: gate.status,
			EvidenceRefs: []string{"logs/" + gate.purpose + ".txt"}, Summary: gate.purpose + " " + gate.status,
		}
		if gate.status == "failed" {
			finish.FailureKind = "assertion"
		}
		completed, err := completeImplementValidationEpoch(project, feature, finish)
		if err != nil {
			t.Fatalf("finish %s: %v", gate.purpose, err)
		}
		if gate.purpose == "convergence" {
			decision := completed["attempt_decision"].(map[string]any)
			if decision["action"] != "open_logical_gate" || decision["next_attempt_id"] != "V3-A1" {
				t.Fatalf("convergence completion decision = %#v", decision)
			}
		}
	}

	unchanged, err := implementValidationBudgetStatus(project, feature)
	if err != nil {
		t.Fatal(err)
	}
	decision := unchanged["attempt_decision"].(map[string]any)
	if unchanged["remaining_gate_slots"] != 0 || decision["action"] != "repair_before_retry" || decision["can_start_attempt"] != false {
		t.Fatalf("unchanged decision = %#v", unchanged)
	}

	writeTextFile(t, filepath.Join(project, "src", "demo.txt"), "after repair\n")
	repairedFingerprint := implementSnapshotSHA256(project, feature)
	repaired, err := implementValidationBudgetStatus(project, feature)
	if err != nil {
		t.Fatal(err)
	}
	decision = repaired["attempt_decision"].(map[string]any)
	if decision["action"] != "retry_same_gate" || decision["can_start_attempt"] != true || decision["next_attempt_id"] != "V3-A2" {
		t.Fatalf("repaired decision = %#v", decision)
	}
	retry, err := reserveImplementValidationEpoch(project, feature, "review", "delivery", repairedFingerprint, []string{"pytest -q"}, []string{"T001"})
	if err != nil {
		t.Fatal(err)
	}
	if retry["run_id"] != "V3" || retry["attempt_id"] != "V3-A2" || retry["used_epochs"] != 3 {
		t.Fatalf("retry = %#v", retry)
	}
}

func TestImplementValidationPassedBaselineWithChangedSourceOpensConvergence(t *testing.T) {
	project, feature, _ := newImplementFeatureProject(t)
	baseline, err := reserveImplementValidationEpoch(project, feature, "implement", "baseline", "sha-before", []string{"pytest -q"}, []string{"T001"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := completeImplementValidationEpoch(project, feature, implementValidationFinishRequest{
		RunID: baseline["run_id"].(string), Status: "passed",
		EvidenceRefs: []string{"logs/baseline.txt"}, Summary: "Expected pre-change baseline observed.",
	}); err != nil {
		t.Fatal(err)
	}
	decision := implementValidationAttemptDecision([]any{readImplementJSONFile(t, filepath.Join(feature, "implementation-review", "validation-runs.json"))["runs"].([]any)[0]}, 3, "sha-after", "implement")
	if decision["action"] != "open_logical_gate" || decision["next_attempt_id"] != "V2-A1" {
		t.Fatalf("baseline decision = %#v", decision)
	}
	if _, err := reserveImplementValidationEpoch(project, feature, "implement", "baseline", "sha-after", []string{"pytest -q"}, []string{"T001"}); err == nil || !strings.Contains(err.Error(), "baseline is immutable") {
		t.Fatalf("passed baseline retry error = %v", err)
	}
}

func TestImplementValidationReviewRepairAfterConvergenceOpensDelivery(t *testing.T) {
	project, feature, _ := newImplementFeatureProject(t)
	convergence, err := reserveImplementValidationEpoch(project, feature, "implement", "convergence", "sha-before-review", []string{"pytest -q"}, []string{"T001"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := completeImplementValidationEpoch(project, feature, implementValidationFinishRequest{
		RunID: convergence["run_id"].(string), Status: "passed",
		EvidenceRefs: []string{"logs/convergence.txt"}, Summary: "Implement convergence passed.",
	}); err != nil {
		t.Fatal(err)
	}
	workflow := readImplementJSONFile(t, filepath.Join(feature, "workflow.json"))
	workflow["stage"] = "review"
	writeImplementJSONFile(t, filepath.Join(feature, "workflow.json"), workflow)
	writeTextFile(t, filepath.Join(project, "src", "review-fix.txt"), "review-owned repair\n")

	status, err := implementValidationBudgetStatus(project, feature)
	if err != nil {
		t.Fatal(err)
	}
	decision := status["attempt_decision"].(map[string]any)
	if decision["action"] != "open_logical_gate" || decision["next_attempt_id"] != "V2-A1" || decision["reason_code"] != "review-owned-repair-needs-delivery-proof" {
		t.Fatalf("review repair decision = %#v", decision)
	}
}

func TestImplementCloseoutRejectsPassedConvergenceForStaleFingerprint(t *testing.T) {
	project, feature, rel := newImplementFeatureProject(t)
	withImplementCwd(t, project)
	writeTextFile(t, filepath.Join(project, "src", "product.txt"), "before\n")
	writeImplementJSONFile(t, filepath.Join(feature, "worker-results", "T001.json"), map[string]any{
		"task_id": "T001", "status": "success",
		"validation_results": []any{map[string]any{"command": "go test ./...", "status": "passed"}},
		"summary":            "Implemented task",
	})
	writeImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T001.json"), map[string]any{
		"version": 1, "task_id": "T001", "status": "accepted", "blockers": []any{},
	})
	validatedFingerprint := implementSnapshotSHA256(project, feature)
	started, err := reserveImplementValidationEpoch(project, feature, "implement", "convergence", validatedFingerprint, []string{"go test ./..."}, []string{"T001"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := completeImplementValidationEpoch(project, feature, implementValidationFinishRequest{
		RunID: started["run_id"].(string), Status: "passed",
		EvidenceRefs: []string{"implementation-review/validation-evidence/V1.txt"}, Summary: "convergence passed",
	}); err != nil {
		t.Fatal(err)
	}
	writeTextFile(t, filepath.Join(project, "src", "product.txt"), "changed after pass\n")

	var stdout bytes.Buffer
	if exit := runImplement([]string{"closeout", "--feature-dir", rel}, &stdout); exit != 10 {
		t.Fatalf("stale closeout exit=%d output=%s", exit, stdout.String())
	}
	if !strings.Contains(stdout.String(), "current implementation fingerprint") {
		t.Fatalf("stale closeout output=%s", stdout.String())
	}
	if _, err := os.Stat(filepath.Join(feature, implementationHandoffFilename)); !os.IsNotExist(err) {
		t.Fatalf("stale closeout wrote handoff: %v", err)
	}
}

func TestImplementValidationMigratesTransitionalV2DuplicateGates(t *testing.T) {
	project, feature, _ := newImplementFeatureProject(t)
	legacyRun := func(runID, stage, purpose, fingerprint, status string) map[string]any {
		failureKind := any(nil)
		if status == "failed" {
			failureKind = "assertion"
		}
		attempt := map[string]any{
			"attempt_id": runID + "-A1", "fingerprint": fingerprint,
			"commands": []any{"pytest -q"}, "covered_task_ids": []any{"T001"},
			"status": status, "failure_kind": failureKind,
			"evidence_refs": []any{"logs/" + runID + ".txt"}, "summary": runID + " " + status,
			"started_at": "2026-07-27T00:00:00Z", "completed_at": "2026-07-27T00:01:00Z",
		}
		run := map[string]any{"run_id": runID, "stage": stage, "purpose": purpose, "attempts": []any{attempt}}
		for key, value := range attempt {
			run[key] = value
		}
		return run
	}
	writeImplementJSONFile(t, filepath.Join(feature, "implementation-review", "validation-runs.json"), map[string]any{
		"version": 2, "mode": "feature_epochs", "budget_scope": "implement-review", "max_epochs": 3,
		"runs": []any{
			legacyRun("V1", "implement", "convergence", "sha-a", "passed"),
			legacyRun("V2", "implement", "convergence", "sha-b", "passed"),
			legacyRun("V3", "review", "delivery", "sha-c", "failed"),
		},
	})

	status, err := implementValidationBudgetStatus(project, feature)
	if err != nil {
		t.Fatal(err)
	}
	runs := status["runs"].([]any)
	if usedAttempts, ok := numberAsInt(status["used_attempts"]); len(runs) != 2 || !ok || usedAttempts != 3 {
		t.Fatalf("migrated status = %#v", status)
	}
	convergence := runs[0].(map[string]any)
	if len(convergence["attempts"].([]any)) != 2 || convergence["attempt_id"] != "V1-A2" {
		t.Fatalf("migrated convergence = %#v", convergence)
	}
	migration := status["migration"].(map[string]any)
	fromVersion, fromOK := numberAsInt(migration["from_version"])
	legacyCount, countOK := numberAsInt(migration["legacy_run_count"])
	if !fromOK || !countOK || fromVersion != 2 || legacyCount != 3 {
		t.Fatalf("migration provenance = %#v", migration)
	}
}

func TestImplementDeferralRequiresExactConfirmationDigest(t *testing.T) {
	project, feature, rel := newImplementFeatureProject(t)
	withImplementCwd(t, project)
	writeImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T001.json"), map[string]any{
		"task_id": "T001", "status": "blocked",
		"blockers": []any{map[string]any{
			"classification": "external", "owner": "user", "evidence": "Device is unavailable.",
			"exact_next_action": "Run the device check in Review.", "completion_impact": "mandatory_for_completion",
		}},
	})
	proposalRaw, err := json.Marshal(validImplementDeferralProposal())
	if err != nil {
		t.Fatal(err)
	}

	var stdout bytes.Buffer
	exit := runImplement([]string{"deferral-propose", "--feature-dir", rel, "--input-json", string(proposalRaw)}, &stdout)
	if exit != 0 {
		t.Fatalf("propose exit=%d output=%s", exit, stdout.String())
	}
	proposal := decodeImplementEnvelope(t, stdout.Bytes()).Data

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
	confirmed := decodeImplementEnvelope(t, stdout.Bytes()).Data
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
	withImplementCwd(t, project)

	var stdout bytes.Buffer
	exit := runImplement([]string{"resume-audit", "--feature-dir", rel}, &stdout)
	if exit != 10 {
		t.Fatalf("resume audit should block: exit=%d output=%s", exit, stdout.String())
	}
	env := decodeImplementEnvelope(t, stdout.Bytes())
	if env.Status != "blocked" || len(env.Blockers) == 0 {
		t.Fatalf("expected blockers: %#v", env)
	}
	blocker := env.Blockers[0].(map[string]any)
	resume := blocker["resume"].(map[string]any)
	if argv, ok := resume["argv"].([]any); !ok || len(argv) != 7 || argv[1] != "implement" || argv[2] != "resume-audit" || argv[3] != "--feature-dir" || argv[5] != "--format" || argv[6] != "json" {
		t.Fatalf("resume argv = %#v", resume["argv"])
	}

	stdout.Reset()
	exit = runImplement([]string{"closeout", "--feature-dir", rel}, &stdout)
	if exit != 10 {
		t.Fatalf("closeout should block: exit=%d output=%s", exit, stdout.String())
	}
}

func TestImplementCloseoutWritesSummaryAndHandoffWhenAuditIsTrusted(t *testing.T) {
	project, feature, rel := newImplementFeatureProject(t)
	withImplementCwd(t, project)
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
	payload := decodeImplementEnvelope(t, stdout.Bytes()).Data
	if payload["status"] != "ok" {
		t.Fatalf("unexpected closeout payload: %#v", payload)
	}
	if payload["resume_audit"] != nil || payload["transaction"] == nil {
		t.Fatalf("default closeout must be compact and receipt-backed: %#v", payload)
	}
	if _, err := os.Stat(filepath.Join(feature, "implementation-summary.md")); err != nil {
		t.Fatalf("summary missing: %v", err)
	}
	if _, err := os.Stat(filepath.Join(feature, "implementation-handoff.json")); err != nil {
		t.Fatalf("handoff missing: %v", err)
	}

	stdout.Reset()
	if exit := runImplement([]string{"closeout", "--feature-dir", rel, "--view", "full"}, &stdout); exit != 0 {
		t.Fatalf("full closeout exit=%d output=%s", exit, stdout.String())
	}
	if full := decodeImplementEnvelope(t, stdout.Bytes()).Data; full["resume_audit"] == nil {
		t.Fatalf("full closeout omitted diagnostics: %#v", full)
	} else if full["hook_result"] != nil {
		t.Fatalf("full closeout must not claim a Python hook ran: %#v", full)
	} else if full["auto_capture"] != nil {
		t.Fatalf("full closeout must not expose legacy Python capture diagnostics: %#v", full)
	} else if validation, ok := full["artifact_validation"].(map[string]any); !ok || validation["status"] != "ok" {
		t.Fatalf("full closeout omitted Go-native artifact validation: %#v", full)
	}
}

func TestImplementCloseoutFreezesCanonicalReviewContractForPrepare(t *testing.T) {
	project, feature, rel := newImplementFeatureProject(t)
	withImplementCwd(t, project)
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
		t.Fatalf("validation-start exit=%d output=%s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runImplement([]string{"validation-finish", "--feature-dir", rel, "--run-id", "V1", "--status", "passed", "--evidence-ref", "implementation-review/validation-evidence/V1.txt", "--summary", "Implement convergence passed."}, &stdout); exit != 0 {
		t.Fatalf("validation-finish exit=%d output=%s", exit, stdout.String())
	}
	stdout.Reset()
	if exit := runImplement([]string{"closeout", "--feature-dir", rel}, &stdout); exit != 0 {
		t.Fatalf("closeout exit=%d output=%s", exit, stdout.String())
	}

	handoff := readImplementJSONFile(t, filepath.Join(feature, "implementation-handoff.json"))
	taskIndex := readImplementJSONFile(t, filepath.Join(feature, "task-index.json"))
	sourceRevision, _ := numberAsInt(handoff["source_revision"])
	for _, key := range []string{
		"official_entrypoints",
		"system_review_scenarios",
		"review_obligations",
		"human_acceptance_obligations",
		"human_acceptance_scenarios",
		"acceptance_refs",
	} {
		if !reflect.DeepEqual(handoff[key], taskIndex[key]) {
			t.Fatalf("handoff %s = %#v, want %#v", key, handoff[key], taskIndex[key])
		}
	}
	if !reflect.DeepEqual(handoff["task_ids"], []any{"T001"}) {
		t.Fatalf("handoff task_ids = %#v", handoff["task_ids"])
	}
	if strings.TrimSpace(fmt.Sprint(handoff["implementation_fingerprint"])) == "" {
		t.Fatalf("handoff missing implementation_fingerprint: %#v", handoff)
	}
	if handoff["entrypoints"] != nil || handoff["review_scenarios"] != nil || handoff["source_fingerprint"] != nil {
		t.Fatalf("handoff kept legacy aliases: %#v", handoff)
	}

	reviewRel := rel
	reviewFeature := feature
	writeImplementJSONFile(t, filepath.Join(reviewFeature, "workflow.json"), map[string]any{
		"schema_version":           1,
		"feature_id":               "001-budget",
		"revision":                 sourceRevision,
		"stage":                    "review",
		"status":                   "active",
		"summary":                  "review fixture",
		"blocker":                  nil,
		"last_resolution_evidence": []any{},
		"last_reopen":              nil,
		"last_blocker_resolution":  nil,
		"acceptance_sha256":        nil,
	})

	stdout.Reset()
	if code := runReview([]string{"prepare", "--project-root", project, "--feature-dir", reviewRel, "--expected-revision", fmt.Sprintf("%d", sourceRevision), "--format", "json"}, &stdout); code != 0 {
		t.Fatalf("review prepare exit=%d output=%s", code, stdout.String())
	}
	state := readImplementJSONFile(t, filepath.Join(reviewFeature, reviewStateFilename))
	if !reflect.DeepEqual(state["entrypoints"], handoff["official_entrypoints"]) {
		t.Fatalf("review state entrypoints = %#v, want %#v", state["entrypoints"], handoff["official_entrypoints"])
	}
	if !reflect.DeepEqual(state["scenarios"], handoff["system_review_scenarios"]) {
		t.Fatalf("review state scenarios = %#v, want %#v", state["scenarios"], handoff["system_review_scenarios"])
	}
	if !reflect.DeepEqual(state["obligations"], handoff["review_obligations"]) {
		t.Fatalf("review state obligations = %#v, want %#v", state["obligations"], handoff["review_obligations"])
	}
}

func TestImplementSnapshotUsesRealGitIgnoreSemantics(t *testing.T) {
	project, feature, _ := newImplementFeatureProject(t)
	requireGit(t)
	withImplementCwd(t, project)
	writeTextFile(t, filepath.Join(project, ".gitignore"), strings.Join([]string{
		"dist/",
		"*.out",
		"generated/",
		"!generated/",
		"",
	}, "\n"))
	writeTextFile(t, filepath.Join(project, "generated", ".gitignore"), "*\n!keep.txt\n")
	writeTextFile(t, filepath.Join(project, "src", "product.txt"), "before\n")
	gitRun(t, project, "init")
	gitRun(t, project, "config", "user.email", "tests@example.com")
	gitRun(t, project, "config", "user.name", "Spec Runtime Tests")
	gitRun(t, project, "add", ".")
	gitRun(t, project, "commit", "-m", "initial")

	before := implementSnapshotSHA256(project, feature)

	writeTextFile(t, filepath.Join(project, "dist", "bundle.js"), "generated\n")
	writeTextFile(t, filepath.Join(project, "runner.out"), "runtime noise\n")
	writeTextFile(t, filepath.Join(project, "generated", "drop.txt"), "ignored by nested gitignore\n")
	writeTextFile(t, filepath.Join(project, ".specify", "runtime", "leases", "active.json"), "runtime lease\n")
	writeTextFile(t, filepath.Join(project, "web", "test-results", "last-run.json"), "test output\n")
	writeTextFile(t, filepath.Join(project, "web", "playwright-report", "index.html"), "report output\n")
	writeTextFile(t, filepath.Join(feature, "review-evidence", "diagnostic.json"), "{}\n")
	writeTextFile(t, filepath.Join(feature, "implementation-review", "validation-evidence", "V1.txt"), "runner output\n")
	if afterIgnored := implementSnapshotSHA256(project, feature); afterIgnored != before {
		t.Fatalf("ignored/runtime noise changed fingerprint: %s != %s", afterIgnored, before)
	}

	writeTextFile(t, filepath.Join(project, "generated", "keep.txt"), "re-included by nested negation\n")
	if afterKeep := implementSnapshotSHA256(project, feature); afterKeep == before {
		t.Fatal("nonignored nested negation file did not change fingerprint")
	}
}

func TestImplementSnapshotTracksGitHeadTrackedAndUntrackedState(t *testing.T) {
	project, feature, _ := newImplementFeatureProject(t)
	requireGit(t)
	withImplementCwd(t, project)
	writeTextFile(t, filepath.Join(project, "src", "product.txt"), "before\n")
	gitRun(t, project, "init")
	gitRun(t, project, "config", "user.email", "tests@example.com")
	gitRun(t, project, "config", "user.name", "Spec Runtime Tests")
	gitRun(t, project, "add", ".")
	gitRun(t, project, "commit", "-m", "initial")

	before := implementSnapshotSHA256(project, feature)

	writeTextFile(t, filepath.Join(project, "src", "product.txt"), "tracked edit\n")
	afterTracked := implementSnapshotSHA256(project, feature)
	if afterTracked == before {
		t.Fatal("tracked source edit did not change fingerprint")
	}

	gitRun(t, project, "checkout", "--", "src/product.txt")
	clean := implementSnapshotSHA256(project, feature)
	if clean != before {
		t.Fatalf("clean checkout fingerprint = %s, want %s", clean, before)
	}

	writeTextFile(t, filepath.Join(project, "notes.txt"), "nonignored untracked file\n")
	afterUntracked := implementSnapshotSHA256(project, feature)
	if afterUntracked == before {
		t.Fatal("nonignored untracked file did not change fingerprint")
	}

	if err := os.Remove(filepath.Join(project, "notes.txt")); err != nil {
		t.Fatal(err)
	}
	clean = implementSnapshotSHA256(project, feature)
	if clean != before {
		t.Fatalf("clean fingerprint after removing untracked file = %s, want %s", clean, before)
	}

	gitRun(t, project, "commit", "--allow-empty", "-m", "head only change")
	afterHead := implementSnapshotSHA256(project, feature)
	if afterHead == before {
		t.Fatal("HEAD-only change did not change fingerprint")
	}
}

func TestImplementSnapshotTracksQuotedGitPathsViaNULProtocol(t *testing.T) {
	project, feature, _ := newImplementFeatureProject(t)
	requireGit(t)
	withImplementCwd(t, project)
	quotedPath := filepath.Join(project, "docs", "中文 name.txt")
	writeTextFile(t, quotedPath, "before\n")
	gitRun(t, project, "init")
	gitRun(t, project, "config", "user.email", "tests@example.com")
	gitRun(t, project, "config", "user.name", "Spec Runtime Tests")
	gitRun(t, project, "config", "core.quotePath", "true")
	gitRun(t, project, "add", ".")
	gitRun(t, project, "commit", "-m", "initial")

	before := implementSnapshotSHA256(project, feature)
	writeTextFile(t, quotedPath, "after\n")
	after := implementSnapshotSHA256(project, feature)
	if after == before {
		t.Fatal("CJK/space path content change did not change fingerprint")
	}
}

func TestImplementFrozenHandoffPreventsConvergenceRetryButAllowsDelivery(t *testing.T) {
	project, feature, rel := newImplementFeatureProject(t)
	withImplementCwd(t, project)
	writeTextFile(t, filepath.Join(project, "src", "product.txt"), "before\n")
	writeImplementJSONFile(t, filepath.Join(feature, "worker-results", "T001.json"), map[string]any{
		"task_id": "T001", "status": "success",
		"validation_results": []any{map[string]any{"command": "pytest -q", "status": "passed"}},
		"summary":            "Implemented task",
	})
	writeImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T001.json"), map[string]any{
		"version": 1, "task_id": "T001", "status": "accepted", "blockers": []any{},
	})
	convergence, err := reserveImplementValidationEpoch(project, feature, "implement", "convergence", implementSnapshotSHA256(project, feature), []string{"pytest -q"}, []string{"T001"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := completeImplementValidationEpoch(project, feature, implementValidationFinishRequest{
		RunID: convergence["run_id"].(string), Status: "passed",
		EvidenceRefs: []string{"implementation-review/validation-evidence/V1.txt"},
		Summary:      "Implement convergence passed.",
	}); err != nil {
		t.Fatal(err)
	}
	if exit := runImplement([]string{"closeout", "--feature-dir", rel}, &bytes.Buffer{}); exit != 0 {
		t.Fatalf("closeout exit=%d", exit)
	}

	writeTextFile(t, filepath.Join(project, "src", "product.txt"), "after review-owned repair\n")
	repairedFingerprint := implementSnapshotSHA256(project, feature)
	if _, err := reserveImplementValidationEpoch(project, feature, "implement", "convergence", repairedFingerprint, []string{"pytest -q"}, []string{"T001"}); err == nil || !strings.Contains(err.Error(), "immutable") {
		t.Fatalf("expected frozen convergence retry to fail, err=%v", err)
	}

	workflow := readImplementJSONFile(t, filepath.Join(feature, "workflow.json"))
	workflow["stage"] = "review"
	writeImplementJSONFile(t, filepath.Join(feature, "workflow.json"), workflow)
	status, err := implementValidationBudgetStatus(project, feature)
	if err != nil {
		t.Fatal(err)
	}
	decision := status["attempt_decision"].(map[string]any)
	if decision["action"] != "open_logical_gate" || decision["next_attempt_id"] != "V2-A1" {
		t.Fatalf("delivery decision = %#v", decision)
	}
	delivery, err := reserveImplementValidationEpoch(project, feature, "review", "delivery", repairedFingerprint, []string{"pytest -q"}, []string{"T001"})
	if err != nil {
		t.Fatal(err)
	}
	if delivery["run_id"] != "V2" || delivery["attempt_id"] != "V2-A1" {
		t.Fatalf("delivery reservation = %#v", delivery)
	}
}

func TestImplementFrozenHandoffDoesNotBlockReopenedImplementRevision(t *testing.T) {
	project, feature, rel := newImplementFeatureProject(t)
	withImplementCwd(t, project)
	writeTextFile(t, filepath.Join(project, "src", "product.txt"), "before\n")
	writeImplementJSONFile(t, filepath.Join(feature, "worker-results", "T001.json"), map[string]any{
		"task_id": "T001", "status": "success",
		"validation_results": []any{map[string]any{"command": "pytest -q", "status": "passed"}},
		"summary":            "Implemented task",
	})
	writeImplementJSONFile(t, filepath.Join(feature, "implementation-review", "tasks", "T001.json"), map[string]any{
		"version": 1, "task_id": "T001", "status": "accepted", "blockers": []any{},
	})
	convergence, err := reserveImplementValidationEpoch(project, feature, "implement", "convergence", implementSnapshotSHA256(project, feature), []string{"pytest -q"}, []string{"T001"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := completeImplementValidationEpoch(project, feature, implementValidationFinishRequest{
		RunID: convergence["run_id"].(string), Status: "passed",
		EvidenceRefs: []string{"implementation-review/validation-evidence/V1.txt"},
		Summary:      "Implement convergence passed.",
	}); err != nil {
		t.Fatal(err)
	}
	if exit := runImplement([]string{"closeout", "--feature-dir", rel}, &bytes.Buffer{}); exit != 0 {
		t.Fatalf("closeout exit=%d", exit)
	}

	workflow := readImplementJSONFile(t, filepath.Join(feature, "workflow.json"))
	workflow["revision"] = 9
	writeImplementJSONFile(t, filepath.Join(feature, "workflow.json"), workflow)

	writeTextFile(t, filepath.Join(project, "src", "product.txt"), "after reopen\n")
	reopenedFingerprint := implementSnapshotSHA256(project, feature)
	if _, err := reserveImplementValidationEpoch(project, feature, "implement", "convergence", reopenedFingerprint, []string{"pytest -q"}, []string{"T001"}); err != nil {
		t.Fatalf("stale handoff should not freeze reopened implement revision: %v", err)
	}
}

func newImplementFeatureProject(t *testing.T) (string, string, string) {
	t.Helper()
	project := t.TempDir()
	mustMkdir(t, filepath.Join(project, ".specify"))
	feature := filepath.Join(project, ".specify", "features", "001-budget")
	mustMkdir(t, feature)
	writeImplementJSONFile(t, filepath.Join(feature, "task-index.json"), map[string]any{
		"version": 2, "status": "ready",
		"validation_policy": map[string]any{
			"mode": "feature_epochs", "max_epochs": 3, "budget_scope": "implement-review",
			"budget_ref": "implementation-review/validation-runs.json", "heavy_gate_owner": "leader",
		},
		"tasks":           []any{map[string]any{"id": "T001", "task_id": "T001"}},
		"acceptance_refs": []any{"FR-001"},
		"official_entrypoints": []any{map[string]any{
			"id": "EP-1", "command": "npm run dev", "ready_signal": "http://localhost:3000/health",
		}},
		"system_review_scenarios": []any{map[string]any{
			"id": "RS-1", "entrypoint_id": "EP-1", "required": true, "acceptance_refs": []any{"FR-001"},
		}},
		"review_obligations": []any{map[string]any{
			"id": "RO-1", "required": true, "scenario_ids": []any{"RS-1"}, "acceptance_refs": []any{"FR-001"},
		}},
		"human_acceptance_obligations": []any{map[string]any{
			"id": "HA-O-1", "required": true, "acceptance_ref": "FR-001", "scenario_ids": []any{"HA-S-1"},
		}},
		"human_acceptance_scenarios": []any{map[string]any{
			"id": "HA-S-1", "required": true, "review_scenario_ids": []any{"RS-1"}, "entrypoint_id": "EP-1", "actor": "user",
		}},
	})
	writeImplementJSONFile(t, filepath.Join(feature, "spec-contract.json"), map[string]any{"version": 1, "feature_id": "001-budget"})
	writeImplementJSONFile(t, filepath.Join(feature, "plan-contract.json"), map[string]any{"version": 1, "acceptance_refs": []any{"FR-001"}})
	writeImplementJSONFile(t, filepath.Join(feature, "workflow.json"), map[string]any{
		"schema_version": 1, "feature_id": "001-budget", "stage": "implement", "status": "active", "revision": 5,
	})
	writeTextFile(t, filepath.Join(feature, "tasks.md"), "# Tasks\n\n- [X] T001 [US1] Update implementation in src/demo.go\n")
	writeTextFile(t, filepath.Join(feature, "implement-tracker.md"), "---\nstatus: resolved\nfeature: 001-budget\n---\n\n## Open Gaps\n\n")
	mustMkdir(t, filepath.Join(feature, "worker-results"))
	return project, feature, filepath.ToSlash(filepath.Join(".specify", "features", "001-budget"))
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

func decodeImplementEnvelope(t *testing.T, raw []byte) Envelope {
	t.Helper()
	var env Envelope
	if err := json.Unmarshal(raw, &env); err != nil {
		t.Fatalf("decode envelope: %v\n%s", err, raw)
	}
	return env
}

func withImplementCwd(t *testing.T, dir string) {
	t.Helper()
	old, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(dir); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := os.Chdir(old); err != nil {
			t.Fatal(err)
		}
	})
}

func requireGit(t *testing.T) {
	t.Helper()
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git is not available")
	}
}

func gitRun(t *testing.T, dir string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %s failed: %v\n%s", strings.Join(args, " "), err, string(out))
	}
	return string(out)
}

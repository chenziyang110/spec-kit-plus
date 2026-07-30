package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestReviewPrepareRestartStaleArchivesExactState(t *testing.T) {
	projectRoot, featureDir, featureRel := newReviewAcceptWorkflowFeature(t, "106-review-restart")
	writeReviewAcceptWorkflowStateFixture(t, featureDir, "106-review-restart", 4, "review", "active", nil)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), reviewAcceptHandoffFixture(projectRoot, featureDir, 4))

	var out bytes.Buffer
	args := []string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}
	if code := runReview(args, &out); code != 0 {
		t.Fatalf("initial prepare exit = %d output = %s", code, out.String())
	}
	statePath := filepath.Join(featureDir, reviewStateFilename)
	stale := readReviewAcceptJSON(t, statePath)
	stale["source"].(map[string]any)["workflow_revision"] = 3
	mustWriteReviewAcceptJSON(t, statePath, stale)
	previousRaw, err := os.ReadFile(statePath)
	if err != nil {
		t.Fatal(err)
	}
	previousDigest := fmt.Sprintf("%x", sha256.Sum256(previousRaw))

	out.Reset()
	if code := runReview(args, &out); code != 10 {
		t.Fatalf("stale prepare without restart exit = %d output = %s", code, out.String())
	}
	afterBlocked, _ := os.ReadFile(statePath)
	if !bytes.Equal(afterBlocked, previousRaw) {
		t.Fatal("blocked stale prepare changed review-state.json")
	}

	out.Reset()
	restartArgs := append(append([]string{}, args...), "--restart-stale")
	if code := runReview(restartArgs, &out); code != 0 {
		t.Fatalf("restart stale exit = %d output = %s", code, out.String())
	}
	restarted := readReviewAcceptEnvelope(t, out.Bytes())
	if restarted.Data["archived_review_state_ref"] != "review-history/review-state-"+previousDigest+".json" {
		t.Fatalf("restart archive ref = %#v", restarted.Data["archived_review_state_ref"])
	}
	archived, err := os.ReadFile(filepath.Join(featureDir, "review-history", "review-state-"+previousDigest+".json"))
	if err != nil || !bytes.Equal(archived, previousRaw) {
		t.Fatalf("archived state mismatch: err=%v", err)
	}
	state := readReviewAcceptJSON(t, statePath)
	source := state["source"].(map[string]any)
	if int(source["review_cycle"].(float64)) != 2 || source["previous_review_state_sha256"] != previousDigest || source["restart_reason"] != "stale-review-restart" {
		t.Fatalf("restarted source = %#v", source)
	}
}

func TestReviewPrepareRejectsNonCanonicalOrStaleImplementationHandoff(t *testing.T) {
	projectRoot, featureDir, featureRel := newReviewAcceptWorkflowFeature(t, "108-review-handoff-contract")
	writeReviewAcceptWorkflowStateFixture(t, featureDir, "108-review-handoff-contract", 4, "review", "active", nil)
	handoff := reviewAcceptHandoffFixture(projectRoot, featureDir, 4)
	handoff["implementation_fingerprint"] = strings.Repeat("0", 64)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), handoff)

	var out bytes.Buffer
	args := []string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}
	if code := runReview(args, &out); code != 10 {
		t.Fatalf("stale handoff exit = %d output = %s", code, out.String())
	}
	if !strings.Contains(out.String(), "fingerprint is stale") {
		t.Fatalf("stale handoff output = %s", out.String())
	}
	if _, err := os.Stat(filepath.Join(featureDir, reviewStateFilename)); !os.IsNotExist(err) {
		t.Fatalf("stale handoff created review state: %v", err)
	}

	handoff = reviewAcceptHandoffFixture(projectRoot, featureDir, 4)
	delete(handoff, "official_entrypoints")
	handoff["entrypoints"] = []any{"legacy-web"}
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), handoff)
	out.Reset()
	if code := runReview(args, &out); code != 10 {
		t.Fatalf("legacy handoff exit = %d output = %s", code, out.String())
	}
	if !strings.Contains(out.String(), "legacy field entrypoints") {
		t.Fatalf("legacy handoff output = %s", out.String())
	}
}

func TestReviewPrepareRejectsMutationOfFrozenValidationLedgerPrefix(t *testing.T) {
	projectRoot, featureDir, featureRel := newReviewAcceptWorkflowFeature(t, "109-review-frozen-ledger")
	writeReviewAcceptWorkflowStateFixture(t, featureDir, "109-review-frozen-ledger", 2, "implement", "active", nil)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, "task-index.json"), map[string]any{
		"version": 2,
		"status":  "ready",
		"validation_policy": map[string]any{
			"mode": "feature_epochs", "max_epochs": 3, "budget_scope": "implement-review",
			"budget_ref": "implementation-review/validation-runs.json", "heavy_gate_owner": "leader",
		},
	})
	started, err := reserveImplementValidationEpoch(projectRoot, featureDir, "implement", "convergence", "source-a", []string{"go test ./..."}, []string{"T001"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := completeImplementValidationEpoch(projectRoot, featureDir, implementValidationFinishRequest{
		RunID: started["run_id"].(string), Status: "passed",
		EvidenceRefs: []string{"implementation-review/validation-evidence/V1.txt"}, Summary: "convergence passed",
	}); err != nil {
		t.Fatal(err)
	}
	status, err := implementValidationBudgetStatus(projectRoot, featureDir)
	if err != nil {
		t.Fatal(err)
	}
	handoff := reviewAcceptHandoffFixture(projectRoot, featureDir, 4)
	handoff["validation_budget"] = map[string]any{
		"mode": "feature_epochs", "ledger_ref": "implementation-review/validation-runs.json",
		"max_epochs": 3, "used_epochs": status["used_epochs"], "remaining_epochs": status["remaining_epochs"],
		"consumed_runs_sha256": status["runs_sha256"],
	}
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), handoff)

	ledgerPath := filepath.Join(featureDir, "implementation-review", "validation-runs.json")
	ledger := readReviewAcceptJSON(t, ledgerPath)
	gate := ledger["runs"].([]any)[0].(map[string]any)
	attempt := gate["attempts"].([]any)[0].(map[string]any)
	attempt["summary"] = "mutated after freeze"
	gate["summary"] = "mutated after freeze"
	mustWriteReviewAcceptJSON(t, ledgerPath, ledger)
	writeReviewAcceptWorkflowStateFixture(t, featureDir, "109-review-frozen-ledger", 4, "review", "active", nil)

	var out bytes.Buffer
	args := []string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}
	if code := runReview(args, &out); code != 10 {
		t.Fatalf("mutated frozen ledger exit = %d output = %s", code, out.String())
	}
	if !strings.Contains(out.String(), "consumed_runs_sha256") {
		t.Fatalf("mutated frozen ledger output = %s", out.String())
	}
}

func TestReviewPrepareRestartStalePreservesMalformedState(t *testing.T) {
	projectRoot, featureDir, featureRel := newReviewAcceptWorkflowFeature(t, "107-review-restart-malformed")
	writeReviewAcceptWorkflowStateFixture(t, featureDir, "107-review-restart-malformed", 4, "review", "active", nil)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), reviewAcceptHandoffFixture(projectRoot, featureDir, 4))
	statePath := filepath.Join(featureDir, reviewStateFilename)
	malformed := []byte("{not-json\n")
	if err := os.WriteFile(statePath, malformed, 0o644); err != nil {
		t.Fatal(err)
	}
	var out bytes.Buffer
	args := []string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}
	if code := runReview(args, &out); code != 10 {
		t.Fatalf("malformed prepare without restart exit = %d output = %s", code, out.String())
	}
	if current, _ := os.ReadFile(statePath); !bytes.Equal(current, malformed) {
		t.Fatal("blocked malformed prepare changed review-state.json")
	}

	out.Reset()
	if code := runReview(append(args, "--restart-stale"), &out); code != 0 {
		t.Fatalf("malformed restart exit = %d output = %s", code, out.String())
	}
	digest := fmt.Sprintf("%x", sha256.Sum256(malformed))
	archived, err := os.ReadFile(filepath.Join(featureDir, "review-history", "review-state-"+digest+".json"))
	if err != nil || !bytes.Equal(archived, malformed) {
		t.Fatalf("malformed archive mismatch: err=%v", err)
	}
	state := readReviewAcceptJSON(t, statePath)
	rounds := state["rounds"].([]any)
	if len(rounds) != 1 || strings.TrimSpace(fmt.Sprint(rounds[0].(map[string]any)["restart_error"])) == "" {
		t.Fatalf("malformed restart rounds = %#v", rounds)
	}
}

func TestReviewPrepareValidateAndCloseout(t *testing.T) {
	projectRoot, featureDir, featureRel := newReviewAcceptWorkflowFeature(t, "101-review")
	writeReviewAcceptWorkflowStateFixture(t, featureDir, "101-review", 4, "review", "active", nil)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), reviewAcceptHandoffFixture(projectRoot, featureDir, 4))
	writeTextFile(t, filepath.Join(featureDir, humanAcceptanceSummaryFilename), "stale summary\n")

	var out bytes.Buffer
	if code := runReview([]string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}, &out); code != 0 {
		t.Fatalf("prepare exit = %d output = %s", code, out.String())
	}
	prepared := readReviewAcceptEnvelope(t, out.Bytes())
	if prepared.Status != "ok" {
		t.Fatalf("prepare = %#v", prepared)
	}
	state := readReviewAcceptJSON(t, filepath.Join(featureDir, reviewStateFilename))
	if state["status"] != "gathering" || int(state["version"].(float64)) != reviewStateVersion {
		t.Fatalf("prepared state = %#v", state)
	}
	if targets := state["reviewed_runtime_targets"].([]any); len(targets) != 0 {
		t.Fatalf("prepared Review inherited unreviewed runtime targets: %#v", targets)
	}
	if summarySHA := state["final"].(map[string]any)["implementation_summary_sha256"]; summarySHA != "" {
		t.Fatalf("prepared Review inherited stale implementation summary digest: %#v", summarySHA)
	}

	out.Reset()
	if code := runReview([]string{"validate", "--project-root", projectRoot, "--feature-dir", featureRel, "--format", "json"}, &out); code != 0 {
		t.Fatalf("validate exit = %d output = %s", code, out.String())
	}
	validated := readReviewAcceptEnvelope(t, out.Bytes())
	if validated.Data["valid"] != true || validated.Data["fresh"] != true {
		t.Fatalf("validate draft = %#v", validated)
	}

	bindReadyReviewTarget(t, projectRoot, featureDir, featureRel, "RS-1")
	state = readReviewAcceptJSON(t, filepath.Join(featureDir, reviewStateFilename))
	state["status"] = "approved"
	final := state["final"].(map[string]any)
	final["verdict"] = "pass"
	final["coverage_verdict"] = "pass"
	final["repair_verdict"] = "pass"
	final["integration_verdict"] = "pass"
	final["all_packets_joined"] = true
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, reviewStateFilename), state)

	out.Reset()
	if code := runReview([]string{"closeout", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}, &out); code != 0 {
		t.Fatalf("closeout exit = %d output = %s", code, out.String())
	}
	closed := readReviewAcceptEnvelope(t, out.Bytes())
	if closed.Status != "ok" || !equalStringSlices(closed.NextArgv[1:], []string{"workflow", "complete-stage", "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}) {
		t.Fatalf("closeout = %#v", closed)
	}
}

func TestReviewPrepareUpgradesPreExceptionV2StateInPlace(t *testing.T) {
	projectRoot, featureDir, featureRel := newReviewAcceptWorkflowFeature(t, "104-review-upgrade")
	writeReviewAcceptWorkflowStateFixture(t, featureDir, "104-review-upgrade", 4, "review", "active", nil)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), reviewAcceptHandoffFixture(projectRoot, featureDir, 4))

	var out bytes.Buffer
	args := []string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}
	if code := runReview(args, &out); code != 0 {
		t.Fatalf("initial prepare exit = %d output = %s", code, out.String())
	}
	statePath := filepath.Join(featureDir, reviewStateFilename)
	legacy := readReviewAcceptJSON(t, statePath)
	delete(legacy, "review_exceptions")
	delete(legacy["final"].(map[string]any), "review_exceptions_sha256")
	delete(legacy["source"].(map[string]any), "review_cycle_id")
	mustWriteReviewAcceptJSON(t, statePath, legacy)

	out.Reset()
	if code := runReview(args, &out); code != 0 {
		t.Fatalf("resume prepare exit = %d output = %s", code, out.String())
	}
	upgraded := readReviewAcceptJSON(t, statePath)
	if !reflect.DeepEqual(upgraded["review_exceptions"], []any{}) {
		t.Fatalf("review_exceptions = %#v", upgraded["review_exceptions"])
	}
	final := upgraded["final"].(map[string]any)
	wantDigest := reviewExceptionsSHA256([]any{})
	if final["review_exceptions_sha256"] != wantDigest {
		t.Fatalf("review_exceptions_sha256 = %v, want %s", final["review_exceptions_sha256"], wantDigest)
	}
	upgradedSource := upgraded["source"].(map[string]any)
	wantCycleID := reviewCycleID(4, fmt.Sprint(upgradedSource["implementation_handoff_sha256"]), 1, "", "", "")
	if upgradedSource["review_cycle_id"] != wantCycleID {
		t.Fatalf("review_cycle_id = %v, want %s", upgradedSource["review_cycle_id"], wantCycleID)
	}
	legacySource := cloneAny(legacy["source"]).(map[string]any)
	legacySource["review_cycle_id"] = wantCycleID
	if !reflect.DeepEqual(upgraded["source"], legacySource) || !reflect.DeepEqual(upgraded["scenarios"], legacy["scenarios"]) {
		t.Fatal("compatibility upgrade changed existing Review evidence")
	}
}

func TestReviewFingerprintTracksProductButIgnoresReviewEvidence(t *testing.T) {
	projectRoot, featureDir, _ := newReviewAcceptWorkflowFeature(t, "105-review-fingerprint")
	mustMkdir(t, filepath.Join(projectRoot, "src"))
	writeTextFile(t, filepath.Join(projectRoot, "src", "product.txt"), "before\n")
	before := sourceTreeFingerprint(projectRoot, featureDir)

	mustMkdir(t, filepath.Join(featureDir, "review-evidence"))
	writeTextFile(t, filepath.Join(featureDir, "review-evidence", "diagnostic.json"), "{}\n")
	if afterEvidence := sourceTreeFingerprint(projectRoot, featureDir); afterEvidence != before {
		t.Fatalf("Review-owned evidence changed implementation fingerprint: %s != %s", afterEvidence, before)
	}

	writeTextFile(t, filepath.Join(projectRoot, "src", "product.txt"), "after repair\n")
	if afterProduct := sourceTreeFingerprint(projectRoot, featureDir); afterProduct == before {
		t.Fatal("product repair did not change implementation fingerprint")
	}
}

func TestReviewTargetBindOwnsIdentityAndRejectsDerivedOrExcludedInputs(t *testing.T) {
	projectRoot, featureDir, featureRel := newReviewAcceptWorkflowFeature(t, "110-review-target-bind")
	writeReviewAcceptWorkflowStateFixture(t, featureDir, "110-review-target-bind", 4, "review", "active", nil)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), reviewAcceptHandoffFixture(projectRoot, featureDir, 4))
	var out bytes.Buffer
	if code := runReview([]string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}, &out); code != 0 {
		t.Fatalf("prepare exit = %d output = %s", code, out.String())
	}

	bound := bindReadyReviewTarget(t, projectRoot, featureDir, featureRel, "RS-1")
	target := bound.Data["target"].(map[string]any)
	identityRef := target["identity_evidence_ref"].(string)
	identity := readReviewAcceptJSON(t, filepath.Join(featureDir, filepath.FromSlash(identityRef)))
	if !reflect.DeepEqual(identity, cloneAny(reviewRuntimeIdentityClaim(target))) {
		t.Fatalf("identity claim = %#v, want %#v", identity, cloneAny(reviewRuntimeIdentityClaim(target)))
	}
	state := readReviewAcceptJSON(t, filepath.Join(featureDir, reviewStateFilename))
	final := state["final"].(map[string]any)
	if final["reviewed_snapshot_sha256"] != sourceTreeFingerprint(projectRoot, featureDir) || final["runtime_targets_sha256"] != reviewRuntimeTargetsSHA256(state["reviewed_runtime_targets"].([]any)) {
		t.Fatalf("runtime-derived final target bindings = %#v", final)
	}

	before, err := os.ReadFile(filepath.Join(featureDir, reviewStateFilename))
	if err != nil {
		t.Fatal(err)
	}
	invalid := map[string]any{
		"id": "RT-RS-1", "mode": "source", "status": "ready", "entrypoint_id": "EP-1",
		"environment_ref": "local", "instance_ref": "http://localhost:3000", "configuration_ref": "test",
		"test_data_refs": []any{}, "ready_evidence_refs": []any{"review-evidence/runtime-ready-RS-1.json"},
		"review_scenario_ids": []any{"RS-1"},
	}
	invalidRaw, _ := json.Marshal(invalid)
	out.Reset()
	if code := runReview([]string{"target-bind", "--project-root", projectRoot, "--feature-dir", featureRel, "--input-json", string(invalidRaw), "--format", "json"}, &out); code != 10 || !strings.Contains(out.String(), "unsupported runtime target field") {
		t.Fatalf("derived input should block: exit=%d output=%s", code, out.String())
	}
	after, _ := os.ReadFile(filepath.Join(featureDir, reviewStateFilename))
	if !bytes.Equal(before, after) {
		t.Fatal("blocked derived target input changed review-state.json")
	}

	readyRef := "review-evidence/runtime-ready-RS-1.json"
	readySHA := optionalFileSHA256(filepath.Join(featureDir, filepath.FromSlash(readyRef)))
	excludedArtifact := map[string]any{
		"id": "RT-BUILD", "mode": "build", "entrypoint_id": "EP-1",
		"environment_ref": "local", "instance_ref": "http://localhost:3000", "configuration_ref": "test",
		"artifact_ref": readyRef, "artifact_sha256": readySHA, "test_data_refs": []any{},
		"ready_evidence_refs": []any{readyRef}, "review_scenario_ids": []any{"RS-1"},
	}
	excludedRaw, _ := json.Marshal(excludedArtifact)
	out.Reset()
	if code := runReview([]string{"target-bind", "--project-root", projectRoot, "--feature-dir", featureRel, "--input-json", string(excludedRaw), "--format", "json"}, &out); code != 10 || !strings.Contains(out.String(), "excluded from the implementation snapshot") {
		t.Fatalf("Review evidence artifact should block: exit=%d output=%s", code, out.String())
	}

	writeTextFile(t, filepath.Join(featureDir, filepath.FromSlash(identityRef)), "{}\n")
	out.Reset()
	if code := runReview([]string{"validate", "--project-root", projectRoot, "--feature-dir", featureRel, "--format", "json"}, &out); code != 0 {
		t.Fatalf("validate exit = %d output = %s", code, out.String())
	}
	validation := readReviewAcceptEnvelope(t, out.Bytes())
	if validation.Data["valid"] != false || !strings.Contains(fmt.Sprint(validation.Data["errors"]), "identity_evidence") {
		t.Fatalf("tampered identity validation = %#v", validation)
	}
}

func TestReviewHardwareExceptionRequiresExactHumanConfirmation(t *testing.T) {
	projectRoot, featureDir, featureRel := newReviewAcceptWorkflowFeature(t, "103-review-hardware")
	writeReviewAcceptWorkflowStateFixture(t, featureDir, "103-review-hardware", 4, "review", "active", nil)
	handoff := reviewAcceptHandoffFixture(projectRoot, featureDir, 4)
	handoff["system_review_scenarios"] = []any{
		map[string]any{"id": "RS-HW-1", "required": true, "result": "pending", "evidence": []any{}, "entrypoint_id": "EP-1"},
		map[string]any{"id": "RS-1", "required": true, "result": "pending", "evidence": []any{}, "entrypoint_id": "EP-1", "obligation_ids": []any{"RO-1"}},
	}
	handoff["review_obligations"] = []any{
		map[string]any{"id": "RO-HW-1", "required": true, "scenario_ids": []any{"RS-HW-1"}, "status": "pending", "review_assignment_ids": []any{"RA-1"}},
		map[string]any{"id": "RO-1", "required": true, "scenario_ids": []any{"RS-1"}, "status": "pending", "review_assignment_ids": []any{"RA-2"}},
	}
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), handoff)

	var out bytes.Buffer
	if code := runReview([]string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}, &out); code != 0 {
		t.Fatalf("prepare exit = %d output = %s", code, out.String())
	}
	mustMkdir(t, filepath.Join(featureDir, "review-evidence"))
	evidenceRef := "review-evidence/hardware-unavailable.json"
	writeTextFile(t, filepath.Join(featureDir, filepath.FromSlash(evidenceRef)), "{\"observed_devices\":[]}\n")
	proposalInput := map[string]any{
		"kind": "hardware_unavailable", "scenario_ids": []any{"RS-HW-1"},
		"obligation_ids": []any{"RO-HW-1"}, "required_resource": "USB security key model X",
		"unavailable_evidence_refs": []any{evidenceRef},
		"attempted_alternatives":    []any{"Enumerated attached USB devices."},
		"claims_withheld":           []any{"physical security key behavior verified"},
		"residual_risk":             "The physical interaction remains unobserved.", "risk_severity": "medium",
	}
	proposalRaw, err := json.Marshal(proposalInput)
	if err != nil {
		t.Fatal(err)
	}

	out.Reset()
	if code := runReview([]string{"exception-propose", "--project-root", projectRoot, "--feature-dir", featureRel, "--input-json", string(proposalRaw), "--format", "json"}, &out); code != 0 {
		t.Fatalf("propose exit = %d output = %s", code, out.String())
	}
	proposal := readReviewAcceptEnvelope(t, out.Bytes()).Data
	if proposal["status"] != "proposed" {
		t.Fatalf("proposal = %#v", proposal)
	}

	out.Reset()
	if code := runReview([]string{"exception-confirm", "--project-root", projectRoot, "--feature-dir", featureRel, "--exception-id", proposal["exception_id"].(string), "--proposal-sha256", strings.Repeat("0", 64), "--confirmation-source", "human-reply", "--statement", "Proceed without this unavailable hardware.", "--format", "json"}, &out); code != 10 {
		t.Fatalf("wrong digest should block: exit=%d output=%s", code, out.String())
	}

	out.Reset()
	if code := runReview([]string{"exception-confirm", "--project-root", projectRoot, "--feature-dir", featureRel, "--exception-id", proposal["exception_id"].(string), "--proposal-sha256", proposal["proposal_sha256"].(string), "--confirmation-source", "human-reply", "--statement", "Proceed without this unavailable hardware.", "--format", "json"}, &out); code != 0 {
		t.Fatalf("confirm exit = %d output = %s", code, out.String())
	}

	state := readReviewAcceptJSON(t, filepath.Join(featureDir, reviewStateFilename))
	if state["scenarios"].([]any)[0].(map[string]any)["result"] != "waived" || state["obligations"].([]any)[0].(map[string]any)["status"] != "waived" {
		t.Fatalf("confirmed exception did not mark explicit waivers: %#v", state)
	}
	bindReadyReviewTarget(t, projectRoot, featureDir, featureRel, "RS-1")
	state = readReviewAcceptJSON(t, filepath.Join(featureDir, reviewStateFilename))
	state["status"] = "approved"
	final := state["final"].(map[string]any)
	final["verdict"] = "pass_with_waivers"
	final["coverage_verdict"] = "pass_with_waivers"
	final["repair_verdict"] = "pass"
	final["integration_verdict"] = "pass"
	final["all_packets_joined"] = true
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, reviewStateFilename), state)

	out.Reset()
	if code := runReview([]string{"closeout", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}, &out); code != 0 {
		t.Fatalf("waived closeout exit = %d output = %s", code, out.String())
	}
}

func TestAcceptPrepareValidateCloseoutAndRouteRepair(t *testing.T) {
	projectRoot, featureDir, featureRel := newReviewAcceptWorkflowFeature(t, "102-accept")
	writeReviewAcceptWorkflowStateFixture(t, featureDir, "102-accept", 9, "accept", "active", nil)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), reviewAcceptHandoffFixture(projectRoot, featureDir, 8))
	reviewState := approvedReviewStateFixture(t, projectRoot, featureDir, featureRel, 8)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, reviewStateFilename), reviewState)

	var out bytes.Buffer
	if code := runAccept([]string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--format", "json"}, &out); code != 0 {
		t.Fatalf("prepare exit = %d output = %s", code, out.String())
	}
	prepared := readReviewAcceptEnvelope(t, out.Bytes())
	if prepared.Status != "ok" {
		t.Fatalf("accept prepare = %#v", prepared)
	}
	acceptance := readReviewAcceptJSON(t, filepath.Join(featureDir, humanAcceptanceFilename))
	if acceptance["status"] != "draft" || int(acceptance["version"].(float64)) != humanAcceptanceStateVersion {
		t.Fatalf("acceptance state = %#v", acceptance)
	}

	out.Reset()
	if code := runAccept([]string{"validate", "--project-root", projectRoot, "--feature-dir", featureRel, "--format", "json"}, &out); code != 0 {
		t.Fatalf("validate exit = %d output = %s", code, out.String())
	}
	draftValidation := readReviewAcceptEnvelope(t, out.Bytes())
	if draftValidation.Data["valid"] != false || draftValidation.Data["accepted"] != false {
		t.Fatalf("draft validation = %#v", draftValidation)
	}

	accepted := cloneAny(acceptance).(map[string]any)
	accepted["status"] = "accepted"
	accepted["overall"] = map[string]any{
		"verdict":        "pass",
		"human_decision": "accept",
		"next_command":   "workflow closeout",
	}
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, humanAcceptanceFilename), accepted)
	out.Reset()
	if code := runAccept([]string{"closeout", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "9", "--format", "json"}, &out); code != 0 {
		t.Fatalf("closeout exit = %d output = %s", code, out.String())
	}
	closed := readReviewAcceptEnvelope(t, out.Bytes())
	if closed.Status != "ok" || !equalStringSlices(closed.NextArgv[1:], []string{"workflow", "closeout", "--feature-dir", featureRel, "--expected-revision", "9", "--format", "json"}) {
		t.Fatalf("accept closeout = %#v", closed)
	}

	rejected := cloneAny(acceptance).(map[string]any)
	rejected["status"] = "rejected"
	rejected["findings"] = []any{map[string]any{
		"id": "HA-1", "route": "sp-review", "status": "open", "scenario_id": "HA-S-1", "step_id": "step-1",
		"expected": "The accepted action succeeds.", "observed": "The accepted action failed.", "evidence": []any{"sanitized failed acceptance scenario"},
	}}
	rejected["overall"] = map[string]any{"verdict": "fail", "human_decision": "reject", "next_command": "sp-review"}
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, humanAcceptanceFilename), rejected)
	previousReviewSHA := optionalFileSHA256(filepath.Join(featureDir, reviewStateFilename))
	out.Reset()
	if code := runAccept([]string{"route-repair", "--project-root", projectRoot, "--feature-dir", featureRel, "--finding-id", "HA-1", "--route", "sp-review", "--expected-revision", "9", "--evidence", "sanitized failed acceptance scenario", "--format", "json"}, &out); code != 0 {
		t.Fatalf("route-repair exit = %d output = %s", code, out.String())
	}
	routed := readReviewAcceptEnvelope(t, out.Bytes())
	if routed.Status != "ok" || routed.Data["stage"] != "review" || routed.Data["revision"] != float64(10) {
		t.Fatalf("route-repair = %#v", routed)
	}
	if _, err := os.Stat(filepath.Join(featureDir, humanAcceptanceRepairJournalName)); err != nil {
		t.Fatalf("missing repair journal: %v", err)
	}
	if _, err := os.Stat(filepath.Join(featureDir, humanAcceptanceRepairBackupName)); err != nil {
		t.Fatalf("missing repair backup: %v", err)
	}
	invalidated := readReviewAcceptJSON(t, filepath.Join(featureDir, humanAcceptanceFilename))
	if invalidated["status"] != "draft" {
		t.Fatalf("invalidated acceptance = %#v", invalidated)
	}
	handoffPath := filepath.Join(featureDir, implementationHandoffFilename)
	originalHandoff, err := os.ReadFile(handoffPath)
	if err != nil {
		t.Fatal(err)
	}
	changedHandoff := readReviewAcceptJSON(t, handoffPath)
	changedHandoff["post_acceptance_change"] = true
	mustWriteReviewAcceptJSON(t, handoffPath, changedHandoff)
	out.Reset()
	if code := runReview([]string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "10", "--format", "json"}, &out); code != 10 {
		t.Fatalf("stale acceptance repair handoff exit = %d output = %s", code, out.String())
	}
	if err := os.WriteFile(handoffPath, originalHandoff, 0o644); err != nil {
		t.Fatal(err)
	}

	out.Reset()
	if code := runReview([]string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "10", "--format", "json"}, &out); code != 0 {
		t.Fatalf("acceptance repair review prepare exit = %d output = %s", code, out.String())
	}
	repairReview := readReviewAcceptJSON(t, filepath.Join(featureDir, reviewStateFilename))
	repairSource := repairReview["source"].(map[string]any)
	if int(repairSource["review_cycle"].(float64)) != 2 || repairSource["previous_review_state_sha256"] != previousReviewSHA || repairSource["acceptance_finding_id"] != "HA-1" {
		t.Fatalf("acceptance repair review source = %#v", repairSource)
	}
	if findings := repairReview["findings"].([]any); len(findings) != 1 || findings[0].(map[string]any)["origin_acceptance_finding_id"] != "HA-1" {
		t.Fatalf("acceptance repair findings = %#v", findings)
	}
}

func bindReadyReviewTarget(t *testing.T, projectRoot, featureDir, featureRel, scenarioID string) Envelope {
	t.Helper()
	statePath := filepath.Join(featureDir, reviewStateFilename)
	state := readReviewAcceptJSON(t, statePath)
	scenario := findObjectByID(state["scenarios"], scenarioID)
	if scenario == nil {
		t.Fatalf("missing Review scenario %s", scenarioID)
	}
	entrypointID := stringField(scenario, "entrypoint_id")
	if entrypointID == "" {
		t.Fatalf("Review scenario %s has no entrypoint", scenarioID)
	}
	mustMkdir(t, filepath.Join(featureDir, "review-evidence"))
	readyRef := filepath.ToSlash(filepath.Join("review-evidence", "runtime-ready-"+scenarioID+".json"))
	writeTextFile(t, filepath.Join(featureDir, filepath.FromSlash(readyRef)), "{\"ready\":true}\n")
	scenario["result"] = "pass"
	scenario["evidence"] = []any{map[string]any{"kind": "runtime_diagnostics", "path": readyRef}}
	mustWriteReviewAcceptJSON(t, statePath, state)
	input := map[string]any{
		"id": "RT-" + scenarioID, "mode": "source", "entrypoint_id": entrypointID,
		"environment_ref": "local", "instance_ref": "http://localhost:3000", "configuration_ref": "test",
		"test_data_refs": []any{}, "ready_evidence_refs": []any{readyRef}, "review_scenario_ids": []any{scenarioID},
	}
	raw, err := json.Marshal(input)
	if err != nil {
		t.Fatal(err)
	}
	var out bytes.Buffer
	if code := runReview([]string{"target-bind", "--project-root", projectRoot, "--feature-dir", featureRel, "--input-json", string(raw), "--format", "json"}, &out); code != 0 {
		t.Fatalf("target-bind exit = %d output = %s", code, out.String())
	}
	return readReviewAcceptEnvelope(t, out.Bytes())
}

func approvedReviewStateFixture(t *testing.T, projectRoot, featureDir, featureRel string, revision int) map[string]any {
	t.Helper()
	handoffPath := filepath.Join(featureDir, implementationHandoffFilename)
	handoff := readReviewAcceptJSON(t, handoffPath)
	fingerprint := sourceTreeFingerprint(projectRoot, featureDir)
	feature := reviewAcceptFeature{id: filepath.Base(featureDir), abs: featureDir, rel: featureRel}
	state := newReviewState(feature, handoff, revision, optionalFileSHA256(handoffPath), fingerprint, 1, "", "", nil, nil)
	mustMkdir(t, filepath.Join(featureDir, "review-evidence"))
	readyRef := "review-evidence/runtime-ready-RS-1.json"
	writeTextFile(t, filepath.Join(featureDir, filepath.FromSlash(readyRef)), "{\"ready\":true}\n")
	scenario := findObjectByID(state["scenarios"], "RS-1")
	scenario["result"] = "pass"
	scenario["evidence"] = []any{map[string]any{"kind": "runtime_diagnostics", "path": readyRef}}
	target, err := normalizeReviewRuntimeTarget(feature, state, map[string]any{
		"id": "RT-RS-1", "mode": "source", "entrypoint_id": "EP-1",
		"environment_ref": "local", "instance_ref": "http://localhost:3000", "configuration_ref": "test",
		"test_data_refs": []any{}, "ready_evidence_refs": []any{readyRef}, "review_scenario_ids": []any{"RS-1"},
	}, fingerprint)
	if err != nil {
		t.Fatal(err)
	}
	identityRef := reviewRuntimeTargetIdentityRef("RT-RS-1", 1)
	identity := reviewRuntimeIdentityClaim(target)
	identityRaw, err := marshalReviewAcceptJSON(identity)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(featureDir, filepath.FromSlash(identityRef)), identityRaw, 0o644); err != nil {
		t.Fatal(err)
	}
	target["identity_evidence_ref"] = identityRef
	target["identity_evidence_sha256"] = fileContentSHA256(identityRaw)
	state["reviewed_runtime_targets"] = []any{target}
	state["status"] = "approved"
	final := state["final"].(map[string]any)
	final["verdict"] = "pass"
	final["coverage_verdict"] = "pass"
	final["repair_verdict"] = "pass"
	final["integration_verdict"] = "pass"
	final["all_packets_joined"] = true
	final["reviewed_snapshot_sha256"] = fingerprint
	final["runtime_targets_sha256"] = reviewRuntimeTargetsSHA256([]any{target})
	return state
}

func reviewAcceptHandoffFixture(projectRoot, featureDir string, revision int) map[string]any {
	humanAcceptanceObligations := []any{map[string]any{"id": "HA-O-1", "required": true, "scenario_ids": []any{"HA-S-1"}, "acceptance_ref": "FR-001"}}
	humanAcceptanceScenarios := []any{map[string]any{"id": "HA-S-1", "required": true, "review_scenario_ids": []any{"RS-1"}, "entrypoint_id": "EP-1", "actor": "user"}}
	userConfirmedDeferrals := []any{}
	return map[string]any{
		"version":                          1,
		"status":                           "ready_for_review",
		"source_revision":                  revision,
		"source_stage":                     "implement",
		"feature_dir":                      filepath.ToSlash(featureDir),
		"implementation_fingerprint":       sourceTreeFingerprint(projectRoot, featureDir),
		"fingerprint_algorithm":            implementationFingerprintAlgorith,
		"official_entrypoints":             []any{map[string]any{"id": "EP-1", "command": "npm run dev", "ready_signal": "http://localhost:3000/health"}},
		"runtime_targets":                  []any{"http://localhost:3000"},
		"system_review_scenarios":          []any{map[string]any{"id": "RS-1", "required": true, "obligation_ids": []any{"RO-1"}, "entrypoint_id": "EP-1"}},
		"review_obligations":               []any{map[string]any{"id": "RO-1", "required": true, "scenario_ids": []any{"RS-1"}}},
		"human_acceptance_scenarios":       humanAcceptanceScenarios,
		"human_acceptance_obligations":     humanAcceptanceObligations,
		"human_acceptance_contract_sha256": canonicalJSONSHA256(map[string]any{"human_acceptance_obligations": humanAcceptanceObligations, "human_acceptance_scenarios": humanAcceptanceScenarios}),
		"human_acceptance_contract_origin": "task-index-v2",
		"acceptance_refs":                  []any{"FR-001"},
		"task_ids":                         []any{"T001"},
		"user_confirmed_deferrals":         userConfirmedDeferrals,
		"user_confirmed_deferral_refs":     []any{},
		"user_confirmed_deferrals_sha256":  canonicalJSONSHA256(map[string]any{"user_confirmed_deferrals": userConfirmedDeferrals}),
		"validation_policy": map[string]any{
			"mode": "feature_epochs", "max_epochs": 3, "budget_scope": "implement-review",
			"budget_ref": "implementation-review/validation-runs.json", "heavy_gate_owner": "leader",
		},
		"validation_budget": map[string]any{
			"mode": "feature_epochs", "ledger_ref": "implementation-review/validation-runs.json",
			"max_epochs": 3, "used_epochs": 0, "remaining_epochs": 3,
			"consumed_runs_sha256": canonicalJSONSHA256([]any{}),
		},
	}
}

func mustWriteReviewAcceptJSON(t *testing.T, path string, payload any) {
	t.Helper()
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(raw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func readReviewAcceptJSON(t *testing.T, path string) map[string]any {
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

func readReviewAcceptEnvelope(t *testing.T, raw []byte) Envelope {
	t.Helper()
	var env Envelope
	if err := json.Unmarshal(raw, &env); err != nil {
		t.Fatalf("parse envelope %q: %v", string(raw), err)
	}
	return env
}

func equalStringSlices(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for i := range left {
		if left[i] != right[i] {
			return false
		}
	}
	return true
}

func newReviewAcceptWorkflowFeature(t *testing.T, featureID string) (string, string, string) {
	t.Helper()
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join(".specify", "features", featureID))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	return projectRoot, featureDir, featureRel
}

func writeReviewAcceptWorkflowStateFixture(t *testing.T, featureDir, featureID string, revision int, stage, status string, acceptanceSHA256 *string) {
	t.Helper()
	payload := map[string]any{
		"schema_version":           1,
		"feature_id":               featureID,
		"revision":                 revision,
		"stage":                    stage,
		"status":                   status,
		"summary":                  stage + " fixture",
		"blocker":                  nil,
		"last_resolution_evidence": []string{},
		"last_reopen":              nil,
		"last_blocker_resolution":  nil,
		"acceptance_sha256":        acceptanceSHA256,
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(featureDir, "workflow.json"), append(raw, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

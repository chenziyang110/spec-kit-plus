package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestReviewPrepareValidateAndCloseout(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "101-review")
	writeWorkflowStateFixture(t, featureDir, "101-review", 4, "review", "active", nil)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), reviewAcceptHandoffFixture(4))

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

	out.Reset()
	if code := runReview([]string{"validate", "--project-root", projectRoot, "--feature-dir", featureRel, "--format", "json"}, &out); code != 0 {
		t.Fatalf("validate exit = %d output = %s", code, out.String())
	}
	validated := readReviewAcceptEnvelope(t, out.Bytes())
	if validated.Data["valid"] != true || validated.Data["fresh"] != true {
		t.Fatalf("validate draft = %#v", validated)
	}

	state["status"] = "approved"
	state["final"] = map[string]any{
		"verdict":                       "pass",
		"coverage_verdict":              "pass",
		"repair_verdict":                "pass",
		"integration_verdict":           "pass",
		"all_packets_joined":            true,
		"reviewed_snapshot_sha256":      "",
		"implementation_summary_sha256": "",
		"runtime_targets_sha256":        "",
		"review_exceptions_sha256":      canonicalJSONSHA256(map[string]any{"review_exceptions": []any{}}),
	}
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
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "104-review-upgrade")
	writeWorkflowStateFixture(t, featureDir, "104-review-upgrade", 4, "review", "active", nil)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), reviewAcceptHandoffFixture(4))

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
	projectRoot, featureDir, _ := newWorkflowFeature(t, "105-review-fingerprint")
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

func TestReviewHardwareExceptionRequiresExactHumanConfirmation(t *testing.T) {
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "103-review-hardware")
	writeWorkflowStateFixture(t, featureDir, "103-review-hardware", 4, "review", "active", nil)
	handoff := reviewAcceptHandoffFixture(4)
	handoff["review_scenarios"] = []any{map[string]any{
		"id": "RS-HW-1", "required": true, "result": "pending", "evidence": []any{},
	}}
	handoff["review_obligations"] = []any{map[string]any{
		"id": "RO-HW-1", "required": true, "scenario_ids": []any{"RS-HW-1"},
		"status": "pending", "review_assignment_ids": []any{"RA-1"},
	}}
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), handoff)

	var out bytes.Buffer
	if code := runReview([]string{"prepare", "--project-root", projectRoot, "--feature-dir", featureRel, "--expected-revision", "4", "--format", "json"}, &out); code != 0 {
		t.Fatalf("prepare exit = %d output = %s", code, out.String())
	}
	mustMkdir(t, filepath.Join(featureDir, "review-evidence"))
	evidenceRef := "review-evidence/hardware-unavailable.json"
	writeTextFile(t, filepath.Join(featureDir, filepath.FromSlash(evidenceRef)), "{\"observed_devices\":[]}\n")
	proposalRef := "review-evidence/hardware-exception-proposal.json"
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, filepath.FromSlash(proposalRef)), map[string]any{
		"kind": "hardware_unavailable", "scenario_ids": []any{"RS-HW-1"},
		"obligation_ids": []any{"RO-HW-1"}, "required_resource": "USB security key model X",
		"unavailable_evidence_refs": []any{evidenceRef},
		"attempted_alternatives":    []any{"Enumerated attached USB devices."},
		"claims_withheld":           []any{"physical security key behavior verified"},
		"residual_risk":             "The physical interaction remains unobserved.", "risk_severity": "medium",
	})

	out.Reset()
	if code := runReview([]string{"exception-propose", "--project-root", projectRoot, "--feature-dir", featureRel, "--input", filepath.ToSlash(filepath.Join(featureRel, proposalRef)), "--format", "json"}, &out); code != 0 {
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
	projectRoot, featureDir, featureRel := newWorkflowFeature(t, "102-accept")
	writeWorkflowStateFixture(t, featureDir, "102-accept", 9, "accept", "active", nil)
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, implementationHandoffFilename), reviewAcceptHandoffFixture(8))
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
	rejected["findings"] = []any{map[string]any{"id": "HA-1", "route": "sp-review", "status": "open"}}
	rejected["overall"] = map[string]any{"verdict": "fail", "human_decision": "reject", "next_command": "sp-review"}
	mustWriteReviewAcceptJSON(t, filepath.Join(featureDir, humanAcceptanceFilename), rejected)
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
}

func approvedReviewStateFixture(t *testing.T, projectRoot, featureDir, featureRel string, revision int) map[string]any {
	t.Helper()
	handoffPath := filepath.Join(featureDir, implementationHandoffFilename)
	return map[string]any{
		"version":    reviewStateVersion,
		"schema_ref": reviewSchemaRef,
		"status":     "approved",
		"source": map[string]any{
			"workflow_revision":             revision,
			"implementation_handoff_sha256": optionalFileSHA256(handoffPath),
			"implementation_fingerprint":    sourceTreeFingerprint(projectRoot, featureDir),
			"review_cycle":                  1,
		},
		"findings":                 []any{},
		"reviewed_runtime_targets": []any{"http://localhost:3000"},
		"final": map[string]any{
			"verdict":                       "pass",
			"coverage_verdict":              "pass",
			"repair_verdict":                "pass",
			"integration_verdict":           "pass",
			"all_packets_joined":            true,
			"reviewed_snapshot_sha256":      "",
			"implementation_summary_sha256": "",
			"runtime_targets_sha256":        "",
			"review_exceptions_sha256":      canonicalJSONSHA256(map[string]any{"review_exceptions": []any{}}),
		},
		"review_exceptions": []any{},
		"feature_dir":       featureRel,
	}
}

func reviewAcceptHandoffFixture(revision int) map[string]any {
	return map[string]any{
		"source_revision":              revision,
		"fingerprint_algorithm":        implementationFingerprintAlgorith,
		"entrypoints":                  []any{"web"},
		"runtime_targets":              []any{"http://localhost:3000"},
		"review_scenarios":             []any{map[string]any{"id": "RS-1", "required": true}},
		"review_obligations":           []any{map[string]any{"id": "RO-1", "required": true}},
		"human_acceptance_scenarios":   []any{map[string]any{"id": "HA-S-1", "required": true}},
		"human_acceptance_obligations": []any{map[string]any{"id": "HA-O-1", "required": true}},
		"human_acceptance_contract":    map[string]any{"sha256": "contract"},
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

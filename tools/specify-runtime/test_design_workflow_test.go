package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestTestDesignWorkflowFeatureLifecycleProducesTaskHandoff(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	for _, dir := range []string{"src", "tests"} {
		if err := os.MkdirAll(filepath.Join(projectRoot, dir), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(featureDir, "spec.md"), []byte("# Spec\n\nREQ-001 approval.\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)

	initInput := map[string]any{
		"query":          "Design exhaustive approval tests",
		"source_refs":    []any{featureRel + "/spec.md"},
		"included_paths": []any{"src", "tests"},
		"excluded_paths": []any{"vendor"},
		"risk_dimensions": []any{
			"functional", "boundary", "permission", "recovery", "security",
		},
	}
	initEnv, exit := runTestDesignWorkflowCommand(t, []string{
		"test-design", "init", "--scope", "feature", "--mode", "feature",
		"--feature-dir", featureRel, "--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, initInput), "--format", "json",
	})
	if exit != 0 || initEnv.Status != "ok" {
		t.Fatalf("init exit=%d env=%#v", exit, initEnv)
	}

	artifactRoot := filepath.Join(featureDir, "test-design")
	for _, name := range []string{
		"test-state.json",
		"test-universe.json",
		"test-catalog.json",
		"test-data-manifest.json",
		"coverage-matrix.json",
		"test-gaps.json",
		"lane-manifest.json",
	} {
		if _, err := os.Stat(filepath.Join(artifactRoot, name)); err != nil {
			t.Fatalf("missing initialized %s: %v", name, err)
		}
	}

	evidenceRef := registerTestDesignEvidence(t, projectRoot, `{"kind":"runtime-diagnostics","result":"pass"}`)
	writeValidTestDesignWorkflowBundle(t, artifactRoot, evidenceRef)
	requireTestDesignOK(t, []string{"test-design", "universe-build", "--feature-dir", featureRel, "--format", "json"})

	lanes := map[string]any{"lanes": []any{map[string]any{
		"lane_id":        "LANE-001",
		"kind":           "discovery",
		"title":          "Approval behavior and risk scan",
		"obligation_ids": []any{"TO-001"},
		"read_paths":     []any{"src", "tests", featureRel + "/spec.md"},
		"questions":      []any{"Find positive, negative, boundary, permission, and recovery cases."},
	}}}
	requireTestDesignOK(t, []string{
		"test-design", "lane-prepare", "--feature-dir", featureRel,
		"--input-json", mustTestDesignJSON(t, lanes), "--format", "json",
	})
	lease := requireTestDesignOK(t, []string{
		"test-design", "lane-lease", "--feature-dir", featureRel,
		"--worker-id", "worker-1", "--format", "json",
	})
	attemptID, _ := lease.Data["attempt_id"].(string)
	if attemptID == "" {
		t.Fatalf("lease missing attempt_id: %#v", lease.Data)
	}
	result := map[string]any{
		"lane_id":            "LANE-001",
		"attempt_id":         attemptID,
		"status":             "success",
		"inspected_paths":    []any{"src", "tests", featureRel + "/spec.md"},
		"evidence_refs":      []any{evidenceRef},
		"obligation_results": testDesignCoveredObligationResult(evidenceRef),
		"checks":             []any{},
		"candidate_cases":    []any{map[string]any{"test_case_id": "TC-001", "summary": "Approval succeeds once"}},
		"data_requirements":  []any{map[string]any{"test_data_id": "TD-001", "disposition": "generate"}},
		"contradictions":     []any{},
		"unknowns":           []any{},
		"gaps":               []any{},
		"summary":            "Approval lane complete.",
	}
	requireTestDesignOK(t, []string{
		"test-design", "lane-checkpoint", "--feature-dir", featureRel,
		"--lane-id", "LANE-001", "--attempt-id", attemptID,
		"--result-json", mustTestDesignJSON(t, result), "--format", "json",
	})
	requireTestDesignOK(t, []string{
		"test-design", "lane-accept", "--feature-dir", featureRel,
		"--lane-id", "LANE-001", "--attempt-id", attemptID, "--format", "json",
	})
	requireTestDesignOK(t, []string{"test-design", "synthesize", "--feature-dir", featureRel, "--leader-id", "leader-1", "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "audit-prepare", "--feature-dir", featureRel, "--format", "json"})
	auditLease := requireTestDesignOK(t, []string{
		"test-design", "lane-lease", "--feature-dir", featureRel,
		"--worker-id", "independent-auditor", "--format", "json",
	})
	auditLaneID, _ := auditLease.Data["lane_id"].(string)
	auditAttemptID, _ := auditLease.Data["attempt_id"].(string)
	auditResult := map[string]any{
		"lane_id":    auditLaneID,
		"attempt_id": auditAttemptID,
		"status":     "success",
		"inspected_paths": []any{
			filepath.ToSlash(filepath.Join(featureRel, "test-design", "test-universe.json")),
			filepath.ToSlash(filepath.Join(featureRel, "test-design", "test-catalog.json")),
			filepath.ToSlash(filepath.Join(featureRel, "test-design", "test-data-manifest.json")),
			filepath.ToSlash(filepath.Join(featureRel, "test-design", "coverage-matrix.json")),
			filepath.ToSlash(filepath.Join(featureRel, "test-design", "test-gaps.json")),
		},
		"evidence_refs":      []any{evidenceRef},
		"obligation_results": testDesignCoveredObligationResult(evidenceRef),
		"checks":             testDesignAuditChecks(evidenceRef),
		"candidate_cases":    []any{},
		"data_requirements":  []any{},
		"contradictions":     []any{},
		"unknowns":           []any{},
		"gaps":               []any{},
		"findings":           []any{},
		"summary":            "Independent audit found no unresolved omission.",
	}
	requireTestDesignOK(t, []string{
		"test-design", "lane-checkpoint", "--feature-dir", featureRel,
		"--lane-id", auditLaneID, "--attempt-id", auditAttemptID,
		"--result-json", mustTestDesignJSON(t, auditResult), "--format", "json",
	})
	requireTestDesignOK(t, []string{
		"test-design", "lane-accept", "--feature-dir", featureRel,
		"--lane-id", auditLaneID, "--attempt-id", auditAttemptID, "--format", "json",
	})

	validated := requireTestDesignOK(t, []string{"test-design", "validate", "--feature-dir", featureRel, "--format", "json"})
	if validated.Data["claim_status"] != "complete_against_frozen_scope" {
		t.Fatalf("claim_status=%#v, want complete_against_frozen_scope", validated.Data["claim_status"])
	}
	requireTestDesignOK(t, []string{"test-design", "handoff", "--feature-dir", featureRel, "--format", "json"})
	stateAfterHandoff, err := os.ReadFile(filepath.Join(artifactRoot, "test-state.json"))
	if err != nil {
		t.Fatal(err)
	}
	handoffAfterPublish, err := os.ReadFile(filepath.Join(artifactRoot, "handoff-to-tasks.json"))
	if err != nil {
		t.Fatal(err)
	}
	requireTestDesignOK(t, []string{"test-design", "handoff", "--feature-dir", featureRel, "--format", "json"})
	stateAfterRepeat, _ := os.ReadFile(filepath.Join(artifactRoot, "test-state.json"))
	handoffAfterRepeat, _ := os.ReadFile(filepath.Join(artifactRoot, "handoff-to-tasks.json"))
	if !bytes.Equal(stateAfterHandoff, stateAfterRepeat) || !bytes.Equal(handoffAfterPublish, handoffAfterRepeat) {
		t.Fatal("repeated handoff rewrote the frozen state or handoff binding")
	}
	revalidate, revalidateExit := runTestDesignWorkflowCommand(t, []string{"test-design", "validate", "--feature-dir", featureRel, "--format", "json"})
	if revalidateExit == 0 || revalidate.Status != "blocked" {
		t.Fatalf("validate regressed a handed-off generation: exit=%d env=%#v", revalidateExit, revalidate)
	}

	handoff := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "handoff-to-tasks.json"))
	if handoff["claim_status"] != "complete_against_frozen_scope" {
		t.Fatalf("handoff claim_status=%#v", handoff["claim_status"])
	}
	if handoff["next_command"] != "/sp.tasks" {
		t.Fatalf("handoff next_command=%#v", handoff["next_command"])
	}
	assertStringListEquals(t, handoff["test_case_refs"], []string{"test-catalog.json#/cases/TC-001"})
	assertStringListEquals(t, handoff["test_data_refs"], []string{"test-data-manifest.json#/datasets/TD-001"})
}

func TestTestDesignWorkflowSupportsProjectBaselineRoot(t *testing.T) {
	projectRoot := t.TempDir()
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(projectRoot, "README.md"), []byte("# Project\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)

	input := map[string]any{
		"query":           "Build a project test baseline",
		"source_refs":     []any{"README.md"},
		"included_paths":  []any{"."},
		"excluded_paths":  []any{"vendor"},
		"risk_dimensions": []any{"functional", "security", "operations"},
	}
	requireTestDesignOK(t, []string{
		"test-design", "init", "--scope", "project", "--mode", "project-baseline",
		"--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, input), "--format", "json",
	})

	for _, name := range []string{"test-state.json", "test-universe.json", "test-gaps.json"} {
		if _, err := os.Stat(filepath.Join(projectRoot, ".specify", "test-design", name)); err != nil {
			t.Fatalf("missing project baseline artifact %s: %v", name, err)
		}
	}
	metadata, ok := LookupArtifactType(".specify/test-design/test-universe.json")
	if !ok || metadata.Role != "canonical" || artifactTypeAllows(metadata, "submit") {
		t.Fatalf("project test universe metadata=%#v ok=%v", metadata, ok)
	}
	projectHandoff, projectHandoffExit := runTestDesignWorkflowCommand(t, []string{"test-design", "handoff", "--format", "json"})
	if projectHandoffExit == 0 || projectHandoff.Status != "blocked" || !strings.Contains(projectHandoff.Summary, "feature scope") {
		t.Fatalf("project baseline published a tasks handoff: exit=%d env=%#v", projectHandoffExit, projectHandoff)
	}
}

func TestTestDesignIncrementalInitRequiresCASAndInvalidatesPriorGeneration(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	for _, dir := range []string{"src", "tests", "docs"} {
		if err := os.MkdirAll(filepath.Join(projectRoot, dir), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(featureDir, "spec.md"), []byte("REQ-001\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)
	input := map[string]any{
		"query": "baseline", "source_refs": []any{featureRel + "/spec.md"},
		"included_paths": []any{"src", "tests"}, "excluded_paths": []any{"vendor"}, "risk_dimensions": []any{"functional", "security"},
	}
	requireTestDesignOK(t, []string{"test-design", "init", "--scope", "feature", "--mode", "feature", "--feature-dir", featureRel, "--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, input), "--format", "json"})
	artifactRoot := filepath.Join(featureDir, "test-design")
	writeValidTestDesignWorkflowBundle(t, artifactRoot, registerTestDesignEvidence(t, projectRoot, "incremental fixture"))

	state := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-state.json"))
	state["revision"] = 7
	state["phase"] = "handed-off"
	state["status"] = "complete"
	state["claim_status"] = "complete_against_frozen_scope"
	state["lanes"] = map[string]any{"manifest_ref": "lane-manifest.json", "accepted_result_refs": []any{"lane-results/LANE-001.json"}}
	state["audit"] = map[string]any{"status": "accepted", "lane_id": "AUDIT-001", "result_ref": "lane-results/AUDIT-001.json"}
	if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, "test-state.json"), state); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, "lane-manifest.json"), map[string]any{
		"version": 1, "artifact": "test-design-lane-manifest", "generation_id": "old-generation", "status": "accepted",
		"lanes": []any{map[string]any{"lane_id": "LANE-001", "kind": "discovery", "state": "accepted"}},
	}); err != nil {
		t.Fatal(err)
	}
	if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, "handoff-to-tasks.json"), map[string]any{"old": true}); err != nil {
		t.Fatal(err)
	}

	updateInput := map[string]any{
		"query": "incremental refresh", "source_refs": []any{featureRel + "/spec.md"},
		"included_paths": []any{"src", "tests", "docs"}, "excluded_paths": []any{"vendor"}, "risk_dimensions": []any{"functional", "security", "regression"},
	}
	missingCAS, exit := runTestDesignWorkflowCommand(t, []string{"test-design", "init", "--scope", "feature", "--mode", "incremental-update", "--feature-dir", featureRel, "--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, updateInput), "--format", "json"})
	if exit == 0 || missingCAS.Status != "blocked" {
		t.Fatalf("missing CAS exit=%d env=%#v", exit, missingCAS)
	}
	requireTestDesignOK(t, []string{"test-design", "init", "--scope", "feature", "--mode", "incremental-update", "--feature-dir", featureRel, "--leader-id", "leader-1", "--expected-revision", "7", "--input-json", mustTestDesignJSON(t, updateInput), "--format", "json"})

	resetState := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-state.json"))
	if resetState["revision"] != float64(8) || resetState["phase"] != "scoped" || resetState["claim_status"] != "pending" {
		t.Fatalf("reset state=%#v", resetState)
	}
	lanes := resetState["lanes"].(map[string]any)
	if len(lanes["accepted_result_refs"].([]any)) != 0 {
		t.Fatalf("accepted refs survived reset: %#v", lanes)
	}
	audit := resetState["audit"].(map[string]any)
	if audit["status"] != "pending" || audit["lane_id"] != nil || audit["result_ref"] != nil {
		t.Fatalf("audit survived reset: %#v", audit)
	}
	manifest := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "lane-manifest.json"))
	if len(manifest["lanes"].([]any)) != 0 || manifest["generation_id"] == "old-generation" {
		t.Fatalf("lane generation was not reset: %#v", manifest)
	}
	fingerprint := resetState["source"].(map[string]any)["fingerprint"].(string)
	if manifest["generation_id"] != "tdg-"+fingerprint[:16] {
		t.Fatalf("incremental generation_id=%#v, want canonical fingerprint-derived id", manifest["generation_id"])
	}
	if _, err := os.Stat(filepath.Join(artifactRoot, "handoff-to-tasks.json")); !os.IsNotExist(err) {
		t.Fatalf("old handoff remains public: %v", err)
	}
	universe := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-universe.json"))
	if universe["obligations"].([]any)[0].(map[string]any)["obligation_id"] != "TO-001" || universe["test_cases"].([]any)[0].(map[string]any)["test_case_id"] != "TC-001" {
		t.Fatalf("stable universe IDs changed: %#v", universe)
	}
	data := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-data-manifest.json"))
	if data["datasets"].([]any)[0].(map[string]any)["test_data_id"] != "TD-001" {
		t.Fatalf("stable data ID changed: %#v", data)
	}
}

func TestTestDesignAuditInitRejectsBoundaryChanges(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	for _, dir := range []string{"src", "secrets"} {
		if err := os.MkdirAll(filepath.Join(projectRoot, dir), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(featureDir, "spec.md"), []byte("REQ-001\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)
	input := map[string]any{"query": "baseline", "source_refs": []any{featureRel + "/spec.md"}, "included_paths": []any{"src"}, "excluded_paths": []any{"vendor"}, "risk_dimensions": []any{"functional"}}
	requireTestDesignOK(t, []string{"test-design", "init", "--scope", "feature", "--mode", "feature", "--feature-dir", featureRel, "--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, input), "--format", "json"})
	changed := map[string]any{"query": "audit", "source_refs": []any{featureRel + "/spec.md"}, "included_paths": []any{"src", "secrets"}, "excluded_paths": []any{"vendor"}, "risk_dimensions": []any{"functional"}}
	env, exit := runTestDesignWorkflowCommand(t, []string{"test-design", "init", "--scope", "feature", "--mode", "audit", "--feature-dir", featureRel, "--leader-id", "leader-1", "--expected-revision", "1", "--input-json", mustTestDesignJSON(t, changed), "--format", "json"})
	if exit == 0 || env.Status != "blocked" {
		t.Fatalf("audit boundary change exit=%d env=%#v", exit, env)
	}
	state := readTestDesignJSONMap(t, filepath.Join(featureDir, "test-design", "test-state.json"))
	if state["revision"] != float64(1) || state["mode"] != "feature" {
		t.Fatalf("rejected audit mutated state: %#v", state)
	}
}

func TestTestDesignLaneYieldPersistsAuditableReason(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(projectRoot, "src"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(featureDir, "spec.md"), []byte("REQ-001\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)
	input := map[string]any{"query": "yield", "source_refs": []any{featureRel + "/spec.md"}, "included_paths": []any{"src"}, "excluded_paths": []any{}, "risk_dimensions": []any{"functional"}}
	requireTestDesignOK(t, []string{"test-design", "init", "--scope", "feature", "--mode", "feature", "--feature-dir", featureRel, "--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, input), "--format", "json"})
	writeValidTestDesignWorkflowBundle(t, filepath.Join(featureDir, "test-design"), registerTestDesignEvidence(t, projectRoot, "yield fixture"))
	requireTestDesignOK(t, []string{"test-design", "universe-build", "--feature-dir", featureRel, "--format", "json"})
	lanes := map[string]any{"lanes": []any{map[string]any{
		"lane_id": "LANE-001", "kind": "discovery", "title": "bounded", "obligation_ids": []any{"TO-001"}, "read_paths": []any{"src"}, "questions": []any{"inspect"},
	}}}
	requireTestDesignOK(t, []string{"test-design", "lane-prepare", "--feature-dir", featureRel, "--input-json", mustTestDesignJSON(t, lanes), "--format", "json"})
	leaderLease, leaderLeaseExit := runTestDesignWorkflowCommand(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "leader-1", "--format", "json"})
	if leaderLeaseExit == 0 || leaderLease.Status != "blocked" {
		t.Fatalf("generation leader leased discovery lane: exit=%d env=%#v", leaderLeaseExit, leaderLease)
	}
	lease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "worker-1", "--format", "json"})
	attemptID := lease.Data["attempt_id"].(string)
	if attemptID != "ATTEMPT-001" {
		t.Fatalf("attempt_id=%q", attemptID)
	}
	requireTestDesignOK(t, []string{"test-design", "lane-yield", "--feature-dir", featureRel, "--lane-id", "LANE-001", "--attempt-id", attemptID, "--reason", "Need a bounded fixture owner decision", "--format", "json"})
	manifest := readTestDesignJSONMap(t, filepath.Join(featureDir, "test-design", "lane-manifest.json"))
	lane := manifest["lanes"].([]any)[0].(map[string]any)
	history := lane["yield_history"].([]any)
	if lane["state"] != "pending" || len(history) != 1 || history[0].(map[string]any)["reason"] != "Need a bounded fixture owner decision" {
		t.Fatalf("yield audit missing: %#v", lane)
	}
}

func TestTestDesignLaneCheckpointRejectsReadsOutsideTheFrozenPacket(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	if err := os.MkdirAll(filepath.Join(projectRoot, filepath.FromSlash(featureRel)), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(projectRoot, "src"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(projectRoot, filepath.FromSlash(featureRel), "spec.md"), []byte("REQ-001\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)

	input := map[string]any{
		"query": "scope", "source_refs": []any{featureRel + "/spec.md"},
		"included_paths": []any{"src"}, "excluded_paths": []any{}, "risk_dimensions": []any{"functional"},
	}
	requireTestDesignOK(t, []string{"test-design", "init", "--scope", "feature", "--mode", "feature", "--feature-dir", featureRel, "--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, input), "--format", "json"})
	writeValidTestDesignWorkflowBundle(t, filepath.Join(projectRoot, filepath.FromSlash(featureRel), "test-design"), registerTestDesignEvidence(t, projectRoot, "scope fixture"))
	requireTestDesignOK(t, []string{"test-design", "universe-build", "--feature-dir", featureRel, "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "lane-prepare", "--feature-dir", featureRel, "--input-json", mustTestDesignJSON(t, map[string]any{"lanes": []any{map[string]any{
		"lane_id": "LANE-001", "kind": "discovery", "title": "bounded", "obligation_ids": []any{"TO-001"}, "read_paths": []any{"src"}, "questions": []any{"inspect"},
	}}}), "--format", "json"})
	lease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "worker-1", "--format", "json"})
	attemptID := lease.Data["attempt_id"].(string)
	result := map[string]any{
		"lane_id": "LANE-001", "attempt_id": attemptID, "status": "success",
		"inspected_paths": []any{"secrets"}, "evidence_refs": []any{}, "candidate_cases": []any{},
		"data_requirements": []any{}, "contradictions": []any{}, "unknowns": []any{}, "gaps": []any{}, "summary": "escaped",
	}
	env, exit := runTestDesignWorkflowCommand(t, []string{"test-design", "lane-checkpoint", "--feature-dir", featureRel, "--lane-id", "LANE-001", "--attempt-id", attemptID, "--result-json", mustTestDesignJSON(t, result), "--format", "json"})
	if exit == 0 || env.Status != "invalid" {
		t.Fatalf("out-of-scope checkpoint exit=%d status=%q env=%#v", exit, env.Status, env)
	}
}

func TestTestDesignGapReconcileSupportsQualifiedHandoffAndBlocksBlockingGap(t *testing.T) {
	for _, tc := range []struct {
		name        string
		severity    string
		disposition string
		wantClaim   string
		wantHandoff bool
	}{
		{name: "nonblocking qualified", severity: "medium", disposition: "open", wantClaim: "qualified_with_declared_gaps", wantHandoff: true},
		{name: "deferred qualified", severity: "medium", disposition: "deferred", wantClaim: "qualified_with_declared_gaps", wantHandoff: true},
		{name: "blocking stops handoff", severity: "blocking", disposition: "open", wantClaim: "blocked", wantHandoff: false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			projectRoot := t.TempDir()
			featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
			featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
			if err := os.MkdirAll(featureDir, 0o755); err != nil {
				t.Fatal(err)
			}
			if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
				t.Fatal(err)
			}
			for _, dir := range []string{"src", "tests"} {
				if err := os.MkdirAll(filepath.Join(projectRoot, dir), 0o755); err != nil {
					t.Fatal(err)
				}
			}
			if err := os.WriteFile(filepath.Join(projectRoot, "src", "approval.go"), []byte("package approval\n"), 0o644); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(filepath.Join(featureDir, "spec.md"), []byte("REQ-001\n"), 0o644); err != nil {
				t.Fatal(err)
			}
			withTestDesignCWD(t, projectRoot)
			input := map[string]any{
				"query": "gap lifecycle", "source_refs": []any{featureRel + "/spec.md"},
				"included_paths": []any{"src", "tests"}, "excluded_paths": []any{}, "risk_dimensions": []any{"functional", "state"},
			}
			requireTestDesignOK(t, []string{"test-design", "init", "--scope", "feature", "--mode", "feature", "--feature-dir", featureRel, "--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, input), "--format", "json"})
			evidenceRef := registerTestDesignEvidence(t, projectRoot, "gap diagnostics")
			artifactRoot := filepath.Join(featureDir, "test-design")
			writeValidTestDesignWorkflowBundle(t, artifactRoot, evidenceRef)
			requireTestDesignOK(t, []string{"test-design", "universe-build", "--feature-dir", featureRel, "--format", "json"})
			lanes := map[string]any{"lanes": []any{map[string]any{
				"lane_id": "LANE-001", "kind": "discovery", "title": "Gap discovery", "obligation_ids": []any{"TO-001"},
				"read_paths": []any{"src", "tests", featureRel + "/spec.md"}, "questions": []any{"Find residual gaps."},
			}}}
			requireTestDesignOK(t, []string{"test-design", "lane-prepare", "--feature-dir", featureRel, "--input-json", mustTestDesignJSON(t, lanes), "--format", "json"})
			lease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "worker-1", "--format", "json"})
			attemptID := lease.Data["attempt_id"].(string)
			result := map[string]any{
				"lane_id": "LANE-001", "attempt_id": attemptID, "status": "success",
				"inspected_paths": []any{"src", "tests", featureRel + "/spec.md"}, "evidence_refs": []any{evidenceRef},
				"obligation_results": []any{map[string]any{
					"obligation_id": "TO-001", "status": "gap", "evidence_refs": []any{}, "gap_refs": []any{"GAP-001"}, "summary": "Residual coverage gap found.",
				}},
				"checks": []any{}, "candidate_cases": []any{map[string]any{"test_case_id": "TC-001"}},
				"data_requirements": []any{map[string]any{"test_data_id": "TD-001"}},
				"contradictions":    []any{}, "unknowns": []any{}, "gaps": []any{map[string]any{"gap_id": "GAP-001"}}, "summary": "Gap proposed.",
			}
			requireTestDesignOK(t, []string{"test-design", "lane-checkpoint", "--feature-dir", featureRel, "--lane-id", "LANE-001", "--attempt-id", attemptID, "--result-json", mustTestDesignJSON(t, result), "--format", "json"})
			requireTestDesignOK(t, []string{"test-design", "lane-accept", "--feature-dir", featureRel, "--lane-id", "LANE-001", "--attempt-id", attemptID, "--format", "json"})
			state := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-state.json"))
			gap := map[string]any{
				"gap_id": "GAP-001", "category": "coverage", "severity": tc.severity, "disposition": tc.disposition,
				"source_refs": []any{"REQ-001"}, "affected_obligation_refs": []any{"TO-001"}, "coverage_refs": []any{"COV-001"},
				"affected_test_case_refs": []any{"TC-001"}, "affected_test_data_refs": []any{},
				"owner": "test-design leader", "residual_risk": "A bounded residual coverage gap remains.",
				"next_action": "Carry the gap into implementation validation.", "unblock_criteria": "Close the residual coverage gap.",
			}
			requireTestDesignOK(t, []string{"test-design", "gap-reconcile", "--feature-dir", featureRel, "--leader-id", "leader-1", "--expected-revision", fmt.Sprint(intFromAny(state["revision"])), "--input-json", mustTestDesignJSON(t, map[string]any{"gaps": []any{gap}}), "--format", "json"})
			requireTestDesignOK(t, []string{"test-design", "synthesize", "--feature-dir", featureRel, "--leader-id", "leader-1", "--format", "json"})
			requireTestDesignOK(t, []string{"test-design", "audit-prepare", "--feature-dir", featureRel, "--format", "json"})
			auditLease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "auditor-1", "--format", "json"})
			auditLaneID := auditLease.Data["lane_id"].(string)
			auditAttemptID := auditLease.Data["attempt_id"].(string)
			auditPaths := []any{}
			for _, name := range []string{"test-universe.json", "test-catalog.json", "test-data-manifest.json", "coverage-matrix.json", "test-gaps.json"} {
				auditPaths = append(auditPaths, filepath.ToSlash(filepath.Join(featureRel, "test-design", name)))
			}
			auditResult := map[string]any{
				"lane_id": auditLaneID, "attempt_id": auditAttemptID, "status": "success", "inspected_paths": auditPaths, "evidence_refs": []any{evidenceRef},
				"obligation_results": []any{map[string]any{
					"obligation_id": "TO-001", "status": "gap", "evidence_refs": []any{}, "gap_refs": []any{"GAP-001"}, "summary": "Canonical residual gap independently confirmed.",
				}},
				"checks": testDesignAuditChecks(evidenceRef), "candidate_cases": []any{}, "data_requirements": []any{},
				"contradictions": []any{}, "unknowns": []any{}, "gaps": []any{}, "findings": []any{}, "summary": "Independent gap audit confirms the canonical residual gap.",
			}
			requireTestDesignOK(t, []string{"test-design", "lane-checkpoint", "--feature-dir", featureRel, "--lane-id", auditLaneID, "--attempt-id", auditAttemptID, "--result-json", mustTestDesignJSON(t, auditResult), "--format", "json"})
			requireTestDesignOK(t, []string{"test-design", "lane-accept", "--feature-dir", featureRel, "--lane-id", auditLaneID, "--attempt-id", auditAttemptID, "--format", "json"})
			validated, exit := runTestDesignWorkflowCommand(t, []string{"test-design", "validate", "--feature-dir", featureRel, "--format", "json"})
			if validated.Data["claim_status"] != tc.wantClaim {
				t.Fatalf("claim_status=%#v want=%s env=%#v", validated.Data["claim_status"], tc.wantClaim, validated)
			}
			if tc.wantHandoff {
				if exit != 0 || validated.Status != "ok" {
					t.Fatalf("qualified validation exit=%d env=%#v", exit, validated)
				}
				requireTestDesignOK(t, []string{"test-design", "handoff", "--feature-dir", featureRel, "--format", "json"})
			} else {
				if exit == 0 || validated.Status != "blocked" {
					t.Fatalf("blocking validation exit=%d env=%#v", exit, validated)
				}
				handoff, handoffExit := runTestDesignWorkflowCommand(t, []string{"test-design", "handoff", "--feature-dir", featureRel, "--format", "json"})
				if handoffExit == 0 || handoff.Status != "blocked" {
					t.Fatalf("blocking gap handoff exit=%d env=%#v", handoffExit, handoff)
				}
			}
		})
	}
}

func TestTestDesignAuditFindingRepairRequiresFreshAuditWave(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	for _, dir := range []string{"src", "tests"} {
		if err := os.MkdirAll(filepath.Join(projectRoot, dir), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(projectRoot, "src", "approval.go"), []byte("package approval\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(featureDir, "spec.md"), []byte("REQ-001\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)
	input := map[string]any{
		"query": "audit repair loop", "source_refs": []any{featureRel + "/spec.md"},
		"included_paths": []any{"src", "tests"}, "excluded_paths": []any{}, "risk_dimensions": []any{"functional", "state"},
	}
	requireTestDesignOK(t, []string{"test-design", "init", "--scope", "feature", "--mode", "feature", "--feature-dir", featureRel, "--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, input), "--format", "json"})
	evidenceRef := registerTestDesignEvidence(t, projectRoot, "audit repair evidence")
	artifactRoot := filepath.Join(featureDir, "test-design")
	writeValidTestDesignWorkflowBundle(t, artifactRoot, evidenceRef)
	requireTestDesignOK(t, []string{"test-design", "universe-build", "--feature-dir", featureRel, "--format", "json"})
	lanes := map[string]any{"lanes": []any{map[string]any{
		"lane_id": "LANE-001", "kind": "discovery", "title": "Independent discovery", "obligation_ids": []any{"TO-001"},
		"read_paths": []any{"src", "tests", featureRel + "/spec.md"}, "questions": []any{"Prove the frozen obligation."},
	}}}
	requireTestDesignOK(t, []string{"test-design", "lane-prepare", "--feature-dir", featureRel, "--input-json", mustTestDesignJSON(t, lanes), "--format", "json"})
	discoveryLease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "worker-1", "--format", "json"})
	discoveryAttempt := discoveryLease.Data["attempt_id"].(string)
	discoveryResult := map[string]any{
		"lane_id": "LANE-001", "attempt_id": discoveryAttempt, "status": "success",
		"inspected_paths": []any{"src", "tests", featureRel + "/spec.md"}, "evidence_refs": []any{evidenceRef},
		"obligation_results": testDesignCoveredObligationResult(evidenceRef), "checks": []any{},
		"candidate_cases": []any{map[string]any{"test_case_id": "TC-001"}}, "data_requirements": []any{map[string]any{"test_data_id": "TD-001"}},
		"contradictions": []any{}, "unknowns": []any{}, "gaps": []any{}, "summary": "Discovery complete.",
	}
	requireTestDesignOK(t, []string{"test-design", "lane-checkpoint", "--feature-dir", featureRel, "--lane-id", "LANE-001", "--attempt-id", discoveryAttempt, "--result-json", mustTestDesignJSON(t, discoveryResult), "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "lane-accept", "--feature-dir", featureRel, "--lane-id", "LANE-001", "--attempt-id", discoveryAttempt, "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "synthesize", "--feature-dir", featureRel, "--leader-id", "leader-1", "--format", "json"})

	auditPaths := []any{}
	for _, name := range []string{"test-universe.json", "test-catalog.json", "test-data-manifest.json", "coverage-matrix.json", "test-gaps.json"} {
		auditPaths = append(auditPaths, filepath.ToSlash(filepath.Join(featureRel, "test-design", name)))
	}
	requireTestDesignOK(t, []string{"test-design", "audit-prepare", "--feature-dir", featureRel, "--format", "json"})
	firstLease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "auditor-1", "--format", "json"})
	firstLane := firstLease.Data["lane_id"].(string)
	firstAttempt := firstLease.Data["attempt_id"].(string)
	firstChecks := testDesignAuditChecks(evidenceRef)
	firstCheck := firstChecks[0].(map[string]any)
	firstCheck["status"] = "finding"
	firstCheck["finding_refs"] = []any{"FIND-001"}
	firstResult := map[string]any{
		"lane_id": firstLane, "attempt_id": firstAttempt, "status": "success", "inspected_paths": auditPaths, "evidence_refs": []any{evidenceRef},
		"obligation_results": []any{map[string]any{"obligation_id": "TO-001", "status": "gap", "evidence_refs": []any{}, "gap_refs": []any{"GAP-900"}, "summary": "Audit found a residual gap."}},
		"checks":             firstChecks, "candidate_cases": []any{}, "data_requirements": []any{}, "contradictions": []any{}, "unknowns": []any{},
		"gaps": []any{map[string]any{"gap_id": "GAP-900"}}, "findings": []any{map[string]any{"finding_id": "FIND-001", "status": "open"}}, "summary": "Repair is required.",
	}
	requireTestDesignOK(t, []string{"test-design", "lane-checkpoint", "--feature-dir", featureRel, "--lane-id", firstLane, "--attempt-id", firstAttempt, "--result-json", mustTestDesignJSON(t, firstResult), "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "lane-accept", "--feature-dir", featureRel, "--lane-id", firstLane, "--attempt-id", firstAttempt, "--format", "json"})
	blockedValidation, blockedExit := runTestDesignWorkflowCommand(t, []string{"test-design", "validate", "--feature-dir", featureRel, "--format", "json"})
	if blockedExit == 0 || blockedValidation.Status != "blocked" {
		t.Fatalf("unresolved audit finding validated: exit=%d env=%#v", blockedExit, blockedValidation)
	}

	state := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-state.json"))
	gap := map[string]any{
		"gap_id": "GAP-900", "category": "coverage", "severity": "medium", "disposition": "waived",
		"source_refs": []any{"REQ-001"}, "affected_obligation_refs": []any{"TO-001"}, "coverage_refs": []any{"COV-001"},
		"affected_test_case_refs": []any{"TC-001"}, "affected_test_data_refs": []any{}, "owner": "test-design leader",
		"residual_risk": "The audit-confirmed residual risk is explicitly carried.", "next_action": "Verify during implementation.", "unblock_criteria": "Replace the waiver with direct coverage.",
	}
	requireTestDesignOK(t, []string{"test-design", "gap-reconcile", "--feature-dir", featureRel, "--leader-id", "leader-1", "--expected-revision", fmt.Sprint(intFromAny(state["revision"])), "--input-json", mustTestDesignJSON(t, map[string]any{"gaps": []any{gap}}), "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "synthesize", "--feature-dir", featureRel, "--leader-id", "leader-1", "--format", "json"})
	manifest := readTestDesignJSONMap(t, filepath.Join(artifactRoot, "lane-manifest.json"))
	if len(manifest["lanes"].([]any)) != 1 {
		t.Fatalf("old audit wave remained active after repair synthesis: %#v", manifest["lanes"])
	}
	state = readTestDesignJSONMap(t, filepath.Join(artifactRoot, "test-state.json"))
	if state["audit"].(map[string]any)["status"] != "pending" || len(state["lanes"].(map[string]any)["accepted_result_refs"].([]any)) != 1 {
		t.Fatalf("old audit state/result refs were not invalidated: %#v", state)
	}

	requireTestDesignOK(t, []string{"test-design", "audit-prepare", "--feature-dir", featureRel, "--format", "json"})
	secondLease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "auditor-2", "--format", "json"})
	secondLane := secondLease.Data["lane_id"].(string)
	secondAttempt := secondLease.Data["attempt_id"].(string)
	if secondLane != "AUDIT-002" {
		t.Fatalf("fresh audit wave lane_id=%q, want AUDIT-002", secondLane)
	}
	secondResult := map[string]any{
		"lane_id": secondLane, "attempt_id": secondAttempt, "status": "success", "inspected_paths": auditPaths, "evidence_refs": []any{evidenceRef},
		"obligation_results": []any{map[string]any{"obligation_id": "TO-001", "status": "gap", "evidence_refs": []any{}, "gap_refs": []any{"GAP-900"}, "summary": "Declared residual gap is fully accounted."}},
		"checks":             testDesignAuditChecks(evidenceRef), "candidate_cases": []any{}, "data_requirements": []any{}, "contradictions": []any{}, "unknowns": []any{},
		"gaps": []any{}, "findings": []any{}, "summary": "Fresh audit confirms the repaired canonical bundle.",
	}
	requireTestDesignOK(t, []string{"test-design", "lane-checkpoint", "--feature-dir", featureRel, "--lane-id", secondLane, "--attempt-id", secondAttempt, "--result-json", mustTestDesignJSON(t, secondResult), "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "lane-accept", "--feature-dir", featureRel, "--lane-id", secondLane, "--attempt-id", secondAttempt, "--format", "json"})
	validated := requireTestDesignOK(t, []string{"test-design", "validate", "--feature-dir", featureRel, "--format", "json"})
	if validated.Data["claim_status"] != "qualified_with_declared_gaps" {
		t.Fatalf("repaired audit claim=%#v", validated.Data["claim_status"])
	}
	requireTestDesignOK(t, []string{"test-design", "handoff", "--feature-dir", featureRel, "--format", "json"})
}

func TestTestDesignEvidenceVerifierRejectsMetadataAndObjectTampering(t *testing.T) {
	for _, tc := range []struct {
		name   string
		mutate func(t *testing.T, projectRoot, ref string, record map[string]any)
	}{
		{name: "empty metadata", mutate: func(t *testing.T, projectRoot, ref string, record map[string]any) {
			record["source"] = ""
			if err := writeTestDesignJSONFixture(filepath.Join(projectRoot, filepath.FromSlash(ref)), record); err != nil {
				t.Fatal(err)
			}
		}},
		{name: "identity metadata tamper", mutate: func(t *testing.T, projectRoot, ref string, record map[string]any) {
			record["provenance"] = "forged provenance"
			if err := writeTestDesignJSONFixture(filepath.Join(projectRoot, filepath.FromSlash(ref)), record); err != nil {
				t.Fatal(err)
			}
		}},
		{name: "object bytes tamper", mutate: func(t *testing.T, projectRoot, _ string, record map[string]any) {
			objectPath := filepath.Join(projectRoot, filepath.FromSlash(record["object_ref"].(string)))
			if err := os.Chmod(objectPath, 0o644); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(objectPath, []byte("tampered"), 0o644); err != nil {
				t.Fatal(err)
			}
		}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			projectRoot := t.TempDir()
			ref := registerTestDesignEvidence(t, projectRoot, "authentic evidence")
			service := testDesignService{projectRoot: projectRoot}
			if err := service.verifyEvidenceRefs([]string{ref}); err != nil {
				t.Fatalf("authentic evidence rejected: %v", err)
			}
			record := readTestDesignJSONMap(t, filepath.Join(projectRoot, filepath.FromSlash(ref)))
			tc.mutate(t, projectRoot, ref, record)
			if err := service.verifyEvidenceRefs([]string{ref}); err == nil {
				t.Fatal("tampered evidence was accepted")
			}
		})
	}
}

func TestTestDesignBundleRejectsSemanticCoverageAndReadinessShortcuts(t *testing.T) {
	newBundle := func(t *testing.T) testDesignBundle {
		artifactRoot := t.TempDir()
		writeValidTestDesignWorkflowBundle(t, artifactRoot, "")
		bundle, err := testDesignReadBundle(artifactRoot)
		if err != nil {
			t.Fatal(err)
		}
		return bundle
	}
	t.Run("applicable cannot be not applicable coverage", func(t *testing.T) {
		bundle := newBundle(t)
		row := bundle.CoverageMatrix["rows"].([]any)[0].(map[string]any)
		row["status"] = "not_applicable"
		row["evidence_refs"] = []any{}
		row["acceptance_refs"] = []any{}
		if err := testDesignValidateBundle(bundle); err == nil || !strings.Contains(err.Error(), "incompatible with applicable") {
			t.Fatalf("invalid applicability/status matrix error=%v", err)
		}
	})
	t.Run("not applicable and recipe ready remain complete", func(t *testing.T) {
		bundle := newBundle(t)
		obligation := bundle.Universe["obligations"].([]any)[0].(map[string]any)
		obligation["applicability"] = "not_applicable"
		row := bundle.CoverageMatrix["rows"].([]any)[0].(map[string]any)
		row["status"] = "not_applicable"
		row["evidence_refs"] = []any{}
		row["acceptance_refs"] = []any{}
		dataset := bundle.DataManifest["datasets"].([]any)[0].(map[string]any)
		dataset["readiness"] = "recipe-ready"
		if err := testDesignValidateBundle(bundle); err != nil {
			t.Fatalf("valid explained denominator rejected: %v", err)
		}
		if claim := testDesignClassifyClaim(bundle); claim != "complete_against_frozen_scope" {
			t.Fatalf("claim=%s", claim)
		}
	})
	for _, tc := range []struct {
		name   string
		mutate func(testDesignBundle)
	}{
		{name: "deferred data without gap", mutate: func(bundle testDesignBundle) {
			dataset := bundle.DataManifest["datasets"].([]any)[0].(map[string]any)
			dataset["disposition"] = "defer"
			dataset["readiness"] = "deferred"
			dataset["blocker_reason"] = "Deferred by scope"
			dataset["unblock_criteria"] = "Scope is restored"
		}},
		{name: "deferred case variant without gap", mutate: func(bundle testDesignBundle) {
			candidate := bundle.Catalog["cases"].([]any)[0].(map[string]any)
			candidate["variants"].(map[string]any)["compatibility"] = "deferred"
		}},
		{name: "steps expected results mismatch", mutate: func(bundle testDesignBundle) {
			candidate := bundle.Catalog["cases"].([]any)[0].(map[string]any)
			candidate["expected_results"] = []any{"Only one oracle"}
		}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bundle := newBundle(t)
			tc.mutate(bundle)
			if err := testDesignValidateBundle(bundle); err == nil {
				t.Fatal("semantic shortcut was accepted")
			}
		})
	}
}

func TestTestDesignAuditRequiresIndependentCompleteEvidenceBackedAccounting(t *testing.T) {
	projectRoot := t.TempDir()
	evidenceRef := registerTestDesignEvidence(t, projectRoot, "audit evidence")
	service := testDesignService{projectRoot: projectRoot}
	auditLane := testDesignLane{
		LaneID: "AUDIT-001", Kind: "audit", AttemptID: "ATTEMPT-001", ObligationIDs: []string{"TO-001"},
		ReadPaths: []string{"root/test-universe.json", "root/test-catalog.json", "root/test-data-manifest.json", "root/coverage-matrix.json", "root/test-gaps.json"},
	}
	base := map[string]any{
		"lane_id": "AUDIT-001", "attempt_id": "ATTEMPT-001", "status": "success",
		"inspected_paths": stringsToAny(auditLane.ReadPaths), "evidence_refs": []any{evidenceRef},
		"obligation_results": testDesignCoveredObligationResult(evidenceRef), "checks": []any{},
		"candidate_cases": []any{}, "data_requirements": []any{}, "contradictions": []any{}, "unknowns": []any{}, "gaps": []any{}, "findings": []any{}, "summary": "summary only",
	}
	if err := service.validateLaneResult(base, auditLane); err == nil {
		t.Fatal("summary-only empty audit checks were accepted")
	}
	auditLane.ObligationIDs = []string{"TO-001", "TO-002"}
	base["checks"] = testDesignAuditChecks(evidenceRef)
	if err := service.validateLaneResult(base, auditLane); err == nil || !strings.Contains(err.Error(), "exactly the assigned obligation") {
		t.Fatalf("unaccounted obligation error=%v", err)
	}
	manifest := testDesignLaneManifest{LeaderID: "leader-1", SynthesisOwnerID: "leader-1", Lanes: []testDesignLane{{Kind: "discovery", State: "accepted", WorkerID: "worker-1"}}}
	if !testDesignAuditWorkerConflict(manifest, "leader-1") || !testDesignAuditWorkerConflict(manifest, "worker-1") || testDesignAuditWorkerConflict(manifest, "auditor-1") {
		t.Fatalf("audit identity conflict policy is incorrect")
	}
}

func TestTestDesignStatusValidateAndHandoffRejectEditedIncludedSource(t *testing.T) {
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	if err := os.MkdirAll(filepath.Join(projectRoot, filepath.FromSlash(featureRel)), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)
	publishValidTestDesignHandoff(t, projectRoot, featureRel)
	if err := os.WriteFile(filepath.Join(projectRoot, "src", "approval.go"), []byte("package approval\n// changed\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	for _, command := range [][]string{
		{"test-design", "status", "--feature-dir", featureRel, "--format", "json"},
		{"test-design", "handoff", "--feature-dir", featureRel, "--format", "json"},
		{"test-design", "validate", "--feature-dir", featureRel, "--format", "json"},
	} {
		env, exit := runTestDesignWorkflowCommand(t, command)
		if exit == 0 || env.Status != "blocked" {
			t.Fatalf("stale command %v exit=%d env=%#v", command, exit, env)
		}
	}
}

func TestTestDesignRejectsUnknownRepeatedAndMissingOptionValues(t *testing.T) {
	for _, args := range [][]string{
		{"test-design", "status", "--modee", "feature", "--format", "json"},
		{"test-design", "status", "--feature-dir", "a", "--feature-dir", "b", "--format", "json"},
		{"test-design", "status", "--feature-dir", "--format", "json"},
	} {
		env, exit := runTestDesignWorkflowCommand(t, args)
		if exit == 0 || env.Status != "usage-error" {
			t.Fatalf("invalid options %v exit=%d env=%#v", args, exit, env)
		}
	}
}

func TestTestDesignArchiveRejectsSymlinkOrJunctionHistory(t *testing.T) {
	projectRoot := t.TempDir()
	root := filepath.Join(projectRoot, ".specify", "test-design")
	outside := t.TempDir()
	if err := os.MkdirAll(root, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "handoff-to-tasks.json"), []byte("{}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	history := filepath.Join(root, "handoff-history")
	var err error
	if runtime.GOOS == "windows" {
		err = exec.Command("cmd", "/c", "mklink", "/J", history, outside).Run()
	} else {
		err = os.Symlink(outside, history)
	}
	if err != nil {
		t.Skipf("platform cannot create symlink/junction fixture: %v", err)
	}
	service := testDesignService{projectRoot: projectRoot}
	if _, err := service.archiveHandoff(root, 1); err == nil {
		t.Fatal("archive accepted a symlink/junction handoff-history path")
	}
}

func TestTestDesignCheckpointTransactionRejectsSymlinkOrJunctionParent(t *testing.T) {
	fixture := setupLeasedTestDesignDiscovery(t)
	laneResults := filepath.Join(fixture.artifactRoot, "lane-results")
	if err := os.MkdirAll(laneResults, 0o755); err != nil {
		t.Fatal(err)
	}
	outside := t.TempDir()
	checkpointParent := filepath.Join(laneResults, "checkpoints")
	var linkErr error
	if runtime.GOOS == "windows" {
		linkErr = exec.Command("cmd", "/c", "mklink", "/J", checkpointParent, outside).Run()
	} else {
		linkErr = os.Symlink(outside, checkpointParent)
	}
	if linkErr != nil {
		t.Skipf("platform cannot create symlink/junction fixture: %v", linkErr)
	}
	result := fixture.discoveryResult("junction target must be rejected")
	env, exit := runTestDesignWorkflowCommand(t, []string{
		"test-design", "lane-checkpoint", "--feature-dir", fixture.featureRel,
		"--lane-id", "LANE-001", "--attempt-id", fixture.attemptID,
		"--result-json", mustTestDesignJSON(t, result), "--format", "json",
	})
	if exit == 0 || env.Status != "error" {
		t.Fatalf("checkpoint transaction accepted a symlink/junction parent: exit=%d env=%#v", exit, env)
	}
	entries, err := os.ReadDir(outside)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Fatalf("checkpoint transaction wrote outside the project: %#v", entries)
	}
}

func TestTestDesignReentryPreservesImmutableContentAddressedLaneHistory(t *testing.T) {
	fixture := setupLeasedTestDesignDiscovery(t)
	firstResult := fixture.discoveryResult("generation one result")
	requireTestDesignOK(t, []string{
		"test-design", "lane-checkpoint", "--feature-dir", fixture.featureRel,
		"--lane-id", "LANE-001", "--attempt-id", fixture.attemptID,
		"--result-json", mustTestDesignJSON(t, firstResult), "--format", "json",
	})
	requireTestDesignOK(t, []string{
		"test-design", "lane-accept", "--feature-dir", fixture.featureRel,
		"--lane-id", "LANE-001", "--attempt-id", fixture.attemptID, "--format", "json",
	})
	firstManifest, err := testDesignReadManifest(fixture.artifactRoot)
	if err != nil {
		t.Fatal(err)
	}
	firstLane := firstManifest.Lanes[0]
	firstCheckpointPath := filepath.Join(fixture.artifactRoot, filepath.FromSlash(firstLane.CheckpointRef))
	firstResultPath := filepath.Join(fixture.artifactRoot, filepath.FromSlash(firstLane.ResultRef))
	firstCheckpointBytes, err := os.ReadFile(firstCheckpointPath)
	if err != nil {
		t.Fatal(err)
	}
	firstResultBytes, err := os.ReadFile(firstResultPath)
	if err != nil {
		t.Fatal(err)
	}
	state, err := testDesignReadState(fixture.artifactRoot)
	if err != nil {
		t.Fatal(err)
	}
	requireTestDesignOK(t, []string{
		"test-design", "init", "--scope", "feature", "--mode", "incremental-update",
		"--feature-dir", fixture.featureRel, "--leader-id", "leader-1",
		"--expected-revision", fmt.Sprint(state.Revision), "--input-json", mustTestDesignJSON(t, fixture.initInput), "--format", "json",
	})
	assertTestDesignFileBytes(t, firstCheckpointPath, firstCheckpointBytes)
	assertTestDesignFileBytes(t, firstResultPath, firstResultBytes)

	requireTestDesignOK(t, []string{"test-design", "universe-build", "--feature-dir", fixture.featureRel, "--format", "json"})
	requireTestDesignOK(t, []string{
		"test-design", "lane-prepare", "--feature-dir", fixture.featureRel,
		"--input-json", mustTestDesignJSON(t, fixture.lanes), "--format", "json",
	})
	secondLease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", fixture.featureRel, "--worker-id", "worker-2", "--format", "json"})
	fixture.attemptID = secondLease.Data["attempt_id"].(string)
	secondResult := fixture.discoveryResult("generation two changed result")
	requireTestDesignOK(t, []string{
		"test-design", "lane-checkpoint", "--feature-dir", fixture.featureRel,
		"--lane-id", "LANE-001", "--attempt-id", fixture.attemptID,
		"--result-json", mustTestDesignJSON(t, secondResult), "--format", "json",
	})
	requireTestDesignOK(t, []string{
		"test-design", "lane-accept", "--feature-dir", fixture.featureRel,
		"--lane-id", "LANE-001", "--attempt-id", fixture.attemptID, "--format", "json",
	})
	secondManifest, err := testDesignReadManifest(fixture.artifactRoot)
	if err != nil {
		t.Fatal(err)
	}
	secondLane := secondManifest.Lanes[0]
	if secondLane.CheckpointRef == firstLane.CheckpointRef || secondLane.ResultRef == firstLane.ResultRef {
		t.Fatalf("changed reentry result reused immutable paths: old=%s/%s new=%s/%s", firstLane.CheckpointRef, firstLane.ResultRef, secondLane.CheckpointRef, secondLane.ResultRef)
	}
	assertTestDesignFileBytes(t, firstCheckpointPath, firstCheckpointBytes)
	assertTestDesignFileBytes(t, firstResultPath, firstResultBytes)
}

type testDesignDiscoveryFixture struct {
	projectRoot  string
	featureRel   string
	artifactRoot string
	evidenceRef  string
	attemptID    string
	initInput    map[string]any
	lanes        map[string]any
}

func setupLeasedTestDesignDiscovery(t *testing.T) testDesignDiscoveryFixture {
	t.Helper()
	projectRoot := t.TempDir()
	featureRel := filepath.ToSlash(filepath.Join("specs", "001-test-design"))
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	if err := os.MkdirAll(featureDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := seedTestDesignScaffoldTemplates(projectRoot); err != nil {
		t.Fatal(err)
	}
	for _, dir := range []string{"src", "tests"} {
		if err := os.MkdirAll(filepath.Join(projectRoot, dir), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(projectRoot, "src", "approval.go"), []byte("package approval\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(featureDir, "spec.md"), []byte("REQ-001\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)
	initInput := map[string]any{
		"query": "immutable lane history", "source_refs": []any{featureRel + "/spec.md"},
		"included_paths": []any{"src", "tests"}, "excluded_paths": []any{}, "risk_dimensions": []any{"functional", "state"},
	}
	requireTestDesignOK(t, []string{
		"test-design", "init", "--scope", "feature", "--mode", "feature", "--feature-dir", featureRel,
		"--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, initInput), "--format", "json",
	})
	evidenceRef := registerTestDesignEvidence(t, projectRoot, "immutable history evidence")
	artifactRoot := filepath.Join(featureDir, "test-design")
	writeValidTestDesignWorkflowBundle(t, artifactRoot, evidenceRef)
	requireTestDesignOK(t, []string{"test-design", "universe-build", "--feature-dir", featureRel, "--format", "json"})
	lanes := map[string]any{"lanes": []any{map[string]any{
		"lane_id": "LANE-001", "kind": "discovery", "title": "Independent discovery", "obligation_ids": []any{"TO-001"},
		"read_paths": []any{"src", "tests", featureRel + "/spec.md"}, "questions": []any{"Prove the frozen obligation."},
	}}}
	requireTestDesignOK(t, []string{"test-design", "lane-prepare", "--feature-dir", featureRel, "--input-json", mustTestDesignJSON(t, lanes), "--format", "json"})
	lease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "worker-1", "--format", "json"})
	return testDesignDiscoveryFixture{
		projectRoot: projectRoot, featureRel: featureRel, artifactRoot: artifactRoot,
		evidenceRef: evidenceRef, attemptID: lease.Data["attempt_id"].(string), initInput: initInput, lanes: lanes,
	}
}

func (fixture testDesignDiscoveryFixture) discoveryResult(summary string) map[string]any {
	return map[string]any{
		"lane_id": "LANE-001", "attempt_id": fixture.attemptID, "status": "success",
		"inspected_paths": []any{"src", "tests", fixture.featureRel + "/spec.md"}, "evidence_refs": []any{fixture.evidenceRef},
		"obligation_results": testDesignCoveredObligationResult(fixture.evidenceRef), "checks": []any{},
		"candidate_cases": []any{map[string]any{"test_case_id": "TC-001"}}, "data_requirements": []any{map[string]any{"test_data_id": "TD-001"}},
		"contradictions": []any{}, "unknowns": []any{}, "gaps": []any{}, "summary": summary,
	}
}

func assertTestDesignFileBytes(t *testing.T, path string, want []byte) {
	t.Helper()
	got, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, want) {
		t.Fatalf("immutable runtime artifact changed: %s", path)
	}
}

func runTestDesignWorkflowCommand(t *testing.T, args []string) (Envelope, int) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	exit := Run(args, &stdout, &stderr, "test")
	var env Envelope
	if err := json.Unmarshal(stdout.Bytes(), &env); err != nil {
		t.Fatalf("decode envelope for %v: %v; stdout=%q stderr=%q", args, err, stdout.String(), stderr.String())
	}
	return env, exit
}

func requireTestDesignOK(t *testing.T, args []string) Envelope {
	t.Helper()
	env, exit := runTestDesignWorkflowCommand(t, args)
	if exit != 0 || env.Status != "ok" {
		t.Fatalf("command %v exit=%d env=%#v", args, exit, env)
	}
	return env
}

func withTestDesignCWD(t *testing.T, projectRoot string) {
	t.Helper()
	oldCWD, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(projectRoot); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(oldCWD) })
}

func mustTestDesignJSON(t *testing.T, payload any) string {
	t.Helper()
	raw, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}

func writeValidTestDesignWorkflowBundle(t *testing.T, artifactRoot, evidenceRef string) {
	t.Helper()
	evidenceRefs := []any{}
	if evidenceRef != "" {
		evidenceRefs = append(evidenceRefs, evidenceRef)
	}
	fixtures := map[string]map[string]any{
		"test-universe.json": {
			"version": 1, "artifact": "test-universe", "feature_ref": "specs/001-test-design",
			"obligations": []any{map[string]any{
				"obligation_id": "TO-001", "title": "Approval is idempotent", "source_refs": []any{"REQ-001"},
				"capability_refs": []any{"CAP-001"}, "scenario_refs": []any{"SCN-001"}, "dimension": "state", "risk_tier": "high",
				"applicability": "applicable", "rationale": "Duplicate approval corrupts state", "required_evidence_classes": []any{"runtime-diagnostics"},
				"test_case_ids": []any{"TC-001"}, "gap_refs": []any{}, "invalidation_triggers": []any{"approval state machine changes"},
			}},
			"capabilities": []any{map[string]any{"capability_id": "CAP-001", "title": "Approval", "requirement_refs": []any{"REQ-001"}, "obligation_ids": []any{"TO-001"}, "test_case_ids": []any{"TC-001"}, "scenario_ids": []any{"SCN-001"}}},
			"scenarios":    []any{map[string]any{"scenario_id": "SCN-001", "title": "Approve", "capability_refs": []any{"CAP-001"}, "obligation_refs": []any{"TO-001"}, "test_case_ids": []any{"TC-001"}, "coverage_ref": "COV-001"}},
			"test_cases":   []any{map[string]any{"test_case_id": "TC-001", "title": "Approve once", "kind": "review", "obligation_refs": []any{"TO-001"}, "capability_refs": []any{"CAP-001"}, "scenario_refs": []any{"SCN-001"}, "data_refs": []any{"TD-001"}, "coverage_refs": []any{"COV-001"}}},
		},
		"test-catalog.json": {
			"version": 1, "artifact": "test-catalog", "cases": []any{map[string]any{
				"test_case_id": "TC-001", "title": "Approve once", "objective": "Prove approval is idempotent", "status": "approved", "stage": "review", "priority": "p0",
				"risk_tags": []any{"state", "idempotency"}, "requirement_refs": []any{"REQ-001"}, "obligation_refs": []any{"TO-001"}, "capability_refs": []any{"CAP-001"}, "scenario_refs": []any{"SCN-001"}, "test_data_refs": []any{"TD-001"},
				"automation_target": "automated", "owner_stage": "review", "environment": []any{"local test runtime"}, "entrypoint_refs": []any{"cmd/review"},
				"preconditions": []any{"Queued order exists"}, "roles_permissions": []any{"reviewer can approve"}, "configuration": []any{"single approval worker"},
				"steps": []any{"Open approval", "Approve"}, "expected_results": []any{"Approval succeeds", "Second effect is suppressed"},
				"variants":      map[string]any{"positive": "covered", "negative": "covered", "boundary": "covered", "state": "covered", "permission": "covered", "concurrency": "covered", "timing": "covered", "recovery": "covered", "compatibility": "not_applicable"},
				"cleanup_reset": "Delete the synthetic order", "idempotency": "A repeated run starts from the same seed", "side_effect_boundary": "Only the synthetic order may change",
				"verification_method": "runtime-diagnostics", "pass_criteria": []any{"Order is approved exactly once"}, "evidence_requirements": []any{"runtime_diagnostics"},
				"freshness_rule": "Recapture after approval code changes", "invalidation_triggers": []any{"approval workflow changes"}, "flake_risks": []any{}, "residual_risk": "None within the frozen scope",
			}},
		},
		"test-data-manifest.json": {
			"version": 1, "artifact": "test-data-manifest", "datasets": []any{map[string]any{
				"test_data_id": "TD-001", "name": "Synthetic approval order", "kind": "synthetic", "sensitivity": "public", "contains_pii": false,
				"source": "generated", "disposition": "generate", "readiness": "ready", "provenance_refs": []any{},
				"format": "json", "volume": "one order", "constraints": []any{"queued state"}, "license": "project-internal synthetic", "usage_limits": "test only",
				"fixed_seed": "42", "distribution": "single deterministic row", "edge_partitions": []any{"already-approved"}, "checksum": "sha256:fixture-001",
				"allowed_usage": []any{"automated review tests"}, "snapshot_binding": "fixture-v1", "refresh_policy": "regenerate on schema change", "cleanup_reset": "delete order",
				"oracle_binding": "approval state oracle", "limitations": []any{}, "residual_risk": "synthetic data may miss production skew",
				"generation_recipe": "fixed seed 42 with one queued order", "applicable_test_case_ids": []any{"TC-001"}, "applicable_scenario_ids": []any{"SCN-001"},
				"hygiene": map[string]any{"classification_reason": "Synthetic only", "sanitization_status": "not_required", "retention_policy": "ephemeral"},
			}},
		},
		"coverage-matrix.json": {
			"version": 1, "artifact": "coverage-matrix", "rows": []any{map[string]any{
				"coverage_id": "COV-001", "requirement_ref": "REQ-001", "obligation_ref": "TO-001", "capability_ref": "CAP-001", "scenario_ref": "SCN-001", "test_case_ref": "TC-001",
				"test_data_refs": []any{"TD-001"}, "evidence_refs": evidenceRefs, "acceptance_refs": []any{"HA-001"}, "gap_refs": []any{}, "status": "covered",
			}},
		},
		"test-gaps.json": {"schema_version": "spec-kit-test-design-gaps-v1", "status": "clear", "gaps": []any{}},
	}
	for name, payload := range fixtures {
		if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, name), payload); err != nil {
			t.Fatal(err)
		}
	}
}

func registerTestDesignEvidence(t *testing.T, projectRoot, content string) string {
	t.Helper()
	env := (evidenceService{projectRoot: projectRoot}).registerContent(content, evidenceCommonInput{
		Scope: "test-design", Source: "runtime-test", Provenance: "test fixture", MIME: "application/json",
	})
	if env.Status != "ok" {
		t.Fatalf("register test-design evidence: %#v", env)
	}
	ref, _ := env.Data["record_ref"].(string)
	if !testDesignEvidenceRefPattern.MatchString(ref) {
		t.Fatalf("registered evidence ref = %q", ref)
	}
	return ref
}

func testDesignCoveredObligationResult(evidenceRef string) []any {
	return []any{map[string]any{
		"obligation_id": "TO-001", "status": "covered", "evidence_refs": []any{evidenceRef},
		"gap_refs": []any{}, "summary": "TO-001 is covered by verified evidence.",
	}}
}

func testDesignAuditChecks(evidenceRef string) []any {
	checks := make([]any, 0, len(testDesignAuditCoreCheckIDs))
	for _, checkID := range testDesignAuditCoreCheckIDs {
		checks = append(checks, map[string]any{
			"check_id": checkID, "status": "passed", "evidence_refs": []any{evidenceRef},
			"affected_obligation_refs": []any{"TO-001"}, "finding_refs": []any{},
			"summary": "Independent verified check passed.",
		})
	}
	return checks
}

func publishValidTestDesignHandoff(t *testing.T, projectRoot, featureRel string) string {
	t.Helper()
	featureDir := filepath.Join(projectRoot, filepath.FromSlash(featureRel))
	for _, dir := range []string{"src", "tests"} {
		if err := os.MkdirAll(filepath.Join(projectRoot, dir), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(projectRoot, "src", "approval.go"), []byte("package approval\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(featureDir, "spec.md"), []byte("REQ-001 approval\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	initInput := map[string]any{
		"query": "Design approval tests", "source_refs": []any{featureRel + "/spec.md"},
		"included_paths": []any{"src", "tests"}, "excluded_paths": []any{"vendor"},
		"risk_dimensions": []any{"functional", "state", "security"},
	}
	requireTestDesignOK(t, []string{"test-design", "init", "--scope", "feature", "--mode", "feature", "--feature-dir", featureRel, "--leader-id", "leader-1", "--input-json", mustTestDesignJSON(t, initInput), "--format", "json"})
	evidenceRef := registerTestDesignEvidence(t, projectRoot, "verified approval diagnostics")
	artifactRoot := filepath.Join(featureDir, "test-design")
	writeValidTestDesignWorkflowBundle(t, artifactRoot, evidenceRef)
	requireTestDesignOK(t, []string{"test-design", "universe-build", "--feature-dir", featureRel, "--format", "json"})
	lanes := map[string]any{"lanes": []any{map[string]any{
		"lane_id": "LANE-001", "kind": "discovery", "title": "Approval discovery", "obligation_ids": []any{"TO-001"},
		"read_paths": []any{"src", "tests", featureRel + "/spec.md"}, "questions": []any{"Prove the frozen obligation."},
	}}}
	requireTestDesignOK(t, []string{"test-design", "lane-prepare", "--feature-dir", featureRel, "--input-json", mustTestDesignJSON(t, lanes), "--format", "json"})
	lease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "worker-1", "--format", "json"})
	attemptID := lease.Data["attempt_id"].(string)
	result := map[string]any{
		"lane_id": "LANE-001", "attempt_id": attemptID, "status": "success",
		"inspected_paths": []any{"src", "tests", featureRel + "/spec.md"}, "evidence_refs": []any{evidenceRef},
		"obligation_results": testDesignCoveredObligationResult(evidenceRef), "checks": []any{},
		"candidate_cases":   []any{map[string]any{"test_case_id": "TC-001"}},
		"data_requirements": []any{map[string]any{"test_data_id": "TD-001"}},
		"contradictions":    []any{}, "unknowns": []any{}, "gaps": []any{}, "summary": "Discovery complete.",
	}
	requireTestDesignOK(t, []string{"test-design", "lane-checkpoint", "--feature-dir", featureRel, "--lane-id", "LANE-001", "--attempt-id", attemptID, "--result-json", mustTestDesignJSON(t, result), "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "lane-accept", "--feature-dir", featureRel, "--lane-id", "LANE-001", "--attempt-id", attemptID, "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "synthesize", "--feature-dir", featureRel, "--leader-id", "leader-1", "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "audit-prepare", "--feature-dir", featureRel, "--format", "json"})
	auditLease := requireTestDesignOK(t, []string{"test-design", "lane-lease", "--feature-dir", featureRel, "--worker-id", "auditor-1", "--format", "json"})
	auditLaneID := auditLease.Data["lane_id"].(string)
	auditAttemptID := auditLease.Data["attempt_id"].(string)
	auditPaths := []any{}
	for _, name := range []string{"test-universe.json", "test-catalog.json", "test-data-manifest.json", "coverage-matrix.json", "test-gaps.json"} {
		auditPaths = append(auditPaths, filepath.ToSlash(filepath.Join(featureRel, "test-design", name)))
	}
	auditResult := map[string]any{
		"lane_id": auditLaneID, "attempt_id": auditAttemptID, "status": "success",
		"inspected_paths": auditPaths, "evidence_refs": []any{evidenceRef},
		"obligation_results": testDesignCoveredObligationResult(evidenceRef), "checks": testDesignAuditChecks(evidenceRef),
		"candidate_cases": []any{}, "data_requirements": []any{}, "contradictions": []any{}, "unknowns": []any{}, "gaps": []any{}, "findings": []any{},
		"summary": "Independent audit complete.",
	}
	requireTestDesignOK(t, []string{"test-design", "lane-checkpoint", "--feature-dir", featureRel, "--lane-id", auditLaneID, "--attempt-id", auditAttemptID, "--result-json", mustTestDesignJSON(t, auditResult), "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "lane-accept", "--feature-dir", featureRel, "--lane-id", auditLaneID, "--attempt-id", auditAttemptID, "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "validate", "--feature-dir", featureRel, "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "handoff", "--feature-dir", featureRel, "--format", "json"})
	return evidenceRef
}

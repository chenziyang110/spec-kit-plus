package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
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
		"--feature-dir", featureRel, "--input-json", mustTestDesignJSON(t, initInput), "--format", "json",
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

	writeValidTestDesignWorkflowBundle(t, artifactRoot, "EVD-PLANNED-001")
	requireTestDesignOK(t, []string{"test-design", "universe-build", "--feature-dir", featureRel, "--format", "json"})

	lanes := map[string]any{"lanes": []any{map[string]any{
		"lane_id":        "LANE-001",
		"kind":           "discovery",
		"title":          "Approval behavior and risk scan",
		"obligation_ids": []any{"REQ-001"},
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
		"lane_id":           "LANE-001",
		"attempt_id":        attemptID,
		"status":            "success",
		"inspected_paths":   []any{"src", "tests", featureRel + "/spec.md"},
		"evidence_refs":     []any{"EVD-PLANNED-001"},
		"candidate_cases":   []any{map[string]any{"test_case_id": "TC-001", "summary": "Approval succeeds once"}},
		"data_requirements": []any{map[string]any{"test_data_id": "TD-001", "disposition": "generate"}},
		"contradictions":    []any{},
		"unknowns":          []any{},
		"gaps":              []any{},
		"summary":           "Approval lane complete.",
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
	requireTestDesignOK(t, []string{"test-design", "synthesize", "--feature-dir", featureRel, "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "audit-prepare", "--feature-dir", featureRel, "--format", "json"})
	auditLease := requireTestDesignOK(t, []string{
		"test-design", "lane-lease", "--feature-dir", featureRel,
		"--worker-id", "independent-auditor", "--format", "json",
	})
	auditLaneID, _ := auditLease.Data["lane_id"].(string)
	auditAttemptID, _ := auditLease.Data["attempt_id"].(string)
	auditResult := map[string]any{
		"lane_id":           auditLaneID,
		"attempt_id":        auditAttemptID,
		"status":            "success",
		"inspected_paths":   []any{filepath.ToSlash(filepath.Join(featureRel, "test-design"))},
		"evidence_refs":     []any{},
		"candidate_cases":   []any{},
		"data_requirements": []any{},
		"contradictions":    []any{},
		"unknowns":          []any{},
		"gaps":              []any{},
		"findings":          []any{},
		"summary":           "Independent audit found no unresolved omission.",
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
		"--input-json", mustTestDesignJSON(t, input), "--format", "json",
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
	if err := os.WriteFile(filepath.Join(projectRoot, filepath.FromSlash(featureRel), "spec.md"), []byte("REQ-001\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	withTestDesignCWD(t, projectRoot)

	input := map[string]any{
		"query": "scope", "source_refs": []any{featureRel + "/spec.md"},
		"included_paths": []any{"src"}, "excluded_paths": []any{}, "risk_dimensions": []any{"functional"},
	}
	requireTestDesignOK(t, []string{"test-design", "init", "--scope", "feature", "--mode", "feature", "--feature-dir", featureRel, "--input-json", mustTestDesignJSON(t, input), "--format", "json"})
	writeValidTestDesignWorkflowBundle(t, filepath.Join(projectRoot, filepath.FromSlash(featureRel), "test-design"), "EVD-PLANNED-001")
	requireTestDesignOK(t, []string{"test-design", "universe-build", "--feature-dir", featureRel, "--format", "json"})
	requireTestDesignOK(t, []string{"test-design", "lane-prepare", "--feature-dir", featureRel, "--input-json", mustTestDesignJSON(t, map[string]any{"lanes": []any{map[string]any{
		"lane_id": "LANE-001", "kind": "discovery", "title": "bounded", "obligation_ids": []any{"REQ-001"}, "read_paths": []any{"src"}, "questions": []any{"inspect"},
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
	fixtures := map[string]map[string]any{
		"test-universe.json": {
			"version": 1, "artifact": "test-universe", "feature_ref": "specs/001-test-design",
			"capabilities": []any{map[string]any{"capability_id": "CAP-001", "title": "Approval", "requirement_refs": []any{"REQ-001"}, "test_case_ids": []any{"TC-001"}, "scenario_ids": []any{"SCN-001"}}},
			"scenarios": []any{map[string]any{"scenario_id": "SCN-001", "title": "Approve", "capability_refs": []any{"CAP-001"}, "test_case_ids": []any{"TC-001"}, "coverage_ref": "COV-001"}},
			"test_cases": []any{map[string]any{"test_case_id": "TC-001", "title": "Approve once", "kind": "review", "capability_refs": []any{"CAP-001"}, "scenario_refs": []any{"SCN-001"}, "data_refs": []any{"TD-001"}, "coverage_refs": []any{"COV-001"}}},
		},
		"test-catalog.json": {
			"version": 1, "artifact": "test-catalog", "cases": []any{map[string]any{
				"test_case_id": "TC-001", "title": "Approve once", "objective": "Prove approval is idempotent", "stage": "review", "priority": "p0",
				"requirement_refs": []any{"REQ-001"}, "capability_refs": []any{"CAP-001"}, "scenario_refs": []any{"SCN-001"}, "test_data_refs": []any{"TD-001"},
				"verification_method": "runtime-diagnostics", "preconditions": []any{"Queued order exists"}, "steps": []any{"Open approval", "Approve"},
				"pass_criteria": []any{"Order is approved exactly once"}, "evidence_requirements": []any{"runtime_diagnostics"},
			}},
		},
		"test-data-manifest.json": {
			"version": 1, "artifact": "test-data-manifest", "datasets": []any{map[string]any{
				"test_data_id": "TD-001", "name": "Synthetic approval order", "kind": "synthetic", "sensitivity": "public", "contains_pii": false,
				"source": "generated", "disposition": "generate", "readiness": "recipe-ready", "provenance_refs": []any{},
				"generation_recipe": "fixed seed 42 with one queued order", "applicable_test_case_ids": []any{"TC-001"}, "applicable_scenario_ids": []any{"SCN-001"},
				"hygiene": map[string]any{"classification_reason": "Synthetic only", "sanitization_status": "not_required", "retention_policy": "ephemeral"},
			}},
		},
		"coverage-matrix.json": {
			"version": 1, "artifact": "coverage-matrix", "rows": []any{map[string]any{
				"coverage_id": "COV-001", "requirement_ref": "REQ-001", "capability_ref": "CAP-001", "scenario_ref": "SCN-001", "test_case_ref": "TC-001",
				"test_data_refs": []any{"TD-001"}, "evidence_refs": []any{evidenceRef}, "acceptance_refs": []any{"HA-001"}, "status": "covered",
			}},
		},
	}
	for name, payload := range fixtures {
		if err := writeTestDesignJSONFixture(filepath.Join(artifactRoot, name), payload); err != nil {
			t.Fatal(err)
		}
	}
}


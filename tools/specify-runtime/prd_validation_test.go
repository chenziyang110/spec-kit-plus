package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestValidatePRDStageArtifactsAcceptsReadyForBuildScanPackage(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-prd-run"
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command:        "sp-prd-scan",
		status:         "ready-for-build",
		scanStatus:     "complete",
		buildStatus:    "pending",
		classification: "service",
		nextCommand:    "/sp.prd-build",
		freshness:      "fresh",
		latestRun:      runID,
		includeBuild:   false,
	})

	if err := validatePRDStageArtifacts(projectRoot, runDir, "prd-scan"); err != nil {
		t.Fatalf("validatePRDStageArtifacts(prd-scan) error = %v", err)
	}
}

func TestValidatePRDStageArtifactsRejectsLiveSourceDrift(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-prd-stale"
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command:        "sp-prd-scan",
		status:         "ready-for-build",
		scanStatus:     "complete",
		buildStatus:    "pending",
		classification: "service",
		nextCommand:    "/sp.prd-build",
		freshness:      "fresh",
		latestRun:      runID,
	})
	prdWriteTestFile(t, projectRoot, filepath.Join("src", "app.go"), "package app\n")

	err := validatePRDStageArtifacts(projectRoot, runDir, "prd-scan")
	if err == nil || !strings.Contains(err.Error(), "full-stale") {
		t.Fatalf("validatePRDStageArtifacts stale error = %v, want live freshness blocker", err)
	}
}

func TestValidatePRDStageArtifactsAcceptsCompletedBuildBundle(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-prd-build"
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command:        "sp-prd-build",
		status:         "complete",
		scanStatus:     "complete",
		buildStatus:    "complete",
		classification: "mixed",
		nextCommand:    "none",
		freshness:      "fresh",
		latestRun:      runID,
		includeBuild:   true,
	})

	if err := validatePRDStageArtifacts(projectRoot, runDir, "prd-build"); err != nil {
		t.Fatalf("validatePRDStageArtifacts(prd-build) error = %v", err)
	}
}

func TestValidatePRDStageArtifactsRejectsStatusLatestRunMismatch(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-prd-mismatch"
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command:        "sp-prd-scan",
		status:         "ready-for-build",
		scanStatus:     "complete",
		buildStatus:    "pending",
		classification: "service",
		nextCommand:    "/sp.prd-build",
		freshness:      "fresh",
		latestRun:      "260729-other-run",
		includeBuild:   false,
	})

	err := validatePRDStageArtifacts(projectRoot, runDir, "prd-scan")
	if err == nil || !strings.Contains(err.Error(), "latest_run") {
		t.Fatalf("validatePRDStageArtifacts mismatch error = %v, want latest_run blocker", err)
	}
}

func TestValidatePRDStageArtifactsRejectsBuildWithoutCompletedScanState(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-prd-forged-build"
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command:        "sp-prd-build",
		status:         "complete",
		scanStatus:     "pending",
		buildStatus:    "complete",
		classification: "service",
		nextCommand:    "none",
		freshness:      "fresh",
		latestRun:      runID,
		includeBuild:   true,
	})

	err := validatePRDStageArtifacts(projectRoot, runDir, "prd-build")
	if err == nil || !strings.Contains(err.Error(), "scan_status") {
		t.Fatalf("validatePRDStageArtifacts forged build error = %v, want scan_status blocker", err)
	}
}

func TestValidatePRDStageArtifactsRejectsMalformedScanContractJSON(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-prd-bad-json"
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command:        "sp-prd-scan",
		status:         "ready-for-build",
		scanStatus:     "complete",
		buildStatus:    "pending",
		classification: "service",
		nextCommand:    "/sp.prd-build",
		freshness:      "fresh",
		latestRun:      runID,
		includeBuild:   false,
	})
	prdWriteTestFile(t, runDir, "capability-ledger.json", `{"wrong":[]}`+"\n")

	err := validatePRDStageArtifacts(projectRoot, runDir, "prd-scan")
	if err == nil || !strings.Contains(err.Error(), "capability-ledger.json") {
		t.Fatalf("validatePRDStageArtifacts malformed json error = %v, want capability-ledger.json blocker", err)
	}
}

func TestValidatePRDStageArtifactsRejectsShallowReadyScanPackage(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-prd-shallow"
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command:        "sp-prd-scan",
		status:         "ready-for-build",
		scanStatus:     "complete",
		buildStatus:    "pending",
		classification: "service",
		nextCommand:    "/sp.prd-build",
		freshness:      "fresh",
		latestRun:      runID,
	})
	prdWriteTestFile(t, runDir, "capability-ledger.json", `{"capabilities":[]}`+"\n")

	err := validatePRDStageArtifacts(projectRoot, runDir, "prd-scan")
	if err == nil || !strings.Contains(err.Error(), "critical capability") {
		t.Fatalf("validatePRDStageArtifacts shallow package error = %v, want critical capability blocker", err)
	}
}

func TestValidatePRDStageArtifactsRejectsNoncanonicalWorkerResult(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-prd-worker"
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command:        "sp-prd-scan",
		status:         "ready-for-build",
		scanStatus:     "complete",
		buildStatus:    "pending",
		classification: "service",
		nextCommand:    "/sp.prd-build",
		freshness:      "fresh",
		latestRun:      runID,
	})
	prdWriteTestFile(t, runDir, filepath.Join("worker-results", "lane-001.json"), `{"lane_id":"lane-001","reported_status":"done","paths_read":["src/app.go"],"recommended_ledger_updates":[]}`+"\n")

	err := validatePRDStageArtifacts(projectRoot, runDir, "prd-scan")
	if err == nil || !strings.Contains(err.Error(), "confidence") {
		t.Fatalf("validatePRDStageArtifacts worker result error = %v, want canonical field blocker", err)
	}
}

func TestValidatePRDStageArtifactsRejectsCompatibilityReadyWithoutBuildHandoff(t *testing.T) {
	projectRoot := t.TempDir()
	runID := "260729-prd-compat"
	runDir := seedPRDRunFixture(t, projectRoot, runID, prdFixtureOptions{
		command:        "sp-prd",
		status:         "ready-for-build",
		scanStatus:     "complete",
		buildStatus:    "pending",
		classification: "ui",
		nextCommand:    "none",
		freshness:      "fresh",
		latestRun:      runID,
		includeBuild:   false,
	})

	err := validatePRDStageArtifacts(projectRoot, runDir, "prd")
	if err == nil || !strings.Contains(err.Error(), "next_command") {
		t.Fatalf("validatePRDStageArtifacts compatibility error = %v, want next_command blocker", err)
	}
}

type prdFixtureOptions struct {
	command        string
	status         string
	scanStatus     string
	buildStatus    string
	classification string
	nextCommand    string
	freshness      string
	latestRun      string
	includeBuild   bool
}

func seedPRDRunFixture(t *testing.T, projectRoot string, runID string, opts prdFixtureOptions) string {
	t.Helper()
	runDir := filepath.Join(projectRoot, ".specify", "prd-runs", runID)
	for _, dirname := range []string{"evidence", "scan-packets", "worker-results", "master", "exports"} {
		path := filepath.Join(runDir, dirname)
		if err := os.MkdirAll(path, 0o755); err != nil {
			t.Fatalf("mkdir %s: %v", path, err)
		}
	}
	prdWriteTestFile(t, runDir, "workflow-state.md", prdWorkflowStateFixture(runID, opts))
	prdWriteTestFile(t, runDir, "prd-scan.md", "# PRD Scan\n\n## Reconstruction Summary\n\n- Status: complete\n")
	prdWriteTestFile(t, runDir, "coverage-ledger.md", "# Coverage Ledger\n\n| Surface | Status | Evidence | Notes |\n| --- | --- | --- | --- |\n| Runtime | complete | EVD-001 | Ready |\n")
	prdWriteTestFile(t, runDir, filepath.Join("scan-packets", "lane-001.md"), "# Packet\n\n- lane_id: lane-001\n")
	prdWriteTestFile(t, runDir, filepath.Join("worker-results", "lane-001.json"), `{"lane_id":"lane-001","reported_status":"done","paths_read":["src/app.go"],"key_facts":["entrypoint observed"],"evidence_refs":["evidence/EVD-001.json"],"recommended_contract_updates":[],"confidence":"high","unknowns":[],"minimum_verification":["inspect entrypoint"],"result_handoff_path":"worker-results/lane-001.json"}`+"\n")
	prdWriteTestFile(t, runDir, filepath.Join("evidence", "EVD-001.json"), `{"id":"EVD-001","kind":"repository"}`+"\n")

	for relative, payload := range map[string]map[string]any{
		"coverage-ledger.json":          {"version": 1, "rows": []any{map[string]any{"id": "COV-001", "status": "covered", "evidence": []any{"EVD-001"}}}},
		"capability-ledger.json":        {"capabilities": []any{map[string]any{"id": "CAP-001", "tier": "critical", "status": "reconstruction-ready"}}},
		"artifact-contracts.json":       {"artifacts": []any{map[string]any{"id": "ART-001", "status": "complete"}}},
		"reconstruction-checklist.json": {"checks": []any{map[string]any{"id": "CHK-001", "status": "passed"}}},
		"entrypoint-ledger.json":        {"entrypoints": []any{}},
		"config-contracts.json":         {"configs": []any{}},
		"protocol-contracts.json":       {"protocols": []any{}},
		"state-machines.json":           {"machines": []any{}},
		"error-semantics.json":          {"errors": []any{}},
		"verification-surfaces.json":    {"surfaces": []any{}},
	} {
		prdWriteTestFile(t, runDir, relative, mustJSON(t, payload))
	}

	if opts.includeBuild {
		for relative, content := range map[string]string{
			filepath.Join("master", "master-pack.md"):              "# Master Pack\n\nCanonical reconstruction package.\n",
			filepath.Join("exports", "README.md"):                  "# README\n\nUse the linked reconstruction exports.\n",
			filepath.Join("exports", "prd.md"):                     "# PRD\n\n## Capability Overview\n\nCore capability.\n\n## Critical Capability Notes\n\nCritical path is evidence-bound.\n\n## Unknowns and Evidence Confidence\n\nNo critical unknowns remain.\n",
			filepath.Join("exports", "reconstruction-appendix.md"): "# Reconstruction Appendix\n\nEvidence mapping.\n",
			filepath.Join("exports", "data-model.md"):              "# Data Model\n\nCanonical entities.\n",
			filepath.Join("exports", "integration-contracts.md"):   "# Integration Contracts\n\nEntrypoint contract.\n",
			filepath.Join("exports", "runtime-behaviors.md"):       "# Runtime Behaviors\n\nObserved runtime behavior.\n",
			filepath.Join("exports", "config-contracts.md"):        "# Config Contracts\n\nConfiguration contract.\n",
			filepath.Join("exports", "protocol-contracts.md"):      "# Protocol Contracts\n\nProtocol contract.\n",
			filepath.Join("exports", "state-machines.md"):          "# State Machines\n\nLifecycle states.\n",
			filepath.Join("exports", "error-semantics.md"):         "# Error Semantics\n\nFailure behavior.\n",
			filepath.Join("exports", "verification-surface.md"):    "# Verification Surface\n\nVerification commands.\n",
			filepath.Join("exports", "reconstruction-risks.md"):    "# Reconstruction Risks\n\nResidual risk is documented.\n",
		} {
			prdWriteTestFile(t, runDir, relative, content)
		}
	}

	snapshot, err := currentPRDGitSnapshot(projectRoot)
	if err != nil {
		t.Fatalf("currentPRDGitSnapshot: %v", err)
	}
	statusPath := filepath.Join(projectRoot, ".specify", "prd", "status.json")
	prdWriteTestFile(t, filepath.Dir(statusPath), filepath.Base(statusPath), mustJSON(t, map[string]any{
		"version":                          1,
		"status_family":                    "prd",
		"freshness":                        opts.freshness,
		"last_refresh_commit":              snapshot.commit,
		"last_refresh_branch":              snapshot.branch,
		"last_refresh_at":                  "2026-07-29T00:00:00Z",
		"last_refresh_scope":               "full",
		"last_refresh_basis":               snapshot.basis,
		"last_refresh_changed_files_basis": stringSliceToAny(snapshot.changedFiles),
		"manual_force_stale":               false,
		"manual_force_stale_reasons":       []any{},
		"latest_run":                       opts.latestRun,
	}))

	return runDir
}

func prdWorkflowStateFixture(runID string, opts prdFixtureOptions) string {
	lines := []string{
		"---",
		"id: \"" + runID + "\"",
		"slug: \"demo\"",
		"status: \"initialized\"",
		"created_at: \"2026-07-29T00:00:00Z\"",
		"---",
		"# PRD Workflow State",
		"",
		"## Current Command",
		"",
		"- active_command: `" + opts.command + "`",
		"- status: `" + opts.status + "`",
		"",
		"## Phase Mode",
		"",
		"- phase_mode: `analysis-only`",
		"- classification: `" + opts.classification + "`",
		"- scan_status: `" + opts.scanStatus + "`",
		"- build_status: `" + opts.buildStatus + "`",
		"- failed_readiness_checks: `none`",
		"- failed_reverse_coverage_checks: `none`",
		"- next_action: `validate bundle`",
		"",
		"## Allowed Artifact Writes",
		"",
		"- `.specify/prd-runs/" + runID + "/workflow-state.md`",
		"- `.specify/prd-runs/" + runID + "/prd-scan.md`",
		"",
		"## Forbidden Actions",
		"",
		"- edit source code",
		"- implement product changes",
		"",
		"## Authoritative Files",
		"",
		"- `.specify/prd-runs/" + runID + "/workflow-state.md`",
		"- `.specify/prd-runs/" + runID + "/coverage-ledger.json`",
		"",
		"## Next Command",
		"",
		"- `" + opts.nextCommand + "`",
		"",
	}
	return strings.Join(lines, "\n")
}

func mustJSON(t *testing.T, payload map[string]any) string {
	t.Helper()
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatalf("marshal json: %v", err)
	}
	return string(raw) + "\n"
}

func prdWriteTestFile(t *testing.T, root, relative, content string) {
	t.Helper()
	path := filepath.Join(root, relative)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("create parent for %s: %v", relative, err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", relative, err)
	}
}

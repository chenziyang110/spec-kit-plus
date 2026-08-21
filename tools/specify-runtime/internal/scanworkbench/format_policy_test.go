package scanworkbench

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestConfirmedFormatPolicyControlsScanBoundary(t *testing.T) {
	files := []string{
		"backend/main.go",
		"docs/guide.md",
		"data/export.csv",
		"domain/model.flowdsl",
	}
	paths := newScanPaths(t, files)

	inventory, err := InventoryFormats(paths, FormatInventoryInput{})
	if err != nil {
		t.Fatalf("InventoryFormats returned error: %v", err)
	}
	if inventory.Status != "ready_for_agent_policy" || inventory.PathCount != 4 || inventory.CohortCount != 4 {
		t.Fatalf("format inventory payload = %#v", inventory)
	}

	decisions := []FormatPolicyDecisionGroup{
		{CohortIDs: []string{cohortIDForFormat(t, inventory.Cohorts, "go")}, Decision: "semantic_scan", Reason: "application code"},
		{CohortIDs: []string{cohortIDForFormat(t, inventory.Cohorts, "markdown")}, Decision: "exclude", Reason: "not needed for the code baseline"},
		{CohortIDs: []string{cohortIDForFormat(t, inventory.Cohorts, "csv")}, Decision: "inventory_only", Reason: "runtime data"},
		{CohortIDs: []string{cohortIDForFormat(t, inventory.Cohorts, "unknown")}, Decision: "sample", Reason: "custom format needs bounded semantic inspection"},
	}
	staged, err := StageFormatPolicy(paths, StageFormatPolicyInput{
		Protocol:        formatPolicyProposalProtocolV1,
		InventoryDigest: inventory.InventoryDigest,
		DecisionGroups:  decisions,
	})
	if err != nil {
		t.Fatalf("StageFormatPolicy returned error: %v", err)
	}
	if staged.Status != "staged" || !staged.ReviewRequired || !staged.ConfirmationAllowed || staged.ProposalDigest == "" {
		t.Fatalf("staged format policy = %#v", staged)
	}

	if _, err := Prepare(paths, PrepareInput{RequireConfirmedPolicy: true}); err == nil || !strings.Contains(err.Error(), "confirmed scan policy") {
		t.Fatalf("Prepare before confirmation error = %v", err)
	}
	if _, err := ConfirmFormatPolicy(paths, ConfirmFormatPolicyInput{ProposalDigest: "wrong"}); err == nil || !strings.Contains(err.Error(), "proposal digest") {
		t.Fatalf("ConfirmFormatPolicy with wrong digest error = %v", err)
	}
	confirmed, err := ConfirmFormatPolicy(paths, ConfirmFormatPolicyInput{ProposalDigest: staged.ProposalDigest})
	if err != nil {
		t.Fatalf("ConfirmFormatPolicy returned error: %v", err)
	}
	if confirmed.Status != "confirmed" || confirmed.PolicyDigest == "" || confirmed.NextAction != "run_scan_prepare" {
		t.Fatalf("confirmed format policy = %#v", confirmed)
	}

	prepared, err := Prepare(paths, PrepareInput{RequireConfirmedPolicy: true, PacketSize: len(files)})
	if err != nil {
		t.Fatalf("Prepare with confirmed policy returned error: %v", err)
	}
	if prepared.PolicyDigest != confirmed.PolicyDigest {
		t.Fatalf("Prepare policy digest = %q, want %q", prepared.PolicyDigest, confirmed.PolicyDigest)
	}

	universe := readJSONObject(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"))
	rows := rowsByPath(t, universe["candidate_universe"])
	expectations := map[string]struct {
		decision    string
		disposition string
		agentAssist string
	}{
		"backend/main.go":      {"scan", "deep_read", "semantic_scan"},
		"docs/guide.md":        {"exclude", "excluded", "none"},
		"data/export.csv":      {"inventory_only", "inventory_only", "none"},
		"domain/model.flowdsl": {"sample", "sampled", "semantic_scan"},
	}
	for path, expectation := range expectations {
		row := rows[path]
		if row["scan_decision"] != expectation.decision || row["disposition"] != expectation.disposition || row["agent_assist"] != expectation.agentAssist {
			t.Fatalf("confirmed policy row %s = %#v", path, row)
		}
		if row["policy_decision"] == "" || row["cohort_id"] == "" {
			t.Fatalf("confirmed policy metadata missing for %s: %#v", path, row)
		}
	}
	if universe["policy_digest"] != confirmed.PolicyDigest {
		t.Fatalf("repository universe policy_digest = %v, want %s", universe["policy_digest"], confirmed.PolicyDigest)
	}
}

func TestInventoryFormatsGroupsRepositoryCohortsAndCapsRepresentatives(t *testing.T) {
	files := []string{
		"domain/a.flowdsl",
		"domain/b.flowdsl",
		"domain/c.flowdsl",
		"domain/d.flowdsl",
		"domain/e.flowdsl",
		"other/a.flowdsl",
		"config/app.json",
		"data/app.json",
	}
	paths := newScanPaths(t, files)

	inventory, err := InventoryFormats(paths, FormatInventoryInput{})
	if err != nil {
		t.Fatalf("InventoryFormats returned error: %v", err)
	}
	domain := cohortFor(t, inventory.Cohorts, func(cohort FormatCohort) bool {
		return cohort.FormatKey == "extension:.flowdsl" && cohort.DirectoryFamily == "domain"
	})
	if domain.PathCount != 5 || len(domain.RepresentativePaths) != 3 {
		t.Fatalf("domain custom-format cohort = %#v", domain)
	}
	other := cohortFor(t, inventory.Cohorts, func(cohort FormatCohort) bool {
		return cohort.FormatKey == "extension:.flowdsl" && cohort.DirectoryFamily == "other"
	})
	if other.PathCount != 1 || domain.CohortID == other.CohortID {
		t.Fatalf("directory-specific format cohorts: domain=%#v other=%#v", domain, other)
	}
	configJSON := cohortFor(t, inventory.Cohorts, func(cohort FormatCohort) bool {
		return cohort.FileFormat == "json" && cohort.DirectoryFamily == "config"
	})
	dataJSON := cohortFor(t, inventory.Cohorts, func(cohort FormatCohort) bool {
		return cohort.FileFormat == "json" && cohort.DirectoryFamily == "data"
	})
	if configJSON.FormatFamily != "config" || dataJSON.FormatFamily != "data" || configJSON.CohortID == dataJSON.CohortID {
		t.Fatalf("JSON cohorts were not split by role: config=%#v data=%#v", configJSON, dataJSON)
	}
}

func TestStageFormatPolicyRequiresExactCohortCoverage(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go", "docs/guide.md"})
	inventory, err := InventoryFormats(paths, FormatInventoryInput{})
	if err != nil {
		t.Fatal(err)
	}
	first := inventory.Cohorts[0].CohortID
	second := inventory.Cohorts[1].CohortID

	tests := []struct {
		name   string
		groups []FormatPolicyDecisionGroup
		want   string
	}{
		{
			name:   "missing cohort",
			groups: []FormatPolicyDecisionGroup{{CohortIDs: []string{first}, Decision: "semantic_scan", Reason: "code"}},
			want:   "missing cohort",
		},
		{
			name: "duplicate cohort",
			groups: []FormatPolicyDecisionGroup{
				{CohortIDs: []string{first, second}, Decision: "semantic_scan", Reason: "first"},
				{CohortIDs: []string{first}, Decision: "sample", Reason: "duplicate"},
			},
			want: "duplicate cohort",
		},
		{
			name: "unknown cohort",
			groups: []FormatPolicyDecisionGroup{
				{CohortIDs: []string{first}, Decision: "semantic_scan", Reason: "code"},
				{CohortIDs: []string{"fmt-does-not-exist"}, Decision: "sample", Reason: "unknown"},
			},
			want: "unknown cohort",
		},
		{
			name: "empty reason",
			groups: []FormatPolicyDecisionGroup{
				{CohortIDs: []string{first}, Decision: "semantic_scan", Reason: ""},
				{CohortIDs: []string{second}, Decision: "sample", Reason: "docs"},
			},
			want: "reason",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := StageFormatPolicy(paths, StageFormatPolicyInput{
				Protocol:        formatPolicyProposalProtocolV1,
				InventoryDigest: inventory.InventoryDigest,
				DecisionGroups:  tt.groups,
			})
			if err == nil || !strings.Contains(err.Error(), tt.want) {
				t.Fatalf("StageFormatPolicy error = %v, want %q", err, tt.want)
			}
		})
	}
}

func TestConfirmedFormatPolicyReusesKnownCohortAndRejectsNewCohort(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go"})
	inventory, err := InventoryFormats(paths, FormatInventoryInput{})
	if err != nil {
		t.Fatal(err)
	}
	staged, err := StageFormatPolicy(paths, StageFormatPolicyInput{
		Protocol:        formatPolicyProposalProtocolV1,
		InventoryDigest: inventory.InventoryDigest,
		DecisionGroups: []FormatPolicyDecisionGroup{{
			CohortIDs: []string{inventory.Cohorts[0].CohortID},
			Decision:  "semantic_scan",
			Reason:    "application code",
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ConfirmFormatPolicy(paths, ConfirmFormatPolicyInput{ProposalDigest: staged.ProposalDigest}); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(paths.Root, "src", "app.go"), []byte("package fixture\n\nfunc main() {}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	prepared, err := Prepare(paths, PrepareInput{RequireConfirmedPolicy: true})
	if err != nil {
		t.Fatalf("Prepare after same-cohort content drift returned error: %v", err)
	}
	if prepared.PolicyDigest == "" {
		t.Fatalf("Prepare after same-cohort content drift lost policy binding: %#v", prepared)
	}

	pythonPath := filepath.Join(paths.Root, "src", "tool.py")
	if err := os.WriteFile(pythonPath, []byte("print('new cohort')\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeJSON(t, filepath.Join(paths.RuntimeDir, "tmp", "scan-files.json"), map[string]any{
		"files": []string{"src/app.go", "src/tool.py"},
	})
	if _, err := Prepare(paths, PrepareInput{RequireConfirmedPolicy: true}); err == nil || !strings.Contains(err.Error(), "new format cohorts") {
		t.Fatalf("Prepare with unconfirmed new cohort error = %v", err)
	}
}

func TestConfirmFormatPolicyRejectsTamperedStagedProposal(t *testing.T) {
	paths := newScanPaths(t, []string{"src/app.go", "docs/guide.md"})
	inventory, err := InventoryFormats(paths, FormatInventoryInput{})
	if err != nil {
		t.Fatal(err)
	}
	staged, err := StageFormatPolicy(paths, StageFormatPolicyInput{
		Protocol:        formatPolicyProposalProtocolV1,
		InventoryDigest: inventory.InventoryDigest,
		DecisionGroups: []FormatPolicyDecisionGroup{
			{CohortIDs: []string{cohortIDForFormat(t, inventory.Cohorts, "go")}, Decision: "semantic_scan", Reason: "application code"},
			{CohortIDs: []string{cohortIDForFormat(t, inventory.Cohorts, "markdown")}, Decision: "sample", Reason: "behavioral documentation"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	proposalPath := formatPolicyProposalPath(paths)
	proposal := readJSONObject(t, proposalPath)
	groups := objectRows(t, proposal["decision_groups"])
	groups[0]["decision"] = "exclude"
	proposal["decision_groups"] = groups
	writeJSON(t, proposalPath, proposal)

	if _, err := ConfirmFormatPolicy(paths, ConfirmFormatPolicyInput{ProposalDigest: staged.ProposalDigest}); err == nil || !strings.Contains(err.Error(), "digest does not match") {
		t.Fatalf("ConfirmFormatPolicy tampered proposal error = %v", err)
	}
}

func cohortIDForFormat(t *testing.T, cohorts []FormatCohort, format string) string {
	t.Helper()
	return cohortFor(t, cohorts, func(cohort FormatCohort) bool {
		return cohort.FileFormat == format
	}).CohortID
}

func cohortFor(t *testing.T, cohorts []FormatCohort, match func(FormatCohort) bool) FormatCohort {
	t.Helper()
	for _, cohort := range cohorts {
		if match(cohort) {
			return cohort
		}
	}
	t.Fatalf("format cohort not found in %#v", cohorts)
	return FormatCohort{}
}

package store

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
)

func TestScopeProofMaterialReadsEveryCurrentClaimBeyondNavigationHeads(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	input := validImportInput("GEN-scope-proof")
	for i := 0; i < 30; i++ {
		input.Claims = append(input.Claims, ClaimImport{ID: fmt.Sprintf("claim:%02d", i), NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "scope", State: claim.StateSupported, Freshness: claim.FreshnessFresh, SupportingEvidenceIDs: []string{"E-001"}})
	}
	if _, err := st.ImportGeneration(context.Background(), input); err != nil {
		t.Fatal(err)
	}
	material, err := st.ScopeProofMaterialForNodeIDs(context.Background(), []string{"N-app"})
	if err != nil {
		t.Fatal(err)
	}
	count := 0
	for _, row := range material.Evidence {
		if row.OwnerKind == "claim" {
			count++
		}
	}
	if count != 30 || len(material.IncompleteReasons) != 0 {
		t.Fatalf("complete claim proof=%#v count=%d", material, count)
	}
	if _, err := st.DB().Exec(`UPDATE claims SET state='stale',freshness='stale' WHERE id='claim:29'`); err != nil {
		t.Fatal(err)
	}
	material, err = st.ScopeProofMaterialForNodeIDs(context.Background(), []string{"N-app"})
	if err != nil || !strings.Contains(strings.Join(material.IncompleteReasons, ","), "claim_lifecycle_requires_live_verification") {
		t.Fatalf("late stale claim omitted: %#v err=%v", material, err)
	}
}

func TestScopeProofMaterialDisclosesMissingWeakAndContradictingSupport(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	input := validImportInput("GEN-scope-support")
	input.Claims = []ClaimImport{{ID: "claim:app", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "scope", State: claim.StateSupported, Freshness: claim.FreshnessFresh, SupportingEvidenceIDs: []string{"E-001"}}}
	input.Edges = []EdgeImport{{ID: "edge:app", Type: "depends_on", SourceID: "N-app", TargetID: "N-app", Confidence: "weak"}}
	if _, err := st.ImportGeneration(context.Background(), input); err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().Exec(`UPDATE claim_evidence SET role='contradicting' WHERE claim_id='claim:app'`); err != nil {
		t.Fatal(err)
	}
	material, err := st.ScopeProofMaterialForNodeIDs(context.Background(), []string{"N-app", "N-missing"})
	if err != nil {
		t.Fatal(err)
	}
	joined := strings.Join(material.IncompleteReasons, ",")
	for _, reason := range []string{"node_missing:N-missing", "edge_support_weak:edge:app", "edge_evidence_incomplete:edge:app", "claim_support_uncertain:claim:app"} {
		if !strings.Contains(joined, reason) {
			t.Fatalf("missing conservative reason %s in %#v", reason, material)
		}
	}
	owners, err := st.ScopeOwners(context.Background())
	if err != nil || len(owners) != 1 || owners[0].ContentHash != "hash-app" {
		t.Fatalf("owner source basis=%#v err=%v", owners, err)
	}
}

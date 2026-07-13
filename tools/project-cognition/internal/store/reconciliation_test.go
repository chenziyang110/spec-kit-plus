package store

import (
	"context"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
)

func TestApplyClaimReconciliationAtomicallyReplacesCurrentBasis(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-reconcile")
	input.Claims = []ClaimImport{{
		ID: "claim:app-owner", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns runtime behavior",
		State: claim.StateStale, PriorState: claim.StateSupported, Freshness: claim.FreshnessStale, StateReason: "changed_path:src/app.go",
		SupportingEvidenceIDs: []string{"E-001"},
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	result, err := st.ApplyClaimReconciliation(ctx, ClaimReconciliationBatch{
		ID: "claim-reconciliation:packet-1", PacketHash: "packet-1", GenerationID: "GEN-reconcile",
		Workflow: "sp-implement", ObservedAt: "2026-07-13T10:00:00Z", CommitSHA: "abc123",
		Items: []ClaimReconciliationItem{{
			ClaimID: "claim:app-owner", ExpectedState: claim.StateStale, Reason: "live_source_and_test_confirm_owner",
			Evidence: []ClaimReconciliationEvidence{{
				ID: "E-reconcile-1", SourceKind: "source", SourcePath: "src/app.go", Span: "L1-L20",
				ContentHash: "sha256:current", Role: "supporting",
			}},
			Verification: &ClaimReconciliationVerification{ID: "V-reconcile-1", Result: claim.VerificationPassed, Command: "go test ./src/..."},
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if result.Replayed || result.ResultState != "ready" || len(result.Claims) != 1 {
		t.Fatalf("result = %#v, want one newly reconciled claim", result)
	}
	record := result.Claims[0]
	if record.FromState != claim.StateStale || record.ToState != claim.StateVerified || record.TransitionID == "" {
		t.Fatalf("record = %#v, want stale -> verified with transition", record)
	}

	var state, freshness string
	if err := st.DB().QueryRowContext(ctx, `SELECT state, freshness FROM claims WHERE id = ?`, "claim:app-owner").Scan(&state, &freshness); err != nil {
		t.Fatal(err)
	}
	if state != string(claim.StateVerified) || freshness != string(claim.FreshnessFresh) {
		t.Fatalf("claim = %q/%q, want verified/fresh", state, freshness)
	}
	var oldBasis, newBasis string
	if err := st.DB().QueryRowContext(ctx, `SELECT basis_state FROM claim_evidence WHERE claim_id = ? AND evidence_id = ?`, "claim:app-owner", "E-001").Scan(&oldBasis); err != nil {
		t.Fatal(err)
	}
	if err := st.DB().QueryRowContext(ctx, `SELECT basis_state FROM claim_evidence WHERE claim_id = ? AND evidence_id = ?`, "claim:app-owner", "E-reconcile-1").Scan(&newBasis); err != nil {
		t.Fatal(err)
	}
	if oldBasis != "superseded" || newBasis != "current" {
		t.Fatalf("basis states = %q/%q, want superseded/current", oldBasis, newBasis)
	}
	for table, want := range map[string]int{"evidence": 2, "claim_verifications": 1, "claim_transitions": 2, "claim_reconciliations": 1} {
		var got int
		if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM `+table).Scan(&got); err != nil {
			t.Fatal(err)
		}
		if got != want {
			t.Fatalf("%s row count = %d, want %d", table, got, want)
		}
	}
}

func TestApplyClaimReconciliationIsIdempotentAndRejectsStaleWriters(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-replay")
	input.Claims = []ClaimImport{{
		ID: "claim:app-owner", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns runtime behavior",
		State: claim.StateStale, PriorState: claim.StateSupported, Freshness: claim.FreshnessStale, StateReason: "changed_path",
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}
	batch := ClaimReconciliationBatch{
		ID: "claim-reconciliation:packet-replay", PacketHash: "packet-replay", GenerationID: "GEN-replay",
		Workflow: "sp-plan", ObservedAt: "2026-07-13T10:00:00Z", CommitSHA: "abc123",
		Items: []ClaimReconciliationItem{{
			ClaimID: "claim:app-owner", ExpectedState: claim.StateStale, Reason: "bounded_live_read",
			Evidence:     []ClaimReconciliationEvidence{{ID: "E-replay", SourceKind: "source", SourcePath: "src/app.go", Span: "L1-L5", ContentHash: "sha256:replay", Role: "supporting"}},
			Verification: &ClaimReconciliationVerification{ID: "V-replay", Result: claim.VerificationPassed, Command: "go test ./..."},
		}},
	}
	if _, err := st.ApplyClaimReconciliation(ctx, batch); err != nil {
		t.Fatal(err)
	}
	replayed, err := st.ApplyClaimReconciliation(ctx, batch)
	if err != nil {
		t.Fatal(err)
	}
	if !replayed.Replayed {
		t.Fatalf("replayed result = %#v, want replayed=true", replayed)
	}

	conflict := batch
	conflict.ID = "claim-reconciliation:packet-conflict"
	conflict.PacketHash = "packet-conflict"
	conflict.ObservedAt = "2026-07-13T09:59:59Z"
	if _, err := st.ApplyClaimReconciliation(ctx, conflict); err == nil {
		t.Fatal("older reconciliation succeeded, want stale-writer rejection")
	}
	var count int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM claim_reconciliations`).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Fatalf("claim_reconciliations count = %d, want atomic no-write on rejection", count)
	}
}

package store

import (
	"context"
	"strings"
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
		Workflow: "sp-implement", ObservedAt: "2026-07-13T09:00:00Z", CommitSHA: "abc123",
		Items: []ClaimReconciliationItem{{
			ClaimID: "claim:app-owner", ExpectedState: claim.StateStale, ExpectedRevision: 1, Reason: "live_source_and_test_confirm_owner",
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
	claims, err := st.ClaimEvidenceForNodeIDs(ctx, []string{"N-app"})
	if err != nil {
		t.Fatal(err)
	}
	if len(claims) != 1 || len(claims[0].Evidence) != 1 || claims[0].Evidence[0].ID != "E-reconcile-1" {
		t.Fatalf("current claim evidence = %#v, want only E-reconcile-1", claims)
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

func TestApplyClaimReconciliationRecordsGenericFailureWithoutPromotion(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-failed")
	input.Claims = []ClaimImport{{
		ID: "claim:app-owner", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns runtime behavior",
		State: claim.StateStale, PriorState: claim.StateSupported, Freshness: claim.FreshnessStale, StateReason: "changed_path", SupportingEvidenceIDs: []string{"E-001"},
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	result, err := st.ApplyClaimReconciliation(ctx, ClaimReconciliationBatch{
		ID: "claim-reconciliation:failed", PacketHash: "failed", GenerationID: "GEN-failed", Workflow: "sp-debug",
		ObservedAt: "2026-07-13T09:00:00Z", CommitSHA: "abc123",
		Items: []ClaimReconciliationItem{{
			ClaimID: "claim:app-owner", ExpectedState: claim.StateStale, ExpectedRevision: 1, Reason: "generic suite failed",
			Verification: &ClaimReconciliationVerification{ID: "V-failed", Result: claim.VerificationFailed, Command: "go test ./..."},
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if result.ResultState != "partial" || result.Claims[0].ToState != claim.StateStale || result.Claims[0].TransitionID != "" {
		t.Fatalf("result = %#v, want partial stale claim without transition", result)
	}
	var state, basis string
	if err := st.DB().QueryRowContext(ctx, `SELECT state FROM claims WHERE id = ?`, "claim:app-owner").Scan(&state); err != nil {
		t.Fatal(err)
	}
	if err := st.DB().QueryRowContext(ctx, `SELECT basis_state FROM claim_evidence WHERE claim_id = ? AND evidence_id = ?`, "claim:app-owner", "E-001").Scan(&basis); err != nil {
		t.Fatal(err)
	}
	if state != string(claim.StateStale) || basis != "current" {
		t.Fatalf("claim/basis = %q/%q, generic failure must preserve stale/current", state, basis)
	}
}

func TestApplyClaimReconciliationPreflightsWholeBatchBeforeWriting(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-atomic")
	input.Claims = []ClaimImport{{
		ID: "claim:app-owner", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns runtime behavior",
		State: claim.StateStale, PriorState: claim.StateSupported, Freshness: claim.FreshnessStale, StateReason: "changed_path",
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}
	evidence := func(id string) []ClaimReconciliationEvidence {
		return []ClaimReconciliationEvidence{{ID: id, SourceKind: "source", SourcePath: "src/app.go", Span: "L1", ContentHash: "sha256:atomic", Role: "supporting"}}
	}
	_, err := st.ApplyClaimReconciliation(ctx, ClaimReconciliationBatch{
		ID: "claim-reconciliation:atomic", PacketHash: "atomic", GenerationID: "GEN-atomic", Workflow: "sp-plan",
		ObservedAt: "2026-07-13T09:00:00Z", CommitSHA: "abc123",
		Items: []ClaimReconciliationItem{
			{ClaimID: "claim:app-owner", ExpectedState: claim.StateStale, ExpectedRevision: 1, Reason: "valid first item", Evidence: evidence("E-atomic-1")},
			{ClaimID: "claim:missing", ExpectedState: claim.StateStale, ExpectedRevision: 1, Reason: "invalid second item", Evidence: evidence("E-atomic-2")},
		},
	})
	if err == nil {
		t.Fatal("ApplyClaimReconciliation succeeded with missing second claim")
	}
	for table := range map[string]bool{"claim_reconciliations": true, "claim_verifications": true} {
		var count int
		if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM `+table).Scan(&count); err != nil {
			t.Fatal(err)
		}
		if count != 0 {
			t.Fatalf("%s count = %d, want zero after atomic preflight failure", table, count)
		}
	}
	var evidenceCount int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM evidence WHERE id LIKE 'E-atomic-%'`).Scan(&evidenceCount); err != nil {
		t.Fatal(err)
	}
	if evidenceCount != 0 {
		t.Fatalf("reconciliation evidence count = %d, want zero", evidenceCount)
	}
}

func TestApplyClaimReconciliationCanReplaceContradictedBasis(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-recover")
	input.Claims = []ClaimImport{{
		ID: "claim:app-owner", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns runtime behavior",
		State: claim.StateContradicted, Freshness: claim.FreshnessFresh, StateReason: "old counterexample", ContradictingEvidenceIDs: []string{"E-001"},
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}
	result, err := st.ApplyClaimReconciliation(ctx, ClaimReconciliationBatch{
		ID: "claim-reconciliation:recover", PacketHash: "recover", GenerationID: "GEN-recover", Workflow: "sp-debug",
		ObservedAt: "2026-07-13T09:00:00Z", CommitSHA: "abc123",
		Items: []ClaimReconciliationItem{{
			ClaimID: "claim:app-owner", ExpectedState: claim.StateContradicted, ExpectedRevision: 1, Reason: "new bounded basis resolves counterexample",
			Evidence:     []ClaimReconciliationEvidence{{ID: "E-recover", SourceKind: "test", SourcePath: "src/app.go", Span: "L1", ContentHash: "sha256:recover", Role: "supporting"}},
			Verification: &ClaimReconciliationVerification{ID: "V-recover", Result: claim.VerificationPassed, Command: "go test ./..."},
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if result.Claims[0].FromState != claim.StateContradicted || result.Claims[0].ToState != claim.StateVerified {
		t.Fatalf("record = %#v, want contradicted -> verified", result.Claims[0])
	}
	var oldBasis, newBasis string
	if err := st.DB().QueryRowContext(ctx, `SELECT basis_state FROM claim_evidence WHERE evidence_id = 'E-001'`).Scan(&oldBasis); err != nil {
		t.Fatal(err)
	}
	if err := st.DB().QueryRowContext(ctx, `SELECT basis_state FROM claim_evidence WHERE evidence_id = 'E-recover'`).Scan(&newBasis); err != nil {
		t.Fatal(err)
	}
	if oldBasis != "superseded" || newBasis != "current" {
		t.Fatalf("basis = %q/%q, want superseded/current", oldBasis, newBasis)
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
		Workflow: "sp-plan", ObservedAt: "2026-07-13T09:00:00Z", CommitSHA: "abc123",
		Items: []ClaimReconciliationItem{{
			ClaimID: "claim:app-owner", ExpectedState: claim.StateStale, ExpectedRevision: 1, Reason: "bounded_live_read",
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
	conflict.ObservedAt = "2026-07-13T08:59:59Z"
	conflict.Items = append([]ClaimReconciliationItem(nil), batch.Items...)
	conflict.Items[0].ExpectedState = claim.StateVerified
	if _, err := st.ApplyClaimReconciliation(ctx, conflict); err == nil || !strings.Contains(err.Error(), "revision") {
		t.Fatal("older reconciliation succeeded, want stale-writer rejection")
	}
	replayConflict := batch
	replayConflict.PacketHash = "different-packet"
	if _, err := st.ApplyClaimReconciliation(ctx, replayConflict); err == nil || !strings.Contains(err.Error(), "conflicts with an existing packet") {
		t.Fatal("conflicting idempotency key succeeded, want packet identity rejection")
	}
	var count int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM claim_reconciliations`).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Fatalf("claim_reconciliations count = %d, want atomic no-write on rejection", count)
	}
}

func TestApplyClaimReconciliationDerivesSupportedContradictedAndBlockedStates(t *testing.T) {
	tests := []struct {
		name         string
		from         claim.State
		freshness    claim.Freshness
		evidenceRole string
		verification *ClaimReconciliationVerification
		wantState    claim.State
		wantResult   string
		wantBasis    string
	}{
		{name: "support without verification", from: claim.StateStale, freshness: claim.FreshnessStale, evidenceRole: "supporting", wantState: claim.StateSupported, wantResult: "ready", wantBasis: "current"},
		{name: "claim-specific contradiction", from: claim.StateSupported, freshness: claim.FreshnessFresh, evidenceRole: "contradicting", verification: &ClaimReconciliationVerification{ID: "V-case", Result: claim.VerificationContradicted, Command: "go test ./..."}, wantState: claim.StateContradicted, wantResult: "ready", wantBasis: "current"},
		{name: "blocked verification", from: claim.StateStale, freshness: claim.FreshnessStale, evidenceRole: "supporting", verification: &ClaimReconciliationVerification{ID: "V-case", Result: claim.VerificationBlocked, Command: "go test ./..."}, wantState: claim.StateStale, wantResult: "partial", wantBasis: "historical"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			st := openImportTestStore(t)
			defer st.Close()
			ctx := context.Background()
			input := validImportInput("GEN-case")
			input.Claims = []ClaimImport{{ID: "claim:app", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "owner", State: tt.from, Freshness: tt.freshness, StateReason: "old"}}
			if _, err := st.ImportGeneration(ctx, input); err != nil {
				t.Fatal(err)
			}
			result, err := st.ApplyClaimReconciliation(ctx, ClaimReconciliationBatch{
				ID: "claim-reconciliation:case", PacketHash: "case", GenerationID: "GEN-case", Workflow: "sp-plan", ObservedAt: "2026-07-13T09:00:00Z", CommitSHA: "abc123",
				Items: []ClaimReconciliationItem{{
					ClaimID: "claim:app", ExpectedState: tt.from, ExpectedRevision: 1, Reason: "case evidence",
					Evidence:     []ClaimReconciliationEvidence{{ID: "E-case", SourceKind: "source", SourcePath: "src/app.go", Span: "L1", ContentHash: "sha256:case", Role: tt.evidenceRole}},
					Verification: tt.verification,
				}},
			})
			if err != nil {
				t.Fatal(err)
			}
			if result.ResultState != tt.wantResult || result.Claims[0].ToState != tt.wantState {
				t.Fatalf("result = %#v, want %s/%s", result, tt.wantResult, tt.wantState)
			}
			var basis string
			if err := st.DB().QueryRowContext(ctx, `SELECT basis_state FROM claim_evidence WHERE evidence_id = 'E-case'`).Scan(&basis); err != nil {
				t.Fatal(err)
			}
			if basis != tt.wantBasis {
				t.Fatalf("basis = %q, want %q", basis, tt.wantBasis)
			}
		})
	}
}

func TestValidateClaimReconciliationBatchRejectsInvalidContracts(t *testing.T) {
	valid := ClaimReconciliationBatch{
		ID: "claim-reconciliation:valid", PacketHash: "valid", GenerationID: "GEN", Workflow: "sp-plan", ObservedAt: "2026-07-13T09:00:00Z", CommitSHA: "abc123",
		Items: []ClaimReconciliationItem{{
			ClaimID: "claim:app", ExpectedState: claim.StateStale, ExpectedRevision: 1, Reason: "bounded evidence",
			Evidence:     []ClaimReconciliationEvidence{{ID: "E-valid", SourceKind: "source", SourcePath: "src/app.go", Span: "L1", ContentHash: "sha256:valid", Role: "supporting"}},
			Verification: &ClaimReconciliationVerification{ID: "V-valid", Result: claim.VerificationPassed, Command: "go test ./..."},
		}},
	}
	tests := map[string]func(*ClaimReconciliationBatch){
		"missing id":           func(batch *ClaimReconciliationBatch) { batch.ID = "" },
		"bad timestamp":        func(batch *ClaimReconciliationBatch) { batch.ObservedAt = "today" },
		"future timestamp":     func(batch *ClaimReconciliationBatch) { batch.ObservedAt = "2099-01-01T00:00:00Z" },
		"no items":             func(batch *ClaimReconciliationBatch) { batch.Items = nil },
		"missing claim fields": func(batch *ClaimReconciliationBatch) { batch.Items[0].Reason = "" },
		"no evidence or verification": func(batch *ClaimReconciliationBatch) {
			batch.Items[0].Evidence = nil
			batch.Items[0].Verification = nil
		},
		"incomplete evidence":           func(batch *ClaimReconciliationBatch) { batch.Items[0].Evidence[0].Span = "" },
		"invalid role":                  func(batch *ClaimReconciliationBatch) { batch.Items[0].Evidence[0].Role = "truth" },
		"missing verification identity": func(batch *ClaimReconciliationBatch) { batch.Items[0].Verification.ID = "" },
		"invalid result":                func(batch *ClaimReconciliationBatch) { batch.Items[0].Verification.Result = "unknown" },
		"passed without support":        func(batch *ClaimReconciliationBatch) { batch.Items[0].Evidence[0].Role = "contradicting" },
		"contradicted without counter": func(batch *ClaimReconciliationBatch) {
			batch.Items[0].Verification.Result = claim.VerificationContradicted
		},
	}
	for name, mutate := range tests {
		t.Run(name, func(t *testing.T) {
			batch := cloneReconciliationBatch(valid)
			mutate(&batch)
			if err := validateReconciliationBatch(batch); err == nil {
				t.Fatal("validateReconciliationBatch succeeded, want rejection")
			}
		})
	}
}

func cloneReconciliationBatch(batch ClaimReconciliationBatch) ClaimReconciliationBatch {
	batch.Items = append([]ClaimReconciliationItem(nil), batch.Items...)
	for index := range batch.Items {
		batch.Items[index].Evidence = append([]ClaimReconciliationEvidence(nil), batch.Items[index].Evidence...)
		if batch.Items[index].Verification != nil {
			verification := *batch.Items[index].Verification
			batch.Items[index].Verification = &verification
		}
	}
	return batch
}

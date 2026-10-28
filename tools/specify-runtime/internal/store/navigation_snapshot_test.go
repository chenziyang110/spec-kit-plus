package store

import (
	"context"
	"fmt"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
)

func TestNavigationSnapshotBindsEveryCurrentGraphTable(t *testing.T) {
	mutations := map[string]string{
		"metadata":              `UPDATE metadata SET updated_at = updated_at || '-changed'`,
		"generations":           `UPDATE generations SET source_commit = 'new-commit' WHERE state = 'active'`,
		"nodes":                 `UPDATE nodes SET attrs_json = '{"owner":"changed"}'`,
		"evidence":              `UPDATE evidence SET content_hash = 'changed'`,
		"node_evidence":         `DELETE FROM node_evidence`,
		"edges":                 `UPDATE edges SET type = 'changed'`,
		"edge_evidence":         `DELETE FROM edge_evidence`,
		"observations":          `UPDATE observations SET summary = 'changed'`,
		"observation_evidence":  `DELETE FROM observation_evidence`,
		"path_index":            `UPDATE path_index SET path = 'src/renamed.go'`,
		"alias_index":           `UPDATE alias_index SET normalized_alias = 'changed'`,
		"claims":                `UPDATE claims SET revision = revision + 1`,
		"claim_evidence":        `UPDATE claim_evidence SET basis_state = 'superseded'`,
		"claim_verifications":   `UPDATE claim_verifications SET result = 'failed'`,
		"claim_transitions":     `UPDATE claim_transitions SET reason = 'changed'`,
		"claim_reconciliations": `UPDATE claim_reconciliations SET packet_hash = 'changed'`,
		"updates":               `UPDATE updates SET result_state = 'ready'`,
	}
	for _, table := range RequiredTables() {
		if _, ok := mutations[table]; !ok {
			t.Fatalf("navigation coverage has no mutation for current table %s", table)
		}
	}
	for table, mutation := range mutations {
		t.Run(table, func(t *testing.T) {
			st := navigationTestStore(t)
			defer st.Close()
			ctx := context.Background()
			before, err := st.ReadNavigationSnapshot(ctx)
			if err != nil {
				t.Fatal(err)
			}
			same, err := st.ReadNavigationSnapshot(ctx)
			if err != nil || same != before {
				t.Fatalf("unchanged snapshot: %#v %v", same, err)
			}
			result, err := st.DB().ExecContext(ctx, mutation)
			if err != nil {
				t.Fatal(err)
			}
			count, err := result.RowsAffected()
			if err != nil || count == 0 {
				t.Fatalf("mutation did not affect rows: %d %v", count, err)
			}
			after, err := st.ReadNavigationSnapshot(ctx)
			if err != nil {
				t.Fatal(err)
			}
			if after.GenerationID != before.GenerationID || after.Digest == before.Digest {
				t.Fatalf("same-generation %s mutation did not invalidate snapshot: before=%#v after=%#v", table, before, after)
			}
		})
	}
}

func TestNavigationReadRejectsConcurrentCommitIncludingSemanticABA(t *testing.T) {
	st := navigationTestStore(t)
	defer st.Close()
	ctx := context.Background()
	read, err := st.BeginNavigationRead(ctx)
	if err != nil {
		t.Fatal(err)
	}
	defer read.Close()
	if err := read.Validate(ctx); err != nil {
		t.Fatal(err)
	}
	done := make(chan error, 1)
	go func() {
		if _, err := st.DB().ExecContext(ctx, `UPDATE nodes SET title = 'temporary' WHERE id = 'N-app'`); err != nil {
			done <- err
			return
		}
		_, err := st.DB().ExecContext(ctx, `UPDATE nodes SET title = 'App' WHERE id = 'N-app'`)
		done <- err
	}()
	if err := <-done; err != nil {
		t.Fatal(err)
	}
	after, err := st.ReadNavigationSnapshot(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if after != read.Snapshot {
		t.Fatalf("fixture must restore semantic bytes to test ABA: %#v %#v", after, read.Snapshot)
	}
	if err := read.Validate(ctx); err == nil {
		t.Fatal("navigation guard accepted intervening commits restored to old content")
	}
}

func navigationTestStore(t *testing.T) *Store {
	t.Helper()
	st := openImportTestStore(t)
	t.Cleanup(func() { _ = st.Close() })
	ctx := context.Background()
	input := validImportInput("GEN-navigation")
	input.Edges = []EdgeImport{{ID: "edge:app", Type: "owns", SourceID: "N-app", TargetID: "N-app", Confidence: "verified", EvidenceIDs: []string{"E-001"}}}
	input.Observations = []ObservationImport{{ID: "obs:app", ObservationType: "owner", Summary: "App owns route", EvidenceIDs: []string{"E-001"}}}
	input.Aliases = []AliasImport{{ID: "alias:app", Alias: "app", NormalizedAlias: "app", TargetType: "node", TargetID: "N-app", Source: "test", Confidence: "verified", EvidenceID: "E-001"}}
	input.Claims = []ClaimImport{{ID: "claim:app", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns route", State: claim.StateStale, PriorState: claim.StateSupported, Freshness: claim.FreshnessStale, StateReason: "fixture", SupportingEvidenceIDs: []string{"E-001"}}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}
	if _, err := st.ApplyClaimReconciliation(ctx, ClaimReconciliationBatch{
		ID: "reconcile:nav", PacketHash: "packet", GenerationID: input.GenerationID, Workflow: "sp-debug", ObservedAt: "2026-07-13T09:00:00Z", CommitSHA: "abc123",
		Items: []ClaimReconciliationItem{{ClaimID: "claim:app", ExpectedState: claim.StateStale, ExpectedRevision: 1, Reason: "live evidence", Evidence: []ClaimReconciliationEvidence{{ID: "E-reconciled", SourceKind: "source", SourcePath: "src/app.go", Span: "L1-L2", ContentHash: "sha256:current", Role: "supporting"}}, Verification: &ClaimReconciliationVerification{ID: "verification:nav", Result: claim.VerificationPassed, Command: "test"}}},
	}); err != nil {
		t.Fatal(err)
	}
	if err := st.RecordStructuredUpdate(ctx, UpdateRecord{ID: "update:nav", Trigger: "test", ResultState: "partial"}); err != nil {
		t.Fatal(err)
	}
	if err := st.DB().PingContext(ctx); err != nil {
		t.Fatal(fmt.Errorf("fixture store: %w", err))
	}
	return st
}

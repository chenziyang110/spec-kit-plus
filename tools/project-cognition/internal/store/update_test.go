package store

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
)

func TestRecordStructuredUpdatePersistsAffectedFields(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-update")
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	record := UpdateRecord{
		ID:             "upd-test",
		Trigger:        "workflow-finalize",
		ChangedPaths:   []string{"src/app.go"},
		AffectedNodes:  []string{"capability:app"},
		AffectedClaims: []string{"claim:app"},
		AffectedSlices: []string{"slice:runtime"},
		ResultState:    "ready",
		Attrs: map[string]any{
			"known_unknowns": []string{"none"},
		},
	}
	if err := st.RecordStructuredUpdate(ctx, record); err != nil {
		t.Fatal(err)
	}

	var changedJSON, nodesJSON, claimsJSON, slicesJSON, resultState, attrsJSON string
	if err := st.DB().QueryRowContext(ctx, `SELECT changed_paths_json, affected_nodes_json, affected_claims_json, affected_slices_json, result_state, attrs_json FROM updates WHERE id = ?`, "upd-test").Scan(&changedJSON, &nodesJSON, &claimsJSON, &slicesJSON, &resultState, &attrsJSON); err != nil {
		t.Fatal(err)
	}
	if resultState != "ready" {
		t.Fatalf("result_state = %q, want ready", resultState)
	}
	assertJSONStrings(t, changedJSON, []string{"src/app.go"})
	assertJSONStrings(t, nodesJSON, []string{"capability:app"})
	assertJSONStrings(t, claimsJSON, []string{"claim:app"})
	assertJSONStrings(t, slicesJSON, []string{"slice:runtime"})
	var attrs map[string]any
	if err := json.Unmarshal([]byte(attrsJSON), &attrs); err != nil {
		t.Fatal(err)
	}
	if _, ok := attrs["known_unknowns"]; !ok {
		t.Fatalf("attrs = %#v, want known_unknowns", attrs)
	}
}

func TestAffectedClosureForPathsReturnsRelatedTypedClaims(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-closure")
	input.Claims = []ClaimImport{{
		ID: "claim:app-owner", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns runtime behavior",
		State: claim.StateSupported, Freshness: claim.FreshnessFresh, StateReason: "supporting_evidence",
		SupportingEvidenceIDs: []string{"E-001"},
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	closure, err := st.AffectedClosureForPaths(ctx, []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	if !containsString(closure.NodeIDs, "N-app") {
		t.Fatalf("closure = %#v, want N-app", closure)
	}
	if !containsString(closure.ClaimIDs, "claim:app-owner") {
		t.Fatalf("closure.ClaimIDs = %#v, want claim:app-owner", closure.ClaimIDs)
	}
	if len(closure.SliceIDs) != 0 {
		t.Fatalf("closure.SliceIDs = %#v, want empty until slice tables return", closure.SliceIDs)
	}
}

func TestMarkClaimsStaleRecordsAuditableTransition(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-stale-claim")
	input.Claims = []ClaimImport{{
		ID: "claim:app-owner", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns runtime behavior",
		State: claim.StateSupported, Freshness: claim.FreshnessFresh, StateReason: "supporting_evidence",
		SupportingEvidenceIDs: []string{"E-001"},
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	transitions, err := st.MarkClaimsStale(ctx, []string{"claim:app-owner"}, "changed_path:src/app.go", "update:test")
	if err != nil {
		t.Fatal(err)
	}
	if len(transitions) != 1 || transitions[0].FromState != claim.StateSupported || transitions[0].ToState != claim.StateStale {
		t.Fatalf("transitions = %#v, want supported -> stale", transitions)
	}
	var state, priorState, freshness, reason string
	if err := st.DB().QueryRowContext(ctx, `SELECT state, prior_state, freshness, state_reason FROM claims WHERE id = 'claim:app-owner'`).Scan(&state, &priorState, &freshness, &reason); err != nil {
		t.Fatal(err)
	}
	if state != string(claim.StateStale) || priorState != string(claim.StateSupported) || freshness != string(claim.FreshnessStale) || reason != "changed_path:src/app.go" {
		t.Fatalf("claim lifecycle = %q/%q/%q/%q, want stale/supported/stale/changed_path", state, priorState, freshness, reason)
	}
}

func TestRefreshPathCoverageUpdatesIndexedPathEvidence(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-adopt")
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	record, err := st.RefreshPathCoverage(ctx, PathCoverageRefresh{
		UpdateID:   "upd-adopt",
		Path:       "src/app.go",
		NodeID:     "N-app",
		Relation:   "owns",
		Confidence: "verified",
		Reason:     "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if record.EvidenceID == "" {
		t.Fatalf("record = %#v, want evidence id", record)
	}
	var evidenceID string
	if err := st.DB().QueryRowContext(ctx, `SELECT evidence_id FROM path_index WHERE generation_id = ? AND path = ?`, "GEN-adopt", "src/app.go").Scan(&evidenceID); err != nil {
		t.Fatal(err)
	}
	if evidenceID != record.EvidenceID {
		t.Fatalf("path evidence = %q, want %q", evidenceID, record.EvidenceID)
	}
}

func TestRefreshPathCoverageWritesPathAliases(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-path-alias")); err != nil {
		t.Fatal(err)
	}

	if _, err := st.RefreshPathCoverage(ctx, PathCoverageRefresh{
		UpdateID:   "upd-path-alias",
		Path:       "src/new-feature.go",
		NodeID:     "N-app",
		Relation:   "owns",
		Confidence: "verified",
		Reason:     "workflow-finalize",
	}); err != nil {
		t.Fatal(err)
	}

	row := activeCandidateRow(t, st, ctx, "N-app")
	if !conceptAliasContains(row.Aliases, "new-feature", "workflow_update_path") {
		t.Fatalf("aliases = %#v, want workflow_update_path alias for new-feature", row.Aliases)
	}
	if !conceptAliasContains(row.Aliases, "src/new-feature.go", "workflow_update_path") {
		t.Fatalf("aliases = %#v, want workflow_update_path alias for full path", row.Aliases)
	}
}

func TestAdoptWorkflowPathWritesAliasRows(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-adopt-alias")); err != nil {
		t.Fatal(err)
	}

	nodeID, err := st.AdoptWorkflowPath(ctx, WorkflowPathAdoption{
		UpdateID:         "upd-adopt-alias",
		Path:             "src/semantic-router.go",
		Workflow:         "sp-implement",
		BehaviorSurfaces: []string{"semantic routing"},
		Verification:     []map[string]string{{"command": "go test ./...", "result": "passed"}},
		Reason:           "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}

	row := activeCandidateRow(t, st, ctx, nodeID)
	if !conceptAliasContains(row.Aliases, "semantic-router.go", "workflow_update_title") {
		t.Fatalf("aliases = %#v, want workflow_update_title alias", row.Aliases)
	}
	if !conceptAliasContains(row.Aliases, "semantic-router", "workflow_update_path") {
		t.Fatalf("aliases = %#v, want workflow_update_path alias", row.Aliases)
	}
	if !conceptAliasContains(row.Aliases, "sp-implement", "workflow_update_workflow") {
		t.Fatalf("aliases = %#v, want workflow_update_workflow alias", row.Aliases)
	}
	if !conceptAliasContains(row.Aliases, "semantic routing", "workflow_update_surface") {
		t.Fatalf("aliases = %#v, want workflow_update_surface alias", row.Aliases)
	}
}

func activeCandidateRow(t *testing.T, st *Store, ctx context.Context, nodeID string) ConceptCandidateRow {
	t.Helper()
	rows, err := st.AllActiveConceptCandidateRows(ctx)
	if err != nil {
		t.Fatal(err)
	}
	for _, row := range rows {
		if row.NodeID == nodeID {
			return row
		}
	}
	t.Fatalf("active candidate rows = %#v, want %s", rows, nodeID)
	return ConceptCandidateRow{}
}

func assertJSONStrings(t *testing.T, raw string, want []string) {
	t.Helper()
	var got []string
	if err := json.Unmarshal([]byte(raw), &got); err != nil {
		t.Fatal(err)
	}
	if len(got) != len(want) {
		t.Fatalf("got %#v, want %#v", got, want)
	}
	for index := range want {
		if got[index] != want[index] {
			t.Fatalf("got %#v, want %#v", got, want)
		}
	}
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

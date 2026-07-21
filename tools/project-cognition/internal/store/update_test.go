package store

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"

	changemodel "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/changes/model"
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

func TestAffectedClosureForPathsEmptyDoesNotReturnWholeGraph(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	if _, err := st.ImportGeneration(context.Background(), validImportInput("GEN-empty-closure")); err != nil {
		t.Fatal(err)
	}

	closure, err := st.AffectedClosureForPaths(context.Background(), nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(closure.NodeIDs) != 0 || len(closure.ClaimIDs) != 0 || len(closure.SliceIDs) != 0 || closure.Truncated {
		t.Fatalf("closure = %#v, empty path input must not expand the whole graph", closure)
	}
}

func TestAffectedClosureForPathsTraversesTypedEdgesWithoutSilentLimit(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-wide-closure")
	input.Nodes = []NodeImport{}
	input.Edges = []EdgeImport{}
	for index := 0; index < 31; index++ {
		nodeID := fmt.Sprintf("N-%02d", index)
		input.Nodes = append(input.Nodes, NodeImport{
			ID: nodeID, Type: "capability", Title: nodeID, Confidence: "verified", EvidenceIDs: []string{"E-001"},
		})
		if index > 0 {
			input.Edges = append(input.Edges, EdgeImport{
				ID: fmt.Sprintf("EDGE-%02d", index), Type: "consumes", SourceID: nodeID,
				TargetID: fmt.Sprintf("N-%02d", index-1), Confidence: "verified", EvidenceIDs: []string{"E-001"},
			})
		}
	}
	input.PathIndex = []PathIndexImport{{
		ID: "P-wide-root", Path: "src/app.go", NodeID: "N-00", Relation: "owns", Confidence: "verified", EvidenceID: "E-001",
	}}
	input.Claims = []ClaimImport{{
		ID: "claim:wide-consumer", NodeID: "N-30", GraphClaimType: "runtime_consumer", Summary: "Tail consumes root",
		State: claim.StateSupported, Freshness: claim.FreshnessFresh, StateReason: "supporting_evidence", SupportingEvidenceIDs: []string{"E-001"},
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	closure, err := st.AffectedClosureForPaths(ctx, []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	if len(closure.NodeIDs) != 31 || !containsString(closure.NodeIDs, "N-30") {
		t.Fatalf("closure.NodeIDs = %#v, want all 31 typed-edge-connected nodes", closure.NodeIDs)
	}
	if !containsString(closure.ClaimIDs, "claim:wide-consumer") {
		t.Fatalf("closure.ClaimIDs = %#v, want downstream consumer claim", closure.ClaimIDs)
	}
	if closure.Truncated {
		t.Fatalf("closure = %#v, default traversal must not silently truncate", closure)
	}
}

func TestAffectedClosureBudgetReportsTruncationExplicitly(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-budget-closure")
	input.Nodes = []NodeImport{}
	input.Edges = []EdgeImport{}
	for index := 0; index < 8; index++ {
		nodeID := fmt.Sprintf("N-budget-%02d", index)
		input.Nodes = append(input.Nodes, NodeImport{ID: nodeID, Type: "capability", Title: nodeID, Confidence: "verified", EvidenceIDs: []string{"E-001"}})
		if index > 0 {
			input.Edges = append(input.Edges, EdgeImport{
				ID: fmt.Sprintf("EDGE-budget-%02d", index), Type: "owns", SourceID: fmt.Sprintf("N-budget-%02d", index-1),
				TargetID: nodeID, Confidence: "verified", EvidenceIDs: []string{"E-001"},
			})
		}
	}
	input.PathIndex = []PathIndexImport{{ID: "P-budget", Path: "src/app.go", NodeID: "N-budget-00", Relation: "owns", Confidence: "verified", EvidenceID: "E-001"}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	closure, err := st.AffectedClosureForPathsWithBudget(ctx, []string{"src/app.go"}, ClosureBudget{MaxNodes: 5})
	if err != nil {
		t.Fatal(err)
	}
	if len(closure.NodeIDs) != 5 || !closure.Truncated || closure.TruncationReason != "node_budget_exhausted" {
		t.Fatalf("closure = %#v, want explicit five-node budget truncation", closure)
	}

	nodeClosure, err := st.AffectedClosureForPathsAndNodeIDsWithBudget(ctx, nil, []string{"N-budget-00"}, ClosureBudget{MaxNodes: 5})
	if err != nil {
		t.Fatal(err)
	}
	if len(nodeClosure.NodeIDs) != 5 || !nodeClosure.Truncated || nodeClosure.TruncationReason != "node_budget_exhausted" {
		t.Fatalf("node closure = %#v, want explicit-node seeds to use the same bounded traversal", nodeClosure)
	}
}

func TestApplyTypedUpdateAtomicallyAppliesAllPathOperationsAndRecordsThem(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	input := validImportInput("GEN-typed-update")
	input.Nodes = append(input.Nodes,
		NodeImport{ID: "N-obsolete", Type: "capability", Title: "Obsolete", Confidence: "verified", EvidenceIDs: []string{"E-001"}},
		NodeImport{ID: "N-stable", Type: "capability", Title: "Stable", Confidence: "verified", EvidenceIDs: []string{"E-001"}},
	)
	input.PathIndex = append(input.PathIndex,
		PathIndexImport{ID: "P-obsolete", Path: "src/obsolete.go", NodeID: "N-obsolete", Relation: "owns", Confidence: "verified", EvidenceID: "E-001"},
		PathIndexImport{ID: "P-stable", Path: "src/stable.go", NodeID: "N-stable", Relation: "owns", Confidence: "verified", EvidenceID: "E-001"},
	)
	input.Aliases = []AliasImport{
		{ID: "ALIAS-app-path", Alias: "src/app.go", NormalizedAlias: "src/app.go", TargetType: "node", TargetID: "N-app", Source: "workflow_update_path", Confidence: "verified", EvidenceID: "E-001"},
		{ID: "ALIAS-obsolete-path", Alias: "src/obsolete.go", NormalizedAlias: "src/obsolete.go", TargetType: "node", TargetID: "N-obsolete", Source: "workflow_update_path", Confidence: "verified", EvidenceID: "E-001"},
	}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}
	disposition := changemodel.DispositionAdoptable
	pathChanges := []changemodel.PathChange{
		{Path: "src/renamed-app.go", OldPath: "src/app.go", Operation: changemodel.OperationRename, NodeID: "N-app", Disposition: &disposition, EvidenceRefs: []string{"E-001"}},
		{Path: "src/obsolete.go", Operation: changemodel.OperationDelete, NodeID: "N-obsolete", Disposition: &disposition, EvidenceRefs: []string{"E-001"}},
		{Path: "src/stable.go", Operation: changemodel.OperationModify, NodeID: "N-stable", Disposition: &disposition, EvidenceRefs: []string{"test:stable"}},
		{Path: "src/new-feature.go", Operation: changemodel.OperationAdd, Disposition: &disposition, EvidenceRefs: []string{"test:new-feature"}},
	}
	result, err := st.ApplyTypedUpdate(ctx, TypedUpdate{
		Record:           UpdateRecord{ID: "upd-typed", Trigger: "workflow-finalize", ChangedPaths: []string{"src/renamed-app.go", "src/obsolete.go", "src/stable.go", "src/new-feature.go"}, AffectedNodes: []string{"N-app", "N-obsolete", "N-stable"}, ResultState: "ready"},
		PathChanges:      pathChanges,
		Workflow:         "sp-implement",
		BehaviorSurfaces: []string{"typed update"},
		Verification:     []map[string]string{{"command": "go test ./...", "result": "passed"}},
		Reason:           "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(result.RenamedPaths) != 1 || len(result.DeletedPaths) != 1 || len(result.RefreshedPaths) != 1 || len(result.AdoptedPaths) != 1 {
		t.Fatalf("result = %#v, want one result for every operation", result)
	}
	mapped, err := st.NodeIDsForExactPaths(ctx, []string{"src/app.go", "src/renamed-app.go", "src/obsolete.go", "src/stable.go", "src/new-feature.go"})
	if err != nil {
		t.Fatal(err)
	}
	if mapped["src/renamed-app.go"] != "N-app" || mapped["src/app.go"] != "" || mapped["src/obsolete.go"] != "" || mapped["src/stable.go"] != "N-stable" || mapped["src/new-feature.go"] == "" {
		t.Fatalf("mapped paths = %#v, want rename/delete/modify/add effects", mapped)
	}
	var attrsJSON string
	if err := st.DB().QueryRowContext(ctx, `SELECT attrs_json FROM updates WHERE id = 'upd-typed'`).Scan(&attrsJSON); err != nil {
		t.Fatal(err)
	}
	var attrs map[string]json.RawMessage
	if err := json.Unmarshal([]byte(attrsJSON), &attrs); err != nil {
		t.Fatal(err)
	}
	if _, ok := attrs["path_changes"]; !ok {
		t.Fatalf("update attrs = %s, want path_changes audit payload", attrsJSON)
	}
	var oldAliasCount, newAliasCount int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM alias_index WHERE generation_id = 'GEN-typed-update' AND source = 'workflow_update_path' AND normalized_alias = 'src/app.go'`).Scan(&oldAliasCount); err != nil {
		t.Fatal(err)
	}
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM alias_index WHERE generation_id = 'GEN-typed-update' AND source = 'workflow_update_path' AND normalized_alias = 'src/renamed-app.go'`).Scan(&newAliasCount); err != nil {
		t.Fatal(err)
	}
	if oldAliasCount != 0 || newAliasCount != 1 {
		t.Fatalf("path aliases old/new = %d/%d, want 0/1", oldAliasCount, newAliasCount)
	}
}

func TestApplyTypedUpdateRollsBackPathMutationWhenRecordFails(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-typed-rollback")); err != nil {
		t.Fatal(err)
	}
	if err := st.RecordStructuredUpdate(ctx, UpdateRecord{ID: "upd-duplicate", Trigger: "seed", ResultState: "recorded"}); err != nil {
		t.Fatal(err)
	}
	disposition := changemodel.DispositionAdoptable
	_, err := st.ApplyTypedUpdate(ctx, TypedUpdate{
		Record:      UpdateRecord{ID: "upd-duplicate", Trigger: "workflow-finalize", ChangedPaths: []string{"src/renamed-app.go"}, ResultState: "ready"},
		PathChanges: []changemodel.PathChange{{Path: "src/renamed-app.go", OldPath: "src/app.go", Operation: changemodel.OperationRename, NodeID: "N-app", Disposition: &disposition}},
	})
	if err == nil {
		t.Fatal("ApplyTypedUpdate returned nil error for duplicate update id")
	}
	mapped, lookupErr := st.NodeIDsForExactPaths(ctx, []string{"src/app.go", "src/renamed-app.go"})
	if lookupErr != nil {
		t.Fatal(lookupErr)
	}
	if mapped["src/app.go"] != "N-app" || mapped["src/renamed-app.go"] != "" {
		t.Fatalf("mapped paths after rollback = %#v, want original src/app.go mapping", mapped)
	}
}

func TestApplyTypedUpdateRejectsMissingDispositionBeforeMutation(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-disposition-required")); err != nil {
		t.Fatal(err)
	}

	_, err := st.ApplyTypedUpdate(ctx, TypedUpdate{
		Record:      UpdateRecord{ID: "upd-missing-disposition", Trigger: "workflow-finalize", ResultState: "partial_refresh"},
		PathChanges: []changemodel.PathChange{{Path: "src/new-feature.go", Operation: changemodel.OperationAdd}},
	})
	if err == nil {
		t.Fatal("ApplyTypedUpdate returned nil error for unresolved disposition")
	}
	var updateCount, pathCount int
	if queryErr := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM updates WHERE id = 'upd-missing-disposition'`).Scan(&updateCount); queryErr != nil {
		t.Fatal(queryErr)
	}
	if queryErr := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM path_index WHERE generation_id = 'GEN-disposition-required' AND path = 'src/new-feature.go'`).Scan(&pathCount); queryErr != nil {
		t.Fatal(queryErr)
	}
	if updateCount != 0 || pathCount != 0 {
		t.Fatalf("mutation counts update/path = %d/%d, want 0/0", updateCount, pathCount)
	}
}

func TestApplyTypedUpdateAuditsReviewOnlyPathWithoutAdoptingIt(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-review-only")); err != nil {
		t.Fatal(err)
	}
	disposition := changemodel.DispositionReviewOnly
	result, err := st.ApplyTypedUpdate(ctx, TypedUpdate{
		Record:      UpdateRecord{ID: "upd-review-only", Trigger: "workflow-finalize", ChangedPaths: []string{"src/review-only.go"}, ResultState: "partial_refresh"},
		PathChanges: []changemodel.PathChange{{Path: "src/review-only.go", Operation: changemodel.OperationAdd, Disposition: &disposition}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(result.SkippedPaths) != 1 || result.SkippedPaths[0] != "src/review-only.go" {
		t.Fatalf("result = %#v, want review-only path skipped", result)
	}
	var updateCount, pathCount int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM updates WHERE id = 'upd-review-only'`).Scan(&updateCount); err != nil {
		t.Fatal(err)
	}
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM path_index WHERE generation_id = 'GEN-review-only' AND path = 'src/review-only.go'`).Scan(&pathCount); err != nil {
		t.Fatal(err)
	}
	if updateCount != 1 || pathCount != 0 {
		t.Fatalf("mutation counts update/path = %d/%d, want audit-only 1/0", updateCount, pathCount)
	}
	var changedPathsJSON string
	if err := st.DB().QueryRowContext(ctx, `SELECT changed_paths_json FROM updates WHERE id = 'upd-review-only'`).Scan(&changedPathsJSON); err != nil {
		t.Fatal(err)
	}
	assertJSONStrings(t, changedPathsJSON, []string{})
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

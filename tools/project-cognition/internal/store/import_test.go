package store

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

func TestImportGenerationPersistsTypedClaimsAndLifecycleEvidence(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()
	input := validImportInput("GEN-claims")
	input.Claims = []ClaimImport{{
		ID:                    "claim:app-owner",
		NodeID:                "N-app",
		GraphClaimType:        "runtime_owner",
		Summary:               "App owns runtime behavior",
		State:                 claim.StateVerified,
		Freshness:             claim.FreshnessFresh,
		StateReason:           "supporting_evidence_and_current_verification",
		SupportingEvidenceIDs: []string{"E-001"},
		Verifications: []ClaimVerificationImport{{
			ID: "verification:app-owner", Result: claim.VerificationPassed, EvidenceID: "E-001", ObservedAt: "2026-07-13T10:00:00Z",
		}},
	}}

	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}
	var state, freshness, role, verificationResult string
	if err := st.DB().QueryRowContext(ctx, `SELECT state, freshness FROM claims WHERE id = 'claim:app-owner'`).Scan(&state, &freshness); err != nil {
		t.Fatal(err)
	}
	if state != string(claim.StateVerified) || freshness != string(claim.FreshnessFresh) {
		t.Fatalf("claim state/freshness = %q/%q, want %q/%q", state, freshness, claim.StateVerified, claim.FreshnessFresh)
	}
	if err := st.DB().QueryRowContext(ctx, `SELECT role FROM claim_evidence WHERE claim_id = 'claim:app-owner' AND evidence_id = 'E-001'`).Scan(&role); err != nil {
		t.Fatal(err)
	}
	if role != "supporting" {
		t.Fatalf("claim evidence role = %q, want supporting", role)
	}
	if err := st.DB().QueryRowContext(ctx, `SELECT result FROM claim_verifications WHERE claim_id = 'claim:app-owner'`).Scan(&verificationResult); err != nil {
		t.Fatal(err)
	}
	if verificationResult != string(claim.VerificationPassed) {
		t.Fatalf("verification result = %q, want passed", verificationResult)
	}
	snapshot, err := st.ActiveIdentitySnapshot(ctx)
	if err != nil {
		t.Fatal(err)
	}
	assertSnapshotIdentity(t, snapshot.Claims, "claim:app-owner")
}

func TestClaimLifecycleSummariesIncludeAllClaimsWithoutExpandingEvidence(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-claim-summary")); err != nil {
		t.Fatal(err)
	}
	claims := []struct {
		id        string
		state     string
		freshness string
	}{
		{id: "claim:a-candidate", state: "candidate", freshness: "fresh"},
		{id: "claim:b-supported", state: "supported", freshness: "fresh"},
		{id: "claim:c-verified", state: "verified_in_graph_generation", freshness: "fresh"},
		{id: "claim:y-stale", state: "stale", freshness: "stale"},
		{id: "claim:z-contradicted", state: "contradicted", freshness: "fresh"},
	}
	for _, graphClaim := range claims {
		if _, err := st.DB().ExecContext(ctx, `INSERT INTO claims(id, generation_id, node_id, graph_claim_type, summary, state, prior_state, freshness, state_reason, attrs_json, created_at, updated_at) VALUES(?, 'GEN-claim-summary', 'N-app', 'runtime_owner', ?, ?, '', ?, 'test', '{}', '2026-07-13T00:00:00Z', '2026-07-13T00:00:00Z')`, graphClaim.id, graphClaim.id, graphClaim.state, graphClaim.freshness); err != nil {
			t.Fatal(err)
		}
	}

	summaries, err := st.ClaimLifecycleSummariesForNodeIDs(ctx, []string{"N-app"})
	if err != nil {
		t.Fatal(err)
	}
	if len(summaries) != 1 {
		t.Fatalf("summaries = %#v, want one node aggregate", summaries)
	}
	got := summaries[0]
	if got.NodeID != "N-app" || got.ClaimCount != 5 || got.ContradictedCount != 1 || got.StaleCount != 1 || got.FreshVerifiedCount != 1 || got.FreshSupportedCount != 1 {
		t.Fatalf("summary = %#v, want complete lifecycle counts", got)
	}
}

func TestImportGenerationRejectsClaimReferencesBeforeMutation(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()
	input := validImportInput("GEN-broken-claim")
	input.Claims = []ClaimImport{{
		ID:                    "claim:broken",
		NodeID:                "N-missing",
		GraphClaimType:        "runtime_owner",
		Summary:               "Broken claim",
		State:                 claim.StateSupported,
		Freshness:             claim.FreshnessFresh,
		SupportingEvidenceIDs: []string{"E-missing"},
	}}

	_, err := st.ImportGeneration(ctx, input)
	if err == nil || !strings.Contains(err.Error(), "claim claim:broken references missing node N-missing") {
		t.Fatalf("ImportGeneration() error = %v, want missing claim node", err)
	}
	var generationCount int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM generations WHERE id = 'GEN-broken-claim'`).Scan(&generationCount); err != nil {
		t.Fatal(err)
	}
	if generationCount != 0 {
		t.Fatalf("generation count = %d, want zero after pre-transaction validation", generationCount)
	}
}

func TestImportGenerationPublishesActiveIdentitySnapshot(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	generationID, err := st.ImportGeneration(ctx, ImportInput{
		GenerationID: "GEN-import",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []EvidenceImport{{
			ID:          "E-001",
			SourcePath:  "src/app.go",
			SourceKind:  "source",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-app",
		}},
		Nodes: []NodeImport{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "App",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-001"},
		}},
		Edges: []EdgeImport{{
			ID:          "EDGE-app-self",
			Type:        "owns",
			SourceID:    "N-app",
			TargetID:    "N-app",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-001"},
		}},
		Observations: []ObservationImport{{
			ID:              "OBS-app",
			ObservationType: "summary",
			Summary:         "App observed",
			EvidenceIDs:     []string{"E-001"},
		}},
		PathIndex: []PathIndexImport{{
			ID:         "P-src-app-go",
			Path:       "src/app.go",
			NodeID:     "N-app",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-001",
		}},
		Rejections: []RowDecision{{
			Category: "coverage",
			Identity: "docs/missing.md",
			Reason:   "no_node_relation",
		}},
		MergeRecords: []MergeRecord{{
			Category:       "node",
			SourceIdentity: "N-app-duplicate",
			TargetIdentity: "N-app",
			Reason:         "duplicate_label",
		}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if generationID != "GEN-import" {
		t.Fatalf("generationID = %q, want GEN-import", generationID)
	}
	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "GEN-import" {
		t.Fatalf("activeID = %q, want GEN-import", activeID)
	}

	snapshot, err := st.ActiveIdentitySnapshot(ctx)
	if err != nil {
		t.Fatal(err)
	}
	assertSnapshotIdentity(t, snapshot.Evidence, "E-001|src/app.go|hash-app")
	assertSnapshotIdentity(t, snapshot.Nodes, "N-app")
	assertSnapshotIdentity(t, snapshot.Edges, "EDGE-app-self|N-app|N-app|owns")
	assertSnapshotIdentity(t, snapshot.Observations, "OBS-app")
	assertSnapshotIdentity(t, snapshot.CoveragePaths, "src/app.go")
	if len(snapshot.Rejections) != 1 || snapshot.Rejections[0].Reason != "no_node_relation" {
		t.Fatalf("Rejections = %#v, want one no_node_relation rejection", snapshot.Rejections)
	}
	if len(snapshot.MergeRecords) != 1 || snapshot.MergeRecords[0].TargetIdentity != "N-app" {
		t.Fatalf("MergeRecords = %#v, want one N-app target merge record", snapshot.MergeRecords)
	}
}

func TestInitializeGreenfieldEmptyCreatesReadyEmptyGeneration(t *testing.T) {
	paths := testPaths(t)
	st, err := Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()

	generationID, err := st.InitializeGreenfieldEmpty(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if generationID == "" {
		t.Fatal("generationID is empty")
	}

	activeGenerationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if activeGenerationID != generationID {
		t.Fatalf("active generation = %q, want %q", activeGenerationID, generationID)
	}

	kind, err := st.ActiveGenerationKind(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if kind != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("generation kind = %q, want %q", kind, rt.BaselineKindGreenfieldEmpty)
	}

	meta, err := st.Metadata(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if meta["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("metadata baseline_kind = %q, want %q", meta["baseline_kind"], rt.BaselineKindGreenfieldEmpty)
	}
	if meta["graph_ready"] != "true" {
		t.Fatalf("metadata graph_ready = %q, want true", meta["graph_ready"])
	}

	snapshot, err := st.ActiveIdentitySnapshot(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(snapshot.Evidence) != 0 ||
		len(snapshot.Nodes) != 0 ||
		len(snapshot.Edges) != 0 ||
		len(snapshot.Observations) != 0 ||
		len(snapshot.CoveragePaths) != 0 ||
		len(snapshot.Rejections) != 0 ||
		len(snapshot.MergeRecords) != 0 {
		t.Fatalf("greenfield snapshot = %#v, want empty graph rows", snapshot)
	}
}

func TestGreenfieldEmptyEligibleAcceptsOnlyScaffoldFiles(t *testing.T) {
	scaffoldRoot := t.TempDir()
	for _, path := range []string{
		"AGENTS.md",
		"README.md",
		".gitignore",
		".cognitionignore",
		filepath.Join(".git", "HEAD"),
		filepath.Join(".specify", "memory", "project-rules.md"),
		filepath.Join(".codex", "skills", "sp-plan", "SKILL.md"),
	} {
		fullPath := filepath.Join(scaffoldRoot, path)
		if err := os.MkdirAll(filepath.Dir(fullPath), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(fullPath, []byte("scaffold\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	if !GreenfieldEmptyEligible(scaffoldRoot) {
		t.Fatalf("scaffold-only root should be eligible")
	}

	nonScaffoldRoot := t.TempDir()
	if err := os.WriteFile(filepath.Join(nonScaffoldRoot, "README.md"), []byte("scaffold\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(nonScaffoldRoot, "src"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(nonScaffoldRoot, "src", "app.go"), []byte("package app\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if GreenfieldEmptyEligible(nonScaffoldRoot) {
		t.Fatalf("root with non-scaffold file should be ineligible")
	}
}

func TestGreenfieldEmptyEligibleRejectsMissingRoot(t *testing.T) {
	missingRoot := filepath.Join(t.TempDir(), "missing")
	if GreenfieldEmptyEligible(missingRoot) {
		t.Fatalf("missing root should be ineligible")
	}
}

func TestImportGenerationRefreshesBaselineKindAfterGreenfieldReady(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.InitializeGreenfieldEmpty(ctx); err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-brownfield")); err != nil {
		t.Fatal(err)
	}

	metadata, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != "GEN-brownfield" {
		t.Fatalf("active_generation_id = %q, want GEN-brownfield", metadata["active_generation_id"])
	}
	if metadata["baseline_kind"] != rt.BaselineKindBrownfieldFull {
		t.Fatalf("metadata baseline_kind = %q, want %q", metadata["baseline_kind"], rt.BaselineKindBrownfieldFull)
	}
	if metadata["graph_ready"] != "false" || metadata["baseline_state"] != "building" {
		t.Fatalf("metadata = %#v, want building brownfield metadata", metadata)
	}
}

func TestMarkRuntimeMetadataBlockedRefreshesBaselineKindAfterGreenfieldReady(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.InitializeGreenfieldEmpty(ctx); err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-brownfield")); err != nil {
		t.Fatal(err)
	}
	if err := st.MarkRuntimeMetadataBlocked(ctx, "GEN-brownfield"); err != nil {
		t.Fatal(err)
	}

	metadata, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != "GEN-brownfield" {
		t.Fatalf("active_generation_id = %q, want GEN-brownfield", metadata["active_generation_id"])
	}
	if metadata["baseline_kind"] != rt.BaselineKindBrownfieldFull {
		t.Fatalf("metadata baseline_kind = %q, want %q", metadata["baseline_kind"], rt.BaselineKindBrownfieldFull)
	}
	if metadata["graph_ready"] != "false" || metadata["baseline_state"] != "blocked" {
		t.Fatalf("metadata = %#v, want blocked brownfield metadata", metadata)
	}
}

func TestImportGenerationStoresAliasIndexRows(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	input := validImportInput("GEN-alias")
	input.Aliases = []AliasImport{{
		ID:              "ALIAS-app",
		Alias:           "App UI",
		NormalizedAlias: "app ui",
		TargetType:      "node",
		TargetID:        "N-app",
		EvidenceID:      "E-001",
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	rows, err := st.ActiveConceptCandidateRows(ctx, 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 1 {
		t.Fatalf("rows = %#v, want one row", rows)
	}
	if !conceptAliasContains(rows[0].Aliases, "App UI", "scan_alias") {
		t.Fatalf("Aliases = %#v, want App UI scan_alias", rows[0].Aliases)
	}
	if rows[0].Aliases[0].Confidence != "medium" {
		t.Fatalf("alias confidence = %q, want medium", rows[0].Aliases[0].Confidence)
	}

	var language, source, confidence string
	if err := st.DB().QueryRowContext(ctx, `SELECT language, source, confidence FROM alias_index WHERE id = ?`, "ALIAS-app").Scan(&language, &source, &confidence); err != nil {
		t.Fatal(err)
	}
	if language != "unknown" || source != "scan_alias" || confidence != "medium" {
		t.Fatalf("alias defaults = language:%q source:%q confidence:%q, want unknown scan_alias medium", language, source, confidence)
	}
}

func TestImportGenerationRejectsInvalidAliasReferences(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	tests := []struct {
		name    string
		alias   AliasImport
		wantErr string
	}{
		{
			name: "missing node",
			alias: AliasImport{
				ID:              "ALIAS-missing-node",
				Alias:           "Missing",
				NormalizedAlias: "missing",
				TargetType:      "node",
				TargetID:        "N-missing",
				Language:        "en",
				Source:          "scan_alias",
				Confidence:      "verified",
			},
			wantErr: "references missing node N-missing",
		},
		{
			name: "missing evidence",
			alias: AliasImport{
				ID:              "ALIAS-missing-evidence",
				Alias:           "App",
				NormalizedAlias: "app",
				TargetType:      "node",
				TargetID:        "N-app",
				Language:        "en",
				Source:          "scan_alias",
				Confidence:      "verified",
				EvidenceID:      "E-missing",
			},
			wantErr: "references missing evidence E-missing",
		},
		{
			name: "empty normalized alias",
			alias: AliasImport{
				ID:         "ALIAS-empty",
				Alias:      "App",
				TargetType: "node",
				TargetID:   "N-app",
				Language:   "en",
				Source:     "scan_alias",
				Confidence: "verified",
			},
			wantErr: "normalized_alias is required",
		},
		{
			name: "empty alias",
			alias: AliasImport{
				ID:              "ALIAS-empty-alias",
				Alias:           " ",
				NormalizedAlias: "app",
				TargetType:      "node",
				TargetID:        "N-app",
				Language:        "en",
				Source:          "scan_alias",
				Confidence:      "verified",
			},
			wantErr: "alias is required",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			input := validImportInput("GEN-" + tt.name)
			input.Aliases = []AliasImport{tt.alias}
			_, err := st.ImportGeneration(ctx, input)
			if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("err = %v, want %q", err, tt.wantErr)
			}
		})
	}
}

func TestActiveConceptCandidateRowsDeriveGraphMaterial(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	input := validImportInput("GEN-ui")
	input.Evidence = []EvidenceImport{{
		ID:          "E-gui",
		SourceKind:  "source",
		SourcePath:  "src/gui/window.tsx",
		CommitSHA:   "abc123",
		Extractor:   "test",
		ContentHash: "hash-gui",
	}}
	input.Nodes = []NodeImport{{
		ID:          "N-gui",
		Type:        "capability",
		Title:       "GUI Shell",
		Confidence:  "verified",
		EvidenceIDs: []string{"E-gui"},
		Attrs: map[string]any{
			"aliases":            []any{"GUI", "desktop UI"},
			"domain":             "desktop",
			"owner":              "frontend",
			"route_hints":        []any{"src/gui"},
			"verification_hints": []any{"npm test -- gui"},
		},
	}}
	input.Observations = []ObservationImport{{
		ID:              "OBS-gui",
		ObservationType: "summary",
		Summary:         "GUI Shell owns frame rendering and input dispatch.",
		EvidenceIDs:     []string{"E-gui"},
	}}
	input.PathIndex = []PathIndexImport{{
		ID:         "P-gui",
		Path:       "src/gui/window.tsx",
		NodeID:     "N-gui",
		Relation:   "owns",
		Confidence: "verified",
		EvidenceID: "E-gui",
	}}
	input.Aliases = []AliasImport{
		{
			ID:              "ALIAS-gui",
			Alias:           "GUI",
			NormalizedAlias: "gui",
			TargetType:      "node",
			TargetID:        "N-gui",
			Language:        "en",
			Source:          "scan_alias",
			Confidence:      "verified",
			EvidenceID:      "E-gui",
		},
		{
			ID:              "ALIAS-desktop-ui",
			Alias:           "desktop UI",
			NormalizedAlias: "desktop ui",
			TargetType:      "node",
			TargetID:        "N-gui",
			Language:        "en",
			Source:          "scan_alias",
			Confidence:      "verified",
			EvidenceID:      "E-gui",
		},
	}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	rows, err := st.ActiveConceptCandidateRows(ctx, 25)
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 1 {
		t.Fatalf("rows = %#v, want one candidate row", rows)
	}
	row := rows[0]
	if row.GenerationID != "GEN-ui" || row.NodeID != "N-gui" || row.Title != "GUI Shell" {
		t.Fatalf("row identity = %#v", row)
	}
	assertStringSliceContains(t, row.Paths, "src/gui/window.tsx")
	assertStringSliceContains(t, row.EvidenceIDs, "E-gui")
	assertStringSliceContains(t, row.EvidencePaths, "src/gui/window.tsx")
	assertStringSliceContains(t, row.ObservationSummaries, "GUI Shell owns frame rendering and input dispatch.")
	if !conceptAliasContains(row.Aliases, "GUI", "scan_alias") {
		t.Fatalf("Aliases = %#v, want GUI scan_alias", row.Aliases)
	}
	if !conceptAliasContains(row.Aliases, "desktop UI", "scan_alias") {
		t.Fatalf("Aliases = %#v, want desktop UI scan_alias", row.Aliases)
	}
}

func TestAllActiveConceptCandidateRowsReturnsUncappedUniverse(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	const totalNodes = 205
	input := validImportInput("GEN-wide")
	input.Evidence = make([]EvidenceImport, 0, totalNodes)
	input.Nodes = make([]NodeImport, 0, totalNodes)
	input.PathIndex = make([]PathIndexImport, 0, totalNodes)
	for i := 1; i <= totalNodes; i++ {
		nodeID := fmt.Sprintf("N-node-%03d", i)
		evidenceID := fmt.Sprintf("E-node-%03d", i)
		path := fmt.Sprintf("src/node/%03d.go", i)
		input.Evidence = append(input.Evidence, EvidenceImport{
			ID:          evidenceID,
			SourceKind:  "source",
			SourcePath:  path,
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: fmt.Sprintf("hash-node-%03d", i),
		})
		input.Nodes = append(input.Nodes, NodeImport{
			ID:          nodeID,
			Type:        "capability",
			Title:       fmt.Sprintf("Node %03d", i),
			Confidence:  "verified",
			EvidenceIDs: []string{evidenceID},
		})
		input.PathIndex = append(input.PathIndex, PathIndexImport{
			ID:         fmt.Sprintf("P-node-%03d", i),
			Path:       path,
			NodeID:     nodeID,
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: evidenceID,
		})
	}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	limitedRows, err := st.ActiveConceptCandidateRows(ctx, 0)
	if err != nil {
		t.Fatal(err)
	}
	if len(limitedRows) != 200 {
		t.Fatalf("ActiveConceptCandidateRows(ctx, 0) returned %d rows, want 200", len(limitedRows))
	}
	allRows, err := st.AllActiveConceptCandidateRows(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if len(allRows) != totalNodes {
		t.Fatalf("AllActiveConceptCandidateRows returned %d rows, want %d", len(allRows), totalNodes)
	}
}

func TestNodesForIDsUsesOnlyActiveGeneration(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-old")); err != nil {
		t.Fatal(err)
	}
	next := validImportInput("GEN-new")
	next.Nodes[0].Title = "Current App"
	if _, err := st.ImportGeneration(ctx, next); err != nil {
		t.Fatal(err)
	}

	nodes, err := st.NodesForIDs(ctx, []string{"N-app"})
	if err != nil {
		t.Fatal(err)
	}
	if len(nodes) != 1 || nodes[0]["title"] != "Current App" {
		t.Fatalf("nodes = %#v, want current active generation node", nodes)
	}
}

func TestImportGenerationPublishesOnlyProvisionalRuntimeMetadata(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-import")); err != nil {
		t.Fatal(err)
	}

	metadata, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != "GEN-import" {
		t.Fatalf("active_generation_id = %q, want GEN-import", metadata["active_generation_id"])
	}
	if metadata["graph_ready"] != "false" {
		t.Fatalf("graph_ready = %q, want false after import before sparse gates", metadata["graph_ready"])
	}
	if metadata["baseline_state"] == "fresh" {
		t.Fatalf("baseline_state = %q, want non-ready state after import before sparse gates", metadata["baseline_state"])
	}
	if _, ok := metadata["query_contract_version"]; ok {
		t.Fatalf("query_contract_version present after import before sparse gates: %#v", metadata)
	}
	if _, ok := metadata["update_contract_version"]; ok {
		t.Fatalf("update_contract_version present after import before sparse gates: %#v", metadata)
	}
}

func TestImportGenerationClearsPriorReadyContractMetadata(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-ready")); err != nil {
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(ctx, "GEN-ready", rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-next")); err != nil {
		t.Fatal(err)
	}

	metadata, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != "GEN-next" {
		t.Fatalf("active_generation_id = %q, want GEN-next", metadata["active_generation_id"])
	}
	if metadata["graph_ready"] != "false" || metadata["baseline_state"] == "fresh" {
		t.Fatalf("metadata = %#v, want non-ready metadata for newly imported generation", metadata)
	}
	if _, ok := metadata["query_contract_version"]; ok {
		t.Fatalf("query_contract_version present after replacement import: %#v", metadata)
	}
	if _, ok := metadata["update_contract_version"]; ok {
		t.Fatalf("update_contract_version present after replacement import: %#v", metadata)
	}
}

func TestPublishRuntimeMetadataRefusesGenerationMismatch(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-validated")); err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-current")); err != nil {
		t.Fatal(err)
	}

	_, _, err := st.PublishRuntimeMetadata(ctx, "GEN-validated", rt.BaselineKindBrownfieldFull)
	if err == nil {
		t.Fatal("PublishRuntimeMetadata error = nil, want generation mismatch error")
	}

	metadata, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != "GEN-current" {
		t.Fatalf("active_generation_id = %q, want GEN-current", metadata["active_generation_id"])
	}
	if metadata["graph_ready"] != "false" {
		t.Fatalf("graph_ready = %q, want false after refused ready publish", metadata["graph_ready"])
	}
	if _, ok := metadata["query_contract_version"]; ok {
		t.Fatalf("query_contract_version present after refused ready publish: %#v", metadata)
	}
	if _, ok := metadata["update_contract_version"]; ok {
		t.Fatalf("update_contract_version present after refused ready publish: %#v", metadata)
	}
}

func TestPublishRuntimeMetadataCommitsWhenStatusCallbackFails(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-ready")); err != nil {
		t.Fatal(err)
	}
	callbackErr := errors.New("status write failed")

	_, _, err := st.PublishRuntimeMetadata(ctx, "GEN-ready", rt.BaselineKindBrownfieldFull, func() error {
		return callbackErr
	})
	if !errors.Is(err, callbackErr) {
		t.Fatalf("PublishRuntimeMetadata error = %v, want callback error", err)
	}

	metadata, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != "GEN-ready" {
		t.Fatalf("active_generation_id = %q, want GEN-ready", metadata["active_generation_id"])
	}
	if metadata["graph_ready"] != "true" || metadata["baseline_state"] != "fresh" {
		t.Fatalf("metadata = %#v, want committed ready metadata after failed status callback", metadata)
	}
	if metadata["query_contract_version"] != "1" {
		t.Fatalf("query_contract_version = %q, want 1 after failed status callback", metadata["query_contract_version"])
	}
	if metadata["update_contract_version"] != "1" {
		t.Fatalf("update_contract_version = %q, want 1 after failed status callback", metadata["update_contract_version"])
	}
}

func TestPublishRuntimeMetadataDoesNotCallStatusCallbackWhenPostCommitGenerationChanges(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-ready")); err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(ctx, `
CREATE TRIGGER activate_generation_after_ready_metadata
AFTER UPDATE OF value_json ON metadata
WHEN NEW.key = 'graph_ready' AND NEW.value_json = 'true'
BEGIN
	INSERT INTO generations(id, sequence, kind, state, source_commit, started_at, published_at, superseded_at, attrs_json)
	VALUES('GEN-current', 9999, 'full', 'active', '', '2026-05-26T00:00:00Z', '2026-05-26T00:00:00Z', '', '{}');
	UPDATE generations SET state = 'superseded', superseded_at = '2026-05-26T00:00:00Z'
	WHERE id = 'GEN-ready';
END`); err != nil {
		t.Fatal(err)
	}
	called := false

	_, _, err := st.PublishRuntimeMetadata(ctx, "GEN-ready", rt.BaselineKindBrownfieldFull, func() error {
		called = true
		return nil
	})
	if err == nil || !strings.Contains(err.Error(), "active generation changed after ready metadata publication") {
		t.Fatalf("PublishRuntimeMetadata error = %v, want post-commit generation mismatch", err)
	}
	if called {
		t.Fatal("status callback was called after post-commit generation mismatch")
	}

	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "GEN-current" {
		t.Fatalf("activeID = %q, want GEN-current after trigger activation", activeID)
	}
	metadata, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != "GEN-ready" || metadata["graph_ready"] != "true" {
		t.Fatalf("metadata = %#v, want committed GEN-ready metadata without status callback", metadata)
	}
}

func TestMarkRuntimeMetadataBlockedCommitsWhenStatusCallbackFails(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-ready")); err != nil {
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(ctx, "GEN-ready", rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatal(err)
	}
	callbackErr := errors.New("blocked status write failed")

	err := st.MarkRuntimeMetadataBlocked(ctx, "GEN-ready", func() error {
		return callbackErr
	})
	if !errors.Is(err, callbackErr) {
		t.Fatalf("MarkRuntimeMetadataBlocked error = %v, want callback error", err)
	}

	metadata, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != "GEN-ready" {
		t.Fatalf("active_generation_id = %q, want GEN-ready", metadata["active_generation_id"])
	}
	if metadata["graph_ready"] != "false" || metadata["baseline_state"] != "blocked" {
		t.Fatalf("metadata = %#v, want committed blocked metadata after failed status callback", metadata)
	}
	if _, ok := metadata["query_contract_version"]; ok {
		t.Fatalf("query_contract_version present after committed blocked metadata: %#v", metadata)
	}
	if _, ok := metadata["update_contract_version"]; ok {
		t.Fatalf("update_contract_version present after committed blocked metadata: %#v", metadata)
	}
}

func TestMarkRuntimeMetadataBlockedRefusesGenerationMismatch(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-ready")); err != nil {
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(ctx, "GEN-ready", rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-current")); err != nil {
		t.Fatal(err)
	}

	err := st.MarkRuntimeMetadataBlocked(ctx, "GEN-ready")
	if err == nil {
		t.Fatal("MarkRuntimeMetadataBlocked error = nil, want generation mismatch error")
	}

	metadata, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != "GEN-current" {
		t.Fatalf("active_generation_id = %q, want GEN-current", metadata["active_generation_id"])
	}
	if metadata["graph_ready"] != "false" {
		t.Fatalf("graph_ready = %q, want unchanged non-ready current generation metadata", metadata["graph_ready"])
	}
}

func TestMarkRuntimeMetadataBlockedDoesNotCallStatusCallbackWhenPostCommitGenerationChanges(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-ready")); err != nil {
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(ctx, "GEN-ready", rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(ctx, `
CREATE TRIGGER activate_generation_after_blocked_metadata
AFTER UPDATE OF value_json ON metadata
WHEN NEW.key = 'graph_ready' AND NEW.value_json = 'false'
BEGIN
	INSERT INTO generations(id, sequence, kind, state, source_commit, started_at, published_at, superseded_at, attrs_json)
	VALUES('GEN-current', 9999, 'full', 'active', '', '2026-05-26T00:00:00Z', '2026-05-26T00:00:00Z', '', '{}');
	UPDATE generations SET state = 'superseded', superseded_at = '2026-05-26T00:00:00Z'
	WHERE id = 'GEN-ready';
END`); err != nil {
		t.Fatal(err)
	}
	called := false

	err := st.MarkRuntimeMetadataBlocked(ctx, "GEN-ready", func() error {
		called = true
		return nil
	})
	if err == nil || !strings.Contains(err.Error(), "active generation changed after blocked metadata publication") {
		t.Fatalf("MarkRuntimeMetadataBlocked error = %v, want post-commit generation mismatch", err)
	}
	if called {
		t.Fatal("status callback was called after post-commit generation mismatch")
	}

	metadata, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != "GEN-ready" {
		t.Fatalf("active_generation_id = %q, want GEN-ready", metadata["active_generation_id"])
	}
	if metadata["graph_ready"] != "false" || metadata["baseline_state"] != "blocked" {
		t.Fatalf("metadata = %#v, want committed blocked metadata without status callback", metadata)
	}
	if _, ok := metadata["query_contract_version"]; ok {
		t.Fatalf("query_contract_version present after committed blocked metadata: %#v", metadata)
	}
}

func TestImportGenerationRollsBackOnInvalidEdge(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	_, err := st.ImportGeneration(ctx, ImportInput{
		GenerationID: "GEN-bad",
		Edges: []EdgeImport{{
			ID:       "EDGE-bad",
			Type:     "owns",
			SourceID: "N-missing-source",
			TargetID: "N-missing-target",
		}},
	})
	if err == nil {
		t.Fatal("ImportGeneration error = nil, want invalid edge error")
	}
	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "" {
		t.Fatalf("activeID = %q, want empty after rollback", activeID)
	}
}

func TestImportGenerationRollsBackOnInvalidNodeEvidence(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	_, err := st.ImportGeneration(ctx, ImportInput{
		GenerationID: "GEN-bad-node-evidence",
		Nodes: []NodeImport{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "App",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-missing"},
		}},
	})
	if err == nil {
		t.Fatal("ImportGeneration error = nil, want invalid node evidence error")
	}
	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "" {
		t.Fatalf("activeID = %q, want empty after rollback", activeID)
	}
}

func TestImportGenerationRollsBackInvalidPathIndexAndPreservesActiveGeneration(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-active")); err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name      string
		pathIndex PathIndexImport
	}{
		{
			name: "missing node",
			pathIndex: PathIndexImport{
				ID:         "P-missing-node",
				Path:       "src/app.go",
				NodeID:     "N-missing",
				Relation:   "owns",
				Confidence: "verified",
				EvidenceID: "E-002",
			},
		},
		{
			name: "missing evidence",
			pathIndex: PathIndexImport{
				ID:         "P-missing-evidence",
				Path:       "src/app.go",
				NodeID:     "N-app-2",
				Relation:   "owns",
				Confidence: "verified",
				EvidenceID: "E-missing",
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := st.ImportGeneration(ctx, ImportInput{
				GenerationID: "GEN-bad-path-" + tt.name,
				Evidence: []EvidenceImport{{
					ID:          "E-002",
					SourcePath:  "src/app.go",
					SourceKind:  "source",
					CommitSHA:   "abc123",
					Extractor:   "test",
					ContentHash: "hash-app",
				}},
				Nodes: []NodeImport{{
					ID:         "N-app-2",
					Type:       "capability",
					Title:      "App",
					Confidence: "verified",
				}},
				PathIndex: []PathIndexImport{tt.pathIndex},
			})
			if err == nil {
				t.Fatal("ImportGeneration error = nil, want invalid path_index reference error")
			}
			activeID, err := st.ActiveGenerationID(ctx)
			if err != nil {
				t.Fatal(err)
			}
			if activeID != "GEN-active" {
				t.Fatalf("activeID = %q, want GEN-active after rollback", activeID)
			}
		})
	}
}

func TestImportGenerationAllowsEmptyPathIndexEvidence(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	input := validImportInput("GEN-empty-path-evidence")
	input.PathIndex[0].EvidenceID = ""
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}
	snapshot, err := st.ActiveIdentitySnapshot(ctx)
	if err != nil {
		t.Fatal(err)
	}
	assertSnapshotIdentity(t, snapshot.CoveragePaths, "src/app.go")

	var evidenceID string
	if err := st.DB().QueryRowContext(ctx, `SELECT evidence_id FROM path_index WHERE id = ?`, input.PathIndex[0].ID).Scan(&evidenceID); err != nil {
		t.Fatal(err)
	}
	if evidenceID != "" {
		t.Fatalf("path_index evidence_id = %q, want empty", evidenceID)
	}
}

func TestImportGenerationAllowsStableRowIDsAcrossGenerations(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-active")); err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-next")); err != nil {
		t.Fatal(err)
	}

	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "GEN-next" {
		t.Fatalf("activeID = %q, want GEN-next", activeID)
	}
	snapshot, err := st.ActiveIdentitySnapshot(ctx)
	if err != nil {
		t.Fatal(err)
	}
	assertSnapshotIdentity(t, snapshot.Evidence, "E-001|src/app.go|hash-app")
	assertSnapshotIdentity(t, snapshot.Nodes, "N-app")
	assertSnapshotIdentity(t, snapshot.CoveragePaths, "src/app.go")

	var activeOldCount int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM generations WHERE id = ? AND state = 'active'`, "GEN-active").Scan(&activeOldCount); err != nil {
		t.Fatal(err)
	}
	if activeOldCount != 0 {
		t.Fatalf("GEN-active active count = %d, want 0", activeOldCount)
	}
}

func TestImportGenerationStableIDFailurePreservesPriorActiveGeneration(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-active")); err != nil {
		t.Fatal(err)
	}
	input := validImportInput("GEN-next")
	input.PathIndex[0].EvidenceID = "E-missing"
	_, err := st.ImportGeneration(ctx, input)
	if err == nil {
		t.Fatal("ImportGeneration error = nil, want invalid path_index evidence error")
	}

	activeID, err := st.ActiveGenerationID(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "GEN-active" {
		t.Fatalf("activeID = %q, want GEN-active after rollback", activeID)
	}
	snapshot, err := st.ActiveIdentitySnapshot(ctx)
	if err != nil {
		t.Fatal(err)
	}
	assertSnapshotIdentity(t, snapshot.Evidence, "E-001|src/app.go|hash-app")
	assertSnapshotIdentity(t, snapshot.Nodes, "N-app")
	assertSnapshotIdentity(t, snapshot.CoveragePaths, "src/app.go")
}

func TestImportGenerationRollsBackOnInvalidEdgeOrObservationEvidence(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	tests := []struct {
		name  string
		input ImportInput
	}{
		{
			name: "edge evidence",
			input: ImportInput{
				GenerationID: "GEN-bad-edge-evidence",
				Nodes: []NodeImport{
					{ID: "N-source", Type: "capability", Title: "Source", Confidence: "verified"},
					{ID: "N-target", Type: "capability", Title: "Target", Confidence: "verified"},
				},
				Edges: []EdgeImport{{
					ID:          "EDGE-bad",
					Type:        "owns",
					SourceID:    "N-source",
					TargetID:    "N-target",
					Confidence:  "verified",
					EvidenceIDs: []string{"E-missing"},
				}},
			},
		},
		{
			name: "observation evidence",
			input: ImportInput{
				GenerationID: "GEN-bad-observation-evidence",
				Observations: []ObservationImport{{
					ID:              "OBS-bad",
					ObservationType: "summary",
					Summary:         "Bad evidence",
					EvidenceIDs:     []string{"E-missing"},
				}},
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := st.ImportGeneration(ctx, tt.input)
			if err == nil {
				t.Fatal("ImportGeneration error = nil, want invalid evidence error")
			}
			activeID, err := st.ActiveGenerationID(ctx)
			if err != nil {
				t.Fatal(err)
			}
			if activeID != "" {
				t.Fatalf("activeID = %q, want empty after rollback", activeID)
			}
		})
	}
}

func TestImportGenerationStoresRejectionsInGenerationAttrs(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	_, err := st.ImportGeneration(ctx, ImportInput{
		GenerationID: "GEN-rejections",
		Rejections: []RowDecision{{
			Category: "coverage",
			Identity: "docs/missing.md",
			Reason:   "no_node_relation",
		}},
	})
	if err != nil {
		t.Fatal(err)
	}

	var attrsJSON string
	if err := st.DB().QueryRowContext(ctx, `SELECT attrs_json FROM generations WHERE id = ?`, "GEN-rejections").Scan(&attrsJSON); err != nil {
		t.Fatal(err)
	}
	var attrs struct {
		Rejections []RowDecision `json:"rejections"`
	}
	if err := json.Unmarshal([]byte(attrsJSON), &attrs); err != nil {
		t.Fatal(err)
	}
	if len(attrs.Rejections) != 1 || attrs.Rejections[0].Reason != "no_node_relation" {
		t.Fatalf("attrs rejections = %#v, want top-level no_node_relation rejection", attrs.Rejections)
	}
}

func openImportTestStore(t *testing.T) *Store {
	t.Helper()
	paths := testPaths(t)
	st, err := Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	return st
}

func testPaths(t *testing.T) rt.Paths {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	return paths
}

func validImportInput(generationID string) ImportInput {
	return ImportInput{
		GenerationID: generationID,
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []EvidenceImport{{
			ID:          "E-001",
			SourcePath:  "src/app.go",
			SourceKind:  "source",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-app",
		}},
		Nodes: []NodeImport{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "App",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-001"},
		}},
		PathIndex: []PathIndexImport{{
			ID:         "P-src-app-go",
			Path:       "src/app.go",
			NodeID:     "N-app",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-001",
		}},
	}
}

func assertSnapshotIdentity(t *testing.T, identities map[string]bool, identity string) {
	t.Helper()
	if !identities[identity] {
		t.Fatalf("identity %q missing from %#v", identity, identities)
	}
}

func assertStringSliceContains(t *testing.T, values []string, want string) {
	t.Helper()
	for _, value := range values {
		if value == want {
			return
		}
	}
	t.Fatalf("%#v does not contain %q", values, want)
}

func conceptAliasContains(rows []ConceptAliasRow, alias string, source string) bool {
	for _, row := range rows {
		if row.Alias == alias && row.Source == source {
			return true
		}
	}
	return false
}

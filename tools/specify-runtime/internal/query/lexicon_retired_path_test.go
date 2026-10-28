package query

import (
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestLexiconSuppressesRetiredPathOnlyRenameEndpoints(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-r4-rename",
		Kind:         "full",
		SourceCommit: "fixture",
		Evidence: []store.EvidenceImport{
			{ID: "E-old-owner", SourceKind: "file", SourcePath: "src/old.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "old-owner"},
			{ID: "E-old-test", SourceKind: "file", SourcePath: "src/old_owner_test.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "old-test"},
			{ID: "E-app", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "app"},
			{ID: "E-renamed-owner", SourceKind: "file", SourcePath: "src/renamed-owner.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "renamed-owner"},
			{ID: "E-renamed-test", SourceKind: "file", SourcePath: "src/renamed_owner_test.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "renamed-test"},
			{ID: "E-root-old-owner", SourceKind: "file", SourcePath: "old.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "root-old-owner"},
			{ID: "E-root-old-test", SourceKind: "file", SourcePath: "old_root_test.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "root-old-test"},
			{ID: "E-root-renamed-owner", SourceKind: "file", SourcePath: "renamed-root.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "root-renamed-owner"},
			{ID: "E-root-renamed-test", SourceKind: "file", SourcePath: "renamed_root_test.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "root-renamed-test"},
			{ID: "E-multi-old", SourceKind: "file", SourcePath: "src/multi-old.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "multi-old"},
			{ID: "E-multi-current", SourceKind: "file", SourcePath: "src/multi-current.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "multi-current"},
		},
		Nodes: []store.NodeImport{
			{ID: "N-old-owner", Type: "capability", Title: "src/old.go", Confidence: "verified", EvidenceIDs: []string{"E-old-owner"}},
			{ID: "N-old-test", Type: "capability", Title: "src/old_owner_test.go", Confidence: "verified", EvidenceIDs: []string{"E-old-test"}},
			{ID: "N-app", Type: "capability", Title: "src/app.go", Confidence: "verified", EvidenceIDs: []string{"E-app"}},
			{ID: "N-renamed-owner", Type: "component", Title: "R4 V6 Renamed Owner", Confidence: "supported", EvidenceIDs: []string{"E-renamed-owner"}},
			{ID: "N-renamed-test", Type: "verification", Title: "R4 V6 Renamed Verification", Confidence: "supported", EvidenceIDs: []string{"E-renamed-test"}},
			{ID: "N-root-old-owner", Type: "capability", Title: "old.go", Confidence: "verified", EvidenceIDs: []string{"E-root-old-owner"}},
			{ID: "N-root-old-test", Type: "capability", Title: "old_root_test.go", Confidence: "verified", EvidenceIDs: []string{"E-root-old-test"}},
			{ID: "N-root-renamed-owner", Type: "component", Title: "R4 V8 Root Renamed Owner", Confidence: "supported", EvidenceIDs: []string{"E-root-renamed-owner"}},
			{ID: "N-root-renamed-test", Type: "verification", Title: "R4 V8 Root Renamed Verification", Confidence: "supported", EvidenceIDs: []string{"E-root-renamed-test"}},
			{ID: "N-multi", Type: "component", Title: "Multi Path Owner", Confidence: "verified", EvidenceIDs: []string{"E-multi-old", "E-multi-current"}},
			{ID: "N-abstract", Type: "capability", Title: "Abstract Owner", Confidence: "verified", EvidenceIDs: []string{"E-old-owner"}},
		},
		Aliases: []store.AliasImport{
			{ID: "A-old-owner-id", Alias: "N-old-owner", NormalizedAlias: "n-old-owner", TargetType: "node", TargetID: "N-old-owner", Source: "scoped_registration_retirement_retained_node_id", Confidence: "partial"},
			{ID: "A-old-test-id", Alias: "N-old-test", NormalizedAlias: "n-old-test", TargetType: "node", TargetID: "N-old-test", Source: "scoped_registration_retirement_retained_node_id", Confidence: "partial"},
			{ID: "A-renamed-owner", Alias: "R4 V6 Renamed Owner", NormalizedAlias: "r4 v6 renamed owner", TargetType: "node", TargetID: "N-renamed-owner", Source: "scoped_registration", Confidence: "supported", EvidenceID: "E-renamed-owner"},
			{ID: "A-renamed-test", Alias: "R4 V6 Renamed Verification", NormalizedAlias: "r4 v6 renamed verification", TargetType: "node", TargetID: "N-renamed-test", Source: "scoped_registration", Confidence: "supported", EvidenceID: "E-renamed-test"},
			{ID: "A-root-old-owner-id", Alias: "N-root-old-owner", NormalizedAlias: "n-root-old-owner", TargetType: "node", TargetID: "N-root-old-owner", Source: "scoped_registration_retirement_retained_node_id", Confidence: "partial"},
			{ID: "A-root-old-test-id", Alias: "N-root-old-test", NormalizedAlias: "n-root-old-test", TargetType: "node", TargetID: "N-root-old-test", Source: "scoped_registration_retirement_retained_node_id", Confidence: "partial"},
			{ID: "A-root-renamed-owner", Alias: "R4 V8 Root Renamed Owner", NormalizedAlias: "r4 v8 root renamed owner", TargetType: "node", TargetID: "N-root-renamed-owner", Source: "scoped_registration", Confidence: "supported", EvidenceID: "E-root-renamed-owner"},
			{ID: "A-root-renamed-test", Alias: "R4 V8 Root Renamed Verification", NormalizedAlias: "r4 v8 root renamed verification", TargetType: "node", TargetID: "N-root-renamed-test", Source: "scoped_registration", Confidence: "supported", EvidenceID: "E-root-renamed-test"},
		},
		PathIndex: []store.PathIndexImport{
			{ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-app"},
			{ID: "P-renamed-owner", Path: "src/renamed-owner.go", NodeID: "N-renamed-owner", Relation: "owns", Confidence: "supported", EvidenceID: "E-renamed-owner"},
			{ID: "P-renamed-test", Path: "src/renamed_owner_test.go", NodeID: "N-renamed-test", Relation: "verifies", Confidence: "supported", EvidenceID: "E-renamed-test"},
			{ID: "P-root-renamed-owner", Path: "renamed-root.go", NodeID: "N-root-renamed-owner", Relation: "owns", Confidence: "supported", EvidenceID: "E-root-renamed-owner"},
			{ID: "P-root-renamed-test", Path: "renamed_root_test.go", NodeID: "N-root-renamed-test", Relation: "verifies", Confidence: "supported", EvidenceID: "E-root-renamed-test"},
			{ID: "P-multi-current", Path: "src/multi-current.go", NodeID: "N-multi", Relation: "owns", Confidence: "verified", EvidenceID: "E-multi-current"},
		},
	})

	for _, query := range []string{"src/old.go", "src/old_owner_test.go", "old.go", "old_root_test.go", `src\old.go`, "./old.go"} {
		payload, err := LexiconWithOptions(paths, LexiconInput{Intent: "debug", Query: query, Limit: 20, Mode: "catalog"})
		if err != nil {
			t.Fatal(err)
		}
		assertLexiconNodeAbsent(t, payload.ConceptCandidates, "N-old-owner")
		assertLexiconNodeAbsent(t, payload.ConceptCandidates, "N-old-test")
		assertLexiconNodeAbsent(t, payload.ConceptCandidates, "N-root-old-owner")
		assertLexiconNodeAbsent(t, payload.ConceptCandidates, "N-root-old-test")
		assertLexiconNodeAbsent(t, payload.AliasCatalog, "N-old-owner")
		assertLexiconNodeAbsent(t, payload.AliasCatalog, "N-old-test")
		assertLexiconNodeAbsent(t, payload.AliasCatalog, "N-root-old-owner")
		assertLexiconNodeAbsent(t, payload.AliasCatalog, "N-root-old-test")
		assertLexiconPathAbsent(t, payload.AliasCatalog, query)
	}

	payload, err := LexiconWithOptions(paths, LexiconInput{Intent: "debug", Query: "renamed", Limit: 20, Mode: "catalog"})
	if err != nil {
		t.Fatal(err)
	}
	assertLexiconNodePresent(t, payload.AliasCatalog, "N-renamed-owner", "src/renamed-owner.go")
	assertLexiconNodePresent(t, payload.AliasCatalog, "N-renamed-test", "src/renamed_owner_test.go")
	assertLexiconNodePresent(t, payload.AliasCatalog, "N-root-renamed-owner", "renamed-root.go")
	assertLexiconNodePresent(t, payload.AliasCatalog, "N-root-renamed-test", "renamed_root_test.go")
	assertLexiconNodePresent(t, payload.AliasCatalog, "N-multi", "src/multi-current.go")
	assertLexiconPathAbsent(t, payload.AliasCatalog, "src/multi-old.go")
	assertLexiconNodePresent(t, payload.AliasCatalog, "N-abstract", "")
}

func TestLexiconEmptyCatalogPaginatesAcrossRetiredPathHoles(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-r4-catalog-holes",
		Kind:         "full",
		SourceCommit: "fixture",
		Evidence: []store.EvidenceImport{
			{ID: "E-retired-root", SourceKind: "file", SourcePath: "old.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "old"},
			{ID: "E-retired-src", SourceKind: "file", SourcePath: "src/old.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "src-old"},
			{ID: "E-active-a", SourceKind: "file", SourcePath: "a.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "a"},
			{ID: "E-active-b", SourceKind: "file", SourcePath: "b.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "b"},
			{ID: "E-active-c", SourceKind: "file", SourcePath: "c.go", CommitSHA: "fixture", Extractor: "test", ContentHash: "c"},
		},
		Nodes: []store.NodeImport{
			{ID: "N-001-retired-root", Type: "capability", Title: "old.go", Confidence: "verified", EvidenceIDs: []string{"E-retired-root"}},
			{ID: "N-002-active-a", Type: "capability", Title: "Active A", Confidence: "verified", EvidenceIDs: []string{"E-active-a"}},
			{ID: "N-003-retired-src", Type: "capability", Title: "src/old.go", Confidence: "verified", EvidenceIDs: []string{"E-retired-src"}},
			{ID: "N-004-active-b", Type: "capability", Title: "Active B", Confidence: "verified", EvidenceIDs: []string{"E-active-b"}},
			{ID: "N-005-active-c", Type: "capability", Title: "Active C", Confidence: "verified", EvidenceIDs: []string{"E-active-c"}},
		},
		Aliases: []store.AliasImport{
			{ID: "A-retired-root", Alias: "N-001-retired-root", NormalizedAlias: "n-001-retired-root", TargetType: "node", TargetID: "N-001-retired-root", Source: "retained", Confidence: "partial"},
			{ID: "A-retired-src", Alias: "N-003-retired-src", NormalizedAlias: "n-003-retired-src", TargetType: "node", TargetID: "N-003-retired-src", Source: "retained", Confidence: "partial"},
		},
		PathIndex: []store.PathIndexImport{
			{ID: "P-active-a", Path: "a.go", NodeID: "N-002-active-a", Relation: "owns", Confidence: "verified", EvidenceID: "E-active-a"},
			{ID: "P-active-b", Path: "b.go", NodeID: "N-004-active-b", Relation: "owns", Confidence: "verified", EvidenceID: "E-active-b"},
			{ID: "P-active-c", Path: "c.go", NodeID: "N-005-active-c", Relation: "owns", Confidence: "verified", EvidenceID: "E-active-c"},
		},
	})

	first, err := LexiconWithOptions(paths, LexiconInput{Intent: "debug", Mode: "catalog", Limit: 2})
	if err != nil {
		t.Fatal(err)
	}
	if first.AliasCatalogCount != 3 || first.CatalogPage == nil || !first.CatalogPage.HasMore || first.CatalogPage.NextOffset == nil || *first.CatalogPage.NextOffset != 2 {
		t.Fatalf("first catalog page = count:%d page:%#v", first.AliasCatalogCount, first.CatalogPage)
	}
	assertLexiconNodePresent(t, first.AliasCatalog, "N-002-active-a", "a.go")
	assertLexiconNodePresent(t, first.AliasCatalog, "N-004-active-b", "b.go")
	assertLexiconNodeAbsent(t, first.AliasCatalog, "N-001-retired-root")
	assertLexiconNodeAbsent(t, first.AliasCatalog, "N-003-retired-src")

	second, err := LexiconWithOptions(paths, LexiconInput{Intent: "debug", Mode: "catalog", Limit: 2, Offset: *first.CatalogPage.NextOffset, CatalogRevision: first.CatalogPage.Revision})
	if err != nil {
		t.Fatal(err)
	}
	if second.AliasCatalogCount != 3 || second.CatalogPage == nil || second.CatalogPage.HasMore || len(second.AliasCatalog) != 1 {
		t.Fatalf("second catalog page = count:%d rows:%#v page:%#v", second.AliasCatalogCount, second.AliasCatalog, second.CatalogPage)
	}
	assertLexiconNodePresent(t, second.AliasCatalog, "N-005-active-c", "c.go")
}

func assertLexiconNodeAbsent(t *testing.T, rows []map[string]any, nodeID string) {
	t.Helper()
	for _, row := range rows {
		if row["node_id"] == nodeID {
			t.Fatalf("lexicon row still exposes retired node %s: %#v", nodeID, row)
		}
	}
}

func assertLexiconNodePresent(t *testing.T, rows []map[string]any, nodeID, wantPath string) {
	t.Helper()
	for _, row := range rows {
		if row["node_id"] != nodeID {
			continue
		}
		if wantPath != "" && !mapStringSliceContains(row["path_hints"], wantPath) {
			t.Fatalf("lexicon row %s path_hints = %#v, want %s", nodeID, row["path_hints"], wantPath)
		}
		return
	}
	t.Fatalf("lexicon rows missing node %s: %#v", nodeID, rows)
}

func assertLexiconPathAbsent(t *testing.T, rows []map[string]any, path string) {
	t.Helper()
	for _, row := range rows {
		if mapStringSliceContains(row["path_hints"], path) || mapStringSliceContains(row["paths"], path) {
			t.Fatalf("lexicon row exposes retired path %s: %#v", path, row)
		}
	}
}

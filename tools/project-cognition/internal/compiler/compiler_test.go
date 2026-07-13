package compiler

import (
	"encoding/json"
	"reflect"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
)

func TestCompileLegacyProposalIsDeterministicAcrossInputOrdering(t *testing.T) {
	first := legacyPackageFixture()
	second := legacyPackageFixture()
	second.Evidence[0], second.Evidence[1] = second.Evidence[1], second.Evidence[0]
	second.Nodes[0], second.Nodes[1] = second.Nodes[1], second.Nodes[0]
	second.Edges[0].EvidenceIDs = []string{"E-worker", "E-app"}
	second.CoveragePaths = []string{"src/worker.go", "src/app.go"}

	compiledFirst, resultFirst := Compile(AdaptLegacy(first))
	compiledSecond, resultSecond := Compile(AdaptLegacy(second))

	if !resultFirst.PublicationAllowed || !resultSecond.PublicationAllowed {
		t.Fatalf("publication_allowed = (%v, %v), want true; conflicts=(%v, %v)", resultFirst.PublicationAllowed, resultSecond.PublicationAllowed, resultFirst.Conflicts, resultSecond.Conflicts)
	}
	if resultFirst.ProposalFingerprint == "" || resultFirst.CompiledFingerprint == "" {
		t.Fatal("fingerprints must be present")
	}
	if resultFirst.ProposalFingerprint != resultSecond.ProposalFingerprint {
		t.Fatalf("proposal fingerprints differ: %q != %q", resultFirst.ProposalFingerprint, resultSecond.ProposalFingerprint)
	}
	if resultFirst.CompiledFingerprint != resultSecond.CompiledFingerprint {
		t.Fatalf("compiled fingerprints differ: %q != %q", resultFirst.CompiledFingerprint, resultSecond.CompiledFingerprint)
	}
	if !reflect.DeepEqual(compiledFirst.Package, compiledSecond.Package) {
		t.Fatalf("compiled packages differ:\nfirst=%#v\nsecond=%#v", compiledFirst.Package, compiledSecond.Package)
	}
}

func TestCompileMergesEquivalentRowsAndRecordsDecision(t *testing.T) {
	pkg := legacyPackageFixture()
	pkg.Nodes = append(pkg.Nodes, pkg.Nodes[0])

	compiled, result := Compile(AdaptLegacy(pkg))

	if !result.PublicationAllowed {
		t.Fatalf("publication_allowed = false; conflicts=%v", result.Conflicts)
	}
	if len(compiled.Package.Nodes) != 2 {
		t.Fatalf("compiled node count = %d, want 2", len(compiled.Package.Nodes))
	}
	if len(result.MergeRecords) != 1 {
		t.Fatalf("merge_records = %#v, want one equivalent duplicate decision", result.MergeRecords)
	}
	if got := result.MergeRecords[0]; got.Category != "node" || got.SourceIdentity != "N-app" || got.TargetIdentity != "N-app" || got.Reason != "duplicate_equivalent" {
		t.Fatalf("merge record = %#v, want equivalent N-app merge", got)
	}
}

func TestCompileBlocksConflictingIdentityAndMissingReferences(t *testing.T) {
	tests := []struct {
		name       string
		mutate     func(*scanartifacts.Package)
		wantReason string
	}{
		{
			name: "conflicting duplicate node",
			mutate: func(pkg *scanartifacts.Package) {
				conflict := pkg.Nodes[0]
				conflict.Title = "Different App"
				pkg.Nodes = append(pkg.Nodes, conflict)
			},
			wantReason: "identity_conflict",
		},
		{
			name: "missing evidence",
			mutate: func(pkg *scanartifacts.Package) {
				pkg.Nodes[0].EvidenceIDs = []string{"E-missing"}
			},
			wantReason: "missing_evidence:E-missing",
		},
		{
			name: "orphan edge",
			mutate: func(pkg *scanartifacts.Package) {
				pkg.Edges[0].TargetID = "N-missing"
			},
			wantReason: "missing_target_node:N-missing",
		},
		{
			name: "internal runtime path",
			mutate: func(pkg *scanartifacts.Package) {
				pkg.Nodes[0].Paths = append(pkg.Nodes[0].Paths, ".specify/private.json")
			},
			wantReason: "reserved_runtime_path",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			pkg := legacyPackageFixture()
			tt.mutate(&pkg)

			_, result := Compile(AdaptLegacy(pkg))

			if result.PublicationAllowed {
				t.Fatalf("publication_allowed = true, want false; result=%#v", result)
			}
			if result.Status != "blocked" {
				t.Fatalf("status = %q, want blocked", result.Status)
			}
			if !hasDecisionReason(result.Conflicts, tt.wantReason) {
				t.Fatalf("conflicts = %#v, want reason %q", result.Conflicts, tt.wantReason)
			}
		})
	}
}

func TestCompileResultHasCompactStableJSONContract(t *testing.T) {
	_, result := Compile(AdaptLegacy(legacyPackageFixture()))
	encoded, err := json.Marshal(result)
	if err != nil {
		t.Fatal(err)
	}
	var payload map[string]any
	if err := json.Unmarshal(encoded, &payload); err != nil {
		t.Fatal(err)
	}
	for _, field := range []string{"contract_version", "status", "proposal_id", "proposal_fingerprint", "compiled_fingerprint", "counts", "merge_records", "rejections", "conflicts", "unknowns", "publication_allowed"} {
		if _, ok := payload[field]; !ok {
			t.Fatalf("compiled result JSON missing %q: %s", field, encoded)
		}
	}
}

func hasDecisionReason(decisions []Decision, reason string) bool {
	for _, decision := range decisions {
		if decision.Reason == reason {
			return true
		}
	}
	return false
}

func legacyPackageFixture() scanartifacts.Package {
	return scanartifacts.Package{
		Evidence: []scanartifacts.EvidenceRow{
			{ID: "E-app", SourceKind: "source", SourcePath: "src/app.go", ContentHash: "hash-app"},
			{ID: "E-worker", SourceKind: "source", SourcePath: "src/worker.go", ContentHash: "hash-worker"},
		},
		Nodes: []scanartifacts.NodeRow{
			{ID: "N-app", Type: "capability", Title: "App", Confidence: "high", Paths: []string{"src/app.go"}, CanonicalPaths: []string{"src/app.go"}, EvidenceIDs: []string{"E-app"}},
			{ID: "N-worker", Type: "capability", Title: "Worker", Confidence: "medium", Paths: []string{"src/worker.go"}, CanonicalPaths: []string{"src/worker.go"}, EvidenceIDs: []string{"E-worker"}},
		},
		Edges: []scanartifacts.EdgeRow{
			{ID: "EDGE-app-worker", Type: "calls", SourceID: "N-app", TargetID: "N-worker", Confidence: "medium", EvidenceIDs: []string{"E-app", "E-worker"}},
		},
		Observations: []scanartifacts.ObservationRow{
			{ID: "OBS-app", ObservationType: "note", Summary: "App delegates work", EvidenceIDs: []string{"E-worker"}},
		},
		CoveragePaths: []string{"src/app.go", "src/worker.go"},
		AcceptedGaps:  map[string]bool{},
	}
}

package compiler

import (
	"encoding/json"
	"reflect"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
)

func TestCompileCanonicalizesAndDerivesTypedGraphClaims(t *testing.T) {
	pkg := legacyPackageFixture()
	pkg.Claims = []scanartifacts.ClaimRow{
		{
			ID:                    "claim:verified",
			NodeID:                "N-app",
			GraphClaimType:        "runtime_owner",
			Summary:               "App owns runtime behavior",
			RequestedState:        claim.StateCandidate,
			SupportingEvidenceIDs: []string{"E-app"},
			Verifications: []claim.Verification{{
				ID: "verification:owner", Result: claim.VerificationPassed, EvidenceID: "E-app", ObservedAt: "2026-07-13T10:00:00Z",
			}},
		},
		{
			ID:             "claim:agent-certified",
			NodeID:         "N-worker",
			GraphClaimType: "entrypoint",
			Summary:        "Agent requested verification without evidence",
			RequestedState: claim.StateVerified,
		},
	}

	compiled, result := Compile(AdaptLegacy(pkg))
	if !result.PublicationAllowed {
		t.Fatalf("publication_allowed = false; conflicts=%#v", result.Conflicts)
	}
	if result.Counts["claims"] != 2 || len(compiled.Package.Claims) != 2 {
		t.Fatalf("claim counts = %#v/%d, want 2", result.Counts, len(compiled.Package.Claims))
	}
	if got := compiled.Package.Claims[0]; got.ID != "claim:agent-certified" || got.State != claim.StateCandidate || got.Freshness != claim.FreshnessUnknown {
		t.Fatalf("first compiled claim = %#v, want canonical candidate that ignores requested verified", got)
	}
	if got := compiled.Package.Claims[1]; got.ID != "claim:verified" || got.State != claim.StateVerified || got.Freshness != claim.FreshnessFresh {
		t.Fatalf("second compiled claim = %#v, want verified-in-graph-generation", got)
	}

	reversed := legacyPackageFixture()
	reversed.Claims = []scanartifacts.ClaimRow{pkg.Claims[1], pkg.Claims[0]}
	_, reversedResult := Compile(AdaptLegacy(reversed))
	if result.ProposalFingerprint != reversedResult.ProposalFingerprint || result.CompiledFingerprint != reversedResult.CompiledFingerprint {
		t.Fatalf("claim input ordering changed fingerprints: %#v != %#v", result, reversedResult)
	}
}

func TestCompileBlocksGraphClaimWithMissingReferences(t *testing.T) {
	pkg := legacyPackageFixture()
	pkg.Claims = []scanartifacts.ClaimRow{{
		ID:                    "claim:broken",
		NodeID:                "N-missing",
		GraphClaimType:        "runtime_owner",
		Summary:               "Broken claim",
		SupportingEvidenceIDs: []string{"E-missing"},
	}}

	_, result := Compile(AdaptLegacy(pkg))
	if result.PublicationAllowed {
		t.Fatalf("publication_allowed = true, want false; result=%#v", result)
	}
	for _, want := range []string{"missing_node:N-missing", "missing_evidence:E-missing"} {
		if !hasDecisionReason(result.Conflicts, want) {
			t.Errorf("conflicts = %#v, want %q", result.Conflicts, want)
		}
	}
}

func TestCompileBlocksMalformedGraphClaimBeforePublication(t *testing.T) {
	pkg := legacyPackageFixture()
	pkg.Claims = []scanartifacts.ClaimRow{
		{ID: "claim:missing-type", NodeID: "N-app", Summary: "Missing type"},
		{ID: "claim:missing-summary", NodeID: "N-app", GraphClaimType: "runtime_owner"},
		{
			ID: "claim:evidence-role-conflict", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "Conflicting role",
			SupportingEvidenceIDs: []string{"E-app"}, ContradictingEvidenceIDs: []string{"E-app"},
		},
		{
			ID: "claim:invalid-verification", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "Invalid verification",
			SupportingEvidenceIDs: []string{"E-app"},
			Verifications:         []claim.Verification{{Result: "unknown", ObservedAt: ""}},
		},
	}

	_, result := Compile(AdaptLegacy(pkg))
	if result.PublicationAllowed {
		t.Fatalf("publication_allowed = true, want false; result=%#v", result)
	}
	for _, want := range []string{
		"missing_graph_claim_type",
		"missing_summary",
		"evidence_role_conflict:E-app",
		"missing_verification_id",
		"invalid_verification_result:unknown",
		"verification_evidence_required",
		"verification_observed_at_required",
	} {
		if !hasDecisionReason(result.Conflicts, want) {
			t.Errorf("conflicts = %#v, want %q", result.Conflicts, want)
		}
	}
}

func TestCompileMergesEquivalentClaimVerificationIDsAndBlocksConflicts(t *testing.T) {
	pkg := legacyPackageFixture()
	verification := claim.Verification{
		ID: "verification:owner", Result: claim.VerificationPassed, EvidenceID: "E-app", ObservedAt: "2026-07-13T10:00:00Z",
	}
	pkg.Claims = []scanartifacts.ClaimRow{{
		ID: "claim:owner", NodeID: "N-app", GraphClaimType: "runtime_owner", Summary: "App owns runtime behavior",
		SupportingEvidenceIDs: []string{"E-app"}, Verifications: []claim.Verification{verification, verification},
	}}

	compiled, result := Compile(AdaptLegacy(pkg))
	if !result.PublicationAllowed || len(compiled.Package.Claims[0].Verifications) != 1 {
		t.Fatalf("compiled/result = %#v/%#v, want one merged verification", compiled, result)
	}
	if len(result.MergeRecords) != 1 || result.MergeRecords[0].Category != "claim_verification" {
		t.Fatalf("merge records = %#v, want claim_verification merge", result.MergeRecords)
	}

	conflicting := verification
	conflicting.Result = claim.VerificationFailed
	pkg.Claims[0].Verifications = []claim.Verification{verification, conflicting}
	_, result = Compile(AdaptLegacy(pkg))
	if result.PublicationAllowed || !hasDecisionReason(result.Conflicts, "verification_identity_conflict:verification:owner") {
		t.Fatalf("result = %#v, want conflicting verification ID block", result)
	}
}

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
		{
			name: "nested traversal outside repository",
			mutate: func(pkg *scanartifacts.Package) {
				pkg.Nodes[0].Paths = append(pkg.Nodes[0].Paths, "src/../../outside.go")
			},
			wantReason: "path_outside_repository",
		},
		{
			name: "internal traversal alias",
			mutate: func(pkg *scanartifacts.Package) {
				pkg.Nodes[0].Paths = append(pkg.Nodes[0].Paths, "src/../other.go")
			},
			wantReason: "non_concrete_path",
		},
		{
			name: "glob path",
			mutate: func(pkg *scanartifacts.Package) {
				pkg.Nodes[0].Paths = append(pkg.Nodes[0].Paths, "src/*.go")
			},
			wantReason: "non_concrete_path",
		},
		{
			name: "repository root",
			mutate: func(pkg *scanartifacts.Package) {
				pkg.Nodes[0].Paths = append(pkg.Nodes[0].Paths, ".")
			},
			wantReason: "non_concrete_path",
		},
		{
			name: "empty path segment",
			mutate: func(pkg *scanartifacts.Package) {
				pkg.Nodes[0].Paths = append(pkg.Nodes[0].Paths, "src//app.go")
			},
			wantReason: "non_concrete_path",
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

func TestCompileDoesNotMutateAgentProposal(t *testing.T) {
	pkg := legacyPackageFixture()
	pkg.Nodes[0].Paths = []string{"src/z.go", "src/app.go"}
	pkg.Edges[0].EvidenceIDs = []string{"E-worker", "E-app"}
	proposal := AdaptLegacy(pkg)
	before, err := json.Marshal(proposal)
	if err != nil {
		t.Fatal(err)
	}

	Compile(proposal)

	after, err := json.Marshal(proposal)
	if err != nil {
		t.Fatal(err)
	}
	if string(after) != string(before) {
		t.Fatalf("Compile mutated proposal:\nbefore=%s\nafter=%s", before, after)
	}
}

func TestCompileCoversVersionIdentityPathAndUnknownPolicies(t *testing.T) {
	pkg := legacyPackageFixture()
	pkg.Nodes = append(pkg.Nodes, scanartifacts.NodeRow{Type: "capability", Title: "Missing ID"})
	pkg.Nodes[0].EvidenceIDs = nil
	pkg.Nodes[0].Paths = append(pkg.Nodes[0].Paths, "../outside.go")
	pkg.Edges[0].SourceID = "N-missing"
	pkg.Observations[0].EvidenceIDs = []string{"E-missing"}
	proposal := AdaptLegacy(pkg)
	proposal.ProposalVersion = ContractVersion + 1

	_, result := Compile(proposal)

	if result.PublicationAllowed {
		t.Fatalf("publication_allowed = true, want false; result=%#v", result)
	}
	for _, reason := range []string{
		"unsupported_proposal_version",
		"missing_identity",
		"path_outside_repository",
		"missing_source_node:N-missing",
		"missing_evidence:E-missing",
	} {
		if !hasDecisionReason(result.Conflicts, reason) {
			t.Fatalf("conflicts = %#v, want %q", result.Conflicts, reason)
		}
	}
	if !hasDecisionReason(result.Unknowns, "no_evidence_reference") {
		t.Fatalf("unknowns = %#v, want no_evidence_reference", result.Unknowns)
	}
}

func TestCompileDeepClonesAttributesAndMergesEveryRowCategory(t *testing.T) {
	pkg := legacyPackageFixture()
	pkg.Nodes[0].Attrs = map[string]any{
		"nested": map[string]any{"owners": []any{"runtime", map[string]any{"name": "agent"}}},
		"tags":   []string{"a", "b"},
	}
	pkg.Evidence = append(pkg.Evidence, pkg.Evidence[0])
	pkg.Edges = append(pkg.Edges, pkg.Edges[0])
	pkg.Observations = append(pkg.Observations, pkg.Observations[0])

	compiled, result := Compile(AdaptLegacy(pkg))

	if !result.PublicationAllowed {
		t.Fatalf("publication_allowed = false; conflicts=%#v", result.Conflicts)
	}
	if len(result.MergeRecords) != 3 {
		t.Fatalf("merge_records = %#v, want evidence, edge, and observation merges", result.MergeRecords)
	}
	compiledNested := compiled.Package.Nodes[0].Attrs["nested"].(map[string]any)
	compiledNested["owners"].([]any)[0] = "changed"
	compiled.Package.Nodes[0].Attrs["tags"].([]string)[0] = "changed"
	originalNested := pkg.Nodes[0].Attrs["nested"].(map[string]any)
	if originalNested["owners"].([]any)[0] != "runtime" || pkg.Nodes[0].Attrs["tags"].([]string)[0] != "a" {
		t.Fatalf("compiled attrs share memory with proposal attrs: %#v", pkg.Nodes[0].Attrs)
	}
}

func TestProposalFingerprintIgnoresDerivedIdentityCache(t *testing.T) {
	withoutCache := legacyPackageFixture()
	withCache := legacyPackageFixture()
	withCache.Identities = scanartifacts.IdentitySet{
		Evidence:      map[string]bool{"stale-evidence": true},
		Nodes:         map[string]bool{"stale-node": true},
		Edges:         map[string]bool{"stale-edge": true},
		Observations:  map[string]bool{"stale-observation": true},
		CoveragePaths: map[string]bool{"stale/path.go": true},
	}

	_, first := Compile(AdaptLegacy(withoutCache))
	_, second := Compile(AdaptLegacy(withCache))

	if first.ProposalFingerprint != second.ProposalFingerprint {
		t.Fatalf("proposal fingerprints differ for identical source rows: %q != %q", first.ProposalFingerprint, second.ProposalFingerprint)
	}
}

func TestCompileEnforcesDeclaredProposalScope(t *testing.T) {
	proposal := AdaptLegacy(legacyPackageFixture())
	proposal.Scope = []string{"src/app.go"}

	_, result := Compile(proposal)

	if result.PublicationAllowed {
		t.Fatalf("publication_allowed = true, want out-of-scope block; result=%#v", result)
	}
	if !hasDecisionReason(result.Conflicts, "outside_proposal_scope") {
		t.Fatalf("conflicts = %#v, want outside_proposal_scope", result.Conflicts)
	}
}

func TestCompileRejectsUnrelatedCoverageWithoutBlockingPublication(t *testing.T) {
	pkg := legacyPackageFixture()
	pkg.CoveragePaths = append(pkg.CoveragePaths, "docs/guide.md")

	_, result := Compile(AdaptLegacy(pkg))

	if !result.PublicationAllowed {
		t.Fatalf("publication_allowed = false; conflicts=%#v", result.Conflicts)
	}
	if !hasDecision(result.Rejections, "coverage", "docs/guide.md", "no_node_relation") {
		t.Fatalf("rejections = %#v, want explicit unrelated coverage decision", result.Rejections)
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

func hasDecision(decisions []Decision, category, identity, reason string) bool {
	for _, decision := range decisions {
		if decision.Category == category && decision.Identity == identity && decision.Reason == reason {
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

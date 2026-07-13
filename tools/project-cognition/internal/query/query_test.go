package query

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestCurrentQueryContractVersions(t *testing.T) {
	if ClaimRetrievalContractVersion != 2 || CandidateUniverseVersion != 2 {
		t.Fatalf("query contract versions = claim:%d candidate:%d, want current-only 2/2", ClaimRetrievalContractVersion, CandidateUniverseVersion)
	}
}

func TestRunReturnsOnlyRelatedCompactGraphClaims(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-claims",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{
			{ID: "E-app", SourceKind: "source", SourcePath: "src/app.go", CommitSHA: "abc123", Span: "12:1-28:2", Extractor: "test", ContentHash: "hash-app"},
		},
		Nodes: []store.NodeImport{
			{ID: "N-app", Type: "capability", Title: "App", Confidence: "high", EvidenceIDs: []string{"E-app"}},
		},
		Claims: []store.ClaimImport{{
			ID:                    "claim:app-owner",
			NodeID:                "N-app",
			GraphClaimType:        "runtime_owner",
			Summary:               "App owns runtime behavior",
			State:                 claim.StateSupported,
			Freshness:             claim.FreshnessFresh,
			StateReason:           "supporting_evidence",
			SupportingEvidenceIDs: []string{"E-app"},
		}},
		PathIndex: []store.PathIndexImport{
			{ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "high", EvidenceID: "E-app"},
		},
	})

	payload, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ClaimRetrievalContractVersion != 2 {
		t.Fatalf("ClaimRetrievalContractVersion = %d, want 2", payload.ClaimRetrievalContractVersion)
	}
	var serialized map[string]any
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(data, &serialized); err != nil {
		t.Fatal(err)
	}
	if serialized["candidate_universe_version"] != float64(2) {
		t.Fatalf("candidate_universe_version = %#v, want current version 2", serialized["candidate_universe_version"])
	}
	claims, ok := payload.Subgraph["claims"].([]map[string]any)
	if !ok || len(claims) != 1 {
		t.Fatalf("subgraph.claims = %#v, want one compact graph claim", payload.Subgraph["claims"])
	}
	got := claims[0]
	for _, key := range []string{"id", "node_id", "graph_claim_type", "summary", "state", "freshness", "state_reason"} {
		if _, exists := got[key]; !exists {
			t.Errorf("claim = %#v, missing compact field %q", got, key)
		}
	}
	if _, exists := got["verifications"]; exists {
		t.Fatalf("claim = %#v, default query must not dump verification history", got)
	}
	if _, exists := got["evidence"]; exists {
		t.Fatalf("claim = %#v, existing compact graph claim contract must stay compact", got)
	}
	if len(payload.ClaimSignals) != 1 {
		t.Fatalf("ClaimSignals = %#v, want one related claim signal", payload.ClaimSignals)
	}
	signal := payload.ClaimSignals[0]
	if signal.RouteConfidence != "high" || signal.ConfidenceScope != "route_candidate" {
		t.Fatalf("claim signal confidence = %#v, want high route_candidate confidence", signal)
	}
	if signal.Stale {
		t.Fatalf("claim signal stale = true, want false")
	}
	if !signal.LiveVerificationRequired {
		t.Fatalf("claim signal live verification = false, want true")
	}
	if signal.EvidenceCount != 1 || len(signal.EvidenceRefs) != 1 || signal.EvidenceTruncated {
		t.Fatalf("claim signal evidence = %#v, want one untruncated evidence ref", signal)
	}
	ref := signal.EvidenceRefs[0]
	if ref.ID != "E-app" || ref.Role != "supporting" || ref.SourceKind != "source" || ref.SourcePath != "src/app.go" || ref.Span != "12:1-28:2" || ref.CommitSHA != "abc123" {
		t.Errorf("claim evidence ref = %#v, want source identity and exact span", ref)
	}
	if payload.EpistemicContract.GraphOnlyClaimsAllowed {
		t.Fatalf("epistemic contract = %#v, graph claims must not authorize final claims", payload.EpistemicContract)
	}
}

func TestRunScopesClaimRouteConfidenceWithoutUpgradingGraphTruth(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-claim-confidence",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{
			{ID: "E-support", SourceKind: "source", SourcePath: "src/app.go", CommitSHA: "abc123", Span: "1:1-8:1", Extractor: "test", ContentHash: "hash-support"},
			{ID: "E-contradict", SourceKind: "test", SourcePath: "tests/app_test.go", CommitSHA: "abc123", Span: "10:1-22:1", Extractor: "test", ContentHash: "hash-contradict"},
		},
		Nodes: []store.NodeImport{{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-support"}}},
		Claims: []store.ClaimImport{
			{ID: "claim:verified", NodeID: "N-app", GraphClaimType: "behavior", Summary: "Verified graph assertion", State: claim.StateVerified, Freshness: claim.FreshnessFresh, StateReason: "supporting_evidence_and_current_verification", SupportingEvidenceIDs: []string{"E-support"}},
			{ID: "claim:supported", NodeID: "N-app", GraphClaimType: "behavior", Summary: "Supported graph assertion", State: claim.StateSupported, Freshness: claim.FreshnessFresh, StateReason: "supporting_evidence", SupportingEvidenceIDs: []string{"E-support"}},
			{ID: "claim:candidate", NodeID: "N-app", GraphClaimType: "behavior", Summary: "Candidate graph assertion", State: claim.StateCandidate, Freshness: claim.FreshnessUnknown, StateReason: "evidence_required"},
			{ID: "claim:contradicted", NodeID: "N-app", GraphClaimType: "behavior", Summary: "Contradicted graph assertion", State: claim.StateContradicted, Freshness: claim.FreshnessFresh, StateReason: "contradicting_evidence", ContradictingEvidenceIDs: []string{"E-contradict"}},
			{ID: "claim:stale", NodeID: "N-app", GraphClaimType: "behavior", Summary: "Stale graph assertion", State: claim.StateStale, Freshness: claim.FreshnessStale, StateReason: "source_changed", SupportingEvidenceIDs: []string{"E-support"}},
		},
		PathIndex: []store.PathIndexImport{{ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-support"}},
	})

	payload, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})
	if err != nil {
		t.Fatal(err)
	}
	byID := map[string]ClaimSignal{}
	for _, signal := range payload.ClaimSignals {
		byID[signal.ID] = signal
	}
	for _, id := range []string{"claim:verified", "claim:supported", "claim:candidate", "claim:contradicted", "claim:stale"} {
		if byID[id].RouteConfidence != "verified" || byID[id].ConfidenceScope != "route_candidate" {
			t.Errorf("%s route confidence = %#v, want verified route_candidate scope", id, byID[id])
		}
		if !byID[id].LiveVerificationRequired {
			t.Errorf("%s live verification required = false, want true", id)
		}
	}
	if !byID["claim:stale"].Stale || byID["claim:stale"].Freshness != string(claim.FreshnessStale) {
		t.Errorf("stale claim signal = %#v, want explicit stale state", byID["claim:stale"])
	}
	if byID["claim:contradicted"].Stale || byID["claim:contradicted"].State != string(claim.StateContradicted) {
		t.Errorf("contradicted claim signal = %#v, want contradicted without conflating staleness", byID["claim:contradicted"])
	}
}

func TestParsePlanNormalizesLegacyAliases(t *testing.T) {
	plan, err := ParsePlan(`{"candidate_universe_version":2,"path_hints":["./src/a.go"],"reason":"because"}`, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Paths) != 1 || plan.Paths[0] != "src/a.go" {
		t.Fatalf("paths = %#v", plan.Paths)
	}
	if plan.SelectionReason != "because" {
		t.Fatalf("selection reason = %q", plan.SelectionReason)
	}
}

func TestParsePlanRequiresCurrentCandidateUniverseVersion(t *testing.T) {
	for name, document := range map[string]string{
		"missing": `{"lexicon_generation_id":"GEN-current"}`,
		"old":     `{"lexicon_generation_id":"GEN-current","candidate_universe_version":1}`,
		"future":  `{"lexicon_generation_id":"GEN-current","candidate_universe_version":3}`,
	} {
		t.Run(name, func(t *testing.T) {
			_, _, err := ParsePlanWithDiagnostics(document, "")
			if err == nil || !strings.Contains(err.Error(), "candidate_universe_version") {
				t.Fatalf("ParsePlanWithDiagnostics(%s) error = %v, want current-version-only rejection", name, err)
			}
		})
	}

	plan, diagnostics, err := ParsePlanWithDiagnostics(
		`{"lexicon_generation_id":"GEN-current","candidate_universe_version":2}`,
		"",
	)
	if err != nil {
		t.Fatal(err)
	}
	data, err := json.Marshal(plan)
	if err != nil {
		t.Fatal(err)
	}
	var serializedPlan map[string]any
	if err := json.Unmarshal(data, &serializedPlan); err != nil {
		t.Fatal(err)
	}
	if diagnostics.Warnings != nil || serializedPlan["candidate_universe_version"] != float64(2) {
		t.Fatalf("plan = %#v diagnostics = %#v, want current candidate contract", plan, diagnostics)
	}
}

func TestParsePlanAcceptsConceptDecisionsAndGeneration(t *testing.T) {
	plan, err := ParsePlan(`{
		"raw_query": "GUI feels laggy",
		"lexicon_generation_id": "GEN-ui",
		"candidate_universe_version": 2,
		"selected_concepts": ["concept:GEN-ui:N-gui"],
		"rejected_concepts": ["concept:GEN-ui:N-login"],
		"concept_decisions": [
			{
				"concept_id": "concept:GEN-ui:N-gui",
				"decision": "selected",
				"selection_reason": "GUI owns the whole surface described by the user.",
				"confidence": "high",
				"paths": ["src/gui/window.tsx"]
			},
			{
				"concept_id": "concept:GEN-ui:N-login",
				"decision": "rejected",
				"selection_reason": "Login is a GUI flow but the request is not authentication-specific.",
				"confidence": "medium",
				"risk": "over-narrowing"
			}
		]
	}`, "")
	if err != nil {
		t.Fatal(err)
	}
	if plan.LexiconGenerationID != "GEN-ui" {
		t.Fatalf("LexiconGenerationID = %q, want GEN-ui", plan.LexiconGenerationID)
	}
	if len(plan.ConceptDecisions) != 2 {
		t.Fatalf("ConceptDecisions = %#v, want two decisions", plan.ConceptDecisions)
	}
	if got := plan.ConceptDecisions[0].Paths; len(got) != 1 || got[0] != "src/gui/window.tsx" {
		t.Fatalf("decision paths = %#v, want src/gui/window.tsx", got)
	}
}

func TestParsePlanPreservesRepositorySearchTerms(t *testing.T) {
	plan, err := ParsePlan(`{
		"raw_query": "Complete button should live in workflow status",
		"candidate_universe_version": 2,
		"repository_search_terms": [
			"workflow status",
			"Complete",
			"workflow status",
			"status header",
			""
		]
	}`, "")
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"workflow status", "Complete", "status header"}
	if len(plan.RepositorySearchTerms) != len(want) {
		t.Fatalf("RepositorySearchTerms = %#v, want %#v", plan.RepositorySearchTerms, want)
	}
	for index, term := range want {
		if plan.RepositorySearchTerms[index] != term {
			t.Fatalf("RepositorySearchTerms = %#v, want %#v", plan.RepositorySearchTerms, want)
		}
	}
}

func TestParsePlanAcceptsSemanticIntakeAndFacetCoverageDecisions(t *testing.T) {
	plan, err := ParsePlan(`{
		"raw_query": "Token usage today says 230M, is that wrong?",
		"candidate_universe_version": 2,
		"semantic_intake": {
			"workflow_intent": "debug",
			"normalized_query": "Investigate local CLI session token usage aggregation and daily accounting accuracy.",
			"intent_facets": ["token accounting", "usage aggregation", "daily total"],
			"negative_constraints": ["not only CLI launcher invocation behavior"],
			"alias_interpretations": [
				{"alias": "usage", "meaning": "token usage aggregation", "confidence": "high"}
			],
			"open_semantic_questions": []
		},
		"concept_decisions": [
			{
				"concept_id": "concept:GEN-usage:N-token-accounting",
				"decision": "selected",
				"selection_reason": "Covers accounting and aggregation facets.",
				"covered_facets": ["token accounting", "usage aggregation"],
				"missing_facets": ["daily total"],
				"match_sources": ["alias", "semantic_intake", "path"],
				"confidence": "high"
			}
		]
	}`, "")
	if err != nil {
		t.Fatal(err)
	}
	if plan.SemanticIntake.WorkflowIntent != "debug" {
		t.Fatalf("SemanticIntake.WorkflowIntent = %q, want debug", plan.SemanticIntake.WorkflowIntent)
	}
	if len(plan.SemanticIntake.IntentFacets) != 3 {
		t.Fatalf("SemanticIntake.IntentFacets = %#v, want three facets", plan.SemanticIntake.IntentFacets)
	}
	if len(plan.SemanticIntake.AliasInterpretations) != 1 || plan.SemanticIntake.AliasInterpretations[0].Meaning != "token usage aggregation" {
		t.Fatalf("SemanticIntake.AliasInterpretations = %#v", plan.SemanticIntake.AliasInterpretations)
	}
	decision := plan.ConceptDecisions[0]
	if !hasString(decision.CoveredFacets, "token accounting") {
		t.Fatalf("CoveredFacets = %#v, want token accounting", decision.CoveredFacets)
	}
	if !hasString(decision.MissingFacets, "daily total") {
		t.Fatalf("MissingFacets = %#v, want daily total", decision.MissingFacets)
	}
	if !hasString(decision.MatchSources, "semantic_intake") {
		t.Fatalf("MatchSources = %#v, want semantic_intake", decision.MatchSources)
	}
}

func TestParsePlanMergesTopLevelSemanticIntakeAliases(t *testing.T) {
	plan, err := ParsePlan(`{
		"candidate_universe_version": 2,
		"workflow_intent": " debug ",
		"normalized_query": " token usage accounting ",
		"intent_facets": ["token accounting", "token accounting", "daily total"],
		"negative_constraints": ["not pricing"],
		"alias_interpretations": [
			{"alias": " usage ", "meaning": " token usage ", "confidence": " high "}
		],
		"open_semantic_questions": ["which date window?"]
	}`, "")
	if err != nil {
		t.Fatal(err)
	}

	if plan.SemanticIntake.WorkflowIntent != "debug" {
		t.Fatalf("WorkflowIntent = %q", plan.SemanticIntake.WorkflowIntent)
	}
	if plan.SemanticIntake.NormalizedQuery != "token usage accounting" {
		t.Fatalf("NormalizedQuery = %q", plan.SemanticIntake.NormalizedQuery)
	}
	if len(plan.SemanticIntake.IntentFacets) != 2 || plan.SemanticIntake.IntentFacets[1] != "daily total" {
		t.Fatalf("IntentFacets = %#v", plan.SemanticIntake.IntentFacets)
	}
	if len(plan.SemanticIntake.AliasInterpretations) != 1 ||
		plan.SemanticIntake.AliasInterpretations[0].Alias != "usage" ||
		plan.SemanticIntake.AliasInterpretations[0].Meaning != "token usage" {
		t.Fatalf("AliasInterpretations = %#v", plan.SemanticIntake.AliasInterpretations)
	}
}

func TestParsePlanWithDiagnosticsCoercesTopLevelStringAliases(t *testing.T) {
	plan, diagnostics, err := ParsePlanWithDiagnostics(`{
		"candidate_universe_version": 2,
		"normalized_query": "WinPE driver download stall",
		"alias_interpretations": ["PE程序"]
	}`, "")
	if err != nil {
		t.Fatal(err)
	}

	if !hasString(diagnostics.Warnings, "coerced_top_level_alias_interpretations") {
		t.Fatalf("warnings = %#v, want coerced_top_level_alias_interpretations", diagnostics.Warnings)
	}
	if !hasString(diagnostics.Warnings, "query_plan_missing_lexicon_generation_id") {
		t.Fatalf("warnings = %#v, want missing lexicon generation warning", diagnostics.Warnings)
	}
	if len(plan.SemanticIntake.AliasInterpretations) != 1 {
		t.Fatalf("SemanticIntake.AliasInterpretations = %#v", plan.SemanticIntake.AliasInterpretations)
	}
	alias := plan.SemanticIntake.AliasInterpretations[0]
	if alias.Alias != "PE程序" || alias.Meaning != "PE程序" || alias.Confidence != "low" {
		t.Fatalf("alias = %#v, want low-confidence coerced object", alias)
	}
}

func TestParsePlanWithDiagnosticsCoercesNestedStringAliases(t *testing.T) {
	plan, diagnostics, err := ParsePlanWithDiagnostics(`{
		"lexicon_generation_id": "GEN-debug",
		"candidate_universe_version": 2,
		"semantic_intake": {
			"normalized_query": "WinPE driver download stall",
			"alias_interpretations": ["PE程序"]
		}
	}`, "")
	if err != nil {
		t.Fatal(err)
	}

	if !hasString(diagnostics.Warnings, "coerced_semantic_intake_alias_interpretations") {
		t.Fatalf("warnings = %#v, want nested alias coercion warning", diagnostics.Warnings)
	}
	alias := plan.SemanticIntake.AliasInterpretations[0]
	if alias.Alias != "PE程序" || alias.Meaning != "PE程序" || alias.Confidence != "low" {
		t.Fatalf("alias = %#v, want low-confidence coerced object", alias)
	}
}

func TestParsePlanKeepsNestedSemanticIntakeOverTopLevelAliases(t *testing.T) {
	plan, err := ParsePlan(`{
		"candidate_universe_version": 2,
		"normalized_query": "top level query",
		"intent_facets": ["top facet"],
		"alias_interpretations": [
			{"alias": "top", "meaning": "top alias"}
		],
		"semantic_intake": {
			"normalized_query": "nested query",
			"intent_facets": ["nested facet"],
			"alias_interpretations": [
				{"alias": "nested", "meaning": "nested alias"}
			]
		}
	}`, "")
	if err != nil {
		t.Fatal(err)
	}

	if plan.SemanticIntake.NormalizedQuery != "nested query" {
		t.Fatalf("NormalizedQuery = %q", plan.SemanticIntake.NormalizedQuery)
	}
	if len(plan.SemanticIntake.IntentFacets) != 1 || plan.SemanticIntake.IntentFacets[0] != "nested facet" {
		t.Fatalf("IntentFacets = %#v", plan.SemanticIntake.IntentFacets)
	}
	if len(plan.SemanticIntake.AliasInterpretations) != 1 ||
		plan.SemanticIntake.AliasInterpretations[0].Alias != "nested" {
		t.Fatalf("AliasInterpretations = %#v, want nested alias only", plan.SemanticIntake.AliasInterpretations)
	}
}

func TestParsePlanWithDiagnosticsRejectsUnsupportedAliasShape(t *testing.T) {
	_, _, err := ParsePlanWithDiagnostics(`{
		"lexicon_generation_id": "GEN-debug",
		"candidate_universe_version": 2,
		"semantic_intake": {
			"alias_interpretations": [{"alias": 95}]
		}
	}`, "")
	if err == nil {
		t.Fatal("expected unsupported alias shape error")
	}
	var parseErr *PlanParseError
	if !errors.As(err, &parseErr) {
		t.Fatalf("error = %T %[1]v, want PlanParseError", err)
	}
	if len(parseErr.Errors) == 0 {
		t.Fatalf("parseErr.Errors = %#v, want diagnostic errors", parseErr.Errors)
	}
	if len(parseErr.RepairHints) == 0 {
		t.Fatalf("parseErr.RepairHints = %#v, want repair hints", parseErr.RepairHints)
	}
	if parseErr.ExpectedShape == nil {
		t.Fatalf("parseErr.ExpectedShape = nil, want expected shape")
	}
}

func TestNormalizePlanBackfillsLegacyConceptDecisions(t *testing.T) {
	plan := NormalizePlan(Plan{
		SelectedConcepts: []string{"concept:GEN-ui:N-gui", "concept:GEN-ui:N-gui"},
		RejectedConcepts: []string{"concept:GEN-ui:N-login"},
		SelectionReason:  "GUI is relevant; login is too narrow.",
	})

	if got := plan.SelectedConcepts; len(got) != 1 || got[0] != "concept:GEN-ui:N-gui" {
		t.Fatalf("SelectedConcepts = %#v", got)
	}
	if len(plan.ConceptDecisions) != 2 {
		t.Fatalf("ConceptDecisions = %#v, want selected and rejected compatibility decisions", plan.ConceptDecisions)
	}
	if plan.ConceptDecisions[0].Decision != "selected" {
		t.Fatalf("first decision = %#v, want selected", plan.ConceptDecisions[0])
	}
	if plan.ConceptDecisions[1].Decision != "rejected" {
		t.Fatalf("second decision = %#v, want rejected", plan.ConceptDecisions[1])
	}
}

func TestNormalizePlanBackfillsMissingLegacyDecisionsForMixedInput(t *testing.T) {
	plan := NormalizePlan(Plan{
		ConceptDecisions: []ConceptDecision{
			{
				ConceptID:       "concept:GEN-ui:N-gui",
				Decision:        "selected",
				SelectionReason: "GUI owns the explicit user interaction surface.",
			},
		},
		SelectedConcepts: []string{"concept:GEN-ui:N-gui", "concept:GEN-ui:N-rendering"},
		RejectedConcepts: []string{"concept:GEN-ui:N-login"},
		SelectionReason:  "GUI and rendering match the request; login is out of scope.",
	})

	want := []ConceptDecision{
		{
			ConceptID:       "concept:GEN-ui:N-gui",
			Decision:        "selected",
			SelectionReason: "GUI owns the explicit user interaction surface.",
		},
		{
			ConceptID:       "concept:GEN-ui:N-rendering",
			Decision:        "selected",
			SelectionReason: "GUI and rendering match the request; login is out of scope.",
		},
		{
			ConceptID:       "concept:GEN-ui:N-login",
			Decision:        "rejected",
			SelectionReason: "GUI and rendering match the request; login is out of scope.",
		},
	}

	if len(plan.ConceptDecisions) != len(want) {
		t.Fatalf("ConceptDecisions = %#v, want %#v", plan.ConceptDecisions, want)
	}
	seen := map[string]bool{}
	for i, decision := range plan.ConceptDecisions {
		if decision.ConceptID != want[i].ConceptID || decision.Decision != want[i].Decision || decision.SelectionReason != want[i].SelectionReason {
			t.Fatalf("ConceptDecisions[%d] = %#v, want %#v", i, decision, want[i])
		}
		key := decision.ConceptID + "\x00" + decision.Decision
		if seen[key] {
			t.Fatalf("duplicate concept decision for %q/%q", decision.ConceptID, decision.Decision)
		}
		seen[key] = true
	}
}

func TestParsePlanSupportsAtFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "plan.json")
	if err := os.WriteFile(path, []byte(`{"candidate_universe_version":2,"paths":["docs/x.md"]}`), 0o644); err != nil {
		t.Fatal(err)
	}
	plan, err := ParsePlan("@"+path, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Paths) != 1 || plan.Paths[0] != "docs/x.md" {
		t.Fatalf("paths = %#v", plan.Paths)
	}
}

func TestRunBlocksSplitBrainBaseline(t *testing.T) {
	paths := queryTestPaths(t)
	seedSplitBrainRuntime(t, paths)

	_, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}
}

func TestLexiconBlocksSplitBrainBaseline(t *testing.T) {
	paths := queryTestPaths(t)
	seedSplitBrainRuntime(t, paths)

	_, err := Lexicon(paths, "plan", "app", 10)

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}
}

func TestLexiconReportsMissingDatabaseAsUnmappedIntent(t *testing.T) {
	paths := queryTestPaths(t)

	payload, err := Lexicon(paths, "implement", "GUI lag", 10)
	if err != nil {
		t.Fatal(err)
	}
	if !payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = false, payload = %#v", payload)
	}
	if !hasString(payload.MissingCoverage, "project_cognition_database_missing") {
		t.Fatalf("MissingCoverage = %#v, want project_cognition_database_missing", payload.MissingCoverage)
	}
	if len(payload.ConceptCandidates) != 0 {
		t.Fatalf("ConceptCandidates = %#v, want empty", payload.ConceptCandidates)
	}
	if payload.Readiness != rt.NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.NeedsRebuildReadiness)
	}
}

func TestLexiconReportsEmptyGraphCandidateUniverse(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-empty",
		Kind:         "full",
		SourceCommit: "abc123",
	})

	payload, err := Lexicon(paths, "implement", "GUI lag", 10)
	if err != nil {
		t.Fatal(err)
	}
	if !payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = false, payload = %#v", payload)
	}
	if !hasString(payload.MissingCoverage, "empty_graph_candidate_universe") {
		t.Fatalf("MissingCoverage = %#v, want empty_graph_candidate_universe", payload.MissingCoverage)
	}
	if payload.ActiveGenerationID != "GEN-empty" || payload.LexiconGenerationID != "GEN-empty" {
		t.Fatalf("generation fields = active %q lexicon %q, want GEN-empty", payload.ActiveGenerationID, payload.LexiconGenerationID)
	}
	if len(payload.ConceptCandidates) != 0 {
		t.Fatalf("ConceptCandidates = %#v, want empty", payload.ConceptCandidates)
	}
}

func TestTermsFromKeepsUnicodeLetters(t *testing.T) {
	terms := termsFrom("GUI 卡顿 刷新率低", 10)

	for _, want := range []string{"gui", "卡顿", "刷新率低"} {
		if !hasString(terms, want) {
			t.Fatalf("termsFrom() = %#v, want %q", terms, want)
		}
	}
}

func TestTermsFromExtractsAsciiTermsEmbeddedInCJKText(t *testing.T) {
	terms := termsFrom("使用tui安装skill选择用户级后用户目录没有对应skill", 10)

	for _, want := range []string{"tui", "skill"} {
		if !hasString(terms, want) {
			t.Fatalf("termsFrom() = %#v, want %q", terms, want)
		}
	}
}

func TestLexiconCatalogIncludesCompactAliasMaterialBeforeCandidateRanking(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-usage",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-usage",
			SourceKind:  "source",
			SourcePath:  "src/usage/daily_rollup.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-usage",
		}, {
			ID:          "E-cli",
			SourceKind:  "source",
			SourcePath:  "src/cli/launcher.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-cli",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-token-accounting",
			Type:        "capability",
			Title:       "Token Usage Accounting",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-usage"},
			Attrs: map[string]any{
				"aliases":            []any{"usage rollup", "daily token accounting"},
				"domain":             "usage",
				"owner":              "billing-runtime",
				"route_hints":        []any{"src/usage"},
				"verification_hints": []any{"go test ./internal/usage"},
			},
		}, {
			ID:          "N-claude-cli-launcher",
			Type:        "capability",
			Title:       "Claude CLI Launcher",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-cli"},
			Attrs: map[string]any{
				"aliases": []any{"CLI launcher invocation behavior"},
				"domain":  "cli",
				"owner":   "launcher",
			},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-usage",
			Path:       "src/usage/daily_rollup.go",
			NodeID:     "N-token-accounting",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-usage",
		}, {
			ID:         "P-cli",
			Path:       "src/cli/launcher.go",
			NodeID:     "N-claude-cli-launcher",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-cli",
		}},
		Observations: []store.ObservationImport{{
			ID:              "OBS-usage",
			ObservationType: "summary",
			Summary:         "daily token rollup",
			EvidenceIDs:     []string{"E-usage"},
		}},
	})

	payload, err := LexiconWithOptions(paths, LexiconInput{
		Intent: "debug",
		Query:  "today says 230M, is it wrong?",
		Limit:  1,
		Mode:   "catalog",
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.ConceptCandidates) != 1 {
		t.Fatalf("ConceptCandidates = %#v, want selection window limited to one candidate", payload.ConceptCandidates)
	}
	if len(payload.AliasCatalog) != 1 {
		t.Fatalf("AliasCatalog = %#v, want budgeted alias catalog with one entry", payload.AliasCatalog)
	}
	if payload.AliasCatalogCount != 2 {
		t.Fatalf("AliasCatalogCount = %d, want full active graph count 2", payload.AliasCatalogCount)
	}
	if payload.AliasCatalogLimit != 1 {
		t.Fatalf("AliasCatalogLimit = %d, want 1", payload.AliasCatalogLimit)
	}
	if !payload.AliasCatalogTruncated {
		t.Fatalf("AliasCatalogTruncated = false, want true")
	}
	firstCatalog := payload.AliasCatalog[0]
	for _, key := range []string{"concept_id", "title", "aliases", "owner", "domain", "node_type", "confidence", "path_hints", "route_hints", "verification_hints", "evidence_summary_tags"} {
		if _, ok := firstCatalog[key]; !ok {
			t.Fatalf("alias catalog item missing %s: %#v", key, firstCatalog)
		}
	}
	acceptedFields := payload.QueryPlanningContract["accepted_fields"]
	for _, want := range []string{"semantic_intake", "normalized_query", "intent_facets", "negative_constraints", "repository_search_terms"} {
		if !mapStringSliceContains(acceptedFields, want) {
			t.Fatalf("accepted_fields = %#v, want %q", acceptedFields, want)
		}
	}
	decisionFields := payload.QueryPlanningContract["concept_decision_fields"]
	for _, want := range []string{"covered_facets", "missing_facets", "match_sources"} {
		if !mapStringSliceContains(decisionFields, want) {
			t.Fatalf("concept_decision_fields = %#v, want %q", decisionFields, want)
		}
	}
}

func TestLexiconAgentNormalizationRequiredForZeroPositiveMatchesWithCatalog(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-normalization-zero",
		Kind:         "full",
		SourceCommit: "abc123",
		Nodes: []store.NodeImport{{
			ID:         "N-lifecycle-confirmation",
			Type:       "capability",
			Title:      "Lifecycle Confirmation Preview",
			Confidence: "verified",
			Attrs: map[string]any{
				"aliases": []any{"install lifecycle", "confirmation preview", "action plan preview"},
			},
		}},
	})

	payload, err := LexiconWithOptions(paths, LexiconInput{
		Intent: "debug",
		Query:  "payment ledger rounding",
		Limit:  10,
		Mode:   "catalog",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.AgentNormalization == nil {
		t.Fatalf("AgentNormalization = nil, want required diagnostic")
	}
	if !payload.AgentNormalization.Required {
		t.Fatalf("AgentNormalization.Required = false, want true")
	}
	if payload.AgentNormalization.Action != "write_semantic_intake_from_alias_catalog" {
		t.Fatalf("AgentNormalization.Action = %q", payload.AgentNormalization.Action)
	}
	if !hasString(payload.AgentNormalization.Triggers, "zero_positive_matches") {
		t.Fatalf("AgentNormalization.Triggers = %#v, want zero_positive_matches", payload.AgentNormalization.Triggers)
	}
	if !hasString(payload.AgentNormalization.Triggers, "no_graph_candidate_matched_query") {
		t.Fatalf("AgentNormalization.Triggers = %#v, want no_graph_candidate_matched_query", payload.AgentNormalization.Triggers)
	}
	if len(payload.AliasCatalog) == 0 {
		t.Fatalf("AliasCatalog = %#v, want usable catalog", payload.AliasCatalog)
	}
}

func TestLexiconAgentNormalizationRequiredForCJKWithPositiveRawMatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-normalization-cjk",
		Kind:         "full",
		SourceCommit: "abc123",
		Nodes: []store.NodeImport{{
			ID:         "N-tui-install",
			Type:       "capability",
			Title:      "TUI Install Lifecycle",
			Confidence: "verified",
			Attrs: map[string]any{
				"aliases": []any{"tui install lifecycle", "install confirmation"},
			},
		}},
	})

	payload, err := LexiconWithOptions(paths, LexiconInput{
		Intent: "debug",
		Query:  "使用tui安装后确认弹窗不一样",
		Limit:  10,
		Mode:   "catalog",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.MatchingProfile["positive_matches"] == 0 {
		t.Fatalf("positive_matches = 0, want raw match through embedded tui term")
	}
	if payload.AgentNormalization == nil {
		t.Fatalf("AgentNormalization = nil, want required diagnostic for mixed CJK/ASCII")
	}
	if !hasString(payload.AgentNormalization.Triggers, "cjk_or_mixed_language_query") {
		t.Fatalf("AgentNormalization.Triggers = %#v, want cjk_or_mixed_language_query", payload.AgentNormalization.Triggers)
	}
}

func TestLexiconOmitsAgentNormalizationForPlainEnglishRawMatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-normalization-english",
		Kind:         "full",
		SourceCommit: "abc123",
		Nodes: []store.NodeImport{{
			ID:         "N-lifecycle-confirmation",
			Type:       "capability",
			Title:      "Lifecycle Confirmation Preview",
			Confidence: "verified",
			Attrs: map[string]any{
				"aliases": []any{"install lifecycle", "confirmation preview"},
			},
		}},
	})

	payload, err := LexiconWithOptions(paths, LexiconInput{
		Intent: "debug",
		Query:  "install lifecycle confirmation preview",
		Limit:  10,
		Mode:   "catalog",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.AgentNormalization != nil {
		t.Fatalf("AgentNormalization = %#v, want omitted diagnostic", payload.AgentNormalization)
	}
}

func TestLexiconCatalogModeReturnsAliasCatalogForEmptyQuery(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-empty-query",
		Kind:         "full",
		SourceCommit: "abc123",
		Nodes: []store.NodeImport{{
			ID:         "N-token-accounting",
			Type:       "capability",
			Title:      "Token Usage Accounting",
			Confidence: "verified",
			Attrs: map[string]any{
				"aliases": []any{"usage rollup"},
			},
		}},
	})

	payload, err := LexiconWithOptions(paths, LexiconInput{
		Intent: "debug",
		Query:  "",
		Limit:  10,
		Mode:   "catalog",
	})
	if err != nil {
		t.Fatal(err)
	}
	if !payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = false, want true for empty query terms")
	}
	if !hasString(payload.MissingCoverage, "empty_query_terms") {
		t.Fatalf("MissingCoverage = %#v, want empty_query_terms", payload.MissingCoverage)
	}
	if len(payload.AliasCatalog) != 1 {
		t.Fatalf("AliasCatalog = %#v, want alias catalog despite empty query", payload.AliasCatalog)
	}
	if len(payload.ConceptCandidates) != 0 {
		t.Fatalf("ConceptCandidates = %#v, want no ranked candidates for empty query", payload.ConceptCandidates)
	}
	if payload.AgentNormalization == nil {
		t.Fatalf("AgentNormalization = nil, want required diagnostic for empty catalog query")
	}
	if !payload.AgentNormalization.Required {
		t.Fatalf("AgentNormalization.Required = false, want true")
	}
	if payload.AgentNormalization.Reason != "raw_terms_did_not_match_project_aliases" {
		t.Fatalf("AgentNormalization.Reason = %q", payload.AgentNormalization.Reason)
	}
	if payload.AgentNormalization.Reminder != "Do not stop at score=0. Translate user language into project vocabulary using the alias catalog." {
		t.Fatalf("AgentNormalization.Reminder = %q", payload.AgentNormalization.Reminder)
	}
	if !hasString(payload.AgentNormalization.Triggers, "zero_positive_matches") {
		t.Fatalf("AgentNormalization.Triggers = %#v, want zero_positive_matches", payload.AgentNormalization.Triggers)
	}
}

func TestLexiconOmitsAgentNormalizationWhenCatalogIsNotUsable(t *testing.T) {
	cases := []struct {
		name       string
		freshness  string
		readiness  string
		graphReady bool
		nextAction string
	}{
		{
			name:       "needs rebuild",
			freshness:  rt.ReadyFreshness,
			readiness:  rt.NeedsRebuildReadiness,
			graphReady: true,
			nextAction: "run_map_scan_build",
		},
		{
			name:       "blocked",
			freshness:  rt.ReadyFreshness,
			readiness:  rt.BlockedReadiness,
			graphReady: true,
			nextAction: "run_map_scan_build",
		},
		{
			name:       "stale",
			freshness:  rt.StaleFreshness,
			readiness:  rt.ReadyReadiness,
			graphReady: true,
			nextAction: "run_map_update",
		},
		{
			name:       "graph not ready",
			freshness:  rt.ReadyFreshness,
			readiness:  rt.ReadyReadiness,
			graphReady: false,
			nextAction: "run_map_scan_build",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			paths := queryTestPaths(t)
			seedReadyGraph(t, paths, store.ImportInput{
				GenerationID: "GEN-normalization-unusable",
				Kind:         "full",
				SourceCommit: "abc123",
				Nodes: []store.NodeImport{{
					ID:         "N-lifecycle-confirmation",
					Type:       "capability",
					Title:      "Lifecycle Confirmation Preview",
					Confidence: "verified",
					Attrs: map[string]any{
						"aliases": []any{"install lifecycle", "confirmation preview"},
					},
				}},
			})
			status, err := rt.ReadStatus(paths)
			if err != nil {
				t.Fatal(err)
			}
			status.Freshness = tc.freshness
			status.Readiness = tc.readiness
			status.GraphReady = tc.graphReady
			status.RecommendedNextAction = tc.nextAction
			if err := rt.WriteStatus(paths, status); err != nil {
				t.Fatal(err)
			}

			payload, err := LexiconWithOptions(paths, LexiconInput{
				Intent: "debug",
				Query:  "payment ledger rounding",
				Limit:  10,
				Mode:   "catalog",
			})
			if err != nil {
				t.Fatal(err)
			}
			if len(payload.AliasCatalog) == 0 {
				t.Fatalf("AliasCatalog = %#v, want catalog data to remain available", payload.AliasCatalog)
			}
			if payload.AgentNormalization != nil {
				t.Fatalf("AgentNormalization = %#v, want omitted diagnostic when catalog is not usable", payload.AgentNormalization)
			}
			if payload.Readiness != tc.readiness {
				t.Fatalf("Readiness = %q, want %q", payload.Readiness, tc.readiness)
			}
			if payload.RecommendedNextAction != tc.nextAction {
				t.Fatalf("RecommendedNextAction = %q, want %q", payload.RecommendedNextAction, tc.nextAction)
			}
		})
	}
}

func TestLexiconUsesStoredAliasRowsInsteadOfAttrsAliases(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-stored-alias",
		Kind:         "full",
		SourceCommit: "abc123",
		Nodes: []store.NodeImport{{
			ID:         "N-app",
			Type:       "capability",
			Title:      "Application Shell",
			Confidence: "verified",
			Attrs: map[string]any{
				"aliases": []any{"legacy attr alias"},
			},
		}},
		Aliases: []store.AliasImport{{
			ID:              "AI-stored-alias",
			Alias:           "Stored Name",
			NormalizedAlias: "stored name",
			TargetType:      "node",
			TargetID:        "N-app",
			Source:          "test",
			Confidence:      "verified",
		}},
	})

	payload, err := LexiconWithOptions(paths, LexiconInput{
		Intent: "debug",
		Query:  "legacy attr alias",
		Limit:  10,
		Mode:   "catalog",
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.AliasCatalog) != 1 {
		t.Fatalf("AliasCatalog = %#v, want one item", payload.AliasCatalog)
	}
	if !payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = false, want legacy attrs alias query to be unmapped")
	}
	if !hasString(payload.MissingCoverage, "no_graph_candidate_matched_query") {
		t.Fatalf("MissingCoverage = %#v, want no_graph_candidate_matched_query", payload.MissingCoverage)
	}
	if len(payload.ConceptCandidates) != 1 {
		t.Fatalf("ConceptCandidates = %#v, want one zero-score catalogued candidate", payload.ConceptCandidates)
	}
	if payload.ConceptCandidates[0]["score"] != 0 {
		t.Fatalf("ConceptCandidates = %#v, want no score from legacy attrs alias", payload.ConceptCandidates)
	}
	aliases, ok := payload.AliasCatalog[0]["aliases"].([]string)
	if !ok {
		t.Fatalf("aliases = %#v, want []string", payload.AliasCatalog[0]["aliases"])
	}
	if !hasString(aliases, "Stored Name") {
		t.Fatalf("aliases = %#v, want Stored Name from alias_index", aliases)
	}
	if hasString(aliases, "legacy attr alias") {
		t.Fatalf("aliases = %#v, do not want legacy attrs alias", aliases)
	}
}

func TestLexiconReturnsGraphCandidatesWithoutInventedTermConcepts(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}, {
			ID:          "E-login",
			SourceKind:  "source",
			SourcePath:  "src/auth/login.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-login",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
			Attrs: map[string]any{
				"aliases":            []any{"GUI", "desktop UI", "smoothness"},
				"domain":             "desktop",
				"owner":              "frontend",
				"verification_hints": []any{"npm test -- gui"},
			},
		}, {
			ID:          "N-login",
			Type:        "capability",
			Title:       "Login Flow",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-login"},
			Attrs:       map[string]any{"aliases": []any{"login", "auth"}},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}, {
			ID:         "P-login",
			Path:       "src/auth/login.tsx",
			NodeID:     "N-login",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-login",
		}},
	})

	payload, err := Lexicon(paths, "debug", "The GUI feels laggy and not smooth", 10)
	if err != nil {
		t.Fatal(err)
	}
	if payload.ActiveGenerationID != "GEN-ui" || payload.LexiconGenerationID != "GEN-ui" {
		t.Fatalf("generation fields = %#v", payload)
	}
	if payload.CandidateUniverseVersion != CandidateUniverseVersion {
		t.Fatalf("CandidateUniverseVersion = %d", payload.CandidateUniverseVersion)
	}
	if len(payload.ConceptCandidates) == 0 {
		t.Fatal("ConceptCandidates is empty")
	}
	first := payload.ConceptCandidates[0]
	if first["concept_id"] != "concept:GEN-ui:N-gui" {
		t.Fatalf("first candidate = %#v, want GUI concept", first)
	}
	for _, candidate := range payload.ConceptCandidates {
		conceptID, ok := candidate["concept_id"].(string)
		if !ok {
			t.Fatalf("candidate concept_id is not string: %#v", candidate)
		}
		if strings.HasPrefix(conceptID, "term:") {
			t.Fatalf("lexicon invented term candidate: %#v", candidate)
		}
	}
	if payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = true with GUI graph candidate: %#v", payload)
	}
}

func TestLexiconPayloadIncludesPlanningContractAndCandidateFields(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
			Attrs: map[string]any{
				"aliases":            []any{"GUI", "desktop UI", "smoothness"},
				"domain":             "desktop",
				"owner":              "frontend",
				"route_hints":        []any{"src/gui"},
				"verification_hints": []any{"npm test -- gui"},
			},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}},
	})

	payload, err := Lexicon(paths, "debug", "GUI lag", 10)
	if err != nil {
		t.Fatal(err)
	}
	acceptedFields := payload.QueryPlanningContract["accepted_fields"]
	for _, want := range []string{"concept_decisions", "lexicon_generation_id", "candidate_universe_version"} {
		if !mapStringSliceContains(acceptedFields, want) {
			t.Fatalf("accepted_fields = %#v, want %q", acceptedFields, want)
		}
	}
	if payload.QueryPlanningContract["candidate_universe_version"] != CandidateUniverseVersion {
		t.Fatalf("query planning candidate version = %#v, want %d", payload.QueryPlanningContract["candidate_universe_version"], CandidateUniverseVersion)
	}
	if len(payload.ConceptCandidates) == 0 {
		t.Fatal("ConceptCandidates is empty")
	}
	first := payload.ConceptCandidates[0]
	requiredKeys := []string{
		"concept_id",
		"node_id",
		"label",
		"title",
		"target_type",
		"node_type",
		"aliases",
		"matched_terms",
		"colloquial_matches",
		"paths",
		"evidence_ids",
		"confidence",
		"score",
		"rank",
		"domain",
		"owner",
		"route_hints",
		"verification_hints",
		"disambiguation_hint",
		"selection_guidance",
	}
	if !candidateHasKeys(first, requiredKeys...) {
		t.Fatalf("first candidate missing required keys: %#v", first)
	}
}

func TestLexiconRanksRelevantCandidateBeyondStoreDefaultWindow(t *testing.T) {
	paths := queryTestPaths(t)
	evidence := make([]store.EvidenceImport, 0, 225)
	nodes := make([]store.NodeImport, 0, 225)
	pathIndex := make([]store.PathIndexImport, 0, 225)
	for i := 1; i <= 225; i++ {
		nodeID := fmt.Sprintf("N-filler-%03d", i)
		title := fmt.Sprintf("Filler Concept %03d", i)
		sourcePath := fmt.Sprintf("src/filler/%03d.go", i)
		aliases := []any{"unrelated"}
		if i == 225 {
			nodeID = "N-render-latency"
			title = "Render Latency"
			sourcePath = "src/render/latency.go"
			aliases = []any{"render latency"}
		}
		suffix := strings.TrimPrefix(nodeID, "N-")
		evidenceID := "E-" + suffix
		pathID := "P-" + suffix
		evidence = append(evidence, store.EvidenceImport{
			ID:          evidenceID,
			SourceKind:  "source",
			SourcePath:  sourcePath,
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-" + suffix,
		})
		nodes = append(nodes, store.NodeImport{
			ID:          nodeID,
			Type:        "capability",
			Title:       title,
			Confidence:  "verified",
			EvidenceIDs: []string{evidenceID},
			Attrs:       map[string]any{"aliases": aliases},
		})
		pathIndex = append(pathIndex, store.PathIndexImport{
			ID:         pathID,
			Path:       sourcePath,
			NodeID:     nodeID,
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: evidenceID,
		})
	}
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-latency",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence:     evidence,
		Nodes:        nodes,
		PathIndex:    pathIndex,
	})

	payload, err := Lexicon(paths, "debug", "render latency", 5)
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.ConceptCandidates) == 0 {
		t.Fatal("ConceptCandidates is empty")
	}
	first := payload.ConceptCandidates[0]
	if first["concept_id"] != "concept:GEN-latency:N-render-latency" {
		t.Fatalf("first candidate = %#v, want late render latency concept", first)
	}
	if payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = true with late render latency candidate: %#v", payload)
	}
}

func TestLexiconReportsEmptyQueryTerms(t *testing.T) {
	paths := queryTestPaths(t)

	payload, err := Lexicon(paths, "implement", "!!!", 10)
	if err != nil {
		t.Fatal(err)
	}
	if !payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = false, payload = %#v", payload)
	}
	if !hasString(payload.MissingCoverage, "empty_query_terms") {
		t.Fatalf("MissingCoverage = %#v, want empty_query_terms", payload.MissingCoverage)
	}
	if len(payload.ConceptCandidates) != 0 {
		t.Fatalf("ConceptCandidates = %#v, want empty", payload.ConceptCandidates)
	}
	counts, ok := payload.CandidateUniverse["counts"].(map[string]any)
	if !ok {
		t.Fatalf("CandidateUniverse counts = %#v, want map", payload.CandidateUniverse["counts"])
	}
	if counts["nodes"] != 0 || counts["candidates"] != 0 {
		t.Fatalf("CandidateUniverse counts = %#v, want zero nodes and candidates", counts)
	}
}

func TestLexiconGreenfieldEmptyKeepsEmptyTermsUnmapped(t *testing.T) {
	paths := queryTestPaths(t)
	seedGreenfieldEmptyRuntime(t, paths)

	payload, err := Lexicon(paths, "plan", "!!!", 10)
	if err != nil {
		t.Fatal(err)
	}
	if payload.BaselineKind != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("BaselineKind = %q, want %q", payload.BaselineKind, rt.BaselineKindGreenfieldEmpty)
	}
	if !payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = false, payload = %#v", payload)
	}
	if !hasString(payload.MissingCoverage, "empty_query_terms") {
		t.Fatalf("MissingCoverage = %#v, want empty_query_terms", payload.MissingCoverage)
	}
	if !hasString(payload.MissingCoverage, "greenfield_empty_no_project_code") {
		t.Fatalf("MissingCoverage = %#v, want greenfield_empty_no_project_code", payload.MissingCoverage)
	}
	if len(payload.ConceptCandidates) != 0 {
		t.Fatalf("ConceptCandidates = %#v, want empty", payload.ConceptCandidates)
	}
}

func TestLexiconReportsUnmappedIntentWhenNoGraphCandidateMatches(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}},
	})

	payload, err := Lexicon(paths, "implement", "payment settlement ledger rounding", 10)
	if err != nil {
		t.Fatal(err)
	}
	if !payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = false, payload = %#v", payload)
	}
	if !hasString(payload.MissingCoverage, "no_graph_candidate_matched_query") {
		t.Fatalf("MissingCoverage = %#v, want no_graph_candidate_matched_query", payload.MissingCoverage)
	}
	for _, candidate := range payload.ConceptCandidates {
		conceptID, ok := candidate["concept_id"].(string)
		if !ok {
			t.Fatalf("candidate concept_id is not string: %#v", candidate)
		}
		if strings.HasPrefix(conceptID, "term:") {
			t.Fatalf("lexicon invented term candidate: %#v", candidate)
		}
	}
}

func TestRunBlocksStatusOnlyBaselineWithoutCreatingDatabase(t *testing.T) {
	paths := queryTestPaths(t)
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-status"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	_, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err == nil {
		t.Fatal("expected status-only agreement error")
	}
	if !strings.Contains(err.Error(), "project-cognition.db is missing") {
		t.Fatalf("error = %q, want missing DB", err.Error())
	}
	if _, statErr := os.Stat(paths.DatabasePath); !os.IsNotExist(statErr) {
		t.Fatalf("database stat err = %v, want missing DB", statErr)
	}
}

func TestRunBlocksIncompatibleDatabaseWithoutArchiving(t *testing.T) {
	paths := queryTestPaths(t)
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	for _, statement := range []string{
		`CREATE TABLE metadata(key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL)`,
		`CREATE TABLE generations(id TEXT PRIMARY KEY, state TEXT NOT NULL)`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('active_generation_id', '"GEN-db"', 'now')`,
		`INSERT INTO generations(id, state) VALUES('GEN-db', 'active')`,
	} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			t.Fatal(err)
		}
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-db"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	_, err = Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err == nil {
		t.Fatal("expected incompatible DB agreement error")
	}
	if !strings.Contains(err.Error(), "current runtime requires 3") {
		t.Fatalf("error = %q, want current schema requirement", err.Error())
	}
	if _, statErr := os.Stat(paths.DatabasePath + ".legacy"); !os.IsNotExist(statErr) {
		t.Fatalf("legacy archive stat err = %v, want no archive", statErr)
	}
}

func TestRunMissingBaselineReturnsNeedsRebuildWithoutCreatingDatabase(t *testing.T) {
	paths := queryTestPaths(t)

	payload, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err != nil {
		t.Fatalf("Run() error = %v", err)
	}
	if payload.Readiness != rt.NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q, want needs_rebuild", payload.Readiness)
	}
	if payload.RecommendedNextAction != "run_map_scan_build" {
		t.Fatalf("RecommendedNextAction = %q, want run_map_scan_build", payload.RecommendedNextAction)
	}
	if _, statErr := os.Stat(paths.DatabasePath); !os.IsNotExist(statErr) {
		t.Fatalf("database stat err = %v, want missing DB", statErr)
	}
}

func TestRunGreenfieldEmptyPreservesPlanPathsInMinimalLiveReads(t *testing.T) {
	paths := queryTestPaths(t)
	seedGreenfieldEmptyRuntime(t, paths)

	payload, err := Run(paths, QueryInput{
		Intent: "plan",
		Plan: Plan{
			RawQuery:  "build login",
			Paths:     []string{"./docs/login.md", ".specify/memory/constitution.md", "docs/login.md"},
			PathHints: []string{"./docs/auth.md", "docs/login.md"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.BaselineKind != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("BaselineKind = %q, want %q", payload.BaselineKind, rt.BaselineKindGreenfieldEmpty)
	}
	for _, want := range []string{
		".specify/memory/constitution.md",
		".specify/memory/project-rules.md",
		"AGENTS.md",
		"docs/login.md",
		"docs/auth.md",
	} {
		if !hasString(payload.MinimalLiveReads, want) {
			t.Fatalf("MinimalLiveReads = %#v, want %s", payload.MinimalLiveReads, want)
		}
	}
	if countString(payload.MinimalLiveReads, ".specify/memory/constitution.md") != 1 {
		t.Fatalf("MinimalLiveReads = %#v, want deduplicated constitution read", payload.MinimalLiveReads)
	}
	routePackReads, ok := payload.RoutePack["minimal_live_reads"].([]string)
	if !ok {
		t.Fatalf("route_pack.minimal_live_reads = %#v, want []string", payload.RoutePack["minimal_live_reads"])
	}
	if !equalStrings(routePackReads, payload.MinimalLiveReads) {
		t.Fatalf("route_pack.minimal_live_reads = %#v, want %#v", routePackReads, payload.MinimalLiveReads)
	}
	if !hasString(routePackReads, "docs/auth.md") {
		t.Fatalf("route_pack.minimal_live_reads = %#v, want docs/auth.md", routePackReads)
	}
	if !hasString(payload.MissingCoverage, "greenfield_empty_no_project_code") {
		t.Fatalf("MissingCoverage = %#v, want greenfield_empty_no_project_code", payload.MissingCoverage)
	}
}

func TestRunResolvesSelectedConceptsToNodesAndReads(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "GUI feels laggy",
		Plan: Plan{
			RawQuery:            "GUI feels laggy",
			LexiconGenerationID: "GEN-ui",
			SelectedConcepts:    []string{"concept:GEN-ui:N-gui"},
			ConceptDecisions: []ConceptDecision{{
				ConceptID:       "concept:GEN-ui:N-gui",
				Decision:        "selected",
				SelectionReason: "GUI owns the laggy surface.",
				Confidence:      "high",
			}},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Readiness != rt.ReadyReadiness {
		t.Fatalf("Readiness = %q, want query_ready", payload.Readiness)
	}
	if len(payload.AffectedNodes) == 0 {
		t.Fatalf("AffectedNodes = %#v, want selected concept node", payload.AffectedNodes)
	}
	if !hasString(payload.MinimalLiveReads, "src/gui/window.tsx") {
		t.Fatalf("MinimalLiveReads = %#v, want src/gui/window.tsx", payload.MinimalLiveReads)
	}
	if len(payload.QueryPlan.ConceptDecisions) != 1 {
		t.Fatalf("QueryPlan.ConceptDecisions = %#v", payload.QueryPlan.ConceptDecisions)
	}
}

func TestRunSemanticIntakeRetrievesFacetMatchAndRejectsNegativeFalsePositive(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-usage",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-usage",
			SourceKind:  "source",
			SourcePath:  "src/usage/daily_rollup.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-usage",
		}, {
			ID:          "E-cli",
			SourceKind:  "source",
			SourcePath:  "src/cli/launcher.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-cli",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-token-accounting",
			Type:        "capability",
			Title:       "Token Usage Accounting",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-usage"},
			Attrs: map[string]any{
				"aliases": []any{"usage aggregation", "local session records", "daily total", "unit conversion"},
				"domain":  "usage",
				"owner":   "billing-runtime",
			},
		}, {
			ID:          "N-claude-cli-launcher",
			Type:        "capability",
			Title:       "Claude CLI Launcher",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-cli"},
			Attrs: map[string]any{
				"aliases": []any{"CLI launcher invocation behavior", "general Claude CLI startup"},
				"domain":  "cli",
				"owner":   "launcher",
			},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-usage",
			Path:       "src/usage/daily_rollup.go",
			NodeID:     "N-token-accounting",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-usage",
		}, {
			ID:         "P-cli",
			Path:       "src/cli/launcher.go",
			NodeID:     "N-claude-cli-launcher",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-cli",
		}},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "Today says 230M, is that wrong?",
		Plan: Plan{
			RawQuery:            "Today says 230M, is that wrong?",
			LexiconGenerationID: "GEN-usage",
			SemanticIntake: SemanticIntake{
				WorkflowIntent:  "debug",
				NormalizedQuery: "Investigate local CLI session token usage aggregation and daily accounting accuracy.",
				IntentFacets: []string{
					"token accounting",
					"usage aggregation",
					"local session records",
					"daily total",
					"duplicate counting",
					"unit conversion",
				},
				NegativeConstraints: []string{
					"not only CLI launcher invocation behavior",
					"not general model pricing",
				},
				AliasInterpretations: []AliasInterpretation{{
					Alias:      "usage",
					Meaning:    "token usage aggregation",
					Confidence: "high",
				}},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if !hasString(payload.SelectedConcepts, "concept:GEN-usage:N-token-accounting") {
		t.Fatalf("SelectedConcepts = %#v, want token accounting concept", payload.SelectedConcepts)
	}
	if !hasString(payload.RejectedConcepts, "concept:GEN-usage:N-claude-cli-launcher") {
		t.Fatalf("RejectedConcepts = %#v, want CLI launcher false positive rejected", payload.RejectedConcepts)
	}
	if !hasString(payload.MinimalLiveReads, "src/usage/daily_rollup.go") {
		t.Fatalf("MinimalLiveReads = %#v, want usage rollup path", payload.MinimalLiveReads)
	}
	if payload.Readiness != "review" {
		t.Fatalf("Readiness = %q, want review for partial semantic facet coverage", payload.Readiness)
	}
	if payload.RecommendedNextAction != "use_minimal_live_reads_and_review_missing_coverage" {
		t.Fatalf("RecommendedNextAction = %q", payload.RecommendedNextAction)
	}
	if !hasString(payload.MissingCoverage, "semantic_intake_partial_facet_coverage") {
		t.Fatalf("MissingCoverage = %#v, want semantic_intake_partial_facet_coverage", payload.MissingCoverage)
	}
	selectedDecision := findConceptDecision(payload.QueryPlan.ConceptDecisions, "concept:GEN-usage:N-token-accounting", "selected")
	if selectedDecision == nil {
		t.Fatalf("ConceptDecisions = %#v, want selected token accounting decision", payload.QueryPlan.ConceptDecisions)
	}
	if !hasString(selectedDecision.CoveredFacets, "usage aggregation") || !hasString(selectedDecision.CoveredFacets, "daily total") {
		t.Fatalf("selected CoveredFacets = %#v", selectedDecision.CoveredFacets)
	}
	if !hasString(selectedDecision.MatchSources, "semantic_intake") || !hasString(selectedDecision.MatchSources, "intent_facets") {
		t.Fatalf("selected MatchSources = %#v", selectedDecision.MatchSources)
	}
	rejectedDecision := findConceptDecision(payload.QueryPlan.ConceptDecisions, "concept:GEN-usage:N-claude-cli-launcher", "rejected")
	if rejectedDecision == nil {
		t.Fatalf("ConceptDecisions = %#v, want rejected CLI launcher decision", payload.QueryPlan.ConceptDecisions)
	}
	if rejectedDecision.Risk != "lexical false positive" {
		t.Fatalf("rejected Risk = %q, want lexical false positive", rejectedDecision.Risk)
	}
	if !hasString(rejectedDecision.MissingFacets, "token accounting") {
		t.Fatalf("rejected MissingFacets = %#v, want token accounting", rejectedDecision.MissingFacets)
	}
}

func TestRunLocalizedSemanticIntakeSelectsDriverDownloadStallConcept(t *testing.T) {
	paths := queryTestPaths(t)
	seedDriverDownloadGraph(t, paths)

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "PE程序下驱动下载目前好像有点问题，现象就是卡在进度95卡了很久很久 排查下问题",
		Plan: Plan{
			RawQuery:            "PE程序下驱动下载目前好像有点问题，现象就是卡在进度95卡了很久很久 排查下问题",
			LexiconGenerationID: "GEN-driver",
			SemanticIntake: SemanticIntake{
				WorkflowIntent:  "debug",
				NormalizedQuery: "Investigate driver download progress stalling near 95 percent in the WinPE program flow.",
				IntentFacets: []string{
					"WinPE runtime",
					"driver download",
					"progress reporting",
					"95 percent stall",
					"download completion transition",
				},
				NegativeConstraints: []string{
					"not a generic UI status screen issue",
				},
				AliasInterpretations: []AliasInterpretation{{
					Alias:      "PE程序",
					Meaning:    "WinPE environment program flow",
					Confidence: "high",
				}},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	driverConcept := "concept:GEN-driver:N-driver-download"
	uiConcept := "concept:GEN-driver:N-progress-ui"
	if !hasString(payload.SelectedConcepts, driverConcept) {
		t.Fatalf("SelectedConcepts = %#v, want driver download concept", payload.SelectedConcepts)
	}
	if !hasString(payload.RejectedConcepts, uiConcept) {
		t.Fatalf("RejectedConcepts = %#v, want general progress UI rejected", payload.RejectedConcepts)
	}
	if !hasString(payload.MinimalLiveReads, "src/winpe/driver_download.go") {
		t.Fatalf("MinimalLiveReads = %#v, want driver download source", payload.MinimalLiveReads)
	}
	selectedDecision := findConceptDecision(payload.QueryPlan.ConceptDecisions, driverConcept, "selected")
	if selectedDecision == nil {
		t.Fatalf("ConceptDecisions = %#v, want selected driver decision", payload.QueryPlan.ConceptDecisions)
	}
	for _, facet := range []string{"WinPE runtime", "driver download", "progress reporting", "95 percent stall", "download completion transition"} {
		if !hasString(selectedDecision.CoveredFacets, facet) {
			t.Fatalf("selected CoveredFacets = %#v, want %s", selectedDecision.CoveredFacets, facet)
		}
	}
	if !hasString(selectedDecision.MatchSources, "semantic_intake") || !hasString(selectedDecision.MatchSources, "alias") {
		t.Fatalf("selected MatchSources = %#v, want semantic_intake and alias", selectedDecision.MatchSources)
	}
	rejectedDecision := findConceptDecision(payload.QueryPlan.ConceptDecisions, uiConcept, "rejected")
	if rejectedDecision == nil {
		t.Fatalf("ConceptDecisions = %#v, want rejected UI decision", payload.QueryPlan.ConceptDecisions)
	}
	if !hasString(rejectedDecision.MissingFacets, "driver download") {
		t.Fatalf("rejected MissingFacets = %#v, want driver download", rejectedDecision.MissingFacets)
	}
	if rejectedDecision.Risk != "lexical false positive" {
		t.Fatalf("rejected Risk = %q, want lexical false positive", rejectedDecision.Risk)
	}
}

func TestRunInformalSemanticIntakeSelectsDriverFetchCompletion(t *testing.T) {
	paths := queryTestPaths(t)
	seedDriverDownloadGraph(t, paths)

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "installer hangs right before finishing the driver fetch",
		Plan: Plan{
			RawQuery:            "installer hangs right before finishing the driver fetch",
			LexiconGenerationID: "GEN-driver",
			SemanticIntake: SemanticIntake{
				WorkflowIntent:  "debug",
				NormalizedQuery: "Investigate installer driver fetch completion transition hang.",
				IntentFacets: []string{
					"installer flow",
					"driver fetch",
					"completion transition",
				},
				NegativeConstraints: []string{
					"not a generic installer status screen issue",
				},
				AliasInterpretations: []AliasInterpretation{{
					Alias:      "driver fetch",
					Meaning:    "driver download completion transition",
					Confidence: "high",
				}},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	driverConcept := "concept:GEN-driver:N-driver-download"
	installerUIConcept := "concept:GEN-driver:N-installer-progress-ui"
	if !hasString(payload.SelectedConcepts, driverConcept) {
		t.Fatalf("SelectedConcepts = %#v, want driver download concept", payload.SelectedConcepts)
	}
	if !hasString(payload.RejectedConcepts, installerUIConcept) {
		t.Fatalf("RejectedConcepts = %#v, want installer UI progress rejected", payload.RejectedConcepts)
	}
	selectedDecision := findConceptDecision(payload.QueryPlan.ConceptDecisions, driverConcept, "selected")
	if selectedDecision == nil {
		t.Fatalf("ConceptDecisions = %#v, want selected driver decision", payload.QueryPlan.ConceptDecisions)
	}
	for _, facet := range []string{"installer flow", "driver fetch", "completion transition"} {
		if !hasString(selectedDecision.CoveredFacets, facet) {
			t.Fatalf("selected CoveredFacets = %#v, want %s", selectedDecision.CoveredFacets, facet)
		}
	}
	rejectedDecision := findConceptDecision(payload.QueryPlan.ConceptDecisions, installerUIConcept, "rejected")
	if rejectedDecision == nil {
		t.Fatalf("ConceptDecisions = %#v, want rejected installer UI decision", payload.QueryPlan.ConceptDecisions)
	}
	if !hasString(rejectedDecision.MissingFacets, "driver fetch") {
		t.Fatalf("rejected MissingFacets = %#v, want driver fetch", rejectedDecision.MissingFacets)
	}
}

func TestRunSemanticIntakeNegativeConstraintsIgnoreNegationFillers(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-negative",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-token",
			SourceKind:  "source",
			SourcePath:  "src/usage/tokens.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-token",
		}, {
			ID:          "E-general",
			SourceKind:  "source",
			SourcePath:  "src/general/help.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-general",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-token-accounting",
			Type:        "capability",
			Title:       "Token Usage Accounting",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-token"},
			Attrs: map[string]any{
				"aliases": []any{"token accounting", "usage aggregation"},
			},
		}, {
			ID:          "N-general-help",
			Type:        "documentation",
			Title:       "General Help",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-general"},
			Attrs: map[string]any{
				"aliases": []any{"general guide"},
			},
		}},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "usage total looks wrong",
		Plan: Plan{
			RawQuery:            "usage total looks wrong",
			LexiconGenerationID: "GEN-negative",
			SemanticIntake: SemanticIntake{
				WorkflowIntent:      "debug",
				NormalizedQuery:     "Investigate token usage aggregation.",
				IntentFacets:        []string{"token accounting", "usage aggregation"},
				NegativeConstraints: []string{"not general model pricing"},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	generalDecision := findConceptDecision(payload.QueryPlan.ConceptDecisions, "concept:GEN-negative:N-general-help", "rejected")
	if generalDecision != nil && generalDecision.Risk == "lexical false positive" {
		t.Fatalf("general filler term triggered negative false positive: %#v", generalDecision)
	}
}

func TestRunSemanticIntakeFallbackSelectsMultipleFacetCoveringConcepts(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-multi",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-usage",
			SourceKind:  "source",
			SourcePath:  "src/usage/rollup.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-usage",
		}, {
			ID:          "E-session",
			SourceKind:  "source",
			SourcePath:  "src/session/store.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-session",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-usage-rollup",
			Type:        "capability",
			Title:       "Usage Rollup",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-usage"},
			Attrs: map[string]any{
				"aliases": []any{"usage aggregation", "daily total"},
			},
		}, {
			ID:          "N-session-records",
			Type:        "capability",
			Title:       "Session Records",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-session"},
			Attrs: map[string]any{
				"aliases": []any{"local session records", "duplicate counting"},
			},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-usage",
			Path:       "src/usage/rollup.go",
			NodeID:     "N-usage-rollup",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-usage",
		}, {
			ID:         "P-session",
			Path:       "src/session/store.go",
			NodeID:     "N-session-records",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-session",
		}},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "usage total looks duplicated",
		Plan: Plan{
			LexiconGenerationID: "GEN-multi",
			SemanticIntake: SemanticIntake{
				WorkflowIntent:  "debug",
				NormalizedQuery: "Investigate usage aggregation over local session records and duplicate counting.",
				IntentFacets: []string{
					"usage aggregation",
					"daily total",
					"local session records",
					"duplicate counting",
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	for _, want := range []string{"concept:GEN-multi:N-usage-rollup", "concept:GEN-multi:N-session-records"} {
		if !hasString(payload.SelectedConcepts, want) {
			t.Fatalf("SelectedConcepts = %#v, want %s", payload.SelectedConcepts, want)
		}
	}
	for _, want := range []string{"src/usage/rollup.go", "src/session/store.go"} {
		if !hasString(payload.MinimalLiveReads, want) {
			t.Fatalf("MinimalLiveReads = %#v, want %s", payload.MinimalLiveReads, want)
		}
	}
	if hasString(payload.MissingCoverage, "semantic_intake_partial_facet_coverage") {
		t.Fatalf("MissingCoverage = %#v, all facets should be covered across selected concepts", payload.MissingCoverage)
	}
	usageDecision := findConceptDecision(payload.QueryPlan.ConceptDecisions, "concept:GEN-multi:N-usage-rollup", "selected")
	sessionDecision := findConceptDecision(payload.QueryPlan.ConceptDecisions, "concept:GEN-multi:N-session-records", "selected")
	if usageDecision == nil || sessionDecision == nil {
		t.Fatalf("ConceptDecisions = %#v, want both selected concepts", payload.QueryPlan.ConceptDecisions)
	}
	if !strings.Contains(usageDecision.SelectionReason, "runtime fallback") ||
		!strings.Contains(sessionDecision.SelectionReason, "runtime fallback") {
		t.Fatalf("Selection reasons should mark runtime fallback: %#v", payload.QueryPlan.ConceptDecisions)
	}
}

func TestRunReportsPartiallyUnknownSelectedConcepts(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "GUI feels laggy",
		Plan: Plan{
			LexiconGenerationID: "GEN-ui",
			SelectedConcepts: []string{
				"concept:GEN-ui:N-gui",
				"concept:GEN-ui:N-missing",
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.AffectedNodes) == 0 {
		t.Fatalf("AffectedNodes = %#v, want valid GUI node", payload.AffectedNodes)
	}
	if !hasString(payload.MinimalLiveReads, "src/gui/window.tsx") {
		t.Fatalf("MinimalLiveReads = %#v, want src/gui/window.tsx", payload.MinimalLiveReads)
	}
	if !hasString(payload.MissingCoverage, "unknown_selected_concept:concept:GEN-ui:N-missing") {
		t.Fatalf("MissingCoverage = %#v, want unknown selected concept", payload.MissingCoverage)
	}
	if payload.Readiness != "review" {
		t.Fatalf("Readiness = %q, want review", payload.Readiness)
	}
}

func TestRunResolvesStableConceptIDWithColonDelimitedNodeID(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{
			{
				ID:          "E-app",
				SourceKind:  "source",
				SourcePath:  "src/app/main.go",
				CommitSHA:   "abc123",
				Extractor:   "test",
				ContentHash: "hash-app",
			},
			{
				ID:          "E-prefix",
				SourceKind:  "source",
				SourcePath:  "src/prefix/wrong.go",
				CommitSHA:   "abc123",
				Extractor:   "test",
				ContentHash: "hash-prefix",
			},
		},
		Nodes: []store.NodeImport{
			{
				ID:          "capability:app",
				Type:        "capability",
				Title:       "Application Capability",
				Confidence:  "verified",
				EvidenceIDs: []string{"E-app"},
			},
			{
				ID:          "capability",
				Type:        "capability",
				Title:       "Wrong Prefix Capability",
				Confidence:  "verified",
				EvidenceIDs: []string{"E-prefix"},
			},
		},
		PathIndex: []store.PathIndexImport{
			{
				ID:         "P-app",
				Path:       "src/app/main.go",
				NodeID:     "capability:app",
				Relation:   "owns",
				Confidence: "verified",
				EvidenceID: "E-app",
			},
			{
				ID:         "P-prefix",
				Path:       "src/prefix/wrong.go",
				NodeID:     "capability",
				Relation:   "owns",
				Confidence: "verified",
				EvidenceID: "E-prefix",
			},
		},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "implement",
		Query:  "app capability",
		Plan: Plan{
			LexiconGenerationID: "GEN-ui",
			SelectedConcepts:    []string{"concept:GEN-ui:capability:app"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.AffectedNodes) != 1 {
		t.Fatalf("AffectedNodes = %#v, want only colon-delimited app node", payload.AffectedNodes)
	}
	if got := payload.AffectedNodes[0]["id"]; got != "capability:app" {
		t.Fatalf("AffectedNodes[0].id = %q, want capability:app", got)
	}
	if !hasString(payload.MinimalLiveReads, "src/app/main.go") {
		t.Fatalf("MinimalLiveReads = %#v, want src/app/main.go", payload.MinimalLiveReads)
	}
	if hasString(payload.MinimalLiveReads, "src/prefix/wrong.go") {
		t.Fatalf("MinimalLiveReads = %#v, resolved prefix node instead of colon-delimited node", payload.MinimalLiveReads)
	}
}

func TestRunReportsEveryUnknownSelectedConceptAlias(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
	})

	selectedConcepts := []string{
		"concept:GEN-ui:N-missing",
		"concept:GEN-ui:N-missing:alias:gui",
		"concept:GEN-ui:N-missing:path:src-gui",
	}
	payload, err := Run(paths, QueryInput{
		Intent: "implement",
		Query:  "GUI feels laggy",
		Plan: Plan{
			LexiconGenerationID: "GEN-ui",
			SelectedConcepts:    selectedConcepts,
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Readiness != "review" {
		t.Fatalf("Readiness = %q, want review", payload.Readiness)
	}
	for _, conceptID := range selectedConcepts {
		want := "unknown_selected_concept:" + conceptID
		if !hasString(payload.MissingCoverage, want) {
			t.Fatalf("MissingCoverage = %#v, want %s", payload.MissingCoverage, want)
		}
	}
}

func TestRunAcceptsSuffixAndRawSelectedConceptIDs(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "GUI feels laggy",
		Plan: Plan{
			LexiconGenerationID: "GEN-ui",
			SelectedConcepts: []string{
				"concept:GEN-ui:N-gui:alias:gui-shell",
				"N-gui",
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.AffectedNodes) == 0 {
		t.Fatalf("AffectedNodes = %#v, want selected GUI node", payload.AffectedNodes)
	}
	if !hasString(payload.MinimalLiveReads, "src/gui/window.tsx") {
		t.Fatalf("MinimalLiveReads = %#v, want src/gui/window.tsx", payload.MinimalLiveReads)
	}
}

func TestRunReportsSelectedConceptGenerationMismatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Nodes: []store.NodeImport{{
			ID:         "N-gui",
			Type:       "capability",
			Title:      "GUI Shell",
			Confidence: "verified",
		}},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "GUI feels laggy",
		Plan: Plan{
			SelectedConcepts: []string{"concept:GEN-old:N-gui"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if !hasString(payload.MissingCoverage, "selected_concept_generation_mismatch:concept:GEN-old:N-gui") {
		t.Fatalf("MissingCoverage = %#v, want selected concept generation mismatch", payload.MissingCoverage)
	}
	if payload.Readiness != "review" {
		t.Fatalf("Readiness = %q, want review", payload.Readiness)
	}
}

func TestRunReportsLexiconGenerationMismatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-current",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "GUI feels laggy",
		Plan: Plan{
			LexiconGenerationID: "GEN-old",
			SelectedConcepts:    []string{"concept:GEN-old:N-gui"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Readiness != rt.ReviewReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.ReviewReadiness)
	}
	if payload.RecommendedNextAction != "rerun_project_cognition_lexicon" {
		t.Fatalf("RecommendedNextAction = %q", payload.RecommendedNextAction)
	}
	if !hasString(payload.MissingCoverage, "lexicon_generation_mismatch") {
		t.Fatalf("MissingCoverage = %#v, want lexicon_generation_mismatch", payload.MissingCoverage)
	}
	if payload.BaselineKind != rt.BaselineKindBrownfieldFull {
		t.Fatalf("BaselineKind = %q, want %q", payload.BaselineKind, rt.BaselineKindBrownfieldFull)
	}
	if payload.BaselineHealth["baseline_kind"] != rt.BaselineKindBrownfieldFull {
		t.Fatalf("BaselineHealth = %#v, want baseline_kind", payload.BaselineHealth)
	}
	if payload.QueryCoverage["baseline_kind"] != rt.BaselineKindBrownfieldFull {
		t.Fatalf("QueryCoverage = %#v, want baseline_kind", payload.QueryCoverage)
	}
}

func TestRunReportsUnknownSelectedConcept(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
	})

	payload, err := Run(paths, QueryInput{
		Intent: "implement",
		Query:  "GUI feels laggy",
		Plan: Plan{
			LexiconGenerationID: "GEN-ui",
			SelectedConcepts:    []string{"concept:GEN-ui:N-missing"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Readiness != "review" {
		t.Fatalf("Readiness = %q, want review", payload.Readiness)
	}
	if !hasString(payload.MissingCoverage, "unknown_selected_concept:concept:GEN-ui:N-missing") {
		t.Fatalf("MissingCoverage = %#v", payload.MissingCoverage)
	}
}

func queryTestPaths(t *testing.T) rt.Paths {
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

func seedSplitBrainRuntime(t *testing.T, paths rt.Paths) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-db",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence:     []store.EvidenceImport{{ID: "E-app", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-app"}},
		Nodes:        []store.NodeImport{{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-app"}}},
		PathIndex:    []store.PathIndexImport{{ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-app"}},
	})
	if closeErr := st.Close(); closeErr != nil {
		t.Fatal(closeErr)
	}
	if err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func seedDriverDownloadGraph(t *testing.T, paths rt.Paths) {
	t.Helper()
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-driver",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-driver",
			SourceKind:  "source",
			SourcePath:  "src/winpe/driver_download.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-driver",
		}, {
			ID:          "E-progress-ui",
			SourceKind:  "source",
			SourcePath:  "src/ui/progress_view.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-progress",
		}, {
			ID:          "E-installer-ui",
			SourceKind:  "source",
			SourcePath:  "src/installer/progress_screen.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-installer-progress",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-driver-download",
			Type:        "capability",
			Title:       "WinPE Driver Download Completion",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-driver"},
			Attrs: map[string]any{
				"aliases": []any{
					"WinPE runtime",
					"WinPE environment program flow",
					"driver download",
					"driver fetch",
					"progress reporting",
					"95 percent stall",
					"download completion transition",
					"completion transition",
					"installer flow",
				},
				"domain": "driver-download",
				"owner":  "winpe-runtime",
			},
		}, {
			ID:          "N-progress-ui",
			Type:        "ui",
			Title:       "Generic Progress Display",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-progress-ui"},
			Attrs: map[string]any{
				"aliases": []any{
					"general UI progress display",
					"progress reporting",
					"generic progress screen",
				},
				"domain": "ui",
				"owner":  "shell-ui",
			},
		}, {
			ID:          "N-installer-progress-ui",
			Type:        "ui",
			Title:       "Installer Status Screen",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-installer-ui"},
			Attrs: map[string]any{
				"aliases": []any{
					"generic installer status screen",
					"installer progress UI",
					"installer flow",
				},
				"domain": "ui",
				"owner":  "installer-shell",
			},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-driver",
			Path:       "src/winpe/driver_download.go",
			NodeID:     "N-driver-download",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-driver",
		}, {
			ID:         "P-progress-ui",
			Path:       "src/ui/progress_view.go",
			NodeID:     "N-progress-ui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-progress-ui",
		}, {
			ID:         "P-installer-ui",
			Path:       "src/installer/progress_screen.go",
			NodeID:     "N-installer-progress-ui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-installer-ui",
		}},
	})
}

func seedReadyGraph(t *testing.T, paths rt.Paths, input store.ImportInput) {
	t.Helper()
	input = withFixtureAliasRows(input)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(context.Background(), input); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	generationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), generationID, rt.BaselineKindBrownfieldFull); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = generationID
	status.QueryContractVersion = 1
	status.UpdateContractVersion = 1
	status.BaselineKind = rt.BaselineKindBrownfieldFull
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func withFixtureAliasRows(input store.ImportInput) store.ImportInput {
	nodesWithExplicitAliases := map[string]bool{}
	for _, alias := range input.Aliases {
		if alias.TargetType == "node" {
			nodesWithExplicitAliases[alias.TargetID] = true
		}
	}
	for _, node := range input.Nodes {
		if nodesWithExplicitAliases[node.ID] {
			continue
		}
		aliases := []string{node.Title, node.ID, node.Type}
		aliases = append(aliases, testAttrStrings(node.Attrs, "aliases")...)
		seenNormalized := map[string]bool{}
		aliasIndex := 0
		for _, alias := range uniqueStrings(aliases) {
			normalized := strings.ToLower(strings.TrimSpace(alias))
			if normalized == "" || seenNormalized[normalized] {
				continue
			}
			seenNormalized[normalized] = true
			input.Aliases = append(input.Aliases, store.AliasImport{
				ID:              fmt.Sprintf("AI-fixture-%s-%d", node.ID, aliasIndex),
				Alias:           alias,
				NormalizedAlias: normalized,
				TargetType:      "node",
				TargetID:        node.ID,
				Source:          "test_fixture",
				Confidence:      "verified",
			})
			aliasIndex++
		}
	}
	return input
}

func testAttrStrings(attrs map[string]any, key string) []string {
	value, ok := attrs[key]
	if !ok {
		return []string{}
	}
	switch typed := value.(type) {
	case []any:
		out := make([]string, 0, len(typed))
		for _, item := range typed {
			if text, ok := item.(string); ok {
				out = append(out, text)
			}
		}
		return out
	case []string:
		return typed
	case string:
		return []string{typed}
	default:
		return []string{}
	}
}

func seedGreenfieldEmptyRuntime(t *testing.T, paths rt.Paths) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	generationID, err := st.InitializeGreenfieldEmpty(context.Background())
	if closeErr := st.Close(); closeErr != nil {
		t.Fatal(closeErr)
	}
	if err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = generationID
	status.QueryContractVersion = 1
	status.UpdateContractVersion = 1
	status.BaselineKind = rt.BaselineKindGreenfieldEmpty
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func hasString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func countString(values []string, want string) int {
	count := 0
	for _, value := range values {
		if value == want {
			count++
		}
	}
	return count
}

func equalStrings(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for i := range left {
		if left[i] != right[i] {
			return false
		}
	}
	return true
}

func mapStringSliceContains(value any, want string) bool {
	switch typed := value.(type) {
	case []string:
		return hasString(typed, want)
	case []any:
		for _, item := range typed {
			if item == want {
				return true
			}
		}
	}
	return false
}

func candidateHasKeys(candidate map[string]any, keys ...string) bool {
	for _, key := range keys {
		if _, ok := candidate[key]; !ok {
			return false
		}
	}
	return true
}

func findConceptDecision(decisions []ConceptDecision, conceptID, decision string) *ConceptDecision {
	for i := range decisions {
		if decisions[i].ConceptID == conceptID && decisions[i].Decision == decision {
			return &decisions[i]
		}
	}
	return nil
}

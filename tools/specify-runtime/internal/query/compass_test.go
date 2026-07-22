package query

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestCompassQueryDraftReturnsCompactPacketAndTopLevelMinimalReads(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent: "debug",
		Query:  "切模型 failed runtimeOverride deepseek 方块 屏幕小",
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.Mode != "compass" {
		t.Fatalf("Mode = %q, want compass", payload.Mode)
	}
	if payload.Readiness != rt.ReadyReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.ReadyReadiness)
	}
	if payload.FacetSource != "mechanical_query_facets" {
		t.Fatalf("FacetSource = %q, want mechanical_query_facets", payload.FacetSource)
	}
	if len(payload.EvidenceLanes) < 2 {
		t.Fatalf("EvidenceLanes = %#v, want provider/runtime and UI readability lanes", payload.EvidenceLanes)
	}
	if len(payload.MinimalLiveReads) == 0 || len(payload.MinimalLiveReads) > 15 {
		t.Fatalf("MinimalLiveReads = %#v, want compact non-empty list", payload.MinimalLiveReads)
	}
	if total := compassLanePathCount(payload.EvidenceLanes); total > 15 {
		t.Fatalf("lane first_pass_paths total = %d, want <= 15: %#v", total, payload.EvidenceLanes)
	}
	wantReads := dedupeCompassLanePaths(payload.EvidenceLanes)
	if !equalStrings(payload.MinimalLiveReads, wantReads) {
		t.Fatalf("MinimalLiveReads = %#v, want lane path union %#v", payload.MinimalLiveReads, wantReads)
	}
	if compassLaneTitleContains(payload.EvidenceLanes, "Runtime Surface Index") {
		t.Fatalf("fallback title appeared as route lane: %#v", payload.EvidenceLanes)
	}
	if compassLaneTitleContains(payload.EvidenceLanes, "Narrow Looking Runtime Hint") {
		t.Fatalf("boolean fallback title appeared as route lane: %#v", payload.EvidenceLanes)
	}
	if !compassDiagnosticsContain(payload.CoverageDiagnostics, "broad_fallback_suppressed") {
		t.Fatalf("CoverageDiagnostics = %#v, want broad fallback diagnostic", payload.CoverageDiagnostics)
	}
	if !compassDiagnosticsMessageContains(payload.CoverageDiagnostics, "Narrow Looking Runtime Hint") {
		t.Fatalf("CoverageDiagnostics = %#v, want boolean fallback suppression diagnostic", payload.CoverageDiagnostics)
	}
	if payload.QueryFingerprint == "" {
		t.Fatalf("QueryFingerprint is empty")
	}
	if payload.ClaimRetrievalContractVersion != 2 {
		t.Fatalf("ClaimRetrievalContractVersion = %d, want 2", payload.ClaimRetrievalContractVersion)
	}
	if !compassCoveredFacetHasFirstPassRisk(payload.IntentFacets) {
		t.Fatalf("IntentFacets = %#v, want covered facet risk to guard first-pass scope", payload.IntentFacets)
	}
	providerLane := compassLaneByTitle(payload.EvidenceLanes, "Provider Runtime Override")
	if providerLane == nil || len(providerLane.ClaimRefs) != 1 {
		t.Fatalf("provider lane claim refs = %#v, want one compact claim ref", providerLane)
	}
	if providerLane.ClaimRefs[0].ID != "claim:provider-runtime-owner" {
		t.Fatalf("provider claim id = %q", providerLane.ClaimRefs[0].ID)
	}
	if providerLane.ClaimRefs[0].RouteConfidence != "verified" || providerLane.ClaimRefs[0].ConfidenceScope != "route_candidate" {
		t.Fatalf("provider claim ref contract = %#v", providerLane.ClaimRefs[0])
	}
	if providerLane.ClaimRefs[0].Freshness != "fresh" || providerLane.ClaimRefs[0].Stale {
		t.Fatalf("provider claim freshness = %#v", providerLane.ClaimRefs[0])
	}
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	var serialized map[string]any
	if err := json.Unmarshal(data, &serialized); err != nil {
		t.Fatalf("unmarshal payload: %v", err)
	}
	if _, ok := serialized["expansion_ref"]; !ok {
		t.Fatalf("serialized payload missing expansion_ref after expansion storage was wired: %s", data)
	}
}

func TestCompassReviewReadinessWithLanesStaysUsableWithReview(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.Readiness = rt.ReviewReadiness
	status.RecommendedNextAction = "review_project_cognition"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload, err := Compass(paths, CompassInput{
		Intent: "debug",
		Query:  "切模型 failed runtimeOverride deepseek 方块 屏幕小",
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.CompassState != compassStateUsableWithReview {
		t.Fatalf("CompassState = %q, want %q", payload.CompassState, compassStateUsableWithReview)
	}
	if len(payload.EvidenceLanes) == 0 {
		t.Fatalf("EvidenceLanes is empty")
	}
	if payload.RecommendedNextAction.ActionID == compassRecommendedActionExpandBeforeFix {
		t.Fatalf("RecommendedNextAction.ActionID = %q, want first-pass reads action", payload.RecommendedNextAction.ActionID)
	}
}

func TestCompassCJKMechanicalPartialFacetsRequireSemanticIntakeEvenWithLanes(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent: "debug",
		Query:  "我在H5访问环境变量页面会出错 runtimeOverride",
	})
	if err != nil {
		t.Fatal(err)
	}

	if len(payload.EvidenceLanes) == 0 {
		t.Fatalf("EvidenceLanes is empty, test needs a weak but non-empty first pass")
	}
	if payload.AgentNormalization == nil || !payload.AgentNormalization.Required {
		t.Fatalf("AgentNormalization = %#v, want required semantic intake", payload.AgentNormalization)
	}
	if !hasString(payload.AgentNormalization.Triggers, "partial_cjk_mechanical_facets") {
		t.Fatalf("AgentNormalization.Triggers = %#v, want partial CJK facet trigger", payload.AgentNormalization.Triggers)
	}
	if payload.CompassState != compassStateNeedsSemanticIntake {
		t.Fatalf("CompassState = %q, want %q", payload.CompassState, compassStateNeedsSemanticIntake)
	}
	if payload.RecommendedNextAction.ActionID != "write_semantic_intake_from_alias_catalog" {
		t.Fatalf("RecommendedNextAction.ActionID = %q, want semantic intake action", payload.RecommendedNextAction.ActionID)
	}
}

func TestCompassPlainQueryModeIgnoresPlanFacets(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent: "debug",
		Query:  "runtimeOverride",
		Plan: Plan{
			IntentFacets: []string{"provider model switch"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.FacetSource != compassFacetSourceMechanical {
		t.Fatalf("FacetSource = %q, want %q", payload.FacetSource, compassFacetSourceMechanical)
	}
	for _, facet := range payload.IntentFacets {
		if facet.Name == "provider model switch" {
			t.Fatalf("plain query mode used plan facet: %#v", payload.IntentFacets)
		}
	}
}

func TestCompassPlainQueryModeDoesNotScoreWithStalePlanTerms(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent: "debug",
		Query:  "unmatched raw phrase",
		Plan: Plan{
			NormalizedQuery:       "small viewport font fallback",
			IntentFacets:          []string{"small viewport", "font fallback"},
			RepositorySearchTerms: []string{"desktop/src/styles/global.css"},
			SemanticIntake: SemanticIntake{
				NormalizedQuery: "desktop ui readability",
				IntentFacets:    []string{"square glyphs", "window minimum size"},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if compassLaneTitleContains(payload.EvidenceLanes, "Desktop UI Readability") {
		t.Fatalf("plain query mode selected stale-plan lane: %#v", payload.EvidenceLanes)
	}
	if hasString(payload.MinimalLiveReads, "desktop/src/styles/global.css") {
		t.Fatalf("MinimalLiveReads = %#v, want no stale plan path", payload.MinimalLiveReads)
	}
	if len(payload.EvidenceLanes) != 0 {
		t.Fatalf("EvidenceLanes = %#v, want no match from stale plan terms", payload.EvidenceLanes)
	}
}

func TestCompassSemanticIntakeUsesAgentOwnedFacets(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent:    "debug",
		Query:     "切模型 failure 方块",
		InputMode: "semantic_intake",
		Plan: Plan{
			SemanticIntake: SemanticIntake{
				WorkflowIntent:      "debug",
				NormalizedQuery:     "Investigate provider runtime override failure and desktop readability.",
				IntentFacets:        []string{"provider runtime override", "desktop readability"},
				NegativeConstraints: []string{"not only provider catalog metadata"},
				AliasInterpretations: []AliasInterpretation{
					{Alias: "切模型", Meaning: "provider runtime override"},
					{Alias: "方块", Meaning: "desktop readability"},
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.FacetSource != compassFacetSourceSemanticIntake {
		t.Fatalf("FacetSource = %q, want %q", payload.FacetSource, compassFacetSourceSemanticIntake)
	}
	if len(payload.IntentFacets) != 2 {
		t.Fatalf("IntentFacets = %#v, want two semantic intake facets", payload.IntentFacets)
	}
	for _, want := range []string{"provider runtime override", "desktop readability"} {
		if compassFacetMissing(payload.IntentFacets, want) {
			t.Fatalf("IntentFacets = %#v, want %q covered", payload.IntentFacets, want)
		}
	}
	if payload.CompassState != compassStateUsable {
		t.Fatalf("CompassState = %q, want %q; facets=%#v lanes=%#v", payload.CompassState, compassStateUsable, payload.IntentFacets, payload.EvidenceLanes)
	}
}

func TestCompassQueryPlanUsesConceptDecisionsAndPaths(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent:    "debug",
		Query:     "runtime startup issue",
		InputMode: "query_plan",
		Plan: Plan{
			LexiconGenerationID: "GEN-compass-model-switch",
			SelectedConcepts:    []string{"concept:GEN-compass-model-switch:N-provider-runtime"},
			SemanticIntake: SemanticIntake{
				IntentFacets: []string{"provider runtime override", "startup failure"},
			},
			ConceptDecisions: []ConceptDecision{
				{
					ConceptID:     "concept:GEN-compass-model-switch:N-provider-runtime",
					Decision:      "selected",
					CoveredFacets: []string{"provider runtime override", "startup failure"},
					MatchSources:  []string{"semantic_intake", "alias"},
					Confidence:    "high",
					Paths:         []string{"src/server/ws/handler.ts"},
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.FacetSource != compassFacetSourceQueryPlan {
		t.Fatalf("FacetSource = %q, want %q", payload.FacetSource, compassFacetSourceQueryPlan)
	}
	if !hasString(payload.MinimalLiveReads, "src/server/ws/handler.ts") {
		t.Fatalf("MinimalLiveReads = %#v, want selected concept path", payload.MinimalLiveReads)
	}
	if payload.CompassState != compassStateUsable {
		t.Fatalf("CompassState = %q, want %q; facets=%#v lanes=%#v", payload.CompassState, compassStateUsable, payload.IntentFacets, payload.EvidenceLanes)
	}
}

func TestCompassQueryPlanSelectedDecisionPathSelectsOnlySelectedLane(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassPrecisionDecisionPathGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent:    "debug",
		Query:     "unmapped request",
		InputMode: "query_plan",
		Plan: Plan{
			LexiconGenerationID: "GEN-compass-precision-paths",
			SelectedConcepts:    []string{"concept:GEN-compass-precision-paths:N-selected"},
			ConceptDecisions: []ConceptDecision{
				{
					ConceptID:     "concept:GEN-compass-precision-paths:N-selected",
					Decision:      "selected",
					CoveredFacets: []string{"unmapped desired facet"},
					MatchSources:  []string{"agent_selected_path"},
					Confidence:    "high",
					Paths:         []string{"src/selected/only.ts"},
				},
				{
					ConceptID:     "concept:GEN-compass-precision-paths:N-rejected",
					Decision:      "rejected",
					CoveredFacets: []string{"rejected-only capability"},
					MatchSources:  []string{"agent_rejected_path"},
					Confidence:    "high",
					Paths:         []string{"src/rejected/only.ts"},
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if !hasString(payload.MinimalLiveReads, "src/selected/only.ts") {
		t.Fatalf("MinimalLiveReads = %#v, want selected decision path", payload.MinimalLiveReads)
	}
	if hasString(payload.MinimalLiveReads, "src/rejected/only.ts") {
		t.Fatalf("MinimalLiveReads = %#v, want rejected decision path excluded", payload.MinimalLiveReads)
	}
	if compassLaneTitleContains(payload.EvidenceLanes, "Rejected Precision Owner") {
		t.Fatalf("EvidenceLanes = %#v, want rejected decision lane excluded", payload.EvidenceLanes)
	}
	if compassLaneTitleContains(payload.EvidenceLanes, "Unrelated Precision Owner") {
		t.Fatalf("EvidenceLanes = %#v, want unrelated raw-query lane excluded when selected concepts exist", payload.EvidenceLanes)
	}
}

func TestCompassQueryPlanRejectedConceptHardFilterSuppressesRawQueryMatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassPrecisionDecisionPathGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent:    "debug",
		Query:     "rejected-only capability",
		InputMode: "query_plan",
		Plan: Plan{
			LexiconGenerationID: "GEN-compass-precision-paths",
			RejectedConcepts:    []string{"concept:GEN-compass-precision-paths:N-rejected"},
			ConceptDecisions: []ConceptDecision{
				{
					ConceptID:     "concept:GEN-compass-precision-paths:N-rejected",
					Decision:      "rejected",
					CoveredFacets: []string{"rejected-only capability"},
					MatchSources:  []string{"raw_query"},
					Confidence:    "high",
					Paths:         []string{"src/rejected/only.ts"},
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if compassLaneTitleContains(payload.EvidenceLanes, "Rejected Precision Owner") {
		t.Fatalf("EvidenceLanes = %#v, want rejected raw-query lane excluded", payload.EvidenceLanes)
	}
	if hasString(payload.MinimalLiveReads, "src/rejected/only.ts") {
		t.Fatalf("MinimalLiveReads = %#v, want rejected raw-query path excluded", payload.MinimalLiveReads)
	}
}

func TestCompassQueryPlanPrioritizesSelectedPathInsideLaneBudget(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassWidePrecisionPathGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent:    "debug",
		Query:     "unmapped request",
		InputMode: "query_plan",
		Plan: Plan{
			LexiconGenerationID: "GEN-compass-wide-paths",
			ConceptDecisions: []ConceptDecision{
				{
					ConceptID:     "concept:GEN-compass-wide-paths:N-wide-owner",
					Decision:      "selected",
					CoveredFacets: []string{"wide selected path"},
					MatchSources:  []string{"agent_selected_path"},
					Confidence:    "high",
					Paths:         []string{"src/wide/path-07.ts"},
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if !hasString(payload.MinimalLiveReads, "src/wide/path-07.ts") {
		t.Fatalf("MinimalLiveReads = %#v, want selected path inside lane budget", payload.MinimalLiveReads)
	}
	if len(payload.EvidenceLanes) != 1 {
		t.Fatalf("EvidenceLanes = %#v, want one selected lane", payload.EvidenceLanes)
	}
	if got := len(payload.EvidenceLanes[0].FirstPassPaths); got > maxCompassPathsPerLane {
		t.Fatalf("FirstPassPaths count = %d, want <= %d", got, maxCompassPathsPerLane)
	}
	if len(payload.MinimalLiveReads) > maxCompassReads {
		t.Fatalf("MinimalLiveReads count = %d, want <= %d", len(payload.MinimalLiveReads), maxCompassReads)
	}
}

func TestCompassQueryPlanFingerprintIncludesPrecisionPaths(t *testing.T) {
	base := CompassInput{
		Intent:    "debug",
		Query:     "runtime startup issue",
		InputMode: "query_plan",
		Plan: Plan{
			LexiconGenerationID:   "GEN-compass-model-switch",
			RepositorySearchTerms: []string{"runtimeOverride"},
			Paths:                 []string{"src/server/ws/handler.ts"},
			SelectedConcepts:      []string{"concept:GEN-compass-model-switch:N-provider-runtime"},
			SemanticIntake: SemanticIntake{
				IntentFacets: []string{"provider runtime override"},
			},
			ConceptDecisions: []ConceptDecision{
				{
					ConceptID:     "concept:GEN-compass-model-switch:N-provider-runtime",
					Decision:      "selected",
					CoveredFacets: []string{"provider runtime override"},
					MatchSources:  []string{"semantic_intake", "alias"},
					Paths:         []string{"src/server/ws/handler.ts"},
				},
			},
		},
	}

	withDifferentPlanPath := base
	withDifferentPlanPath.Plan.Paths = []string{"desktop/src/components/controls/ModelSelector.tsx"}
	if compassFingerprint(base) == compassFingerprint(withDifferentPlanPath) {
		t.Fatalf("fingerprints matched after plan path changed")
	}

	withDifferentDecisionPath := base
	withDifferentDecisionPath.Plan.ConceptDecisions = []ConceptDecision{
		{
			ConceptID:     "concept:GEN-compass-model-switch:N-provider-runtime",
			Decision:      "selected",
			CoveredFacets: []string{"provider runtime override"},
			MatchSources:  []string{"semantic_intake", "alias"},
			Paths:         []string{"desktop/src/components/controls/ModelSelector.tsx"},
		},
	}
	if compassFingerprint(base) == compassFingerprint(withDifferentDecisionPath) {
		t.Fatalf("fingerprints matched after selected decision path changed")
	}

	plainBase := base
	plainBase.InputMode = "query"
	plainDifferentDecisionPath := withDifferentDecisionPath
	plainDifferentDecisionPath.InputMode = "query"
	if compassFingerprint(plainBase) != compassFingerprint(plainDifferentDecisionPath) {
		t.Fatalf("plain query fingerprints differed after plan precision path changed")
	}
}

func TestCompassQueryPlanFallsBackToPlanFacetsWhenSemanticIntakeFacetsEmpty(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent:    "debug",
		Query:     "runtimeOverride",
		InputMode: "query_plan",
		Plan: Plan{
			IntentFacets: []string{"runtimeOverride"},
			SemanticIntake: SemanticIntake{
				NormalizedQuery:     "Investigate provider runtime override without narrowing facets.",
				NegativeConstraints: []string{"not only provider catalog metadata"},
				AliasInterpretations: []AliasInterpretation{
					{Alias: "切模型", Meaning: "provider runtime override"},
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.FacetSource != compassFacetSourceQueryPlan {
		t.Fatalf("FacetSource = %q, want %q", payload.FacetSource, compassFacetSourceQueryPlan)
	}
	if len(payload.IntentFacets) != 1 || payload.IntentFacets[0].Name != "runtimeOverride" {
		t.Fatalf("IntentFacets = %#v, want top-level query plan facet", payload.IntentFacets)
	}
}

func TestCompassQueryPlanModeWithCoveredFacetsIsUsable(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent:    "debug",
		Query:     "runtimeOverride",
		InputMode: "query_plan",
		Plan: Plan{
			SemanticIntake: SemanticIntake{
				IntentFacets: []string{"runtimeOverride"},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.FacetSource != compassFacetSourceQueryPlan {
		t.Fatalf("FacetSource = %q, want %q", payload.FacetSource, compassFacetSourceQueryPlan)
	}
	if payload.CompassState != compassStateUsable {
		t.Fatalf("CompassState = %q, want %q; facets=%#v lanes=%#v", payload.CompassState, compassStateUsable, payload.IntentFacets, payload.EvidenceLanes)
	}
}

func TestCompassBlockedReadinessSerializesSummary(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.Readiness = rt.NeedsRebuildReadiness
	status.RecommendedNextAction = "run_map_scan_build"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload, err := Compass(paths, CompassInput{
		Intent: "debug",
		Query:  "runtimeOverride",
	})
	if err != nil {
		t.Fatal(err)
	}
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	var encoded map[string]any
	if err := json.Unmarshal(data, &encoded); err != nil {
		t.Fatal(err)
	}
	summary, ok := encoded["summary"].(string)
	if !ok || summary == "" {
		t.Fatalf("serialized summary = %#v in %s, want non-empty string", encoded["summary"], data)
	}
}

func TestIsBroadFallbackCandidateSuppressesBooleanAttr(t *testing.T) {
	candidate := rankedConceptCandidate{
		row: store.ConceptCandidateRow{
			NodeType: "capability",
			Title:    "Innocuous Runtime Hint",
		},
		attrs: map[string]any{"coverage_fallback": true},
	}

	suppressed, reason := isBroadFallbackCandidate(candidate)

	if !suppressed {
		t.Fatalf("suppressed = false, want true")
	}
	if reason != "attrs_coverage_fallback" {
		t.Fatalf("reason = %q, want attrs_coverage_fallback", reason)
	}
}

func TestCompassClaimsRerankOnlyPositiveMatchedCandidates(t *testing.T) {
	rows := []store.ConceptCandidateRow{
		compassRankingRow("N-supported", "A Supported Route", "routing target"),
		compassRankingRow("N-verified", "B Verified Route", "routing target"),
		compassRankingRow("N-neutral", "C Neutral Route", "routing target"),
		compassRankingRow("N-stale", "D Stale Route", "routing target"),
		compassRankingRow("N-contradicted", "E Contradicted Route", "routing target"),
		compassRankingRow("N-claim-only", "F Claim Only Route", "unrelated surface"),
	}
	candidates := compassCandidates(rows, []string{"routing"}, false, compassConceptFilter{})
	summaries := []store.GraphClaimLifecycleSummary{
		{NodeID: "N-supported", ClaimCount: 20, FreshSupportedCount: 20},
		{NodeID: "N-verified", ClaimCount: 1, FreshVerifiedCount: 1},
		{NodeID: "N-stale", ClaimCount: 1, StaleCount: 1},
		{NodeID: "N-contradicted", ClaimCount: 1, ContradictedCount: 1},
		{NodeID: "N-claim-only", ClaimCount: 1, FreshVerifiedCount: 1},
	}

	candidates = applyClaimRanking(candidates, summaries)

	if got := len(candidates); got != 5 {
		t.Fatalf("candidate count = %d, want five base matches and no claim-only match", got)
	}
	wantOrder := []string{"N-supported", "N-verified", "N-neutral", "N-stale", "N-contradicted"}
	for index, wantNodeID := range wantOrder {
		if got := candidates[index].ranked.row.NodeID; got != wantNodeID {
			t.Fatalf("candidate[%d].node_id = %q, want %q; candidates=%#v", index, got, wantNodeID, candidates)
		}
	}
	wantScores := map[string]struct {
		adjustment int
		score      int
		state      string
	}{
		"N-supported":    {adjustment: 1, score: 11, state: "supported"},
		"N-verified":     {adjustment: 1, score: 11, state: "verified_in_graph_generation"},
		"N-neutral":      {adjustment: 0, score: 10, state: "none"},
		"N-stale":        {adjustment: -1, score: 9, state: "stale"},
		"N-contradicted": {adjustment: -2, score: 8, state: "contradicted"},
	}
	for _, candidate := range candidates {
		want := wantScores[candidate.ranked.row.NodeID]
		if candidate.matchScore != 10 || candidate.ranked.score != want.score {
			t.Fatalf("%s scores = match:%d final:%d, want match:10 final:%d", candidate.ranked.row.NodeID, candidate.matchScore, candidate.ranked.score, want.score)
		}
		if candidate.claimRanking.State != want.state || candidate.claimRanking.Adjustment != want.adjustment {
			t.Fatalf("%s claim ranking = %#v, want state=%q adjustment=%d", candidate.ranked.row.NodeID, candidate.claimRanking, want.state, want.adjustment)
		}
		if want.state != "none" && !candidate.claimRanking.LiveVerificationRequired {
			t.Fatalf("%s claim ranking removed live verification: %#v", candidate.ranked.row.NodeID, candidate.claimRanking)
		}
	}
	raw := candidatesForExpansion(candidates)
	if raw[0]["match_score"] != 10 || raw[0]["score"] != 11 {
		t.Fatalf("raw candidate scores = %#v, want transparent match/final scores", raw[0])
	}
}

func TestCompassClaimBoostCannotOvertakeStrongMatch(t *testing.T) {
	rows := []store.ConceptCandidateRow{
		compassRankingRow("N-strong", "Strong Match", "over"),
		compassRankingRow("N-weak", "Weak Match", "override setting"),
	}
	candidates := compassCandidates(rows, []string{"over"}, false, compassConceptFilter{})
	candidates = applyClaimRanking(candidates, []store.GraphClaimLifecycleSummary{{
		NodeID: "N-weak", ClaimCount: 100, FreshSupportedCount: 100,
	}})

	if got := candidates[0].ranked.row.NodeID; got != "N-strong" {
		t.Fatalf("top candidate = %q, want stronger lexical match; candidates=%#v", got, candidates)
	}
	if candidates[1].claimRanking.Adjustment != 1 {
		t.Fatalf("weak claim adjustment = %d, want bounded +1", candidates[1].claimRanking.Adjustment)
	}
}

func TestCompassUnsafeClaimStatesRequireLiveReconciliation(t *testing.T) {
	tests := []struct {
		name               string
		state              claim.State
		freshness          claim.Freshness
		wantDiagnosticKind string
		wantAction         string
	}{
		{
			name: "contradicted", state: claim.StateContradicted, freshness: claim.FreshnessFresh,
			wantDiagnosticKind: "contradicted_claim_signal", wantAction: "reconcile_contradicted_claim_with_live_repository",
		},
		{
			name: "stale", state: claim.StateStale, freshness: claim.FreshnessStale,
			wantDiagnosticKind: "stale_claim_signal", wantAction: "refresh_claim_evidence_then_verify_live_repository",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			paths := queryTestPaths(t)
			seedCompassUnsafeClaimGraph(t, paths, tt.state, tt.freshness)

			payload, err := Compass(paths, CompassInput{
				Intent: "debug", Query: "runtime route", InputMode: compassInputModeSemanticIntake,
				Plan: Plan{SemanticIntake: SemanticIntake{
					NormalizedQuery: "runtime route", IntentFacets: []string{"runtime route"},
				}},
			})
			if err != nil {
				t.Fatal(err)
			}

			if payload.CompassState != compassStateUsableWithReview {
				t.Fatalf("CompassState = %q, want %q", payload.CompassState, compassStateUsableWithReview)
			}
			if !compassDiagnosticsContain(payload.CoverageDiagnostics, tt.wantDiagnosticKind) {
				t.Fatalf("CoverageDiagnostics = %#v, want %q", payload.CoverageDiagnostics, tt.wantDiagnosticKind)
			}
			if payload.RecommendedNextAction.ActionID != compassRecommendedActionReconcileClaims {
				t.Fatalf("RecommendedNextAction.ActionID = %q, want %q", payload.RecommendedNextAction.ActionID, compassRecommendedActionReconcileClaims)
			}
			if len(payload.EvidenceLanes) != 1 || payload.EvidenceLanes[0].ClaimRanking == nil {
				t.Fatalf("EvidenceLanes = %#v, want one claim-ranked lane", payload.EvidenceLanes)
			}
			ranking := payload.EvidenceLanes[0].ClaimRanking
			if !ranking.ReconciliationRequired || !ranking.LiveVerificationRequired || ranking.ReconciliationAction != tt.wantAction {
				t.Fatalf("ClaimRanking = %#v, want live reconciliation action %q", ranking, tt.wantAction)
			}
			if len(payload.EvidenceLanes[0].ClaimRefs) != 1 || !payload.EvidenceLanes[0].ClaimRefs[0].LiveVerificationRequired {
				t.Fatalf("ClaimRefs = %#v, want explicit live verification gate", payload.EvidenceLanes[0].ClaimRefs)
			}
		})
	}
}

func compassRankingRow(nodeID, title, alias string) store.ConceptCandidateRow {
	return store.ConceptCandidateRow{
		GenerationID: "GEN-ranking", NodeID: nodeID, NodeType: "capability", Title: title,
		Confidence: "verified", Paths: []string{"src/" + nodeID + ".go"},
		Aliases: []store.ConceptAliasRow{{Alias: alias, NormalizedAlias: strings.ToLower(alias)}},
	}
}

func seedCompassUnsafeClaimGraph(t *testing.T, paths rt.Paths, state claim.State, freshness claim.Freshness) {
	t.Helper()
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-unsafe-claim-" + string(state),
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID: "E-route", SourceKind: "source", SourcePath: "src/runtime/route.go",
			CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-route",
		}},
		Nodes: []store.NodeImport{{
			ID: "N-route", Type: "capability", Title: "Runtime Route", Confidence: "verified",
			EvidenceIDs: []string{"E-route"}, Attrs: map[string]any{"aliases": []any{"runtime route"}},
		}},
		Claims: []store.ClaimImport{{
			ID: "claim:runtime-route", NodeID: "N-route", GraphClaimType: "runtime_owner",
			Summary: "Runtime route owns dispatch", State: state, Freshness: freshness,
			StateReason: "test_unsafe_claim", SupportingEvidenceIDs: []string{"E-route"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID: "P-route", Path: "src/runtime/route.go", NodeID: "N-route",
			Relation: "owns", Confidence: "verified", EvidenceID: "E-route",
		}},
	})
}

func seedCompassModelSwitchGraph(t *testing.T, paths rt.Paths) {
	t.Helper()
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-compass-model-switch",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{
			{ID: "E-model-selector", SourceKind: "source", SourcePath: "desktop/src/components/controls/ModelSelector.tsx", CommitSHA: "abc123", Span: "18:1-44:2", Extractor: "test", ContentHash: "hash-model"},
			{ID: "E-ws-handler", SourceKind: "source", SourcePath: "src/server/ws/handler.ts", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-ws"},
			{ID: "E-fonts", SourceKind: "source", SourcePath: "desktop/src/styles/global.css", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-fonts"},
			{ID: "E-window", SourceKind: "source", SourcePath: "desktop/src-tauri/tauri.conf.json", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-window"},
			{ID: "E-bool-fallback", SourceKind: "source", SourcePath: "src/runtime/fallback_index.ts", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-bool-fallback"},
		},
		Nodes: []store.NodeImport{
			{
				ID: "N-provider-runtime", Type: "capability", Title: "Provider Runtime Override", Confidence: "verified", EvidenceIDs: []string{"E-model-selector", "E-ws-handler"},
				Attrs: map[string]any{
					"aliases":            []any{"runtimeOverride", "provider model switch", "deepseek model id", "CLI startup failure"},
					"owner":              "runtime-session",
					"domain":             "provider-runtime",
					"verification_hints": []any{"server runtime override rollback regression"},
					"before_fix_claim":   []any{"Confirm provider registry is not the owner.", "Confirm failed switch does not poison next startup truth."},
					"followup_surfaces":  []any{"provider registry", "session resume", "startup diagnostics redaction"},
				},
			},
			{
				ID: "N-ui-readability", Type: "ui", Title: "Desktop UI Readability", Confidence: "verified", EvidenceIDs: []string{"E-fonts", "E-window"},
				Attrs: map[string]any{
					"aliases":            []any{"square glyphs", "font fallback", "small viewport", "window minimum size"},
					"owner":              "desktop-shell",
					"domain":             "desktop-ui",
					"verification_hints": []any{"desktop rendering smoke test"},
					"followup_surfaces":  []any{"chat error rendering", "zoom persistence"},
				},
			},
			{
				ID: "N-fallback", Type: "coverage_fallback", Title: "Runtime Surface Index", Confidence: "low",
				Attrs: map[string]any{
					"aliases":             []any{"runtimeOverride", "deepseek", "desktop"},
					"fallback_provenance": "coverage_paths_without_existing_nodes",
					"path_count":          3000,
				},
			},
			{
				ID: "N-bool-fallback", Type: "capability", Title: "Narrow Looking Runtime Hint", Confidence: "low", EvidenceIDs: []string{"E-bool-fallback"},
				Attrs: map[string]any{
					"aliases":           []any{"runtimeOverride", "deepseek"},
					"coverage_fallback": true,
				},
			},
		},
		Claims: []store.ClaimImport{
			{ID: "claim:provider-runtime-owner", NodeID: "N-provider-runtime", GraphClaimType: "runtime_owner", Summary: "Provider runtime owns model override behavior", State: "supported", Freshness: "fresh", StateReason: "supporting_evidence", SupportingEvidenceIDs: []string{"E-model-selector"}},
			{ID: "claim:ui-readability-owner", NodeID: "N-ui-readability", GraphClaimType: "ui_owner", Summary: "Desktop shell owns readability behavior", State: "supported", Freshness: "fresh", StateReason: "supporting_evidence", SupportingEvidenceIDs: []string{"E-fonts"}},
		},
		PathIndex: []store.PathIndexImport{
			{ID: "P-model-selector", Path: "desktop/src/components/controls/ModelSelector.tsx", NodeID: "N-provider-runtime", Relation: "owns", Confidence: "verified", EvidenceID: "E-model-selector"},
			{ID: "P-ws-handler", Path: "src/server/ws/handler.ts", NodeID: "N-provider-runtime", Relation: "owns", Confidence: "verified", EvidenceID: "E-ws-handler"},
			{ID: "P-fonts", Path: "desktop/src/styles/global.css", NodeID: "N-ui-readability", Relation: "owns", Confidence: "verified", EvidenceID: "E-fonts"},
			{ID: "P-window", Path: "desktop/src-tauri/tauri.conf.json", NodeID: "N-ui-readability", Relation: "owns", Confidence: "verified", EvidenceID: "E-window"},
			{ID: "P-bool-fallback", Path: "src/runtime/fallback_index.ts", NodeID: "N-bool-fallback", Relation: "owns", Confidence: "low", EvidenceID: "E-bool-fallback"},
		},
	})
}

func seedCompassPrecisionDecisionPathGraph(t *testing.T, paths rt.Paths) {
	t.Helper()
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-compass-precision-paths",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{
			{ID: "E-selected", SourceKind: "source", SourcePath: "src/selected/only.ts", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-selected"},
			{ID: "E-rejected", SourceKind: "source", SourcePath: "src/rejected/only.ts", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-rejected"},
			{ID: "E-unrelated", SourceKind: "source", SourcePath: "src/unrelated/only.ts", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-unrelated"},
		},
		Nodes: []store.NodeImport{
			{
				ID: "N-selected", Type: "capability", Title: "Selected Precision Owner", Confidence: "verified", EvidenceIDs: []string{"E-selected"},
				Attrs: map[string]any{
					"aliases": []any{"selected precision owner"},
					"owner":   "selected-owner",
					"domain":  "selected-domain",
				},
			},
			{
				ID: "N-rejected", Type: "capability", Title: "Rejected Precision Owner", Confidence: "verified", EvidenceIDs: []string{"E-rejected"},
				Attrs: map[string]any{
					"aliases": []any{"rejected-only capability"},
					"owner":   "rejected-owner",
					"domain":  "rejected-domain",
				},
			},
			{
				ID: "N-unrelated", Type: "capability", Title: "Unrelated Precision Owner", Confidence: "verified", EvidenceIDs: []string{"E-unrelated"},
				Attrs: map[string]any{
					"aliases": []any{"unmapped request"},
					"owner":   "unrelated-owner",
					"domain":  "unrelated-domain",
				},
			},
		},
		PathIndex: []store.PathIndexImport{
			{ID: "P-selected", Path: "src/selected/only.ts", NodeID: "N-selected", Relation: "owns", Confidence: "verified", EvidenceID: "E-selected"},
			{ID: "P-rejected", Path: "src/rejected/only.ts", NodeID: "N-rejected", Relation: "owns", Confidence: "verified", EvidenceID: "E-rejected"},
			{ID: "P-unrelated", Path: "src/unrelated/only.ts", NodeID: "N-unrelated", Relation: "owns", Confidence: "verified", EvidenceID: "E-unrelated"},
		},
	})
}

func seedCompassWidePrecisionPathGraph(t *testing.T, paths rt.Paths) {
	t.Helper()
	evidence := make([]store.EvidenceImport, 0, 7)
	pathIndex := make([]store.PathIndexImport, 0, 7)
	for index := 1; index <= 7; index++ {
		id := "wide-0" + string(rune('0'+index))
		path := "src/wide/path-0" + string(rune('0'+index)) + ".ts"
		evidence = append(evidence, store.EvidenceImport{
			ID:          "E-" + id,
			SourceKind:  "source",
			SourcePath:  path,
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-" + id,
		})
		pathIndex = append(pathIndex, store.PathIndexImport{
			ID:         "P-" + id,
			Path:       path,
			NodeID:     "N-wide-owner",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-" + id,
		})
	}
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-compass-wide-paths",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence:     evidence,
		Nodes: []store.NodeImport{
			{
				ID: "N-wide-owner", Type: "capability", Title: "Wide Precision Owner", Confidence: "verified", EvidenceIDs: []string{"E-wide-01", "E-wide-02", "E-wide-03", "E-wide-04", "E-wide-05", "E-wide-06", "E-wide-07"},
				Attrs: map[string]any{
					"aliases": []any{"wide precision owner"},
					"owner":   "wide-owner",
					"domain":  "wide-domain",
				},
			},
		},
		PathIndex: pathIndex,
	})
}

func dedupeCompassLanePaths(lanes []EvidenceLane) []string {
	values := []string{}
	for _, lane := range lanes {
		for _, path := range lane.FirstPassPaths {
			values = appendMissingCoverage(values, path.Path)
		}
	}
	return values
}

func compassLaneTitleContains(lanes []EvidenceLane, title string) bool {
	for _, lane := range lanes {
		if lane.Title == title {
			return true
		}
	}
	return false
}

func compassLaneByTitle(lanes []EvidenceLane, title string) *EvidenceLane {
	for index := range lanes {
		if lanes[index].Title == title {
			return &lanes[index]
		}
	}
	return nil
}

func compassLanePathCount(lanes []EvidenceLane) int {
	count := 0
	for _, lane := range lanes {
		count += len(lane.FirstPassPaths)
	}
	return count
}

func compassDiagnosticsContain(diagnostics []CoverageDiagnostic, kind string) bool {
	for _, diagnostic := range diagnostics {
		if diagnostic.Kind == kind {
			return true
		}
	}
	return false
}

func compassDiagnosticsMessageContains(diagnostics []CoverageDiagnostic, value string) bool {
	for _, diagnostic := range diagnostics {
		if diagnostic.Message == "" {
			continue
		}
		if diagnostic.Message == value || strings.Contains(diagnostic.Message, value) {
			return true
		}
	}
	return false
}

func compassCoveredFacetHasFirstPassRisk(facets []CompassIntentFacet) bool {
	for _, facet := range facets {
		if facet.Coverage == "covered_for_first_pass" && facet.Risk == "first evidence path, not final edit scope" {
			return true
		}
	}
	return false
}

func compassFacetMissing(facets []CompassIntentFacet, name string) bool {
	for _, facet := range facets {
		if facet.Name == name {
			return facet.Coverage == "missing"
		}
	}
	return true
}

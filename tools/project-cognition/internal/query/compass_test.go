package query

import (
	"encoding/json"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
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
	if !compassCoveredFacetHasFirstPassRisk(payload.IntentFacets) {
		t.Fatalf("IntentFacets = %#v, want covered facet risk to guard first-pass scope", payload.IntentFacets)
	}
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	var serialized map[string]any
	if err := json.Unmarshal(data, &serialized); err != nil {
		t.Fatalf("unmarshal payload: %v", err)
	}
	if _, ok := serialized["expansion_ref"]; ok {
		t.Fatalf("serialized payload contains expansion_ref before expansion storage is wired: %s", data)
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
	if payload.RecommendedNextAction == compassRecommendedActionExpandBeforeFix {
		t.Fatalf("RecommendedNextAction = %q, want first-pass reads action", payload.RecommendedNextAction)
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

func seedCompassModelSwitchGraph(t *testing.T, paths rt.Paths) {
	t.Helper()
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-compass-model-switch",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{
			{ID: "E-model-selector", SourceKind: "source", SourcePath: "desktop/src/components/controls/ModelSelector.tsx", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-model"},
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
		PathIndex: []store.PathIndexImport{
			{ID: "P-model-selector", Path: "desktop/src/components/controls/ModelSelector.tsx", NodeID: "N-provider-runtime", Relation: "owns", Confidence: "verified", EvidenceID: "E-model-selector"},
			{ID: "P-ws-handler", Path: "src/server/ws/handler.ts", NodeID: "N-provider-runtime", Relation: "owns", Confidence: "verified", EvidenceID: "E-ws-handler"},
			{ID: "P-fonts", Path: "desktop/src/styles/global.css", NodeID: "N-ui-readability", Relation: "owns", Confidence: "verified", EvidenceID: "E-fonts"},
			{ID: "P-window", Path: "desktop/src-tauri/tauri.conf.json", NodeID: "N-ui-readability", Relation: "owns", Confidence: "verified", EvidenceID: "E-window"},
			{ID: "P-bool-fallback", Path: "src/runtime/fallback_index.ts", NodeID: "N-bool-fallback", Relation: "owns", Confidence: "low", EvidenceID: "E-bool-fallback"},
		},
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

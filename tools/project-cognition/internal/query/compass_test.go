package query

import (
	"encoding/json"
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
	wantReads := dedupeCompassLanePaths(payload.EvidenceLanes)
	if !equalStrings(payload.MinimalLiveReads, wantReads) {
		t.Fatalf("MinimalLiveReads = %#v, want lane path union %#v", payload.MinimalLiveReads, wantReads)
	}
	if compassLaneTitleContains(payload.EvidenceLanes, "Runtime Surface Index") {
		t.Fatalf("fallback title appeared as route lane: %#v", payload.EvidenceLanes)
	}
	if !compassDiagnosticsContain(payload.CoverageDiagnostics, "broad_fallback_suppressed") {
		t.Fatalf("CoverageDiagnostics = %#v, want broad fallback diagnostic", payload.CoverageDiagnostics)
	}
	if payload.QueryFingerprint == "" {
		t.Fatalf("QueryFingerprint is empty")
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
		},
		PathIndex: []store.PathIndexImport{
			{ID: "P-model-selector", Path: "desktop/src/components/controls/ModelSelector.tsx", NodeID: "N-provider-runtime", Relation: "owns", Confidence: "verified", EvidenceID: "E-model-selector"},
			{ID: "P-ws-handler", Path: "src/server/ws/handler.ts", NodeID: "N-provider-runtime", Relation: "owns", Confidence: "verified", EvidenceID: "E-ws-handler"},
			{ID: "P-fonts", Path: "desktop/src/styles/global.css", NodeID: "N-ui-readability", Relation: "owns", Confidence: "verified", EvidenceID: "E-fonts"},
			{ID: "P-window", Path: "desktop/src-tauri/tauri.conf.json", NodeID: "N-ui-readability", Relation: "owns", Confidence: "verified", EvidenceID: "E-window"},
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

func compassDiagnosticsContain(diagnostics []CoverageDiagnostic, kind string) bool {
	for _, diagnostic := range diagnostics {
		if diagnostic.Kind == kind {
			return true
		}
	}
	return false
}

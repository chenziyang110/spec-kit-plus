package query

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

func TestCompassWritesExpansionBundleAndExpandReturnsSection(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	compass, err := Compass(paths, CompassInput{
		Intent: "debug",
		Query:  "切模型 failed runtimeOverride deepseek 方块 屏幕小",
	})
	if err != nil {
		t.Fatal(err)
	}
	if compass.ExpansionRef == nil {
		t.Fatalf("ExpansionRef is nil")
	}
	if compass.ExpansionRef.ID != "exp-"+compass.QueryFingerprint {
		t.Fatalf("ExpansionRef.ID = %q, want exp- + fingerprint %q", compass.ExpansionRef.ID, compass.QueryFingerprint)
	}
	if compass.ExpansionRef.StaleBehavior != expansionRefStaleBehavior {
		t.Fatalf("StaleBehavior = %q, want %q", compass.ExpansionRef.StaleBehavior, expansionRefStaleBehavior)
	}
	if compass.ExpansionRef.StaleBehavior == expansionRecommendedActionRerun {
		t.Fatalf("StaleBehavior = %q, want behavior statement distinct from rerun action", compass.ExpansionRef.StaleBehavior)
	}
	for _, section := range []string{"related_paths", "raw_candidates", "coverage_gaps", "graph_neighbors", "claim_evidence"} {
		if _, ok := compass.ExpansionRef.AvailableSections[section]; !ok {
			t.Fatalf("ExpansionRef.AvailableSections missing %q: %#v", section, compass.ExpansionRef.AvailableSections)
		}
	}

	defaultExpanded, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID})
	if err != nil {
		t.Fatal(err)
	}
	if defaultExpanded.Status != "ok" {
		t.Fatalf("Status = %q, want ok; payload=%#v", defaultExpanded.Status, defaultExpanded)
	}
	if defaultExpanded.Section != "related_paths" {
		t.Fatalf("Section = %q, want related_paths", defaultExpanded.Section)
	}
	relatedPaths, ok := defaultExpanded.Data.([]any)
	if !ok {
		t.Fatalf("Data = %T %#v, want []any from JSON related paths", defaultExpanded.Data, defaultExpanded.Data)
	}
	if len(relatedPaths) == 0 {
		t.Fatalf("related_paths data is empty")
	}
	if defaultExpanded.ActiveGenerationID != compass.ActiveGenerationID {
		t.Fatalf("ActiveGenerationID = %q, want %q", defaultExpanded.ActiveGenerationID, compass.ActiveGenerationID)
	}
	if defaultExpanded.QueryFingerprint != compass.QueryFingerprint {
		t.Fatalf("QueryFingerprint = %q, want %q", defaultExpanded.QueryFingerprint, compass.QueryFingerprint)
	}

	rawExpanded, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID, Section: " raw_candidates "})
	if err != nil {
		t.Fatal(err)
	}
	if rawExpanded.Status != "ok" || rawExpanded.Section != "raw_candidates" {
		t.Fatalf("raw expansion = %#v, want ok raw_candidates", rawExpanded)
	}
	rawCandidates, ok := rawExpanded.Data.([]any)
	if !ok || len(rawCandidates) == 0 {
		t.Fatalf("raw candidate data = %T %#v, want non-empty []any", rawExpanded.Data, rawExpanded.Data)
	}

	claimExpanded, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID, Section: "claim_evidence"})
	if err != nil {
		t.Fatal(err)
	}
	claimPackets, ok := claimExpanded.Data.([]any)
	if !ok || len(claimPackets) < 2 {
		t.Fatalf("claim evidence data = %T %#v, want claim packets for matched candidates", claimExpanded.Data, claimExpanded.Data)
	}
	firstClaim, ok := claimPackets[0].(map[string]any)
	if !ok {
		t.Fatalf("claim evidence item = %T %#v, want object", claimPackets[0], claimPackets[0])
	}
	if firstClaim["route_confidence"] == nil || firstClaim["confidence_scope"] != "route_candidate" || firstClaim["live_verification_required"] != true {
		t.Fatalf("claim evidence contract = %#v", firstClaim)
	}
	refs, ok := firstClaim["evidence_refs"].([]any)
	if !ok || len(refs) == 0 {
		t.Fatalf("claim evidence refs = %T %#v, want non-empty array", firstClaim["evidence_refs"], firstClaim["evidence_refs"])
	}
	firstRef, ok := refs[0].(map[string]any)
	if !ok || firstRef["source_path"] == nil || firstRef["span"] == nil {
		t.Fatalf("claim evidence ref = %T %#v, want source path and span", refs[0], refs[0])
	}
}

func TestCompassWritesDeterministicExpansionBundle(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	input := CompassInput{
		Intent: "debug",
		Query:  "切模型 failed runtimeOverride deepseek 方块 屏幕小",
	}

	first, err := Compass(paths, input)
	if err != nil {
		t.Fatal(err)
	}
	if first.ExpansionRef == nil {
		t.Fatal("first ExpansionRef is nil")
	}
	bundlePath, err := expansionBundlePath(paths, first.ExpansionRef.ID)
	if err != nil {
		t.Fatal(err)
	}
	firstBytes, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatal(err)
	}

	second, err := Compass(paths, input)
	if err != nil {
		t.Fatal(err)
	}
	if second.ExpansionRef == nil {
		t.Fatal("second ExpansionRef is nil")
	}
	secondBytes, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatal(err)
	}
	if string(firstBytes) != string(secondBytes) {
		t.Fatalf("bundle bytes changed for identical Compass input:\nfirst=%s\nsecond=%s", firstBytes, secondBytes)
	}

	var bundle ExpansionBundle
	if err := json.Unmarshal(firstBytes, &bundle); err != nil {
		t.Fatal(err)
	}
	if bundle.CreatedAt != deterministicExpansionCreatedAt(first.QueryFingerprint) {
		t.Fatalf("CreatedAt = %q, want deterministic value for %q", bundle.CreatedAt, first.QueryFingerprint)
	}
	if _, ok := bundle.Sections["related_paths"]; !ok {
		t.Fatalf("Sections = %#v, want map metadata with related_paths", bundle.Sections)
	}
	if bundle.Sections["related_paths"] != first.ExpansionRef.AvailableSections["related_paths"] {
		t.Fatalf("Sections related_paths = %#v, want ExpansionRef metadata %#v", bundle.Sections["related_paths"], first.ExpansionRef.AvailableSections["related_paths"])
	}
}

func TestCompassDoesNotWriteExpansionForNoCandidates(t *testing.T) {
	t.Run("empty graph", func(t *testing.T) {
		paths := queryTestPaths(t)
		seedGreenfieldEmptyRuntime(t, paths)

		compass, err := Compass(paths, CompassInput{
			Intent: "debug",
			Query:  "anything",
		})
		if err != nil {
			t.Fatal(err)
		}
		if compass.ExpansionRef != nil {
			t.Fatalf("ExpansionRef = %#v, want nil for ready graph with no candidate rows", compass.ExpansionRef)
		}
		assertNoExpansionBundles(t, paths)
	})

	t.Run("no computed candidates", func(t *testing.T) {
		paths := queryTestPaths(t)
		seedCompassModelSwitchGraph(t, paths)

		compass, err := Compass(paths, CompassInput{
			Intent: "debug",
			Query:  "unmatched raw phrase",
		})
		if err != nil {
			t.Fatal(err)
		}
		if compass.ExpansionRef != nil {
			t.Fatalf("ExpansionRef = %#v, want nil when candidate rows produce no scored candidates", compass.ExpansionRef)
		}
		assertNoExpansionBundles(t, paths)
	})
}

func TestExpandReturnsStaleExpansionForGenerationMismatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	compass, err := Compass(paths, CompassInput{Intent: "debug", Query: "runtimeOverride"})
	if err != nil {
		t.Fatal(err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.ActiveGenerationID = "GEN-newer"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID, Section: "related_paths"})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "stale_expansion" {
		t.Fatalf("Status = %q, want stale_expansion: %#v", payload.Status, payload)
	}
	if payload.Readiness != rt.ReviewReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.ReviewReadiness)
	}
	if payload.CompassState != "stale_expansion" {
		t.Fatalf("CompassState = %q, want stale_expansion", payload.CompassState)
	}
	if payload.RecommendedNextAction != "rerun_project_cognition_compass" {
		t.Fatalf("RecommendedNextAction = %q", payload.RecommendedNextAction)
	}
}

func TestExpansionStaleDetectsBundleIdentityMismatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	compass, err := Compass(paths, CompassInput{Intent: "debug", Query: "runtimeOverride"})
	if err != nil {
		t.Fatal(err)
	}
	bundlePath, err := expansionBundlePath(paths, compass.ExpansionRef.ID)
	if err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatal(err)
	}
	var bundle ExpansionBundle
	if err := json.Unmarshal(data, &bundle); err != nil {
		t.Fatal(err)
	}

	t.Run("id mismatch", func(t *testing.T) {
		edited := bundle
		edited.ID = "exp-other"
		writeExpansionBundleFileForTest(t, bundlePath, edited)

		payload, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID})
		if err != nil {
			t.Fatal(err)
		}
		if payload.Status != "stale_expansion" {
			t.Fatalf("Status = %q, want stale_expansion: %#v", payload.Status, payload)
		}
	})

	t.Run("fingerprint mismatch", func(t *testing.T) {
		edited := bundle
		edited.QueryFingerprint = "different"
		writeExpansionBundleFileForTest(t, bundlePath, edited)

		payload, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID})
		if err != nil {
			t.Fatal(err)
		}
		if payload.Status != "stale_expansion" {
			t.Fatalf("Status = %q, want stale_expansion: %#v", payload.Status, payload)
		}
	})
}

func TestExpandReturnsMissingExpansionRecovery(t *testing.T) {
	paths := queryTestPaths(t)

	for _, id := range []string{"exp-missing", "../escape"} {
		payload, err := Expand(paths, ExpandInput{ID: id})
		if err != nil {
			t.Fatalf("Expand(%q) error: %v", id, err)
		}
		if payload.Status != "missing_expansion" {
			t.Fatalf("Expand(%q).Status = %q, want missing_expansion", id, payload.Status)
		}
		if payload.RecommendedNextAction != "rerun_project_cognition_compass" {
			t.Fatalf("Expand(%q).RecommendedNextAction = %q", id, payload.RecommendedNextAction)
		}
	}
}

func TestExpansionBundlePathStaysInsideRuntimeDir(t *testing.T) {
	paths := queryTestPaths(t)

	path, err := expansionBundlePath(paths, "exp-safe.ID_123-abc")
	if err != nil {
		t.Fatal(err)
	}
	wantDir := filepath.Join(paths.RuntimeDir, "workbench", "expansions")
	if filepath.Dir(path) != wantDir {
		t.Fatalf("dir = %q, want %q", filepath.Dir(path), wantDir)
	}
	if !strings.HasPrefix(path, wantDir+string(os.PathSeparator)) {
		t.Fatalf("path = %q, want inside %q", path, wantDir)
	}
	if _, err := expansionBundlePath(paths, "exp-../escape"); err == nil {
		t.Fatalf("expansionBundlePath accepted path traversal ID")
	}
	if _, err := expansionBundlePath(paths, "missing-prefix"); err == nil {
		t.Fatalf("expansionBundlePath accepted invalid prefix")
	}
}

func TestExpandReturnsMissingSectionWithAvailableSections(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	compass, err := Compass(paths, CompassInput{Intent: "debug", Query: "runtimeOverride"})
	if err != nil {
		t.Fatal(err)
	}

	payload, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID, Section: "not_a_section"})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "missing_section" {
		t.Fatalf("Status = %q, want missing_section: %#v", payload.Status, payload)
	}
	if _, ok := payload.AvailableSections["related_paths"]; !ok {
		t.Fatalf("AvailableSections = %#v, want related_paths", payload.AvailableSections)
	}
}

func TestSectionMetadataReflectsPayloadSections(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	compass, err := Compass(paths, CompassInput{Intent: "debug", Query: "runtimeOverride"})
	if err != nil {
		t.Fatal(err)
	}
	bundlePath, err := expansionBundlePath(paths, compass.ExpansionRef.ID)
	if err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(bundlePath)
	if err != nil {
		t.Fatal(err)
	}
	var bundle ExpansionBundle
	if err := json.Unmarshal(data, &bundle); err != nil {
		t.Fatal(err)
	}
	bundle.Sections = map[string]ExpansionSectionMeta{
		"stale_advertised": {State: "available", EstimatedItems: 99},
	}
	writeExpansionBundleFileForTest(t, bundlePath, bundle)

	payload, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID, Section: "stale_advertised"})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "missing_section" {
		t.Fatalf("Status = %q, want missing_section: %#v", payload.Status, payload)
	}
	if _, ok := payload.AvailableSections["stale_advertised"]; ok {
		t.Fatalf("AvailableSections = %#v, want stale_advertised omitted", payload.AvailableSections)
	}
	if _, ok := payload.AvailableSections["related_paths"]; !ok {
		t.Fatalf("AvailableSections = %#v, want related_paths derived from payloads", payload.AvailableSections)
	}
}

func assertNoExpansionBundles(t *testing.T, paths rt.Paths) {
	t.Helper()
	expansionDir := filepath.Join(paths.RuntimeDir, "workbench", "expansions")
	matches, err := filepath.Glob(filepath.Join(expansionDir, "*.json"))
	if err != nil {
		t.Fatal(err)
	}
	if len(matches) != 0 {
		t.Fatalf("expansion bundles = %#v, want none", matches)
	}
}

func writeExpansionBundleFileForTest(t *testing.T, path string, bundle ExpansionBundle) {
	t.Helper()
	data, err := json.MarshalIndent(bundle, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

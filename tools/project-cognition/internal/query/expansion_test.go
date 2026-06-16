package query

import (
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
	for _, section := range []string{"related_paths", "raw_candidates", "coverage_gaps", "graph_neighbors"} {
		if _, ok := compass.ExpansionRef.AvailableSections[section]; !ok {
			t.Fatalf("ExpansionRef.AvailableSections missing %q: %#v", section, compass.ExpansionRef.AvailableSections)
		}
	}

	defaultExpanded, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID})
	if err != nil {
		t.Fatal(err)
	}
	if defaultExpanded.Status != "expanded" {
		t.Fatalf("Status = %q, want expanded; payload=%#v", defaultExpanded.Status, defaultExpanded)
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
	if rawExpanded.Status != "expanded" || rawExpanded.Section != "raw_candidates" {
		t.Fatalf("raw expansion = %#v, want expanded raw_candidates", rawExpanded)
	}
	rawCandidates, ok := rawExpanded.Data.([]any)
	if !ok || len(rawCandidates) == 0 {
		t.Fatalf("raw candidate data = %T %#v, want non-empty []any", rawExpanded.Data, rawExpanded.Data)
	}
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

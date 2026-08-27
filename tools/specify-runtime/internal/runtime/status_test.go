package runtime

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestReadStatusReturnsDefaultWhenMissing(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	status, err := ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.RuntimeFormat != RuntimeFormat {
		t.Fatalf("RuntimeFormat = %q", status.RuntimeFormat)
	}
	if status.Readiness != NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q", status.Readiness)
	}
}

func TestStatusProjectsDirtyDebtsIntoLegacyFields(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	status := DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = ReadyFreshness
	status.Readiness = ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.DirtyScopePaths = []string{"templates/legacy"}
	status.DirtyReasons = []string{"project structure changed"}
	status.StalePaths = []string{"docs/stale.md"}
	status.StaleReasons = []string{"affected closure cannot be bounded safely"}
	status.DirtyDebts = []DebtRecord{{ID: "debt-1", Kind: "mark_dirty", Paths: []string{"src/app.go"}, Reason: "deferred"}}
	if err := WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	got, err := ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if !got.Dirty || got.Freshness == ReadyFreshness || got.Readiness == ReadyReadiness ||
		strings.Join(got.DirtyScopePaths, ",") != "docs/stale.md,src/app.go,templates/legacy" ||
		strings.Join(got.StalePaths, ",") != "docs/stale.md,src/app.go,templates/legacy" ||
		strings.Join(got.DirtyReasons, ",") != "affected closure cannot be bounded safely,deferred,project structure changed" ||
		strings.Join(got.StaleReasons, ",") != "affected closure cannot be bounded safely,deferred,project structure changed" {
		t.Fatalf("status = %#v, want debt projected into truthful legacy fields", got)
	}
}

func TestReadStatusRejectsLegacyRuntime(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	legacy := map[string]any{"freshness": "fresh", "graph_ready": true}
	data, _ := json.Marshal(legacy)
	if err := os.WriteFile(filepath.Join(dir, "status.json"), data, 0o644); err != nil {
		t.Fatal(err)
	}
	paths, err := ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	_, err = ReadStatus(paths)
	if !errors.Is(err, ErrUnsupportedLegacy) {
		t.Fatalf("expected ErrUnsupportedLegacy, got %v", err)
	}
}

func TestReadStatusRejectsNonCurrentRuntimeSchema(t *testing.T) {
	for _, runtimeSchema := range []int{0, RuntimeSchema + 1} {
		t.Run(fmt.Sprintf("schema-%d", runtimeSchema), func(t *testing.T) {
			root := t.TempDir()
			if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
				t.Fatal(err)
			}
			paths, err := ResolvePaths(root)
			if err != nil {
				t.Fatal(err)
			}
			if err := os.MkdirAll(filepath.Dir(paths.StatusPath), 0o755); err != nil {
				t.Fatal(err)
			}
			status := DefaultStatus(paths)
			status.RuntimeSchema = runtimeSchema
			data, err := json.Marshal(status)
			if err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(paths.StatusPath, data, 0o644); err != nil {
				t.Fatal(err)
			}

			_, err = ReadStatus(paths)
			if !errors.Is(err, ErrUnsupportedLegacy) {
				t.Fatalf("ReadStatus(runtime_schema=%d) error = %v, want current-only runtime rejection", runtimeSchema, err)
			}
		})
	}
}

func TestReadStatusRejectsMissingCurrentGraphStorePath(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	status := DefaultStatus(paths)
	status.GraphStorePath = ""
	data, err := json.Marshal(status)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(paths.StatusPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	_, err = ReadStatus(paths)
	if !errors.Is(err, ErrUnsupportedLegacy) {
		t.Fatalf("ReadStatus(missing graph_store_path) error = %v, want current-only status rejection", err)
	}
}

func TestWriteStatusUsesGoRuntimeMarker(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	status := DefaultStatus(paths)
	status.ActiveGenerationID = "GEN-atomic"
	if err := WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(paths.StatusPath)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), `"runtime_format": "project-cognition-go"`) {
		t.Fatalf("status payload missing Go runtime marker: %s", data)
	}
}

func TestStatusRoundTripPreservesBaselineKind(t *testing.T) {
	paths := testPaths(t)
	status := DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = ReadyFreshness
	status.Readiness = ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-greenfield-test"
	status.BaselineKind = BaselineKindGreenfieldEmpty

	if err := WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	loaded, err := ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.BaselineKind != BaselineKindGreenfieldEmpty {
		t.Fatalf("BaselineKind = %q, want %q", loaded.BaselineKind, BaselineKindGreenfieldEmpty)
	}
}

func TestReadStatusRepairsLegacyGreenfieldWithProjectPathsToRebuild(t *testing.T) {
	paths := testPaths(t)
	status := DefaultStatus(paths)
	status.Status = "stale"
	status.Freshness = StaleFreshness
	status.Readiness = BlockedReadiness
	status.RecommendedNextAction = "run_map_update"
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-greenfield-legacy"
	status.BaselineKind = BaselineKindGreenfieldEmpty
	status.Dirty = true
	status.DirtyReasons = []string{"workflow-closeout-failed"}
	status.StalePaths = []string{"src/app.go"}
	status.StaleReasons = []string{"workflow-closeout-failed"}
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	data, err := json.Marshal(status)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(paths.StatusPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	loaded, err := ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.Readiness != NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q, want %q", loaded.Readiness, NeedsRebuildReadiness)
	}
	if loaded.RecommendedNextAction != "run_map_scan_build" {
		t.Fatalf("RecommendedNextAction = %q, want run_map_scan_build", loaded.RecommendedNextAction)
	}
	for label, reasons := range map[string][]string{
		"dirty": loaded.DirtyReasons,
		"stale": loaded.StaleReasons,
	} {
		found := false
		for _, reason := range reasons {
			if reason == "greenfield_baseline_has_project_code" {
				found = true
				break
			}
		}
		if !found {
			t.Fatalf("%s reasons = %#v, want greenfield baseline conflict token", label, reasons)
		}
	}
}

func TestWriteStatusDoesNotUseFixedTempPath(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	fixedTempPath := paths.StatusPath + ".tmp"
	if err := os.WriteFile(fixedTempPath, []byte("stale temp from another writer"), 0o644); err != nil {
		t.Fatal(err)
	}
	status := DefaultStatus(paths)
	status.ActiveGenerationID = "GEN-unique-temp"
	if err := WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(fixedTempPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != "stale temp from another writer" {
		t.Fatalf("fixed temp path was clobbered: %q", data)
	}
	matches, err := filepath.Glob(filepath.Join(paths.RuntimeDir, ".status-*.tmp"))
	if err != nil {
		t.Fatal(err)
	}
	if len(matches) != 0 {
		t.Fatalf("unexpected stale unique temp files: %v", matches)
	}
}

func testPaths(t *testing.T) Paths {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	return paths
}

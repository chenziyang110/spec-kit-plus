package runtime

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
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

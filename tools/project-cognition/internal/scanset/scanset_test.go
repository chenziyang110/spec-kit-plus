package scanset

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

func TestResolveWritesMinimalFileListAndRespectsRuntimeExclusions(t *testing.T) {
	root := t.TempDir()
	paths := testPaths(t, root)
	writeScanSetFile(t, root, ".cognitionignore", "vendor/\n")
	writeScanSetFile(t, root, "src/app.go", "package app\n")
	writeScanSetFile(t, root, "vendor/lib.go", "package vendor\n")
	writeScanSetFile(t, root, "node_modules/pkg/index.js", "module.exports = {}\n")
	writeScanSetFile(t, root, ".env", "TOKEN=secret\n")
	writeScanSetFile(t, root, "assets/logo.png", "\x00PNG")

	summary, err := Resolve(paths, Input{
		Scopes: []string{"src", "vendor", "node_modules", ".env", "assets"},
		Out:    DefaultOutputPath,
	})
	if err != nil {
		t.Fatalf("Resolve returned error: %v", err)
	}
	if summary.Files != DefaultOutputPath {
		t.Fatalf("summary files = %q", summary.Files)
	}
	if summary.Count != 1 {
		t.Fatalf("summary count = %d", summary.Count)
	}

	raw, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(DefaultOutputPath)))
	if err != nil {
		t.Fatal(err)
	}
	var list FileList
	if err := json.Unmarshal(raw, &list); err != nil {
		t.Fatal(err)
	}
	if want := []string{"src/app.go"}; !reflect.DeepEqual(list.Files, want) {
		t.Fatalf("files = %#v, want %#v", list.Files, want)
	}
}

func TestResolveHonorsReincludeRulesInsideIgnoredDirectories(t *testing.T) {
	root := t.TempDir()
	paths := testPaths(t, root)
	writeScanSetFile(t, root, ".cognitionignore", "generated/\n!generated/keep.go\n")
	writeScanSetFile(t, root, "generated/drop.go", "package generated\n")
	writeScanSetFile(t, root, "generated/keep.go", "package generated\n")

	summary, err := Resolve(paths, Input{Scopes: []string{"generated"}})
	if err != nil {
		t.Fatalf("Resolve returned error: %v", err)
	}
	if summary.Count != 1 {
		t.Fatalf("summary count = %d", summary.Count)
	}
	raw, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(DefaultOutputPath)))
	if err != nil {
		t.Fatal(err)
	}
	var list FileList
	if err := json.Unmarshal(raw, &list); err != nil {
		t.Fatal(err)
	}
	if want := []string{"generated/keep.go"}; !reflect.DeepEqual(list.Files, want) {
		t.Fatalf("files = %#v, want %#v", list.Files, want)
	}
}

func TestResolveRejectsOutputOutsideRepository(t *testing.T) {
	root := t.TempDir()
	paths := testPaths(t, root)

	if _, err := Resolve(paths, Input{Out: "../scan-files.json"}); err == nil {
		t.Fatal("expected output outside repository to be rejected")
	}
}

func testPaths(t *testing.T, root string) rt.Paths {
	t.Helper()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	return rt.Paths{
		Root:         root,
		RuntimeDir:   runtimeDir,
		StatusPath:   filepath.Join(runtimeDir, rt.StatusFileName),
		DatabasePath: filepath.Join(runtimeDir, rt.DBFileName),
	}
}

func writeScanSetFile(t *testing.T, root string, rel string, content string) {
	t.Helper()
	path := filepath.Join(root, filepath.FromSlash(rel))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

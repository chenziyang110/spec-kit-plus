package ignore

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadMergesRootAndLocalProjectCognitionIgnores(t *testing.T) {
	root := t.TempDir()
	localDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(localDir, 0o755); err != nil {
		t.Fatalf("create local ignore dir: %v", err)
	}
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatalf("write root .cognitionignore: %v", err)
	}
	if err := os.WriteFile(filepath.Join(localDir, ".cognitionignore"), []byte("generated/\n"), 0o644); err != nil {
		t.Fatalf("write local .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("vendor/a.go") {
		t.Fatal("expected root ignore pattern to ignore vendor/a.go")
	}
	if !matcher.Ignored("generated/a.go") {
		t.Fatal("expected local project cognition ignore pattern to ignore generated/a.go")
	}
	if matcher.Ignored("src/a.go") {
		t.Fatal("did not expect src/a.go to be ignored")
	}
}

func TestRootReincludeRulesAreAppliedInOrder(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("generated/\n!generated/keep.go\n"), 0o644); err != nil {
		t.Fatalf("write root .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("generated/drop.go") {
		t.Fatal("expected generated/drop.go to be ignored")
	}
	if matcher.Ignored("generated/keep.go") {
		t.Fatal("did not expect generated/keep.go to be ignored")
	}
}

func TestLocalProjectCognitionReincludeRulesAreAppliedInOrder(t *testing.T) {
	root := t.TempDir()
	localDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(localDir, 0o755); err != nil {
		t.Fatalf("create local ignore dir: %v", err)
	}
	if err := os.WriteFile(filepath.Join(localDir, ".cognitionignore"), []byte("generated/\n!generated/keep.go\n"), 0o644); err != nil {
		t.Fatalf("write local .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("generated/drop.go") {
		t.Fatal("expected generated/drop.go to be ignored")
	}
	if matcher.Ignored("generated/keep.go") {
		t.Fatal("did not expect generated/keep.go to be ignored")
	}
}

func TestUnanchoredDirectoryPatternMatchesNestedDirectory(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("node_modules/\n"), 0o644); err != nil {
		t.Fatalf("write root .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("packages/a/node_modules/pkg/index.js") {
		t.Fatal("expected nested node_modules path to be ignored")
	}
	if matcher.Ignored("packages/a/src/index.js") {
		t.Fatal("did not expect non-node_modules path to be ignored")
	}
}

func TestDoubleStarPatternMatchesNestedDistOutputs(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("**/dist/**\n"), 0o644); err != nil {
		t.Fatalf("write root .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("packages/a/dist/index.js") {
		t.Fatal("expected nested dist output to be ignored")
	}
	if matcher.Ignored("packages/a/src/index.js") {
		t.Fatal("did not expect non-dist path to be ignored")
	}
}

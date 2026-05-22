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

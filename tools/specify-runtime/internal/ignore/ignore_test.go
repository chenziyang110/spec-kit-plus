package ignore

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLoadAppliesBuiltInDefaultIgnores(t *testing.T) {
	root := t.TempDir()

	matcher := Load(root)

	if !matcher.Ignored(".git/config") {
		t.Fatal("expected built-in default rules to ignore .git/config")
	}
	if !matcher.Ignored(".specify/project-cognition/status.json") {
		t.Fatal("expected built-in default rules to ignore project cognition runtime state")
	}
	if !matcher.Ignored(".specify/archive/old-feature/spec.md") {
		t.Fatal("expected built-in default rules to ignore archived specifications")
	}
	if !matcher.Ignored("node_modules/pkg/index.js") {
		t.Fatal("expected built-in default rules to ignore node_modules")
	}
	if matcher.Ignored("src/app.go") {
		t.Fatal("did not expect src/app.go to be ignored by default")
	}
}

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

func TestAnchoredDirectoryPatternMatchesOnlyRootDirectory(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("/generated/\n"), 0o644); err != nil {
		t.Fatalf("write root .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("generated/a.go") {
		t.Fatal("expected root generated path to be ignored")
	}
	if matcher.Ignored("src/generated/a.go") {
		t.Fatal("did not expect nested generated path to be ignored")
	}
}

func TestAnchoredDirectoryPatternMatchesRootPathPrefix(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("/src/generated/\n"), 0o644); err != nil {
		t.Fatalf("write root .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("src/generated/a.go") {
		t.Fatal("expected root src/generated path to be ignored")
	}
	if matcher.Ignored("pkg/src/generated/a.go") {
		t.Fatal("did not expect nested src/generated path to be ignored")
	}
}

func TestAnchoredPatternWithoutSlashMatchesDirectoryDescendants(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("/src/generated\n"), 0o644); err != nil {
		t.Fatalf("write root .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("src/generated/a.go") {
		t.Fatal("expected root src/generated descendant to be ignored")
	}
	if matcher.Ignored("pkg/src/generated/a.go") {
		t.Fatal("did not expect nested src/generated descendant to be ignored")
	}
}

func TestAnchoredSlashlessPatternMatchesOnlyRootComponentDescendants(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("/generated\n"), 0o644); err != nil {
		t.Fatalf("write root .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("generated/a.go") {
		t.Fatal("expected root generated descendant to be ignored")
	}
	if matcher.Ignored("src/generated/a.go") {
		t.Fatal("did not expect nested generated descendant to be ignored")
	}
}

func TestUnanchoredSlashPatternWithoutSlashMatchesDirectoryDescendants(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("src/generated\n"), 0o644); err != nil {
		t.Fatalf("write root .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("src/generated/a.go") {
		t.Fatal("expected direct src/generated descendant to be ignored")
	}
	if !matcher.Ignored("pkg/src/generated/a.go") {
		t.Fatal("expected nested src/generated descendant to be ignored")
	}
	if matcher.Ignored("pkg/src/other/a.go") {
		t.Fatal("did not expect unrelated path to be ignored")
	}
}

func TestDoubleStarSlashMatchesZeroOrMoreDirectories(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("examples/**/*.generated.ts\n"), 0o644); err != nil {
		t.Fatalf("write root .cognitionignore: %v", err)
	}

	matcher := Load(root)

	if !matcher.Ignored("examples/app.generated.ts") {
		t.Fatal("expected direct generated example to be ignored")
	}
	if !matcher.Ignored("examples/demo/app.generated.ts") {
		t.Fatal("expected nested generated example to be ignored")
	}
	if matcher.Ignored("examples/app.ts") {
		t.Fatal("did not expect non-generated example to be ignored")
	}
}

func TestGenerateStarterIgnoreFileCommentsGitignoreSuggestions(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".gitignore"), []byte(`
node_modules/
.specify/
secrets.local
generated/reports/
`), 0o644); err != nil {
		t.Fatalf("write .gitignore: %v", err)
	}
	if err := os.MkdirAll(filepath.Join(root, "fixtures"), 0o755); err != nil {
		t.Fatalf("create fixtures: %v", err)
	}

	content := GenerateStarterIgnoreFile(root)

	for _, want := range []string{
		"Project Cognition ignore rules",
		"gitignore-compatible",
		"# secrets.local",
		"# generated/reports/",
		"# fixtures/",
	} {
		if !strings.Contains(content, want) {
			t.Fatalf("starter ignore missing %q:\n%s", want, content)
		}
	}
	for _, excluded := range []string{"\n# node_modules/\n", "\n# .specify/\n"} {
		if strings.Contains(content, excluded) {
			t.Fatalf("starter ignore should not repeat built-in default %q:\n%s", excluded, content)
		}
	}
}

func TestWriteStarterIgnoreFileDoesNotOverwriteExistingFile(t *testing.T) {
	root := t.TempDir()
	localDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(localDir, 0o755); err != nil {
		t.Fatalf("create local ignore dir: %v", err)
	}
	path := filepath.Join(localDir, ".cognitionignore")
	if err := os.WriteFile(path, []byte("custom/\n"), 0o644); err != nil {
		t.Fatalf("write existing .cognitionignore: %v", err)
	}

	gotPath, created, err := WriteStarterIgnoreFile(root)
	if err != nil {
		t.Fatalf("WriteStarterIgnoreFile returned error: %v", err)
	}
	if created {
		t.Fatal("WriteStarterIgnoreFile reported created=true for an existing file")
	}
	if gotPath != path {
		t.Fatalf("path = %q, want %q", gotPath, path)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read existing .cognitionignore: %v", err)
	}
	if string(data) != "custom/\n" {
		t.Fatalf("existing .cognitionignore was overwritten: %q", string(data))
	}
}

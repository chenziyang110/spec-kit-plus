package query

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParsePlanNormalizesLegacyAliases(t *testing.T) {
	plan, err := ParsePlan(`{"path_hints":["./src/a.go"],"reason":"because"}`, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Paths) != 1 || plan.Paths[0] != "src/a.go" {
		t.Fatalf("paths = %#v", plan.Paths)
	}
	if plan.SelectionReason != "because" {
		t.Fatalf("selection reason = %q", plan.SelectionReason)
	}
}

func TestParsePlanSupportsAtFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "plan.json")
	if err := os.WriteFile(path, []byte(`{"paths":["docs/x.md"]}`), 0o644); err != nil {
		t.Fatal(err)
	}
	plan, err := ParsePlan("@"+path, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Paths) != 1 || plan.Paths[0] != "docs/x.md" {
		t.Fatalf("paths = %#v", plan.Paths)
	}
}

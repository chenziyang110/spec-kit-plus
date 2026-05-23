package query

import (
	"context"
	"database/sql"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
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

func TestRunBlocksSplitBrainBaseline(t *testing.T) {
	paths := queryTestPaths(t)
	seedSplitBrainRuntime(t, paths)

	_, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}
}

func TestLexiconBlocksSplitBrainBaseline(t *testing.T) {
	paths := queryTestPaths(t)
	seedSplitBrainRuntime(t, paths)

	_, err := Lexicon(paths, "plan", "app", 10)

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}
}

func TestRunBlocksStatusOnlyBaselineWithoutCreatingDatabase(t *testing.T) {
	paths := queryTestPaths(t)
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-status"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	_, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err == nil {
		t.Fatal("expected status-only agreement error")
	}
	if !strings.Contains(err.Error(), "project-cognition.db is missing") {
		t.Fatalf("error = %q, want missing DB", err.Error())
	}
	if _, statErr := os.Stat(paths.DatabasePath); !os.IsNotExist(statErr) {
		t.Fatalf("database stat err = %v, want missing DB", statErr)
	}
}

func TestRunBlocksIncompatibleDatabaseWithoutArchiving(t *testing.T) {
	paths := queryTestPaths(t)
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	for _, statement := range []string{
		`CREATE TABLE metadata(key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL)`,
		`CREATE TABLE generations(id TEXT PRIMARY KEY, state TEXT NOT NULL)`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('active_generation_id', '"GEN-db"', 'now')`,
		`INSERT INTO generations(id, state) VALUES('GEN-db', 'active')`,
	} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			t.Fatal(err)
		}
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-db"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	_, err = Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err == nil {
		t.Fatal("expected incompatible DB agreement error")
	}
	if !strings.Contains(err.Error(), "schema is incompatible") {
		t.Fatalf("error = %q, want incompatible schema", err.Error())
	}
	if _, statErr := os.Stat(paths.DatabasePath + ".legacy"); !os.IsNotExist(statErr) {
		t.Fatalf("legacy archive stat err = %v, want no archive", statErr)
	}
}

func TestRunMissingBaselineReturnsNeedsRebuildWithoutCreatingDatabase(t *testing.T) {
	paths := queryTestPaths(t)

	payload, err := Run(paths, QueryInput{Query: "app", Plan: Plan{Paths: []string{"src/app.go"}}})

	if err != nil {
		t.Fatalf("Run() error = %v", err)
	}
	if payload.Readiness != rt.NeedsRebuildReadiness {
		t.Fatalf("Readiness = %q, want needs_rebuild", payload.Readiness)
	}
	if payload.RecommendedNextAction != "run_map_scan_build" {
		t.Fatalf("RecommendedNextAction = %q, want run_map_scan_build", payload.RecommendedNextAction)
	}
	if _, statErr := os.Stat(paths.DatabasePath); !os.IsNotExist(statErr) {
		t.Fatalf("database stat err = %v, want missing DB", statErr)
	}
}

func queryTestPaths(t *testing.T) rt.Paths {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	return paths
}

func seedSplitBrainRuntime(t *testing.T, paths rt.Paths) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-db",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence:     []store.EvidenceImport{{ID: "E-app", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-app"}},
		Nodes:        []store.NodeImport{{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-app"}}},
		PathIndex:    []store.PathIndexImport{{ID: "P-app", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-app"}},
	})
	if closeErr := st.Close(); closeErr != nil {
		t.Fatal(closeErr)
	}
	if err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

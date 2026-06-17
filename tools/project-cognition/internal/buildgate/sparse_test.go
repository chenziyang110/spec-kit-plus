package buildgate

import (
	"context"
	"database/sql"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	_ "modernc.org/sqlite"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestValidateSparsePathIndexExcludesAcceptedGapsFromDenominator(t *testing.T) {
	paths := buildgateTestPaths(t)
	writeBuildgateRequirements(t, paths, []string{"src/a.go", "src/b.go", "src/gap.go"}, []string{"src/gap.go"}, map[string]string{
		"src/a.go":   "low_risk",
		"src/b.go":   "low_risk",
		"src/gap.go": "low_risk",
	})
	db := buildgateTestDB(t, paths)
	seedBuildgatePathIndex(t, db, "GEN-0001", []string{"src/a.go"})

	result := ValidateSparsePathIndex(paths, db, "GEN-0001")

	if !containsBuildgateText(result.Errors, "path_index_to_included_ratio 0.50 is below hard threshold 0.70") {
		t.Fatalf("Errors = %#v, want hard-failing ratio", result.Errors)
	}
	if len(result.Warnings) != 0 {
		t.Fatalf("Warnings = %#v, want none for hard-failing ratio", result.Warnings)
	}
	if result.Details["index_required_count"] != 2 {
		t.Fatalf("index_required_count = %#v, want 2", result.Details["index_required_count"])
	}
}

func TestValidateSparsePathIndexReportsCriticalMissingPath(t *testing.T) {
	paths := buildgateTestPaths(t)
	writeBuildgateRequirements(t, paths, []string{"src/critical.go", "src/indexed.go"}, nil, map[string]string{
		"src/critical.go": "critical",
		"src/indexed.go":  "low_risk",
	})
	db := buildgateTestDB(t, paths)
	seedBuildgatePathIndex(t, db, "GEN-0001", []string{"src/indexed.go"})

	result := ValidateSparsePathIndex(paths, db, "GEN-0001")

	if !containsBuildgateText(result.Errors, "critical_missing_path_index: src/critical.go") {
		t.Fatalf("Errors = %#v, want critical missing path", result.Errors)
	}
}

func TestValidateSparsePathIndexUsesGraphEligibleScanTargetsDenominator(t *testing.T) {
	paths := buildgateTestPaths(t)
	writeBuildgateRequirements(t, paths, []string{
		"src/app.go",
		"src/config.go",
		"tests/app_test.go",
		"vendor/bundle.js",
	}, nil, map[string]string{
		"src/app.go":        "critical",
		"src/config.go":     "important",
		"tests/app_test.go": "low_risk",
		"vendor/bundle.js":  "low_risk",
	})
	writeBuildgateJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-targets.json"), map[string]any{
		"schema_version":         1,
		"selection_policy":       "value_weighted",
		"selected_paths":         []string{"src/app.go", "src/config.go"},
		"sampled_paths":          []string{"tests/app_test.go"},
		"inventory_only_paths":   []string{"vendor/bundle.js"},
		"excluded_paths":         []string{},
		"blocked_paths":          []string{},
		"value_tier":             map[string]string{"src/app.go": "P0", "src/config.go": "P1", "tests/app_test.go": "P2", "vendor/bundle.js": "P3"},
		"scan_decision":          map[string]string{"src/app.go": "scan", "src/config.go": "scan", "tests/app_test.go": "sample", "vendor/bundle.js": "inventory_only"},
		"disposition":            map[string]string{"src/app.go": "deep_read", "src/config.go": "deep_read", "tests/app_test.go": "sampled", "vendor/bundle.js": "inventory_only"},
		"criticality":            map[string]string{"src/app.go": "critical", "src/config.go": "important", "tests/app_test.go": "low_risk", "vendor/bundle.js": "low_risk"},
		"classification_reasons": map[string]string{"src/app.go": "entrypoint", "src/config.go": "config", "tests/app_test.go": "sampled proof", "vendor/bundle.js": "inventory"},
	})
	db := buildgateTestDB(t, paths)
	seedBuildgatePathIndex(t, db, "GEN-0001", []string{"src/app.go", "src/config.go"})

	result := ValidateSparsePathIndex(paths, db, "GEN-0001")

	if len(result.Errors) != 0 {
		t.Fatalf("Errors = %#v, want graph-eligible scan targets to pass", result.Errors)
	}
	if result.Details["index_required_count"] != 2 {
		t.Fatalf("index_required_count = %#v, want only selected P0/P1 paths", result.Details["index_required_count"])
	}
	if result.Details["path_index_to_included_ratio"] != "1.00" {
		t.Fatalf("path_index_to_included_ratio = %#v, want 1.00", result.Details["path_index_to_included_ratio"])
	}
}

func buildgateTestPaths(t *testing.T) rt.Paths {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	return paths
}

func buildgateTestDB(t *testing.T, paths rt.Paths) *sql.DB {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := st.Close(); err != nil {
			t.Fatal(err)
		}
	})
	return st.DB()
}

func seedBuildgatePathIndex(t *testing.T, db *sql.DB, generationID string, paths []string) {
	t.Helper()
	if _, err := db.ExecContext(context.Background(), `INSERT INTO generations(id, sequence, kind, state, source_commit, started_at, published_at, superseded_at, attrs_json) VALUES(?, 1, 'full', 'active', 'abc123', '', '', '', '{}')`, generationID); err != nil {
		t.Fatal(err)
	}
	for i, path := range paths {
		if _, err := db.ExecContext(context.Background(), `INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES(?, ?, ?, ?, 'owns', 'verified', '', '')`, "P-"+path, generationID, path, "N-"+string(rune('a'+i))); err != nil {
			t.Fatal(err)
		}
	}
}

func writeBuildgateRequirements(t *testing.T, paths rt.Paths, included []string, acceptedGaps []string, criticality map[string]string) {
	t.Helper()
	candidates := []map[string]any{}
	dispositions := map[string]string{}
	reasons := map[string]string{}
	sources := map[string]string{}
	for _, path := range included {
		candidates = append(candidates, map[string]any{"path": path, "disposition": "deep_read", "decision_source": "git"})
		dispositions[path] = "deep_read"
		reasons[path] = "test"
		sources[path] = "git"
	}
	openGaps := []map[string]any{}
	for _, path := range acceptedGaps {
		openGaps = append(openGaps, map[string]any{
			"path":                 path,
			"status":               "low_risk_open_gap",
			"owner":                "scan",
			"reason":               "accepted gap",
			"evidence_expectation": "not required",
			"revisit_condition":    "path changes",
		})
	}
	writeBuildgateJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), map[string]any{
		"schema_version":         1,
		"candidate_universe":     candidates,
		"included_paths":         included,
		"excluded_paths":         []string{},
		"ambiguous_paths":        []string{},
		"dispositions":           dispositions,
		"criticality":            criticality,
		"classification_reasons": reasons,
		"decision_source":        sources,
	})
	writeBuildgateJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), map[string]any{
		"rows":      []map[string]any{},
		"open_gaps": openGaps,
	})
	writeBuildgateJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{"nodes": []map[string]any{}})
}

func writeBuildgateJSON(t *testing.T, path string, payload any) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func containsBuildgateText(values []string, want string) bool {
	for _, value := range values {
		if strings.Contains(value, want) {
			return true
		}
	}
	return false
}

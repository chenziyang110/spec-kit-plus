package validation

import (
	"context"
	"database/sql"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	_ "modernc.org/sqlite"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func validationTestPaths(t *testing.T) rt.Paths {
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

func writeBuildAcceptanceInputs(t *testing.T, paths rt.Paths) {
	t.Helper()
	workbench := filepath.Join(paths.RuntimeDir, "workbench")
	if err := os.MkdirAll(filepath.Join(workbench, "worker-results"), 0o755); err != nil {
		t.Fatal(err)
	}
	files := map[string]string{
		filepath.Join(workbench, "capability-ledger.json"): `{"rows":[]}`,
		filepath.Join(workbench, "control-ledger.json"):    `{"rows":[]}`,
		filepath.Join(workbench, "coverage-ledger.json"):   `{"rows":[],"open_gaps":[]}`,
	}
	for path, content := range files {
		if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func TestValidateBuildBlocksMetadataOnlyDatabase(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if payload.Readiness != "blocked" {
		t.Fatalf("Readiness = %q, want blocked", payload.Readiness)
	}
	if !hasValidationError(payload.Errors, "active generation") {
		t.Fatalf("Errors = %#v, want active-generation query-readiness error", payload.Errors)
	}
}

func TestValidateBuildBlocksActiveGenerationWithoutPathIndex(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	seedQueryReadyDatabase(t, paths)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `DELETE FROM path_index`); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationError(payload.Errors, "path_index") {
		t.Fatalf("Errors = %#v, want path_index query-readiness error", payload.Errors)
	}
}

func TestValidateBuildBlocksLegacyThinSchema(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	statements := []string{
		`CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)`,
		`CREATE TABLE generations(id TEXT PRIMARY KEY, state TEXT NOT NULL)`,
		`CREATE TABLE evidence(id TEXT PRIMARY KEY, generation_id TEXT, source_path TEXT)`,
		`CREATE TABLE observations(id TEXT PRIMARY KEY)`,
		`CREATE TABLE observation_evidence(observation_id TEXT, evidence_id TEXT)`,
		`CREATE TABLE nodes(id TEXT PRIMARY KEY, type TEXT NOT NULL, title TEXT NOT NULL, path TEXT)`,
		`CREATE TABLE node_evidence(node_id TEXT, evidence_id TEXT)`,
		`CREATE TABLE edges(id TEXT PRIMARY KEY, source TEXT NOT NULL, target TEXT NOT NULL, type TEXT NOT NULL)`,
		`CREATE TABLE edge_evidence(edge_id TEXT, evidence_id TEXT)`,
		`CREATE TABLE claims(id TEXT PRIMARY KEY, node_id TEXT, text TEXT)`,
		`CREATE TABLE claim_evidence(claim_id TEXT, evidence_id TEXT)`,
		`CREATE TABLE conflicts(id TEXT PRIMARY KEY)`,
		`CREATE TABLE conflict_claims(conflict_id TEXT, claim_id TEXT)`,
		`CREATE TABLE path_index(id TEXT PRIMARY KEY, generation_id TEXT, path TEXT, node_id TEXT)`,
		`CREATE TABLE symbol_index(id TEXT PRIMARY KEY, generation_id TEXT, path TEXT)`,
		`CREATE TABLE alias_index(id TEXT PRIMARY KEY, generation_id TEXT, alias TEXT, target_id TEXT)`,
		`CREATE TABLE entrypoint_index(id TEXT PRIMARY KEY, generation_id TEXT, path TEXT)`,
		`CREATE TABLE test_index(id TEXT PRIMARY KEY, generation_id TEXT, test_path TEXT)`,
		`CREATE TABLE slice_members(id TEXT PRIMARY KEY)`,
		`CREATE TABLE query_examples(id TEXT PRIMARY KEY)`,
		`CREATE TABLE updates(id TEXT PRIMARY KEY, reason TEXT, changed_paths TEXT)`,
		`INSERT INTO metadata(key, value) VALUES('schema_version', '1')`,
		`INSERT INTO generations(id, state) VALUES('GEN-legacy', 'active')`,
		`INSERT INTO evidence(id, generation_id, source_path) VALUES('E-legacy', 'GEN-legacy', 'src/app.go')`,
		`INSERT INTO nodes(id, type, title, path) VALUES('N-legacy', 'capability', 'App', 'src/app.go')`,
		`INSERT INTO path_index(id, generation_id, path, node_id) VALUES('P-legacy', 'GEN-legacy', 'src/app.go', 'N-legacy')`,
	}
	for _, statement := range statements {
		if _, err := db.ExecContext(context.Background(), statement); err != nil {
			t.Fatal(err)
		}
	}

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationError(payload.Errors, "missing required query columns") {
		t.Fatalf("Errors = %#v, want missing query schema columns error", payload.Errors)
	}
}

func TestValidateBuildAcceptsQueryReadyDatabase(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	seedQueryReadyDatabase(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.ActiveGenerationID = "GEN-0001"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload := ValidateBuild(paths)

	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", payload.Status, payload.Errors)
	}
	if payload.Readiness != "query_ready" {
		t.Fatalf("Readiness = %q, want query_ready", payload.Readiness)
	}
	if payload.Details["query_smoke_test"] != "ok" {
		t.Fatalf("Details = %#v, want query smoke test", payload.Details)
	}
}

func seedQueryReadyDatabase(t *testing.T, paths rt.Paths) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	now := time.Now().UTC().Format(time.RFC3339)
	db := st.DB()
	statements := []string{
		`INSERT INTO generations(id, sequence, kind, state, source_commit, started_at, published_at, superseded_at, attrs_json) VALUES('GEN-0001', 1, 'full', 'active', 'abc123', ?, ?, '', '{}')`,
		`INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES('E-001', 'GEN-0001', 'source', 'src/app.go', 'abc123', '', 'test', 'hash', ?, '{}')`,
		`INSERT INTO nodes(id, generation_id, type, title, confidence, attrs_json, created_at, updated_at) VALUES('capability:app', 'GEN-0001', 'capability', 'App', 'verified', '{}', ?, ?)`,
		`INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES('P-001', 'GEN-0001', 'src/app.go', 'capability:app', 'owns', 'verified', 'E-001', ?)`,
	}
	args := [][]any{
		{now, now},
		{now},
		{now, now},
		{now},
	}
	for i, statement := range statements {
		if _, err := db.ExecContext(context.Background(), statement, args[i]...); err != nil {
			t.Fatal(err)
		}
	}
}

func hasValidationError(errors []string, want string) bool {
	for _, err := range errors {
		if strings.Contains(err, want) {
			return true
		}
	}
	return false
}

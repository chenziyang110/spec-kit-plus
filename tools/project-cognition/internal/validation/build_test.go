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
	writeMatchingScanPackage(t, paths)
	seedMatchingQueryReadyDatabase(t, paths, nil, nil)
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

func TestValidateBuildBlocksMissingScanNodeIdentity(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	writeMatchingScanPackage(t, paths)
	seedMatchingQueryReadyDatabase(t, paths, nil, nil)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `DELETE FROM nodes WHERE id = 'N-app'`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	writeReadyStatus(t, paths, "GEN-0001")

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationError(payload.Errors, "missing scan node identities") {
		t.Fatalf("Errors = %#v, want missing scan node identities", payload.Errors)
	}
}

func TestValidateBuildBlocksUnexpectedDBNodeIdentityWithSameCount(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	writeMatchingScanPackage(t, paths)
	seedQueryReadyDatabaseWithNodeID(t, paths, "N-substituted")
	writeReadyStatus(t, paths, "GEN-0001")

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationError(payload.Errors, "unexpected DB node identities") {
		t.Fatalf("Errors = %#v, want unexpected DB node identities", payload.Errors)
	}
}

func TestValidateBuildAllowsMissingScanIdentityCoveredByDecision(t *testing.T) {
	tests := []struct {
		name         string
		rejections   []store.RowDecision
		mergeRecords []store.MergeRecord
	}{
		{
			name:       "rejection",
			rejections: []store.RowDecision{{Category: "node", Identity: "N-app", Reason: "explicitly_rejected"}},
		},
		{
			name:         "merge",
			mergeRecords: []store.MergeRecord{{Category: "node", SourceIdentity: "N-app", TargetIdentity: "N-canonical", Reason: "duplicate"}},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			paths := validationTestPaths(t)
			writeBuildAcceptanceInputs(t, paths)
			writeMatchingScanPackage(t, paths)
			seedQueryReadyDatabaseWithNodeIDAndDecisions(t, paths, "N-canonical", tt.rejections, tt.mergeRecords)
			writeReadyStatus(t, paths, "GEN-0001")

			payload := ValidateBuild(paths)

			if payload.Status != "blocked" {
				t.Fatalf("Status = %q, want blocked only for unexpected canonical node; errors=%#v", payload.Status, payload.Errors)
			}
			if hasValidationError(payload.Errors, "missing scan node identities") {
				t.Fatalf("Errors = %#v, missing scan node identity should be covered by decision", payload.Errors)
			}
			if !hasValidationError(payload.Errors, "unexpected DB node identities") {
				t.Fatalf("Errors = %#v, want unexpected canonical DB node", payload.Errors)
			}
		})
	}
}

func TestValidateBuildAllowsMissingCoveragePathCoveredByDecision(t *testing.T) {
	tests := []struct {
		name         string
		rejections   []store.RowDecision
		mergeRecords []store.MergeRecord
	}{
		{
			name:       "coverage rejection",
			rejections: []store.RowDecision{{Category: "coverage", Identity: "src/app.go", Reason: "covered_elsewhere"}},
		},
		{
			name:         "coverage merge",
			mergeRecords: []store.MergeRecord{{Category: "coverage_paths", SourceIdentity: "src/app.go", TargetIdentity: "docs/app.md", Reason: "canonical_path"}},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			paths := validationTestPaths(t)
			writeBuildAcceptanceInputs(t, paths)
			writeMatchingScanPackage(t, paths)
			seedMatchingQueryReadyDatabase(t, paths, tt.rejections, tt.mergeRecords)
			st, err := store.OpenExisting(paths)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := st.DB().ExecContext(context.Background(), `UPDATE path_index SET path = 'docs/app.md' WHERE path = 'src/app.go'`); err != nil {
				_ = st.Close()
				t.Fatal(err)
			}
			if err := st.Close(); err != nil {
				t.Fatal(err)
			}
			writeReadyStatus(t, paths, "GEN-0001")

			payload := ValidateBuild(paths)

			if hasValidationError(payload.Errors, "missing scan coverage path identities") {
				t.Fatalf("Errors = %#v, missing scan coverage path identity should be covered by decision", payload.Errors)
			}
			if !hasValidationError(payload.Errors, "unexpected DB coverage path identities") {
				t.Fatalf("Errors = %#v, want unexpected canonical DB coverage path", payload.Errors)
			}
		})
	}
}

func TestValidateBuildReportsCategorySpecificMissingIdentities(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	writeMatchingScanPackage(t, paths)
	seedMatchingQueryReadyDatabase(t, paths, nil, nil)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	deletes := []string{
		`DELETE FROM evidence WHERE id = 'E-001'`,
		`DELETE FROM edges WHERE id = 'EDGE-app-self'`,
		`DELETE FROM observations WHERE id = 'OBS-app'`,
		`DELETE FROM path_index WHERE path = 'src/app.go'`,
	}
	for _, statement := range deletes {
		if _, err := st.DB().ExecContext(context.Background(), statement); err != nil {
			_ = st.Close()
			t.Fatal(err)
		}
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	writeReadyStatus(t, paths, "GEN-0001")

	payload := ValidateBuild(paths)

	for _, want := range []string{
		"missing scan evidence identities",
		"missing scan edge identities",
		"missing scan observation identities",
		"missing scan coverage path identities",
	} {
		if !hasValidationError(payload.Errors, want) {
			t.Fatalf("Errors = %#v, want %q", payload.Errors, want)
		}
	}
}

func TestValidateBuildBlocksGenerationMismatchWithRecoveryAction(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	writeMatchingScanPackage(t, paths)
	seedMatchingQueryReadyDatabase(t, paths, nil, nil)
	writeReadyStatus(t, paths, "GEN-stale")

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if payload.Details["recovery_action"] != "rewrite_status_from_db_metadata" {
		t.Fatalf("recovery_action = %#v, want rewrite_status_from_db_metadata; details=%#v", payload.Details["recovery_action"], payload.Details)
	}
	if hasValidationError(payload.Errors, "status.json active_generation_id") {
		t.Fatalf("Errors = %#v, graph validation should not duplicate runtimegate generation mismatch", payload.Errors)
	}
}

func TestValidateBuildSurfacesPartialScanPackageDiagnostics(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	seedMatchingQueryReadyDatabase(t, paths, nil, nil)
	writeReadyStatus(t, paths, "GEN-0001")
	if err := os.MkdirAll(filepath.Join(paths.RuntimeDir, "evidence"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"), []byte(`{"id":"E-001","source_path":"src/app.go","content_hash":"hash-app"}`+"\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	payload := ValidateBuild(paths)

	if payload.Details["identity_reconciliation"] != "skipped_invalid_scan_package" {
		t.Fatalf("identity_reconciliation = %#v, want skipped_invalid_scan_package; details=%#v", payload.Details["identity_reconciliation"], payload.Details)
	}
	if !hasValidationError(payload.Errors, "missing .specify/project-cognition/provisional/nodes.json") {
		t.Fatalf("Errors = %#v, want missing scan package member diagnostic", payload.Errors)
	}
}

func TestValidateBuildIgnoresBlockedScanOwnedCoverageGap(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	writeCoverageLedger(t, paths, `{"rows":[],"open_gaps":[{"owner":"scan","status":"blocked"}]}`)
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
}

func TestValidateBuildBlocksBuildOwnedOrOwnerlessCoverageGap(t *testing.T) {
	tests := []struct {
		name   string
		ledger string
	}{
		{
			name:   "build owned",
			ledger: `{"rows":[],"open_gaps":[{"owner":"build","status":"blocked"}]}`,
		},
		{
			name:   "ownerless",
			ledger: `{"rows":[],"open_gaps":[{"status":"blocked"}]}`,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			paths := validationTestPaths(t)
			writeBuildAcceptanceInputs(t, paths)
			writeCoverageLedger(t, paths, tt.ledger)
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

			if payload.Status != "blocked" {
				t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
			}
			if !hasValidationError(payload.Errors, "coverage gap must be resolved") {
				t.Fatalf("Errors = %#v, want coverage gap error", payload.Errors)
			}
		})
	}
}

func seedMatchingQueryReadyDatabase(t *testing.T, paths rt.Paths, rejections []store.RowDecision, mergeRecords []store.MergeRecord) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-0001",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence:     []store.EvidenceImport{{ID: "E-001", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "abc123", Span: "L1-L5", Extractor: "test", ContentHash: "hash-app", Attrs: map[string]any{"language": "go"}}},
		Nodes:        []store.NodeImport{{ID: "N-app", Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-001"}, Attrs: map[string]any{"owner": "app"}}},
		Edges:        []store.EdgeImport{{ID: "EDGE-app-self", Type: "owns", SourceID: "N-app", TargetID: "N-app", Confidence: "verified", EvidenceIDs: []string{"E-001"}, Attrs: map[string]any{"relation": "self"}}},
		Observations: []store.ObservationImport{{ID: "OBS-app", ObservationType: "implementation", Summary: "App exists", EvidenceIDs: []string{"E-001"}, Attrs: map[string]any{"source": "test"}}},
		PathIndex:    []store.PathIndexImport{{ID: "P-001", Path: "src/app.go", NodeID: "N-app", Relation: "owns", Confidence: "verified", EvidenceID: "E-001"}},
		Rejections:   rejections,
		MergeRecords: mergeRecords,
	})
	if err != nil {
		t.Fatal(err)
	}
}

func seedQueryReadyDatabaseWithNodeID(t *testing.T, paths rt.Paths, nodeID string) {
	t.Helper()
	seedQueryReadyDatabaseWithNodeIDAndDecisions(t, paths, nodeID, nil, nil)
}

func seedQueryReadyDatabaseWithNodeIDAndDecisions(t *testing.T, paths rt.Paths, nodeID string, rejections []store.RowDecision, mergeRecords []store.MergeRecord) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-0001",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence:     []store.EvidenceImport{{ID: "E-001", SourceKind: "file", SourcePath: "src/app.go", CommitSHA: "abc123", Span: "L1-L5", Extractor: "test", ContentHash: "hash-app"}},
		Nodes:        []store.NodeImport{{ID: nodeID, Type: "capability", Title: "App", Confidence: "verified", EvidenceIDs: []string{"E-001"}}},
		PathIndex:    []store.PathIndexImport{{ID: "P-001", Path: "src/app.go", NodeID: nodeID, Relation: "owns", Confidence: "verified", EvidenceID: "E-001"}},
		Rejections:   rejections,
		MergeRecords: mergeRecords,
	})
	if err != nil {
		t.Fatal(err)
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

func writeMatchingScanPackage(t *testing.T, paths rt.Paths) {
	t.Helper()
	files := map[string]string{
		filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"):                 `{"id":"E-001","source_kind":"file","source_path":"src/app.go","commit_sha":"abc123","span":"L1-L5","extractor":"test","content_hash":"hash-app","attrs":{"language":"go"}}`,
		filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"):              `{"nodes":[{"id":"N-app","type":"capability","title":"App","confidence":"verified","paths":["src/app.go"],"evidence_ids":["E-001"],"attrs":{"owner":"app"}}]}`,
		filepath.Join(paths.RuntimeDir, "provisional", "edges.json"):              `{"edges":[{"id":"EDGE-app-self","type":"owns","source_id":"N-app","target_id":"N-app","confidence":"verified","evidence_ids":["E-001"],"attrs":{"relation":"self"}}]}`,
		filepath.Join(paths.RuntimeDir, "provisional", "observations.json"):       `{"observations":[{"id":"OBS-app","observation_type":"implementation","summary":"App exists","evidence_ids":["E-001"],"attrs":{"source":"test"}}]}`,
		filepath.Join(paths.RuntimeDir, "coverage.json"):                          `{"rows":[{"path":"src/app.go"}]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "map-scan.md"):               `# Map Scan`,
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.md"):        `# Coverage Ledger`,
		filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-1.md"): `# Lane 1`,
		filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"):              `# Map State`,
		filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"):  `{"rows":[{"path":"src/app.go"}]}`,
	}
	for path, content := range files {
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
}

func writeReadyStatus(t *testing.T, paths rt.Paths, generationID string) {
	t.Helper()
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.ActiveGenerationID = generationID
	status.GraphReady = true
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func writeCoverageLedger(t *testing.T, paths rt.Paths, content string) {
	t.Helper()
	path := filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json")
	if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
		t.Fatal(err)
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

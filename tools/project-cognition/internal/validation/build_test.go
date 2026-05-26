package validation

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
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
	if err := os.MkdirAll(workbench, 0o755); err != nil {
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

func TestValidateBuildBlocksExcludedBoundaryPathInDB(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	writeMatchingScanPackage(t, paths)
	if err := os.WriteFile(
		filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"),
		[]byte(`{
			"schema_version":1,
			"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
			"included_paths":["src/app.go"],
			"excluded_paths":[{"path":"./vendor/lib.go","reason":"vendor","decision_source":".cognitionignore"}],
			"ambiguous_paths":[],
			"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
			"classification_reasons":{"src/app.go":"source file","vendor/lib.go":"vendor"},
			"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
		}`+"\n"),
		0o644,
	); err != nil {
		t.Fatal(err)
	}
	seedMatchingQueryReadyDatabase(t, paths, nil, nil)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(
		context.Background(),
		`INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES('P-vendor', 'GEN-0001', 'vendor/lib.go', 'N-app', 'owns', 'verified', 'E-001', ?)`,
		time.Now().UTC().Format(time.RFC3339),
	); err != nil {
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
	if !hasValidationError(payload.Errors, "excluded boundary path vendor/lib.go must not enter project cognition graph store") {
		t.Fatalf("Errors = %#v, want excluded boundary path leakage error", payload.Errors)
	}
}

func TestValidateBuildBlocksCriticalAndImportantMissingPathIndex(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	allPaths := []string{"src/critical.go", "src/important.go", "src/low-risk.go"}
	indexedPaths := []string{"src/low-risk.go"}
	writeScanPackageWithUniverse(t, paths, allPaths, allPaths, map[string]string{
		"src/critical.go":  "critical",
		"src/important.go": "important",
		"src/low-risk.go":  "low_risk",
	}, allPaths)
	seedQueryReadyDatabaseWithPaths(t, paths, allPaths, indexedPaths)
	writeReadyStatus(t, paths, "GEN-0001")

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	for _, want := range []string{
		"critical_missing_path_index: src/critical.go",
		"important_missing_path_index: src/important.go",
	} {
		if !hasValidationError(payload.Errors, want) {
			t.Fatalf("Errors = %#v, want %q", payload.Errors, want)
		}
	}
}

func TestValidateBuildWarnsBelowNinetyPercentAndFailsBelowSeventyPercent(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	allPaths := numberedSourcePaths(10)
	indexedPaths := allPaths[:7]
	criticality := map[string]string{}
	for _, path := range allPaths {
		criticality[path] = "low_risk"
	}
	writeScanPackageWithUniverse(t, paths, allPaths, allPaths, criticality, allPaths)
	seedQueryReadyDatabaseWithPaths(t, paths, allPaths, indexedPaths)
	writeReadyStatus(t, paths, "GEN-0001")

	payload := ValidateBuild(paths)

	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationWarning(payload.Warnings, "path_index_to_included_ratio 0.70 is below warning threshold 0.90") {
		t.Fatalf("Warnings = %#v, want sparse ratio warning", payload.Warnings)
	}
}

func TestValidateBuildFailsBelowSeventyPercentRatio(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	allPaths := numberedSourcePaths(10)
	indexedPaths := allPaths[:6]
	criticality := map[string]string{}
	for _, path := range allPaths {
		criticality[path] = "low_risk"
	}
	writeScanPackageWithUniverse(t, paths, allPaths, allPaths, criticality, allPaths)
	seedQueryReadyDatabaseWithPaths(t, paths, allPaths, indexedPaths)
	writeReadyStatus(t, paths, "GEN-0001")

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationError(payload.Errors, "path_index_to_included_ratio 0.60 is below hard threshold 0.70") {
		t.Fatalf("Errors = %#v, want sparse ratio hard failure", payload.Errors)
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
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('runtime_format', '"project-cognition-go"', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('runtime_schema', '1', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('schema_version', '1', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('active_generation_id', '"GEN-0001"', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('graph_store_path', '".specify/project-cognition/project-cognition.db"', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('graph_ready', 'true', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('baseline_state', '"fresh"', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('query_contract_version', '1', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`,
		`INSERT INTO metadata(key, value_json, updated_at) VALUES('update_contract_version', '1', ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at`,
	}
	args := [][]any{
		{now, now},
		{now},
		{now, now},
		{now},
		{now},
		{now},
		{now},
		{now},
		{now},
		{now},
		{now},
		{now},
		{now},
	}
	for i, statement := range statements {
		if _, err := db.ExecContext(context.Background(), statement, args[i]...); err != nil {
			t.Fatal(err)
		}
	}
}

func seedQueryReadyDatabaseWithPaths(t *testing.T, paths rt.Paths, pathsInScan, indexedPaths []string) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	input := store.ImportInput{
		GenerationID: "GEN-0001",
		Kind:         "full",
		SourceCommit: "abc123",
	}
	for i, path := range pathsInScan {
		evidenceID := fmt.Sprintf("E-%03d", i+1)
		nodeID := fmt.Sprintf("N-%03d", i+1)
		input.Evidence = append(input.Evidence, store.EvidenceImport{
			ID:          evidenceID,
			SourceKind:  "file",
			SourcePath:  path,
			CommitSHA:   "abc123",
			Span:        "L1-L5",
			Extractor:   "test",
			ContentHash: fmt.Sprintf("hash-%03d", i+1),
		})
		input.Nodes = append(input.Nodes, store.NodeImport{
			ID:          nodeID,
			Type:        "capability",
			Title:       path,
			Confidence:  "verified",
			EvidenceIDs: []string{evidenceID},
		})
		input.Observations = append(input.Observations, store.ObservationImport{
			ID:              fmt.Sprintf("OBS-%03d", i+1),
			ObservationType: "implementation",
			Summary:         path + " exists",
			EvidenceIDs:     []string{evidenceID},
		})
	}
	pathToOrdinal := map[string]int{}
	for i, path := range pathsInScan {
		pathToOrdinal[path] = i + 1
	}
	indexedSet := map[string]bool{}
	for _, path := range indexedPaths {
		indexedSet[path] = true
	}
	for _, path := range pathsInScan {
		if !indexedSet[path] {
			input.Rejections = append(input.Rejections, store.RowDecision{
				Category: "coverage",
				Identity: path,
				Reason:   "accepted_low_risk_sparse_fixture",
			})
		}
	}
	for _, path := range indexedPaths {
		ordinal := pathToOrdinal[path]
		if ordinal == 0 {
			t.Fatalf("indexed path %s was not supplied in paths", path)
		}
		input.PathIndex = append(input.PathIndex, store.PathIndexImport{
			ID:         fmt.Sprintf("P-%03d", ordinal),
			Path:       path,
			NodeID:     fmt.Sprintf("N-%03d", ordinal),
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: fmt.Sprintf("E-%03d", ordinal),
		})
	}
	if len(pathsInScan) > 0 {
		input.Edges = append(input.Edges, store.EdgeImport{
			ID:          "EDGE-self",
			Type:        "owns",
			SourceID:    "N-001",
			TargetID:    "N-001",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-001"},
		})
	}
	if _, err := st.ImportGeneration(context.Background(), input); err != nil {
		t.Fatal(err)
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
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"):      `{"rows":[{"path":"src/app.go","status":"covered"}],"open_gaps":[]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-1.md"): `# Lane 1`,
		filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json"): `{
			"packet_id":"lane-1",
			"family_id":"app",
			"assigned_paths":["src/app.go"],
			"paths_read":["src/app.go"],
			"ledger":{"todo":[],"doing":[],"done":["src/app.go"],"blocked":[],"overflow":[]},
			"coverage":[{"path":"src/app.go","outcome":"read","evidence_ids":["E-001"]}],
			"confidence":"high",
			"acceptance":"pass"
		}`,
		filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"):             `# Map State`,
		filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"): `{"rows":[{"path":"src/app.go"}]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"): `{"packets":[{
			"packet_id":"lane-1",
			"state":"accepted",
			"assigned_paths":["src/app.go"],
			"result_handoff_path":".specify/project-cognition/workbench/worker-results/lane-1.json"
		}]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"): `{"events":[
			{"event_id":"dispatch-1","packet_id":"lane-1","event_type":"dispatched","created_at":"2026-05-26T00:00:00Z"},
			{"event_id":"return-1","packet_id":"lane-1","event_type":"returned","worker_result_path":".specify/project-cognition/workbench/worker-results/lane-1.json","created_at":"2026-05-26T00:01:00Z"}
		]}`,
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

func writeScanPackageWithUniverse(t *testing.T, paths rt.Paths, universePaths, included []string, criticality map[string]string, indexed []string) {
	t.Helper()
	indexedSet := map[string]bool{}
	for _, path := range indexed {
		indexedSet[path] = true
	}
	coverageRows := []map[string]any{}
	ledgerRows := []map[string]any{}
	evidenceRows := []map[string]any{}
	nodeRows := []map[string]any{}
	workerCoverage := []map[string]any{}
	for i, path := range universePaths {
		evidenceID := fmt.Sprintf("E-%03d", i+1)
		nodeRows = append(nodeRows, map[string]any{
			"id":           fmt.Sprintf("N-%03d", i+1),
			"type":         "capability",
			"title":        path,
			"confidence":   "verified",
			"paths":        []string{path},
			"evidence_ids": []string{evidenceID},
		})
		evidenceRows = append(evidenceRows, map[string]any{
			"id":           evidenceID,
			"source_kind":  "file",
			"source_path":  path,
			"commit_sha":   "abc123",
			"span":         "L1-L5",
			"extractor":    "test",
			"content_hash": fmt.Sprintf("hash-%03d", i+1),
		})
	}
	for _, path := range indexed {
		ordinal := pathOrdinalForBuildFixture(t, universePaths, path)
		evidenceID := fmt.Sprintf("E-%03d", ordinal)
		coverageRows = append(coverageRows, map[string]any{"path": path})
		ledgerRows = append(ledgerRows, map[string]any{"path": path, "status": "accepted"})
		workerCoverage = append(workerCoverage, map[string]any{
			"path":         path,
			"outcome":      "read",
			"evidence_ids": []string{evidenceID},
		})
	}
	candidates := []map[string]any{}
	dispositions := map[string]string{}
	reasons := map[string]string{}
	sources := map[string]string{}
	criticalityMap := map[string]string{}
	for _, path := range universePaths {
		candidates = append(candidates, map[string]any{
			"path":            path,
			"disposition":     "deep_read",
			"decision_source": "git",
		})
		dispositions[path] = "deep_read"
		reasons[path] = "test fixture"
		sources[path] = "git"
		value := criticality[path]
		if value == "" {
			value = "low_risk"
		}
		criticalityMap[path] = value
	}
	openGaps := []map[string]any{}
	for _, path := range included {
		if indexedSet[path] {
			continue
		}
		openGaps = append(openGaps, map[string]any{
			"path":                 path,
			"status":               "low_risk_open_gap",
			"coverage_state":       "low_risk_open_gap",
			"owner":                "scan",
			"reason":               "accepted_low_risk_sparse_fixture",
			"evidence_expectation": "not required for low-risk fixture",
			"revisit_condition":    "path changes",
		})
	}
	files := map[string]any{
		filepath.Join(paths.RuntimeDir, "evidence", "rows.json"): map[string]any{"rows": evidenceRows},
		filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"): map[string]any{
			"nodes": nodeRows,
		},
		filepath.Join(paths.RuntimeDir, "provisional", "edges.json"): map[string]any{
			"edges": edgeRowsForBuildFixture(universePaths),
		},
		filepath.Join(paths.RuntimeDir, "provisional", "observations.json"): map[string]any{
			"observations": observationRowsForBuildFixture(universePaths),
		},
		filepath.Join(paths.RuntimeDir, "coverage.json"): map[string]any{"rows": coverageRows},
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"): map[string]any{
			"rows":      ledgerRows,
			"open_gaps": openGaps,
		},
		filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"): map[string]any{
			"schema_version":         1,
			"candidate_universe":     candidates,
			"included_paths":         included,
			"excluded_paths":         []string{},
			"ambiguous_paths":        []string{},
			"dispositions":           dispositions,
			"criticality":            criticalityMap,
			"classification_reasons": reasons,
			"decision_source":        sources,
		},
		filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"): map[string]any{
			"packets": []map[string]any{{
				"packet_id":           "lane-1",
				"state":               "accepted",
				"assigned_paths":      indexed,
				"result_handoff_path": ".specify/project-cognition/workbench/worker-results/lane-1.json",
			}},
		},
		filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"): map[string]any{
			"events": []map[string]any{
				{"event_id": "dispatch-1", "packet_id": "lane-1", "event_type": "dispatched", "created_at": "2026-05-26T00:00:00Z"},
				{"event_id": "return-1", "packet_id": "lane-1", "event_type": "returned", "worker_result_path": ".specify/project-cognition/workbench/worker-results/lane-1.json", "created_at": "2026-05-26T00:01:00Z"},
			},
		},
		filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json"): map[string]any{
			"packet_id":      "lane-1",
			"family_id":      "sparse-fixture",
			"assigned_paths": indexed,
			"paths_read":     indexed,
			"ledger": map[string]any{
				"todo":     []string{},
				"doing":    []string{},
				"done":     indexed,
				"blocked":  []string{},
				"overflow": []string{},
			},
			"coverage":   workerCoverage,
			"confidence": "high",
			"acceptance": "pass",
		},
	}
	for path, payload := range files {
		writeJSONFileForBuildTest(t, path, payload)
	}
	for _, file := range []string{
		filepath.Join(paths.RuntimeDir, "workbench", "map-scan.md"),
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.md"),
		filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"),
		filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-1.md"),
	} {
		if err := os.MkdirAll(filepath.Dir(file), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(file, []byte("# Build Test Fixture\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
}

func writeJSONFileForBuildTest(t *testing.T, path string, payload any) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func observationRowsForBuildFixture(paths []string) []map[string]any {
	rows := make([]map[string]any, 0, len(paths))
	for i, path := range paths {
		rows = append(rows, map[string]any{
			"id":               fmt.Sprintf("OBS-%03d", i+1),
			"observation_type": "implementation",
			"summary":          path + " exists",
			"evidence_ids":     []string{fmt.Sprintf("E-%03d", i+1)},
		})
	}
	return rows
}

func edgeRowsForBuildFixture(paths []string) []map[string]any {
	if len(paths) == 0 {
		return []map[string]any{}
	}
	return []map[string]any{{
		"id":           "EDGE-self",
		"type":         "owns",
		"source_id":    "N-001",
		"target_id":    "N-001",
		"confidence":   "verified",
		"evidence_ids": []string{"E-001"},
	}}
}

func pathOrdinalForBuildFixture(t *testing.T, paths []string, path string) int {
	t.Helper()
	for i, candidate := range paths {
		if candidate == path {
			return i + 1
		}
	}
	t.Fatalf("path %s was not supplied in universe paths", path)
	return 0
}

func numberedSourcePaths(count int) []string {
	paths := make([]string, 0, count)
	for i := 1; i <= count; i++ {
		paths = append(paths, fmt.Sprintf("src/path-%02d.go", i))
	}
	return paths
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

func hasValidationWarning(warnings []string, want string) bool {
	for _, warning := range warnings {
		if strings.Contains(warning, want) {
			return true
		}
	}
	return false
}

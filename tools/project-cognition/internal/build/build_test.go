package build

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestRunCreatesGoRuntimeFromScanPackage(t *testing.T) {
	paths := writeMinimalScanPackage(t)

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v", err)
	}
	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%v", payload.Status, payload.Errors)
	}
	if payload.Readiness != rt.ReadyReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.ReadyReadiness)
	}
	if payload.ActiveGenerationID == "" {
		t.Fatal("ActiveGenerationID is empty")
	}
	if payload.ScanArtifactCounts["nodes"] != 1 || payload.ScanArtifactCounts["coverage_paths"] != 2 {
		t.Fatalf("ScanArtifactCounts = %#v, want one node and two coverage paths", payload.ScanArtifactCounts)
	}
	if payload.DBCounts["nodes"] != 1 || payload.DBCounts["coverage_paths"] != 1 {
		t.Fatalf("DBCounts = %#v, want one node and one indexed coverage path", payload.DBCounts)
	}
	if payload.IdentityReconciliation["nodes"].Status != "ok" {
		t.Fatalf("node reconciliation = %#v, want ok", payload.IdentityReconciliation["nodes"])
	}
	if payload.IdentityReconciliation["coverage_paths"].Status != "mismatch" {
		t.Fatalf("coverage reconciliation = %#v, want decision-covered mismatch", payload.IdentityReconciliation["coverage_paths"])
	}
	if len(payload.Rejections) != 1 || payload.Rejections[0].Identity != "docs/guide.md" || payload.Rejections[0].Reason != "no_node_relation" {
		t.Fatalf("Rejections = %#v, want coverage rejection for docs/guide.md", payload.Rejections)
	}
	if payload.MergeRecords == nil {
		t.Fatal("MergeRecords is nil, want present empty slice")
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.ActiveGenerationID != payload.ActiveGenerationID {
		t.Fatalf("status ActiveGenerationID = %q, want payload %q", status.ActiveGenerationID, payload.ActiveGenerationID)
	}
	if !status.GraphReady || status.QueryContractVersion != 1 || status.UpdateContractVersion != 1 {
		t.Fatalf("status graph contract fields = %#v", status)
	}

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	snapshot, err := st.ActiveIdentitySnapshot(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if !snapshot.Nodes["N-app"] {
		t.Fatalf("snapshot nodes = %#v, want N-app", snapshot.Nodes)
	}
	if !snapshot.CoveragePaths["src/app.go"] {
		t.Fatalf("snapshot coverage paths = %#v, want src/app.go", snapshot.CoveragePaths)
	}
}

func TestReconciliationErrorsRequireExplicitDecisionRecords(t *testing.T) {
	reconciliation := map[string]ReconciliationCategory{
		"coverage_paths": {Status: "mismatch", Missing: []string{"docs/guide.md"}},
		"nodes":          {Status: "mismatch", Missing: []string{"N-missing"}},
	}
	snapshot := store.IdentitySnapshot{
		Rejections: []store.RowDecision{{Category: "coverage", Identity: "docs/guide.md", Reason: "no_node_relation"}},
	}

	errors := reconciliationErrors(reconciliation, snapshot)

	if len(errors) != 1 || !strings.Contains(errors[0], "missing scan node identities: N-missing") {
		t.Fatalf("errors = %#v, want only uncovered missing node", errors)
	}
}

func TestRunReplacesLegacyStatus(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	data, _ := json.Marshal(map[string]any{"freshness": "fresh", "graph_ready": true})
	if err := os.WriteFile(paths.StatusPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v", err)
	}
	if !payload.LegacyRuntimeReplaced {
		t.Fatal("LegacyRuntimeReplaced = false, want true")
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.RuntimeFormat != rt.RuntimeFormat {
		t.Fatalf("RuntimeFormat = %q, want %q", status.RuntimeFormat, rt.RuntimeFormat)
	}
}

func TestRunIndexesNodePathWithoutEvidence(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{
		"nodes": []map[string]any{{
			"id":         "N-docs",
			"type":       "doc",
			"title":      "Docs",
			"confidence": "",
			"paths":      []string{"docs/guide.md"},
			"attrs":      map[string]any{"owner": "test"},
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), map[string]any{
		"edges": []map[string]any{},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), map[string]any{
		"observations": []map[string]any{},
	})

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v; payload=%#v", err, payload)
	}
	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%v", payload.Status, payload.Errors)
	}
	for _, rejection := range payload.Rejections {
		if rejection.Category == "coverage" && rejection.Identity == "docs/guide.md" && rejection.Reason == "no_node_relation" {
			t.Fatalf("Rejections = %#v, want no no_node_relation rejection for docs/guide.md", payload.Rejections)
		}
	}

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	snapshot, err := st.ActiveIdentitySnapshot(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if !snapshot.CoveragePaths["docs/guide.md"] {
		t.Fatalf("snapshot coverage paths = %#v, want docs/guide.md", snapshot.CoveragePaths)
	}

	var evidenceID, confidence string
	if err := st.DB().QueryRowContext(context.Background(), `SELECT evidence_id, confidence FROM path_index WHERE path = ?`, "docs/guide.md").Scan(&evidenceID, &confidence); err != nil {
		t.Fatal(err)
	}
	if evidenceID != "" {
		t.Fatalf("path_index evidence_id = %q, want empty", evidenceID)
	}
	if confidence != "provisional" {
		t.Fatalf("path_index confidence = %q, want provisional", confidence)
	}
}

func TestRunImportsPathIndexRowsWithCollidingSanitizedPaths(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	writeJSON(t, filepath.Join(paths.RuntimeDir, "evidence", "app.json"), map[string]any{
		"rows": []map[string]any{
			{
				"id":           "E-001",
				"source_kind":  "source",
				"source_path":  "src/a/b.go",
				"commit_sha":   "abc123",
				"span":         "1:1-10:1",
				"extractor":    "test",
				"content_hash": "hash-a-b",
				"attrs":        map[string]any{"language": "go"},
			},
			{
				"id":           "E-002",
				"source_kind":  "source",
				"source_path":  "src/a-b.go",
				"commit_sha":   "abc123",
				"span":         "1:1-10:1",
				"extractor":    "test",
				"content_hash": "hash-a-dash-b",
				"attrs":        map[string]any{"language": "go"},
			},
		},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{
		"nodes": []map[string]any{{
			"id":           "N-app",
			"type":         "capability",
			"title":        "App",
			"confidence":   "verified",
			"paths":        []string{"src/a/b.go", "src/a-b.go"},
			"evidence_ids": []string{"E-001", "E-002"},
			"attrs":        map[string]any{"owner": "test"},
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "coverage.json"), map[string]any{
		"rows": []map[string]any{
			{"path": "src/a/b.go"},
			{"path": "src/a-b.go"},
		},
	})

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v; payload=%#v", err, payload)
	}
	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%v", payload.Status, payload.Errors)
	}

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	rows, err := st.DB().QueryContext(context.Background(), `SELECT id, path, node_id FROM path_index ORDER BY path`)
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	seen := map[string]string{}
	ids := map[string]bool{}
	for rows.Next() {
		var id, path, nodeID string
		if err := rows.Scan(&id, &path, &nodeID); err != nil {
			t.Fatal(err)
		}
		seen[path] = nodeID
		if ids[id] {
			t.Fatalf("duplicate path_index id %q", id)
		}
		ids[id] = true
	}
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
	for _, path := range []string{"src/a/b.go", "src/a-b.go"} {
		if seen[path] != "N-app" {
			t.Fatalf("path_index rows = %#v, want %s owned by N-app", seen, path)
		}
	}
}

func TestRunArchivesLegacyThinDatabaseBeforeImport(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	for _, statement := range []string{
		`CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)`,
		`CREATE TABLE generations(id TEXT PRIMARY KEY, state TEXT NOT NULL)`,
		`INSERT INTO metadata(key, value) VALUES('schema_version', '0')`,
		`INSERT INTO generations(id, state) VALUES('GEN-legacy', 'active')`,
	} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			t.Fatal(err)
		}
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v; payload=%#v", err, payload)
	}
	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%v", payload.Status, payload.Errors)
	}
	if !payload.LegacyRuntimeReplaced {
		t.Fatal("LegacyRuntimeReplaced = false, want true")
	}
	if payload.ActiveGenerationID == "" || payload.ActiveGenerationID == "GEN-legacy" {
		t.Fatalf("ActiveGenerationID = %q, want fresh non-legacy generation", payload.ActiveGenerationID)
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.ActiveGenerationID != payload.ActiveGenerationID || !status.GraphReady {
		t.Fatalf("status = %#v, want active fresh graph", status)
	}

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	activeID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if activeID != payload.ActiveGenerationID {
		t.Fatalf("active generation = %q, want payload %q", activeID, payload.ActiveGenerationID)
	}
	if _, err := os.Stat(paths.DatabasePath + ".legacy"); err != nil {
		t.Fatalf("legacy database archive missing: %v", err)
	}
}

func TestRunBlocksWhenStatusWriteFailsAfterDBCommit(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	badStatusPath := filepath.Join(paths.Root, "missing-parent", "status.json")
	paths.StatusPath = badStatusPath

	payload, err := Run(paths)
	if err == nil {
		t.Fatal("Run() error = nil, want status write error")
	}
	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.RecoveryAction != "rewrite_status_from_db_metadata" {
		t.Fatalf("RecoveryAction = %q, want rewrite_status_from_db_metadata", payload.RecoveryAction)
	}
	if payload.ActiveGenerationID == "" {
		t.Fatal("ActiveGenerationID is empty after status write failure")
	}

	st, openErr := store.OpenExisting(paths)
	if openErr != nil {
		t.Fatal(openErr)
	}
	defer st.Close()
	activeID, activeErr := st.ActiveGenerationID(context.Background())
	if activeErr != nil {
		t.Fatal(activeErr)
	}
	if activeID != payload.ActiveGenerationID {
		t.Fatalf("DB active generation = %q, want payload %q", activeID, payload.ActiveGenerationID)
	}
	if _, statErr := os.Stat(paths.StatusPath); !errors.Is(statErr, os.ErrNotExist) {
		t.Fatalf("status file stat error = %v, want missing file", statErr)
	}
}

func writeMinimalScanPackage(t *testing.T) rt.Paths {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	mkdirs := []string{
		filepath.Join(paths.RuntimeDir, "evidence"),
		filepath.Join(paths.RuntimeDir, "provisional"),
		filepath.Join(paths.RuntimeDir, "workbench", "scan-packets"),
	}
	for _, dir := range mkdirs {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	writeJSON(t, filepath.Join(paths.RuntimeDir, "evidence", "app.json"), map[string]any{
		"rows": []map[string]any{{
			"id":           "E-001",
			"source_kind":  "source",
			"source_path":  "src/app.go",
			"commit_sha":   "abc123",
			"span":         "1:1-10:1",
			"extractor":    "test",
			"content_hash": "hash-app",
			"attrs":        map[string]any{"language": "go"},
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{
		"nodes": []map[string]any{{
			"id":           "N-app",
			"type":         "capability",
			"title":        "App",
			"confidence":   "verified",
			"paths":        []string{"src/app.go"},
			"evidence_ids": []string{"E-001"},
			"attrs":        map[string]any{"owner": "test"},
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), map[string]any{
		"edges": []map[string]any{{
			"id":           "EDGE-app-self",
			"type":         "owns",
			"source_id":    "N-app",
			"target_id":    "N-app",
			"confidence":   "verified",
			"evidence_ids": []string{"E-001"},
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), map[string]any{
		"observations": []map[string]any{{
			"id":               "OBS-app",
			"observation_type": "summary",
			"summary":          "App observed",
			"evidence_ids":     []string{"E-001"},
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "coverage.json"), map[string]any{
		"rows": []map[string]any{
			{"path": "src/app.go"},
			{"path": "docs/guide.md"},
		},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), map[string]any{
		"rows":      []map[string]any{{"path": "src/app.go", "status": "covered"}},
		"open_gaps": []map[string]any{},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), map[string]any{
		"rows": []map[string]any{{"path": "src/app.go"}},
	})
	for _, rel := range []string{
		filepath.Join("workbench", "map-scan.md"),
		filepath.Join("workbench", "coverage-ledger.md"),
		filepath.Join("workbench", "map-state.md"),
	} {
		if err := os.WriteFile(filepath.Join(paths.RuntimeDir, rel), []byte("# Test\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return paths
}

func writeJSON(t *testing.T, path string, payload any) {
	t.Helper()
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func containsError(errors []string, want string) bool {
	for _, err := range errors {
		if strings.Contains(err, want) {
			return true
		}
	}
	return false
}

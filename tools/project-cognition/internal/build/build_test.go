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
	if payload.Compilation.ContractVersion != 1 || payload.Compilation.Status != "compiled" || !payload.Compilation.PublicationAllowed {
		t.Fatalf("Compilation = %#v, want publishable contract v1", payload.Compilation)
	}
	if payload.Compilation.ProposalFingerprint == "" || payload.Compilation.CompiledFingerprint == "" {
		t.Fatalf("Compilation = %#v, want deterministic fingerprints", payload.Compilation)
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
	metadata, err := st.Metadata(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if metadata["active_generation_id"] != payload.ActiveGenerationID {
		t.Fatalf("metadata active_generation_id = %q, want payload %q", metadata["active_generation_id"], payload.ActiveGenerationID)
	}
	if metadata["graph_ready"] != "true" || metadata["baseline_state"] != "fresh" {
		t.Fatalf("metadata = %#v, want query-ready graph metadata after successful sparse gates", metadata)
	}
	if metadata["query_contract_version"] != "1" || metadata["update_contract_version"] != "1" {
		t.Fatalf("metadata = %#v, want ready contract versions after successful sparse gates", metadata)
	}
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

func TestRunBlocksCompilerConflictBeforeCreatingGraphStore(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{
		"nodes": []map[string]any{
			{
				"id": "N-app", "type": "capability", "title": "App", "confidence": "high",
				"paths": []string{"src/app.go"}, "evidence_ids": []string{"E-001"},
			},
			{
				"id": "N-app", "type": "capability", "title": "Conflicting App", "confidence": "high",
				"paths": []string{"src/app.go"}, "evidence_ids": []string{"E-001"},
			},
		},
	})

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v; payload=%#v", err, payload)
	}
	if payload.Status != "blocked" || payload.Compilation.PublicationAllowed {
		t.Fatalf("payload = %#v, want compiler-blocked publication", payload)
	}
	if payload.ActiveGenerationID != "" {
		t.Fatalf("ActiveGenerationID = %q, want empty", payload.ActiveGenerationID)
	}
	if _, err := os.Stat(paths.DatabasePath); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("graph store stat error = %v, want not exist", err)
	}
}

func TestRunBlocksReadyPublicationWhenSparsePathIndexFails(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	writeSparseBuildBoundary(t, paths, []sparseBuildPath{
		{Path: "src/app.go", Criticality: "critical", Indexed: true},
		{Path: "src/important.go", Criticality: "important", Indexed: false},
	})

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v; payload=%#v", err, payload)
	}
	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%v", payload.Status, payload.Errors)
	}
	if payload.Readiness != rt.BlockedReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.BlockedReadiness)
	}
	if !containsError(payload.Errors, "important_missing_path_index: src/important.go") {
		t.Fatalf("Errors = %#v, want sparse path-index failure", payload.Errors)
	}
	if payload.SparsePathIndexDetails["index_required_count"] != 2 {
		t.Fatalf("SparsePathIndexDetails = %#v, want sparse gate details", payload.SparsePathIndexDetails)
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.Readiness == rt.ReadyReadiness || status.Freshness == rt.ReadyFreshness || status.GraphReady {
		t.Fatalf("status = %#v, want non-ready status after sparse gate failure", status)
	}

	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	metadata, err := st.Metadata(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if metadata["graph_ready"] == "true" || metadata["baseline_state"] == "fresh" {
		t.Fatalf("metadata = %#v, want non-ready metadata after sparse gate failure", metadata)
	}
	if metadata["query_contract_version"] == "1" || metadata["update_contract_version"] == "1" {
		t.Fatalf("metadata = %#v, want blocked metadata without ready contract versions", metadata)
	}
}

func TestRunRewritesPreexistingReadyStatusWhenSparsePathIndexFails(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	readyStatus := rt.DefaultStatus(paths)
	readyStatus.Status = "ok"
	readyStatus.Freshness = rt.ReadyFreshness
	readyStatus.Readiness = rt.ReadyReadiness
	readyStatus.RecommendedNextAction = "use_project_cognition"
	readyStatus.GraphReady = true
	readyStatus.ActiveGenerationID = "GEN-previous"
	readyStatus.QueryContractVersion = 1
	readyStatus.UpdateContractVersion = 1
	if err := rt.WriteStatus(paths, readyStatus); err != nil {
		t.Fatal(err)
	}
	writeSparseBuildBoundary(t, paths, []sparseBuildPath{
		{Path: "src/app.go", Criticality: "critical", Indexed: true},
		{Path: "src/important.go", Criticality: "important", Indexed: false},
	})

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v; payload=%#v", err, payload)
	}
	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%v", payload.Status, payload.Errors)
	}
	if payload.Readiness != rt.BlockedReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.BlockedReadiness)
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.Readiness == rt.ReadyReadiness || status.Freshness == rt.ReadyFreshness || status.GraphReady {
		t.Fatalf("status = %#v, want preexisting ready status rewritten as non-ready", status)
	}
}

func TestRunRewritesPreexistingReadyStatusWhenReconciliationFails(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	readyStatus := rt.DefaultStatus(paths)
	readyStatus.Status = "ok"
	readyStatus.Freshness = rt.ReadyFreshness
	readyStatus.Readiness = rt.ReadyReadiness
	readyStatus.RecommendedNextAction = "use_project_cognition"
	readyStatus.GraphReady = true
	readyStatus.ActiveGenerationID = "GEN-previous"
	readyStatus.QueryContractVersion = 1
	readyStatus.UpdateContractVersion = 1
	if err := rt.WriteStatus(paths, readyStatus); err != nil {
		t.Fatal(err)
	}
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{
		"nodes": []map[string]any{{
			"id":           "N-app",
			"type":         "capability",
			"title":        "App",
			"confidence":   "verified",
			"paths":        []string{"src/app.go", "docs/unexpected.md"},
			"evidence_ids": []string{"E-001"},
			"attrs":        map[string]any{"owner": "test"},
		}},
	})

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v; payload=%#v", err, payload)
	}
	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%v", payload.Status, payload.Errors)
	}
	if !containsError(payload.Errors, "unexpected DB coverage path identities: docs/unexpected.md") {
		t.Fatalf("Errors = %#v, want unexpected reconciliation failure", payload.Errors)
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.Readiness == rt.ReadyReadiness || status.Freshness == rt.ReadyFreshness || status.GraphReady {
		t.Fatalf("status = %#v, want preexisting ready status rewritten as non-ready", status)
	}
	if status.ActiveGenerationID != payload.ActiveGenerationID {
		t.Fatalf("status ActiveGenerationID = %q, want current generation %q", status.ActiveGenerationID, payload.ActiveGenerationID)
	}
}

func TestRunPublishesReadyWhenSparsePathIndexOnlyWarns(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	writeSparseBuildBoundary(t, paths, []sparseBuildPath{
		{Path: "src/app.go", Criticality: "critical", Indexed: true},
		{Path: "src/important.go", Criticality: "important", Indexed: true},
		{Path: "src/low-1.go", Criticality: "low_risk", Indexed: true},
		{Path: "src/low-2.go", Criticality: "low_risk", Indexed: true},
		{Path: "src/low-3.go", Criticality: "low_risk", Indexed: true},
		{Path: "src/low-4.go", Criticality: "low_risk", Indexed: false},
		{Path: "src/low-5.go", Criticality: "low_risk", Indexed: false},
	})

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v; payload=%#v", err, payload)
	}
	if payload.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%v", payload.Status, payload.Errors)
	}
	if payload.Readiness != rt.ReadyReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.ReadyReadiness)
	}
	if !containsError(payload.Warnings, "path_index_to_included_ratio 0.71 is below warning threshold 0.90") {
		t.Fatalf("Warnings = %#v, want sparse warning", payload.Warnings)
	}
	if payload.SparsePathIndexDetails["path_index_to_included_ratio"] != "0.71" {
		t.Fatalf("SparsePathIndexDetails = %#v, want warning ratio detail", payload.SparsePathIndexDetails)
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.Readiness != rt.ReadyReadiness || status.Freshness != rt.ReadyFreshness || !status.GraphReady {
		t.Fatalf("status = %#v, want query-ready graph", status)
	}
}

func TestRunBuildsPathIndexFromCompatibilityNodeFields(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	const pagePath = "desktop/src/pages/ActiveSession.tsx"
	writeJSON(t, filepath.Join(paths.RuntimeDir, "evidence", "app.json"), map[string]any{
		"rows": []map[string]any{{
			"id":           "E-active-session",
			"source_kind":  "source",
			"source_path":  pagePath,
			"commit_sha":   "abc123",
			"span":         "1:1-10:1",
			"extractor":    "test",
			"content_hash": "hash-active-session",
			"attrs_json":   map[string]any{"language": "tsx"},
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{
		"nodes": []map[string]any{{
			"node_id":     "NO_ID",
			"kind":        "page",
			"label":       "Active Session Page",
			"confidence":  "verified",
			"evidence_id": "E-active-session",
			"attrs_json": map[string]any{
				"path":   pagePath,
				"detail": "session UI",
			},
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), map[string]any{
		"edges": []map[string]any{{
			"id":             "NO_ID",
			"kind":           "owns",
			"source_node_id": pagePath,
			"target_node_id": pagePath,
			"confidence":     "verified",
			"evidence_id":    "E-active-session",
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), map[string]any{
		"observations": []any{"Active session page owns session UI state"},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "coverage.json"), map[string]any{
		"coverage": []map[string]any{{"path": pagePath}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), map[string]any{
		"rows":      []map[string]any{{"path": pagePath, "status": "covered"}},
		"open_gaps": []map[string]any{},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), map[string]any{
		"rows": []map[string]any{{"path": pagePath}},
	})
	writeAcceptedScanQueue(t, paths, []string{pagePath})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json"), map[string]any{
		"packet_id":      "lane-1",
		"family_id":      "desktop",
		"assigned_paths": []string{pagePath},
		"paths_read":     []string{pagePath},
		"ledger": map[string]any{
			"todo":     []string{},
			"doing":    []string{},
			"done":     []string{pagePath},
			"blocked":  []string{},
			"overflow": []string{},
		},
		"coverage": []map[string]any{{
			"path":        pagePath,
			"outcome":     "read",
			"evidence_id": "E-active-session",
		}},
		"confidence": "high",
		"acceptance": "pass",
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
	var nodeID, nodeType, nodeTitle, path string
	err = st.DB().QueryRowContext(
		context.Background(),
		`SELECT n.id, n.type, n.title, p.path
		 FROM nodes n
		 JOIN path_index p ON p.node_id = n.id
		 WHERE p.path = ?`,
		pagePath,
	).Scan(&nodeID, &nodeType, &nodeTitle, &path)
	if err != nil {
		t.Fatal(err)
	}
	if nodeID == "" || nodeID == "NO_ID" {
		t.Fatalf("nodeID = %q, want generated stable ID", nodeID)
	}
	if nodeType != "page" || nodeTitle != "Active Session Page" || path != pagePath {
		t.Fatalf("row = (%q, %q, %q, %q), want normalized page/title/path", nodeID, nodeType, nodeTitle, path)
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
	writeSparseBuildBoundary(t, paths, []sparseBuildPath{
		{Path: "docs/guide.md", Criticality: "low_risk", Indexed: true},
	})
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
	writeSparseBuildBoundary(t, paths, []sparseBuildPath{
		{Path: "src/a/b.go", Criticality: "low_risk", Indexed: true},
		{Path: "src/a-b.go", Criticality: "low_risk", Indexed: true},
	})
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
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), map[string]any{
		"rows": []map[string]any{
			{"path": "src/a/b.go", "status": "covered"},
			{"path": "src/a-b.go", "status": "covered"},
		},
		"open_gaps": []map[string]any{},
	})
	writeAcceptedScanQueue(t, paths, []string{"src/a/b.go", "src/a-b.go"})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json"), map[string]any{
		"packet_id":      "lane-1",
		"family_id":      "app",
		"assigned_paths": []string{"src/a/b.go", "src/a-b.go"},
		"paths_read":     []string{"src/a/b.go", "src/a-b.go"},
		"ledger": map[string]any{
			"todo":     []string{},
			"doing":    []string{},
			"done":     []string{"src/a/b.go", "src/a-b.go"},
			"blocked":  []string{},
			"overflow": []string{},
		},
		"coverage": []map[string]any{
			{"path": "src/a/b.go", "outcome": "read", "evidence_ids": []string{"E-001"}},
			{"path": "src/a-b.go", "outcome": "read", "evidence_ids": []string{"E-002"}},
		},
		"confidence": "high",
		"acceptance": "pass",
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

func TestRunAcceptsEvidenceIDAliasDuringImport(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	writeJSON(t, filepath.Join(paths.RuntimeDir, "evidence", "app.json"), map[string]any{
		"rows": []map[string]any{{
			"evidence_id":  "mod-001",
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
			"id":          "project-root",
			"type":        "capability",
			"title":       "Project Root",
			"confidence":  "verified",
			"paths":       []string{"src/app.go"},
			"evidence_id": "mod-001",
			"attrs":       map[string]any{"owner": "test"},
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), map[string]any{
		"edges": []map[string]any{{
			"id":          "EDGE-root-self",
			"type":        "owns",
			"source_id":   "project-root",
			"target_id":   "project-root",
			"confidence":  "verified",
			"evidence_id": "mod-001",
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), map[string]any{
		"observations": []map[string]any{{
			"id":               "OBS-root",
			"observation_type": "summary",
			"summary":          "Root observed",
			"evidence_id":      "mod-001",
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json"), map[string]any{
		"packet_id":      "lane-1",
		"family_id":      "app",
		"assigned_paths": []string{"src/app.go"},
		"paths_read":     []string{"src/app.go"},
		"ledger": map[string]any{
			"todo":     []string{},
			"doing":    []string{},
			"done":     []string{"src/app.go"},
			"blocked":  []string{},
			"overflow": []string{},
		},
		"coverage": []map[string]any{{
			"path":        "src/app.go",
			"outcome":     "read",
			"evidence_id": "mod-001",
		}},
		"confidence": "high",
		"acceptance": "pass",
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
	var count int
	if err := st.DB().QueryRowContext(context.Background(), `SELECT COUNT(*) FROM evidence WHERE id = ?`, "mod-001").Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Fatalf("evidence id mod-001 count = %d, want 1", count)
	}
}

func TestRunAcceptsSourceTargetEdgeAliases(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), map[string]any{
		"edges": []map[string]any{{
			"id":           "EDGE-app-self",
			"type":         "owns",
			"source":       "N-app",
			"target":       "N-app",
			"confidence":   "verified",
			"evidence_ids": []string{"E-001"},
		}},
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
	var count int
	if err := st.DB().QueryRowContext(context.Background(), `SELECT COUNT(*) FROM edges WHERE source_id = ? AND target_id = ?`, "N-app", "N-app").Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Fatalf("edge count = %d, want 1", count)
	}
}

func TestRunResolvesPathEdgeEndpointsToOwningNodes(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), map[string]any{
		"edges": []map[string]any{{
			"id":           "EDGE-app-path",
			"type":         "owns",
			"source":       "src/app.go",
			"target":       "src/app.go",
			"confidence":   "verified",
			"evidence_ids": []string{"E-001"},
		}},
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
	var count int
	if err := st.DB().QueryRowContext(context.Background(), `SELECT COUNT(*) FROM edges WHERE source_id = ? AND target_id = ?`, "N-app", "N-app").Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Fatalf("edge count = %d, want 1", count)
	}
}

func TestRunCompilerFailureDoesNotReportIdentityReconciliationOK(t *testing.T) {
	paths := writeMinimalScanPackage(t)
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), map[string]any{
		"edges": []map[string]any{{
			"id":           "EDGE-bad",
			"type":         "owns",
			"source_id":    "N-app",
			"target_id":    "N-missing",
			"confidence":   "verified",
			"evidence_ids": []string{"E-001"},
		}},
	})

	payload, err := Run(paths)
	if err != nil {
		t.Fatalf("Run() error = %v, want structured compiler block", err)
	}
	if payload.Compilation.PublicationAllowed {
		t.Fatalf("Compilation = %#v, want blocked orphan edge", payload.Compilation)
	}
	if payload.IdentityReconciliation["evidence"].Status != "not_run" {
		t.Fatalf("evidence reconciliation = %#v, want not_run", payload.IdentityReconciliation["evidence"])
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

func TestRunBlocksWhenStatusWriteFailsAfterReadyDBCommit(t *testing.T) {
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
	metadata, metadataErr := st.Metadata(context.Background())
	if metadataErr != nil {
		t.Fatal(metadataErr)
	}
	if metadata["active_generation_id"] != payload.ActiveGenerationID {
		t.Fatalf("metadata active_generation_id = %q, want payload %q", metadata["active_generation_id"], payload.ActiveGenerationID)
	}
	if metadata["graph_ready"] != "true" || metadata["baseline_state"] != "fresh" {
		t.Fatalf("metadata = %#v, want committed ready metadata after status write failure", metadata)
	}
	if metadata["query_contract_version"] != "1" {
		t.Fatalf("query_contract_version = %q, want 1 after status write failure", metadata["query_contract_version"])
	}
	if metadata["update_contract_version"] != "1" {
		t.Fatalf("update_contract_version = %q, want 1 after status write failure", metadata["update_contract_version"])
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
		filepath.Join(paths.RuntimeDir, "workbench", "worker-results"),
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
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), map[string]any{
		"packets": []map[string]any{{
			"packet_id":           "lane-1",
			"state":               "accepted",
			"assigned_paths":      []string{"src/app.go"},
			"result_handoff_path": ".specify/project-cognition/workbench/worker-results/lane-1.json",
		}},
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "handoff-ledger.json"), map[string]any{
		"events": []map[string]any{
			{"event_id": "dispatch-1", "packet_id": "lane-1", "event_type": "dispatched", "created_at": "2026-05-26T00:00:00Z"},
			{"event_id": "return-1", "packet_id": "lane-1", "event_type": "returned", "worker_result_path": ".specify/project-cognition/workbench/worker-results/lane-1.json", "created_at": "2026-05-26T00:01:00Z"},
		},
	})
	if err := os.WriteFile(filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-1.md"), []byte("# Lane 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json"), map[string]any{
		"packet_id":      "lane-1",
		"family_id":      "app",
		"assigned_paths": []string{"src/app.go"},
		"paths_read":     []string{"src/app.go"},
		"ledger": map[string]any{
			"todo":     []string{},
			"doing":    []string{},
			"done":     []string{"src/app.go"},
			"blocked":  []string{},
			"overflow": []string{},
		},
		"coverage": []map[string]any{{
			"path":         "src/app.go",
			"outcome":      "read",
			"evidence_ids": []string{"E-001"},
		}},
		"confidence": "high",
		"acceptance": "pass",
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

func writeAcceptedScanQueue(t *testing.T, paths rt.Paths, assignedPaths []string) {
	t.Helper()
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-queue.json"), map[string]any{
		"packets": []map[string]any{{
			"packet_id":           "lane-1",
			"state":               "accepted",
			"assigned_paths":      assignedPaths,
			"result_handoff_path": ".specify/project-cognition/workbench/worker-results/lane-1.json",
		}},
	})
}

type sparseBuildPath struct {
	Path        string
	Criticality string
	Indexed     bool
}

func writeSparseBuildBoundary(t *testing.T, paths rt.Paths, entries []sparseBuildPath) {
	t.Helper()
	candidates := []map[string]any{}
	dispositions := map[string]string{}
	criticality := map[string]string{}
	reasons := map[string]string{}
	sources := map[string]string{}
	coverage := []map[string]any{}
	ledgerRows := []map[string]any{}
	queuePaths := []string{}
	readPaths := []string{}
	nodes := []map[string]any{}
	evidence := []map[string]any{}
	for i, entry := range entries {
		candidates = append(candidates, map[string]any{
			"path":            entry.Path,
			"disposition":     "deep_read",
			"decision_source": "test",
		})
		dispositions[entry.Path] = "deep_read"
		criticality[entry.Path] = entry.Criticality
		reasons[entry.Path] = "test"
		sources[entry.Path] = "test"
		coverage = append(coverage, map[string]any{"path": entry.Path})
		ledgerRows = append(ledgerRows, map[string]any{"path": entry.Path, "status": "covered"})
		queuePaths = append(queuePaths, entry.Path)
		readPaths = append(readPaths, entry.Path)
		evidenceID := "E-sparse-" + sanitizeIDPart(entry.Path)
		evidence = append(evidence, map[string]any{
			"id":           evidenceID,
			"source_kind":  "source",
			"source_path":  entry.Path,
			"commit_sha":   "abc123",
			"span":         "1:1-10:1",
			"extractor":    "test",
			"content_hash": "hash-sparse-" + sanitizeIDPart(entry.Path),
			"attrs":        map[string]any{"language": "go"},
		})
		if entry.Indexed {
			nodes = append(nodes, map[string]any{
				"id":           "N-sparse-" + sanitizeIDPart(entry.Path),
				"type":         "capability",
				"title":        "Sparse Path",
				"confidence":   "verified",
				"paths":        []string{entry.Path},
				"evidence_ids": []string{evidenceID},
				"attrs":        map[string]any{"index": i},
			})
		}
	}
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), map[string]any{
		"schema_version":         1,
		"candidate_universe":     candidates,
		"included_paths":         queuePaths,
		"excluded_paths":         []string{},
		"ambiguous_paths":        []string{},
		"dispositions":           dispositions,
		"criticality":            criticality,
		"classification_reasons": reasons,
		"decision_source":        sources,
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "coverage.json"), map[string]any{"rows": coverage})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), map[string]any{
		"rows":      ledgerRows,
		"open_gaps": []map[string]any{},
	})
	writeAcceptedScanQueue(t, paths, queuePaths)
	writeJSON(t, filepath.Join(paths.RuntimeDir, "workbench", "worker-results", "lane-1.json"), map[string]any{
		"packet_id":      "lane-1",
		"family_id":      "sparse",
		"assigned_paths": queuePaths,
		"paths_read":     readPaths,
		"ledger": map[string]any{
			"todo":     []string{},
			"doing":    []string{},
			"done":     readPaths,
			"blocked":  []string{},
			"overflow": []string{},
		},
		"coverage":   sparseCoverageRows(entries),
		"confidence": "high",
		"acceptance": "pass",
	})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "evidence", "app.json"), map[string]any{"rows": evidence})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), map[string]any{"nodes": nodes})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), map[string]any{"edges": []map[string]any{}})
	writeJSON(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), map[string]any{"observations": []map[string]any{}})
}

func sparseCoverageRows(entries []sparseBuildPath) []map[string]any {
	rows := []map[string]any{}
	for _, entry := range entries {
		rows = append(rows, map[string]any{
			"path":        entry.Path,
			"outcome":     "read",
			"evidence_id": "E-sparse-" + sanitizeIDPart(entry.Path),
		})
	}
	return rows
}

func containsError(errors []string, want string) bool {
	for _, err := range errors {
		if strings.Contains(err, want) {
			return true
		}
	}
	return false
}

package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestVersionPrintsBinaryName(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"--version"}, &stdout, &stderr, "v1.2.3")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	if strings.TrimSpace(stdout.String()) != "project-cognition v1.2.3" {
		t.Fatalf("stdout = %q", stdout.String())
	}
}

func TestStatusReturnsUnsupportedLegacyJSON(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "status.json"), []byte(`{"freshness":"fresh"}`), 0o644); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"status", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["error_code"] != "unsupported_legacy_runtime" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestBuildFromScanCommandCreatesRuntime(t *testing.T) {
	payload := runBuildFromScanCLI(t, "build-from-scan")

	if payload["status"] != "ok" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
	if _, ok := payload["identity_reconciliation"].(map[string]any); !ok {
		t.Fatalf("identity_reconciliation missing from payload = %#v", payload)
	}
}

func TestValidateScanCommandAcceptsDownstreamCompatibilityShapes(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	pagePath := "desktop/src/pages/ActiveSession.tsx"
	writeTestJSON(t, filepath.Join(runtimeDir, "status.json"), map[string]any{
		"version":     1,
		"graph_ready": false,
	})
	writeTestJSON(t, filepath.Join(runtimeDir, "evidence", "app.json"), map[string]any{
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
	writeTestJSON(t, filepath.Join(runtimeDir, "provisional", "nodes.json"), map[string]any{
		"nodes": []map[string]any{{
			"node_id":     "NO_ID",
			"kind":        "page",
			"label":       "Active Session Page",
			"confidence":  "verified",
			"evidence_id": "E-active-session",
			"attrs_json":  map[string]any{"path": pagePath},
		}},
	})
	writeTestJSON(t, filepath.Join(runtimeDir, "provisional", "edges.json"), map[string]any{
		"edges": []map[string]any{{
			"id":             "NO_ID",
			"kind":           "owns",
			"source_node_id": pagePath,
			"target_node_id": pagePath,
			"confidence":     "verified",
			"evidence_id":    "E-active-session",
		}},
	})
	writeTestJSON(t, filepath.Join(runtimeDir, "provisional", "observations.json"), map[string]any{
		"observations": []any{"Active session page owns session UI state"},
	})
	writeTestJSON(t, filepath.Join(runtimeDir, "coverage.json"), map[string]any{
		"coverage": []map[string]any{{"path": pagePath}},
	})
	writeTestJSON(t, filepath.Join(runtimeDir, "workbench", "coverage-ledger.json"), map[string]any{
		"rows":      []map[string]any{{"path": pagePath, "status": "covered"}},
		"open_gaps": []map[string]any{},
	})
	writeTestJSON(t, filepath.Join(runtimeDir, "workbench", "repository-universe.json"), map[string]any{
		"rows": []map[string]any{{"path": pagePath}},
	})
	writeAcceptedCLIScanQueue(t, runtimeDir, []string{pagePath})
	writeTestJSON(t, filepath.Join(runtimeDir, "workbench", "worker-results", "lane-1.json"), map[string]any{
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

	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"validate-scan", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "ok" || payload["readiness"] != "scan_ready" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestImportScanAliasUsesBuildFromScan(t *testing.T) {
	for _, command := range []string{"import-scan", "rebuild-from-scan"} {
		t.Run(command, func(t *testing.T) {
			payload := runBuildFromScanCLI(t, command)

			if payload["status"] != "ok" {
				t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
			}
		})
	}
}

func TestPublishRuntimeMetadataRefusesSparseInvalidGeneration(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var buildStdout, buildStderr bytes.Buffer
	buildCode := Run([]string{"build-from-scan", "--format", "json"}, &buildStdout, &buildStderr, "test")
	if buildCode != 0 {
		t.Fatalf("build code = %d stderr=%s stdout=%s", buildCode, buildStderr.String(), buildStdout.String())
	}
	var buildPayload map[string]any
	if err := json.Unmarshal(buildStdout.Bytes(), &buildPayload); err != nil {
		t.Fatal(err)
	}
	if buildPayload["status"] != "ok" {
		t.Fatalf("build payload = %#v", buildPayload)
	}

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	generationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `DELETE FROM path_index WHERE generation_id = ?`, generationID); err != nil {
		t.Fatal(err)
	}
	if err := st.MarkRuntimeMetadataBlocked(context.Background(), generationID); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "blocked"
	status.Readiness = rt.BlockedReadiness
	status.ActiveGenerationID = generationID
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"publish-runtime-metadata", "--format", "json"}, &stdout, &stderr, "test")
	if code != 1 {
		t.Fatalf("code = %d, want 1; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "blocked" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
	if !jsonStringSliceContains(payload["errors"], "critical_missing_path_index: src/app.go") {
		t.Fatalf("errors = %#v, want critical_missing_path_index: src/app.go", payload["errors"])
	}

	st, err = store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	meta, err := st.Metadata(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if meta["graph_ready"] != "false" {
		t.Fatalf("metadata graph_ready = %q, want false; metadata = %#v", meta["graph_ready"], meta)
	}
	if _, ok := meta["query_contract_version"]; ok {
		t.Fatalf("query_contract_version metadata present after blocked publish: %#v", meta)
	}
	persistedStatus, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if persistedStatus.Readiness == rt.ReadyReadiness || persistedStatus.GraphReady {
		t.Fatalf("status became ready: %#v", persistedStatus)
	}
}

func TestPublishRuntimeMetadataDoesNotWriteBlockedStatusWhenBlockedMetadataFails(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var buildStdout, buildStderr bytes.Buffer
	buildCode := Run([]string{"build-from-scan", "--format", "json"}, &buildStdout, &buildStderr, "test")
	if buildCode != 0 {
		t.Fatalf("build code = %d stderr=%s stdout=%s", buildCode, buildStderr.String(), buildStdout.String())
	}

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	generationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `DELETE FROM path_index WHERE generation_id = ?`, generationID); err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `CREATE TRIGGER metadata_blocked_insert_failure BEFORE INSERT ON metadata BEGIN SELECT RAISE(FAIL, 'blocked metadata insert failed'); END`); err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `CREATE TRIGGER metadata_blocked_update_failure BEFORE UPDATE ON metadata BEGIN SELECT RAISE(FAIL, 'blocked metadata update failed'); END`); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-sentinel"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"publish-runtime-metadata", "--format", "json"}, &stdout, &stderr, "test")
	if code != 1 {
		t.Fatalf("code = %d, want 1; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "blocked" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
	if !jsonStringSliceHasPrefix(payload["errors"], "write blocked DB metadata:") {
		t.Fatalf("errors = %#v, want blocked metadata write failure", payload["errors"])
	}

	persistedStatus, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if persistedStatus.ActiveGenerationID != "GEN-sentinel" || persistedStatus.Status != "ok" || !persistedStatus.GraphReady {
		t.Fatalf("status.json was overwritten after blocked metadata failure: %#v", persistedStatus)
	}
}

func TestPublishRuntimeMetadataReturnsNonzeroWhenNoActiveGeneration(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var buildStdout, buildStderr bytes.Buffer
	buildCode := Run([]string{"build-from-scan", "--format", "json"}, &buildStdout, &buildStderr, "test")
	if buildCode != 0 {
		t.Fatalf("build code = %d stderr=%s stdout=%s", buildCode, buildStderr.String(), buildStdout.String())
	}

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `UPDATE generations SET state = 'archived' WHERE state = 'active'`); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"publish-runtime-metadata", "--format", "json"}, &stdout, &stderr, "test")
	if code != 1 {
		t.Fatalf("code = %d, want 1; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "error" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
	if !jsonStringSliceContains(payload["errors"], "project-cognition.db has no active generation") {
		t.Fatalf("errors = %#v, want no active generation error", payload["errors"])
	}
}

func TestPublishRuntimeMetadataReturnsNonzeroForUnsupportedLegacyStatus(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var buildStdout, buildStderr bytes.Buffer
	buildCode := Run([]string{"build-from-scan", "--format", "json"}, &buildStdout, &buildStderr, "test")
	if buildCode != 0 {
		t.Fatalf("build code = %d stderr=%s stdout=%s", buildCode, buildStderr.String(), buildStdout.String())
	}

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(paths.StatusPath, []byte(`{"freshness":"fresh"}`), 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"publish-runtime-metadata", "--format", "json"}, &stdout, &stderr, "test")
	if code != 1 {
		t.Fatalf("code = %d, want 1; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["error_code"] != rt.ErrLegacyCode {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["status"] != "blocked" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
}

func TestPublishRuntimeMetadataReturnsNonzeroWhenReadyMetadataWriteFails(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var buildStdout, buildStderr bytes.Buffer
	buildCode := Run([]string{"build-from-scan", "--format", "json"}, &buildStdout, &buildStderr, "test")
	if buildCode != 0 {
		t.Fatalf("build code = %d stderr=%s stdout=%s", buildCode, buildStderr.String(), buildStdout.String())
	}

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `CREATE TRIGGER metadata_ready_update_failure BEFORE UPDATE ON metadata BEGIN SELECT RAISE(FAIL, 'ready metadata update failed'); END`); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"publish-runtime-metadata", "--format", "json"}, &stdout, &stderr, "test")
	if code != 1 {
		t.Fatalf("code = %d, want 1; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "error" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
	if !jsonStringSliceHasPrefix(payload["errors"], "write metadata ") {
		t.Fatalf("errors = %#v, want ready metadata write failure", payload["errors"])
	}
}

func TestPublishRuntimeMetadataReturnsNonzeroWhenBlockedStatusWriteFails(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var buildStdout, buildStderr bytes.Buffer
	buildCode := Run([]string{"build-from-scan", "--format", "json"}, &buildStdout, &buildStderr, "test")
	if buildCode != 0 {
		t.Fatalf("build code = %d stderr=%s stdout=%s", buildCode, buildStderr.String(), buildStdout.String())
	}

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	generationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `DELETE FROM path_index WHERE generation_id = ?`, generationID); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	blockedRuntimeDir := filepath.Join(root, "status-write-blocker")
	if err := os.WriteFile(blockedRuntimeDir, []byte("not a directory"), 0o644); err != nil {
		t.Fatal(err)
	}
	paths.RuntimeDir = blockedRuntimeDir
	paths.StatusPath = filepath.Join(blockedRuntimeDir, "status.json")

	var stdout, stderr bytes.Buffer
	code := publishMetadataCommand([]string{"--format", "json"}, &stdout, &stderr, paths)
	if code != 1 {
		t.Fatalf("code = %d, want 1; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "blocked" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
	if !jsonStringSliceHasPrefix(payload["errors"], "write blocked status:") {
		t.Fatalf("errors = %#v, want blocked status write failure", payload["errors"])
	}
	if payload["recovery_action"] != "rewrite_status_from_db_metadata" {
		t.Fatalf("recovery_action = %#v, payload = %#v", payload["recovery_action"], payload)
	}

	paths.RuntimeDir = filepath.Join(root, ".specify", "project-cognition")
	paths.StatusPath = filepath.Join(paths.RuntimeDir, "status.json")
	st, err = store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	meta, err := st.Metadata(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if meta["graph_ready"] != "false" || meta["baseline_state"] != "blocked" {
		t.Fatalf("metadata = %#v, want committed blocked metadata before blocked status write failure", meta)
	}
	if _, ok := meta["query_contract_version"]; ok {
		t.Fatalf("query_contract_version present after blocked status write failure: %#v", meta)
	}
	if _, ok := meta["update_contract_version"]; ok {
		t.Fatalf("update_contract_version present after blocked status write failure: %#v", meta)
	}
}

func TestPublishRuntimeMetadataReturnsNonzeroWhenReadyStatusWriteFails(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var buildStdout, buildStderr bytes.Buffer
	buildCode := Run([]string{"build-from-scan", "--format", "json"}, &buildStdout, &buildStderr, "test")
	if buildCode != 0 {
		t.Fatalf("build code = %d stderr=%s stdout=%s", buildCode, buildStderr.String(), buildStdout.String())
	}

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `UPDATE metadata SET value_json = 'false' WHERE key = 'graph_ready'`); err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `DELETE FROM metadata WHERE key IN ('query_contract_version', 'update_contract_version')`); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	originalStatusPath := paths.StatusPath
	if err := os.Remove(originalStatusPath); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(originalStatusPath, 0o755); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := publishMetadataCommand([]string{"--format", "json"}, &stdout, &stderr, paths)
	if code != 1 {
		t.Fatalf("code = %d, want 1; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "error" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
	if !jsonStringSliceHasPrefix(payload["errors"], "write ready status:") {
		t.Fatalf("errors = %#v, want ready status write failure", payload["errors"])
	}
	if payload["recovery_action"] != "rewrite_status_from_db_metadata" {
		t.Fatalf("recovery_action = %#v, payload = %#v", payload["recovery_action"], payload)
	}

	st, err = store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	meta, err := st.Metadata(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if meta["graph_ready"] != "true" || meta["baseline_state"] != "fresh" {
		t.Fatalf("metadata = %#v, want committed ready metadata before status write failure", meta)
	}
	if meta["query_contract_version"] != "1" {
		t.Fatalf("query_contract_version = %q, want 1 after failed ready status write", meta["query_contract_version"])
	}
	if meta["update_contract_version"] != "1" {
		t.Fatalf("update_contract_version = %q, want 1 after failed ready status write", meta["update_contract_version"])
	}
}

func TestBuildFromScanCommandReturnsNonzeroForOperationalErrorPayload(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	paths.StatusPath = filepath.Join(root, "missing-parent", "status.json")

	var stdout, stderr bytes.Buffer
	code := buildFromScanCommand([]string{"--format", "json"}, &stdout, &stderr, paths)
	if code != 1 {
		t.Fatalf("code = %d, want 1; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "blocked" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
	if payload["recovery_action"] != "rewrite_status_from_db_metadata" {
		t.Fatalf("recovery_action = %#v, payload = %#v", payload["recovery_action"], payload)
	}
}

func TestDeltaBeginCommandCreatesSession(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["session_id"] == "" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestDeltaBeginCommandCapturesGitMetadata(t *testing.T) {
	root := t.TempDir()
	runGit(t, root, "init")
	runGit(t, root, "checkout", "-b", "main")
	runGit(t, root, "config", "user.email", "test@example.com")
	runGit(t, root, "config", "user.name", "Test User")
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify", ".keep"), []byte("keep\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, root, "add", ".specify/.keep")
	runGit(t, root, "commit", "-m", "initial")
	wantHead := strings.TrimSpace(runGit(t, root, "rev-parse", "HEAD"))

	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	gitPayload, ok := payload["git"].(map[string]any)
	if !ok {
		t.Fatalf("payload = %#v", payload)
	}
	if gitPayload["base_commit"] != wantHead {
		t.Fatalf("base_commit = %#v, want %q", gitPayload["base_commit"], wantHead)
	}
	if gitPayload["branch"] != "main" {
		t.Fatalf("branch = %#v, want main", gitPayload["branch"])
	}
}

func TestDeltaGitMetadataSkipsDirtyPathsOnTimeout(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	calls := []string{}
	runner := func(ctx context.Context, root string, args ...string) (string, error) {
		command := strings.Join(args, " ")
		calls = append(calls, command)
		if len(args) >= 2 && args[0] == "rev-parse" && args[1] == "--is-inside-work-tree" {
			return "true\n", nil
		}
		if len(args) >= 2 && args[0] == "rev-parse" && args[1] == "HEAD" {
			return "abc123\n", nil
		}
		if len(args) >= 2 && args[0] == "branch" && args[1] == "--show-current" {
			return "main\n", nil
		}
		if command == "status --porcelain=v1 -z --untracked-files=all" {
			return "", context.DeadlineExceeded
		}
		return "", errors.New("unexpected git command: " + command)
	}

	metadata := collectDeltaGitMetadata(root, time.Millisecond, runner)

	if metadata.baseCommit != "abc123" {
		t.Fatalf("baseCommit = %q", metadata.baseCommit)
	}
	if metadata.branch != "main" {
		t.Fatalf("branch = %q", metadata.branch)
	}
	if len(metadata.initialDirty) != 0 {
		t.Fatalf("initialDirty = %#v", metadata.initialDirty)
	}
	if !hasCall(calls, "status --porcelain=v1 -z --untracked-files=all") {
		t.Fatalf("calls = %#v", calls)
	}
}

func TestDeltaGitMetadataCapturesDirtyPathsWithoutRootGitDirectory(t *testing.T) {
	root := t.TempDir()
	calls := []string{}
	runner := func(ctx context.Context, root string, args ...string) (string, error) {
		command := strings.Join(args, " ")
		calls = append(calls, command)
		switch command {
		case "rev-parse --is-inside-work-tree":
			return "true\n", nil
		case "rev-parse HEAD":
			return "abc123\n", nil
		case "branch --show-current":
			return "main\n", nil
		case "status --porcelain=v1 -z --untracked-files=all":
			return " M src/a.go\x00", nil
		default:
			return "", errors.New("unexpected git command: " + command)
		}
	}

	metadata := collectDeltaGitMetadata(root, time.Millisecond, runner)

	if !hasCall(calls, "status --porcelain=v1 -z --untracked-files=all") {
		t.Fatalf("calls = %#v", calls)
	}
	if got := metadata.initialDirty; len(got) != 1 || got[0] != "src/a.go" {
		t.Fatalf("initialDirty = %#v, want src/a.go", got)
	}
}

func TestDeltaGitMetadataParsesRawZStatusNonASCIIPath(t *testing.T) {
	root := t.TempDir()
	calls := []string{}
	runner := func(ctx context.Context, root string, args ...string) (string, error) {
		command := strings.Join(args, " ")
		calls = append(calls, command)
		switch command {
		case "rev-parse --is-inside-work-tree":
			return "true\n", nil
		case "rev-parse HEAD":
			return "abc123\n", nil
		case "branch --show-current":
			return "main\n", nil
		case "status --porcelain=v1 -z --untracked-files=all":
			return "?? café.go\x00", nil
		default:
			return "", errors.New("unexpected git command: " + command)
		}
	}

	metadata := collectDeltaGitMetadata(root, time.Millisecond, runner)

	if !hasCall(calls, "status --porcelain=v1 -z --untracked-files=all") {
		t.Fatalf("calls = %#v", calls)
	}
	if got := metadata.initialDirty; len(got) != 1 || got[0] != "café.go" {
		t.Fatalf("initialDirty = %#v, want café.go", got)
	}
}

func TestParseDeltaGitStatusZKeepsRenameTargetPath(t *testing.T) {
	paths := parseDeltaGitStatusZ("R  new.txt\x00old.txt\x00")

	if got := paths; len(got) != 1 || got[0] != "new.txt" {
		t.Fatalf("paths = %#v, want new.txt", got)
	}
	if hasString(paths, "old.txt") {
		t.Fatalf("paths = %#v, did not want old.txt", paths)
	}
}

func TestDeltaAppendCommandWritesEvent(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--event-type", "worker_result",
		"--changed-path", "src/a.go",
		"--verification", "go test ./... PASS",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["event_id"] == "" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestDeltaAppendCommandAcceptsPacketFile(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	packet := filepath.Join(root, "packet.json")
	data := []byte(`{"event_type":"worker_result","changed_paths":["src/a.go"],"verification_evidence":["go test ./... PASS"]}`)
	if err := os.WriteFile(packet, data, 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--packet-file", packet,
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["event_type"] != "worker_result" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestUpdateCommandAcceptsDeltaSession(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var appendStdout, appendStderr bytes.Buffer
	appendCode := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--event-type", "worker_result",
		"--changed-path", "src/a.go",
		"--format", "json",
	}, &appendStdout, &appendStderr, "test")
	if appendCode != 0 {
		t.Fatalf("append code = %d stderr=%s", appendCode, appendStderr.String())
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"update",
		"--delta-session", sessionID,
		"--reason", "workflow-finalize",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["update_outcome"] != "boundary_resolved" {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["readiness"] == "query_ready" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestUpdateCommandTreatsQuotedInitialDirtyUnicodePathAsAmbiguous(t *testing.T) {
	root := t.TempDir()
	runGit(t, root, "init")
	runGit(t, root, "checkout", "-b", "main")
	runGit(t, root, "config", "user.email", "test@example.com")
	runGit(t, root, "config", "user.name", "Test User")
	runGit(t, root, "config", "core.quotePath", "true")
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify", ".keep"), []byte("keep\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, root, "add", ".specify/.keep")
	runGit(t, root, "commit", "-m", "initial")
	if err := os.WriteFile(filepath.Join(root, "café.go"), []byte("package demo\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var appendStdout, appendStderr bytes.Buffer
	appendCode := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--event-type", "worker_result",
		"--changed-path", "café.go",
		"--format", "json",
	}, &appendStdout, &appendStderr, "test")
	if appendCode != 0 {
		t.Fatalf("append code = %d stderr=%s", appendCode, appendStderr.String())
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"update",
		"--delta-session", sessionID,
		"--reason", "workflow-finalize",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	boundary, ok := payload["boundary"].(map[string]any)
	if !ok {
		t.Fatalf("payload = %#v", payload)
	}
	if !jsonStringSliceContains(boundary["ambiguous_paths"], "café.go") {
		t.Fatalf("boundary ambiguous_paths = %#v, want café.go", boundary["ambiguous_paths"])
	}
	if jsonStringSliceContains(boundary["workflow_owned_paths"], "café.go") {
		t.Fatalf("boundary workflow_owned_paths = %#v, did not want café.go", boundary["workflow_owned_paths"])
	}
}

func TestUpdateCommandTreatsStagedRenameTargetAsAmbiguous(t *testing.T) {
	root := t.TempDir()
	runGit(t, root, "init")
	runGit(t, root, "checkout", "-b", "main")
	runGit(t, root, "config", "user.email", "test@example.com")
	runGit(t, root, "config", "user.name", "Test User")
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".specify", ".keep"), []byte("keep\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "old.txt"), []byte("old\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, root, "add", ".specify/.keep", "old.txt")
	runGit(t, root, "commit", "-m", "initial")
	runGit(t, root, "mv", "old.txt", "new.txt")

	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var appendStdout, appendStderr bytes.Buffer
	appendCode := Run([]string{
		"delta", "append",
		"--session", sessionID,
		"--event-type", "worker_result",
		"--changed-path", "new.txt",
		"--format", "json",
	}, &appendStdout, &appendStderr, "test")
	if appendCode != 0 {
		t.Fatalf("append code = %d stderr=%s", appendCode, appendStderr.String())
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"update",
		"--delta-session", sessionID,
		"--reason", "workflow-finalize",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	boundary, ok := payload["boundary"].(map[string]any)
	if !ok {
		t.Fatalf("payload = %#v", payload)
	}
	if !jsonStringSliceContains(boundary["ambiguous_paths"], "new.txt") {
		t.Fatalf("boundary ambiguous_paths = %#v, want new.txt", boundary["ambiguous_paths"])
	}
	if jsonStringSliceContains(boundary["workflow_owned_paths"], "new.txt") {
		t.Fatalf("boundary workflow_owned_paths = %#v, did not want new.txt", boundary["workflow_owned_paths"])
	}
}

func TestUpdateCommandRejectsBadDeltaCommitRange(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	sessionID := beginDeltaSession(t)
	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"update",
		"--delta-session", sessionID,
		"--commit-range", "bad-range",
		"--reason", "workflow-finalize",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code == 0 {
		t.Fatalf("code = %d stdout=%s stderr=%s, want non-zero", code, stdout.String(), stderr.String())
	}
}

func beginDeltaSession(t *testing.T) string {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("begin code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	sessionID, ok := payload["session_id"].(string)
	if !ok || sessionID == "" {
		t.Fatalf("payload = %#v", payload)
	}
	return sessionID
}

func runBuildFromScanCLI(t *testing.T, command string) map[string]any {
	t.Helper()
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{command, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("%s code = %d stderr=%s", command, code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	return payload
}

func writeMinimalCLIScanPackage(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	for _, dir := range []string{
		filepath.Join(runtimeDir, "evidence"),
		filepath.Join(runtimeDir, "provisional"),
		filepath.Join(runtimeDir, "workbench", "scan-packets"),
		filepath.Join(runtimeDir, "workbench", "worker-results"),
	} {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	writeTestJSON(t, filepath.Join(runtimeDir, "evidence", "app.json"), map[string]any{
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
	writeTestJSON(t, filepath.Join(runtimeDir, "provisional", "nodes.json"), map[string]any{
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
	writeTestJSON(t, filepath.Join(runtimeDir, "provisional", "edges.json"), map[string]any{
		"edges": []map[string]any{{
			"id":           "EDGE-app-self",
			"type":         "owns",
			"source_id":    "N-app",
			"target_id":    "N-app",
			"confidence":   "verified",
			"evidence_ids": []string{"E-001"},
		}},
	})
	writeTestJSON(t, filepath.Join(runtimeDir, "provisional", "observations.json"), map[string]any{
		"observations": []map[string]any{{
			"id":               "OBS-app",
			"observation_type": "summary",
			"summary":          "App observed",
			"evidence_ids":     []string{"E-001"},
		}},
	})
	writeTestJSON(t, filepath.Join(runtimeDir, "coverage.json"), map[string]any{
		"rows": []map[string]any{{"path": "src/app.go"}},
	})
	writeTestJSON(t, filepath.Join(runtimeDir, "workbench", "coverage-ledger.json"), map[string]any{
		"rows":      []map[string]any{{"path": "src/app.go", "status": "covered"}},
		"open_gaps": []map[string]any{},
	})
	writeTestJSON(t, filepath.Join(runtimeDir, "workbench", "repository-universe.json"), map[string]any{
		"schema_version":     1,
		"candidate_universe": []map[string]any{{"path": "src/app.go", "source": "test"}},
		"included_paths":     []string{"src/app.go"},
		"excluded_paths":     []string{},
		"ambiguous_paths":    []string{},
		"dispositions":       map[string]any{"src/app.go": "deep_read"},
		"criticality":        map[string]any{"src/app.go": "critical"},
		"classification_reasons": map[string]any{
			"src/app.go": "test",
		},
		"decision_source": map[string]any{"src/app.go": "test"},
	})
	writeAcceptedCLIScanQueue(t, runtimeDir, []string{"src/app.go"})
	writeTestJSON(t, filepath.Join(runtimeDir, "workbench", "handoff-ledger.json"), map[string]any{
		"events": []map[string]any{
			{"event_id": "dispatch-1", "packet_id": "lane-1", "event_type": "dispatched", "created_at": "2026-05-26T00:00:00Z"},
			{"event_id": "return-1", "packet_id": "lane-1", "event_type": "returned", "worker_result_path": ".specify/project-cognition/workbench/worker-results/lane-1.json", "created_at": "2026-05-26T00:01:00Z"},
		},
	})
	if err := os.WriteFile(filepath.Join(runtimeDir, "workbench", "scan-packets", "lane-1.md"), []byte("# Lane 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeTestJSON(t, filepath.Join(runtimeDir, "workbench", "worker-results", "lane-1.json"), map[string]any{
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
		if err := os.WriteFile(filepath.Join(runtimeDir, rel), []byte("# Test\n"), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

func writeAcceptedCLIScanQueue(t *testing.T, runtimeDir string, assignedPaths []string) {
	t.Helper()
	writeTestJSON(t, filepath.Join(runtimeDir, "workbench", "scan-queue.json"), map[string]any{
		"packets": []map[string]any{{
			"packet_id":           "lane-1",
			"state":               "accepted",
			"assigned_paths":      assignedPaths,
			"result_handoff_path": ".specify/project-cognition/workbench/worker-results/lane-1.json",
		}},
	})
}

func writeTestJSON(t *testing.T, path string, payload any) {
	t.Helper()
	data, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, append(data, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
}

func runGit(t *testing.T, dir string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	data, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %s failed: %v\n%s", strings.Join(args, " "), err, data)
	}
	return string(data)
}

func hasCall(calls []string, want string) bool {
	for _, call := range calls {
		if call == want {
			return true
		}
	}
	return false
}

func hasString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func jsonStringSliceContains(value any, want string) bool {
	values, ok := value.([]any)
	if !ok {
		return false
	}
	for _, value := range values {
		if text, ok := value.(string); ok && text == want {
			return true
		}
	}
	return false
}

func jsonStringSliceHasPrefix(value any, prefix string) bool {
	values, ok := value.([]any)
	if !ok {
		return false
	}
	for _, value := range values {
		if text, ok := value.(string); ok && strings.HasPrefix(text, prefix) {
			return true
		}
	}
	return false
}

package cli

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtimegate"
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

func TestInitEmptyCommandCreatesGreenfieldRuntime(t *testing.T) {
	root := t.TempDir()
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"init-empty", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "ok" {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("baseline_kind = %#v, payload = %#v", payload["baseline_kind"], payload)
	}
	if payload["readiness"] != rt.ReadyReadiness {
		t.Fatalf("readiness = %#v, payload = %#v", payload["readiness"], payload)
	}

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(paths.StatusPath); err != nil {
		t.Fatalf("status.json missing: %v", err)
	}
	if _, err := os.Stat(paths.DatabasePath); err != nil {
		t.Fatalf("project-cognition.db missing: %v", err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.BaselineKind != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("status baseline kind = %q", status.BaselineKind)
	}
}

func TestPublishRuntimeMetadataPreservesGreenfieldBaseline(t *testing.T) {
	root := t.TempDir()
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var initStdout, initStderr bytes.Buffer
	initCode := Run([]string{"init-empty", "--format", "json"}, &initStdout, &initStderr, "test")
	if initCode != 0 {
		t.Fatalf("init code = %d stderr=%s stdout=%s", initCode, initStderr.String(), initStdout.String())
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"publish-runtime-metadata", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "ok" {
		t.Fatalf("payload = %#v", payload)
	}
	metadata, ok := payload["metadata"].(map[string]any)
	if !ok {
		t.Fatalf("metadata = %#v", payload["metadata"])
	}
	if metadata["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("metadata baseline_kind = %#v, payload = %#v", metadata["baseline_kind"], payload)
	}

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.BaselineKind != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("status baseline kind = %q", status.BaselineKind)
	}
	agreement := runtimegate.Check(paths)
	if agreement.Status != "ok" {
		t.Fatalf("agreement = %#v", agreement)
	}
}

func TestInitEmptyCommandDoesNotOverwriteExistingRuntime(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	before, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"init-empty", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["already_initialized"] != true {
		t.Fatalf("already_initialized = %#v, payload = %#v", payload["already_initialized"], payload)
	}
	after, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if after.ActiveGenerationID != before.ActiveGenerationID {
		t.Fatalf("active generation changed: before=%s after=%s", before.ActiveGenerationID, after.ActiveGenerationID)
	}
}

func TestInitEmptyPathsRemapsFilesystemRootCapture(t *testing.T) {
	root := t.TempDir()
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	filesystemRoot := filepath.VolumeName(root) + string(os.PathSeparator)
	got := initEmptyPaths(rt.Paths{
		Root:         filesystemRoot,
		RuntimeDir:   filepath.Join(filesystemRoot, rt.SpecifyDir, rt.CognitionDir),
		StatusPath:   filepath.Join(filesystemRoot, rt.SpecifyDir, rt.CognitionDir, rt.StatusFileName),
		DatabasePath: filepath.Join(filesystemRoot, rt.SpecifyDir, rt.CognitionDir, rt.DBFileName),
	})

	if got.Root != root {
		t.Fatalf("Root = %q, want %q", got.Root, root)
	}
	wantRuntimeDir := filepath.Join(root, rt.SpecifyDir, rt.CognitionDir)
	if got.RuntimeDir != wantRuntimeDir {
		t.Fatalf("RuntimeDir = %q, want %q", got.RuntimeDir, wantRuntimeDir)
	}
}

func TestInitEmptyPathsRemapsHomeCapture(t *testing.T) {
	home, err := os.UserHomeDir()
	if err != nil {
		t.Skipf("user home unavailable: %v", err)
	}
	home, err = filepath.Abs(home)
	if err != nil {
		t.Skipf("user home absolute path unavailable: %v", err)
	}
	root := t.TempDir()
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	got := initEmptyPaths(rt.Paths{
		Root:         home,
		RuntimeDir:   filepath.Join(home, rt.SpecifyDir, rt.CognitionDir),
		StatusPath:   filepath.Join(home, rt.SpecifyDir, rt.CognitionDir, rt.StatusFileName),
		DatabasePath: filepath.Join(home, rt.SpecifyDir, rt.CognitionDir, rt.DBFileName),
	})

	if got.Root != root {
		t.Fatalf("Root = %q, want %q", got.Root, root)
	}
	wantRuntimeDir := filepath.Join(root, rt.SpecifyDir, rt.CognitionDir)
	if got.RuntimeDir != wantRuntimeDir {
		t.Fatalf("RuntimeDir = %q, want %q", got.RuntimeDir, wantRuntimeDir)
	}
}

func TestInitEmptyCommandDeclinesNonScaffoldProject(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "main.go"), []byte("package main\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"init-empty", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "declined" {
		t.Fatalf("payload = %#v", payload)
	}
	if _, err := os.Stat(filepath.Join(root, rt.SpecifyDir, rt.CognitionDir, rt.StatusFileName)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("status.json exists or stat failed unexpectedly: %v", err)
	}
	if _, err := os.Stat(filepath.Join(root, rt.SpecifyDir, rt.CognitionDir, rt.DBFileName)); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("project-cognition.db exists or stat failed unexpectedly: %v", err)
	}
}

func TestInitEmptyCommandBlocksPartialExistingRuntime(t *testing.T) {
	root := t.TempDir()
	paths := cliRuntimePaths(root)
	status := rt.DefaultStatus(paths)
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"init-empty", "--format", "json"}, &stdout, &stderr, "test")
	if code == 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "blocked" || payload["already_initialized"] != false {
		t.Fatalf("payload = %#v", payload)
	}
	if _, err := os.Stat(paths.DatabasePath); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("project-cognition.db exists or stat failed unexpectedly: %v", err)
	}
	after, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if after.BaselineKind == rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("partial runtime was converted to greenfield baseline: %#v", after)
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

func TestBuildFromScanCommandWritesAliasIndexRows(t *testing.T) {
	payload := runBuildFromScanCLI(t, "build-from-scan")

	if payload["status"] != "ok" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
	paths, err := rt.ResolvePaths(".")
	if err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	var aliasCount int
	if err := db.QueryRowContext(context.Background(), `SELECT COUNT(*) FROM alias_index WHERE target_type = 'node'`).Scan(&aliasCount); err != nil {
		t.Fatal(err)
	}
	if aliasCount == 0 {
		t.Fatal("alias_index node row count = 0, want > 0")
	}

	var rawSummaryAliases int
	if err := db.QueryRowContext(context.Background(), `SELECT COUNT(*) FROM alias_index WHERE alias LIKE '%owns frame rendering and input dispatch%'`).Scan(&rawSummaryAliases); err != nil {
		t.Fatal(err)
	}
	if rawSummaryAliases != 0 {
		t.Fatalf("raw summary alias count = %d, want 0", rawSummaryAliases)
	}
}

func TestBuildFromScanArchivesV1DatabaseBeforeCreatingV2(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(context.Background(), `CREATE TABLE legacy_marker(id TEXT PRIMARY KEY)`); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(context.Background(), `INSERT INTO metadata(key, value_json, updated_at) VALUES('schema_version', '1', CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value_json='1', updated_at=CURRENT_TIMESTAMP`); err != nil {
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"build-from-scan", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["legacy_runtime_replaced"] != true {
		t.Fatalf("legacy_runtime_replaced = %#v, payload = %#v", payload["legacy_runtime_replaced"], payload)
	}

	reopened, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	if hasTable(t, reopened, "legacy_marker") {
		t.Fatal("legacy_marker table survived outdated database replacement")
	}
	var version string
	if err := reopened.QueryRowContext(context.Background(), `SELECT value_json FROM metadata WHERE key = 'schema_version'`).Scan(&version); err != nil {
		t.Fatal(err)
	}
	if version != "2" {
		t.Fatalf("schema_version = %q, want 2", version)
	}
	if _, err := os.Stat(paths.DatabasePath + ".legacy"); err != nil {
		t.Fatalf("legacy archive missing: %v", err)
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

func TestLexiconCommandEmitsGraphBackedContractFields(t *testing.T) {
	setupReadyMinimalCLIRuntime(t)

	var stdout, stderr bytes.Buffer
	code := Run([]string{"lexicon", "--intent", "implement", "--query", "App GUI", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	generationID, ok := payload["active_generation_id"].(string)
	if !ok || generationID == "" {
		t.Fatalf("active_generation_id missing from payload = %#v", payload)
	}
	if payload["candidate_universe_version"] != float64(1) {
		t.Fatalf("candidate_universe_version = %#v, want 1; payload = %#v", payload["candidate_universe_version"], payload)
	}
	if _, ok := payload["candidate_universe"].(map[string]any); !ok {
		t.Fatalf("candidate_universe missing from payload = %#v", payload)
	}
	contract, ok := payload["query_planning_contract"].(map[string]any)
	if !ok {
		t.Fatalf("query_planning_contract missing from payload = %#v", payload)
	}
	if !jsonStringSliceContains(contract["accepted_fields"], "concept_decisions") {
		t.Fatalf("accepted_fields = %#v, want concept_decisions", contract["accepted_fields"])
	}
	if !jsonStringSliceContains(contract["accepted_fields"], "lexicon_generation_id") {
		t.Fatalf("accepted_fields = %#v, want lexicon_generation_id", contract["accepted_fields"])
	}
	candidates, ok := payload["concept_candidates"].([]any)
	if !ok || len(candidates) == 0 {
		t.Fatalf("concept_candidates = %#v, want at least one candidate", payload["concept_candidates"])
	}
	first, ok := candidates[0].(map[string]any)
	if !ok {
		t.Fatalf("first concept candidate = %#v, want object", candidates[0])
	}
	conceptID, ok := first["concept_id"].(string)
	if !ok || !strings.HasPrefix(conceptID, "concept:") || strings.HasPrefix(conceptID, "term:") {
		t.Fatalf("first concept_id = %#v, want concept-backed id", first["concept_id"])
	}
}

func TestLexiconCommandCatalogModeEmitsAliasCatalogAndSemanticContract(t *testing.T) {
	setupReadyMinimalCLIRuntime(t)

	var stdout, stderr bytes.Buffer
	code := Run([]string{"lexicon", "--intent", "debug", "--query", "App GUI", "--mode", "catalog", "--limit", "1", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	catalog, ok := payload["alias_catalog"].([]any)
	if !ok || len(catalog) == 0 {
		t.Fatalf("alias_catalog = %#v, want non-empty catalog", payload["alias_catalog"])
	}
	if payload["alias_catalog_count"].(float64) < float64(len(catalog)) {
		t.Fatalf("alias_catalog_count = %#v, catalog len = %d", payload["alias_catalog_count"], len(catalog))
	}
	if payload["alias_catalog_limit"].(float64) != 1 {
		t.Fatalf("alias_catalog_limit = %#v, want 1", payload["alias_catalog_limit"])
	}
	first, ok := catalog[0].(map[string]any)
	if !ok {
		t.Fatalf("alias catalog item = %#v, want object", catalog[0])
	}
	aliases, ok := first["aliases"].([]any)
	if !ok {
		t.Fatalf("aliases = %#v", first["aliases"])
	}
	if !jsonAnySliceContains(aliases, "App") {
		t.Fatalf("aliases = %#v, want App from alias_index", aliases)
	}
	if jsonAnySliceContains(aliases, "App observed") {
		t.Fatalf("aliases = %#v, do not want raw observation summary alias", aliases)
	}
	if jsonAnySliceContains(aliases, "App owns frame rendering and input dispatch.") {
		t.Fatalf("aliases = %#v, do not want observation summary alias", aliases)
	}
	for _, key := range []string{"concept_id", "title", "aliases", "owner", "domain", "node_type", "confidence", "path_hints", "route_hints", "verification_hints", "evidence_summary_tags"} {
		if _, ok := first[key]; !ok {
			t.Fatalf("alias catalog item missing %s: %#v", key, first)
		}
	}
	contract, ok := payload["query_planning_contract"].(map[string]any)
	if !ok {
		t.Fatalf("query_planning_contract missing from payload = %#v", payload)
	}
	if !jsonStringSliceContains(contract["accepted_fields"], "semantic_intake") {
		t.Fatalf("accepted_fields = %#v, want semantic_intake", contract["accepted_fields"])
	}
	if !jsonStringSliceContains(contract["accepted_fields"], "intent_facets") {
		t.Fatalf("accepted_fields = %#v, want intent_facets", contract["accepted_fields"])
	}
	if !jsonStringSliceContains(contract["concept_decision_fields"], "covered_facets") {
		t.Fatalf("concept_decision_fields = %#v, want covered_facets", contract["concept_decision_fields"])
	}
}

func TestLexiconBlocksV1DatabaseWithRebuildGuidance(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(context.Background(), `INSERT INTO metadata(key, value_json, updated_at) VALUES('schema_version', '1', CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value_json = '1', updated_at = CURRENT_TIMESTAMP`); err != nil {
		_ = db.Close()
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"lexicon", "--intent", "debug", "--mode", "catalog", "--format", "json"}, &stdout, &stderr, "test")

	if code == 0 {
		t.Fatalf("code = %d, want non-zero; stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
	output := stdout.String() + stderr.String()
	if !strings.Contains(output, "run_map_scan_build") && !strings.Contains(output, "schema_version") {
		t.Fatalf("output = %s, want rebuild or schema version guidance", output)
	}
}

func TestLexiconCommandHandlesGreenfieldEmptyBaseline(t *testing.T) {
	initEmptyCLIRuntime(t)

	var stdout, stderr bytes.Buffer
	code := Run([]string{"lexicon", "--intent", "plan", "--query", "build login", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["readiness"] != rt.ReadyReadiness {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["recommended_next_action"] != "use_project_cognition" {
		t.Fatalf("payload = %#v", payload)
	}
	if !jsonStringSliceContains(payload["missing_coverage"], "greenfield_empty_no_project_code") {
		t.Fatalf("missing_coverage = %#v", payload["missing_coverage"])
	}
	candidates, ok := payload["concept_candidates"].([]any)
	if !ok || len(candidates) != 0 {
		t.Fatalf("concept_candidates = %#v, want empty", payload["concept_candidates"])
	}
}

func TestRootHelpListsCompassAndExpand(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"--help"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	output := stdout.String()
	for _, command := range []string{"compass", "expand"} {
		if !strings.Contains(output, command) {
			t.Fatalf("root help = %q, want %s", output, command)
		}
	}
}

func TestCompassHelpListsPrecisionFlags(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"compass", "--help"}, &stdout, &stderr, "test")
	if code != 2 {
		t.Fatalf("code = %d, want 2 for flag help; stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	output := stdout.String() + stderr.String()
	for _, flagName := range []string{"-query", "-semantic-intake-file", "-query-plan-file"} {
		if !strings.Contains(output, flagName) {
			t.Fatalf("compass help = %q, want %s", output, flagName)
		}
	}
}

func TestExpandHelpListsSectionFlag(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"expand", "--help"}, &stdout, &stderr, "test")
	if code != 2 {
		t.Fatalf("code = %d, want 2 for flag help; stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	output := stdout.String() + stderr.String()
	if !strings.Contains(output, "-section") {
		t.Fatalf("expand help = %q, want -section", output)
	}
}

func TestCompassCommandEmitsCompactPacket(t *testing.T) {
	setupReadyMinimalCLIRuntime(t)

	var stdout, stderr bytes.Buffer
	code := Run([]string{"compass", "--intent", "debug", "--query", "App GUI", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["mode"] != "compass" {
		t.Fatalf("mode = %#v, payload = %#v", payload["mode"], payload)
	}
	if _, ok := payload["minimal_live_reads"].([]any); !ok {
		t.Fatalf("minimal_live_reads = %#v, want array", payload["minimal_live_reads"])
	}
	lanes, ok := payload["evidence_lanes"].([]any)
	if !ok {
		t.Fatalf("evidence_lanes = %#v, want array", payload["evidence_lanes"])
	}
	if len(lanes) > 0 {
		if _, ok := payload["expansion_ref"].(map[string]any); !ok {
			t.Fatalf("expansion_ref missing for lanes; payload = %#v", payload)
		}
	}
}

func TestCompassV1DatabaseReturnsBlockedPacketWithRebuildGuidance(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(context.Background(), `INSERT INTO metadata(key, value_json, updated_at) VALUES('schema_version', '1', CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value_json = '1', updated_at = CURRENT_TIMESTAMP`); err != nil {
		_ = db.Close()
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"compass", "--intent", "debug", "--query", "会话界面切模型失败 Failed to switch provider/model CLI exited during startup code 143 DeepSeek 方块 屏幕很小", "--format", "json"}, &stdout, &stderr, "test")

	if code != 0 {
		t.Fatalf("code = %d, want 0; stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["mode"] != "compass" {
		t.Fatalf("mode = %#v, payload = %#v", payload["mode"], payload)
	}
	if payload["compass_state"] != "blocked" {
		t.Fatalf("compass_state = %#v, payload = %#v", payload["compass_state"], payload)
	}
	if payload["readiness"] != rt.NeedsRebuildReadiness {
		t.Fatalf("readiness = %#v, payload = %#v", payload["readiness"], payload)
	}
	for _, key := range []string{"minimal_live_reads", "evidence_lanes", "coverage_diagnostics", "errors"} {
		values, ok := payload[key].([]any)
		if !ok || len(values) != 0 {
			t.Fatalf("%s = %#v, want empty array; payload = %#v", key, payload[key], payload)
		}
	}
	if payload["recommended_next_action"] != "run_map_scan_build" {
		t.Fatalf("recommended_next_action = %#v, payload = %#v", payload["recommended_next_action"], payload)
	}
	if payload["recovery_action"] != "run_map_scan_build" {
		t.Fatalf("recovery_action = %#v, payload = %#v", payload["recovery_action"], payload)
	}
}

func TestExpandCommandReturnsStoredSection(t *testing.T) {
	setupReadyMinimalCLIRuntime(t)

	var compassStdout, compassStderr bytes.Buffer
	compassCode := Run([]string{"compass", "--intent", "debug", "--query", "App GUI", "--format", "json"}, &compassStdout, &compassStderr, "test")
	if compassCode != 0 {
		t.Fatalf("compass code = %d stderr=%s stdout=%s", compassCode, compassStderr.String(), compassStdout.String())
	}
	var compassPayload map[string]any
	if err := json.Unmarshal(compassStdout.Bytes(), &compassPayload); err != nil {
		t.Fatal(err)
	}
	expansionRef, ok := compassPayload["expansion_ref"].(map[string]any)
	if !ok {
		t.Fatalf("expansion_ref missing from compass payload = %#v", compassPayload)
	}
	expansionID, ok := expansionRef["id"].(string)
	if !ok || expansionID == "" {
		t.Fatalf("expansion_ref.id = %#v", expansionRef["id"])
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"expand", "--id", expansionID, "--section", "related_paths", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "ok" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}
	if payload["section"] != "related_paths" {
		t.Fatalf("section = %#v, payload = %#v", payload["section"], payload)
	}
}

func TestCompassCommandAcceptsSemanticIntakeFileShapes(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	cases := []struct {
		name    string
		payload string
	}{
		{
			name: "direct",
			payload: `{
				"workflow_intent": "debug",
				"normalized_query": "App GUI",
				"intent_facets": ["App GUI"],
				"alias_interpretations": [{"alias": "App", "meaning": "application UI"}]
			}`,
		},
		{
			name: "wrapper",
			payload: `{
				"semantic_intake": {
					"workflow_intent": "debug",
					"normalized_query": "App GUI",
					"intent_facets": ["App GUI"],
					"alias_interpretations": [{"alias": "GUI", "meaning": "graphical interface"}]
				}
			}`,
		},
	}
	for _, tt := range cases {
		t.Run(tt.name, func(t *testing.T) {
			path := filepath.Join(root, tt.name+"-semantic-intake.json")
			if err := os.WriteFile(path, []byte(tt.payload), 0o644); err != nil {
				t.Fatal(err)
			}
			var stdout, stderr bytes.Buffer
			code := Run([]string{"compass", "--semantic-intake-file", path, "--format", "json"}, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
			}
			var payload map[string]any
			if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
				t.Fatal(err)
			}
			if payload["mode"] != "compass" {
				t.Fatalf("mode = %#v, payload = %#v", payload["mode"], payload)
			}
			if payload["facet_source"] != "semantic_intake.intent_facets" {
				t.Fatalf("facet_source = %#v, payload = %#v", payload["facet_source"], payload)
			}
		})
	}
}

func TestCompassCommandRejectsWrappedSemanticIntakeNonObject(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	cases := []struct {
		name    string
		payload string
	}{
		{name: "null", payload: `{"semantic_intake": null}`},
		{name: "array", payload: `{"semantic_intake": []}`},
		{name: "string", payload: `{"semantic_intake": "App GUI"}`},
		{name: "number", payload: `{"semantic_intake": 42}`},
		{name: "boolean", payload: `{"semantic_intake": true}`},
	}
	for _, tt := range cases {
		t.Run(tt.name, func(t *testing.T) {
			path := filepath.Join(root, tt.name+"-bad-semantic-intake.json")
			if err := os.WriteFile(path, []byte(tt.payload), 0o644); err != nil {
				t.Fatal(err)
			}
			var stdout, stderr bytes.Buffer
			code := Run([]string{"compass", "--semantic-intake-file", path, "--format", "json"}, &stdout, &stderr, "test")
			if code == 0 {
				t.Fatalf("code = 0, want non-zero for %s; stdout=%s", tt.name, stdout.String())
			}
			if !strings.Contains(stderr.String(), "semantic_intake has unsupported shape: expected object") {
				t.Fatalf("stderr = %q, want semantic_intake object shape error", stderr.String())
			}
		})
	}
}

func TestQueryCommandAcceptsConceptDecisionPlan(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	conceptID := "concept:" + status.ActiveGenerationID + ":N-app"
	queryPlan := marshalQueryPlan(t, map[string]any{
		"lexicon_generation_id": status.ActiveGenerationID,
		"selected_concepts":     []string{conceptID},
		"concept_decisions": []map[string]any{{
			"concept_id":       conceptID,
			"decision":         "selected",
			"selection_reason": "App owns the requested implementation surface.",
			"confidence":       "high",
			"paths":            []string{"src/app.go"},
		}},
	})

	var stdout, stderr bytes.Buffer
	code := Run([]string{"query", "--intent", "implement", "--query-plan", queryPlan, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["readiness"] != "query_ready" {
		t.Fatalf("readiness = %#v, payload = %#v", payload["readiness"], payload)
	}
	if !jsonStringSliceContains(payload["minimal_live_reads"], "src/app.go") {
		t.Fatalf("minimal_live_reads = %#v, want src/app.go", payload["minimal_live_reads"])
	}
	if !jsonStringSliceContains(payload["selected_concepts"], conceptID) {
		t.Fatalf("selected_concepts = %#v, want %s", payload["selected_concepts"], conceptID)
	}
	queryPlanPayload, ok := payload["query_plan"].(map[string]any)
	if !ok {
		t.Fatalf("query_plan missing from payload = %#v", payload)
	}
	if decisions, ok := queryPlanPayload["concept_decisions"].([]any); !ok || len(decisions) == 0 {
		t.Fatalf("query_plan.concept_decisions = %#v, want non-empty decisions", queryPlanPayload["concept_decisions"])
	}
}

func TestQueryCommandEmitsDiagnosticsForCoercedAliasInterpretationsAcrossPlanInputs(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	queryPlan := marshalQueryPlan(t, map[string]any{
		"raw_query":               "PE程序下驱动下载卡在95",
		"normalized_query":        "Investigate WinPE driver download progress stalling at 95 percent.",
		"intent_facets":           []string{"WinPE runtime", "driver download", "95 percent stall"},
		"alias_interpretations":   []string{"PE程序"},
		"expanded_queries":        []string{"WinPE driver download progress stall"},
		"paths":                   []string{"src/app.go"},
		"open_semantic_questions": []string{},
	})
	queryPlanFile := filepath.Join(root, "query-plan.json")
	if err := os.WriteFile(queryPlanFile, []byte(queryPlan), 0o644); err != nil {
		t.Fatal(err)
	}

	cases := []struct {
		name string
		args []string
	}{
		{
			name: "inline",
			args: []string{"query", "--intent", "debug", "--query-plan", queryPlan, "--format", "json"},
		},
		{
			name: "at-file",
			args: []string{"query", "--intent", "debug", "--query-plan", "@" + queryPlanFile, "--format", "json"},
		},
		{
			name: "query-plan-file",
			args: []string{"query", "--intent", "debug", "--query-plan-file", queryPlanFile, "--format", "json"},
		},
	}
	for _, tt := range cases {
		t.Run(tt.name, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			code := Run(tt.args, &stdout, &stderr, "test")
			if code != 0 {
				t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
			}
			var payload map[string]any
			if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
				t.Fatal(err)
			}
			if !jsonStringSliceContains(payload["warnings"], "coerced_top_level_alias_interpretations") {
				t.Fatalf("warnings = %#v, want alias coercion warning", payload["warnings"])
			}
			if !jsonStringSliceContains(payload["warnings"], "query_plan_missing_lexicon_generation_id") {
				t.Fatalf("warnings = %#v, want missing generation warning", payload["warnings"])
			}
			if hints, ok := payload["repair_hints"].([]any); !ok || len(hints) == 0 {
				t.Fatalf("repair_hints = %#v, want non-empty hints", payload["repair_hints"])
			}
			queryPlanPayload, ok := payload["query_plan"].(map[string]any)
			if !ok {
				t.Fatalf("query_plan missing from payload = %#v", payload)
			}
			intake, ok := queryPlanPayload["semantic_intake"].(map[string]any)
			if !ok {
				t.Fatalf("semantic_intake missing from query_plan = %#v", queryPlanPayload)
			}
			aliases, ok := intake["alias_interpretations"].([]any)
			if !ok || len(aliases) != 1 {
				t.Fatalf("alias_interpretations = %#v, want one normalized alias object", intake["alias_interpretations"])
			}
			alias, ok := aliases[0].(map[string]any)
			if !ok {
				t.Fatalf("alias_interpretations[0] = %#v, want object", aliases[0])
			}
			if alias["alias"] != "PE程序" || alias["meaning"] != "PE程序" || alias["confidence"] != "low" {
				t.Fatalf("alias = %#v, want low-confidence coerced object", alias)
			}
		})
	}
}

func TestQueryCommandReturnsStructuredJSONForUnrecoverableQueryPlanShape(t *testing.T) {
	setupReadyMinimalCLIRuntime(t)
	queryPlan := `{"semantic_intake":{"alias_interpretations":[{"alias":95}]}}`

	var stdout, stderr bytes.Buffer
	code := Run([]string{"query", "--intent", "debug", "--query-plan", queryPlan, "--format", "json"}, &stdout, &stderr, "test")
	if code == 0 {
		t.Fatalf("code = 0, want non-zero for unrecoverable query plan; stdout=%s", stdout.String())
	}
	if strings.TrimSpace(stdout.String()) == "" {
		t.Fatalf("stdout is empty; stderr-only parser failures are not acceptable, stderr=%s", stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatalf("stdout is not JSON: %v\nstdout=%s\nstderr=%s", err, stdout.String(), stderr.String())
	}
	if payload["status"] != "error" {
		t.Fatalf("payload = %#v, want status=error", payload)
	}
	if errors, ok := payload["errors"].([]any); !ok || len(errors) == 0 {
		t.Fatalf("errors = %#v, want non-empty errors array", payload["errors"])
	}
	if _, ok := payload["warnings"].([]any); !ok {
		t.Fatalf("warnings = %#v, want warnings array", payload["warnings"])
	}
	if hints, ok := payload["repair_hints"].([]any); !ok || len(hints) == 0 {
		t.Fatalf("repair_hints = %#v, want non-empty repair hints", payload["repair_hints"])
	}
	if _, ok := payload["expected_shape"].(map[string]any); !ok {
		t.Fatalf("expected_shape = %#v, want object", payload["expected_shape"])
	}
	if !strings.Contains(stderr.String(), "query plan") {
		t.Fatalf("stderr = %q, want concise query plan message", stderr.String())
	}
}

func TestQueryCommandHandlesGreenfieldEmptyBaseline(t *testing.T) {
	initEmptyCLIRuntime(t)
	queryPlan := marshalQueryPlan(t, map[string]any{
		"raw_query": "build login",
		"paths":     []string{"docs/login.md"},
	})

	var stdout, stderr bytes.Buffer
	code := Run([]string{"query", "--intent", "plan", "--query-plan", queryPlan, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["readiness"] != rt.ReadyReadiness {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("payload = %#v", payload)
	}
	if !jsonStringSliceContains(payload["minimal_live_reads"], ".specify/memory/constitution.md") {
		t.Fatalf("minimal_live_reads = %#v", payload["minimal_live_reads"])
	}
	if !jsonStringSliceContains(payload["minimal_live_reads"], "docs/login.md") {
		t.Fatalf("minimal_live_reads = %#v", payload["minimal_live_reads"])
	}
	if !jsonStringSliceContains(payload["missing_coverage"], "greenfield_empty_no_project_code") {
		t.Fatalf("missing_coverage = %#v", payload["missing_coverage"])
	}
}

func TestQueryCommandAcceptsSuffixConceptIDPlan(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	conceptID := "concept:" + status.ActiveGenerationID + ":N-app:alias:app"
	queryPlan := marshalQueryPlan(t, map[string]any{
		"lexicon_generation_id": status.ActiveGenerationID,
		"selected_concepts":     []string{conceptID},
	})

	var stdout, stderr bytes.Buffer
	code := Run([]string{"query", "--intent", "implement", "--query-plan", queryPlan, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if !jsonStringSliceContains(payload["minimal_live_reads"], "src/app.go") {
		t.Fatalf("minimal_live_reads = %#v, want src/app.go", payload["minimal_live_reads"])
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

func TestPublishRuntimeMetadataChecksLegacyStatusBeforeSparseInvalidWrites(t *testing.T) {
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
	if generationID == "" {
		t.Fatal("active generation id is empty")
	}
	if _, err := st.DB().ExecContext(context.Background(), `DELETE FROM path_index WHERE generation_id = ?`, generationID); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	legacyStatus := []byte(`{"freshness":"fresh"}`)
	if err := os.WriteFile(paths.StatusPath, legacyStatus, 0o644); err != nil {
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
	if got, err := os.ReadFile(paths.StatusPath); err != nil {
		t.Fatal(err)
	} else if !bytes.Equal(got, legacyStatus) {
		t.Fatalf("status.json was overwritten:\ngot:  %s\nwant: %s", got, legacyStatus)
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

func setupReadyMinimalCLIRuntime(t *testing.T) string {
	t.Helper()
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

	var publishStdout, publishStderr bytes.Buffer
	publishCode := Run([]string{"publish-runtime-metadata", "--format", "json"}, &publishStdout, &publishStderr, "test")
	if publishCode != 0 {
		t.Fatalf("publish code = %d stderr=%s stdout=%s", publishCode, publishStderr.String(), publishStdout.String())
	}
	return root
}

func initEmptyCLIRuntime(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"init-empty", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("init-empty code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	return root
}

func cliRuntimePaths(root string) rt.Paths {
	runtimeDir := filepath.Join(root, rt.SpecifyDir, rt.CognitionDir)
	return rt.Paths{
		Root:         root,
		RuntimeDir:   runtimeDir,
		StatusPath:   filepath.Join(runtimeDir, rt.StatusFileName),
		DatabasePath: filepath.Join(runtimeDir, rt.DBFileName),
	}
}

func marshalQueryPlan(t *testing.T, payload map[string]any) string {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	return string(data)
}

func hasTable(t *testing.T, db *sql.DB, tableName string) bool {
	t.Helper()
	var name string
	err := db.QueryRowContext(context.Background(), `SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?`, tableName).Scan(&name)
	if errors.Is(err, sql.ErrNoRows) {
		return false
	}
	if err != nil {
		t.Fatal(err)
	}
	return true
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
			"summary":          "App owns frame rendering and input dispatch.",
			"evidence_ids":     []string{"E-001"},
		}, {
			"id":               "OBS-app-observed",
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

func TestUpdateCommandAcceptsPayloadFileAndEmitsResultState(t *testing.T) {
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

	payloadPath := filepath.Join(root, ".specify", "project-cognition", "updates", "workflow-finalize.json")
	if err := os.MkdirAll(filepath.Dir(payloadPath), 0o755); err != nil {
		t.Fatal(err)
	}
	payload := map[string]any{
		"workflow":          "sp-implement",
		"reason":            "workflow-finalize",
		"changed_paths":     []string{"src/app.go"},
		"scope_paths":       []string{"src"},
		"behavior_surfaces": []string{"application entrypoint"},
		"verification": []map[string]string{
			{"command": "go test ./...", "result": "passed", "artifact": "artifacts/quality-runs/example/report.md"},
		},
		"known_unknowns":   []string{},
		"confidence_notes": []string{"indexed path refresh"},
	}
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(payloadPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"update", "--payload-file", payloadPath, "--reason", "workflow-finalize", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var result map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result["result_state"] == "" {
		t.Fatalf("payload = %#v, want result_state", result)
	}
	if result["update_id"] == "" {
		t.Fatalf("payload = %#v, want update_id", result)
	}
	if _, ok := result["status_update"].(map[string]any); !ok {
		t.Fatalf("payload = %#v, want status_update object", result)
	}
}

func TestUpdateCommandAcceptsVerificationForDirectChangedPaths(t *testing.T) {
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

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"update",
		"--changed-path", "src/app.go",
		"--behavior-surface", "application entrypoint",
		"--verification", "go test ./... PASS",
		"--reason", "workflow-finalize",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var result map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result["result_state"] != "ready" {
		t.Fatalf("payload = %#v, want ready result_state", result)
	}
	if result["readiness"] != rt.ReadyReadiness {
		t.Fatalf("payload = %#v, want ready readiness", result)
	}
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
	return jsonAnySliceContains(values, want)
}

func jsonAnySliceContains(values []any, want string) bool {
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

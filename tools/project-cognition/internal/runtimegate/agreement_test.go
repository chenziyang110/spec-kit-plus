package runtimegate

import (
	"context"
	"database/sql"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestCheckAgreementAcceptsMatchingStatusAndDB(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	importAndPublishReady(t, st, "GEN-1")
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-1"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	agreement := Check(paths)

	if agreement.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%v", agreement.Status, agreement.Errors)
	}
}

func TestCheckAgreementAcceptsMatchingGenerationRegardlessOfStatusValue(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	importAndPublishReady(t, st, "GEN-1")
	status := rt.DefaultStatus(paths)
	status.Status = "missing"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-1"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	agreement := Check(paths)

	if agreement.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%v", agreement.Status, agreement.Errors)
	}
}

func TestCheckAgreementAcceptsEquivalentGraphStorePathVariants(t *testing.T) {
	for _, graphStorePath := range []string{
		`.specify\project-cognition\project-cognition.db`,
		`./.specify/project-cognition/project-cognition.db`,
		`.specify/project-cognition/../project-cognition/project-cognition.db`,
	} {
		t.Run(graphStorePath, func(t *testing.T) {
			paths := testPaths(t)
			st, err := store.Open(paths)
			if err != nil {
				t.Fatal(err)
			}
			defer st.Close()
			importAndPublishReady(t, st, "GEN-1")
			status := rt.DefaultStatus(paths)
			status.Status = "ok"
			status.Freshness = rt.ReadyFreshness
			status.Readiness = rt.ReadyReadiness
			status.GraphReady = true
			status.ActiveGenerationID = "GEN-1"
			if err := rt.WriteStatus(paths, status); err != nil {
				t.Fatal(err)
			}
			data, err := os.ReadFile(paths.StatusPath)
			if err != nil {
				t.Fatal(err)
			}
			var payload map[string]any
			if err := json.Unmarshal(data, &payload); err != nil {
				t.Fatal(err)
			}
			payload["graph_store_path"] = graphStorePath
			data, err = json.MarshalIndent(payload, "", "  ")
			if err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(paths.StatusPath, append(data, '\n'), 0o644); err != nil {
				t.Fatal(err)
			}

			agreement := Check(paths)

			if agreement.Status != "ok" {
				t.Fatalf("Status = %q, want ok; errors=%v", agreement.Status, agreement.Errors)
			}
			if agreement.GraphStorePath != ".specify/project-cognition/project-cognition.db" {
				t.Fatalf("GraphStorePath = %q, want normalized default", agreement.GraphStorePath)
			}
		})
	}
}

func TestCheckAgreementBlocksSplitBrainActiveGeneration(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	importAndPublishReady(t, st, "GEN-db")
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	agreement := Check(paths)

	if agreement.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", agreement.Status)
	}
	if agreement.RecoveryAction != "rewrite_status_from_db_metadata" {
		t.Fatalf("RecoveryAction = %q, want rewrite_status_from_db_metadata", agreement.RecoveryAction)
	}
	if !strings.Contains(strings.Join(agreement.Errors, "\n"), "mismatch") {
		t.Fatalf("Errors = %v, want mismatch message", agreement.Errors)
	}
}

func TestCheckAgreementBlocksIncompatibleDatabaseWithoutArchiving(t *testing.T) {
	paths := testPaths(t)
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

	agreement := Check(paths)

	if agreement.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%v", agreement.Status, agreement.Errors)
	}
	if !strings.Contains(strings.Join(agreement.Errors, "\n"), "current runtime requires 5") {
		t.Fatalf("Errors = %#v, want current schema requirement", agreement.Errors)
	}
	if _, err := os.Stat(paths.DatabasePath + ".legacy"); !os.IsNotExist(err) {
		t.Fatalf("legacy archive stat err = %v, want no archive", err)
	}
}

func TestCheckAgreementBlocksMissingRequiredMetadata(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	importAndPublishReady(t, st, "GEN-1")
	if _, err := st.DB().ExecContext(context.Background(), `DELETE FROM metadata WHERE key = 'runtime_format'`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-1"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	agreement := Check(paths)

	if agreement.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%v", agreement.Status, agreement.Errors)
	}
	if agreement.RecoveryAction != "rewrite_status_from_db_metadata" {
		t.Fatalf("RecoveryAction = %q, want rewrite_status_from_db_metadata", agreement.RecoveryAction)
	}
	if !strings.Contains(strings.Join(agreement.Errors, "\n"), "metadata missing runtime_format") {
		t.Fatalf("Errors = %#v, want missing metadata error", agreement.Errors)
	}
}

func TestRuntimeGateBlocksGreenfieldKindMismatch(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	generationID, err := st.InitializeGreenfieldEmpty(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `UPDATE metadata SET value_json = '"brownfield_full"' WHERE key = 'baseline_kind'`); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = generationID
	status.BaselineKind = rt.BaselineKindGreenfieldEmpty
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	agreement := Check(paths)

	if agreement.Status != "blocked" {
		t.Fatalf("agreement = %#v", agreement)
	}
	if !containsString(agreement.Errors, `baseline_kind mismatch: status.json has "greenfield_empty", DB metadata has "brownfield_full"`) {
		t.Fatalf("errors = %#v", agreement.Errors)
	}
}

func TestRuntimeGateBlocksMetadataGenerationKindMismatch(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	generationID, err := st.InitializeGreenfieldEmpty(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `UPDATE metadata SET value_json = '"brownfield_full"' WHERE key = 'baseline_kind'`); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = generationID
	status.BaselineKind = rt.BaselineKindBrownfieldFull
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	agreement := Check(paths)

	if agreement.Status != "blocked" {
		t.Fatalf("agreement = %#v", agreement)
	}
	if !containsString(agreement.Errors, `baseline_kind mismatch: DB metadata has "brownfield_full", active generation has "greenfield_empty"`) {
		t.Fatalf("errors = %#v", agreement.Errors)
	}
}

func TestBlockIfExistingSkipsMissingBaselineAndBlocksSplitBrain(t *testing.T) {
	missingPaths := testPaths(t)
	if err := BlockIfExisting(missingPaths); err != nil {
		t.Fatalf("missing baseline error = %v, want nil", err)
	}

	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	importAndPublishReady(t, st, "GEN-db")
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	err = BlockIfExisting(paths)

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %q, want rewrite_status_from_db_metadata", err.Error())
	}
}

func TestBlockIfExistingBlocksOneSidedRuntimeState(t *testing.T) {
	statusOnly := testPaths(t)
	status := rt.DefaultStatus(statusOnly)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-status"
	if err := rt.WriteStatus(statusOnly, status); err != nil {
		t.Fatal(err)
	}
	err := BlockIfExisting(statusOnly)
	if err == nil {
		t.Fatal("expected status-only agreement error")
	}
	if !strings.Contains(err.Error(), "project-cognition.db is missing") {
		t.Fatalf("error = %q, want missing DB", err.Error())
	}

	dbOnly := testPaths(t)
	st, err := store.Open(dbOnly)
	if err != nil {
		t.Fatal(err)
	}
	importAndPublishReady(t, st, "GEN-db")
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	err = BlockIfExisting(dbOnly)
	if err == nil {
		t.Fatal("expected DB-only agreement error")
	}
	if !strings.Contains(err.Error(), "status.json is missing") {
		t.Fatalf("error = %q, want missing status", err.Error())
	}
}

func importAndPublishReady(t *testing.T, st *store.Store, generationID string) {
	t.Helper()
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{GenerationID: generationID, Kind: "full"}); err != nil {
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), generationID, rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatal(err)
	}
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func testPaths(t *testing.T) rt.Paths {
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

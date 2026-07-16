package runtimegate

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
	if agreement.RecoveryAction != RepairStatusAction {
		t.Fatalf("RecoveryAction = %q, want %q", agreement.RecoveryAction, RepairStatusAction)
	}
	if agreement.CauseCode != CauseStatusGenerationMismatch || agreement.CauseOwner != CauseOwnerStatus {
		t.Fatalf("cause = %q/%q, want status generation mismatch", agreement.CauseOwner, agreement.CauseCode)
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
	if agreement.RecoveryAction != rebuildAction {
		t.Fatalf("RecoveryAction = %q, want %q", agreement.RecoveryAction, rebuildAction)
	}
	if agreement.CauseCode != CauseGraphStoreMetadataInvalid || agreement.CauseOwner != CauseOwnerGraphStore {
		t.Fatalf("cause = %q/%q, want graph store metadata invalid", agreement.CauseOwner, agreement.CauseCode)
	}
	if !strings.Contains(strings.Join(agreement.Errors, "\n"), "metadata missing runtime_format") {
		t.Fatalf("Errors = %#v, want missing metadata error", agreement.Errors)
	}
}

func TestCheckAgreementRoutesEveryInvalidDBMetadataInvariantToGraphRepair(t *testing.T) {
	tests := []struct {
		key   string
		value any
	}{
		{key: "runtime_format", value: "wrong-runtime"},
		{key: "runtime_schema", value: 99},
		{key: "schema_version", value: 1},
		{key: "active_generation_id", value: "GEN-missing"},
		{key: "graph_store_path", value: ".specify/wrong.db"},
		{key: "graph_ready", value: false},
		{key: "baseline_state", value: "stale"},
		{key: "baseline_kind", value: "invalid"},
		{key: "query_contract_version", value: 99},
		{key: "update_contract_version", value: 99},
	}

	for _, tt := range tests {
		t.Run(tt.key, func(t *testing.T) {
			paths := testPaths(t)
			st, err := store.Open(paths)
			if err != nil {
				t.Fatal(err)
			}
			importAndPublishReady(t, st, "GEN-1")
			encoded, err := json.Marshal(tt.value)
			if err != nil {
				t.Fatal(err)
			}
			if _, err := st.DB().ExecContext(
				context.Background(),
				`UPDATE metadata SET value_json = ? WHERE key = ?`,
				string(encoded),
				tt.key,
			); err != nil {
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

			if agreement.Status != "blocked" || agreement.CauseOwner != CauseOwnerGraphStore {
				t.Fatalf("agreement = %#v, want graph-store blocker", agreement)
			}
			if agreement.RecoveryAction != rebuildAction || agreement.RecommendedNextAction != rebuildAction {
				t.Fatalf("actions = %q/%q, want rebuild", agreement.RecoveryAction, agreement.RecommendedNextAction)
			}
			if agreement.CauseCode == "" {
				t.Fatal("CauseCode is empty")
			}
		})
	}
}

func TestRepairStatusFromDBRepairsOnlyStatusOwnedMismatch(t *testing.T) {
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
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	repaired, err := RepairStatusFromDB(paths)
	if err != nil {
		t.Fatal(err)
	}

	if repaired.ActiveGenerationID != "GEN-db" || repaired.Readiness != rt.ReadyReadiness {
		t.Fatalf("repaired status = %#v", repaired)
	}
	if agreement := Check(paths); agreement.Status != "ok" {
		t.Fatalf("agreement after repair = %#v", agreement)
	}
}

func TestRepairStatusFromDBRefusesCorruptGraphMetadataWithoutChangingStatus(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	importAndPublishReady(t, st, "GEN-1")
	if _, err := st.DB().ExecContext(
		context.Background(),
		`UPDATE metadata SET value_json = '"wrong-runtime"' WHERE key = 'runtime_format'`,
	); err != nil {
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
	before, err := os.ReadFile(paths.StatusPath)
	if err != nil {
		t.Fatal(err)
	}

	_, err = RepairStatusFromDB(paths)

	if err == nil || !strings.Contains(err.Error(), "runtime_format") {
		t.Fatalf("error = %v, want runtime_format graph validation failure", err)
	}
	var typed *RepairError
	if !errors.As(err, &typed) || typed.CauseCode != CauseGraphStoreMetadataInvalid || typed.CauseOwner != CauseOwnerGraphStore {
		t.Fatalf("typed repair error = %#v, want graph metadata owner", typed)
	}
	after, readErr := os.ReadFile(paths.StatusPath)
	if readErr != nil {
		t.Fatal(readErr)
	}
	if string(after) != string(before) {
		t.Fatal("status changed after graph-owned repair refusal")
	}
}

func TestRepairStatusFromDBReconstructsBlockedGraphState(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-blocked",
		Kind:         "full",
	}); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.MarkRuntimeMetadataBlocked(context.Background(), "GEN-blocked"); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	repaired, err := RepairStatusFromDB(paths)
	if err != nil {
		t.Fatal(err)
	}

	if repaired.Status != "blocked" || repaired.Readiness != rt.BlockedReadiness || repaired.GraphReady {
		t.Fatalf("repaired status = %#v, want truthful blocked graph state", repaired)
	}
	if repaired.RecommendedNextAction != rebuildAction {
		t.Fatalf("recommended action = %q, want %q", repaired.RecommendedNextAction, rebuildAction)
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
	if !containsString(agreement.Errors, `baseline_kind mismatch: DB metadata has "brownfield_full", active generation has "greenfield_empty"`) {
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
	if !strings.Contains(err.Error(), RepairStatusAction) {
		t.Fatalf("error = %q, want %s", err.Error(), RepairStatusAction)
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

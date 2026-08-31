package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"testing"
	"time"
)

func TestFreshStoreInitializesOnlySharedCoordination(t *testing.T) {
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	want := []string{"events", "execution_activities", "execution_resource_intents", "metadata", "work_items", "write_intents"}
	if got := databaseTables(t, store.db); !reflect.DeepEqual(got, want) {
		t.Fatalf("fresh store tables = %v, want only shared coordination tables %v", got, want)
	}
	var count int
	if err := store.db.QueryRow(`SELECT COUNT(*) FROM events`).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 0 {
		t.Fatalf("opening an empty board emitted %d lifecycle events", count)
	}
}

func TestOpenMigratesLegacyStoresAdditively(t *testing.T) {
	for version := 3; version <= 13; version++ {
		t.Run(fmt.Sprintf("v%d", version), func(t *testing.T) {
			databasePath, db := openLegacyFixture(t, version)
			before := databaseContents(t, db)
			if err := db.Close(); err != nil {
				t.Fatal(err)
			}

			store := openTestStore(t, databasePath)
			assertPreservedDatabaseContents(t, store.db, before)
			var migrated int
			if err := store.db.QueryRow(`SELECT value FROM metadata WHERE key = 'schema_version'`).Scan(&migrated); err != nil {
				t.Fatal(err)
			}
			if migrated != schemaVersion {
				t.Fatalf("schema version = %d, want %d", migrated, schemaVersion)
			}
			// Migration may add shared tables, never missing retired tables.
			shared := map[string]bool{"metadata": true, "events": true, "work_items": true, "write_intents": true,
				"execution_activities": true, "execution_resource_intents": true}
			for _, table := range databaseTables(t, store.db) {
				if _, existed := before[table]; !existed && !shared[table] {
					t.Errorf("migration introduced retired table %q", table)
				}
			}
			if err := store.Close(); err != nil {
				t.Fatal(err)
			}
			reopened := openTestStore(t, databasePath)
			assertPreservedDatabaseContents(t, reopened.db, before)
		})
	}
}

func openLegacyFixture(t *testing.T, version int) (string, *sql.DB) {
	t.Helper()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	db, err := sql.Open("sqlite", databasePath)
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	t.Cleanup(func() { _ = db.Close() })
	if _, err := db.Exec(`PRAGMA foreign_keys = ON`); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"legacy_store.sql", "legacy_rows.sql"} {
		data, err := os.ReadFile(filepath.Join("testdata", name))
		if err != nil {
			t.Fatal(err)
		}
		for _, section := range strings.Split(string(data), "-- schema-version: ")[1:] {
			parts := strings.SplitN(section, "\n", 2)
			introduced, err := strconv.Atoi(strings.TrimSpace(parts[0]))
			if err != nil || len(parts) != 2 {
				t.Fatalf("invalid version marker in %s: %q", name, parts[0])
			}
			if introduced > version {
				continue
			}
			statement := strings.ReplaceAll(parts[1], "TEST_SHA256", strings.Repeat("a", 64))
			if _, err := db.Exec(statement); err != nil {
				t.Fatalf("load %s v%d: %v", name, introduced, err)
			}
		}
	}
	if _, err := db.Exec(`INSERT INTO metadata (key, value) VALUES ('schema_version', ?)`, version); err != nil {
		t.Fatal(err)
	}
	return databasePath, db
}

func databaseTables(t *testing.T, db *sql.DB) []string {
	t.Helper()
	rows, err := db.Query(`SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name`)
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()
	var names []string
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			t.Fatal(err)
		}
		names = append(names, name)
	}
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
	return names
}

type preservedTable struct {
	Schema string
	Rows   [][]any
}

func databaseContents(t *testing.T, db *sql.DB) map[string]preservedTable {
	t.Helper()
	result := make(map[string]preservedTable)
	for _, name := range databaseTables(t, db) {
		var table preservedTable
		if err := db.QueryRow(`SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?`, name).Scan(&table.Schema); err != nil {
			t.Fatal(err)
		}
		query := `SELECT * FROM "` + strings.ReplaceAll(name, `"`, `""`) + `"`
		if name == "metadata" {
			query += ` WHERE key <> 'schema_version'`
		}
		rows, err := db.Query(query + ` ORDER BY rowid`)
		if err != nil {
			t.Fatal(err)
		}
		columns, err := rows.Columns()
		if err != nil {
			t.Fatal(err)
		}
		for rows.Next() {
			values := make([]any, len(columns))
			destinations := make([]any, len(columns))
			for i := range values {
				destinations[i] = &values[i]
			}
			if err := rows.Scan(destinations...); err != nil {
				t.Fatal(err)
			}
			table.Rows = append(table.Rows, values)
		}
		if err := rows.Err(); err != nil {
			t.Fatal(err)
		}
		if err := rows.Close(); err != nil {
			t.Fatal(err)
		}
		result[name] = table
	}
	return result
}

func assertPreservedDatabaseContents(t *testing.T, db *sql.DB, before map[string]preservedTable) {
	t.Helper()
	after := databaseContents(t, db)
	for name, table := range before {
		if !reflect.DeepEqual(after[name], table) {
			t.Errorf("opening or closing the shared store changed legacy table %q (schema or row contents)", name)
		}
	}
}

func TestMigratedLegacyWorkKeepsGuardsAndCanCompleteIndependently(t *testing.T) {
	ctx := context.Background()
	databasePath, db := openLegacyFixture(t, 13)
	_, workspaceRoot := createLinkedRepository(t)
	userPath := filepath.Join(workspaceRoot, "unfinished.txt")
	userContent := []byte("preserve old workspace work\n")
	if err := os.WriteFile(userPath, userContent, 0o644); err != nil {
		t.Fatal(err)
	}
	beforeHead := runGit(t, ensureGitAvailable(t), workspaceRoot, "rev-parse", "HEAD")
	if _, err := db.Exec(`UPDATE workspaces SET root_path = ?`, workspaceRoot); err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec(`UPDATE work_items SET workspace_root = ?`, workspaceRoot); err != nil {
		t.Fatal(err)
	}
	before := databaseContents(t, db)
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	store := openTestStore(t, databasePath)
	assertPreservedDatabaseContents(t, store.db, before)
	registration, err := store.GetExecutionActivity(ctx, "legacy-execution")
	if err != nil {
		t.Fatal(err)
	}
	if registration.Work.Fence != 4 || registration.Work.Revision != 7 || registration.Work.Status != WorkActive ||
		registration.Work.RunID != "legacy-run" || registration.Activity.Phase != ExecutionPhaseExecuting {
		t.Fatalf("migration changed active authority: %#v", registration)
	}
	claim := ClaimWorkIntentsParams{
		WorkID: registration.Work.WorkID, ExpectedRevision: registration.Work.Revision, Fence: registration.Work.Fence,
		Specs: []WriteIntentSpec{{Path: "src/owned.go"}},
	}
	if _, _, err := store.VerifyExecutionWorkClaim(ctx, claim); err != nil {
		t.Fatalf("valid migrated guard rejected: %v", err)
	}
	staleClaim := claim
	staleClaim.Fence++
	if _, _, err := store.VerifyExecutionWorkClaim(ctx, staleClaim); !errors.Is(err, ErrStaleFence) {
		t.Fatalf("migration accepted a stale fence: %v", err)
	}
	staleClaim = claim
	staleClaim.ExpectedRevision--
	if _, _, err := store.VerifyExecutionWorkClaim(ctx, staleClaim); !errors.Is(err, ErrRevisionConflict) {
		t.Fatalf("migration accepted a stale revision: %v", err)
	}
	for _, path := range []string{"src/owned.go", "src/recovery.go"} {
		_, _, err := store.BeginWork(ctx, BeginWorkParams{
			WorkID: "competing", Summary: "competing work", AgentID: "another-agent", AdapterID: "codex",
			WorkspaceRoot: workspaceRoot, LeaseUntil: time.Now().UTC().Add(time.Hour),
			WriteIntents: []WriteIntentSpec{{Path: path}},
		})
		if !errors.Is(err, ErrWorkIntentConflict) {
			t.Fatalf("migration released live or dirty ownership of %q: %v", path, err)
		}
	}
	assertPreservedDatabaseContents(t, store.db, before)

	oldRevision, err := store.CoordinationRevision(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if oldRevision != 203 {
		t.Fatalf("migration reset event watermark: %d", oldRevision)
	}
	competitor := announceExecutionTestActivity(t, store, "new-activity", "debug:new", "src/new.go", ResourceAPI, "/v1/legacy")
	currentRevision, err := store.CoordinationRevision(ctx)
	if err != nil {
		t.Fatal(err)
	}
	guard := GuardExecutionParams{
		ActivityID: competitor.Activity.ActivityID, ExpectedWorkRevision: competitor.Work.Revision, Fence: competitor.Work.Fence,
		ExpectedCoordinationRevision: oldRevision, OverviewSHA256: strings.Repeat("b", 64), Reason: "claim competing scope",
		WriteIntents: []WriteIntentSpec{{Path: "src/new.go", Confidence: IntentConfirmed}},
		Resources:    []ExecutionResourceIntentSpec{{ResourceType: ResourceAPI, ResourceKey: "/v1/legacy", Confidence: IntentConfirmed}},
	}
	if _, err := store.GuardExecution(ctx, guard); !errors.Is(err, ErrExecutionSnapshotStale) {
		t.Fatalf("migration accepted a stale overview: %v", err)
	}
	guard.ExpectedCoordinationRevision = currentRevision
	if _, err := store.GuardExecution(ctx, guard); !errors.Is(err, ErrExecutionResourceConflict) {
		t.Fatalf("migration released semantic ownership: %v", err)
	}
	unchanged, err := store.GetExecutionActivity(ctx, competitor.Activity.ActivityID)
	if err != nil || !reflect.DeepEqual(unchanged, competitor) {
		t.Fatalf("failed guard partially acquired scope: %#v, %v", unchanged, err)
	}
	completed, err := store.CompleteExecution(ctx, CompleteExecutionParams{
		ActivityID: registration.Activity.ActivityID, ExpectedWorkRevision: registration.Work.Revision, Fence: registration.Work.Fence,
		ChangedPaths: []string{"src/owned.go"}, ValidationJSON: `[{"command":"fixture validation","result":"passed"}]`,
		Reason: "complete shared work without a legacy Run lifecycle",
	})
	if err != nil || completed.Work.Status != WorkCompleted || completed.Activity.Phase != ExecutionPhaseCompleted {
		t.Fatalf("legacy metadata prevented shared completion: %#v, %v", completed, err)
	}
	retired := make(map[string]preservedTable)
	for name, table := range before {
		switch name {
		case "metadata", "events", "work_items", "write_intents", "execution_activities", "execution_resource_intents":
			continue
		}
		retired[name] = table
	}
	assertPreservedDatabaseContents(t, store.db, retired)
	if err := store.Close(); err != nil {
		t.Fatal(err)
	}
	reopened := openTestStore(t, databasePath)
	assertPreservedDatabaseContents(t, reopened.db, retired)
	if content, err := os.ReadFile(userPath); err != nil || string(content) != string(userContent) {
		t.Fatalf("migration changed legacy worktree contents: %q, %v", content, err)
	}
	if afterHead := runGit(t, ensureGitAvailable(t), workspaceRoot, "rev-parse", "HEAD"); afterHead != beforeHead {
		t.Fatalf("migration moved legacy worktree HEAD: %s -> %s", beforeHead, afterHead)
	}
}

func TestExecutionCompletionIgnoresHistoricalRunIDWithoutLifecycleTables(t *testing.T) {
	ctx := context.Background()
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	registration, err := store.AnnounceExecution(ctx, AnnounceExecutionParams{
		ActivityID: "historical", WorkID: "historical", RunID: "an-old-label-with-no-row", TaskRef: "fast:historical",
		Workflow: ExecutionWorkflowFast, SubjectID: "historical", Summary: "independent shared work",
		AgentID: "agent", AdapterID: "codex", WorkspaceRoot: t.TempDir(), LeaseUntil: time.Now().UTC().Add(time.Hour),
		PlannedWriteIntents: []WriteIntentSpec{{Path: "src/owned.go", Confidence: IntentCandidate}},
	})
	if err != nil {
		t.Fatal(err)
	}
	guarded := guardTestExecution(t, store, registration)
	completed, err := store.CompleteExecution(ctx, CompleteExecutionParams{
		ActivityID: guarded.Activity.ActivityID, ExpectedWorkRevision: guarded.Work.Revision, Fence: guarded.Work.Fence,
		ChangedPaths: []string{"src/owned.go"}, ValidationJSON: `[{"command":"fixture validation","result":"passed"}]`, Reason: "done",
	})
	if err != nil || completed.Work.Status != WorkCompleted {
		t.Fatalf("historical RunID affected execution completion: %#v, %v", completed, err)
	}
	if len(databaseTables(t, store.db)) != 6 {
		t.Fatal("execution initialized lifecycle tables")
	}
}

func TestFailedAdditiveMigrationRollsBackSharedSchema(t *testing.T) {
	databasePath, db := openLegacyFixture(t, 3)
	if _, err := db.Exec(`CREATE TABLE work_items (work_id TEXT PRIMARY KEY, custom BLOB);
		INSERT INTO work_items VALUES ('preserved', x'deadbeef')`); err != nil {
		t.Fatal(err)
	}
	before := databaseContents(t, db)
	store, err := Open(context.Background(), databasePath)
	if store != nil || err == nil {
		if store != nil {
			_ = store.Close()
		}
		t.Fatalf("incompatible shared table unexpectedly migrated: %v", err)
	}
	assertPreservedDatabaseContents(t, db, before)
	if len(databaseTables(t, db)) != len(before) {
		t.Fatal("failed migration left partial tables")
	}
	var version int
	if err := db.QueryRow(`SELECT value FROM metadata WHERE key = 'schema_version'`).Scan(&version); err != nil || version != 3 {
		t.Fatalf("failed migration changed schema version to %d: %v", version, err)
	}
}

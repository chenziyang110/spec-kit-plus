package runcontrol

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"testing"
	"time"
)

func TestViewEnforcesSQLiteQueryOnlyMode(t *testing.T) {
	ctx := context.Background()
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	store := openTestStore(t, databasePath)
	work, _, err := store.BeginWork(ctx, BeginWorkParams{
		WorkID: "view-work", Summary: "view work", AgentID: "agent", AdapterID: "codex",
		WorkspaceRoot: t.TempDir(), LeaseUntil: time.Now().UTC().Add(time.Hour),
	})
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Close(); err != nil {
		t.Fatal(err)
	}
	view, err := OpenView(ctx, databasePath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = view.Close() })
	var queryOnly int
	if err := view.db.QueryRow("PRAGMA query_only").Scan(&queryOnly); err != nil || queryOnly != 1 {
		t.Fatalf("query_only = %d, err = %v", queryOnly, err)
	}
	if _, err := view.db.ExecContext(ctx, `UPDATE work_items SET status = 'abandoned' WHERE work_id = ?`, work.WorkID); err == nil {
		t.Fatal("query-only View accepted a write")
	}
	if _, err := view.db.ExecContext(ctx, `PRAGMA query_only = OFF`); err != nil {
		t.Fatal(err)
	}
	if _, err := view.db.ExecContext(ctx, `UPDATE work_items SET status = 'abandoned' WHERE work_id = ?`, work.WorkID); err == nil {
		t.Fatal("read-only database connection accepted a write")
	}
	loaded, _, err := view.GetWork(ctx, work.WorkID)
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(loaded, work) {
		t.Fatalf("work changed through View: %#v", loaded)
	}
	if err := view.Close(); err != nil {
		t.Fatal(err)
	}
	if err := view.Close(); err != nil {
		t.Fatalf("second View.Close() error = %v", err)
	}
}

func TestViewProjectsLegacySharedStateWithoutMigration(t *testing.T) {
	for _, version := range []int{3, 12, 13} {
		t.Run(fmt.Sprintf("v%d", version), func(t *testing.T) {
			databasePath, db := openLegacyFixture(t, version)
			before := databaseContents(t, db)
			view, err := OpenView(context.Background(), databasePath)
			if err != nil {
				t.Fatal(err)
			}
			t.Cleanup(func() { _ = view.Close() })
			works, err := view.ListWork(context.Background(), ListWorkParams{})
			if err != nil {
				t.Fatal(err)
			}
			activities, err := view.ListExecutionActivities(context.Background(), ListExecutionActivitiesParams{})
			if err != nil {
				t.Fatal(err)
			}
			wantWork, wantActivities := 0, 0
			if version >= 12 {
				wantWork = 2
			}
			if version >= 13 {
				wantActivities = 2
			}
			if len(works) != wantWork || len(activities) != wantActivities {
				t.Fatalf("projection contains %d work/%d activities, want %d/%d", len(works), len(activities), wantWork, wantActivities)
			}
			owners, err := view.FindWorkOwners(context.Background(), "src/owned.go")
			if err != nil || (version >= 12 && len(owners) != 1) || (version < 12 && len(owners) != 0) {
				t.Fatalf("legacy ownership = %#v, error = %v", owners, err)
			}
			if _, _, err := view.GetWork(context.Background(), "missing"); !errors.Is(err, ErrNotFound) {
				t.Fatalf("missing work = %v", err)
			}
			if _, err := view.GetExecutionActivity(context.Background(), "missing"); !errors.Is(err, ErrNotFound) {
				t.Fatalf("missing activity = %v", err)
			}
			changes, err := view.ListCoordinationChanges(context.Background(), 0, 100)
			if err != nil {
				t.Fatal(err)
			}
			revision, err := view.CoordinationRevision(context.Background())
			if err != nil {
				t.Fatal(err)
			}
			if version == 3 && (len(changes) != 0 || revision != 100) {
				t.Fatalf("legacy view must retain the event watermark without projecting Run events: %#v, revision %d", changes, revision)
			}
			if err := view.Close(); err != nil {
				t.Fatal(err)
			}
			assertPreservedDatabaseContents(t, db, before)
			var afterVersion int
			if err := db.QueryRow(`SELECT value FROM metadata WHERE key = 'schema_version'`).Scan(&afterVersion); err != nil {
				t.Fatal(err)
			}
			if afterVersion != version || len(databaseTables(t, db)) != len(before) {
				t.Fatalf("read-only view migrated v%d store to v%d", version, afterVersion)
			}
		})
	}
}

func TestViewDoesNotMaterializeMissingDatabase(t *testing.T) {
	directory := filepath.Join(t.TempDir(), "missing")
	view, err := OpenView(context.Background(), filepath.Join(directory, "run-control.sqlite"))
	if view != nil || !errors.Is(err, ErrNotFound) {
		t.Fatalf("missing View = %v, err = %v", view, err)
	}
	if _, err := os.Stat(directory); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("read-only view materialized its directory: %v", err)
	}
}

package runcontrol

import (
	"context"
	"database/sql"
	"errors"
	"path/filepath"
	"strconv"
	"sync"
	"testing"
)

func openTestStore(t *testing.T, databasePath string, options ...OpenOption) *Store {
	t.Helper()
	store, err := Open(context.Background(), databasePath, options...)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := store.Close(); err != nil {
			t.Errorf("close shared store: %v", err)
		}
	})
	return store
}

func TestSQLiteDurabilityPragmas(t *testing.T) {
	store := openTestStore(t, filepath.Join(t.TempDir(), "run-control.sqlite"))
	for pragma, want := range map[string]int{"foreign_keys": 1, "synchronous": 2, "busy_timeout": sqliteBusyTimeoutMS} {
		var got int
		if err := store.db.QueryRow("PRAGMA " + pragma).Scan(&got); err != nil {
			t.Fatal(err)
		}
		if got != want {
			t.Errorf("PRAGMA %s = %d, want %d", pragma, got, want)
		}
	}
	var journal string
	if err := store.db.QueryRow("PRAGMA journal_mode").Scan(&journal); err != nil {
		t.Fatal(err)
	}
	if journal != "wal" {
		t.Fatalf("journal mode = %q, want wal", journal)
	}
}

func TestOpenRejectsUnsupportedSchemaWithoutChangingRecords(t *testing.T) {
	for _, version := range []string{"0", "1", "2", strconv.Itoa(schemaVersion + 1), "999", "invalid", ""} {
		t.Run("version_"+version, func(t *testing.T) {
			databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
			db, err := sql.Open("sqlite", databasePath)
			if err != nil {
				t.Fatal(err)
			}
			t.Cleanup(func() { _ = db.Close() })
			if _, err := db.Exec(`CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)`); err != nil {
				t.Fatal(err)
			}
			if version != "" {
				if _, err := db.Exec(`INSERT INTO metadata VALUES ('schema_version', ?)`, version); err != nil {
					t.Fatal(err)
				}
			}
			if _, err := db.Exec(`INSERT INTO metadata VALUES ('user_data', 'keep')`); err != nil {
				t.Fatal(err)
			}
			before := databaseContents(t, db)
			store, err := Open(context.Background(), databasePath)
			if store != nil {
				_ = store.Close()
				t.Error("unsupported schema returned a store")
			}
			if !errors.Is(err, ErrUnsupportedSchema) {
				t.Fatalf("Open = %v, want ErrUnsupportedSchema", err)
			}
			assertPreservedDatabaseContents(t, db, before)
			if got := len(databaseTables(t, db)); got != 1 {
				t.Errorf("unsupported open added tables: %d", got)
			}
		})
	}
}

func TestConcurrentOpenInitializesOneSharedStore(t *testing.T) {
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	start := make(chan struct{})
	errs := make(chan error, 6)
	var workers sync.WaitGroup
	for i := 0; i < cap(errs); i++ {
		workers.Add(1)
		go func() {
			defer workers.Done()
			<-start
			store, err := Open(context.Background(), databasePath)
			if err == nil {
				err = store.Close()
			}
			errs <- err
		}()
	}
	close(start)
	workers.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			t.Errorf("concurrent open/close: %v", err)
		}
	}
	store := openTestStore(t, databasePath)
	if count := len(databaseTables(t, store.db)); count != 6 {
		t.Fatalf("shared table count = %d, want 6", count)
	}
}

func TestLegacyOwnerOptionIsInert(t *testing.T) {
	databasePath := filepath.Join(t.TempDir(), "run-control.sqlite")
	first := openTestStore(t, databasePath, WithOwnerEpoch("same-historical-owner"))
	second := openTestStore(t, databasePath, WithOwnerEpoch("same-historical-owner"))
	if err := first.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := second.ListWork(context.Background(), ListWorkParams{}); err != nil {
		t.Fatal(err)
	}
	if _, err := Open(context.Background(), databasePath, WithOwnerEpoch(" ")); !errors.Is(err, ErrInvalidArgument) {
		t.Fatalf("blank compatibility option = %v, want invalid argument", err)
	}
}

package store

import (
	"bytes"
	"context"
	"database/sql"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
)

func TestIncompatibleStoreGuidancePreservesExactDatabase(t *testing.T) {
	for _, kind := range []string{"empty", "legacy", "incomplete"} {
		t.Run(kind, func(t *testing.T) {
			paths := testPaths(t)
			if err := os.MkdirAll(filepath.Dir(paths.DatabasePath), 0o755); err != nil {
				t.Fatal(err)
			}
			if kind == "empty" {
				if err := os.WriteFile(paths.DatabasePath, nil, 0o644); err != nil {
					t.Fatal(err)
				}
			} else {
				db, err := sql.Open("sqlite", paths.DatabasePath)
				if err != nil {
					t.Fatal(err)
				}
				version := SchemaVersion
				if kind == "legacy" {
					version--
				}
				_, err = db.ExecContext(context.Background(), `CREATE TABLE metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL); INSERT INTO metadata VALUES ('schema_version', ?);`, strconv.Itoa(version))
				closeErr := db.Close()
				if err != nil || closeErr != nil {
					t.Fatalf("fixture: exec=%v close=%v", err, closeErr)
				}
			}
			before, err := os.ReadFile(paths.DatabasePath)
			if err != nil {
				t.Fatal(err)
			}
			_, err = requireCurrentDatabase(paths)
			if err == nil || !strings.Contains(err.Error(), rt.IncompatibleStoreRecovery) || strings.Contains(err.Error(), "remove the database") {
				t.Fatalf("error = %v, want guarded inspection and digest-bound archive guidance", err)
			}
			after, err := os.ReadFile(paths.DatabasePath)
			if err != nil || !bytes.Equal(before, after) {
				t.Fatalf("rejected database changed: err=%v", err)
			}
		})
	}
}

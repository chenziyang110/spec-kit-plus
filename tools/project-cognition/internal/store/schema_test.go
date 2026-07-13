package store

import (
	"context"
	"database/sql"
	"errors"
	"os"
	"reflect"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

func TestSchemaV4RequiredTablesIncludeClaimReconciliation(t *testing.T) {
	want := []string{
		"metadata",
		"generations",
		"evidence",
		"observations",
		"observation_evidence",
		"nodes",
		"node_evidence",
		"edges",
		"edge_evidence",
		"path_index",
		"alias_index",
		"claims",
		"claim_evidence",
		"claim_verifications",
		"claim_transitions",
		"claim_reconciliations",
		"updates",
	}
	if got := RequiredTables(); !reflect.DeepEqual(got, want) {
		t.Fatalf("RequiredTables() = %#v, want %#v", got, want)
	}
}

func TestOpenInitializesSchemaV4WithCurrentClaimEvidenceBasis(t *testing.T) {
	ctx := context.Background()
	paths := testPaths(t)
	st, err := Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()

	meta, err := st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if meta["schema_version"] != "4" {
		t.Fatalf("schema_version = %q, want 4", meta["schema_version"])
	}

	for _, table := range RequiredTables() {
		exists, err := tableExists(ctx, st.DB(), table)
		if err != nil {
			t.Fatal(err)
		}
		if !exists {
			t.Fatalf("required table %s was not created", table)
		}
	}

	removed := []string{
		"conflicts",
		"conflict_claims",
		"symbol_index",
		"entrypoint_index",
		"test_index",
		"slice_members",
		"query_examples",
		"claim_fts",
		"observation_fts",
		"alias_fts",
	}
	for _, table := range removed {
		exists, err := tableExists(ctx, st.DB(), table)
		if err != nil {
			t.Fatal(err)
		}
		if exists {
			t.Fatalf("removed table %s should not exist in schema v4", table)
		}
	}

	columns, err := tableColumns(ctx, st.DB(), "claim_evidence")
	if err != nil {
		t.Fatal(err)
	}
	for _, column := range []string{"reconciliation_id", "basis_state"} {
		if !columns[column] {
			t.Fatalf("claim_evidence is missing schema-v4 column %q", column)
		}
	}
}

func TestOpenRejectsSchemaV2WithoutMigrationOrArchive(t *testing.T) {
	ctx := context.Background()
	paths := testPaths(t)
	st, err := Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-v2")); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	for _, table := range []string{"claim_transitions", "claim_verifications", "claim_evidence", "claims"} {
		if _, err := db.ExecContext(ctx, `DROP TABLE `+table); err != nil {
			_ = db.Close()
			t.Fatal(err)
		}
	}
	if _, err := db.ExecContext(ctx, `UPDATE metadata SET value_json = '2' WHERE key = 'schema_version'`); err != nil {
		_ = db.Close()
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	st, err = Open(paths)
	if err == nil {
		_ = st.Close()
		t.Fatal("Open() succeeded for schema v2, want current-schema-only rejection")
	}
	if !strings.Contains(err.Error(), "schema_version 2") || !strings.Contains(err.Error(), "requires 4") {
		t.Fatalf("Open() error = %v, want explicit current schema requirement", err)
	}

	db, err = sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	var version string
	if err := db.QueryRowContext(ctx, `SELECT value_json FROM metadata WHERE key = 'schema_version'`).Scan(&version); err != nil {
		t.Fatal(err)
	}
	if version != "2" {
		t.Fatalf("schema_version = %q, want untouched v2 database", version)
	}
	exists, err := tableExists(ctx, db, "claims")
	if err != nil {
		t.Fatal(err)
	}
	if exists {
		t.Fatal("claims table was recreated, want no implicit v2 migration")
	}
	if _, err := os.Stat(paths.DatabasePath + ".legacy"); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("legacy archive stat error = %v, want no implicit archive", err)
	}
}

func TestOpenRejectsLegacyMetadataValueColumn(t *testing.T) {
	paths := testPaths(t)
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	for _, statement := range []string{
		`CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)`,
		`INSERT INTO metadata(key, value) VALUES('schema_version', '3')`,
	} {
		if _, err := db.Exec(statement); err != nil {
			_ = db.Close()
			t.Fatal(err)
		}
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	_, err = Open(paths)
	if err == nil || !strings.Contains(err.Error(), "no value_json column") {
		t.Fatalf("Open() error = %v, want current metadata column rejection", err)
	}
	if _, err := os.Stat(paths.DatabasePath + ".legacy"); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("legacy archive stat error = %v, want old database untouched", err)
	}
}

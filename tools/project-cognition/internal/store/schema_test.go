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

func TestSchemaV3RequiredTablesIncludeTypedClaimLifecycle(t *testing.T) {
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
		"updates",
	}
	if got := RequiredTables(); !reflect.DeepEqual(got, want) {
		t.Fatalf("RequiredTables() = %#v, want %#v", got, want)
	}
}

func TestOpenInitializesSchemaV3WithTypedClaimLifecycle(t *testing.T) {
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
	if meta["schema_version"] != "3" {
		t.Fatalf("schema_version = %q, want 3", meta["schema_version"])
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
			t.Fatalf("removed table %s should not exist in schema v3", table)
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
	if !strings.Contains(err.Error(), "schema_version 2") || !strings.Contains(err.Error(), "requires 3") {
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

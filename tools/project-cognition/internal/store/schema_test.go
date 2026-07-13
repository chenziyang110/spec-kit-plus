package store

import (
	"context"
	"database/sql"
	"os"
	"reflect"
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

func TestOpenArchivesOutdatedDatabaseBeforeSchemaV3Init(t *testing.T) {
	ctx := context.Background()
	paths := testPaths(t)
	st, err := Open(paths)
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
	if _, err := db.ExecContext(ctx, `CREATE TABLE claims(id TEXT PRIMARY KEY)`); err != nil {
		_ = db.Close()
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx, `UPDATE metadata SET value_json = '1' WHERE key = 'schema_version'`); err != nil {
		_ = db.Close()
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	st, err = Open(paths)
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
	exists, err := tableExists(ctx, st.DB(), "claims")
	if err != nil {
		t.Fatal(err)
	}
	if !exists {
		t.Fatal("typed claims table should exist after outdated database replacement")
	}
	if _, err := os.Stat(paths.DatabasePath + ".legacy"); err != nil {
		t.Fatalf("legacy archive stat error = %v, want archived database", err)
	}
}

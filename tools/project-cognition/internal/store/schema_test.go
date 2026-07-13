package store

import (
	"context"
	"database/sql"
	"errors"
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

func TestOpenMigratesSchemaV2ToV3WithoutArchivingGraphData(t *testing.T) {
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
	if _, err := db.ExecContext(ctx, `INSERT OR REPLACE INTO metadata(key, value_json, updated_at) VALUES('migration_sentinel', 'preserved', '2026-07-13T00:00:00Z')`); err != nil {
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
		t.Fatal("typed claims table should exist after v2 migration")
	}
	meta, err = st.Metadata(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if meta["migration_sentinel"] != "preserved" {
		t.Fatalf("migration_sentinel = %q, want preserved", meta["migration_sentinel"])
	}
	var nodeCount int
	if err := st.DB().QueryRowContext(ctx, `SELECT COUNT(*) FROM nodes WHERE generation_id = 'GEN-v2'`).Scan(&nodeCount); err != nil {
		t.Fatal(err)
	}
	if nodeCount == 0 {
		t.Fatal("v2 graph data was not preserved")
	}
	if _, err := os.Stat(paths.DatabasePath + ".legacy"); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("legacy archive stat error = %v, want no archive during additive migration", err)
	}
}

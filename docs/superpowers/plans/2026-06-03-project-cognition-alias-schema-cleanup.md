# Project Cognition Alias Schema Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship project-cognition schema v2 with a smaller truthful SQLite surface and a required `alias_index` that powers alias-first lexicon and query planning.

**Architecture:** Keep implemented graph storage in SQLite, remove unused semantic tables from the default schema, and make aliases a produced/imported graph artifact instead of a lexicon-time reconstruction. Treat v1 databases as diagnostic/inspect-only, while `build-from-scan` archives v1 and rebuilds a clean v2 database before import.

**Tech Stack:** Go project-cognition runtime, `modernc.org/sqlite`, SQLite schema/version metadata, Python pytest template and integration tests

---

## File Responsibility Map

- `tools/project-cognition/internal/store/schema.go`: Own schema version, schema DDL, required table list, and required columns.
- `tools/project-cognition/internal/store/store.go`: Own DB open compatibility, metadata helpers, active concept candidate rows, update closure, and workflow path adoption.
- `tools/project-cognition/internal/store/import.go`: Own generation import types, reference validation, inserts, active-generation cleanup, and identity snapshots.
- `tools/project-cognition/internal/build/build.go`: Own build-from-scan orchestration and v1 DB replacement before opening the store.
- `tools/project-cognition/internal/build/aliases.go`: Own alias derivation from scan artifacts and stable alias identity generation.
- `tools/project-cognition/internal/query/lexicon.go`: Own lexicon output and candidate ranking from stored alias rows.
- `tools/project-cognition/internal/validation/build.go`: Own build readiness checks, including schema v2 and brownfield alias coverage.
- `tools/project-cognition/internal/update/state.go`: Continue recording update closure with node IDs and empty claim/slice closures until those tables return in a later schema.
- `tests/project_cognition_fake.py` and embedded test DB builders: Keep test fake schema aligned with schema v2.
- `templates/commands/**`, `templates/command-partials/common/**`, `templates/passive-skills/**`, `README.md`, and `PROJECT-HANDBOOK.md`: Carry the alias-first and schema-v2 guidance to generated projects and docs.

### Task 1: Shrink Store Schema to v2

**Files:**
- Create: `tools/project-cognition/internal/store/schema_test.go`
- Modify: `tools/project-cognition/internal/store/schema.go`
- Modify: `tools/project-cognition/internal/store/import.go`
- Modify: `tools/project-cognition/internal/store/store.go`
- Modify: `tools/project-cognition/internal/store/update_test.go`
- Modify: `tools/project-cognition/internal/update/state_test.go`
- Modify: `tools/project-cognition/internal/validation/build.go`
- Test: `tools/project-cognition/internal/store/schema_test.go`
- Test: `tools/project-cognition/internal/store/update_test.go`
- Test: `tools/project-cognition/internal/update/state_test.go`

- [ ] **Step 1: Write failing schema-v2 tests**

Create `tools/project-cognition/internal/store/schema_test.go`:

```go
package store

import (
	"context"
	"reflect"
	"testing"
)

func TestSchemaV2RequiredTablesAreCurrentRuntimeSurface(t *testing.T) {
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
		"updates",
	}
	if got := RequiredTables(); !reflect.DeepEqual(got, want) {
		t.Fatalf("RequiredTables() = %#v, want %#v", got, want)
	}
}

func TestOpenInitializesSchemaV2WithoutRemovedTables(t *testing.T) {
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
	if meta["schema_version"] != "2" {
		t.Fatalf("schema_version = %q, want 2", meta["schema_version"])
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
		"claims",
		"claim_evidence",
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
			t.Fatalf("removed table %s should not exist in schema v2", table)
		}
	}
}
```

- [ ] **Step 2: Run the focused store schema tests and confirm failure**

Run from `tools/project-cognition`:

```powershell
go test ./internal/store -run "TestSchemaV2RequiredTablesAreCurrentRuntimeSurface|TestOpenInitializesSchemaV2WithoutRemovedTables" -count=1
```

Expected: FAIL because `SchemaVersion` is still `1` and removed v1 tables are still required and created.

- [ ] **Step 3: Update `schema.go` to schema v2**

In `tools/project-cognition/internal/store/schema.go`, change:

```go
const SchemaVersion = 2
```

Delete the DDL blocks and indexes for these tables from `schemaSQL`:

```text
claims
claim_evidence
conflicts
conflict_claims
symbol_index
entrypoint_index
test_index
slice_members
query_examples
claim_fts
observation_fts
alias_fts
```

Keep the `updates` table with the existing JSON columns:

```sql
CREATE TABLE IF NOT EXISTS updates (
	id TEXT PRIMARY KEY,
	generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
	trigger TEXT NOT NULL,
	changed_paths_json TEXT NOT NULL,
	affected_nodes_json TEXT NOT NULL,
	affected_claims_json TEXT NOT NULL,
	affected_slices_json TEXT NOT NULL,
	result_state TEXT NOT NULL,
	completed_at TEXT NOT NULL,
	attrs_json TEXT NOT NULL DEFAULT '{}'
);
```

Replace `RequiredTables()` with:

```go
func RequiredTables() []string {
	return []string{
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
		"updates",
	}
}
```

Remove the matching entries for removed tables from `RequiredTableColumns()`.

- [ ] **Step 4: Remove schema-v2-invalid imports and closure queries**

In `tools/project-cognition/internal/store/import.go`, remove these fields and types:

```go
Claims       []ClaimImport
SliceMembers []SliceMemberImport
```

Delete the claim insert loop, slice-member insert loop, claim evidence validation loop, and these cleanup statements from `deleteGenerationData()`:

```go
`DELETE FROM claim_evidence WHERE claim_id IN (SELECT id FROM claims WHERE generation_id = ?)`,
`DELETE FROM conflict_claims WHERE conflict_id IN (SELECT id FROM conflicts WHERE generation_id = ?)`,
`DELETE FROM query_examples WHERE generation_id = ?`,
`DELETE FROM slice_members WHERE generation_id = ?`,
`DELETE FROM test_index WHERE generation_id = ?`,
`DELETE FROM entrypoint_index WHERE generation_id = ?`,
`DELETE FROM symbol_index WHERE generation_id = ?`,
`DELETE FROM conflicts WHERE generation_id = ?`,
`DELETE FROM claims WHERE generation_id = ?`,
```

In `tools/project-cognition/internal/store/store.go`, replace `AffectedClosureForPaths()` with the node-only current-schema closure:

```go
func (s *Store) AffectedClosureForPaths(ctx context.Context, paths []string) (AffectedClosure, error) {
	nodes, err := s.NodesForPaths(ctx, paths)
	if err != nil {
		return AffectedClosure{}, err
	}
	return AffectedClosure{
		NodeIDs:  uniqueSorted(nodeIDsFromMaps(nodes)),
		ClaimIDs: []string{},
		SliceIDs: []string{},
	}, nil
}
```

Delete `claimIDsForSubjects()` and `sliceIDsForObjects()` from `store.go`.

In `tools/project-cognition/internal/validation/build.go`, replace `graphPathTableChecks()` with:

```go
func graphPathTableChecks() []struct {
	table  string
	column string
} {
	return []struct {
		table  string
		column string
	}{
		{table: "path_index", column: "path"},
		{table: "evidence", column: "source_path"},
	}
}
```

- [ ] **Step 5: Update tests that intentionally used removed claim/slice tables**

In `tools/project-cognition/internal/store/update_test.go`, rename and rewrite `TestAffectedClosureForPathsReturnsNodesClaimsAndSlices`:

```go
func TestAffectedClosureForPathsReturnsNodesOnlyInSchemaV2(t *testing.T) {
	st := openImportTestStore(t)
	defer st.Close()
	ctx := context.Background()
	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-closure")); err != nil {
		t.Fatal(err)
	}

	closure, err := st.AffectedClosureForPaths(ctx, []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	if !containsString(closure.NodeIDs, "N-app") {
		t.Fatalf("closure = %#v, want N-app", closure)
	}
	if len(closure.ClaimIDs) != 0 {
		t.Fatalf("closure.ClaimIDs = %#v, want empty until claim tables return", closure.ClaimIDs)
	}
	if len(closure.SliceIDs) != 0 {
		t.Fatalf("closure.SliceIDs = %#v, want empty until slice tables return", closure.SliceIDs)
	}
}
```

In `tools/project-cognition/internal/update/state_test.go`, remove `Claims:` and `SliceMembers:` from `seedRuntimeGeneration()`. Update `TestRunUpdateRecordsAffectedClosure` to assert empty claim and slice arrays:

```go
if jsonArrayContains(t, claimsJSON, "claim:app") {
	t.Fatalf("affected_claims_json = %s, want no schema-v2 claim closure", claimsJSON)
}
if jsonArrayContains(t, slicesJSON, "slice:runtime") {
	t.Fatalf("affected_slices_json = %s, want no schema-v2 slice closure", slicesJSON)
}
```

- [ ] **Step 6: Run focused tests**

Run from `tools/project-cognition`:

```powershell
go test ./internal/store ./internal/update ./internal/validation -count=1
```

Expected: PASS after references to removed tables are gone from runtime paths covered by these packages.

- [ ] **Step 7: Commit schema-v2 shrink**

Run:

```powershell
git add tools/project-cognition/internal/store/schema.go tools/project-cognition/internal/store/schema_test.go tools/project-cognition/internal/store/import.go tools/project-cognition/internal/store/store.go tools/project-cognition/internal/store/update_test.go tools/project-cognition/internal/update/state_test.go tools/project-cognition/internal/validation/build.go
git commit -m "feat: shrink project cognition schema to v2"
```

### Task 2: Archive v1 Databases During build-from-scan

**Files:**
- Modify: `tools/project-cognition/internal/store/store.go`
- Modify: `tools/project-cognition/internal/build/build.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`
- Test: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Write a failing CLI test for v1 rebuild behavior**

Add this test near the existing build-from-scan tests in `tools/project-cognition/internal/cli/cli_test.go`:

```go
func TestBuildFromScanArchivesV1DatabaseBeforeCreatingV2(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	oldWD := mustChdir(t, root)
	defer oldWD()

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(paths.DatabasePath), 0o755); err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := db.Exec(`
CREATE TABLE metadata(key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE legacy_marker(id TEXT PRIMARY KEY);
INSERT INTO metadata(key, value_json, updated_at) VALUES('schema_version', '1', '2026-06-03T00:00:00Z');
`); err != nil {
		_ = db.Close()
		t.Fatal(err)
	}
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"build-from-scan", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}

	payload := decodeJSONMap(t, stdout.String())
	if payload["legacy_runtime_replaced"] != true {
		t.Fatalf("legacy_runtime_replaced = %#v, want true", payload["legacy_runtime_replaced"])
	}

	db, err = sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	exists, err := tableExistsForTest(db, "legacy_marker")
	if err != nil {
		t.Fatal(err)
	}
	if exists {
		t.Fatal("legacy_marker remained in rebuilt v2 database")
	}
	var raw string
	if err := db.QueryRow(`SELECT value_json FROM metadata WHERE key = 'schema_version'`).Scan(&raw); err != nil {
		t.Fatal(err)
	}
	if strings.Trim(raw, `"`) != "2" {
		t.Fatalf("schema_version = %q, want 2", raw)
	}
	if _, err := os.Stat(paths.DatabasePath + ".legacy"); err != nil {
		t.Fatalf("legacy archive missing: %v", err)
	}
}
```

If `tableExistsForTest` does not exist in `cli_test.go`, add:

```go
func tableExistsForTest(db *sql.DB, name string) (bool, error) {
	var got string
	err := db.QueryRow(`SELECT name FROM sqlite_master WHERE type='table' AND name = ?`, name).Scan(&got)
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	return err == nil, err
}
```

- [ ] **Step 2: Run the test and confirm failure**

Run from `tools/project-cognition`:

```powershell
go test ./internal/cli -run TestBuildFromScanArchivesV1DatabaseBeforeCreatingV2 -count=1
```

Expected: FAIL because `build-from-scan` does not yet archive a readable database whose metadata says `schema_version=1`.

- [ ] **Step 3: Add store helpers for metadata schema version and outdated replacement**

In `tools/project-cognition/internal/store/store.go`, add `strconv` to imports and add:

```go
func ExistingDatabaseSchemaVersion(paths rt.Paths) (int, bool, error) {
	info, err := os.Stat(paths.DatabasePath)
	if errors.Is(err, os.ErrNotExist) {
		return 0, false, nil
	}
	if err != nil {
		return 0, false, fmt.Errorf("stat project-cognition.db: %w", err)
	}
	if info.Size() == 0 {
		return 0, true, nil
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		return 0, true, fmt.Errorf("open sqlite for schema version check: %w", err)
	}
	defer db.Close()
	if err := db.PingContext(context.Background()); err != nil {
		return 0, true, fmt.Errorf("open sqlite for schema version check: %w", err)
	}
	valueColumn, err := metadataValueColumn(context.Background(), db)
	if err != nil {
		return 0, true, nil
	}
	var raw string
	err = db.QueryRowContext(context.Background(), `SELECT `+valueColumn+` FROM metadata WHERE key = 'schema_version'`).Scan(&raw)
	if errors.Is(err, sql.ErrNoRows) {
		return 0, true, nil
	}
	if err != nil {
		return 0, true, fmt.Errorf("read project-cognition.db metadata.schema_version: %w", err)
	}
	version, err := strconv.Atoi(strings.TrimSpace(decodeMetadataValue(raw)))
	if err != nil {
		return 0, true, nil
	}
	return version, true, nil
}

func ReplaceOutdatedDatabase(paths rt.Paths) (bool, error) {
	version, exists, err := ExistingDatabaseSchemaVersion(paths)
	if err != nil {
		return false, err
	}
	if !exists || version >= SchemaVersion {
		return false, nil
	}
	archivePath, err := archiveDatabasePath(paths.DatabasePath)
	if err != nil {
		return false, err
	}
	if err := os.Rename(paths.DatabasePath, archivePath); err != nil {
		return false, fmt.Errorf("archive outdated project-cognition.db: %w", err)
	}
	return true, nil
}
```

- [ ] **Step 4: Call outdated replacement before `store.Open()` in build**

In `tools/project-cognition/internal/build/build.go`, after `ReplaceIncompatibleDatabase(paths)` and before `store.Open(paths)`, add:

```go
replacedOutdatedDB, err := store.ReplaceOutdatedDatabase(paths)
if err != nil {
	payload.Errors = append(payload.Errors, fmt.Sprintf("recover outdated graph store: %v", err))
	return payload, err
}
if replacedOutdatedDB {
	payload.LegacyRuntimeReplaced = true
}
```

- [ ] **Step 5: Run the focused test**

Run from `tools/project-cognition`:

```powershell
go test ./internal/cli -run TestBuildFromScanArchivesV1DatabaseBeforeCreatingV2 -count=1
```

Expected: PASS.

- [ ] **Step 6: Commit v1 rebuild behavior**

Run:

```powershell
git add tools/project-cognition/internal/store/store.go tools/project-cognition/internal/build/build.go tools/project-cognition/internal/cli/cli_test.go
git commit -m "feat: rebuild outdated cognition databases"
```

### Task 3: Add Alias Import and Store Read Model

**Files:**
- Modify: `tools/project-cognition/internal/store/import.go`
- Modify: `tools/project-cognition/internal/store/store.go`
- Modify: `tools/project-cognition/internal/store/import_test.go`
- Modify: `tools/project-cognition/internal/store/schema.go`
- Test: `tools/project-cognition/internal/store/import_test.go`

- [ ] **Step 1: Write failing alias import tests**

Add to `tools/project-cognition/internal/store/import_test.go`:

```go
func TestImportGenerationStoresAliasIndexRows(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	input := validImportInput("GEN-alias")
	input.Aliases = []AliasImport{{
		ID:              "ALIAS-app",
		Alias:           "App UI",
		NormalizedAlias: "app ui",
		TargetType:      "node",
		TargetID:        "N-app",
		Language:        "en",
		Source:          "scan_alias",
		Confidence:      "verified",
		EvidenceID:      "E-001",
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	rows, err := st.ActiveConceptCandidateRows(ctx, 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 1 {
		t.Fatalf("rows = %#v, want one row", rows)
	}
	if !conceptAliasContains(rows[0].Aliases, "App UI", "scan_alias") {
		t.Fatalf("Aliases = %#v, want App UI scan_alias", rows[0].Aliases)
	}
}

func TestImportGenerationRejectsInvalidAliasReferences(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	tests := []struct {
		name    string
		alias   AliasImport
		wantErr string
	}{
		{
			name: "missing node",
			alias: AliasImport{
				ID:              "ALIAS-missing-node",
				Alias:           "Missing",
				NormalizedAlias: "missing",
				TargetType:      "node",
				TargetID:        "N-missing",
				Language:        "en",
				Source:          "scan_alias",
				Confidence:      "verified",
			},
			wantErr: "references missing node N-missing",
		},
		{
			name: "missing evidence",
			alias: AliasImport{
				ID:              "ALIAS-missing-evidence",
				Alias:           "App",
				NormalizedAlias: "app",
				TargetType:      "node",
				TargetID:        "N-app",
				Language:        "en",
				Source:          "scan_alias",
				Confidence:      "verified",
				EvidenceID:      "E-missing",
			},
			wantErr: "references missing evidence E-missing",
		},
		{
			name: "empty normalized alias",
			alias: AliasImport{
				ID:         "ALIAS-empty",
				Alias:      "App",
				TargetType: "node",
				TargetID:   "N-app",
				Language:   "en",
				Source:     "scan_alias",
				Confidence: "verified",
			},
			wantErr: "normalized_alias is required",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			input := validImportInput("GEN-" + tt.name)
			input.Aliases = []AliasImport{tt.alias}
			_, err := st.ImportGeneration(ctx, input)
			if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
				t.Fatalf("err = %v, want %q", err, tt.wantErr)
			}
		})
	}
}

func conceptAliasContains(rows []ConceptAliasRow, alias string, source string) bool {
	for _, row := range rows {
		if row.Alias == alias && row.Source == source {
			return true
		}
	}
	return false
}
```

- [ ] **Step 2: Run the focused alias import tests and confirm failure**

Run from `tools/project-cognition`:

```powershell
go test ./internal/store -run "TestImportGenerationStoresAliasIndexRows|TestImportGenerationRejectsInvalidAliasReferences" -count=1
```

Expected: FAIL because `ImportInput.Aliases`, `AliasImport`, and candidate row alias loading do not exist.

- [ ] **Step 3: Add alias import types and candidate row aliases**

In `tools/project-cognition/internal/store/import.go`, add:

```go
type AliasImport struct {
	ID              string
	Alias           string
	NormalizedAlias string
	TargetType      string
	TargetID        string
	Language        string
	Source          string
	Confidence      string
	EvidenceID      string
}
```

Add to `ImportInput`:

```go
Aliases []AliasImport
```

In `tools/project-cognition/internal/store/store.go`, add:

```go
type ConceptAliasRow struct {
	Alias           string
	NormalizedAlias string
	Source          string
	Confidence      string
	EvidenceID      string
}
```

Add to `ConceptCandidateRow`:

```go
Aliases []ConceptAliasRow
```

- [ ] **Step 4: Validate and insert aliases during import**

In `validateImportReferences()`, after path index validation, add:

```go
for _, alias := range input.Aliases {
	rowID := strings.TrimSpace(alias.ID)
	if rowID == "" {
		rowID = strings.TrimSpace(alias.Alias)
	}
	if strings.TrimSpace(alias.NormalizedAlias) == "" {
		return fmt.Errorf("alias_index %s normalized_alias is required", rowID)
	}
	if strings.TrimSpace(alias.TargetType) != "node" {
		return fmt.Errorf("alias_index %s target_type %q is not supported", rowID, alias.TargetType)
	}
	if !nodeIDs[alias.TargetID] {
		return fmt.Errorf("alias_index %s references missing node %s", rowID, alias.TargetID)
	}
	if alias.EvidenceID != "" {
		if err := validateImportedEvidenceID("alias_index", rowID, alias.EvidenceID, evidenceIDs); err != nil {
			return err
		}
	}
}
```

In `ImportGeneration()`, after the `path_index` loop and before publishing the generation, add:

```go
for _, alias := range input.Aliases {
	language := defaultString(alias.Language, "unknown")
	source := defaultString(alias.Source, "scan_alias")
	confidence := defaultString(alias.Confidence, "medium")
	if _, err := tx.ExecContext(ctx, `INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, alias.ID, input.GenerationID, alias.Alias, alias.NormalizedAlias, alias.TargetType, alias.TargetID, language, source, confidence, alias.EvidenceID); err != nil {
		return "", fmt.Errorf("insert alias_index %s: %w", alias.ID, err)
	}
}
```

In `deleteGenerationData()`, keep:

```go
`DELETE FROM alias_index WHERE generation_id = ?`,
```

before path, node, and evidence deletes.

- [ ] **Step 5: Add alias uniqueness to schema v2**

In `tools/project-cognition/internal/store/schema.go`, after existing alias indexes, add:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_alias_identity ON alias_index(generation_id, target_type, target_id, normalized_alias, source);
```

- [ ] **Step 6: Load aliases into active candidate rows**

In `activeConceptCandidateRows()` in `tools/project-cognition/internal/store/store.go`, after loading `row.Paths`, add:

```go
row.Aliases, err = s.nodeAliasRows(ctx, generationID, row.NodeID)
if err != nil {
	return nil, fmt.Errorf("query active concept candidate aliases for %s: %w", row.NodeID, err)
}
```

Add:

```go
func (s *Store) nodeAliasRows(ctx context.Context, generationID string, nodeID string) ([]ConceptAliasRow, error) {
	rows, err := s.db.QueryContext(ctx, `SELECT alias, normalized_alias, source, confidence, evidence_id FROM alias_index WHERE generation_id = ? AND target_type = 'node' AND target_id = ? ORDER BY source, normalized_alias, id`, generationID, nodeID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := []ConceptAliasRow{}
	seen := map[string]bool{}
	for rows.Next() {
		var row ConceptAliasRow
		if err := rows.Scan(&row.Alias, &row.NormalizedAlias, &row.Source, &row.Confidence, &row.EvidenceID); err != nil {
			return nil, err
		}
		key := row.Source + "\x00" + row.NormalizedAlias
		if strings.TrimSpace(row.Alias) == "" || seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, row)
	}
	return out, rows.Err()
}
```

- [ ] **Step 7: Run alias import tests**

Run from `tools/project-cognition`:

```powershell
go test ./internal/store -run "TestImportGenerationStoresAliasIndexRows|TestImportGenerationRejectsInvalidAliasReferences|TestActiveConceptCandidateRowsDeriveGraphMaterial" -count=1
```

Expected: PASS after updating `TestActiveConceptCandidateRowsDeriveGraphMaterial` to assert imported aliases through `row.Aliases` rather than assuming lexicon derives them later.

- [ ] **Step 8: Commit alias import model**

Run:

```powershell
git add tools/project-cognition/internal/store/import.go tools/project-cognition/internal/store/store.go tools/project-cognition/internal/store/import_test.go tools/project-cognition/internal/store/schema.go
git commit -m "feat: import cognition aliases"
```

### Task 4: Derive alias_index Rows During build-from-scan

**Files:**
- Create: `tools/project-cognition/internal/build/aliases.go`
- Create: `tools/project-cognition/internal/build/aliases_test.go`
- Modify: `tools/project-cognition/internal/build/build.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`
- Test: `tools/project-cognition/internal/build/aliases_test.go`
- Test: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Write failing alias derivation tests**

Create `tools/project-cognition/internal/build/aliases_test.go`:

```go
package build

import (
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
)

func TestAliasImportsDeriveRequiredNodeAliases(t *testing.T) {
	pkg := scanartifacts.Package{
		Nodes: []scanartifacts.NodeRow{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			Paths:       []string{"src/gui/window.tsx"},
			EvidenceIDs: []string{"E-gui"},
			Attrs: map[string]any{
				"aliases":            []any{"GUI", "desktop UI"},
				"domain":             "desktop",
				"owner":              "frontend",
				"workflow":           "install",
				"route":              "gui route",
				"route_hints":        []any{"src/gui"},
				"verification_hints": []any{"npm test -- gui"},
			},
		}},
		Observations: []scanartifacts.ObservationRow{{
			ID:              "OBS-gui",
			ObservationType: "summary",
			Summary:         "GUI Shell owns frame rendering and input dispatch.",
			EvidenceIDs:     []string{"E-gui"},
		}},
	}

	aliases := aliasImports("GEN-alias-test", pkg)
	assertAliasImport(t, aliases, "GUI Shell", "node_title", "E-gui")
	assertAliasImport(t, aliases, "N-gui", "node_id", "")
	assertAliasImport(t, aliases, "capability", "node_type", "")
	assertAliasImport(t, aliases, "desktop UI", "scan_alias", "E-gui")
	assertAliasImport(t, aliases, "window", "path_material", "E-gui")
	assertAliasImport(t, aliases, "GUI", "observation_tag", "E-gui")
	assertNoAliasImport(t, aliases, "GUI Shell owns frame rendering and input dispatch.")
}

func TestAliasImportsDeduplicateByIdentity(t *testing.T) {
	pkg := scanartifacts.Package{
		Nodes: []scanartifacts.NodeRow{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "App",
			Confidence:  "verified",
			Paths:       []string{"src/app.go"},
			EvidenceIDs: []string{"E-app"},
			Attrs:       map[string]any{"aliases": []any{"App", "app"}},
		}},
	}

	aliases := aliasImports("GEN-alias-test", pkg)
	count := 0
	for _, alias := range aliases {
		if alias.TargetID == "N-app" && alias.NormalizedAlias == "app" && alias.Source == "scan_alias" {
			count++
		}
	}
	if count != 1 {
		t.Fatalf("scan_alias app count = %d, want 1 in %#v", count, aliases)
	}
}
```

Add helper functions in the same file:

```go
func assertAliasImport(t *testing.T, aliases []store.AliasImport, alias string, source string, evidenceID string) {
	t.Helper()
	for _, row := range aliases {
		if row.Alias == alias && row.Source == source && row.EvidenceID == evidenceID {
			return
		}
	}
	t.Fatalf("alias %q source %q evidence %q missing from %#v", alias, source, evidenceID, aliases)
}

func assertNoAliasImport(t *testing.T, aliases []store.AliasImport, alias string) {
	t.Helper()
	for _, row := range aliases {
		if row.Alias == alias {
			t.Fatalf("raw alias %q should not be present in %#v", alias, aliases)
		}
	}
}
```

Add the missing import in `aliases_test.go`:

```go
"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
```

- [ ] **Step 2: Run alias derivation tests and confirm failure**

Run from `tools/project-cognition`:

```powershell
go test ./internal/build -run "TestAliasImportsDeriveRequiredNodeAliases|TestAliasImportsDeduplicateByIdentity" -count=1
```

Expected: FAIL because `aliasImports()` does not exist.

- [ ] **Step 3: Implement `aliases.go`**

Create `tools/project-cognition/internal/build/aliases.go` with:

```go
package build

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"path/filepath"
	"sort"
	"strings"
	"unicode"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

type aliasSeed struct {
	alias      string
	targetID   string
	source     string
	confidence string
	evidenceID string
	language   string
}

func aliasImports(generationID string, pkg scanartifacts.Package) []store.AliasImport {
	observationTagsByEvidence := observationTagsByEvidenceID(pkg.Observations)
	merged := map[string]store.AliasImport{}
	for _, node := range pkg.Nodes {
		evidenceID := firstString(node.EvidenceIDs)
		seeds := []aliasSeed{
			{alias: node.Title, targetID: node.ID, source: "node_title", confidence: defaultConfidence(node.Confidence), evidenceID: evidenceID, language: "unknown"},
			{alias: node.ID, targetID: node.ID, source: "node_id", confidence: "high", language: "code"},
			{alias: node.Type, targetID: node.ID, source: "node_type", confidence: "medium", language: "unknown"},
		}
		seeds = append(seeds, attrAliasSeeds(node, evidenceID)...)
		for _, path := range node.Paths {
			for _, value := range pathAliasValues(path) {
				seeds = append(seeds, aliasSeed{alias: value, targetID: node.ID, source: "path_material", confidence: defaultConfidence(node.Confidence), evidenceID: evidenceID, language: "code"})
			}
		}
		for _, evidenceID := range node.EvidenceIDs {
			for _, value := range observationTagsByEvidence[evidenceID] {
				seeds = append(seeds, aliasSeed{alias: value, targetID: node.ID, source: "observation_tag", confidence: "medium", evidenceID: evidenceID, language: "unknown"})
			}
		}
		for _, seed := range seeds {
			row, ok := aliasImportFromSeed(generationID, node.ID, seed)
			if !ok {
				continue
			}
			key := generationID + "\x00" + row.TargetType + "\x00" + row.TargetID + "\x00" + row.NormalizedAlias + "\x00" + row.Source
			if existing, exists := merged[key]; exists {
				merged[key] = strongerAlias(existing, row)
				continue
			}
			merged[key] = row
		}
	}
	out := make([]store.AliasImport, 0, len(merged))
	for _, row := range merged {
		out = append(out, row)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].TargetID != out[j].TargetID {
			return out[i].TargetID < out[j].TargetID
		}
		if out[i].Source != out[j].Source {
			return out[i].Source < out[j].Source
		}
		return out[i].NormalizedAlias < out[j].NormalizedAlias
	})
	return out
}
```

Add these private helpers after `stableAliasID()`:

```go
func attrAliasSeeds(node scanartifacts.NodeRow, evidenceID string) []aliasSeed {
	out := []aliasSeed{}
	for _, value := range attrStrings(node.Attrs, "aliases") {
		out = append(out, aliasSeed{alias: value, targetID: node.ID, source: "scan_alias", confidence: defaultConfidence(node.Confidence), evidenceID: evidenceID, language: "unknown"})
	}
	for _, key := range []string{"domain", "owner", "workflow", "route"} {
		if value := attrString(node.Attrs, key); value != "" {
			out = append(out, aliasSeed{alias: value, targetID: node.ID, source: "node_attr", confidence: "medium", evidenceID: evidenceID, language: "unknown"})
		}
	}
	for _, value := range attrStrings(node.Attrs, "route_hints") {
		out = append(out, aliasSeed{alias: value, targetID: node.ID, source: "route_hint", confidence: "medium", evidenceID: evidenceID, language: "unknown"})
	}
	for _, value := range attrStrings(node.Attrs, "verification_hints") {
		out = append(out, aliasSeed{alias: value, targetID: node.ID, source: "verification_hint", confidence: "medium", evidenceID: evidenceID, language: "unknown"})
	}
	return out
}

func aliasImportFromSeed(generationID string, nodeID string, seed aliasSeed) (store.AliasImport, bool) {
	alias := strings.TrimSpace(seed.alias)
	normalized := normalizeAlias(alias)
	if alias == "" || normalized == "" {
		return store.AliasImport{}, false
	}
	source := defaultString(seed.source, "scan_alias")
	confidence := defaultString(seed.confidence, "medium")
	language := defaultString(seed.language, "unknown")
	return store.AliasImport{
		ID:              stableAliasID(generationID, "node", nodeID, normalized, source),
		Alias:           alias,
		NormalizedAlias: normalized,
		TargetType:      "node",
		TargetID:        nodeID,
		Language:        language,
		Source:          source,
		Confidence:      confidence,
		EvidenceID:      strings.TrimSpace(seed.evidenceID),
	}, true
}

func stableAliasID(generationID string, targetType string, targetID string, normalizedAlias string, source string) string {
	identity := generationID + "\x00" + targetType + "\x00" + targetID + "\x00" + normalizedAlias + "\x00" + source
	hash := sha256.Sum256([]byte(identity))
	return "ALIAS-" + sanitizeIDPart(targetID) + "-" + hex.EncodeToString(hash[:])[:16]
}
```

Use helper implementations that are deterministic and bounded:

```go
func normalizeAlias(value string) string {
	fields := strings.FieldsFunc(strings.ToLower(strings.TrimSpace(value)), func(r rune) bool {
		return !(unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-' || r == '/' || r == '.')
	})
	return strings.Join(fields, " ")
}

func pathAliasValues(path string) []string {
	path = filepath.ToSlash(strings.TrimSpace(path))
	if path == "" || strings.HasPrefix(path, ".specify/") {
		return []string{}
	}
	base := filepath.Base(path)
	ext := filepath.Ext(base)
	stem := strings.TrimSuffix(base, ext)
	parts := strings.FieldsFunc(path, func(r rune) bool {
		return r == '/' || r == '\\' || r == '.' || r == '_' || r == '-'
	})
	return uniqueAliasStrings(append([]string{path, stem}, parts...))
}

func observationTagsByEvidenceID(rows []scanartifacts.ObservationRow) map[string][]string {
	out := map[string][]string{}
	for _, row := range rows {
		tags := boundedObservationTags(row.Summary)
		for _, evidenceID := range row.EvidenceIDs {
			out[evidenceID] = uniqueAliasStrings(append(out[evidenceID], tags...))
		}
	}
	return out
}

func boundedObservationTags(summary string) []string {
	fields := strings.FieldsFunc(summary, func(r rune) bool {
		return !(unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-' || r == '/')
	})
	out := []string{}
	for _, field := range fields {
		field = strings.TrimSpace(field)
		if len([]rune(field)) < 3 || len([]rune(field)) > 40 {
			continue
		}
		if observationStopwords[strings.ToLower(field)] {
			continue
		}
		if hasCodeSignal(field) {
			out = append(out, field)
		}
		if len(out) >= 8 {
			break
		}
	}
	return uniqueAliasStrings(out)
}
```

Add the remaining private helpers in `aliases.go`:

```go
var observationStopwords = map[string]bool{
	"and": true, "the": true, "for": true, "with": true, "from": true, "into": true,
	"owns": true, "owner": true, "observed": true, "summary": true, "uses": true,
}

func hasCodeSignal(value string) bool {
	for _, r := range value {
		if unicode.IsUpper(r) || unicode.IsDigit(r) || r == '_' || r == '-' || r == '/' {
			return true
		}
	}
	return false
}

func attrString(attrs map[string]any, key string) string {
	value, ok := attrs[key]
	if !ok {
		return ""
	}
	switch typed := value.(type) {
	case string:
		return strings.TrimSpace(typed)
	default:
		return strings.TrimSpace(strings.TrimPrefix(strings.TrimSuffix(strings.TrimSpace(toString(typed)), `"`), `"`))
	}
}

func attrStrings(attrs map[string]any, key string) []string {
	value, ok := attrs[key]
	if !ok {
		return []string{}
	}
	switch typed := value.(type) {
	case []any:
		out := make([]string, 0, len(typed))
		for _, item := range typed {
			out = append(out, toString(item))
		}
		return uniqueAliasStrings(out)
	case []string:
		return uniqueAliasStrings(typed)
	case string:
		return []string{typed}
	default:
		return []string{toString(typed)}
	}
}

func toString(value any) string {
	switch typed := value.(type) {
	case string:
		return strings.TrimSpace(typed)
	default:
		return strings.TrimSpace(fmt.Sprint(typed))
	}
}

func uniqueAliasStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	return out
}

func firstString(values []string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}

func defaultConfidence(value string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return "medium"
	}
	return value
}

func strongerAlias(left store.AliasImport, right store.AliasImport) store.AliasImport {
	if confidenceRank(right.Confidence) > confidenceRank(left.Confidence) {
		left.Confidence = right.Confidence
	}
	if strings.TrimSpace(left.EvidenceID) == "" && strings.TrimSpace(right.EvidenceID) != "" {
		left.EvidenceID = right.EvidenceID
	}
	return left
}

func confidenceRank(value string) int {
	switch strings.TrimSpace(value) {
	case "verified":
		return 5
	case "high":
		return 4
	case "medium":
		return 3
	case "low":
		return 2
	case "provisional":
		return 1
	default:
		return 0
	}
}

func defaultString(value string, fallback string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return fallback
	}
	return value
}
```

- [ ] **Step 4: Wire aliases into build import**

In `importInputFromPackage()` in `tools/project-cognition/internal/build/build.go`, create the generation ID once and pass it to alias derivation:

```go
generationID := newGenerationID()
rejections := coverageRejections(pkg)
return store.ImportInput{
	GenerationID: generationID,
	Kind:         rt.BaselineKindBrownfieldFull,
	SourceCommit: firstSourceCommit(pkg.Evidence),
	Evidence:     evidenceImports(pkg.Evidence),
	Nodes:        nodeImports(pkg.Nodes),
	Edges:        edgeImports(pkg.Edges),
	Observations: observationImports(pkg.Observations),
	PathIndex:    pathIndexImports(pkg.Nodes),
	Aliases:      aliasImports(generationID, pkg),
	Rejections:   rejections,
	MergeRecords: []store.MergeRecord{},
}
```

- [ ] **Step 5: Add CLI-level DB assertion**

In `tools/project-cognition/internal/cli/cli_test.go`, add a build-from-scan test:

```go
func TestBuildFromScanCommandWritesAliasIndexRows(t *testing.T) {
	payload := runBuildFromScanCLI(t, "build-from-scan")
	if payload["status"] != "ok" {
		t.Fatalf("status = %#v, payload = %#v", payload["status"], payload)
	}

	paths, err := rt.ResolvePaths(".")
	if err != nil {
		t.Fatal(err)
	}
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()

	var aliasCount int
	if err := db.QueryRow(`SELECT COUNT(*) FROM alias_index WHERE target_type = 'node'`).Scan(&aliasCount); err != nil {
		t.Fatal(err)
	}
	if aliasCount == 0 {
		t.Fatal("alias_index row count = 0, want aliases from build")
	}

	var rawSummaryAliases int
	if err := db.QueryRow(`SELECT COUNT(*) FROM alias_index WHERE alias LIKE '%owns frame rendering and input dispatch%'`).Scan(&rawSummaryAliases); err != nil {
		t.Fatal(err)
	}
	if rawSummaryAliases != 0 {
		t.Fatalf("raw summary aliases = %d, want 0", rawSummaryAliases)
	}
}
```

- [ ] **Step 6: Run focused build tests**

Run from `tools/project-cognition`:

```powershell
go test ./internal/build ./internal/cli -run "TestAliasImports|TestBuildFromScanCommandWritesAliasIndexRows|TestBuildFromScanCommandCreatesRuntime" -count=1
```

Expected: PASS.

- [ ] **Step 7: Commit build alias production**

Run:

```powershell
git add tools/project-cognition/internal/build/aliases.go tools/project-cognition/internal/build/aliases_test.go tools/project-cognition/internal/build/build.go tools/project-cognition/internal/cli/cli_test.go
git commit -m "feat: derive cognition alias index"
```

### Task 5: Read Lexicon Aliases from alias_index

**Files:**
- Modify: `tools/project-cognition/internal/query/lexicon.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`
- Modify: `tools/project-cognition/internal/query/query_test.go`
- Test: `tools/project-cognition/internal/cli/cli_test.go`
- Test: `tools/project-cognition/internal/query/query_test.go`

- [ ] **Step 1: Add a failing lexicon test that proves catalog source is `alias_index`**

In `tools/project-cognition/internal/cli/cli_test.go`, extend `TestLexiconCommandCatalogModeEmitsAliasCatalogAndSemanticContract` after decoding the payload:

```go
first, ok := catalog[0].(map[string]any)
if !ok {
	t.Fatalf("alias catalog entry = %#v", catalog[0])
}
aliases, ok := first["aliases"].([]any)
if !ok {
	t.Fatalf("aliases = %#v", first["aliases"])
}
if !jsonAnySliceContains(aliases, "App") {
	t.Fatalf("aliases = %#v, want App from alias_index", aliases)
}
if jsonAnySliceContains(aliases, "App observed") {
	t.Fatalf("aliases = %#v, should not include raw observation summary", aliases)
}
```

Add helper if absent:

```go
func jsonAnySliceContains(values []any, want string) bool {
	for _, value := range values {
		if text, ok := value.(string); ok && text == want {
			return true
		}
	}
	return false
}
```

- [ ] **Step 2: Run lexicon tests and confirm failure if lexicon still appends raw observations**

Run from `tools/project-cognition`:

```powershell
go test ./internal/cli -run "TestLexiconCommandCatalogModeEmitsAliasCatalogAndSemanticContract|TestLexiconCommandReturnsGraphBackedCandidates" -count=1
```

Expected before implementation: FAIL if raw observation summaries remain in catalog aliases or aliases are not loaded from stored rows.

- [ ] **Step 3: Update `newRankedConceptCandidate()` to use stored aliases**

In `tools/project-cognition/internal/query/lexicon.go`, replace the alias-building portion of `newRankedConceptCandidate()` with:

```go
paths := uniqueStrings(append(append([]string{}, row.Paths...), row.EvidencePaths...))
aliases := aliasStrings(row.Aliases)
```

Keep route and verification hints from attrs:

```go
return rankedConceptCandidate{
	row:               row,
	attrs:             attrs,
	aliases:           uniqueStrings(aliases),
	paths:             paths,
	routeHints:        uniqueStrings(append(attrStrings(attrs, "route_hints"), attrString(attrs, "route"))),
	verificationHints: uniqueStrings(attrStrings(attrs, "verification_hints")),
}
```

Add:

```go
func aliasStrings(rows []store.ConceptAliasRow) []string {
	out := make([]string, 0, len(rows))
	for _, row := range rows {
		out = append(out, row.Alias)
	}
	return uniqueStrings(out)
}
```

Leave `pathMaterial()` in place only if query package tests still call it directly; otherwise delete it after `rg -n "pathMaterial" tools/project-cognition/internal/query`.

- [ ] **Step 4: Ensure catalog exposes evidence tags separately**

In `aliasCatalogForRows()`, keep:

```go
"evidence_summary_tags": candidate.row.ObservationSummaries,
```

Do not append `candidate.row.ObservationSummaries` to `candidate.aliases`.

- [ ] **Step 5: Run lexicon and query tests**

Run from `tools/project-cognition`:

```powershell
go test ./internal/query ./internal/cli -run "TestLexicon|TestQueryCommand" -count=1
```

Expected: PASS with catalog aliases coming from `alias_index`.

- [ ] **Step 6: Commit lexicon read change**

Run:

```powershell
git add tools/project-cognition/internal/query/lexicon.go tools/project-cognition/internal/cli/cli_test.go tools/project-cognition/internal/query/query_test.go
git commit -m "feat: read lexicon aliases from alias index"
```

### Task 6: Validate Brownfield Alias Coverage

**Files:**
- Modify: `tools/project-cognition/internal/validation/build.go`
- Modify: `tools/project-cognition/internal/validation/build_test.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`
- Test: `tools/project-cognition/internal/validation/build_test.go`
- Test: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Write failing validation tests**

Add to `tools/project-cognition/internal/validation/build_test.go`:

```go
func TestValidateBuildBlocksBrownfieldWithoutAliases(t *testing.T) {
	paths := validationTestPaths(t)
	seedQueryReadyDatabase(t, paths)
	db := openValidationDB(t, paths)
	defer db.Close()
	if _, err := db.Exec(`DELETE FROM alias_index`); err != nil {
		t.Fatal(err)
	}

	payload := ValidateBuild(paths)
	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if !containsString(payload.Errors, "active_generation_has_no_alias_rows") {
		t.Fatalf("Errors = %#v, want active_generation_has_no_alias_rows", payload.Errors)
	}
}

func TestValidateBuildBlocksAliasIndexOrphans(t *testing.T) {
	paths := validationTestPaths(t)
	seedQueryReadyDatabase(t, paths)
	db := openValidationDB(t, paths)
	defer db.Close()
	if _, err := db.Exec(`INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id) VALUES('ALIAS-orphan', 'GEN-1', 'Orphan', 'orphan', 'node', 'N-missing', 'en', 'scan_alias', 'verified', '')`); err != nil {
		t.Fatal(err)
	}

	payload := ValidateBuild(paths)
	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if !containsString(payload.Errors, "alias_index_orphan_target_id:N-missing") {
		t.Fatalf("Errors = %#v, want alias orphan target", payload.Errors)
	}
}

func TestValidateBuildAllowsGreenfieldWithoutAliases(t *testing.T) {
	paths := validationTestPaths(t)
	seedGreenfieldEmptyRuntime(t, paths)

	payload := ValidateBuild(paths)
	if payload.Status != "ok" {
		t.Fatalf("payload = %#v, want greenfield ok without aliases", payload)
	}
}
```

If `openValidationDB` does not exist, add:

```go
func openValidationDB(t *testing.T, paths rt.Paths) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite", paths.DatabasePath)
	if err != nil {
		t.Fatal(err)
	}
	return db
}
```

Update `seedQueryReadyDatabase()` in `build_test.go` so the seeded DB includes at least one alias row:

```sql
INSERT INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id)
VALUES('ALIAS-app', 'GEN-1', 'App', 'app', 'node', 'N-app', 'en', 'node_title', 'verified', 'E-1');
```

- [ ] **Step 2: Run validation tests and confirm failure**

Run from `tools/project-cognition`:

```powershell
go test ./internal/validation -run "TestValidateBuildBlocksBrownfieldWithoutAliases|TestValidateBuildBlocksAliasIndexOrphans|TestValidateBuildAllowsGreenfieldWithoutAliases|TestValidateBuildAcceptsQueryReadyDatabase" -count=1
```

Expected: FAIL because `validateGraphStore()` does not yet inspect alias coverage.

- [ ] **Step 3: Add alias coverage validation**

In `tools/project-cognition/internal/validation/build.go`, after `evidenceCount` is loaded, add:

```go
aliasDetails, aliasErrors, err := validateAliasIndex(db, activeGenerationID, greenfieldEmpty)
if err != nil {
	errors = append(errors, err.Error())
} else {
	for key, value := range aliasDetails {
		details[key] = value
	}
	errors = append(errors, aliasErrors...)
}
```

Add:

```go
func validateAliasIndex(db *sql.DB, generationID string, greenfieldEmpty bool) (map[string]any, []string, error) {
	details := map[string]any{}
	errors := []string{}
	aliasCount, err := countGenerationRows(db, "alias_index", generationID)
	if err != nil {
		return details, errors, err
	}
	details["alias_index_count"] = aliasCount
	if greenfieldEmpty {
		return details, errors, nil
	}
	if aliasCount == 0 {
		errors = append(errors, "active_generation_has_no_alias_rows")
	}

	missingNodes, err := stringColumnRows(db, `
SELECT n.id
FROM nodes n
WHERE n.generation_id = ?
AND NOT EXISTS (
	SELECT 1
	FROM alias_index a
	WHERE a.generation_id = n.generation_id
	AND a.target_type = 'node'
	AND a.target_id = n.id
	AND TRIM(a.normalized_alias) <> ''
)
ORDER BY n.id`, generationID)
	if err != nil {
		return details, errors, err
	}
	details["alias_missing_node_count"] = len(missingNodes)
	for _, nodeID := range missingNodes {
		errors = append(errors, "active_generation_node_missing_aliases:"+nodeID)
	}

	orphanTargets, err := stringColumnRows(db, `
SELECT DISTINCT a.target_id
FROM alias_index a
LEFT JOIN nodes n ON n.generation_id = a.generation_id AND n.id = a.target_id
WHERE a.generation_id = ?
AND a.target_type = 'node'
AND n.id IS NULL
ORDER BY a.target_id`, generationID)
	if err != nil {
		return details, errors, err
	}
	for _, targetID := range orphanTargets {
		errors = append(errors, "alias_index_orphan_target_id:"+targetID)
	}

	missingEvidence, err := stringColumnRows(db, `
SELECT DISTINCT a.evidence_id
FROM alias_index a
LEFT JOIN evidence e ON e.generation_id = a.generation_id AND e.id = a.evidence_id
WHERE a.generation_id = ?
AND TRIM(a.evidence_id) <> ''
AND e.id IS NULL
ORDER BY a.evidence_id`, generationID)
	if err != nil {
		return details, errors, err
	}
	for _, evidenceID := range missingEvidence {
		errors = append(errors, "alias_index_missing_evidence_id:"+evidenceID)
	}
	return details, errors, nil
}
```

Add helper:

```go
func stringColumnRows(db *sql.DB, query string, args ...any) ([]string, error) {
	rows, err := db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []string{}
	for rows.Next() {
		var value string
		if err := rows.Scan(&value); err != nil {
			return nil, err
		}
		out = append(out, value)
	}
	return out, rows.Err()
}
```

- [ ] **Step 4: Add a CLI regression for v1 query blocking**

In `tools/project-cognition/internal/cli/cli_test.go`, add:

```go
func TestLexiconBlocksV1DatabaseWithRebuildGuidance(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	oldWD := mustChdir(t, root)
	defer oldWD()

	payload := runBuildFromScanCLI(t, "build-from-scan")
	if payload["status"] != "ok" {
		t.Fatalf("build payload = %#v", payload)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `UPDATE metadata SET value_json = '1' WHERE key = 'schema_version'`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"lexicon", "--intent", "debug", "--mode", "catalog", "--format", "json"}, &stdout, &stderr, "test")
	if code == 0 {
		t.Fatalf("code = 0, want blocked v1 lexicon; stdout=%s", stdout.String())
	}
	if !strings.Contains(stdout.String(), "run_map_scan_build") && !strings.Contains(stdout.String(), "schema_version") {
		t.Fatalf("stdout = %s, want rebuild/schema guidance", stdout.String())
	}
}
```

- [ ] **Step 5: Run validation and CLI tests**

Run from `tools/project-cognition`:

```powershell
go test ./internal/validation ./internal/cli -run "TestValidateBuild|TestLexiconBlocksV1DatabaseWithRebuildGuidance" -count=1
```

Expected: PASS.

- [ ] **Step 6: Commit alias readiness validation**

Run:

```powershell
git add tools/project-cognition/internal/validation/build.go tools/project-cognition/internal/validation/build_test.go tools/project-cognition/internal/cli/cli_test.go
git commit -m "feat: validate cognition alias readiness"
```

### Task 7: Update Guidance, Fakes, and Integration Surfaces

**Files:**
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/planning-context-loading-gradient.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `tests/project_cognition_fake.py`
- Modify: `tests/contract/test_hook_cli_surface.py`
- Modify: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/test_runtime_handbook_contract.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Test: listed pytest files in this task

- [ ] **Step 1: Add failing guidance assertions**

In `tests/test_map_scan_build_template_guidance.py`, add:

```python
def test_map_guidance_documents_schema_v2_alias_readiness() -> None:
    scan_content = _read("templates/commands/map-scan.md").lower()
    build_content = _read("templates/commands/map-build.md").lower()
    shared_context = _read("templates/command-partials/common/context-loading-gradient.md").lower()
    planning_context = _read("templates/command-partials/common/planning-context-loading-gradient.md").lower()

    for content in (scan_content, build_content, shared_context, planning_context):
        assert "schema v2" in content
        assert "alias_index" in content
        assert "alias catalog" in content
        assert "normalize user input" in content
        assert "run map-scan -> map-build" in content or "run sp-map-scan -> sp-map-build" in content

    assert "claims table" not in build_content
    assert "conflicts table" not in build_content
    assert "symbol_index" not in build_content
```

In `tests/test_runtime_handbook_contract.py`, add:

```python
def test_runtime_docs_explain_alias_index_and_v1_rebuild_contract() -> None:
    handbook = _read("PROJECT-HANDBOOK.md").lower()
    readme = _read("README.md").lower()
    for content in (handbook, readme):
        assert "alias_index" in content
        assert "schema v2" in content
        assert "v1" in content
        assert "rebuild" in content
        assert "alias-first" in content
```

- [ ] **Step 2: Run focused guidance tests and confirm failure**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_runtime_handbook_contract.py -q
```

Expected: FAIL until guidance surfaces mention schema v2, `alias_index`, and v1 rebuild behavior.

- [ ] **Step 3: Update map-scan and map-build templates**

In `templates/commands/map-scan.md`, update graph output guidance to say:

```markdown
- Emit alias-ready node material. `nodes[].title`, `nodes[].type`, `nodes[].paths`, and `nodes[].attrs.aliases/domain/owner/workflow/route/route_hints/verification_hints` feed schema v2 `alias_index` during `sp-map-build`.
- Do not write raw observation summaries as aliases. Observations may support bounded observation tags only when tied to graph evidence.
- `.specify/**` and ignored paths must never enter evidence, nodes, observations, path_index, or alias_index.
```

In `templates/commands/map-build.md`, update build readiness guidance to say:

```markdown
- `project-cognition build-from-scan --format json` rebuilds the graph store into schema v2.
- Schema v2 keeps the implemented runtime tables: `metadata`, `generations`, `evidence`, `nodes`, `node_evidence`, `edges`, `edge_evidence`, `observations`, `observation_evidence`, `path_index`, `alias_index`, and `updates`.
- Future semantic tables such as claims, conflicts, symbols, entrypoints, tests, slices, query examples, and FTS tables are not current readiness requirements.
- For brownfield baselines, `alias_index` is required: every active node must have at least one alias row and no alias may point at a missing node or missing non-empty evidence id.
- If validation reports schema v1 or an old broad schema, route the user to `sp-map-scan -> sp-map-build`; build-from-scan archives the v1 DB and creates a clean schema v2 database.
```

- [ ] **Step 4: Update shared cognition guidance**

In both shared context partials, add this paragraph near the lexicon/query guidance:

```markdown
Use the alias-first project cognition flow. Run `project-cognition lexicon --mode catalog` first, read the schema v2 `alias_index`-backed alias catalog, normalize user input into project vocabulary, record `alias_interpretations`, and only then call `project-cognition query --query-plan`. If the runtime reports schema v1 or rebuild-required readiness, do not query through the old DB; continue with live repository evidence and recommend `sp-map-scan -> sp-map-build` when a usable brownfield baseline is needed.
```

Apply the same contract in:

```text
templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md
templates/passive-skills/spec-kit-workflow-routing/SKILL.md
README.md
PROJECT-HANDBOOK.md
```

Keep existing "map points, code proves" language. The alias catalog is route vocabulary, not evidence by itself.

- [ ] **Step 5: Update integration rendering and fake project cognition DBs**

In `tests/project_cognition_fake.py`, change fake DB creation to:

```python
required_tables = [
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
    "updates",
]
```

Update fake metadata writes from schema version `1` to `2` where they describe the SQLite graph store. Keep unrelated JSON fixture schema versions unchanged.

Insert at least one fake alias row for fake brownfield-ready DBs:

```sql
INSERT OR REPLACE INTO alias_index(id, generation_id, alias, normalized_alias, target_type, target_id, language, source, confidence, evidence_id)
VALUES('ALIAS-app', ?, 'App', 'app', 'node', 'N-app', 'en', 'node_title', 'verified', '');
```

In `tests/contract/test_hook_cli_surface.py`, update embedded test DB DDL to the schema v2 table list and schema metadata value `2`. Remove old table DDL for claims, conflicts, symbols, entrypoints, tests, slices, query examples, and FTS.

In `src/specify_cli/integrations/base.py`, update any injected project cognition text so generated skill surfaces say "schema v2 alias catalog" and do not require removed tables.

- [ ] **Step 6: Run focused Python tests**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_runtime_handbook_contract.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit guidance and fake updates**

Run:

```powershell
git add templates/commands/map-scan.md templates/commands/map-build.md templates/command-partials/common/context-loading-gradient.md templates/command-partials/common/planning-context-loading-gradient.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md src/specify_cli/integrations/base.py tests/project_cognition_fake.py tests/contract/test_hook_cli_surface.py tests/test_map_scan_build_template_guidance.py tests/test_runtime_handbook_contract.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py README.md PROJECT-HANDBOOK.md
git commit -m "docs: document cognition schema v2 alias flow"
```

### Task 8: Full Verification and Cleanup

**Files:**
- Verify: all modified Go, Python, template, README, and handbook files
- Test: Go project-cognition runtime
- Test: focused Python template and integration surfaces

- [ ] **Step 1: Format Go files**

Run from `tools/project-cognition`:

```powershell
gofmt -w internal/store/schema.go internal/store/store.go internal/store/import.go internal/store/schema_test.go internal/store/import_test.go internal/store/update_test.go internal/build/build.go internal/build/aliases.go internal/build/aliases_test.go internal/query/lexicon.go internal/validation/build.go internal/validation/build_test.go internal/cli/cli_test.go internal/update/state_test.go
```

Expected: command exits 0.

- [ ] **Step 2: Run full Go tests**

Run from `tools/project-cognition`:

```powershell
go test ./... -count=1
```

Expected: PASS.

- [ ] **Step 3: Run Go vet and build**

Run from `tools/project-cognition`:

```powershell
go vet ./...
```

Expected: PASS.

Run from `tools/project-cognition`:

```powershell
go build -o $env:TEMP\project-cognition-schema-v2-check.exe .
```

Expected: PASS and creates `$env:TEMP\project-cognition-schema-v2-check.exe`.

- [ ] **Step 4: Run Python focused regression tests**

Run from repository root:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_runtime_handbook_contract.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS.

- [ ] **Step 5: Search for removed schema tables in runtime schema surfaces**

Run from repository root:

```powershell
rg -n "CREATE TABLE IF NOT EXISTS (claims|claim_evidence|conflicts|conflict_claims|symbol_index|entrypoint_index|test_index|slice_members|query_examples)|CREATE VIRTUAL TABLE IF NOT EXISTS (claim_fts|observation_fts|alias_fts)" tools/project-cognition tests/project_cognition_fake.py tests/contract/test_hook_cli_surface.py
```

Expected: no output and exit code 1 from `rg`.

Run from repository root:

```powershell
rg -n "schema_version.: 1|schema_version.*1" tools/project-cognition/internal tests/project_cognition_fake.py tests/contract/test_hook_cli_surface.py
```

Expected: only scan-artifact fixture schema versions remain. No project-cognition SQLite metadata fixture should still expect DB schema version 1.

- [ ] **Step 6: Check diff hygiene**

Run from repository root:

```powershell
git diff --check
```

Expected: no whitespace errors.

Run from repository root:

```powershell
git status --short
```

Expected: only intentional tracked changes are present before the final commit.

- [ ] **Step 7: Final commit**

If verification changed files, commit them:

```powershell
git add tools/project-cognition src tests templates README.md PROJECT-HANDBOOK.md
git commit -m "test: verify cognition schema v2 cleanup"
```

If no files changed after Task 7, skip this commit and record the verification commands in the final implementation handoff.

## Self-Review Notes

- Spec coverage: the plan covers schema v2 table removal, `alias_index` invariants, v1 inspect-only/query-blocked behavior, build-time v1 rebuild, alias production, lexicon catalog reads, validation gates, generated prompt guidance, fakes, docs, and focused tests.
- Placeholder scan: this plan contains no deferred implementation markers. Every task names concrete files, commands, expected outcomes, and code-level changes.
- Type consistency: alias storage uses `store.AliasImport` for writes and `store.ConceptAliasRow` for lexicon reads. Build derivation returns `[]store.AliasImport`; candidate rows expose `[]store.ConceptAliasRow`; validation reads the SQLite table directly.

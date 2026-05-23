# Project Cognition Runtime Build Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a runtime-owned `project-cognition build-from-scan` pipeline that imports validated scan artifacts into SQLite without manual SQL and blocks any DB/status split-brain or scan-vs-DB identity loss.

**Architecture:** Introduce focused Go packages for scan artifact loading, runtime agreement checks, and build orchestration. Keep SQLite writes behind `store` domain writer APIs, keep scan/build validation in `validation`, and update generated `sp-map-build` guidance to call the official importer instead of asking agents to publish DB rows themselves.

**Tech Stack:** Go 1.21, `database/sql`, `modernc.org/sqlite`, JSON artifact parsing, pytest template tests, PowerShell-safe verification commands.

---

## Reference Spec

- `docs/superpowers/specs/2026-05-24-project-cognition-runtime-build-pipeline-design.md`

## Scope

This plan implements Phase 1 from the spec:

- official `build-from-scan` command
- scan artifact validation factoring
- scan artifact identity loading
- store writer APIs for baseline import
- identity reconciliation in `validate-build`
- DB/status agreement gate
- `sp-map-build` template guidance alignment

This plan does not implement the Phase 2/3 semantic upgrades for graph-backed `map-update`, `lexicon`, or `query`. It only adds the baseline safety gate those commands must obey before they read or mutate the graph.

## File Structure

Create new packages:

- `tools/project-cognition/internal/scanartifacts/scanartifacts.go`: load scan artifacts, normalize JSON shapes, validate workbench paths, detect BOM, and expose row identity sets.
- `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`: fixture-driven tests for required paths, BOM diagnostics, status-free artifact validation, and identity extraction.
- `tools/project-cognition/internal/runtimegate/agreement.go`: compare Go `status.json` against SQLite metadata and active generation before baseline-reading commands continue.
- `tools/project-cognition/internal/runtimegate/agreement_test.go`: split-brain and healthy agreement tests.
- `tools/project-cognition/internal/store/import.go`: transactional graph-generation import APIs and active-generation identity snapshots.
- `tools/project-cognition/internal/store/import_test.go`: import, rollback, identity snapshot, rejection, and merge-record tests.
- `tools/project-cognition/internal/build/build.go`: `build-from-scan` orchestration, publish protocol, output payload, and recovery action generation.
- `tools/project-cognition/internal/build/build_test.go`: first baseline, legacy status replacement, identity payload, and status-write failure tests.

Modify existing runtime code:

- `tools/project-cognition/internal/runtime/status.go`: make `WriteStatus` use temp-file plus atomic replace.
- `tools/project-cognition/internal/validation/scan.go`: delegate artifact checks to `scanartifacts` and keep `validate-scan` status-gate behavior.
- `tools/project-cognition/internal/validation/build.go`: enforce runtime agreement and identity reconciliation.
- `tools/project-cognition/internal/cli/cli.go`: add `build-from-scan`, `import-scan`, and `rebuild-from-scan` commands; update help.
- `tools/project-cognition/internal/query/query.go`: check DB/status agreement before returning graph data.
- `tools/project-cognition/internal/query/lexicon.go`: check DB/status agreement before returning graph-backed readiness.
- `tools/project-cognition/internal/update/state.go`: check DB/status agreement before update mutation paths.
- `tools/project-cognition/internal/reference/discover.go`: report split-brain candidates as blocked.
- `tools/project-cognition/internal/reference/read.go`: reject split-brain reference reads.

Modify generated workflow surfaces:

- `templates/commands/map-build.md`
- `templates/command-partials/map-build/shell.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: do not
  edit proactively; update only if template tests fail because this passive
  skill still teaches the old map-build completion path.
- `tests/test_map_scan_build_template_guidance.py`
- `tests/test_map_runtime_template_guidance.py`: do not edit proactively; update
  only if a failing assertion still expects the old map-build runtime command
  sequence.
- `tests/test_alignment_templates.py`: do not edit proactively; update only for
  failing assertions tied to changed map-build command guidance.

---

### Task 1: Factor Scan Artifact Loading And Validation

**Files:**
- Create: `tools/project-cognition/internal/scanartifacts/scanartifacts.go`
- Create: `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`
- Modify: `tools/project-cognition/internal/validation/scan.go`
- Test: `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`

- [ ] **Step 1: Write failing tests for artifact-only validation**

Create `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go` with tests that prove `status.json` is not required for artifact validation:

```go
package scanartifacts

import (
	"os"
	"path/filepath"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

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

func writeMinimalScanPackage(t *testing.T, paths rt.Paths) {
	t.Helper()
	writeFile(t, filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"), `{
	  "id": "E-001",
	  "source_path": "src/app.go",
	  "content_hash": "hash-app",
	  "source_kind": "source",
	  "commit_sha": "abc123"
	}`)
	writeFile(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), `{
	  "nodes": [{
	    "id": "N-app",
	    "type": "capability",
	    "title": "App",
	    "confidence": "verified",
	    "paths": ["src/app.go"],
	    "evidence_ids": ["E-001"]
	  }]
	}`)
	writeFile(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), `{
	  "edges": [{
	    "id": "EDGE-app-self",
	    "type": "owns",
	    "source_id": "N-app",
	    "target_id": "N-app",
	    "confidence": "verified",
	    "evidence_ids": ["E-001"]
	  }]
	}`)
	writeFile(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), `{
	  "observations": [{
	    "id": "OBS-app",
	    "observation_type": "summary",
	    "summary": "App surface observed",
	    "evidence_ids": ["E-001"]
	  }]
	}`)
	writeFile(t, filepath.Join(paths.RuntimeDir, "coverage.json"), `{
	  "rows": [{"path": "src/app.go", "coverage": "deep-read"}]
	}`)
	writeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "map-scan.md"), "# scan\n")
	writeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.md"), "# ledger\n")
	writeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), `{
	  "rows": [{"path": "src/app.go", "owner": "scan"}],
	  "open_gaps": []
	}`)
	writeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-1.md"), "# lane\n")
	writeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"), "readiness=scan_ready\n")
	writeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), `{
	  "included_paths": ["src/app.go"],
	  "excluded_paths": []
	}`)
	writeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "capability-ledger.json"), `{"rows":[]}`)
	writeFile(t, filepath.Join(paths.RuntimeDir, "workbench", "control-ledger.json"), `{"rows":[]}`)
}

func writeFile(t *testing.T, path string, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestValidateArtifactsDoesNotRequireStatusJSON(t *testing.T) {
	paths := testPaths(t)
	writeMinimalScanPackage(t, paths)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, errors=%#v", result.Status, result.Errors)
	}
	if !containsPath(result.CheckedPaths, ".specify/project-cognition/workbench/repository-universe.json") {
		t.Fatalf("CheckedPaths = %#v, want workbench repository universe", result.CheckedPaths)
	}
	if containsPath(result.CheckedPaths, ".specify/project-map") {
		t.Fatalf("CheckedPaths = %#v, did not want legacy project-map path", result.CheckedPaths)
	}
}

func containsPath(paths []string, want string) bool {
	for _, path := range paths {
		if path == want {
			return true
		}
	}
	return false
}
```

- [ ] **Step 2: Write failing tests for BOM and identity extraction**

Append these tests to `scanartifacts_test.go`:

```go
func TestValidateArtifactsReportsUTF8BOM(t *testing.T) {
	paths := testPaths(t)
	writeMinimalScanPackage(t, paths)
	bom := append([]byte{0xEF, 0xBB, 0xBF}, []byte(`{"rows":[]}`)...)
	if err := os.WriteFile(filepath.Join(paths.RuntimeDir, "coverage.json"), bom, 0o644); err != nil {
		t.Fatal(err)
	}

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", result.Status)
	}
	if !containsText(result.Errors, "coverage.json contains UTF-8 BOM") {
		t.Fatalf("Errors = %#v, want BOM diagnostic", result.Errors)
	}
}

func TestLoadExtractsIdentitySets(t *testing.T) {
	paths := testPaths(t)
	writeMinimalScanPackage(t, paths)

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, errors=%#v", result.Status, result.Errors)
	}
	if _, ok := pkg.Identities.Evidence["E-001|src/app.go|hash-app"]; !ok {
		t.Fatalf("Evidence identities = %#v", pkg.Identities.Evidence)
	}
	if _, ok := pkg.Identities.Nodes["N-app"]; !ok {
		t.Fatalf("Node identities = %#v", pkg.Identities.Nodes)
	}
	if _, ok := pkg.Identities.Edges["EDGE-app-self|N-app|N-app|owns"]; !ok {
		t.Fatalf("Edge identities = %#v", pkg.Identities.Edges)
	}
	if _, ok := pkg.Identities.Observations["OBS-app"]; !ok {
		t.Fatalf("Observation identities = %#v", pkg.Identities.Observations)
	}
	if _, ok := pkg.Identities.CoveragePaths["src/app.go"]; !ok {
		t.Fatalf("Coverage identities = %#v", pkg.Identities.CoveragePaths)
	}
}

func containsText(values []string, want string) bool {
	for _, value := range values {
		if strings.Contains(value, want) {
			return true
		}
	}
	return false
}
```

Add `strings` to the test imports.

- [ ] **Step 3: Run the new package tests and confirm they fail**

Run:

```powershell
go test ./internal/scanartifacts
```

from `tools/project-cognition`.

Expected: FAIL because `internal/scanartifacts` does not exist.

- [ ] **Step 4: Implement `scanartifacts` types and artifact validation**

Create `tools/project-cognition/internal/scanartifacts/scanartifacts.go` with these public types and functions:

```go
package scanartifacts

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

type ValidateOptions struct {
	RequireStatusJSON bool
}

type Result struct {
	Status       string         `json:"status"`
	Gate         string         `json:"gate"`
	Readiness    string         `json:"readiness"`
	Errors       []string       `json:"errors"`
	Warnings     []string       `json:"warnings"`
	CheckedPaths []string       `json:"checked_paths"`
	Details      map[string]any `json:"details"`
}

type Package struct {
	Evidence      []EvidenceRow
	Nodes         []NodeRow
	Edges         []EdgeRow
	Observations  []ObservationRow
	CoveragePaths []string
	Identities    IdentitySet
}

type IdentitySet struct {
	Evidence      map[string]bool `json:"evidence"`
	Nodes         map[string]bool `json:"nodes"`
	Edges         map[string]bool `json:"edges"`
	Observations  map[string]bool `json:"observations"`
	CoveragePaths map[string]bool `json:"coverage_paths"`
}

type EvidenceRow struct {
	ID          string
	SourceKind  string
	SourcePath  string
	CommitSHA   string
	Span        string
	Extractor   string
	ContentHash string
	Attrs       map[string]any
}

type NodeRow struct {
	ID          string
	Type        string
	Title       string
	Confidence  string
	Paths       []string
	EvidenceIDs []string
	Attrs       map[string]any
}

type EdgeRow struct {
	ID          string
	Type        string
	SourceID    string
	TargetID    string
	Confidence  string
	EvidenceIDs []string
	Attrs       map[string]any
}

type ObservationRow struct {
	ID              string
	ObservationType string
	Summary         string
	EvidenceIDs     []string
	Attrs           map[string]any
}

func Validate(paths rt.Paths, opts ValidateOptions) Result
func Load(paths rt.Paths, opts ValidateOptions) (Package, Result)
```

Implementation rules:

- Required artifact paths are exactly the current runtime/workbench paths:
  - `.specify/project-cognition/evidence`
  - `.specify/project-cognition/provisional/nodes.json`
  - `.specify/project-cognition/provisional/edges.json`
  - `.specify/project-cognition/provisional/observations.json`
  - `.specify/project-cognition/coverage.json`
  - `.specify/project-cognition/workbench/map-scan.md`
  - `.specify/project-cognition/workbench/coverage-ledger.md`
  - `.specify/project-cognition/workbench/coverage-ledger.json`
  - `.specify/project-cognition/workbench/scan-packets`
  - `.specify/project-cognition/workbench/map-state.md`
  - `.specify/project-cognition/workbench/repository-universe.json`
- Include `.specify/project-cognition/status.json` only when `RequireStatusJSON` is true.
- `readJSONFile` must check the first three bytes for UTF-8 BOM and return `<label> contains UTF-8 BOM`.
- Accept top-level arrays or top-level objects with `rows`, `evidence`, `nodes`, `edges`, or `observations` arrays as appropriate.
- Evidence files under `evidence/*.json` may be a single object or an object containing `rows`/`evidence`.
- Normalize paths with `filepath.ToSlash`, trim spaces, and remove leading `./`.
- Reject `.specify/**` coverage and evidence source paths.
- Require `coverage.json.rows[].path`.
- Require `workbench/coverage-ledger.json.rows`.
- Block `open_gaps[]` with `status="blocked"` or `reason="subagent_blocked"`.
- Build identities with these string keys:
  - evidence: `id + "|" + source_path + "|" + content_hash`
  - node: `id`
  - edge: `id + "|" + source_id + "|" + target_id + "|" + type`
  - observation: `id`
  - coverage path: normalized path
- When evidence `id` is missing, use the file stem plus row index for the ID.
- When evidence `content_hash` is missing, hash the normalized JSON object with SHA-256.
- Node, edge, and observation IDs are required. Missing IDs block validation.

- [ ] **Step 5: Update `validation.ValidateScan` to use the new package**

In `tools/project-cognition/internal/validation/scan.go`, replace the duplicated path/JSON validation with:

```go
func ValidateScan(paths rt.Paths) GatePayload {
	result := scanartifacts.Validate(paths, scanartifacts.ValidateOptions{RequireStatusJSON: true})
	return GatePayload{
		Status:       result.Status,
		Gate:         result.Gate,
		Readiness:    result.Readiness,
		Errors:       result.Errors,
		Warnings:     result.Warnings,
		CheckedPaths: result.CheckedPaths,
		Details:      result.Details,
	}
}
```

After replacing `ValidateScan`, run `rg -n "validateScanEvidence|validateCoverageRows|validateCoverageLedger|normalizedString" tools/project-cognition/internal/validation`. Delete helpers with no remaining references. If `validateCoverageLedger` is still needed by `ValidateBuild`, move it behind the `scanartifacts` API instead of keeping a second scan artifact parser.

- [ ] **Step 6: Verify scan tests**

Run:

```powershell
go test ./internal/scanartifacts ./internal/validation
```

Expected: PASS.

- [ ] **Step 7: Commit Task 1**

```powershell
git add tools/project-cognition/internal/scanartifacts tools/project-cognition/internal/validation/scan.go
git commit -m "feat: factor project cognition scan artifacts"
```

---

### Task 2: Add Store Import APIs And Identity Snapshots

**Files:**
- Create: `tools/project-cognition/internal/store/import.go`
- Create: `tools/project-cognition/internal/store/import_test.go`
- Modify: `tools/project-cognition/internal/store/store.go` only to reuse the
  existing `Store.DB()` and metadata helpers; do not move import logic into
  `store.go`.
- Test: `tools/project-cognition/internal/store/import_test.go`

- [ ] **Step 1: Write failing store import tests**

Create `tools/project-cognition/internal/store/import_test.go`:

```go
package store

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

func importTestPaths(t *testing.T) rt.Paths {
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

func TestImportGenerationPublishesActiveIdentitySnapshot(t *testing.T) {
	paths := importTestPaths(t)
	st, err := Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()

	input := ImportInput{
		GenerationID: "GEN-import",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []EvidenceImport{{
			ID: "E-001", SourceKind: "source", SourcePath: "src/app.go",
			CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-app",
		}},
		Nodes: []NodeImport{{
			ID: "N-app", Type: "capability", Title: "App", Confidence: "verified",
			EvidenceIDs: []string{"E-001"},
		}},
		Edges: []EdgeImport{{
			ID: "EDGE-app-self", Type: "owns", SourceID: "N-app", TargetID: "N-app",
			Confidence: "verified", EvidenceIDs: []string{"E-001"},
		}},
		Observations: []ObservationImport{{
			ID: "OBS-app", ObservationType: "summary", Summary: "App observed",
			EvidenceIDs: []string{"E-001"},
		}},
		PathIndex: []PathIndexImport{{
			ID: "P-src-app-go", Path: "src/app.go", NodeID: "N-app",
			Relation: "owns", Confidence: "verified", EvidenceID: "E-001",
		}},
		Rejections: []RowDecision{{Category: "coverage", Identity: "docs/missing.md", Reason: "no_node_relation"}},
		MergeRecords: []MergeRecord{{Category: "node", SourceIdentity: "N-app-duplicate", TargetIdentity: "N-app", Reason: "duplicate_label"}},
	}

	activeID, err := st.ImportGeneration(context.Background(), input)
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "GEN-import" {
		t.Fatalf("activeID = %q", activeID)
	}
	snapshot, err := st.ActiveIdentitySnapshot(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if !snapshot.Evidence["E-001|src/app.go|hash-app"] {
		t.Fatalf("Evidence identities = %#v", snapshot.Evidence)
	}
	if !snapshot.Nodes["N-app"] {
		t.Fatalf("Node identities = %#v", snapshot.Nodes)
	}
	if !snapshot.Edges["EDGE-app-self|N-app|N-app|owns"] {
		t.Fatalf("Edge identities = %#v", snapshot.Edges)
	}
	if !snapshot.Observations["OBS-app"] {
		t.Fatalf("Observation identities = %#v", snapshot.Observations)
	}
	if !snapshot.CoveragePaths["src/app.go"] {
		t.Fatalf("Coverage identities = %#v", snapshot.CoveragePaths)
	}
	if len(snapshot.Rejections) != 1 || snapshot.Rejections[0].Reason != "no_node_relation" {
		t.Fatalf("Rejections = %#v", snapshot.Rejections)
	}
	if len(snapshot.MergeRecords) != 1 || snapshot.MergeRecords[0].TargetIdentity != "N-app" {
		t.Fatalf("MergeRecords = %#v", snapshot.MergeRecords)
	}
}

func TestImportGenerationRollsBackOnInvalidEdge(t *testing.T) {
	paths := importTestPaths(t)
	st, err := Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()

	_, err = st.ImportGeneration(context.Background(), ImportInput{
		GenerationID: "GEN-bad",
		Kind:         "full",
		SourceCommit: "abc123",
		Edges: []EdgeImport{{
			ID: "EDGE-bad", Type: "owns", SourceID: "missing", TargetID: "missing",
			Confidence: "verified",
		}},
	})
	if err == nil {
		t.Fatal("expected invalid edge import error")
	}
	activeID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if activeID != "" {
		t.Fatalf("active generation = %q, want empty after rollback", activeID)
	}
}

func TestImportGenerationStoresRejectionsInGenerationAttrs(t *testing.T) {
	paths := importTestPaths(t)
	st, err := Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	if _, err := st.ImportGeneration(context.Background(), ImportInput{
		GenerationID: "GEN-reject",
		Kind:         "full",
		SourceCommit: "abc123",
		Rejections: []RowDecision{{
			Category: "node", Identity: "N-bad", Reason: "missing_id",
		}},
	}); err != nil {
		t.Fatal(err)
	}
	var attrs string
	if err := st.DB().QueryRow(`SELECT attrs_json FROM generations WHERE id = 'GEN-reject'`).Scan(&attrs); err != nil {
		t.Fatal(err)
	}
	var payload map[string]any
	if err := json.Unmarshal([]byte(attrs), &payload); err != nil {
		t.Fatal(err)
	}
	if _, ok := payload["rejections"].([]any); !ok {
		t.Fatalf("attrs_json = %#v, want rejections array", payload)
	}
}
```

- [ ] **Step 2: Run store tests and confirm they fail**

Run:

```powershell
go test ./internal/store
```

Expected: FAIL because import APIs are undefined.

- [ ] **Step 3: Implement store import types**

Create `tools/project-cognition/internal/store/import.go` with:

```go
package store

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"
)

type ImportInput struct {
	GenerationID  string
	Kind          string
	SourceCommit  string
	Evidence      []EvidenceImport
	Nodes         []NodeImport
	Edges         []EdgeImport
	Observations  []ObservationImport
	PathIndex     []PathIndexImport
	Rejections    []RowDecision
	MergeRecords  []MergeRecord
}

type EvidenceImport struct {
	ID, SourceKind, SourcePath, CommitSHA, Span, Extractor, ContentHash string
	Attrs map[string]any
}

type NodeImport struct {
	ID, Type, Title, Confidence string
	EvidenceIDs []string
	Attrs map[string]any
}

type EdgeImport struct {
	ID, Type, SourceID, TargetID, Confidence string
	EvidenceIDs []string
	Attrs map[string]any
}

type ObservationImport struct {
	ID, ObservationType, Summary string
	EvidenceIDs []string
	Attrs map[string]any
}

type PathIndexImport struct {
	ID, Path, NodeID, Relation, Confidence, EvidenceID string
}

type RowDecision struct {
	Category string `json:"category"`
	Identity string `json:"identity"`
	Reason   string `json:"reason"`
}

type MergeRecord struct {
	Category       string `json:"category"`
	SourceIdentity string `json:"source_identity"`
	TargetIdentity string `json:"target_identity"`
	Reason         string `json:"reason"`
}

type IdentitySnapshot struct {
	Evidence      map[string]bool `json:"evidence"`
	Nodes         map[string]bool `json:"nodes"`
	Edges         map[string]bool `json:"edges"`
	Observations  map[string]bool `json:"observations"`
	CoveragePaths map[string]bool `json:"coverage_paths"`
	Rejections    []RowDecision   `json:"rejections"`
	MergeRecords  []MergeRecord   `json:"merge_records"`
}
```

- [ ] **Step 4: Implement `ImportGeneration`**

Add:

```go
func (s *Store) ImportGeneration(ctx context.Context, input ImportInput) (string, error)
```

Implementation rules:

- Default `Kind` to `"full"` and `SourceCommit` to `""`.
- Reject empty `GenerationID`.
- Start `tx, err := s.db.BeginTx(ctx, nil)`.
- Insert new generation with `state='building'`.
- Store `rejections` and `merge_records` in `generations.attrs_json`.
- Insert evidence rows before dependent rows.
- Insert node rows and `node_evidence` rows.
- Insert edge rows and `edge_evidence` rows. Before inserting each edge, verify source and target node IDs exist in the imported node set or DB for that generation; return an error if not.
- Insert observation rows and `observation_evidence` rows.
- Insert path index rows after nodes/evidence.
- Supersede existing active generations with `state='superseded'` and `superseded_at=now`.
- Change the new generation to `state='active'`, `published_at=now`.
- Write metadata keys: `runtime_format`, `runtime_schema`, `schema_version`, `active_generation_id`, `graph_store_path`, `graph_ready`, `baseline_state`, `query_contract_version`, `update_contract_version`, `published_at`.
- Roll back on any error before commit.

- [ ] **Step 5: Implement `ActiveIdentitySnapshot`**

Add:

```go
func (s *Store) ActiveIdentitySnapshot(ctx context.Context) (IdentitySnapshot, error)
```

Implementation rules:

- Read active generation with `ActiveGenerationID`.
- Evidence identity query:
  `SELECT id, source_path, content_hash FROM evidence WHERE generation_id = ?`.
- Node identity query:
  `SELECT id FROM nodes WHERE generation_id = ?`.
- Edge identity query:
  `SELECT id, source_id, target_id, type FROM edges WHERE generation_id = ?`.
- Observation identity query:
  `SELECT id FROM observations WHERE generation_id = ?`.
- Coverage identity query:
  `SELECT path FROM path_index WHERE generation_id = ?`.
- Parse `generations.attrs_json.rejections` and `.merge_records` into the snapshot.

- [ ] **Step 6: Verify store tests**

Run:

```powershell
go test ./internal/store
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

```powershell
git add tools/project-cognition/internal/store/import.go tools/project-cognition/internal/store/import_test.go
git commit -m "feat: add project cognition graph import store APIs"
```

---

### Task 3: Add Runtime Agreement Gate And Atomic Status Writes

**Files:**
- Create: `tools/project-cognition/internal/runtimegate/agreement.go`
- Create: `tools/project-cognition/internal/runtimegate/agreement_test.go`
- Modify: `tools/project-cognition/internal/runtime/status.go`
- Modify: `tools/project-cognition/internal/runtime/status_test.go`
- Test: `tools/project-cognition/internal/runtimegate/agreement_test.go`

- [ ] **Step 1: Write failing runtime gate tests**

Create `tools/project-cognition/internal/runtimegate/agreement_test.go`:

```go
package runtimegate

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

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

func TestCheckAgreementAcceptsMatchingStatusAndDB(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{GenerationID: "GEN-1", Kind: "full"}); err != nil {
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

	result := Check(paths)

	if result.Status != "ok" {
		t.Fatalf("Status = %q, errors=%#v", result.Status, result.Errors)
	}
}

func TestCheckAgreementBlocksSplitBrainActiveGeneration(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{GenerationID: "GEN-db", Kind: "full"}); err != nil {
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
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	result := Check(paths)

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", result.Status)
	}
	if result.RecoveryAction != "rewrite_status_from_db_metadata" {
		t.Fatalf("RecoveryAction = %q", result.RecoveryAction)
	}
}
```

- [ ] **Step 2: Add atomic status write test**

Append to `tools/project-cognition/internal/runtime/status_test.go`:

```go
func TestWriteStatusUsesGoRuntimeMarker(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	status := DefaultStatus(paths)
	status.ActiveGenerationID = "GEN-atomic"
	if err := WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(paths.StatusPath)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), `"runtime_format": "project-cognition-go"`) {
		t.Fatalf("status payload = %s", data)
	}
}
```

Add `strings` to the imports in `status_test.go`.

- [ ] **Step 3: Run tests and confirm failure**

Run:

```powershell
go test ./internal/runtime ./internal/runtimegate
```

Expected: FAIL because `runtimegate` does not exist.

- [ ] **Step 4: Implement `runtimegate.Check`**

Create `tools/project-cognition/internal/runtimegate/agreement.go`:

```go
package runtimegate

import (
	"context"
	"errors"
	"fmt"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

type Agreement struct {
	Status                string   `json:"status"`
	Readiness             string   `json:"readiness"`
	Errors                []string `json:"errors"`
	Warnings              []string `json:"warnings"`
	RecoveryAction        string   `json:"recovery_action,omitempty"`
	StatusPath            string   `json:"status_path"`
	GraphStorePath        string   `json:"graph_store_path"`
	StatusGenerationID    string   `json:"status_generation_id,omitempty"`
	DBActiveGenerationID  string   `json:"db_active_generation_id,omitempty"`
	RecommendedNextAction string   `json:"recommended_next_action"`
}

func Check(paths rt.Paths) Agreement
func BlockedPayload(paths rt.Paths, agreement Agreement) map[string]any
```

Implementation rules:

- Call `rt.ReadStatus`.
- If legacy, return `status=blocked`, `readiness=unsupported_runtime`, `recovery_action=run_map_scan_build`.
- Open existing store.
- Read DB active generation ID.
- Compare status `ActiveGenerationID` to DB active ID when both are non-empty.
- Compare `GraphStorePath` to `.specify/project-cognition/project-cognition.db`.
- Return `status=ok` only when status is Go-format, DB exists, active generation exists, and IDs agree.
- Return `status=blocked`, `readiness=blocked`, `recovery_action=rewrite_status_from_db_metadata` for split-brain.

- [ ] **Step 5: Make `runtime.WriteStatus` atomic**

Modify `tools/project-cognition/internal/runtime/status.go`:

- Marshal JSON as before.
- Write to `status.json.tmp`.
- Close file by using `os.WriteFile`.
- Replace status with `os.Rename(tmp, paths.StatusPath)`.
- On Windows, remove the old `status.json` before `os.Rename` if the first rename fails because the destination exists. Do not ignore remove errors.
- Clean up the temp file on failure.

- [ ] **Step 6: Verify runtime gate tests**

Run:

```powershell
go test ./internal/runtime ./internal/runtimegate
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

```powershell
git add tools/project-cognition/internal/runtime/status.go tools/project-cognition/internal/runtime/status_test.go tools/project-cognition/internal/runtimegate
git commit -m "feat: add project cognition runtime agreement gate"
```

---

### Task 4: Build The `build-from-scan` Service

**Files:**
- Create: `tools/project-cognition/internal/build/build.go`
- Create: `tools/project-cognition/internal/build/build_test.go`
- Modify: `tools/project-cognition/internal/store/import.go` if mapping exposes missing fields.
- Test: `tools/project-cognition/internal/build/build_test.go`

- [ ] **Step 1: Write failing build service tests**

Create `tools/project-cognition/internal/build/build_test.go`:

```go
package build

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

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

func TestRunCreatesGoRuntimeFromScanWithoutExistingStatus(t *testing.T) {
	paths := testPaths(t)
	writeMinimalScanPackage(t, paths)

	payload, err := Run(paths)
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "ok" {
		t.Fatalf("Status = %q errors=%#v", payload.Status, payload.Errors)
	}
	if payload.ActiveGenerationID == "" {
		t.Fatalf("ActiveGenerationID is empty")
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.RuntimeFormat != rt.RuntimeFormat {
		t.Fatalf("RuntimeFormat = %q", status.RuntimeFormat)
	}
	if status.ActiveGenerationID != payload.ActiveGenerationID {
		t.Fatalf("status active generation = %q, payload = %q", status.ActiveGenerationID, payload.ActiveGenerationID)
	}
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	snapshot, err := st.ActiveIdentitySnapshot(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if !snapshot.Nodes["N-app"] || !snapshot.CoveragePaths["src/app.go"] {
		t.Fatalf("snapshot = %#v", snapshot)
	}
}

func TestRunReplacesLegacyStatusThroughBuildPath(t *testing.T) {
	paths := testPaths(t)
	writeMinimalScanPackage(t, paths)
	if err := os.WriteFile(paths.StatusPath, []byte(`{"freshness":"fresh"}`), 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := Run(paths)
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "ok" {
		t.Fatalf("Status = %q errors=%#v", payload.Status, payload.Errors)
	}
	if !payload.LegacyRuntimeReplaced {
		t.Fatalf("LegacyRuntimeReplaced = false")
	}
	if _, err := rt.ReadStatus(paths); err != nil {
		t.Fatalf("ReadStatus after build: %v", err)
	}
}

func TestRunReturnsBlockedWhenStatusWriteFailsAfterDBCommit(t *testing.T) {
	paths := testPaths(t)
	writeMinimalScanPackage(t, paths)
	if err := os.MkdirAll(paths.StatusPath, 0o755); err != nil {
		t.Fatal(err)
	}

	payload, err := Run(paths)

	if err == nil {
		t.Fatal("expected status write failure")
	}
	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if payload.RecoveryAction != "rewrite_status_from_db_metadata" {
		t.Fatalf("RecoveryAction = %q", payload.RecoveryAction)
	}
	st, openErr := store.OpenExisting(paths)
	if openErr != nil {
		t.Fatal(openErr)
	}
	defer st.Close()
	activeID, activeErr := st.ActiveGenerationID(context.Background())
	if activeErr != nil {
		t.Fatal(activeErr)
	}
	if activeID == "" {
		t.Fatal("DB active generation should remain after status write failure")
	}
}
```

Append this helper to `build_test.go` so the build package test is self-contained:

```go
func writeMinimalScanPackage(t *testing.T, paths rt.Paths) {
	t.Helper()
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"), `{
	  "id": "E-001",
	  "source_path": "src/app.go",
	  "content_hash": "hash-app",
	  "source_kind": "source",
	  "commit_sha": "abc123"
	}`)
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), `{
	  "nodes": [{
	    "id": "N-app",
	    "type": "capability",
	    "title": "App",
	    "confidence": "verified",
	    "paths": ["src/app.go"],
	    "evidence_ids": ["E-001"]
	  }]
	}`)
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), `{
	  "edges": [{
	    "id": "EDGE-app-self",
	    "type": "owns",
	    "source_id": "N-app",
	    "target_id": "N-app",
	    "confidence": "verified",
	    "evidence_ids": ["E-001"]
	  }]
	}`)
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), `{
	  "observations": [{
	    "id": "OBS-app",
	    "observation_type": "summary",
	    "summary": "App observed",
	    "evidence_ids": ["E-001"]
	  }]
	}`)
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "coverage.json"), `{
	  "rows": [{"path": "src/app.go", "coverage": "deep-read"}]
	}`)
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "workbench", "map-scan.md"), "# scan")
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.md"), "# ledger")
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), `{
	  "rows": [{"path": "src/app.go", "owner": "scan"}],
	  "open_gaps": []
	}`)
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-1.md"), "# lane")
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"), "readiness=scan_ready")
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), `{
	  "included_paths": ["src/app.go"],
	  "excluded_paths": []
	}`)
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "workbench", "capability-ledger.json"), `{"rows":[]}`)
	writeBuildFile(t, filepath.Join(paths.RuntimeDir, "workbench", "control-ledger.json"), `{"rows":[]}`)
}

func writeBuildFile(t *testing.T, path string, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
		t.Fatal(err)
	}
}
```

- [ ] **Step 2: Run build tests and confirm failure**

Run:

```powershell
go test ./internal/build
```

Expected: FAIL because `internal/build` does not exist.

- [ ] **Step 3: Implement build payload and orchestration**

Create `tools/project-cognition/internal/build/build.go` with:

```go
package build

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtimegate"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

type Payload struct {
	Status                 string         `json:"status"`
	Readiness              string         `json:"readiness"`
	Errors                 []string       `json:"errors"`
	Warnings               []string       `json:"warnings"`
	ScanArtifactCounts     map[string]int `json:"scan_artifact_counts"`
	DBCounts               map[string]int `json:"db_counts"`
	IdentityReconciliation map[string]any `json:"identity_reconciliation"`
	Rejections             []store.RowDecision `json:"rejections"`
	MergeRecords           []store.MergeRecord `json:"merge_records"`
	RecoveryAction         string         `json:"recovery_action,omitempty"`
	StatusPath             string         `json:"status_path"`
	GraphStorePath         string         `json:"graph_store_path"`
	ActiveGenerationID     string         `json:"active_generation_id,omitempty"`
	LegacyRuntimeReplaced  bool           `json:"legacy_runtime_replaced"`
}

func Run(paths rt.Paths) (Payload, error)
```

Implementation rules:

- Call `scanartifacts.Load(paths, scanartifacts.ValidateOptions{RequireStatusJSON: false})`.
- If artifact validation is blocked, return `Payload{Status:"blocked", Readiness:"blocked", Errors: result.Errors}`.
- Detect legacy status by calling `rt.ReadStatus(paths)` and checking `errors.Is(err, rt.ErrUnsupportedLegacy)`. Do not fail on legacy in this command.
- Open store with `store.Open(paths)`.
- Map scan package rows into `store.ImportInput`.
- Generate `GenerationID` with UTC timestamp prefix: `GEN-` + `time.Now().UTC().Format("20060102T150405.000000000Z")`.
- Derive path index rows from node paths:
  - for each node path, use first evidence ID when available
  - id format: `PI-` + sanitized path + `-` + sanitized node id
  - relation default: `"owns"`
  - confidence: node confidence or `"provisional"`
- For coverage paths with no node path relation, add a `store.RowDecision{Category:"coverage", Identity:path, Reason:"no_node_relation"}`.
- Call `st.ImportGeneration`.
- Build a status object with `Status="ok"`, `Freshness="fresh"`, `Readiness="query_ready"`, `RecommendedNextAction="use_project_cognition"`, `GraphReady=true`, `ActiveGenerationID=<id>`, `QueryContractVersion=1`, `UpdateContractVersion=1`.
- Call `rt.WriteStatus`.
- If status write fails, return `Payload{Status:"blocked", Readiness:"blocked", RecoveryAction:"rewrite_status_from_db_metadata"}` and the write error.
- Call `runtimegate.Check(paths)` after writing status. If blocked, return blocked payload with the agreement errors.
- Return counts and identity reconciliation summaries.

- [ ] **Step 4: Implement mapping helpers**

In `build.go`, add private helpers:

```go
func toImportInput(pkg scanartifacts.Package, generationID string) store.ImportInput
func scanCounts(pkg scanartifacts.Package) map[string]int
func dbCounts(snapshot store.IdentitySnapshot) map[string]int
func summarizeReconciliation(expected scanartifacts.IdentitySet, actual store.IdentitySnapshot) map[string]any
func sanitizeIDPart(value string) string
```

`summarizeReconciliation` must include at least:

- `evidence`
- `nodes`
- `edges`
- `observations`
- `coverage_paths`
- `missing`
- `unexpected`

Use `"ok"` for categories with no missing or unexpected identities.

- [ ] **Step 5: Verify build tests**

Run:

```powershell
go test ./internal/build ./internal/store ./internal/scanartifacts ./internal/runtimegate
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```powershell
git add tools/project-cognition/internal/build tools/project-cognition/internal/store/import.go
git commit -m "feat: add project cognition build from scan service"
```

---

### Task 5: Add CLI Command And Aliases

**Files:**
- Modify: `tools/project-cognition/internal/cli/cli.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`
- Test: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Write failing CLI tests**

Append to `cli_test.go`:

```go
func TestBuildFromScanCommandCreatesRuntime(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	writeCLIMinimalScanPackage(t, root)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"build-from-scan", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "ok" {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["identity_reconciliation"] == nil {
		t.Fatalf("payload missing identity_reconciliation: %#v", payload)
	}
}

func TestImportScanAliasUsesBuildFromScan(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	writeCLIMinimalScanPackage(t, root)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"import-scan", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	if !strings.Contains(stdout.String(), `"status": "ok"`) {
		t.Fatalf("stdout = %s", stdout.String())
	}
}
```

Append this local helper to `cli_test.go`:

```go
func writeCLIMinimalScanPackage(t *testing.T, root string) {
	t.Helper()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	writeCLIFile(t, filepath.Join(runtimeDir, "evidence", "E-001.json"), `{"id":"E-001","source_path":"src/app.go","content_hash":"hash-app","source_kind":"source","commit_sha":"abc123"}`)
	writeCLIFile(t, filepath.Join(runtimeDir, "provisional", "nodes.json"), `{"nodes":[{"id":"N-app","type":"capability","title":"App","confidence":"verified","paths":["src/app.go"],"evidence_ids":["E-001"]}]}`)
	writeCLIFile(t, filepath.Join(runtimeDir, "provisional", "edges.json"), `{"edges":[{"id":"EDGE-app-self","type":"owns","source_id":"N-app","target_id":"N-app","confidence":"verified","evidence_ids":["E-001"]}]}`)
	writeCLIFile(t, filepath.Join(runtimeDir, "provisional", "observations.json"), `{"observations":[{"id":"OBS-app","observation_type":"summary","summary":"App observed","evidence_ids":["E-001"]}]}`)
	writeCLIFile(t, filepath.Join(runtimeDir, "coverage.json"), `{"rows":[{"path":"src/app.go","coverage":"deep-read"}]}`)
	writeCLIFile(t, filepath.Join(runtimeDir, "workbench", "map-scan.md"), "# scan")
	writeCLIFile(t, filepath.Join(runtimeDir, "workbench", "coverage-ledger.md"), "# ledger")
	writeCLIFile(t, filepath.Join(runtimeDir, "workbench", "coverage-ledger.json"), `{"rows":[{"path":"src/app.go","owner":"scan"}],"open_gaps":[]}`)
	writeCLIFile(t, filepath.Join(runtimeDir, "workbench", "scan-packets", "lane-1.md"), "# lane")
	writeCLIFile(t, filepath.Join(runtimeDir, "workbench", "map-state.md"), "readiness=scan_ready")
	writeCLIFile(t, filepath.Join(runtimeDir, "workbench", "repository-universe.json"), `{"included_paths":["src/app.go"],"excluded_paths":[]}`)
	writeCLIFile(t, filepath.Join(runtimeDir, "workbench", "capability-ledger.json"), `{"rows":[]}`)
	writeCLIFile(t, filepath.Join(runtimeDir, "workbench", "control-ledger.json"), `{"rows":[]}`)
}

func writeCLIFile(t *testing.T, path string, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
		t.Fatal(err)
	}
}
```

- [ ] **Step 2: Run CLI tests and confirm failure**

Run:

```powershell
go test ./internal/cli
```

Expected: FAIL because the command is unknown.

- [ ] **Step 3: Wire CLI route**

Modify `tools/project-cognition/internal/cli/cli.go`:

- Import `internal/build`.
- Add cases:

```go
case "build-from-scan", "import-scan", "rebuild-from-scan":
	return buildFromScanCommand(args[1:], stdout, stderr, paths)
```

- Add command names to `printHelp`.
- Add:

```go
func buildFromScanCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("build-from-scan", flag.ContinueOnError)
	fs.SetOutput(stderr)
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := build.Run(paths)
	if err != nil && payload.Status == "" {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	return writeJSON(stdout, payload)
}
```

Return JSON with `status=blocked` and exit code 0 for validation-style blocked payloads. Return non-zero only when the command cannot produce a payload.

- [ ] **Step 4: Verify CLI tests**

Run:

```powershell
go test ./internal/cli ./internal/build
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```powershell
git add tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/cli/cli_test.go
git commit -m "feat: expose project cognition build-from-scan command"
```

---

### Task 6: Enforce Identity Reconciliation In `validate-build`

**Files:**
- Modify: `tools/project-cognition/internal/validation/build.go`
- Modify: `tools/project-cognition/internal/validation/build_test.go`
- Test: `tools/project-cognition/internal/validation/build_test.go`

- [ ] **Step 1: Write failing tests for truncated and substituted DB rows**

Append to `build_test.go`:

```go
func TestValidateBuildBlocksMissingScanNodeIdentity(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	writeValidationScanPackage(t, paths)
	seedQueryReadyDatabase(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.ActiveGenerationID = "GEN-0001"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationError(payload.Errors, "missing scan node identities") {
		t.Fatalf("Errors = %#v", payload.Errors)
	}
}

func TestValidateBuildBlocksSubstitutedNodeIdentityEvenWhenCountsMatch(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	writeValidationScanPackage(t, paths)
	seedQueryReadyDatabase(t, paths)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `UPDATE nodes SET id = 'N-wrong' WHERE id = 'capability:app'`); err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `UPDATE path_index SET node_id = 'N-wrong' WHERE node_id = 'capability:app'`); err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.ActiveGenerationID = "GEN-0001"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationError(payload.Errors, "unexpected DB node identities") {
		t.Fatalf("Errors = %#v", payload.Errors)
	}
}
```

Append this helper to `build_test.go`. It writes scan artifacts whose node id is
`N-app`, intentionally different from current `seedQueryReadyDatabase` node id
`capability:app`:

```go
func writeValidationScanPackage(t *testing.T, paths rt.Paths) {
	t.Helper()
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"), `{"id":"E-001","source_path":"src/app.go","content_hash":"hash","source_kind":"source","commit_sha":"abc123"}`)
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"), `{"nodes":[{"id":"N-app","type":"capability","title":"App","confidence":"verified","paths":["src/app.go"],"evidence_ids":["E-001"]}]}`)
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "provisional", "edges.json"), `{"edges":[]}`)
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "provisional", "observations.json"), `{"observations":[]}`)
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "coverage.json"), `{"rows":[{"path":"src/app.go"}]}`)
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "workbench", "map-scan.md"), "# scan")
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.md"), "# ledger")
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), `{"rows":[{"path":"src/app.go"}],"open_gaps":[]}`)
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-1.md"), "# lane")
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"), "readiness=scan_ready")
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), `{"included_paths":["src/app.go"],"excluded_paths":[]}`)
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "workbench", "capability-ledger.json"), `{"rows":[]}`)
	writeValidationFile(t, filepath.Join(paths.RuntimeDir, "workbench", "control-ledger.json"), `{"rows":[]}`)
}

func writeValidationFile(t *testing.T, path string, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
		t.Fatal(err)
	}
}
```

- [ ] **Step 2: Write failing test for DB/status agreement**

Append:

```go
func TestValidateBuildBlocksStatusDBActiveGenerationMismatch(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	seedQueryReadyDatabase(t, paths)
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if !hasValidationError(payload.Errors, "status.json active_generation_id") {
		t.Fatalf("Errors = %#v", payload.Errors)
	}
	if payload.Details["recovery_action"] != "rewrite_status_from_db_metadata" {
		t.Fatalf("Details = %#v", payload.Details)
	}
}
```

- [ ] **Step 3: Run validation tests and confirm failure**

Run:

```powershell
go test ./internal/validation
```

Expected: FAIL because identity reconciliation is not implemented.

- [ ] **Step 4: Implement identity reconciliation in `ValidateBuild`**

Modify `validation/build.go`:

- Call `runtimegate.Check(paths)` after `rt.ReadStatus`.
- If agreement is blocked, append agreement errors and set `payload.Details["recovery_action"]`.
- Call `scanartifacts.Load(paths, scanartifacts.ValidateOptions{RequireStatusJSON:false})`.
- If scan artifacts are present and artifact validation is `ok`, compare expected identities to `store.ActiveIdentitySnapshot`.
- Add details:
  - `scan_artifact_counts`
  - `db_counts`
  - `identity_reconciliation`
  - `rejections`
  - `merge_records`
- Missing expected identities are allowed only when a rejection or merge record covers the identity.
- Unexpected DB identities fail validation.
- Error phrases must include:
  - `missing scan evidence identities`
  - `missing scan node identities`
  - `missing scan edge identities`
  - `missing scan observation identities`
  - `missing scan coverage path identities`
  - `unexpected DB node identities`

- [ ] **Step 5: Keep existing acceptance test passing**

Update `TestValidateBuildAcceptsQueryReadyDatabase` to either:

- write a matching scan package whose identities match `seedQueryReadyDatabase`, or
- assert structural-only acceptance only when no scan package exists.

Preferred: create a matching scan package for the acceptance test so the new fidelity gate is exercised.

- [ ] **Step 6: Verify validation tests**

Run:

```powershell
go test ./internal/validation ./internal/scanartifacts ./internal/store ./internal/runtimegate
```

Expected: PASS.

- [ ] **Step 7: Commit Task 6**

```powershell
git add tools/project-cognition/internal/validation/build.go tools/project-cognition/internal/validation/build_test.go
git commit -m "feat: validate project cognition build identity reconciliation"
```

---

### Task 7: Apply DB/Status Agreement Gate To Baseline-Reading Commands

**Files:**
- Modify: `tools/project-cognition/internal/query/query.go`
- Modify: `tools/project-cognition/internal/query/lexicon.go`
- Modify: `tools/project-cognition/internal/query/query_test.go`
- Modify: `tools/project-cognition/internal/update/state.go`
- Modify: `tools/project-cognition/internal/update/state_test.go`
- Modify: `tools/project-cognition/internal/reference/discover.go`
- Modify: `tools/project-cognition/internal/reference/read.go`
- Create or modify: `tools/project-cognition/internal/reference/reference_test.go`
- Test: query, update, reference packages.

- [ ] **Step 1: Write failing query/lexicon agreement tests**

Append to `query_test.go`:

```go
func TestQueryBlocksStatusDBMismatch(t *testing.T) {
	paths := queryTestPathsWithSplitBrain(t)
	_, err := Run(paths, QueryInput{Intent: "implement", Query: "app"})
	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %v", err)
	}
}

func TestLexiconBlocksStatusDBMismatch(t *testing.T) {
	paths := queryTestPathsWithSplitBrain(t)
	_, err := Lexicon(paths, "implement", "app", 10)
	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %v", err)
	}
}
```

Append this helper to `query_test.go` and add imports for `context`, `strings`,
`rt`, and `store` if they are not already present:

```go
func queryTestPathsWithSplitBrain(t *testing.T) rt.Paths {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{GenerationID: "GEN-db", Kind: "full"}); err != nil {
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
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	return paths
}
```

- [ ] **Step 2: Write failing update agreement test**

Append to `update/state_test.go`:

```go
func TestRunUpdateBlocksStatusDBMismatch(t *testing.T) {
	paths := testPaths(t)
	seedUpdateSplitBrainRuntime(t, paths)

	_, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/app.go"},
		Reason:       "test",
	})

	if err == nil {
		t.Fatal("expected split-brain agreement error")
	}
	if !strings.Contains(err.Error(), "rewrite_status_from_db_metadata") {
		t.Fatalf("error = %v", err)
	}
}
```

Append this helper to `update/state_test.go` and add imports for `context` and
`store` if they are not already present:

```go
func seedUpdateSplitBrainRuntime(t *testing.T, paths rt.Paths) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{GenerationID: "GEN-db", Kind: "full"}); err != nil {
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
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}
```

- [ ] **Step 3: Write failing reference agreement tests**

Create `tools/project-cognition/internal/reference/reference_test.go`:

```go
package reference

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestDiscoverReportsSplitBrainAsBlocked(t *testing.T) {
	root := t.TempDir()
	paths := seedReferenceSplitBrain(t, root)

	payload, err := Discover(root)
	if err != nil {
		t.Fatal(err)
	}
	if len(payload.Projects) != 1 {
		t.Fatalf("projects = %#v", payload.Projects)
	}
	if payload.Projects[0].ReferenceReadiness != rt.BlockedReadiness {
		t.Fatalf("project = %#v", payload.Projects[0])
	}
	if len(payload.Projects[0].Blockers) == 0 {
		t.Fatalf("project = %#v, want blocker", payload.Projects[0])
	}
	_ = paths
}

func TestReadRejectsSplitBrainReference(t *testing.T) {
	root := t.TempDir()
	seedReferenceSplitBrain(t, root)

	_, err := Read(root, "overview", nil)
	if err == nil {
		t.Fatal("expected split-brain read error")
	}
}

func seedReferenceSplitBrain(t *testing.T, root string) rt.Paths {
	t.Helper()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{GenerationID: "GEN-db", Kind: "full"}); err != nil {
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
	status.ActiveGenerationID = "GEN-old"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	return paths
}
```

- [ ] **Step 4: Run targeted tests and confirm failure**

Run:

```powershell
go test ./internal/query ./internal/update ./internal/reference
```

Expected: FAIL because commands do not check agreement.

- [ ] **Step 5: Add agreement checks**

Implementation rules:

- In `query.Run`, call `runtimegate.Check(paths)` after `rt.ReadStatus` and before `store.Open`. If blocked, return an error containing `agreement.RecoveryAction`.
- In `query.Lexicon`, call the same gate before returning candidates.
- In `update.RunUpdate`, call the same gate before opening store or writing status. Keep `MarkDirty`, `RecordRefresh`, and `ClearDirty` status-only helpers unchanged unless tests show they read baseline graph state.
- In `update.CompleteRefresh`, call the gate before marking the runtime query-ready.
- In `reference.Discover`, run the gate for each candidate and set `ReferenceReadiness="blocked"` with blockers when split-brain is detected.
- In `reference.Read`, run the gate before accepting a reference project.

- [ ] **Step 6: Verify targeted tests**

Run:

```powershell
go test ./internal/query ./internal/update ./internal/reference ./internal/runtimegate
```

Expected: PASS.

- [ ] **Step 7: Commit Task 7**

```powershell
git add tools/project-cognition/internal/query tools/project-cognition/internal/update tools/project-cognition/internal/reference
git commit -m "feat: block project cognition split-brain reads"
```

---

### Task 8: Update `sp-map-build` Guidance And Template Tests

**Files:**
- Modify: `templates/commands/map-build.md`
- Modify: `templates/command-partials/map-build/shell.md`
- Modify: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/test_map_runtime_template_guidance.py` only if a failing
  assertion still expects `publish-runtime-metadata` or separate
  `complete-refresh` as normal map-build flow.
- Modify: `tests/test_alignment_templates.py` only if a failing assertion still
  expects `publish-runtime-metadata` or separate `complete-refresh` as normal
  map-build flow.
- Test: Python template tests.

- [ ] **Step 1: Write failing template assertions**

Modify `tests/test_map_scan_build_template_guidance.py`:

- In `test_map_build_template_refuses_incomplete_scan_packages`, replace old publication assertions with:

```python
assert "project-cognition build-from-scan --format json" in content
assert "project-cognition publish-runtime-metadata --format json" not in content
assert "manual sql" in lowered
assert "hand-picked node subsets" in lowered
assert "build-from-scan" in lowered
assert "identity reconciliation" in lowered
```

- Keep the `validate-build` assertion.
- Remove any assertion that build must run `complete-refresh` as a separate
  completion step; `build-from-scan` now owns build completion.

- [ ] **Step 2: Run template tests and confirm failure**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py -q
```

Expected: FAIL because templates still mention `publish-runtime-metadata`.

- [ ] **Step 3: Update map-build command template**

Modify `templates/commands/map-build.md`:

- Replace the top instruction that says to run `publish-runtime-metadata` after DB publication with:

```markdown
- Run `{{specify-subcmd:project-cognition build-from-scan --format json}}` after scan/package validation. This command owns SQLite import, metadata publication, Go-format `status.json`, and internal DB/status agreement checks.
```

- In Completion Rule, use this order:

```markdown
- run `{{specify-subcmd:project-cognition validate-scan --format json}}` before graph import
- run `{{specify-subcmd:project-cognition build-from-scan --format json}}`; if it returns `status=blocked`, report its `errors`, `identity_reconciliation`, `rejections`, `merge_records`, and `recovery_action`
- run `{{specify-subcmd:project-cognition validate-build --format json}}` after `build-from-scan`
- report completion only after `validate-build` returns `status=ok` and `readiness=query_ready`
```

- Add a guardrail:

```markdown
- Manual SQL, sqlite shell scripting, hand-picked node subsets, and leader-memory graph reconstruction are not accepted normal build paths.
```

- Remove normal-path `publish-runtime-metadata` and `complete-refresh` instructions. It is acceptable to mention `complete-refresh` only as a non-build maintenance command if the context requires it.

- [ ] **Step 4: Update shell partial**

Modify `templates/command-partials/map-build/shell.md`:

- Replace the context bullet that says to run `publish-runtime-metadata` with:

```markdown
- After scan acceptance, run `{{specify-subcmd:project-cognition build-from-scan --format json}}`; it owns DB import, metadata, status publication, and DB/status agreement.
```

- Add:

```markdown
- Do not construct `.specify/project-cognition/project-cognition.db` with manual SQL as the normal workflow path.
```

- [ ] **Step 5: Run alignment tests and update only failing assertions tied to this behavior**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py -q
```

Expected after template updates: either PASS or targeted failures for assertions that still expect `publish-runtime-metadata`/`complete-refresh`. Update those assertions to the new `build-from-scan` contract only when the failure points to map-build completion guidance.

- [ ] **Step 6: Commit Task 8**

```powershell
git add templates/commands/map-build.md templates/command-partials/map-build/shell.md tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py
git commit -m "docs: route map-build through build-from-scan"
```

---

### Task 9: End-To-End Verification Sweep

**Files:**
- Modify only files required by failing tests from this task.
- Test: full targeted Go and Python verification.

- [ ] **Step 1: Run Go runtime tests**

Run:

```powershell
go test ./...
```

from `tools/project-cognition`.

Expected: PASS.

- [ ] **Step 2: Run project template and runtime tests**

Run from repo root:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py tests/test_runtime_handbook_contract.py tests/test_project_cognition_launcher_rendering.py -q
```

Expected: PASS.

- [ ] **Step 3: Run a manual smoke scenario**

Create a temporary project and run the command sequence manually:

```powershell
$tmp = Join-Path $env:TEMP ("pc-build-smoke-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path (Join-Path $tmp ".specify/project-cognition/evidence") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $tmp ".specify/project-cognition/provisional") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $tmp ".specify/project-cognition/workbench/scan-packets") | Out-Null
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/evidence/E-001.json") -Encoding utf8NoBOM -Value '{"id":"E-001","source_path":"src/app.go","content_hash":"hash-app","source_kind":"source","commit_sha":"abc123"}'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/provisional/nodes.json") -Encoding utf8NoBOM -Value '{"nodes":[{"id":"N-app","type":"capability","title":"App","confidence":"verified","paths":["src/app.go"],"evidence_ids":["E-001"]}]}'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/provisional/edges.json") -Encoding utf8NoBOM -Value '{"edges":[{"id":"EDGE-app-self","type":"owns","source_id":"N-app","target_id":"N-app","confidence":"verified","evidence_ids":["E-001"]}]}'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/provisional/observations.json") -Encoding utf8NoBOM -Value '{"observations":[{"id":"OBS-app","observation_type":"summary","summary":"App observed","evidence_ids":["E-001"]}]}'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/coverage.json") -Encoding utf8NoBOM -Value '{"rows":[{"path":"src/app.go","coverage":"deep-read"}]}'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/workbench/map-scan.md") -Encoding utf8NoBOM -Value '# scan'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/workbench/coverage-ledger.md") -Encoding utf8NoBOM -Value '# ledger'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/workbench/coverage-ledger.json") -Encoding utf8NoBOM -Value '{"rows":[{"path":"src/app.go","owner":"scan"}],"open_gaps":[]}'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/workbench/scan-packets/lane-1.md") -Encoding utf8NoBOM -Value '# lane'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/workbench/map-state.md") -Encoding utf8NoBOM -Value 'readiness=scan_ready'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/workbench/repository-universe.json") -Encoding utf8NoBOM -Value '{"included_paths":["src/app.go"],"excluded_paths":[]}'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/workbench/capability-ledger.json") -Encoding utf8NoBOM -Value '{"rows":[]}'
Set-Content -Path (Join-Path $tmp ".specify/project-cognition/workbench/control-ledger.json") -Encoding utf8NoBOM -Value '{"rows":[]}'
Push-Location $tmp
& F:\github\spec-kit-plus\tools\project-cognition\project-cognition.exe build-from-scan --format json
& F:\github\spec-kit-plus\tools\project-cognition\project-cognition.exe validate-build --format json
Pop-Location
```

If no local binary exists yet, run `go run . build-from-scan --format json` and `go run . validate-build --format json` from `tools/project-cognition` with `-C` not available; instead temporarily `Push-Location` into the smoke project and invoke `go run F:\github\spec-kit-plus\tools\project-cognition`.

Expected:

- `build-from-scan` returns `status=ok`.
- `validate-build` returns `status=ok`, `readiness=query_ready`.
- The payload includes `identity_reconciliation`.

- [ ] **Step 4: Inspect final diff**

Run:

```powershell
git status --short
git diff --stat
git diff --check
```

Expected:

- only intended files changed
- no whitespace errors

- [ ] **Step 5: Commit final fixes if needed**

If Step 1-4 required additional fixes:

```powershell
git add <changed-files>
git commit -m "test: verify project cognition build pipeline"
```

If no additional fixes were needed, do not create an empty commit.

---

## Self-Review Checklist For Implementer

Before claiming complete:

- `project-cognition build-from-scan --format json` exists and aliases `import-scan` and `rebuild-from-scan` work.
- No normal workflow text tells agents to manually write SQLite rows.
- `validate-build` catches both truncated DB rows and substituted same-count DB rows.
- `build-from-scan` can create the first Go-format `status.json` without a pre-existing Go-format runtime.
- DB commit followed by status write failure returns `status=blocked` and `recovery_action=rewrite_status_from_db_metadata`.
- `query`, `lexicon`, `update`, `validate-build`, `complete-refresh`, `read`, and `discover` do not proceed through DB/status disagreement.
- All JSON written by tests uses UTF-8 without BOM.
- The final response reports Go and pytest verification commands actually run.

# Project Cognition Coverage Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make project cognition scan, build, and update flows account for every relevant path through a canonical boundary contract and machine validation.

**Architecture:** Evolve `.specify/project-cognition/workbench/repository-universe.json` into the single boundary artifact. Keep graph-facing coverage limited to included, non-excluded paths. Add validation in the Go `project-cognition` runtime, then align generated workflow templates and tests so leader/subagent behavior matches the runtime gate.

**Tech Stack:** Go project-cognition runtime, Python pytest template/contract tests, Markdown command templates.

---

## File Structure

- Modify `templates/commands/map-scan.md`: document `repository-universe.json` as the canonical boundary artifact, required schema fields, disposition rules, packet `assigned_paths`, overflow behavior, and the distinction between disposition and criticality.
- Modify `templates/command-partials/map-scan/shell.md`: add the short generated-command context for boundary planning before subagent dispatch.
- Modify `templates/commands/map-build.md`: require build intake to reject incomplete boundary coverage and keep excluded paths out of graph-facing coverage.
- Modify `templates/command-partials/map-build/shell.md`: add the short build-context statement for repository-universe validation.
- Modify `templates/commands/map-update.md`: require changed-path accounting with ignored-path reporting, partial readiness, and no full rebuild escalation except reserved conditions.
- Modify `templates/passive-skills/subagent-driven-development/SKILL.md`: add cross-workflow rule that delegated scan/update lanes must use explicit assigned paths and cannot silently narrow scope.
- Modify `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: align advisory guidance with boundary/disposition terminology and changed-path-first update accounting.
- Modify `tests/test_map_scan_build_template_guidance.py`: add assertions for canonical boundary artifact, disposition/criticality separation, excluded-path representation, packet assigned paths, and update accounting.
- Modify `tools/project-cognition/internal/scanartifacts/scanartifacts.go`: parse and validate `repository-universe.json`, compare candidate dispositions to graph-facing coverage, reject excluded-path leakage, and expose boundary details.
- Modify `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`: add unit tests for missing dispositions, excluded leakage, accepted included coverage, and legacy minimal `rows` compatibility if retained.
- Modify `tools/project-cognition/internal/validation/build.go`: use scan package boundary validation during build acceptance and reject DB graph rows that contain excluded paths.
- Modify `tools/project-cognition/internal/validation/build_test.go`: add build acceptance tests for incomplete boundary coverage and excluded path leakage.
- Modify `tools/project-cognition/internal/boundary/boundary.go`: extend update boundary result with per-path accounting metadata, including decision source and dispositions for changed paths.
- Modify `tools/project-cognition/internal/boundary/boundary_test.go`: add tests for ignored changed paths appearing only in boundary accounting and not in changed paths.
- Modify `tools/project-cognition/internal/update/state.go`: return changed-path accounting in `UpdatePayload.PathAdoption` and keep ignored paths out of `MinimalLiveReads`.
- Modify `tools/project-cognition/internal/update/state_test.go`: add tests for ignored-path accounting and no ignored path in minimal live reads.
- Modify `tests/project_cognition_fake.py`: keep Python hook tests aligned with stricter validation for repository-universe and excluded-path leakage.

---

### Task 1: Template Contract Updates

**Files:**
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/command-partials/map-scan/shell.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/command-partials/map-build/shell.md`
- Modify: `templates/commands/map-update.md`
- Modify: `templates/passive-skills/subagent-driven-development/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Test: `tests/test_map_scan_build_template_guidance.py`

- [ ] **Step 1: Add failing template assertions**

Add assertions to `tests/test_map_scan_build_template_guidance.py` in the existing map scan/build/update tests. Use exact phrases that should be present after the template edits:

```python
def test_map_scan_template_requires_canonical_boundary_contract() -> None:
    content = _read("templates/commands/map-scan.md")
    lowered = content.lower()

    assert "canonical boundary artifact" in lowered
    assert "`.specify/project-cognition/workbench/repository-universe.json`" in content
    assert "`schema_version`" in content
    assert "`candidate_universe`" in content
    assert "`decision_source`" in content
    assert "`assigned_paths`" in content
    assert "`deep_read`" in content
    assert "`inventory_only`" in content
    assert "disposition is separate from criticality" in lowered
    assert "excluded paths must not appear in graph-facing `coverage.json` rows" in lowered
    assert "overflow" in lowered


def test_map_build_template_rejects_incomplete_boundary_coverage() -> None:
    content = _read("templates/commands/map-build.md")
    lowered = content.lower()

    assert "repository-universe.json" in content
    assert "every included path is represented in scan coverage or an accepted gap" in lowered
    assert "excluded paths are represented only by the boundary artifact" in lowered
    assert "not by graph-facing coverage rows" in lowered
    assert "scan gap report" in lowered


def test_map_update_template_requires_changed_path_accounting() -> None:
    content = _read("templates/commands/map-update.md")
    lowered = content.lower()

    assert "every changed path must be accounted for" in lowered
    assert "ignored with reason" in lowered
    assert "partial with `minimal_live_reads`" in lowered
    assert "must not write `.cognitionignore`-excluded paths into update records" in lowered
    assert "reserved rebuild reason" in lowered
```

- [ ] **Step 2: Run the failing template test**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py -q
```

Expected: FAIL with missing phrase assertions for the new boundary contract.

- [ ] **Step 3: Update `map-scan` command template**

Edit `templates/commands/map-scan.md` so it states:

```markdown
## Canonical Boundary Contract

- `.specify/project-cognition/workbench/repository-universe.json` is the canonical boundary artifact.
- It must include `schema_version`, `candidate_universe`, `included_paths`, `excluded_paths`, `ambiguous_paths`, `dispositions`, `classification_reasons`, and `decision_source`.
- Every candidate path must receive exactly one disposition: `deep_read`, `sampled`, `inventory_only`, `excluded`, or `blocked`.
- Disposition is separate from criticality. Criticality remains `critical`, `important`, or `low_risk`.
- Excluded paths must not appear in graph-facing `coverage.json` rows, evidence rows, provisional nodes, provisional edges, observations, path indexes, route indexes, or `minimal_live_reads`.
- `MapScanPacket` must include bounded `assigned_paths`.
- Subagents must account for every assigned path with evidence, `sampled`, `inventory_only`, `excluded`, `blocked`, or `overflow`.
- If assigned paths do not fit in context, the subagent must return `overflow` or `blocked`; the leader must split and redispatch or record an open gap.
```

- [ ] **Step 4: Update `map-scan` shell partial**

Add this to `templates/command-partials/map-scan/shell.md` under Context:

```markdown
- Before subagent dispatch, write the canonical boundary in `.specify/project-cognition/workbench/repository-universe.json`; do not rely on user-maintained `.cognitionignore` as the primary boundary mechanism.
- Treat `.cognitionignore` as an override source recorded in `decision_source`; excluded paths stay in boundary accounting and out of graph-facing coverage.
```

- [ ] **Step 5: Update `map-build` command template**

Add this to `templates/commands/map-build.md` near Required Inputs or Build Duties:

```markdown
## Boundary Acceptance

`sp-map-build` must validate `.specify/project-cognition/workbench/repository-universe.json` before publishing runtime truth.

- Every `included_paths` entry must appear in `coverage.json`, `coverage-ledger.json`, or an accepted non-blocking gap.
- Every `excluded_paths` entry must stay only in the boundary artifact or grouped exclusion ledger.
- Excluded paths must not appear in graph-facing coverage rows, evidence rows, provisional graph rows, DB path indexes, route indexes, or `minimal_live_reads`.
- If repository-universe, coverage, and packet handoffs cannot explain the same path universe, return a scan gap report and route back to `sp-map-scan`.
```

- [ ] **Step 6: Update `map-build` shell partial**

Add this to `templates/command-partials/map-build/shell.md` under Context:

```markdown
- Validate `repository-universe.json` as the canonical scan boundary before graph reconstruction; excluded paths are boundary facts, not graph evidence.
```

- [ ] **Step 7: Update `map-update` command template**

Add this to `templates/commands/map-update.md` under Git Delta Intake or Incremental Rule:

```markdown
Every changed path must be accounted for as one of: updated, provisionally adopted, ignored with reason, partial with `minimal_live_reads`, blocked with recovery condition, or requiring full rebuild for a reserved rebuild reason.

Ignored `.cognitionignore` paths are reported in ignored-path accounting only. They must not be written into update records, known unknowns, `minimal_live_reads`, graph evidence, or route indexes.
```

- [ ] **Step 8: Update passive subagent skill**

Add this to `templates/passive-skills/subagent-driven-development/SKILL.md` under Dispatch Prompt Contract:

```markdown
- For scan, build, PRD scan, and map-update evidence lanes, include explicit `assigned_paths` or changed paths. A subagent must not silently narrow assigned scope; if the set does not fit, it returns `overflow` or `blocked` with the smallest safe split suggestion.
```

- [ ] **Step 9: Update cognition gate passive skill**

Add this to `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md` near map-update routing:

```markdown
- Treat repository boundary accounting as separate from graph evidence. `.cognitionignore` exclusions and automatic exclusions explain why a path is outside graph-facing coverage; they do not become project cognition evidence.
- For `map-update`, changed-path accounting must explain every candidate path before readiness can be considered useful.
```

- [ ] **Step 10: Run template tests**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 11: Commit template contract changes**

Run:

```powershell
git add templates/commands/map-scan.md templates/command-partials/map-scan/shell.md templates/commands/map-build.md templates/command-partials/map-build/shell.md templates/commands/map-update.md templates/passive-skills/subagent-driven-development/SKILL.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md tests/test_map_scan_build_template_guidance.py
git commit -m "docs: define project cognition boundary contract"
```

Expected: commit succeeds.

---

### Task 2: Scan Boundary Validation

**Files:**
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts.go`
- Modify: `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`
- Test: `tools/project-cognition/internal/scanartifacts`

- [ ] **Step 1: Add failing scan validation tests**

Add these tests to `tools/project-cognition/internal/scanartifacts/scanartifacts_test.go`:

```go
func TestValidateBlocksIncludedCandidateWithoutCoverageOrGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"deep_read"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included path src/missing.go has no coverage row or accepted gap") {
		t.Fatalf("Errors = %#v, want missing included path coverage error", result.Errors)
	}
}

func TestValidateBlocksExcludedPathInCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/app.go"},{"path":"vendor/lib.go"}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[{"path":"vendor/lib.go","reason":"vendor","decision_source":".cognitionignore"}],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "excluded path vendor/lib.go must not appear in coverage.json") {
		t.Fatalf("Errors = %#v, want excluded coverage error", result.Errors)
	}
}

func TestValidateAcceptsBoundaryExcludedPathOutsideCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[{"path":"vendor/lib.go","reason":"vendor","decision_source":".cognitionignore"}],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}
```

- [ ] **Step 2: Run failing Go scan tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/scanartifacts
cd ..\..
```

Expected: FAIL because boundary validation is not implemented.

- [ ] **Step 3: Add boundary model types and loader**

In `tools/project-cognition/internal/scanartifacts/scanartifacts.go`, add:

```go
type Boundary struct {
	SchemaVersion         int
	CandidatePaths        map[string]string
	IncludedPaths         map[string]bool
	ExcludedPaths         map[string]bool
	AmbiguousPaths        map[string]bool
	Dispositions          map[string]string
	ClassificationReasons map[string]string
	DecisionSource        map[string]string
}
```

Add helper functions:

```go
func loadBoundary(paths rt.Paths, result *Result) Boundary
func boundaryPathsFromValue(value any) map[string]bool
func boundaryDispositionMap(value any) map[string]string
func boundaryCandidatePaths(value any) map[string]string
func validateBoundaryCoverage(boundary Boundary, pkg Package, result *Result)
func acceptedGapPaths(paths rt.Paths) map[string]bool
```

Implementation rules:

- Read `.specify/project-cognition/workbench/repository-universe.json`.
- Accept legacy `{"rows":[{"path":"src/app.go"}]}` by treating rows as included candidates with unknown schema version and warning-free compatibility.
- For versioned shape, read `candidate_universe`, `included_paths`, `excluded_paths`, `ambiguous_paths`, `dispositions`, `classification_reasons`, and `decision_source`.
- Normalize paths with existing `normalizedString`.
- Allow `excluded_paths` as either strings or objects with `path`.
- Allow `included_paths` and `ambiguous_paths` as strings or objects with `path`.
- Allow `candidate_universe` as strings or objects with `path`, `disposition`, and `decision_source`.
- For every candidate path, require a non-empty disposition from `dispositions` or candidate object.
- Valid dispositions are `deep_read`, `sampled`, `inventory_only`, `excluded`, `blocked`.
- Included paths with dispositions `deep_read`, `sampled`, or `inventory_only` must appear in `pkg.CoveragePaths` or accepted gaps.
- Excluded paths must not appear in `pkg.CoveragePaths`.

- [ ] **Step 4: Wire boundary validation into scan load**

In `Load`, after `loadCoverage(paths, &pkg, &result)`, call:

```go
boundary := loadBoundary(paths, &result)
validateBoundaryCoverage(boundary, pkg, &result)
result.Details["boundary"] = map[string]any{
	"candidate_count": len(boundary.CandidatePaths),
	"included_count": len(boundary.IncludedPaths),
	"excluded_count": len(boundary.ExcludedPaths),
	"ambiguous_count": len(boundary.AmbiguousPaths),
}
```

Keep existing required artifact checks unchanged.

- [ ] **Step 5: Run Go scan tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/scanartifacts
cd ..\..
```

Expected: PASS.

- [ ] **Step 6: Commit scan validation**

Run:

```powershell
git add tools/project-cognition/internal/scanartifacts/scanartifacts.go tools/project-cognition/internal/scanartifacts/scanartifacts_test.go
git commit -m "fix: validate project cognition scan boundary"
```

Expected: commit succeeds.

---

### Task 3: Build Validation For Boundary Leakage

**Files:**
- Modify: `tools/project-cognition/internal/validation/build.go`
- Modify: `tools/project-cognition/internal/validation/build_test.go`
- Test: `tools/project-cognition/internal/validation`

- [ ] **Step 1: Add failing build tests**

Add to `tools/project-cognition/internal/validation/build_test.go`:

```go
func TestValidateBuildBlocksExcludedBoundaryPathInDB(t *testing.T) {
	paths := validationTestPaths(t)
	writeBuildAcceptanceInputs(t, paths)
	writeMatchingScanPackage(t, paths)
	writeFile(paths, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), `{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[{"path":"vendor/lib.go","reason":"vendor","decision_source":".cognitionignore"}],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`)
	seedMatchingQueryReadyDatabase(t, paths, nil, nil)
	st, err := store.OpenExisting(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES('P-vendor', 'GEN-0001', 'vendor/lib.go', 'N-app', 'owns', 'weak', 'E-001', 'now')`); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	writeReadyStatus(t, paths, "GEN-0001")

	payload := ValidateBuild(paths)

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", payload.Status, payload.Errors)
	}
	if !hasValidationError(payload.Errors, "excluded boundary path vendor/lib.go must not enter project cognition graph store") {
		t.Fatalf("Errors = %#v, want excluded boundary path error", payload.Errors)
	}
}
```

Add helper if not already present:

```go
func writeFile(t *testing.T, paths rt.Paths, path string, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content+"\n"), 0o644); err != nil {
		t.Fatal(err)
	}
}
```

- [ ] **Step 2: Run failing build validation tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/validation
cd ..\..
```

Expected: FAIL because build validation checks `.specify/**` leakage but not boundary excluded paths.

- [ ] **Step 3: Add excluded boundary path extraction**

In `tools/project-cognition/internal/validation/build.go`, add helper functions near graph validation:

```go
func excludedBoundaryPaths(paths rt.Paths) map[string]bool
func graphPathTableChecks() []struct { table string; column string }
```

Implementation:

- Read `.specify/project-cognition/workbench/repository-universe.json`.
- Parse `excluded_paths` as string array or object array with `path`.
- Normalize with `filepath.ToSlash(strings.TrimSpace(...))`.
- Return empty map when file is missing or malformed; scan validation already owns malformed scan package diagnostics.

- [ ] **Step 4: Reject excluded boundary paths in graph store**

In `validateGraphStore`, before or after the `.specify/**` leak check, load:

```go
excluded := excludedBoundaryPaths(paths)
```

When iterating `path_index.path`, `evidence.source_path`, `symbol_index.path`, `entrypoint_index.path`, and `test_index.test_path`, add:

```go
if excluded[normalized] {
	errors = append(errors, fmt.Sprintf("excluded boundary path %s must not enter project cognition graph store", normalized))
	break
}
```

- [ ] **Step 5: Run build validation tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/validation
cd ..\..
```

Expected: PASS.

- [ ] **Step 6: Commit build validation**

Run:

```powershell
git add tools/project-cognition/internal/validation/build.go tools/project-cognition/internal/validation/build_test.go
git commit -m "fix: reject excluded paths from cognition graph store"
```

Expected: commit succeeds.

---

### Task 4: Map Update Changed-Path Accounting

**Files:**
- Modify: `tools/project-cognition/internal/boundary/boundary.go`
- Modify: `tools/project-cognition/internal/boundary/boundary_test.go`
- Modify: `tools/project-cognition/internal/update/state.go`
- Modify: `tools/project-cognition/internal/update/state_test.go`
- Test: `tools/project-cognition/internal/boundary`, `tools/project-cognition/internal/update`

- [ ] **Step 1: Add failing boundary accounting test**

Add to `tools/project-cognition/internal/boundary/boundary_test.go`:

```go
func TestResolveReportsPerPathAccounting(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatalf("write .cognitionignore: %v", err)
	}

	result := Resolve(ResolveInput{
		Root: root,
		Config: config.Config{
			ProjectCognition: config.ProjectCognitionConfig{AutoCommit: true},
		},
		Bundle: delta.Bundle{
			Events: []delta.Event{
				{ChangedPaths: []string{"src/a.go", "vendor/a.go"}},
			},
		},
	})

	if result.PathAccounting["src/a.go"].Disposition != "updated" {
		t.Fatalf("src accounting = %#v, want updated", result.PathAccounting["src/a.go"])
	}
	if result.PathAccounting["vendor/a.go"].Disposition != "ignored" {
		t.Fatalf("vendor accounting = %#v, want ignored", result.PathAccounting["vendor/a.go"])
	}
	if result.PathAccounting["vendor/a.go"].DecisionSource == "" {
		t.Fatalf("vendor accounting = %#v, want decision source", result.PathAccounting["vendor/a.go"])
	}
}
```

- [ ] **Step 2: Add failing update payload test**

Add to `tools/project-cognition/internal/update/state_test.go`:

```go
func TestRunUpdateKeepsIgnoredPathsOutOfMinimalLiveReads(t *testing.T) {
	paths := testPaths(t)
	if err := os.WriteFile(filepath.Join(paths.Root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/a.go", "vendor/a.go"},
		Reason:       "manual",
	})
	if err != nil {
		t.Fatal(err)
	}

	if containsText(payload.MinimalLiveReads, "vendor/a.go") {
		t.Fatalf("MinimalLiveReads = %#v, ignored path must not appear", payload.MinimalLiveReads)
	}
	if !containsText(payload.IgnoredPaths, "vendor/a.go") {
		t.Fatalf("IgnoredPaths = %#v, want vendor/a.go", payload.IgnoredPaths)
	}
	accounting, ok := payload.PathAdoption["path_accounting"].(map[string]any)
	if !ok {
		t.Fatalf("PathAdoption = %#v, want path_accounting", payload.PathAdoption)
	}
	if _, ok := accounting["vendor/a.go"]; !ok {
		t.Fatalf("path_accounting = %#v, want vendor/a.go", accounting)
	}
}
```

- [ ] **Step 3: Run failing update tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/boundary ./internal/update
cd ..\..
```

Expected: FAIL because `PathAccounting` does not exist.

- [ ] **Step 4: Extend boundary result types**

In `tools/project-cognition/internal/boundary/boundary.go`, add:

```go
type PathAccounting struct {
	Path           string `json:"path"`
	Disposition    string `json:"disposition"`
	DecisionSource string `json:"decision_source"`
	Reason         string `json:"reason"`
}
```

Add to `Result`:

```go
PathAccounting map[string]PathAccounting `json:"path_accounting"`
```

Populate it in `Resolve`:

- For kept workflow-owned paths: `Disposition: "updated"`, `DecisionSource: boundarySource`.
- For ambiguous initial dirty paths: `Disposition: "partial"`, `DecisionSource: boundarySource`, `Reason: "ambiguous_initial_dirty_path"`.
- For ignored paths: `Disposition: "ignored"`, `DecisionSource: ".cognitionignore"`, `Reason: "matched cognition ignore rule"`.

- [ ] **Step 5: Add update path accounting to non-delta RunUpdate**

In `tools/project-cognition/internal/update/state.go`, build a `pathAccounting` map for non-delta updates:

```go
pathAccounting := map[string]any{}
for _, path := range kept {
	pathAccounting[path] = map[string]any{
		"disposition": "updated",
		"decision_source": "changed_paths",
		"reason": "kept for project cognition update",
	}
}
for _, path := range ignored {
	pathAccounting[path] = map[string]any{
		"disposition": "ignored",
		"decision_source": ".cognitionignore",
		"reason": "matched cognition ignore rule",
	}
}
```

Change `pathAdoption` to include:

```go
"path_accounting": pathAccounting,
```

Keep `MinimalLiveReads: kept`.

- [ ] **Step 6: Add delta path accounting to RunUpdate**

In `runDeltaSessionUpdate`, add to `PathAdoption`:

```go
"path_accounting": result.PathAccounting,
```

- [ ] **Step 7: Run boundary/update tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/boundary ./internal/update
cd ..\..
```

Expected: PASS.

- [ ] **Step 8: Commit update accounting**

Run:

```powershell
git add tools/project-cognition/internal/boundary/boundary.go tools/project-cognition/internal/boundary/boundary_test.go tools/project-cognition/internal/update/state.go tools/project-cognition/internal/update/state_test.go
git commit -m "fix: account for map update changed paths"
```

Expected: commit succeeds.

---

### Task 5: Fake Runtime And Integration Test Alignment

**Files:**
- Modify: `tests/project_cognition_fake.py`
- Test: Python hook/integration contract tests that use fake project cognition

- [ ] **Step 1: Add stricter fake validation behavior**

In `tests/project_cognition_fake.py`, update `_validate_scan()` so it also checks:

```python
universe_path = Path.cwd() / ".specify/project-cognition/workbench/repository-universe.json"
if universe_path.exists():
    try:
        universe = json.loads(universe_path.read_text(encoding="utf-8"))
        if isinstance(universe, dict):
            excluded = set()
            for item in universe.get("excluded_paths", []):
                if isinstance(item, str):
                    excluded.add(item.replace("\\", "/"))
                elif isinstance(item, dict):
                    path = str(item.get("path", "")).replace("\\", "/")
                    if path:
                        excluded.add(path)
            coverage_paths = set()
            if coverage_path.exists():
                coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
                for row in coverage.get("rows", []) if isinstance(coverage, dict) else []:
                    if isinstance(row, dict):
                        path = str(row.get("path", "")).replace("\\", "/")
                        if path:
                            coverage_paths.add(path)
            leaked = sorted(excluded & coverage_paths)
            if leaked:
                errors.append(f"excluded path {leaked[0]} must not appear in coverage.json")
    except json.JSONDecodeError as exc:
        errors.append(f".specify/project-cognition/workbench/repository-universe.json: {exc}")
```

- [ ] **Step 2: Run focused Python tests**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/contract/test_hook_cli_surface.py tests/hooks/test_preflight_hooks.py -q
```

Expected: PASS after updating fixtures if needed.

- [ ] **Step 3: Update failing fixtures only if necessary**

If tests fail because fake scan fixtures use `repository-universe.json` rows only, keep the fake validator backward-compatible with `rows`. If tests fail because fixtures put excluded paths in coverage, update those fixture payloads so excluded paths are represented only in repository universe.

- [ ] **Step 4: Commit fake runtime alignment**

Run:

```powershell
git add tests/project_cognition_fake.py tests/contract/test_hook_cli_surface.py tests/hooks/test_preflight_hooks.py
git commit -m "test: align fake cognition validation with boundary contract"
```

Expected: commit succeeds. If no fixture files changed, omit them from `git add`.

---

### Task 6: Full Verification

**Files:**
- No planned source edits unless verification exposes a defect.

- [ ] **Step 1: Run Go runtime tests**

Run:

```powershell
cd tools/project-cognition
go test ./...
cd ..\..
```

Expected: PASS.

- [ ] **Step 2: Run focused Python regression tests**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py tests/test_command_surface_semantics.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_markdown.py -q
```

Expected: PASS.

- [ ] **Step 3: Run broader project cognition hook tests**

Run:

```powershell
pytest tests/hooks/test_preflight_hooks.py tests/contract/test_hook_cli_surface.py tests/test_project_map_freshness_scripts.py -q
```

Expected: PASS.

- [ ] **Step 4: Review git diff**

Run:

```powershell
git status --short
git diff --stat HEAD
```

Expected: only intended files are modified or committed. If uncommitted changes remain, inspect with `git diff` and either commit intended changes or fix the missed step.

- [ ] **Step 5: Final commit if verification fixes were needed**

If verification required additional edits, commit them:

```powershell
git add templates/commands/map-scan.md templates/command-partials/map-scan/shell.md templates/commands/map-build.md templates/command-partials/map-build/shell.md templates/commands/map-update.md templates/passive-skills/subagent-driven-development/SKILL.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md tests/test_map_scan_build_template_guidance.py tools/project-cognition/internal/scanartifacts/scanartifacts.go tools/project-cognition/internal/scanartifacts/scanartifacts_test.go tools/project-cognition/internal/validation/build.go tools/project-cognition/internal/validation/build_test.go tools/project-cognition/internal/boundary/boundary.go tools/project-cognition/internal/boundary/boundary_test.go tools/project-cognition/internal/update/state.go tools/project-cognition/internal/update/state_test.go tests/project_cognition_fake.py tests/contract/test_hook_cli_surface.py tests/hooks/test_preflight_hooks.py
git commit -m "fix: complete cognition boundary verification"
```

Expected: commit succeeds.

---

## Self-Review Notes

- Spec coverage: The plan covers canonical `repository-universe.json`, excluded-path representation, disposition/criticality separation, scan/build validation, and map-update changed-path accounting.
- Scope: This is a single subsystem: project cognition boundary and validation. It touches templates, runtime validation, and tests because the repository treats generated workflow behavior as product surface.
- Risk: The largest risk is making validation too strict for existing legacy scan packages. Task 2 preserves compatibility for minimal `{"rows":[...]}` repository-universe files while enforcing the new contract when versioned fields are present.

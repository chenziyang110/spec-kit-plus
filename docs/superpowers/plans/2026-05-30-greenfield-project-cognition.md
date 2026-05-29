# Greenfield Project Cognition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fresh `specify init` projects get a real query-ready `project-cognition.db` and `status.json` without running `sp-map-scan -> sp-map-build` when there is no business code to scan.

**Architecture:** Add an explicit `baseline_kind` runtime identity, then create a runtime-owned `project-cognition init-empty` command that writes a greenfield-empty SQLite baseline. Validation, query, Python init, generated guidance, and docs read that identity so greenfield projects continue while brownfield baselines keep strict scan/build gates.

**Tech Stack:** Go `project-cognition` runtime with `modernc.org/sqlite`, Python Typer CLI, pytest integration tests, Markdown template/doc surfaces.

---

## File Structure

- `tools/project-cognition/internal/runtime/status.go`: add `BaselineKind` to persisted status and shared constants.
- `tools/project-cognition/internal/store/store.go`: add greenfield-empty DB creation, active generation kind lookup, baseline-kind metadata publication, and greenfield inventory detection helpers.
- `tools/project-cognition/internal/store/import.go`: make normal scan/build import metadata carry `baseline_kind=brownfield_full`.
- `tools/project-cognition/internal/build/build.go`: write `BaselineKindBrownfieldFull` in status for normal build-from-scan publications.
- `tools/project-cognition/internal/buildgate/sparse.go`: skip sparse path-index gates only for verified greenfield-empty generations.
- `tools/project-cognition/internal/runtimegate/agreement.go`: include baseline kind in agreement checks and require DB/status/generation agreement.
- `tools/project-cognition/internal/validation/build.go`: allow zero graph rows only for verified greenfield-empty baselines.
- `tools/project-cognition/internal/query/lexicon.go`: expose greenfield-empty payload state and honest empty candidate coverage.
- `tools/project-cognition/internal/query/query.go`: return greenfield-empty minimal live reads and baseline kind.
- `tools/project-cognition/internal/cli/cli.go`: add `init-empty` to command dispatch and help.
- `tools/project-cognition/internal/cli/cli_test.go`: add runtime CLI tests for init-empty, greenfield query behavior, and brownfield baseline kind.
- `src/specify_cli/project_cognition_runtime.py`: require `init-empty` in cached/release runtime compatibility checks.
- `src/specify_cli/__init__.py`: invoke `project-cognition init-empty --format json` after pinning the runtime.
- `tests/test_project_cognition_runtime_install.py`: add Python tests for required command refresh and init-time bootstrap invocation.
- `src/specify_cli/integrations/base.py`: add greenfield-empty routing to generated project cognition addenda.
- `src/specify_cli/integrations/cursor_agent/__init__.py`: add the same routing to Cursor-specific addendum.
- `templates/command-partials/common/context-loading-gradient.md`: update shared runtime routing.
- `templates/command-partials/common/planning-context-loading-gradient.md`: update planning-specific runtime routing.
- `templates/command-partials/common/navigation-check.md`: update navigation summaries.
- `templates/command-partials/common/senior-consequence-analysis-gate.md`: update consequence-gate routing.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: update passive skill routing.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: update workflow routing skill.
- `README.md`, `PROJECT-HANDBOOK.md`, `docs/quickstart.md`, `docs/installation.md`: document greenfield bootstrap and preserve brownfield rules.
- `tests/test_alignment_templates.py`, `tests/test_command_surface_semantics.py`, `tests/integrations/test_integration_base_markdown.py`, `tests/integrations/test_integration_cursor_agent.py`: update wording and generated-output assertions.

## Task 1: Runtime Status Identity

**Files:**
- Modify: `tools/project-cognition/internal/runtime/status.go`
- Test: `tools/project-cognition/internal/runtime/status_test.go`

- [ ] **Step 1: Write failing status round-trip test**

Add this test to `tools/project-cognition/internal/runtime/status_test.go`:

```go
func TestStatusRoundTripPreservesBaselineKind(t *testing.T) {
	paths := testPaths(t)
	status := DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = ReadyFreshness
	status.Readiness = ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-greenfield-test"
	status.BaselineKind = BaselineKindGreenfieldEmpty

	if err := WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	loaded, err := ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if loaded.BaselineKind != BaselineKindGreenfieldEmpty {
		t.Fatalf("BaselineKind = %q, want %q", loaded.BaselineKind, BaselineKindGreenfieldEmpty)
	}
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd tools/project-cognition
go test ./internal/runtime -run TestStatusRoundTripPreservesBaselineKind -count=1
```

Expected: FAIL with undefined `BaselineKind` or undefined `BaselineKindGreenfieldEmpty`.

- [ ] **Step 3: Add baseline kind constants and status field**

In `tools/project-cognition/internal/runtime/status.go`, add constants near the existing runtime constants:

```go
const (
	RuntimeFormat         = "project-cognition-go"
	RuntimeSchema         = 1
	ErrLegacyCode         = "unsupported_legacy_runtime"
	MissingFreshness      = "missing"
	ReadyFreshness        = "fresh"
	StaleFreshness        = "stale"
	ReadyReadiness        = "query_ready"
	BlockedReadiness      = "blocked"
	NeedsRebuildReadiness = "needs_rebuild"
	UnsupportedReadiness  = "unsupported_runtime"
	BaselineKindBrownfieldFull   = "brownfield_full"
	BaselineKindGreenfieldEmpty  = "greenfield_empty"
)
```

Then add the JSON field to `Status` after `ActiveGenerationID`:

```go
BaselineKind string `json:"baseline_kind,omitempty"`
```

Do not set a baseline kind in `DefaultStatus`; missing status remains missing and should not masquerade as greenfield.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
cd tools/project-cognition
go test ./internal/runtime -run TestStatusRoundTripPreservesBaselineKind -count=1
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tools/project-cognition/internal/runtime/status.go tools/project-cognition/internal/runtime/status_test.go
git commit -m "feat: track project cognition baseline kind"
```

## Task 2: Store Greenfield Bootstrap

**Files:**
- Modify: `tools/project-cognition/internal/store/store.go`
- Test: `tools/project-cognition/internal/store/import_test.go`

- [ ] **Step 1: Write failing store bootstrap test**

Add this test to `tools/project-cognition/internal/store/import_test.go`:

```go
func TestInitializeGreenfieldEmptyCreatesReadyEmptyGeneration(t *testing.T) {
	paths := testPaths(t)
	st, err := Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()

	generationID, err := st.InitializeGreenfieldEmpty(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if generationID == "" {
		t.Fatal("generationID is empty")
	}

	activeGenerationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if activeGenerationID != generationID {
		t.Fatalf("active generation = %q, want %q", activeGenerationID, generationID)
	}

	kind, err := st.ActiveGenerationKind(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if kind != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("generation kind = %q, want %q", kind, rt.BaselineKindGreenfieldEmpty)
	}

	meta, err := st.Metadata(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if meta["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("metadata baseline_kind = %q, want %q", meta["baseline_kind"], rt.BaselineKindGreenfieldEmpty)
	}
	if meta["graph_ready"] != "true" {
		t.Fatalf("metadata graph_ready = %q, want true", meta["graph_ready"])
	}

	snapshot, err := st.ActiveIdentitySnapshot(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(snapshot.Nodes) != 0 || len(snapshot.Evidence) != 0 || len(snapshot.CoveragePaths) != 0 {
		t.Fatalf("greenfield snapshot = %#v, want empty graph rows", snapshot)
	}
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd tools/project-cognition
go test ./internal/store -run TestInitializeGreenfieldEmptyCreatesReadyEmptyGeneration -count=1
```

Expected: FAIL with undefined `InitializeGreenfieldEmpty` or `ActiveGenerationKind`.

- [ ] **Step 3: Add store helper signatures and active kind reader**

In `tools/project-cognition/internal/store/store.go`, add these methods after `ActiveGenerationID`:

```go
func (s *Store) ActiveGenerationKind(ctx context.Context) (string, error) {
	rows, err := s.db.QueryContext(ctx, `SELECT kind FROM generations WHERE state = 'active' ORDER BY sequence DESC, id DESC LIMIT 1`)
	if err != nil {
		return "", fmt.Errorf("read active generation kind: %w", err)
	}
	defer rows.Close()
	if !rows.Next() {
		return "", nil
	}
	var kind string
	if err := rows.Scan(&kind); err != nil {
		return "", fmt.Errorf("scan active generation kind: %w", err)
	}
	return kind, rows.Err()
}
```

- [ ] **Step 4: Add ready metadata writer with baseline kind**

Change `PublishRuntimeMetadata` signature in `store.go` from:

```go
func (s *Store) PublishRuntimeMetadata(ctx context.Context, expectedGenerationID string, afterCommit ...func() error) (map[string]string, string, error) {
```

to:

```go
func (s *Store) PublishRuntimeMetadata(ctx context.Context, expectedGenerationID string, baselineKind string, afterCommit ...func() error) (map[string]string, string, error) {
	if strings.TrimSpace(baselineKind) == "" {
		baselineKind = rt.BaselineKindBrownfieldFull
	}
```

Then add `"baseline_kind": baselineKind,` to the `pairs` map inside that method:

```go
pairs := map[string]any{
	"runtime_format":          rt.RuntimeFormat,
	"runtime_schema":          rt.RuntimeSchema,
	"schema_version":          SchemaVersion,
	"active_generation_id":    generationID,
	"graph_store_path":        ".specify/project-cognition/project-cognition.db",
	"graph_ready":             true,
	"baseline_state":          "fresh",
	"baseline_kind":           baselineKind,
	"query_contract_version":  1,
	"update_contract_version": 1,
	"published_at":            now,
}
```

- [ ] **Step 5: Update existing PublishRuntimeMetadata call sites to compile**

In every current call site, pass `rt.BaselineKindBrownfieldFull` unless the code is greenfield bootstrap. The exact replacements are:

```go
st.PublishRuntimeMetadata(context.Background(), generationID, rt.BaselineKindBrownfieldFull, func() error {
```

and:

```go
st.PublishRuntimeMetadata(context.Background(), activeGenerationID, rt.BaselineKindBrownfieldFull, func() error {
```

- [ ] **Step 6: Add InitializeGreenfieldEmpty**

Add this method to `store.go` after `PublishRuntimeMetadata`:

```go
func (s *Store) InitializeGreenfieldEmpty(ctx context.Context) (string, error) {
	now := time.Now().UTC().Format(time.RFC3339)
	generationID := "GEN-greenfield-" + time.Now().UTC().Format("20060102T150405.000000000Z")
	input := ImportInput{
		GenerationID: generationID,
		Kind:         rt.BaselineKindGreenfieldEmpty,
		SourceCommit: "",
		Evidence:     []EvidenceImport{},
		Nodes:        []NodeImport{},
		Edges:        []EdgeImport{},
		Observations: []ObservationImport{},
		PathIndex:    []PathIndexImport{},
		Rejections:   []RowDecision{},
		MergeRecords: []MergeRecord{},
	}
	importedGenerationID, err := s.ImportGeneration(ctx, input)
	if err != nil {
		return "", err
	}
	meta, readyGenerationID, err := s.PublishRuntimeMetadata(ctx, importedGenerationID, rt.BaselineKindGreenfieldEmpty)
	if err != nil {
		return "", err
	}
	if readyGenerationID != importedGenerationID {
		return "", fmt.Errorf("greenfield metadata active generation mismatch: got %s, want %s", readyGenerationID, importedGenerationID)
	}
	if meta["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		return "", fmt.Errorf("greenfield metadata baseline_kind = %q, want %q", meta["baseline_kind"], rt.BaselineKindGreenfieldEmpty)
	}
	_ = now
	return importedGenerationID, nil
}
```

If Go reports `now` is unused after implementation cleanup, remove the `now` variable and `_ = now` line together.

- [ ] **Step 7: Allow empty import references**

Confirm `validateImportReferences` already accepts empty slices. Do not add fake evidence or path rows.

- [ ] **Step 8: Run store tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/store -run TestInitializeGreenfieldEmptyCreatesReadyEmptyGeneration -count=1
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add tools/project-cognition/internal/store/store.go tools/project-cognition/internal/store/import.go tools/project-cognition/internal/build/build.go tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/store/import_test.go
git commit -m "feat: create greenfield cognition baseline"
```

## Task 3: `project-cognition init-empty` CLI

**Files:**
- Modify: `tools/project-cognition/internal/cli/cli.go`
- Modify: `tools/project-cognition/internal/store/store.go`
- Test: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Write failing CLI test for empty init**

Add this test to `tools/project-cognition/internal/cli/cli_test.go`:

```go
func TestInitEmptyCommandCreatesGreenfieldRuntime(t *testing.T) {
	root := t.TempDir()
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"init-empty", "--format", "json"}, &stdout, &stderr, "test")
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
	if payload["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("baseline_kind = %#v, payload = %#v", payload["baseline_kind"], payload)
	}
	if payload["readiness"] != rt.ReadyReadiness {
		t.Fatalf("readiness = %#v, payload = %#v", payload["readiness"], payload)
	}

	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(paths.StatusPath); err != nil {
		t.Fatalf("status.json missing: %v", err)
	}
	if _, err := os.Stat(paths.DatabasePath); err != nil {
		t.Fatalf("project-cognition.db missing: %v", err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.BaselineKind != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("status baseline kind = %q", status.BaselineKind)
	}
}
```

- [ ] **Step 2: Write failing CLI test for existing baseline**

Add this test to the same file:

```go
func TestInitEmptyCommandDoesNotOverwriteExistingRuntime(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	before, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"init-empty", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["already_initialized"] != true {
		t.Fatalf("already_initialized = %#v, payload = %#v", payload["already_initialized"], payload)
	}
	after, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if after.ActiveGenerationID != before.ActiveGenerationID {
		t.Fatalf("active generation changed: before=%s after=%s", before.ActiveGenerationID, after.ActiveGenerationID)
	}
}
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
cd tools/project-cognition
go test ./internal/cli -run "TestInitEmptyCommand" -count=1
```

Expected: FAIL with `unknown command: init-empty`.

- [ ] **Step 4: Add command dispatch and help**

In `cli.go`, add this switch case after `status, check, doctor`:

```go
case "init-empty":
	return initEmptyCommand(args[1:], stdout, stderr, paths)
```

Update `printHelp` command list to include `init-empty`:

```go
fmt.Fprintln(w, "Commands: status, check, init-empty, mark-dirty, clear-dirty, record-refresh, complete-refresh, refresh-topics, validate-scan, validate-build, build-from-scan, import-scan, rebuild-from-scan, publish-runtime-metadata, update, lexicon, query, discover, read, doctor, rebuild, delta")
```

- [ ] **Step 5: Add `initEmptyCommand`**

Add this function near `statusCommand`:

```go
func initEmptyCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("init-empty", flag.ContinueOnError)
	fs.SetOutput(stderr)
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	agreement, exists := runtimegate.CheckExisting(paths)
	if exists {
		if agreement.Status == "ok" {
			return writeJSON(stdout, map[string]any{
				"status":                 "ok",
				"readiness":              agreement.Readiness,
				"baseline_kind":          "",
				"active_generation_id":   agreement.StatusGenerationID,
				"status_path":            agreement.StatusPath,
				"graph_store_path":       agreement.GraphStorePath,
				"already_initialized":    true,
				"errors":                 []string{},
				"warnings":               []string{},
				"recommended_next_action": agreement.RecommendedNextAction,
			})
		}
		payload := runtimegate.BlockedPayload(paths, agreement)
		payload["already_initialized"] = false
		return writeErrorJSON(stdout, payload)
	}
	if !store.GreenfieldEmptyEligible(paths.Root) {
		return writeJSON(stdout, map[string]any{
			"status":              "declined",
			"readiness":           rt.NeedsRebuildReadiness,
			"baseline_kind":       "",
			"already_initialized": false,
			"status_path":         rt.RelativeRuntimePath(paths, paths.StatusPath),
			"graph_store_path":    ".specify/project-cognition/project-cognition.db",
			"errors":              []string{},
			"warnings":            []string{"project has non-scaffold files; greenfield empty baseline was not created"},
		})
	}
	st, err := store.Open(paths)
	if err != nil {
		return writeErrorJSON(stdout, map[string]any{"status": "blocked", "readiness": rt.BlockedReadiness, "errors": []string{err.Error()}, "warnings": []string{}})
	}
	defer st.Close()
	generationID, err := st.InitializeGreenfieldEmpty(context.Background())
	if err != nil {
		return writeErrorJSON(stdout, map[string]any{"status": "blocked", "readiness": rt.BlockedReadiness, "errors": []string{err.Error()}, "warnings": []string{}})
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = generationID
	status.QueryContractVersion = 1
	status.UpdateContractVersion = 1
	status.BaselineKind = rt.BaselineKindGreenfieldEmpty
	if err := rt.WriteStatus(paths, status); err != nil {
		return writeErrorJSON(stdout, map[string]any{"status": "blocked", "readiness": rt.BlockedReadiness, "errors": []string{err.Error()}, "warnings": []string{}, "recovery_action": "rewrite_status_from_db_metadata"})
	}
	return writeJSON(stdout, map[string]any{
		"status":               "ok",
		"readiness":            rt.ReadyReadiness,
		"baseline_kind":        rt.BaselineKindGreenfieldEmpty,
		"active_generation_id": generationID,
		"status_path":          rt.RelativeRuntimePath(paths, paths.StatusPath),
		"graph_store_path":     ".specify/project-cognition/project-cognition.db",
		"already_initialized":  false,
		"errors":               []string{},
		"warnings":             []string{},
	})
}
```

- [ ] **Step 6: Add conservative greenfield detector**

In `store.go`, add:

```go
func GreenfieldEmptyEligible(root string) bool {
	nonScaffold := 0
	_ = filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil || nonScaffold > 0 {
			return nil
		}
		rel, relErr := filepath.Rel(root, path)
		if relErr != nil {
			nonScaffold++
			return nil
		}
		rel = filepath.ToSlash(rel)
		if rel == "." {
			return nil
		}
		if d.IsDir() && greenfieldSkipDir(rel) {
			return filepath.SkipDir
		}
		if d.IsDir() {
			return nil
		}
		if !greenfieldScaffoldFile(rel) {
			nonScaffold++
		}
		return nil
	})
	return nonScaffold == 0
}

func greenfieldSkipDir(rel string) bool {
	return rel == ".git" ||
		rel == ".specify" ||
		rel == ".claude" ||
		rel == ".cursor" ||
		rel == ".gemini" ||
		rel == ".github" ||
		rel == ".qwen" ||
		rel == ".opencode" ||
		rel == ".codex" ||
		rel == ".windsurf" ||
		rel == ".kilocode" ||
		rel == ".junie" ||
		rel == ".augment" ||
		rel == ".roo" ||
		rel == ".codebuddy" ||
		rel == ".qoder" ||
		rel == ".kiro" ||
		rel == ".agents" ||
		rel == ".shai" ||
		rel == ".tabnine" ||
		rel == ".kimi" ||
		rel == ".pi" ||
		rel == ".iflow" ||
		rel == ".forge" ||
		rel == ".bob" ||
		rel == ".trae" ||
		rel == ".vibe"
}

func greenfieldScaffoldFile(rel string) bool {
	switch rel {
	case "AGENTS.md", "README.md", ".gitignore", ".cognitionignore":
		return true
	default:
		return false
	}
}
```

- [ ] **Step 7: Run CLI tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/cli -run "TestInitEmptyCommand" -count=1
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/cli/cli_test.go tools/project-cognition/internal/store/store.go
git commit -m "feat: add project cognition empty init command"
```

## Task 4: Greenfield Runtime Agreement And Validation

**Files:**
- Modify: `tools/project-cognition/internal/runtimegate/agreement.go`
- Modify: `tools/project-cognition/internal/validation/build.go`
- Modify: `tools/project-cognition/internal/buildgate/sparse.go`
- Test: `tools/project-cognition/internal/runtimegate/agreement_test.go`
- Test: `tools/project-cognition/internal/validation/build_test.go`

- [ ] **Step 1: Write failing validation test**

Add this test to `tools/project-cognition/internal/validation/build_test.go`:

```go
func TestValidateBuildAcceptsGreenfieldEmptyBaseline(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	generationID, err := st.InitializeGreenfieldEmpty(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = generationID
	status.QueryContractVersion = 1
	status.UpdateContractVersion = 1
	status.BaselineKind = rt.BaselineKindGreenfieldEmpty
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload := ValidateBuild(paths)

	if payload.Status != "ok" {
		t.Fatalf("payload = %#v", payload)
	}
	if payload.Details["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("details baseline_kind = %#v", payload.Details["baseline_kind"])
	}
}
```

- [ ] **Step 2: Write failing mismatch test**

Add this test to `runtimegate/agreement_test.go`:

```go
func TestRuntimeGateBlocksGreenfieldKindMismatch(t *testing.T) {
	paths := testPaths(t)
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	generationID, err := st.InitializeGreenfieldEmpty(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.DB().ExecContext(context.Background(), `UPDATE metadata SET value_json = '"brownfield_full"' WHERE key = 'baseline_kind'`); err != nil {
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
	status.ActiveGenerationID = generationID
	status.BaselineKind = rt.BaselineKindGreenfieldEmpty
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	agreement := Check(paths)

	if agreement.Status != "blocked" {
		t.Fatalf("agreement = %#v", agreement)
	}
	if !containsString(agreement.Errors, `baseline_kind mismatch: status.json has "greenfield_empty", DB metadata has "brownfield_full"`) {
		t.Fatalf("errors = %#v", agreement.Errors)
	}
}
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
cd tools/project-cognition
go test ./internal/validation ./internal/runtimegate -run "Greenfield|baseline_kind|ValidateBuildAccepts" -count=1
```

Expected: FAIL because validation still requires nodes, path index, evidence, or runtimegate ignores baseline-kind mismatch.

- [ ] **Step 4: Add baseline kind to runtimegate agreement**

In `runtimegate/agreement.go`, add fields to `Agreement`:

```go
StatusBaselineKind string `json:"status_baseline_kind,omitempty"`
DBBaselineKind     string `json:"db_baseline_kind,omitempty"`
DBGenerationKind   string `json:"db_generation_kind,omitempty"`
```

After metadata is read in `verifyDBMetadata`, make it return metadata or split out a helper. The minimal path is to add this helper:

```go
func baselineKindAgreement(ctx context.Context, st *store.Store, status rt.Status) (dbKind string, generationKind string, err error) {
	meta, err := st.Metadata(ctx)
	if err != nil {
		return "", "", fmt.Errorf("read DB metadata: %w", err)
	}
	dbKind = strings.TrimSpace(meta["baseline_kind"])
	generationKind, err = st.ActiveGenerationKind(ctx)
	if err != nil {
		return "", "", err
	}
	if strings.TrimSpace(status.BaselineKind) != "" && dbKind != status.BaselineKind {
		return dbKind, generationKind, fmt.Errorf("baseline_kind mismatch: status.json has %q, DB metadata has %q", status.BaselineKind, dbKind)
	}
	if status.BaselineKind == rt.BaselineKindGreenfieldEmpty && generationKind != rt.BaselineKindGreenfieldEmpty {
		return dbKind, generationKind, fmt.Errorf("greenfield_empty status requires active generation kind %q, got %q", rt.BaselineKindGreenfieldEmpty, generationKind)
	}
	return dbKind, generationKind, nil
}
```

Call it in `Check` after `verifyDBMetadata`, populate the new agreement fields, and return blocked on error.

- [ ] **Step 5: Require metadata baseline kind for ready runtime**

In `verifyDBMetadata`, add:

```go
"baseline_kind": rt.BaselineKindBrownfieldFull,
```

Then adjust the check so `baseline_kind` accepts either `brownfield_full` or `greenfield_empty` when present:

```go
if key == "baseline_kind" {
	if got != rt.BaselineKindBrownfieldFull && got != rt.BaselineKindGreenfieldEmpty {
		return fmt.Errorf("project-cognition.db metadata baseline_kind has %q, expected %q or %q", got, rt.BaselineKindBrownfieldFull, rt.BaselineKindGreenfieldEmpty)
	}
	continue
}
```

- [ ] **Step 6: Add greenfield predicate to validation**

In `validation/build.go`, add:

```go
func isGreenfieldEmptyBaseline(status rt.Status, db *sql.DB, activeGenerationID string) bool {
	if status.BaselineKind != rt.BaselineKindGreenfieldEmpty {
		return false
	}
	metaKind, err := metadataScalar(db, "baseline_kind")
	if err != nil || metaKind != rt.BaselineKindGreenfieldEmpty {
		return false
	}
	var generationKind string
	err = db.QueryRow("SELECT kind FROM generations WHERE id = ?", activeGenerationID).Scan(&generationKind)
	return err == nil && generationKind == rt.BaselineKindGreenfieldEmpty
}
```

Then wrap zero-row errors in `validateGraphStore`:

```go
greenfieldEmpty := isGreenfieldEmptyBaseline(status, db, activeGenerationID)
details["baseline_kind"] = status.BaselineKind
if nodeCount == 0 && !greenfieldEmpty {
	errors = append(errors, "active generation has no nodes")
}
if pathCount == 0 && !greenfieldEmpty {
	errors = append(errors, "active_generation_has_no_path_index_rows")
}
if pathCount > 0 && sparsePathIndexGateAvailable(paths) {
	sparse := buildgate.ValidateSparsePathIndex(paths, db, activeGenerationID)
	for key, value := range sparse.Details {
		details[key] = value
	}
	errors = append(errors, sparse.Errors...)
	warnings = append(warnings, sparse.Warnings...)
}
if evidenceCount == 0 && !greenfieldEmpty {
	errors = append(errors, "active generation has no evidence rows")
}
```

- [ ] **Step 7: Keep sparse gate brownfield-only when no required rows**

In `buildgate/sparse.go`, add this early return immediately after `result` initialization in `ValidateSparsePathIndex`:

```go
if generationID != "" && generationKindIsGreenfield(context.Background(), db, generationID) {
	result.Details["baseline_kind"] = rt.BaselineKindGreenfieldEmpty
	result.Details["path_index_to_included_ratio"] = "1.00"
	return result
}
```

In the same file, add this helper below `ValidateSparsePathIndex`:

```go
func generationKindIsGreenfield(ctx context.Context, db *sql.DB, generationID string) bool {
	var kind string
	err := db.QueryRowContext(ctx, `SELECT kind FROM generations WHERE id = ?`, generationID).Scan(&kind)
	return err == nil && kind == rt.BaselineKindGreenfieldEmpty
}
```

- [ ] **Step 8: Run focused validation tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/validation ./internal/runtimegate ./internal/buildgate -run "Greenfield|baseline_kind|ValidateBuildAccepts" -count=1
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add tools/project-cognition/internal/runtimegate/agreement.go tools/project-cognition/internal/runtimegate/agreement_test.go tools/project-cognition/internal/validation/build.go tools/project-cognition/internal/validation/build_test.go tools/project-cognition/internal/buildgate/sparse.go
git commit -m "feat: validate greenfield cognition baselines"
```

## Task 5: Lexicon And Query Greenfield Payloads

**Files:**
- Modify: `tools/project-cognition/internal/query/lexicon.go`
- Modify: `tools/project-cognition/internal/query/query.go`
- Test: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Write failing lexicon test**

Add this test to `cli_test.go`:

```go
func TestLexiconCommandHandlesGreenfieldEmptyBaseline(t *testing.T) {
	root := initEmptyCLIRuntime(t)

	var stdout, stderr bytes.Buffer
	code := Run([]string{"lexicon", "--intent", "plan", "--query", "build login", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	_ = root
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["readiness"] != rt.ReadyReadiness {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["recommended_next_action"] != "use_project_cognition" {
		t.Fatalf("payload = %#v", payload)
	}
	if !jsonStringSliceContains(payload["missing_coverage"], "greenfield_empty_no_project_code") {
		t.Fatalf("missing_coverage = %#v", payload["missing_coverage"])
	}
	candidates, ok := payload["concept_candidates"].([]any)
	if !ok || len(candidates) != 0 {
		t.Fatalf("concept_candidates = %#v, want empty", payload["concept_candidates"])
	}
}
```

- [ ] **Step 2: Write failing query test**

Add this test to `cli_test.go`:

```go
func TestQueryCommandHandlesGreenfieldEmptyBaseline(t *testing.T) {
	initEmptyCLIRuntime(t)
	queryPlan := marshalQueryPlan(t, map[string]any{
		"raw_query": "build login",
	})

	var stdout, stderr bytes.Buffer
	code := Run([]string{"query", "--intent", "plan", "--query-plan", queryPlan, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["readiness"] != rt.ReadyReadiness {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["baseline_kind"] != rt.BaselineKindGreenfieldEmpty {
		t.Fatalf("payload = %#v", payload)
	}
	if !jsonStringSliceContains(payload["minimal_live_reads"], ".specify/memory/constitution.md") {
		t.Fatalf("minimal_live_reads = %#v", payload["minimal_live_reads"])
	}
	if !jsonStringSliceContains(payload["missing_coverage"], "greenfield_empty_no_project_code") {
		t.Fatalf("missing_coverage = %#v", payload["missing_coverage"])
	}
}
```

Add this helper near `setupReadyMinimalCLIRuntime`:

```go
func initEmptyCLIRuntime(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"init-empty", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("init-empty code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	return root
}
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
cd tools/project-cognition
go test ./internal/cli -run "GreenfieldEmptyBaseline" -count=1
```

Expected: FAIL because `baseline_kind` is missing from payloads or `minimal_live_reads` does not include greenfield workflow artifacts.

- [ ] **Step 4: Add baseline kind fields**

In `lexicon.go`, add to `LexiconPayload`:

```go
BaselineKind string `json:"baseline_kind,omitempty"`
```

In `query.go`, add to `QueryPayload`:

```go
BaselineKind string `json:"baseline_kind,omitempty"`
```

- [ ] **Step 5: Populate greenfield lexicon behavior**

In `Lexicon`, set `BaselineKind: status.BaselineKind` in the payload literal. After payload creation and before DB candidate lookup, add:

```go
if status.BaselineKind == rt.BaselineKindGreenfieldEmpty {
	payload.UnmappedIntent = len(terms) > 0
	payload.MissingCoverage = []string{"greenfield_empty_no_project_code"}
	payload.CandidateUniverse = map[string]any{
		"counts":           map[string]any{"nodes": 0, "candidates": 0},
		"truncated":        false,
		"selection_window": limit,
	}
	return payload, nil
}
```

- [ ] **Step 6: Populate greenfield query behavior**

In `Run` in `query.go`, set `BaselineKind: status.BaselineKind` in the returned `QueryPayload`. Before opening the store, add:

```go
if status.BaselineKind == rt.BaselineKindGreenfieldEmpty {
	reads := []string{
		".specify/memory/constitution.md",
		".specify/memory/project-rules.md",
		"AGENTS.md",
	}
	return QueryPayload{
		BaselineHealth: map[string]any{
			"freshness":     status.Freshness,
			"readiness":     status.Readiness,
			"dirty":         status.Dirty,
			"baseline_kind": status.BaselineKind,
		},
		QueryCoverage:         map[string]any{"paths": plan.Paths, "nodes": 0, "baseline_kind": status.BaselineKind},
		WorkflowRequirement:   "use_greenfield_workflow_artifacts_then_live_requirements",
		PathAdoption:          map[string]any{"paths": plan.Paths},
		Readiness:             status.Readiness,
		RecommendedNextAction: status.RecommendedNextAction,
		BaselineKind:          status.BaselineKind,
		Intent:                input.Intent,
		Query:                 input.Query,
		QueryPlan:             plan,
		SelectedConcepts:      plan.SelectedConcepts,
		RejectedConcepts:      plan.RejectedConcepts,
		SelectionReason:       plan.SelectionReason,
		CapabilityCandidates:  []map[string]any{},
		SymptomCandidates:     []map[string]any{},
		AffectedNodes:         []map[string]any{},
		MinimalLiveReads:      reads,
		MissingCoverage:       []string{"greenfield_empty_no_project_code"},
		RoutePack: map[string]any{
			"items":              []map[string]any{},
			"routes":             plan.Paths,
			"minimal_live_reads": reads,
			"why_these_reads":    "Greenfield empty baseline has no project source graph yet; use workflow artifacts and live requirements.",
		},
		Subgraph: map[string]any{
			"nodes":     []map[string]any{},
			"edges":     []map[string]any{},
			"claims":    []map[string]any{},
			"conflicts": []map[string]any{},
		},
	}, nil
}
```

- [ ] **Step 7: Run CLI tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/cli -run "InitEmptyCommand|GreenfieldEmptyBaseline" -count=1
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add tools/project-cognition/internal/query/lexicon.go tools/project-cognition/internal/query/query.go tools/project-cognition/internal/cli/cli_test.go
git commit -m "feat: query greenfield cognition baselines"
```

## Task 6: Python Init Bootstrap

**Files:**
- Modify: `src/specify_cli/project_cognition_runtime.py`
- Modify: `src/specify_cli/__init__.py`
- Test: `tests/test_project_cognition_runtime_install.py`

- [ ] **Step 1: Write failing required-command test**

Add this test to `tests/test_project_cognition_runtime_install.py`:

```python
def test_project_cognition_required_commands_include_init_empty():
    assert "build-from-scan" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "init-empty" in project_cognition_runtime.REQUIRED_COMMANDS
```

- [ ] **Step 2: Write failing init bootstrap test**

Add this test after `test_init_prefetches_project_cognition_runtime`:

```python
def test_init_runs_project_cognition_init_empty(monkeypatch, tmp_path: Path):
    binary = tmp_path / "cache" / "project-cognition.py"
    calls_file = tmp_path / "calls.txt"
    binary.parent.mkdir(parents=True)
    binary.write_text(
        "\n".join(
            [
                "import json, pathlib, sys",
                "pathlib.Path(sys.argv[0]).with_name('calls.txt').write_text(' '.join(sys.argv[1:]), encoding='utf-8')",
                "print(json.dumps({'status':'ok','readiness':'query_ready','baseline_kind':'greenfield_empty'}))",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    def fake_ensure_binary():
        return binary

    monkeypatch.setattr(specify_lint, "ensure_binary", lambda: tmp_path / "spec-lint")
    monkeypatch.setattr("specify_cli.project_cognition_runtime.ensure_binary", fake_ensure_binary)
    monkeypatch.setattr(specify_cli, "check_tool", lambda tool, tracker=None: True)

    runner = CliRunner()
    result = runner.invoke(
        specify_cli.app,
        ["init", str(tmp_path / "project"), "--ai", "claude", "--no-git"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert calls_file.read_text(encoding="utf-8") == "init-empty --format json"
```

On Windows, Python scripts may not be directly executable. If this test fails with process launch permissions, replace `binary` with a small `.cmd` or `.ps1` fake for Windows and a POSIX executable script for non-Windows. Keep the assertion on `init-empty --format json`.

- [ ] **Step 3: Run tests to verify they fail**

Run:

```powershell
uv run pytest tests/test_project_cognition_runtime_install.py::test_project_cognition_required_commands_include_init_empty tests/test_project_cognition_runtime_install.py::test_init_runs_project_cognition_init_empty -q
```

Expected: first test FAILS because `init-empty` is missing from `REQUIRED_COMMANDS`; second test FAILS because init does not invoke `init-empty`.

- [ ] **Step 4: Update required commands**

In `src/specify_cli/project_cognition_runtime.py`, change:

```python
REQUIRED_COMMANDS = ("build-from-scan",)
```

to:

```python
REQUIRED_COMMANDS = ("build-from-scan", "init-empty")
```

- [ ] **Step 5: Add bootstrap helper**

In `src/specify_cli/__init__.py`, add this helper near the project cognition runtime setup helpers:

```python
def _run_project_cognition_init_empty(project_path: Path, binary: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [str(binary), "init-empty", "--format", "json"],
            cwd=project_path,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return False, detail or f"project-cognition init-empty exited {result.returncode}"
    return True, "greenfield baseline"
```

`subprocess` and `Path` are already imported in this module; if not, add them at the top with existing imports.

- [ ] **Step 6: Call helper during init**

In the project-cognition tracker block in `init`, replace:

```python
project_cognition_binary = _ensure_project_cognition()
_write_project_cognition_launcher(project_path, project_cognition_binary)
tracker.complete("project-cognition", "available")
```

with:

```python
project_cognition_binary = _ensure_project_cognition()
_write_project_cognition_launcher(project_path, project_cognition_binary)
init_ok, init_detail = _run_project_cognition_init_empty(project_path, project_cognition_binary)
if init_ok:
    tracker.complete("project-cognition", init_detail)
else:
    project_cognition_warning = init_detail
    tracker.complete("project-cognition", "available; empty baseline skipped")
```

- [ ] **Step 7: Run focused Python tests**

Run:

```powershell
uv run pytest tests/test_project_cognition_runtime_install.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add src/specify_cli/project_cognition_runtime.py src/specify_cli/__init__.py tests/test_project_cognition_runtime_install.py
git commit -m "feat: bootstrap greenfield cognition during init"
```

## Task 7: Generated Guidance And Cursor Addendum

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/cursor_agent/__init__.py`
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/planning-context-loading-gradient.md`
- Modify: `templates/command-partials/common/navigation-check.md`
- Modify: `templates/command-partials/common/senior-consequence-analysis-gate.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Test: `tests/integrations/test_integration_base_markdown.py`
- Test: `tests/integrations/test_integration_cursor_agent.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write failing integration assertions**

In `tests/integrations/test_integration_base_markdown.py`, update the project-cognition generated-output assertions so generated content must contain:

```python
assert "greenfield_empty" in content
assert "do not recommend map-scan -> map-build solely because the graph has no paths" in content
```

In `tests/integrations/test_integration_cursor_agent.py`, update `test_cursor_runtime_skills_hard_gate_project_cognition_reads` so non-constitution skills assert:

```python
assert "greenfield_empty" in content
assert "do not recommend map-scan -> map-build solely because the graph has no paths" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
uv run pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_cursor_agent.py -q
```

Expected: FAIL because generated guidance has no `greenfield_empty` branch.

- [ ] **Step 3: Update base integration addendum**

In `src/specify_cli/integrations/base.py`, replace the `needs_rebuild` sentence inside `_append_runtime_project_cognition_gate` with:

```python
"- Interpret returned readiness: `ready` continues with the task-local bundle; `review` permits only returned `minimal_live_reads`; `ambiguous` asks the user to choose; `greenfield_empty` continues with workflow artifacts and live requirements; `needs_update` uses `{{invoke:map-update}}` when updated runtime coverage is required for the touched area, otherwise continues with live repository evidence and carries the stale coverage gap forward; `needs_rebuild` treats map output as advisory, continues with live repository evidence, and recommends `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only for brownfield first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows outside a `greenfield_empty` baseline, `explicit_rebuild_requested`, or `baseline_identity_invalid`; `blocked` reports the runtime issue as advisory map state and continues with live repository evidence. If the user's actual request is to fix cognition runtime state, report the blocked state and follow the same map-update-first routing policy.\n"
```

Replace the next map-update sentence with:

```python
"- Use `map-update` for ordinary existing-baseline gaps. If `baseline_kind=greenfield_empty`, do not recommend map-scan -> map-build solely because the graph has no paths; continue with workflow artifacts and live requirements. Use `map-scan -> map-build` only for brownfield first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows outside `greenfield_empty`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.\n"
```

- [ ] **Step 4: Update Cursor addendum**

In `src/specify_cli/integrations/cursor_agent/__init__.py`, replace the map-update line with:

```python
"- If `baseline_kind=greenfield_empty`, do not recommend map-scan -> map-build solely because the graph has no paths; continue with workflow artifacts and live requirements.\n"
"- Use map-update for ordinary existing-baseline gaps. Use map-scan -> map-build only for brownfield first/missing/unusable baseline, schema failure, zero active-generation path_index rows outside greenfield_empty, explicit_rebuild_requested, or baseline_identity_invalid.\n"
```

- [ ] **Step 5: Update shared partials and passive skills**

In each listed Markdown file, add this routing rule near the existing missing/needs-rebuild guidance:

```markdown
- `greenfield_empty` -> continue with workflow artifacts and live requirements. Do not recommend `map-scan -> map-build` solely because the graph has no paths.
```

When the file already lists first/missing/unusable baseline, change it to brownfield-specific wording:

```markdown
Use `map-scan -> map-build` only for brownfield first/missing/unusable baseline, schema failure, zero active-generation `path_index` rows outside `greenfield_empty`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
```

- [ ] **Step 6: Run generated guidance tests**

Run:

```powershell
uv run pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_cursor_agent.py tests/test_alignment_templates.py -q
```

Expected: PASS after updating any exact string assertions that intentionally encode the old brownfield-only text.

- [ ] **Step 7: Commit**

```powershell
git add src/specify_cli/integrations/base.py src/specify_cli/integrations/cursor_agent/__init__.py templates/command-partials/common/context-loading-gradient.md templates/command-partials/common/planning-context-loading-gradient.md templates/command-partials/common/navigation-check.md templates/command-partials/common/senior-consequence-analysis-gate.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_cursor_agent.py tests/test_alignment_templates.py
git commit -m "docs: route greenfield cognition guidance"
```

## Task 8: User Docs

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/installation.md`
- Test: `tests/test_command_surface_semantics.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write failing docs assertions**

In `tests/test_command_surface_semantics.py`, add:

```python
def test_docs_describe_greenfield_project_cognition_bootstrap() -> None:
    surfaces = {
        "README.md": (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower(),
        "PROJECT-HANDBOOK.md": (PROJECT_ROOT / "PROJECT-HANDBOOK.md").read_text(encoding="utf-8").lower(),
        "docs/quickstart.md": (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8").lower(),
        "docs/installation.md": (PROJECT_ROOT / "docs" / "installation.md").read_text(encoding="utf-8").lower(),
    }
    for path, content in surfaces.items():
        assert "greenfield_empty" in content, path
        assert "init-empty" in content, path
        assert "do not require map-scan -> map-build" in content, path
```

- [ ] **Step 2: Run docs test to verify it fails**

Run:

```powershell
uv run pytest tests/test_command_surface_semantics.py::test_docs_describe_greenfield_project_cognition_bootstrap -q
```

Expected: FAIL because docs do not yet mention `greenfield_empty` and `init-empty`.

- [ ] **Step 3: Update README**

Add this paragraph in the Project Cognition Runtime section:

```markdown
Fresh `specify init` projects bootstrap a query-ready empty cognition runtime by running `project-cognition init-empty` after the binary is pinned. This creates `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db` with `baseline_kind=greenfield_empty`. That state means there is no business code to scan yet, so greenfield requirement and planning workflows do not require map-scan -> map-build solely because the graph has no paths. Brownfield projects with existing code still use map-scan -> map-build for a first missing or unusable baseline when a full baseline is needed.
```

- [ ] **Step 4: Update PROJECT-HANDBOOK**

Add this sentence to the Brownfield cognition lifecycle bullet:

```markdown
Fresh generated projects may start with `baseline_kind=greenfield_empty`, created by `project-cognition init-empty` during `specify init`; that query-ready empty runtime allows greenfield workflows to proceed from workflow artifacts and live requirements without requiring map-scan -> map-build solely because no source graph paths exist yet.
```

- [ ] **Step 5: Update quickstart**

Near existing project-cognition workflow guidance in `docs/quickstart.md`, add:

```markdown
For a newly initialized project with no business code yet, `specify init` creates a starter project cognition runtime with `baseline_kind=greenfield_empty` by calling `project-cognition init-empty`. This still creates the real `.specify/project-cognition/project-cognition.db`; it simply has no source graph rows yet. In that state, continue with `specify -> plan` and do not require map-scan -> map-build solely because the graph has no paths.
```

- [ ] **Step 6: Update installation guide**

In `docs/installation.md` under project-cognition runtime installation, add:

```markdown
During `specify init`, Spec Kit Plus also attempts `project-cognition init-empty` for greenfield projects. When the project has no business code yet, this creates both `.specify/project-cognition/status.json` and `.specify/project-cognition/project-cognition.db` with `baseline_kind=greenfield_empty`. If this best-effort bootstrap fails, initialization still completes and the runtime can be installed or repaired later.
```

- [ ] **Step 7: Run docs tests**

Run:

```powershell
uv run pytest tests/test_command_surface_semantics.py::test_docs_describe_greenfield_project_cognition_bootstrap tests/test_alignment_templates.py -q
```

Expected: PASS after adjusting any exact wording assertions that intentionally encode old brownfield-only guidance.

- [ ] **Step 8: Commit**

```powershell
git add README.md PROJECT-HANDBOOK.md docs/quickstart.md docs/installation.md tests/test_command_surface_semantics.py tests/test_alignment_templates.py
git commit -m "docs: document greenfield cognition bootstrap"
```

## Task 9: Full Verification

**Files:**
- No source edits unless verification exposes a regression.

- [ ] **Step 1: Run Go runtime tests**

Run:

```powershell
cd tools/project-cognition
go test ./...
```

Expected: PASS.

- [ ] **Step 2: Run Python focused tests**

Run:

```powershell
uv run pytest tests/test_project_cognition_runtime_install.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_cursor_agent.py tests/test_command_surface_semantics.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 3: Run targeted grep checks**

Run:

```powershell
rg -n "Use map-scan -> map-build only for first/missing/unusable baseline|zero active-generation path_index rows" src templates docs README.md PROJECT-HANDBOOK.md tests
```

Expected: remaining matches either mention `greenfield_empty`, say `brownfield`, or are explicit tests for brownfield behavior.

- [ ] **Step 4: Run diff checks**

Run:

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors; working tree shows only intended files before final commit.

- [ ] **Step 5: Confirm no stray edits remain**

Run:

```powershell
git status --short
```

Expected: empty output. If output is non-empty, return to the task that owns those paths and repeat that task's focused verification before running the full verification task again.

## Self-Review

- Spec coverage: tasks cover runtime status, real DB creation, CLI command, validation exception, query behavior, Python init bootstrap, shared guidance, Cursor-specific guidance, docs, and verification.
- No placeholder directives are present. Every code-changing task includes concrete tests, exact snippets, and exact commands.
- Type consistency: `BaselineKind`, `BaselineKindBrownfieldFull`, and `BaselineKindGreenfieldEmpty` are introduced before use; Go payload field names use `baseline_kind`; Python and doc assertions use the same literal.
- Scope control: promotion from `greenfield_empty` after future source generation is not implemented in this plan because the approved spec says promotion can remain conservative for the first implementation.

# Inline Map Update Equivalence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make workflow inline project cognition update produce the same runtime effect as `sp-map-update` for workflow-owned changes, with one shared prompt contract and result-state-based validation.

**Architecture:** Add a structured `project-cognition update --payload-file` contract and make delta-session and non-delta update paths converge on one update engine. Persist structured update records with affected graph fields, path adoption metadata, and `result_state`; route `sp-map-update`, inline closeout prompts, Python hooks, fake runtimes, integrations, and docs through the same result-state semantics.

**Tech Stack:** Go 1.21 project-cognition runtime with SQLite via `database/sql` and `modernc.org/sqlite`, Python 3.11+ pytest/Typer hooks and integrations, Markdown command templates, generated integration tests.

---

## Reference Spec

- `docs/superpowers/specs/2026-05-30-inline-map-update-equivalence-design.md`

## Scope Notes

- This is a runtime and generated-workflow contract change. Do not limit the work to prompt text.
- `project-cognition update --changed-path "src/app.go" --scope "src" --reason workflow-finalize --format json` remains a compatibility interface, but clean closeout must key on `result_state`.
- `sp-map-update` must call the same lower-level `project-cognition update` helper as inline closeout before validation and finalization.
- Existing recorded-only update rows remain historical data; new successful closeout must not emit or accept recorded-only success.
- Work in small commits. Each task below ends with a commit command.

## File Structure

Runtime contract and engine:

- `tools/project-cognition/internal/cli/cli.go`: parse `--payload-file`, pass it into update input, emit `result_state`.
- `tools/project-cognition/internal/cli/cli_test.go`: CLI contract tests for payload update and result-state output.
- `tools/project-cognition/internal/update/state.go`: update input structs, payload loading, result-state mapping, shared delta/non-delta engine, status update payload.
- `tools/project-cognition/internal/update/state_test.go`: update engine tests for payload, path-only compatibility, delta convergence, no-op, partial, and ready mapping.
- `tools/project-cognition/internal/store/store.go`: structured update persistence, affected closure readers, path adoption writer.
- `tools/project-cognition/internal/store/schema.go`: schema compatibility checks for `updates` remain stable while attrs carry added metadata.
- `tools/project-cognition/internal/store/update_test.go`: structured update and path adoption persistence tests.
- `tools/project-cognition/internal/delta/**`: no schema rewrite unless tests prove delta normalization needs a helper; add only focused conversion helpers.
- `tools/project-cognition/internal/boundary/**`: no broad rewrite; normalize boundary outputs into update payload input.
- `tools/project-cognition/internal/validation/**`, `tools/project-cognition/internal/buildgate/**`, `tools/project-cognition/internal/runtimegate/**`: participate in final `result_state`.

Generated workflow surfaces:

- `templates/command-partials/common/inline-project-cognition-update.md`: new shared prompt contract.
- `templates/command-partials/common/context-loading-gradient.md`: consume or delegate closeout wording to the shared partial.
- `templates/command-partials/common/planning-context-loading-gradient.md`: consume or delegate closeout wording to the shared partial.
- `templates/command-partials/common/navigation-check.md`: keep entry-only navigation and point closeout to the shared partial.
- `templates/commands/{fast,quick,implement,debug,specify,clarify,deep-research,plan,tasks,analyze,map-update}.md`: use shared inline contract where the command can mutate source/runtime surfaces.
- `templates/command-partials/{fast,quick,implement,debug,specify,clarify,deep-research,plan,tasks,analyze}/shell.md`: remove weaker local closeout text or point to the shared partial.
- `templates/worker-prompts/{quick-worker,implementer,debug-investigator,debug-thinker,code-quality-reviewer,spec-reviewer}.md`: require workers to report changed paths, behavior surfaces, verification, and known unknowns.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: align passive guidance to result-state contract.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: align routing guidance to result-state contract.
- `templates/passive-skills/subagent-driven-development/SKILL.md`: include closeout handoff evidence fields.

Python validation and generated integration surfaces:

- `src/specify_cli/hooks/artifact_validation.py`: validate map-update artifacts by `result_state`, not `last_update_id` or freshness alone.
- `tests/contract/test_hook_cli_surface.py`: reject recorded-only and last-update-id-only map-update artifacts.
- `tests/project_cognition_fake.py`: fake `project-cognition update` supports `--payload-file` and result states.
- `src/specify_cli/integrations/base.py`: generated addenda consume the strong-equivalence contract.
- `src/specify_cli/integrations/cursor_agent/__init__.py`: Cursor addendum consumes the same contract.
- `tests/integrations/**`: generated output assertions for shared wording.
- `tests/test_alignment_templates.py`, `tests/test_command_surface_semantics.py`, `tests/test_map_runtime_template_guidance.py`: cross-template alignment tests.

Docs:

- `README.md`
- `PROJECT-HANDBOOK.md`
- `templates/project-handbook-template.md`
- `docs/quickstart.md`
- `docs/installation.md`

---

### Task 1: Add Runtime Payload And Result-State CLI Contract

**Files:**
- Modify: `tools/project-cognition/internal/cli/cli.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`
- Modify: `tools/project-cognition/internal/update/state.go`
- Modify: `tools/project-cognition/internal/update/state_test.go`

- [ ] **Step 1: Add the failing CLI payload test**

Append this test to `tools/project-cognition/internal/cli/cli_test.go`:

```go
func TestUpdateCommandAcceptsPayloadFileAndEmitsResultState(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var buildStdout, buildStderr bytes.Buffer
	buildCode := Run([]string{"build-from-scan", "--format", "json"}, &buildStdout, &buildStderr, "test")
	if buildCode != 0 {
		t.Fatalf("build code = %d stderr=%s stdout=%s", buildCode, buildStderr.String(), buildStdout.String())
	}

	payloadPath := filepath.Join(root, ".specify", "project-cognition", "updates", "workflow-finalize.json")
	if err := os.MkdirAll(filepath.Dir(payloadPath), 0o755); err != nil {
		t.Fatal(err)
	}
	payload := map[string]any{
		"workflow":          "sp-implement",
		"reason":            "workflow-finalize",
		"changed_paths":     []string{"src/app.go"},
		"scope_paths":       []string{"src"},
		"behavior_surfaces": []string{"application entrypoint"},
		"verification": []map[string]string{
			{"command": "go test ./...", "result": "passed", "artifact": "artifacts/quality-runs/example/report.md"},
		},
		"known_unknowns":   []string{},
		"confidence_notes": []string{"indexed path refresh"},
	}
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(payloadPath, data, 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"update", "--payload-file", payloadPath, "--reason", "workflow-finalize", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var result map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result["result_state"] == "" {
		t.Fatalf("payload = %#v, want result_state", result)
	}
	if result["update_id"] == "" {
		t.Fatalf("payload = %#v, want update_id", result)
	}
	if _, ok := result["status_update"].(map[string]any); !ok {
		t.Fatalf("payload = %#v, want status_update object", result)
	}
}
```

- [ ] **Step 2: Run the failing CLI test**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/cli -run TestUpdateCommandAcceptsPayloadFileAndEmitsResultState -count=1
Pop-Location
```

Expected: FAIL with `flag provided but not defined: -payload-file` or missing `result_state`.

- [ ] **Step 3: Add update contract structs**

In `tools/project-cognition/internal/update/state.go`, replace `UpdateInput` and extend `UpdatePayload` with these fields and helper structs:

```go
type VerificationEvidence struct {
	Command  string `json:"command"`
	Result   string `json:"result"`
	Artifact string `json:"artifact,omitempty"`
}

type UpdateBoundaryInput struct {
	CommitRange        string   `json:"commit_range,omitempty"`
	InitialDirtyPaths  []string `json:"initial_dirty_paths,omitempty"`
	WorkflowOwnedPaths []string `json:"workflow_owned_paths,omitempty"`
}

type PayloadFileInput struct {
	Workflow          string                 `json:"workflow"`
	Reason            string                 `json:"reason"`
	ChangedPaths      []string               `json:"changed_paths"`
	ScopePaths        []string               `json:"scope_paths"`
	BehaviorSurfaces  []string               `json:"behavior_surfaces"`
	GeneratedSurfaces []string               `json:"generated_surfaces"`
	StateContracts    []string               `json:"state_contracts"`
	Verification      []VerificationEvidence `json:"verification"`
	KnownUnknowns     []string               `json:"known_unknowns"`
	ConfidenceNotes   []string               `json:"confidence_notes"`
	UserDecisions     []string               `json:"user_decisions"`
	Boundary          UpdateBoundaryInput    `json:"boundary"`
}

type UpdateInput struct {
	ChangedPaths      []string
	ScopePaths        []string
	Reason            string
	DeltaSessionID    string
	CommitRange       string
	PayloadFile       string
	Workflow          string
	BehaviorSurfaces  []string
	GeneratedSurfaces []string
	StateContracts    []string
	Verification      []VerificationEvidence
	KnownUnknowns     []string
	ConfidenceNotes   []string
	UserDecisions     []string
	Boundary          UpdateBoundaryInput
}

type StatusUpdate struct {
	Status                string   `json:"status"`
	Freshness             string   `json:"freshness"`
	Readiness             string   `json:"readiness"`
	RecommendedNextAction string   `json:"recommended_next_action"`
	Dirty                 bool     `json:"dirty"`
	StalePaths            []string `json:"stale_paths"`
	StaleReasons          []string `json:"stale_reasons"`
	LastUpdateID          string   `json:"last_update_id"`
	LastUpdateOutcome     string   `json:"last_update_outcome"`
}

const (
	ResultReady          = "ready"
	ResultNoOp           = "no_op"
	ResultPartialRefresh = "partial_refresh"
	ResultNeedsRebuild   = "needs_rebuild"
	ResultBlocked        = "blocked"
	ResultRecorded       = "recorded"
)
```

Add these fields to `UpdatePayload`:

```go
	ResultState  string       `json:"result_state"`
	StatusUpdate StatusUpdate `json:"status_update"`
```

- [ ] **Step 4: Add payload-file loading**

Add this helper to `tools/project-cognition/internal/update/state.go`:

```go
func loadPayloadFile(path string) (PayloadFileInput, error) {
	if strings.TrimSpace(path) == "" {
		return PayloadFileInput{}, nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return PayloadFileInput{}, fmt.Errorf("read update payload file: %w", err)
	}
	var payload PayloadFileInput
	if err := json.Unmarshal(data, &payload); err != nil {
		return PayloadFileInput{}, fmt.Errorf("parse update payload file: %w", err)
	}
	payload.ChangedPaths = normalizePaths(payload.ChangedPaths)
	payload.ScopePaths = normalizePaths(payload.ScopePaths)
	payload.KnownUnknowns = compactStrings(payload.KnownUnknowns)
	payload.ConfidenceNotes = compactStrings(payload.ConfidenceNotes)
	return payload, nil
}

func applyPayloadFileInput(input UpdateInput, payload PayloadFileInput) UpdateInput {
	if payload.Workflow != "" {
		input.Workflow = payload.Workflow
	}
	if payload.Reason != "" && input.Reason == "" {
		input.Reason = payload.Reason
	}
	input.ChangedPaths = append(input.ChangedPaths, payload.ChangedPaths...)
	input.ScopePaths = append(input.ScopePaths, payload.ScopePaths...)
	input.BehaviorSurfaces = append(input.BehaviorSurfaces, payload.BehaviorSurfaces...)
	input.GeneratedSurfaces = append(input.GeneratedSurfaces, payload.GeneratedSurfaces...)
	input.StateContracts = append(input.StateContracts, payload.StateContracts...)
	input.Verification = append(input.Verification, payload.Verification...)
	input.KnownUnknowns = append(input.KnownUnknowns, payload.KnownUnknowns...)
	input.ConfidenceNotes = append(input.ConfidenceNotes, payload.ConfidenceNotes...)
	input.UserDecisions = append(input.UserDecisions, payload.UserDecisions...)
	if payload.Boundary.CommitRange != "" {
		input.Boundary = payload.Boundary
	}
	return input
}
```

Add `compactStrings` near `appendUnique`:

```go
func compactStrings(values []string) []string {
	out := make([]string, 0, len(values))
	seen := map[string]bool{}
	for _, value := range values {
		trimmed := strings.TrimSpace(value)
		if trimmed == "" || seen[trimmed] {
			continue
		}
		seen[trimmed] = true
		out = append(out, trimmed)
	}
	sort.Strings(out)
	return out
}
```

- [ ] **Step 5: Wire `--payload-file` through the CLI**

In `tools/project-cognition/internal/cli/cli.go`, update `updateCommand`:

```go
	payloadFile := fs.String("payload-file", "", "Structured update payload JSON file")
```

Pass it into `update.RunUpdate`:

```go
	PayloadFile:    *payloadFile,
```

- [ ] **Step 6: Apply payload input at the start of `RunUpdate`**

At the top of `RunUpdate`, after the split-brain check and before the delta-session branch, add:

```go
	if input.PayloadFile != "" {
		payload, err := loadPayloadFile(input.PayloadFile)
		if err != nil {
			return UpdatePayload{}, err
		}
		input = applyPayloadFileInput(input, payload)
	}
```

- [ ] **Step 7: Return a non-empty compatibility result state**

Before deeper engine work, keep the existing behavior compiling by setting `ResultState: ResultPartialRefresh` and `StatusUpdate: statusUpdateFromStatus(status)` in both current `RunUpdate` return paths. Add this helper:

```go
func statusUpdateFromStatus(status rt.Status) StatusUpdate {
	return StatusUpdate{
		Status:                status.Status,
		Freshness:             status.Freshness,
		Readiness:             status.Readiness,
		RecommendedNextAction: status.RecommendedNextAction,
		Dirty:                 status.Dirty,
		StalePaths:            append([]string{}, status.StalePaths...),
		StaleReasons:          append([]string{}, status.StaleReasons...),
		LastUpdateID:          status.LastUpdateID,
		LastUpdateOutcome:     status.LastUpdateOutcome,
	}
}
```

- [ ] **Step 8: Run the targeted tests and commit**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/cli ./internal/update -count=1
Pop-Location
```

Expected: tests pass or only later result-state semantics tests are still absent.

Commit:

```powershell
git add tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/cli/cli_test.go tools/project-cognition/internal/update/state.go tools/project-cognition/internal/update/state_test.go
git commit -m "feat: add project cognition update payload contract"
```

---

### Task 2: Persist Structured Update Records

**Files:**
- Modify: `tools/project-cognition/internal/store/store.go`
- Modify: `tools/project-cognition/internal/store/update_test.go`
- Modify: `tools/project-cognition/internal/update/state.go`
- Modify: `tools/project-cognition/internal/update/state_test.go`

- [ ] **Step 1: Add the failing structured persistence test**

Create `tools/project-cognition/internal/store/update_test.go`:

```go
package store

import (
	"context"
	"encoding/json"
	"testing"
)

func TestRecordStructuredUpdatePersistsAffectedFields(t *testing.T) {
	st := openImportTestStore(t)
	ctx := context.Background()
	input := validImportInput("GEN-update")
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	record := UpdateRecord{
		ID:             "upd-test",
		Trigger:        "workflow-finalize",
		ChangedPaths:   []string{"src/app.go"},
		AffectedNodes:  []string{"capability:app"},
		AffectedClaims: []string{"claim:app"},
		AffectedSlices: []string{"slice:runtime"},
		ResultState:    "ready",
		Attrs: map[string]any{
			"known_unknowns": []string{"none"},
		},
	}
	if err := st.RecordStructuredUpdate(ctx, record); err != nil {
		t.Fatal(err)
	}

	var changedJSON, nodesJSON, claimsJSON, slicesJSON, resultState, attrsJSON string
	if err := st.DB().QueryRowContext(ctx, `SELECT changed_paths_json, affected_nodes_json, affected_claims_json, affected_slices_json, result_state, attrs_json FROM updates WHERE id = ?`, "upd-test").Scan(&changedJSON, &nodesJSON, &claimsJSON, &slicesJSON, &resultState, &attrsJSON); err != nil {
		t.Fatal(err)
	}
	if resultState != "ready" {
		t.Fatalf("result_state = %q, want ready", resultState)
	}
	assertJSONStrings(t, changedJSON, []string{"src/app.go"})
	assertJSONStrings(t, nodesJSON, []string{"capability:app"})
	assertJSONStrings(t, claimsJSON, []string{"claim:app"})
	assertJSONStrings(t, slicesJSON, []string{"slice:runtime"})
	var attrs map[string]any
	if err := json.Unmarshal([]byte(attrsJSON), &attrs); err != nil {
		t.Fatal(err)
	}
	if _, ok := attrs["known_unknowns"]; !ok {
		t.Fatalf("attrs = %#v, want known_unknowns", attrs)
	}
}

func assertJSONStrings(t *testing.T, raw string, want []string) {
	t.Helper()
	var got []string
	if err := json.Unmarshal([]byte(raw), &got); err != nil {
		t.Fatal(err)
	}
	if len(got) != len(want) {
		t.Fatalf("got %#v, want %#v", got, want)
	}
	for index := range want {
		if got[index] != want[index] {
			t.Fatalf("got %#v, want %#v", got, want)
		}
	}
}
```

- [ ] **Step 2: Run the failing store test**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/store -run TestRecordStructuredUpdatePersistsAffectedFields -count=1
Pop-Location
```

Expected: FAIL because `UpdateRecord` and `RecordStructuredUpdate` are not defined.

- [ ] **Step 3: Add the store update record type**

In `tools/project-cognition/internal/store/store.go`, add:

```go
type UpdateRecord struct {
	ID             string
	Trigger        string
	ChangedPaths   []string
	AffectedNodes  []string
	AffectedClaims []string
	AffectedSlices []string
	ResultState    string
	Attrs          map[string]any
}
```

- [ ] **Step 4: Implement structured persistence**

Replace `RecordUpdate` with a compatibility wrapper and add the structured method:

```go
func (s *Store) RecordUpdate(ctx context.Context, id, reason, changedPathsJSON string) error {
	var changed []string
	if strings.TrimSpace(changedPathsJSON) != "" {
		_ = json.Unmarshal([]byte(changedPathsJSON), &changed)
	}
	return s.RecordStructuredUpdate(ctx, UpdateRecord{
		ID:           id,
		Trigger:      reason,
		ChangedPaths: changed,
		ResultState:  "recorded",
		Attrs:        map[string]any{"legacy_record_update": true},
	})
}

func (s *Store) RecordStructuredUpdate(ctx context.Context, record UpdateRecord) error {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return err
	}
	if generationID == "" {
		return nil
	}
	if strings.TrimSpace(record.ResultState) == "" {
		record.ResultState = "blocked"
	}
	now := time.Now().UTC().Format(time.RFC3339)
	changedJSON, err := json.Marshal(record.ChangedPaths)
	if err != nil {
		return fmt.Errorf("encode update changed paths: %w", err)
	}
	nodesJSON, err := json.Marshal(record.AffectedNodes)
	if err != nil {
		return fmt.Errorf("encode update affected nodes: %w", err)
	}
	claimsJSON, err := json.Marshal(record.AffectedClaims)
	if err != nil {
		return fmt.Errorf("encode update affected claims: %w", err)
	}
	slicesJSON, err := json.Marshal(record.AffectedSlices)
	if err != nil {
		return fmt.Errorf("encode update affected slices: %w", err)
	}
	attrs, err := attrsJSONOrEmpty(record.Attrs)
	if err != nil {
		return fmt.Errorf("encode update attrs: %w", err)
	}
	_, err = s.db.ExecContext(ctx, `INSERT INTO updates(id, generation_id, trigger, changed_paths_json, affected_nodes_json, affected_claims_json, affected_slices_json, result_state, completed_at, attrs_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, record.ID, generationID, record.Trigger, string(changedJSON), string(nodesJSON), string(claimsJSON), string(slicesJSON), record.ResultState, now, attrs)
	if err != nil {
		return fmt.Errorf("record structured update: %w", err)
	}
	return nil
}
```

- [ ] **Step 5: Route update code through structured persistence**

In `tools/project-cognition/internal/update/state.go`, replace direct `st.RecordUpdate` calls with `st.RecordStructuredUpdate`. Use this initial record shape until Task 3 computes full closure:

```go
if err := st.RecordStructuredUpdate(context.Background(), store.UpdateRecord{
	ID:            updateID,
	Trigger:       input.Reason,
	ChangedPaths:  kept,
	AffectedNodes: nodeIDsFromRows(nodes),
	ResultState:   ResultPartialRefresh,
	Attrs: map[string]any{
		"workflow":           input.Workflow,
		"behavior_surfaces":  input.BehaviorSurfaces,
		"generated_surfaces": input.GeneratedSurfaces,
		"state_contracts":    input.StateContracts,
		"verification":       input.Verification,
		"known_unknowns":     input.KnownUnknowns,
		"confidence_notes":   input.ConfidenceNotes,
	},
}); err != nil {
	return UpdatePayload{}, err
}
```

Add this helper:

```go
func nodeIDsFromRows(rows []map[string]any) []string {
	ids := make([]string, 0, len(rows))
	seen := map[string]bool{}
	for _, row := range rows {
		id, ok := row["id"].(string)
		if !ok || id == "" || seen[id] {
			continue
		}
		seen[id] = true
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}
```

- [ ] **Step 6: Run tests and commit**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/store ./internal/update -count=1
Pop-Location
```

Expected: all store tests pass; update tests compile against structured persistence.

Commit:

```powershell
git add tools/project-cognition/internal/store/store.go tools/project-cognition/internal/store/update_test.go tools/project-cognition/internal/update/state.go tools/project-cognition/internal/update/state_test.go
git commit -m "feat: persist structured project cognition updates"
```

---

### Task 3: Implement Result-State Mapping And Non-Delta Engine Semantics

**Files:**
- Modify: `tools/project-cognition/internal/update/state.go`
- Modify: `tools/project-cognition/internal/update/state_test.go`
- Modify: `tools/project-cognition/internal/validation/build.go`
- Modify: `tools/project-cognition/internal/buildgate/sparse.go`
- Modify: `tools/project-cognition/internal/runtime/status.go`

- [ ] **Step 1: Add result-state tests**

Append these tests to `tools/project-cognition/internal/update/state_test.go`:

```go
func TestRunUpdateNoOpWhenAllChangedPathsAreIgnored(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	if err := os.WriteFile(filepath.Join(paths.Root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"vendor/a.go"},
		Reason:       "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultNoOp {
		t.Fatalf("ResultState = %q, want %q", payload.ResultState, ResultNoOp)
	}
	if containsString(payload.MinimalLiveReads, "vendor/a.go") {
		t.Fatalf("MinimalLiveReads = %#v, did not want ignored path", payload.MinimalLiveReads)
	}
}

func TestRunUpdatePathOnlyUnknownCoverageReturnsPartialRefresh(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths: []string{"src/new-feature.go"},
		Reason:       "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultPartialRefresh {
		t.Fatalf("ResultState = %q, want partial_refresh", payload.ResultState)
	}
	if payload.Readiness != "review" {
		t.Fatalf("Readiness = %q, want review", payload.Readiness)
	}
	if !containsString(payload.MinimalLiveReads, "src/new-feature.go") {
		t.Fatalf("MinimalLiveReads = %#v, want changed path", payload.MinimalLiveReads)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastUpdateOutcome != ResultPartialRefresh {
		t.Fatalf("LastUpdateOutcome = %q", status.LastUpdateOutcome)
	}
}

func TestRunUpdatePayloadForIndexedPathReturnsReady(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	payload, err := RunUpdate(paths, UpdateInput{
		ChangedPaths:     []string{"src/app.go"},
		Reason:           "workflow-finalize",
		Workflow:         "sp-implement",
		BehaviorSurfaces: []string{"application entrypoint"},
		Verification: []VerificationEvidence{
			{Command: "go test ./...", Result: "passed", Artifact: "artifacts/quality-runs/example/report.md"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v", payload.ResultState, payload)
	}
	if payload.Readiness != rt.ReadyReadiness {
		t.Fatalf("Readiness = %q, want query_ready", payload.Readiness)
	}
	if len(payload.AffectedNodes) == 0 {
		t.Fatalf("AffectedNodes = %#v, want indexed node", payload.AffectedNodes)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.Freshness != rt.ReadyFreshness || status.LastUpdateOutcome != ResultReady {
		t.Fatalf("status = %#v", status)
	}
}
```

- [ ] **Step 2: Run the failing update tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/update -run "TestRunUpdateNoOpWhenAllChangedPathsAreIgnored|TestRunUpdatePathOnlyUnknownCoverageReturnsPartialRefresh|TestRunUpdatePayloadForIndexedPathReturnsReady" -count=1
Pop-Location
```

Expected: FAIL because `ResultState`, `review` readiness, and ready mapping are not implemented.

- [ ] **Step 3: Add review freshness/readiness constants**

In `tools/project-cognition/internal/runtime/status.go`, add:

```go
PartialRefreshFreshness = "partial_refresh"
ReviewReadiness         = "review"
```

- [ ] **Step 4: Add result-state status mapping**

In `tools/project-cognition/internal/update/state.go`, add:

```go
func applyResultState(status rt.Status, resultState string, updateID string, changedPaths []string, reason string) rt.Status {
	status.LastUpdateID = updateID
	status.LastUpdateOutcome = resultState
	status.LastRefreshChangedFilesBasis = append([]string{}, changedPaths...)
	switch resultState {
	case ResultReady:
		status.Status = "fresh"
		status.Freshness = rt.ReadyFreshness
		status.Readiness = rt.ReadyReadiness
		status.RecommendedNextAction = "use_project_cognition"
		status.Dirty = false
		status.StalePaths = subtractStrings(status.StalePaths, changedPaths)
		status.StaleReasons = subtractStrings(status.StaleReasons, []string{reason})
	case ResultNoOp:
		if status.Readiness == "" {
			status.Readiness = rt.ReadyReadiness
		}
	case ResultPartialRefresh:
		status.Status = "stale"
		status.Freshness = rt.PartialRefreshFreshness
		status.Readiness = rt.ReviewReadiness
		status.RecommendedNextAction = "review_project_cognition_update"
		status.Dirty = true
		status.StalePaths = appendUnique(status.StalePaths, changedPaths...)
		status.StaleReasons = appendUnique(status.StaleReasons, reason)
	case ResultNeedsRebuild:
		status.Status = "stale"
		status.Freshness = rt.StaleFreshness
		status.Readiness = rt.NeedsRebuildReadiness
		status.RecommendedNextAction = "run_map_scan_build"
		status.Dirty = true
		status.StalePaths = appendUnique(status.StalePaths, changedPaths...)
		status.StaleReasons = appendUnique(status.StaleReasons, reason)
	default:
		status.Status = "stale"
		status.Freshness = rt.StaleFreshness
		status.Readiness = rt.BlockedReadiness
		status.RecommendedNextAction = "review_project_cognition_update"
		status.Dirty = true
		status.StalePaths = appendUnique(status.StalePaths, changedPaths...)
		status.StaleReasons = appendUnique(status.StaleReasons, reason)
	}
	return status
}

func subtractStrings(values []string, remove []string) []string {
	removeSet := map[string]bool{}
	for _, value := range remove {
		removeSet[value] = true
	}
	out := make([]string, 0, len(values))
	for _, value := range values {
		if !removeSet[value] {
			out = append(out, value)
		}
	}
	return out
}
```

- [ ] **Step 5: Compute result state in non-delta update**

In `RunUpdate`, after ignore filtering and node lookup, compute:

```go
resultState := ResultPartialRefresh
if len(kept) == 0 {
	resultState = ResultNoOp
} else if len(nodes) > 0 && len(input.Verification) > 0 && len(input.KnownUnknowns) == 0 {
	resultState = ResultReady
}
```

Use `applyResultState` before writing status, set `payload.ResultState`, and use `statusUpdateFromStatus`.

- [ ] **Step 6: Preserve path-only compatibility as partial when closure is not provable**

Keep path-only requests without verification evidence in `partial_refresh` unless all paths are ignored. Do not promote `last_update_id` alone to ready.

- [ ] **Step 7: Run update and validation tests, then commit**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/update ./internal/runtime ./internal/validation ./internal/buildgate -count=1
Pop-Location
```

Expected: all targeted tests pass.

Commit:

```powershell
git add tools/project-cognition/internal/update/state.go tools/project-cognition/internal/update/state_test.go tools/project-cognition/internal/runtime/status.go tools/project-cognition/internal/validation/build.go tools/project-cognition/internal/buildgate/sparse.go
git commit -m "feat: map update results to runtime status"
```

---

### Task 4: Refresh Affected Closure And Path Adoption

**Files:**
- Modify: `tools/project-cognition/internal/store/store.go`
- Modify: `tools/project-cognition/internal/store/update_test.go`
- Modify: `tools/project-cognition/internal/update/state.go`
- Modify: `tools/project-cognition/internal/update/state_test.go`

- [ ] **Step 1: Add affected closure test**

Append to `tools/project-cognition/internal/store/update_test.go`:

```go
func TestAffectedClosureForPathsReturnsNodesClaimsAndSlices(t *testing.T) {
	st := openImportTestStore(t)
	ctx := context.Background()
	input := validImportInput("GEN-closure")
	input.Claims = append(input.Claims, ClaimImport{
		ID:          "claim:app",
		SubjectRef:  "capability:app",
		Predicate:   "owns",
		ObjectText:  "src/app.go",
		Confidence:  "verified",
		EvidenceIDs: []string{"E-001"},
	})
	input.SliceMembers = append(input.SliceMembers, SliceMemberImport{
		ID:         "slice-member:app",
		SliceID:    "slice:runtime",
		ObjectType: "node",
		ObjectID:   "capability:app",
		Rank:       1,
		Reason:     "runtime entrypoint",
	})
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	closure, err := st.AffectedClosureForPaths(ctx, []string{"src/app.go"})
	if err != nil {
		t.Fatal(err)
	}
	if !containsString(closure.NodeIDs, "capability:app") {
		t.Fatalf("closure = %#v", closure)
	}
	if !containsString(closure.ClaimIDs, "claim:app") {
		t.Fatalf("closure = %#v", closure)
	}
	if !containsString(closure.SliceIDs, "slice:runtime") {
		t.Fatalf("closure = %#v", closure)
	}
}
```

- [ ] **Step 2: Add path adoption persistence test**

Append:

```go
func TestRefreshPathCoverageUpdatesIndexedPathEvidence(t *testing.T) {
	st := openImportTestStore(t)
	ctx := context.Background()
	input := validImportInput("GEN-adopt")
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	record, err := st.RefreshPathCoverage(ctx, PathCoverageRefresh{
		UpdateID:   "upd-adopt",
		Path:       "src/app.go",
		NodeID:     "capability:app",
		Relation:   "owns",
		Confidence: "verified",
		Reason:     "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if record.EvidenceID == "" {
		t.Fatalf("record = %#v, want evidence id", record)
	}
	var evidenceID string
	if err := st.DB().QueryRowContext(ctx, `SELECT evidence_id FROM path_index WHERE generation_id = ? AND path = ?`, "GEN-adopt", "src/app.go").Scan(&evidenceID); err != nil {
		t.Fatal(err)
	}
	if evidenceID != record.EvidenceID {
		t.Fatalf("path evidence = %q, want %q", evidenceID, record.EvidenceID)
	}
}
```

- [ ] **Step 3: Run failing store tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/store -run "TestAffectedClosureForPathsReturnsNodesClaimsAndSlices|TestRefreshPathCoverageUpdatesIndexedPathEvidence" -count=1
Pop-Location
```

Expected: FAIL because closure and refresh helpers are missing.

- [ ] **Step 4: Add store types and closure helper**

In `tools/project-cognition/internal/store/store.go`, add:

```go
type AffectedClosure struct {
	NodeIDs  []string
	ClaimIDs []string
	SliceIDs []string
}

type PathCoverageRefresh struct {
	UpdateID   string
	Path       string
	NodeID     string
	Relation   string
	Confidence string
	Reason     string
}

type PathCoverageRefreshResult struct {
	EvidenceID string
	PathIndexID string
}
```

Implement `AffectedClosureForPaths` by querying active-generation `path_index -> nodes`, `claims.subject_ref`, and `slice_members.object_id`:

```go
func (s *Store) AffectedClosureForPaths(ctx context.Context, paths []string) (AffectedClosure, error) {
	nodes, err := s.NodesForPaths(ctx, paths)
	if err != nil {
		return AffectedClosure{}, err
	}
	nodeIDs := nodeIDsFromMaps(nodes)
	claims, err := s.claimIDsForSubjects(ctx, nodeIDs)
	if err != nil {
		return AffectedClosure{}, err
	}
	slices, err := s.sliceIDsForObjects(ctx, nodeIDs)
	if err != nil {
		return AffectedClosure{}, err
	}
	return AffectedClosure{
		NodeIDs:  uniqueSorted(nodeIDs),
		ClaimIDs: uniqueSorted(claims),
		SliceIDs: uniqueSorted(slices),
	}, nil
}
```

Add focused private helpers `claimIDsForSubjects`, `sliceIDsForObjects`, `nodeIDsFromMaps`, and `uniqueSorted` in the same file. Each helper should return an empty slice for an empty input instead of building invalid SQL.

- [ ] **Step 5: Implement path coverage refresh**

Add `RefreshPathCoverage` to `store.go`:

```go
func (s *Store) RefreshPathCoverage(ctx context.Context, refresh PathCoverageRefresh) (PathCoverageRefreshResult, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return PathCoverageRefreshResult{}, err
	}
	if generationID == "" {
		return PathCoverageRefreshResult{}, fmt.Errorf("project-cognition.db has no active generation")
	}
	now := time.Now().UTC().Format(time.RFC3339)
	evidenceID := "E-update-" + refresh.UpdateID + "-" + stableIDPart(refresh.Path)
	pathIndexID := "P-update-" + stableIDPart(refresh.Path)
	attrs, err := attrsJSONOrEmpty(map[string]any{"update_id": refresh.UpdateID, "reason": refresh.Reason})
	if err != nil {
		return PathCoverageRefreshResult{}, err
	}
	_, err = s.db.ExecContext(ctx, `INSERT INTO evidence(id, generation_id, source_kind, source_path, commit_sha, span, extractor, content_hash, captured_at, attrs_json) VALUES(?, ?, 'workflow_update', ?, '', '', 'project-cognition update', '', ?, ?) ON CONFLICT(id) DO UPDATE SET captured_at=excluded.captured_at, attrs_json=excluded.attrs_json`, evidenceID, generationID, refresh.Path, now, attrs)
	if err != nil {
		return PathCoverageRefreshResult{}, fmt.Errorf("upsert update evidence: %w", err)
	}
	_, err = s.db.ExecContext(ctx, `INSERT INTO path_index(id, generation_id, path, node_id, relation, confidence, evidence_id, updated_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET node_id=excluded.node_id, relation=excluded.relation, confidence=excluded.confidence, evidence_id=excluded.evidence_id, updated_at=excluded.updated_at`, pathIndexID, generationID, refresh.Path, refresh.NodeID, refresh.Relation, refresh.Confidence, evidenceID, now)
	if err != nil {
		return PathCoverageRefreshResult{}, fmt.Errorf("upsert path coverage: %w", err)
	}
	return PathCoverageRefreshResult{EvidenceID: evidenceID, PathIndexID: pathIndexID}, nil
}
```

Add:

```go
func stableIDPart(value string) string {
	replacer := strings.NewReplacer("/", "-", "\\", "-", " ", "-", ".", "-", ":", "-")
	return strings.Trim(replacer.Replace(value), "-")
}
```

- [ ] **Step 6: Use closure in update records**

In `RunUpdate`, replace affected node computation with:

```go
closure, err := st.AffectedClosureForPaths(context.Background(), kept)
if err != nil {
	return UpdatePayload{}, err
}
```

Use `closure.NodeIDs`, `closure.ClaimIDs`, and `closure.SliceIDs` in `RecordStructuredUpdate`. For ready indexed paths, call `RefreshPathCoverage` for each kept path using the first affected node id:

```go
if resultState == ResultReady && len(closure.NodeIDs) > 0 {
	for _, path := range kept {
		if _, err := st.RefreshPathCoverage(context.Background(), store.PathCoverageRefresh{
			UpdateID:   updateID,
			Path:       path,
			NodeID:     closure.NodeIDs[0],
			Relation:   "owns",
			Confidence: "verified",
			Reason:     input.Reason,
		}); err != nil {
			return UpdatePayload{}, err
		}
	}
}
```

- [ ] **Step 7: Run runtime tests and commit**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/store ./internal/update -count=1
Pop-Location
```

Expected: all targeted tests pass.

Commit:

```powershell
git add tools/project-cognition/internal/store/store.go tools/project-cognition/internal/store/update_test.go tools/project-cognition/internal/update/state.go tools/project-cognition/internal/update/state_test.go
git commit -m "feat: refresh affected cognition closure"
```

---

### Task 5: Converge Delta-Session Update With The Shared Engine

**Files:**
- Modify: `tools/project-cognition/internal/update/state.go`
- Modify: `tools/project-cognition/internal/update/state_test.go`
- Modify: `tools/project-cognition/internal/boundary/**` only if boundary result needs an exported accessor.
- Modify: `tools/project-cognition/internal/delta/**` only if delta bundle needs an exported conversion helper.

- [ ] **Step 1: Add the delta convergence test**

Append to `tools/project-cognition/internal/update/state_test.go`:

```go
func TestRunUpdateWithDeltaSessionUsesResultStateContract(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	session, err := delta.Begin(delta.BeginInput{
		Root:              paths.Root,
		RuntimeDir:        paths.RuntimeDir,
		OriginCommand:     "implement",
		InitialDirtyPaths: []string{},
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir:        paths.RuntimeDir,
		SessionID:         session.SessionID,
		EventType:         "workflow_closeout",
		ChangedPaths:      []string{"src/app.go"},
		BehaviorSurfaces:  []string{"application entrypoint"},
		Verification:      []string{"go test ./... PASS"},
		KnownUnknowns:     []string{},
	}); err != nil {
		t.Fatal(err)
	}

	payload, err := RunUpdate(paths, UpdateInput{
		DeltaSessionID: session.SessionID,
		Reason:         "workflow-finalize",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.ResultState != ResultReady {
		t.Fatalf("ResultState = %q, payload=%#v", payload.ResultState, payload)
	}
	if payload.StatusUpdate.LastUpdateOutcome != ResultReady {
		t.Fatalf("StatusUpdate = %#v", payload.StatusUpdate)
	}
}
```

- [ ] **Step 2: Run the failing delta test**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/update -run TestRunUpdateWithDeltaSessionUsesResultStateContract -count=1
Pop-Location
```

Expected: FAIL because the delta path still returns boundary-only partial/blocked data.

- [ ] **Step 3: Convert boundary result into shared input**

In `tools/project-cognition/internal/update/state.go`, add:

```go
func updateInputFromBoundary(input UpdateInput, result boundary.Result) UpdateInput {
	input.ChangedPaths = append(input.ChangedPaths, result.ChangedPaths...)
	input.KnownUnknowns = append(input.KnownUnknowns, result.Warnings...)
	input.Boundary.WorkflowOwnedPaths = append(input.Boundary.WorkflowOwnedPaths, result.WorkflowOwnedPaths...)
	if input.CommitRange != "" {
		input.Boundary.CommitRange = input.CommitRange
	}
	return input
}
```

- [ ] **Step 4: Extract shared update finalization**

Create a helper with this signature in `tools/project-cognition/internal/update/state.go`:

```go
func runResolvedUpdate(paths rt.Paths, input UpdateInput, changed []string, ignored []string, boundaryResult *boundary.Result) (UpdatePayload, error)
```

The helper owns these operations in order:

1. Open the existing store when `.specify/project-cognition/project-cognition.db` exists.
2. Read affected closure through `st.AffectedClosureForPaths(context.Background(), changed)`.
3. Refresh path coverage for ready indexed paths through `st.RefreshPathCoverage`.
4. Compute `resultState` using the same rules from Task 3.
5. Persist `store.UpdateRecord` through `RecordStructuredUpdate`.
6. Read and update `status.json` with `applyResultState`.
7. Return `UpdatePayload` with `ResultState`, `StatusUpdate`, `ChangedPaths`, `IgnoredPaths`, `AffectedNodes`, `KnownUnknowns`, `MinimalLiveReads`, `PathAdoption`, and `Boundary`.

The non-delta `RunUpdate` path calls this helper after ignore filtering. The delta path calls the same helper after boundary resolution. Do not leave a second delta-only persistence or status-write path.

- [ ] **Step 5: Make `runDeltaSessionUpdate` call the shared helper**

After `boundary.Resolve`, do:

```go
	resolvedInput := updateInputFromBoundary(input, result)
	kept, ignored := ignore.Load(paths.Root).Filter(result.ChangedPaths)
	payload, err := runResolvedUpdate(paths, resolvedInput, normalizePaths(kept), normalizePaths(ignored), &result)
	if err != nil {
		return UpdatePayload{}, err
	}
	payload.UpdateOutcome = result.Outcome
	payload.Boundary = &result
	return payload, nil
```

Remove the delta-only `RecordUpdate` and stale/blocked status write.

- [ ] **Step 6: Run delta and non-delta tests, then commit**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/update ./internal/boundary ./internal/delta -count=1
Pop-Location
```

Expected: all tests pass; existing boundary diagnostics remain present in `payload.boundary`.

Commit:

```powershell
git add tools/project-cognition/internal/update/state.go tools/project-cognition/internal/update/state_test.go tools/project-cognition/internal/boundary tools/project-cognition/internal/delta
git commit -m "feat: converge delta updates on shared engine"
```

---

### Task 6: Enforce Result-State In Python Hook Validation And Fake Runtime

**Files:**
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `tests/contract/test_hook_cli_surface.py`
- Modify: `tests/project_cognition_fake.py`

- [ ] **Step 1: Add failing hook tests for result-state validation**

In `tests/contract/test_hook_cli_surface.py`, replace the old acceptance test that only sets `last_update_id` with:

```python
def test_hook_validate_artifacts_rejects_map_update_with_last_update_id_only(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _update_project_cognition_status(run_dir, version=1, last_update_id="UPD-001", stale_paths=["src/app.py"])

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
        check=False,
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
    assert any("result_state" in message for message in payload["errors"])
```

Add:

```python
def test_hook_validate_artifacts_accepts_map_update_with_ready_result_state(tmp_path: Path):
    project = _create_project(tmp_path)
    run_dir = project / ".specify" / "project-cognition"
    _write_project_cognition_runtime(run_dir)
    _update_project_cognition_status(
        run_dir,
        version=1,
        freshness="fresh",
        readiness="query_ready",
        last_update_id="UPD-001",
        last_update_outcome="ready",
        recommended_next_action="use_project_cognition",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-artifacts", "--command", "map-update", "--feature-dir", str(run_dir)],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "ok"
```

- [ ] **Step 2: Run failing hook tests**

Run:

```powershell
pytest tests/contract/test_hook_cli_surface.py -k "map_update_with_last_update_id_only or map_update_with_ready_result_state" -q
```

Expected: FAIL because current validation accepts `last_update_id` alone.

- [ ] **Step 3: Update artifact validation**

In `src/specify_cli/hooks/artifact_validation.py`, replace `_validate_map_update_artifacts` body after JSON parsing with:

```python
    result_state = str(payload.get("last_update_outcome") or payload.get("result_state") or "").strip()
    freshness = str(payload.get("freshness") or "").strip()
    readiness = str(payload.get("readiness") or "").strip()
    recommended = str(payload.get("recommended_next_action") or "").strip()
    valid_states = {"ready", "no_op", "partial_refresh", "needs_rebuild", "blocked"}
    if result_state not in valid_states:
        errors.append("status.json must record last_update_outcome/result_state as ready, no_op, partial_refresh, needs_rebuild, or blocked")
        return errors
    if result_state == "ready" and (freshness != "fresh" or readiness != "query_ready" or recommended != "use_project_cognition"):
        errors.append("ready map-update result_state requires freshness=fresh, readiness=query_ready, and recommended_next_action=use_project_cognition")
    if result_state == "partial_refresh" and freshness != "partial_refresh":
        errors.append("partial_refresh map-update result_state requires freshness=partial_refresh")
    if result_state == "needs_rebuild" and readiness != "needs_rebuild":
        errors.append("needs_rebuild map-update result_state requires readiness=needs_rebuild")
    if result_state == "blocked" and readiness != "blocked":
        errors.append("blocked map-update result_state requires readiness=blocked")
    if result_state == "no_op" and not payload.get("last_update_id"):
        errors.append("no_op map-update result_state requires last_update_id")
```

- [ ] **Step 4: Update fake project-cognition update**

In `tests/project_cognition_fake.py`, add an `_update(args)` function in the generated fake script:

```python
            def _update(args):
                payload = _read_status()
                result_state = "partial_refresh"
                if "--payload-file" in args:
                    result_state = "ready"
                payload["last_update_id"] = "upd-fake"
                payload["last_update_outcome"] = result_state
                payload["result_state"] = result_state
                if result_state == "ready":
                    payload["status"] = "fresh"
                    payload["freshness"] = "fresh"
                    payload["readiness"] = "query_ready"
                    payload["recommended_next_action"] = "use_project_cognition"
                    payload["dirty"] = False
                else:
                    payload["status"] = "stale"
                    payload["freshness"] = "partial_refresh"
                    payload["readiness"] = "review"
                    payload["recommended_next_action"] = "review_project_cognition_update"
                    payload["dirty"] = True
                _write_status(payload)
                payload["update_id"] = payload["last_update_id"]
                payload["status_update"] = {
                    "status": payload["status"],
                    "freshness": payload["freshness"],
                    "readiness": payload["readiness"],
                    "recommended_next_action": payload["recommended_next_action"],
                    "dirty": payload["dirty"],
                    "last_update_id": payload["last_update_id"],
                    "last_update_outcome": payload["last_update_outcome"],
                }
                return payload
```

In `main()`, add:

```python
                if command == "update":
                    print(json.dumps(_update(args)))
                    return 0
```

- [ ] **Step 5: Run hook/fake tests and commit**

Run:

```powershell
pytest tests/contract/test_hook_cli_surface.py -k map_update -q
pytest tests/test_map_runtime_template_guidance.py tests/project_cognition_fake.py -q
```

Expected: hook tests pass; fake runtime file is imported or skipped according to existing pytest collection behavior.

Commit:

```powershell
git add src/specify_cli/hooks/artifact_validation.py tests/contract/test_hook_cli_surface.py tests/project_cognition_fake.py
git commit -m "fix: validate map update result state"
```

---

### Task 7: Add Shared Inline Update Partial And Update Workflow Templates

**Files:**
- Create: `templates/command-partials/common/inline-project-cognition-update.md`
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/planning-context-loading-gradient.md`
- Modify: `templates/command-partials/common/navigation-check.md`
- Modify: `templates/commands/{fast,quick,implement,debug,specify,clarify,deep-research,plan,tasks,analyze,map-update}.md`
- Modify: `templates/command-partials/{fast,quick,implement,debug,specify,clarify,deep-research,plan,tasks,analyze}/shell.md`
- Modify: `templates/worker-prompts/{quick-worker,implementer,debug-investigator,debug-thinker,code-quality-reviewer,spec-reviewer}.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_command_surface_semantics.py`
- Modify: `tests/test_map_runtime_template_guidance.py`

- [ ] **Step 1: Add failing template alignment test**

In `tests/test_alignment_templates.py`, add:

```python
def test_inline_project_cognition_update_uses_shared_partial() -> None:
    shared = _read("templates/command-partials/common/inline-project-cognition-update.md")
    assert "project-cognition update --payload-file" in shared
    assert "result_state" in shared
    assert "recorded" in shared

    common_partials = [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/command-partials/common/navigation-check.md",
    ]
    for path in common_partials:
        content = _read(path)
        assert "inline-project-cognition-update.md" in content, path
        assert "project-cognition update --changed-path" not in content, path

    commands = [
        "templates/commands/fast.md",
        "templates/commands/quick.md",
        "templates/commands/implement.md",
        "templates/commands/debug.md",
        "templates/commands/map-update.md",
    ]
    for path in commands:
        assert "inline-project-cognition-update.md" in _read(path), path
```

- [ ] **Step 2: Run the failing alignment test**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_inline_project_cognition_update_uses_shared_partial -q
```

Expected: FAIL because the shared partial does not exist.

- [ ] **Step 3: Create the shared partial**

Create `templates/command-partials/common/inline-project-cognition-update.md`:

```markdown
### Inline Project Cognition Update

Workflow-owned mutation closeout is the workflow-local form of `{{invoke:map-update}}`. If this workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, shared surfaces, or behavior-bearing docs, closeout MUST run inline project cognition update for the workflow-owned changed paths and affected surfaces before claiming clean completion.

Use the current delta session when one exists:

```text
project-cognition delta append --session "$DELTA_SESSION_ID" --event-type workflow_closeout --changed-path "<path>" --behavior-surface "<surface>" --verification "<evidence>" --known-unknown "<unknown>" --format json
project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json
```

When no delta session exists, write a payload file under `.specify/project-cognition/updates/` and call:

```text
project-cognition update --payload-file ".specify/project-cognition/updates/<update-id>.json" --reason workflow-finalize --format json
```

The payload must include `workflow`, `reason`, `changed_paths`, `scope_paths`, `behavior_surfaces`, `generated_surfaces`, `state_contracts`, `verification`, `known_unknowns`, `confidence_notes`, `user_decisions`, and `boundary` when those facts exist.

Clean closeout keys on `result_state`, not `update_id`, `last_update_id`, or freshness alone:

- `ready` or `no_op`: project cognition closeout may be clean when ordinary verification also passed.
- `partial_refresh`: useful update data was written, but the final workflow state must report partial cognition closeout and the returned `minimal_live_reads`.
- `needs_rebuild`: report the exact rebuild condition and route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- `blocked`: report the runtime or validation blocker and the exact recovery command.
- `recorded`: legacy recorded-only output; treat it as partial or blocked, never as clean completion.

Use `project-cognition mark-dirty --reason "<reason>" --format json` only when inline update cannot record useful update data, cannot identify workflow-owned scope, or cannot be trusted because verification/workflow completion is not trustworthy.

`{{invoke:map-update}}` remains the external/manual workflow for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. It is not routine cleanup for changes this workflow just made.
```

- [ ] **Step 4: Delegate existing common partials to the shared partial**

In `context-loading-gradient.md`, replace the `### Mutation Closeout Rule` section with:

```markdown
### Mutation Closeout Rule

{{spec-kit-include: inline-project-cognition-update.md}}
```

In `planning-context-loading-gradient.md`, replace the inline closeout paragraph with:

```markdown
Planning-only artifact writes do not require project cognition refresh. If this planning workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, follow the shared inline closeout contract:

{{spec-kit-include: inline-project-cognition-update.md}}
```

In `navigation-check.md`, keep entry-only bullets and replace its closeout bullet with:

```markdown
- This navigation check is entry-only. Entry-time stale or weak cognition is advisory unless the user requested map maintenance. Workflow-owned mutation closeout is separate and governed by `context-loading-gradient.md` and `inline-project-cognition-update.md`.
```

- [ ] **Step 5: Update source-changing command templates**

For `fast.md`, `quick.md`, `implement.md`, and `debug.md`, replace repeated closeout paragraphs with:

```markdown
{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}
```

For `specify.md`, `clarify.md`, `deep-research.md`, `plan.md`, `tasks.md`, and `analyze.md`, keep artifact-only language and append:

```markdown
If this workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, follow the shared inline closeout contract:

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}
```

For `map-update.md`, add the helper command requirement:

```markdown
Before `validate-build` or `complete-refresh`, build a payload or delta session and call:

```text
project-cognition update --payload-file ".specify/project-cognition/updates/<map-update-id>.json" --reason map-update --format json
```

Use the returned `result_state` to decide whether to finalize, report `partial_refresh`, route to rebuild, or report blocked state.
```

- [ ] **Step 6: Update worker prompt handoff evidence**

In each mutable worker prompt, require this completion block:

```markdown
When you changed project-related files, include `changed_paths`, `behavior_surfaces`, `generated_surfaces`, `state_contracts`, `verification`, `known_unknowns`, and `confidence_notes` in the worker result so the parent workflow can build the inline project cognition update payload.
```

- [ ] **Step 7: Run template tests and commit**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_inline_project_cognition_update_uses_shared_partial tests/test_command_surface_semantics.py tests/test_map_runtime_template_guidance.py -q
```

Expected: tests pass and no template carries the weaker `project-cognition update --changed-path` closeout as the main clean path.

Commit:

```powershell
git add templates tests/test_alignment_templates.py tests/test_command_surface_semantics.py tests/test_map_runtime_template_guidance.py
git commit -m "feat: share inline project cognition closeout contract"
```

---

### Task 8: Align Generated Integration Addenda

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/cursor_agent/__init__.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_cursor_agent.py`

- [ ] **Step 1: Add integration assertions for payload/result-state wording**

In each listed integration test file, extend existing project cognition assertions with:

```python
assert "project-cognition update --payload-file" in content
assert "result_state" in content
assert "update_id" in content
assert "clean closeout" in content
```

For Cursor, add:

```python
assert "recorded" in content
assert "sp-map-update" in content
assert "manual/external" in content
```

- [ ] **Step 2: Run failing integration tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_cursor_agent.py -q
```

Expected: FAIL because addenda still mention the old path-only fallback.

- [ ] **Step 3: Update shared integration addenda**

In `src/specify_cli/integrations/base.py`, update `_append_planning_skill_cognition_refresh_guidance` and the generated project cognition addendum text to say:

```python
"- Inline project cognition update uses `project-cognition delta append` followed by `project-cognition update --delta-session \"$DELTA_SESSION_ID\" --reason workflow-finalize --format json` when a delta session exists. Without a delta session, write `.specify/project-cognition/updates/<update-id>.json` and run `project-cognition update --payload-file \".specify/project-cognition/updates/<update-id>.json\" --reason workflow-finalize --format json`.\n"
"- Clean closeout keys on `result_state`, not `update_id`, `last_update_id`, or freshness alone. Treat `recorded` as legacy partial/blocked output, not success.\n"
```

- [ ] **Step 4: Update Cursor addendum**

In `src/specify_cli/integrations/cursor_agent/__init__.py`, replace the old inline update line with the same two-line contract from Step 3.

- [ ] **Step 5: Run integration tests and commit**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_cursor_agent.py -q
```

Expected: all integration tests pass.

Commit:

```powershell
git add src/specify_cli/integrations/base.py src/specify_cli/integrations/cursor_agent/__init__.py tests/integrations
git commit -m "feat: align integration inline update guidance"
```

---

### Task 9: Align Passive Skills And User Docs

**Files:**
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/subagent-driven-development/SKILL.md`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/installation.md`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_runtime_handbook_contract.py`

- [ ] **Step 1: Add docs assertions**

In `tests/test_specify_guidance_docs.py`, add assertions to the existing project cognition guidance test:

```python
assert "project-cognition update --payload-file" in readme_lower
assert "result_state" in readme_lower
assert "update_id" in readme_lower
assert "recorded-only" in readme_lower
assert "project-cognition update --payload-file" in quickstart_lower
assert "result_state" in quickstart_lower
```

In `tests/test_runtime_handbook_contract.py`, assert:

```python
assert "result_state" in content.lower()
assert "project-cognition update --payload-file" in content.lower()
```

- [ ] **Step 2: Run failing docs tests**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py -q
```

Expected: FAIL because docs still describe inline update without the payload/result-state contract.

- [ ] **Step 3: Update passive skills**

In each passive skill, replace old inline update wording with:

```markdown
Inline update is map-update-equivalent for workflow-owned changes. Use `project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json` when a delta session exists. Without a delta session, write `.specify/project-cognition/updates/<update-id>.json` and run `project-cognition update --payload-file ".specify/project-cognition/updates/<update-id>.json" --reason workflow-finalize --format json`. Clean closeout keys on `result_state`, not `update_id`, `last_update_id`, or freshness alone; `recorded` is legacy partial/blocked output.
```

In `subagent-driven-development`, add:

```markdown
Worker results for mutable work must include changed paths, behavior surfaces, generated surfaces, state contracts, verification, known unknowns, and confidence notes so the parent workflow can build the inline update payload.
```

- [ ] **Step 4: Update docs and handbook**

In `README.md`, `PROJECT-HANDBOOK.md`, `templates/project-handbook-template.md`, `docs/quickstart.md`, and `docs/installation.md`, add the same user-facing rule:

```markdown
Workflow-owned mutation closeout uses the same lower-level update engine as `sp-map-update`. Delta-session closeout calls `project-cognition update --delta-session "$DELTA_SESSION_ID" --reason workflow-finalize --format json`; non-delta closeout writes `.specify/project-cognition/updates/<update-id>.json` and calls `project-cognition update --payload-file ".specify/project-cognition/updates/<update-id>.json" --reason workflow-finalize --format json`. A clean closeout requires `result_state=ready` or `result_state=no_op`; `update_id`, `last_update_id`, freshness, and legacy `recorded` output are not enough.
```

- [ ] **Step 5: Run docs tests and commit**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py tests/test_alignment_templates.py -q
```

Expected: docs and passive skill tests pass.

Commit:

```powershell
git add templates/passive-skills README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md docs/quickstart.md docs/installation.md tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py tests/test_alignment_templates.py
git commit -m "docs: document result-state inline update closeout"
```

---

### Task 10: Full Verification And Drift Scan

**Files:**
- Modify only files needed to fix failures found by the commands in this task.

- [ ] **Step 1: Run Go runtime tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./... -count=1
Pop-Location
```

Expected: all Go tests pass.

- [ ] **Step 2: Run targeted Python regression tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_command_surface_semantics.py tests/test_map_runtime_template_guidance.py tests/contract/test_hook_cli_surface.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_cursor_agent.py tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py -q
```

Expected: all targeted tests pass.

- [ ] **Step 3: Run repository verification**

Run:

```powershell
bun run verify
```

Expected: repository verification passes, or reports only documented policy approval gates unrelated to test correctness.

- [ ] **Step 4: Scan for stale closeout wording**

Run:

```powershell
rg -n "project-cognition update --changed-path|last_update_id.*clean|update_id.*clean|result_state=.*recorded|recorded-only.*success|freshness.*alone" templates src tests README.md PROJECT-HANDBOOK.md docs
```

Expected: no matches that describe clean inline closeout from path-only, update-id-only, freshness-only, or recorded-only output. Matches inside tests that assert rejection are acceptable when the assertion text clearly rejects the behavior.

- [ ] **Step 5: Run whitespace and status checks**

Run:

```powershell
git diff --check
git status --short
```

Expected: `git diff --check` has no output; `git status --short` shows only intended files before the final commit.

- [ ] **Step 6: Final commit**

Run:

```powershell
git add tools/project-cognition src/specify_cli templates tests README.md PROJECT-HANDBOOK.md docs templates/project-handbook-template.md
git commit -m "feat: make inline cognition update map-update equivalent"
```

Expected: final commit succeeds. If earlier task commits already captured every file and `git status --short` is clean, skip this commit and record that no final commit was needed.

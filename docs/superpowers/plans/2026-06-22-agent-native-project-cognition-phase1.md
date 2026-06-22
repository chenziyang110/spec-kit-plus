# Agent-Native Project Cognition Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Git-native `project-cognition changes` command and wire `sp-map-update` to use it with explicit `result_state` and refresh-finalizer gates.

**Architecture:** The Go runtime owns change detection so agents do not guess from memory or broad search. `changes` reuses existing Git status/diff helpers, `.cognitionignore`, runtime status, and path-index lookups to emit an agent-oriented JSON change plan. Generated `sp-map-update` guidance consumes that plan before `update`, then gates completion on `result_state`, `validate-build`, and `complete-refresh` or `record-refresh`.

**Tech Stack:** Go `tools/project-cognition`, SQLite-backed runtime store, Python `pytest` template/install tests, Markdown workflow templates.

---

## Scope

This is the first executable slice of `docs/superpowers/specs/2026-06-22-agent-native-project-cognition-design.md`.

In scope:
- Git-native `project-cognition changes --format json`.
- Recording the Git commit that a refresh is based on.
- `sp-map-update` guidance that starts from `changes` and finalizes only from accepted `result_state`.
- Runtime installer compatibility checks for the new command.
- Focused Go and Python regression tests.

Out of scope for this plan:
- `project-cognition inventory`.
- `project-cognition extract-structure`.
- `project-cognition packetize-scan`.
- `project-cognition normalize-scan`.
- Broad scan/build prompt redesign beyond the small docs surface needed to keep command lists accurate.

## File Structure

- Create `tools/project-cognition/internal/changes/changes.go`
  - Owns the new command's domain logic: merge Git committed and working-tree changes, filter `.cognitionignore`, classify known versus unknown runtime paths, and emit the JSON payload.
- Create `tools/project-cognition/internal/changes/changes_test.go`
  - Unit/integration tests for status changes, commit-range changes, ignored paths, and path-index awareness.
- Modify `tools/project-cognition/internal/cli/cli.go`
  - Adds `changes` dispatch, help text, flags, and JSON command plumbing.
- Modify `tools/project-cognition/internal/cli/cli_test.go`
  - Adds end-to-end CLI tests for `changes --format json`, ignored path accounting, and help exposure.
- Modify `tools/project-cognition/internal/runtime/status.go`
  - Adds refresh Git baseline fields to runtime status.
- Modify `tools/project-cognition/internal/update/state.go`
  - Writes refresh Git baseline fields from `CompleteRefresh` and `RecordRefresh`.
- Modify `tools/project-cognition/internal/update/state_test.go`
  - Verifies refresh finalizers record the current Git HEAD when available and do not fail outside Git.
- Modify `src/specify_cli/project_cognition_runtime.py`
  - Requires the new command in cached/release/runtime compatibility checks.
- Modify `tests/test_project_cognition_runtime_install.py`
  - Extends binary support fixtures and failure coverage for `changes`.
- Modify `templates/commands/map-update.md`
  - Makes `project-cognition changes --format json` the first runtime action in Git delta intake and tightens `result_state` finalization wording.
- Modify `tests/test_map_scan_build_template_guidance.py`
  - Adds template assertions for `changes`, `result_state`, `complete-refresh`, and `record-refresh` behavior.
- Modify `README.md`, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md`
  - Adds the command to the user/operator project-cognition command surface only where command lists already exist.
- Modify docs tests that fail after the docs wording update, likely `tests/test_runtime_handbook_contract.py`.

## JSON Contract

The `changes` command must emit this shape:

```json
{
  "status": "ok",
  "readiness": "query_ready",
  "baseline_commit": "abc123",
  "head_commit": "def456",
  "working_tree_dirty": true,
  "next_action": "affected_closure",
  "summary": {
    "total": 2,
    "included": 1,
    "ignored": 1,
    "known": 1,
    "unknown": 0,
    "deleted": 0,
    "renamed": 0
  },
  "changes": [
    {
      "path": "src/app.go",
      "old_path": "",
      "git_status": "M",
      "sources": ["working_tree"],
      "tracked": true,
      "working_tree_dirty": true,
      "ignored_by_cognition": false,
      "known_to_runtime": true,
      "node_id": "N-app",
      "change_level": "mapped_change",
      "recommended_action": "affected_closure",
      "reason": ["path exists in active runtime path_index"]
    }
  ],
  "ignored_paths": ["scratch/out.log"],
  "unknown_paths": [],
  "warnings": [],
  "errors": []
}
```

Allowed `next_action` values for this phase:
- `no_op`: no included changes remain after `.cognitionignore`.
- `affected_closure`: at least one included change maps to runtime path index.
- `partial_refresh`: at least one included change is missing runtime path coverage.
- `needs_rebuild`: runtime status or DB is unusable.
- `blocked`: Git is unavailable or command input is invalid.

Allowed `change_level` values for this phase:
- `ignored`
- `mapped_change`
- `new_path`
- `deleted_path`
- `renamed_path`
- `unknown_path`

## Task 1: Status Stores Refresh Git Baseline

**Files:**
- Modify: `tools/project-cognition/internal/runtime/status.go`
- Modify: `tools/project-cognition/internal/update/state.go`
- Modify: `tools/project-cognition/internal/update/state_test.go`

- [ ] **Step 1: Add failing tests for refresh Git metadata**

Append these tests to `tools/project-cognition/internal/update/state_test.go`:

```go
func TestCompleteRefreshRecordsGitBaselineCommit(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	initGitRepositoryForUpdateTest(t, paths.Root)

	before, err := rt.GitHead(paths.Root)
	if err != nil {
		t.Fatalf("GitHead before complete refresh: %v", err)
	}

	status, err := CompleteRefresh(paths, "map-update")
	if err != nil {
		t.Fatalf("CompleteRefresh returned error: %v", err)
	}

	if status.LastRefreshGitCommit != before {
		t.Fatalf("LastRefreshGitCommit = %q, want %q", status.LastRefreshGitCommit, before)
	}
	if status.LastRefreshGitBranch == "" {
		t.Fatal("LastRefreshGitBranch is empty")
	}
}

func TestRecordRefreshRecordsGitBaselineCommitWhenGitExists(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)
	initGitRepositoryForUpdateTest(t, paths.Root)

	want, err := rt.GitHead(paths.Root)
	if err != nil {
		t.Fatalf("GitHead before record refresh: %v", err)
	}

	status, err := RecordRefresh(paths, "map-update")
	if err != nil {
		t.Fatalf("RecordRefresh returned error: %v", err)
	}

	if status.LastRefreshGitCommit != want {
		t.Fatalf("LastRefreshGitCommit = %q, want %q", status.LastRefreshGitCommit, want)
	}
	if status.LastRefreshGitBranch == "" {
		t.Fatal("LastRefreshGitBranch is empty")
	}
}

func TestRecordRefreshDoesNotFailOutsideGitRepository(t *testing.T) {
	paths := testPaths(t)
	seedReadyRuntime(t, paths)

	status, err := RecordRefresh(paths, "manual")
	if err != nil {
		t.Fatalf("RecordRefresh returned error outside git repository: %v", err)
	}
	if status.LastRefreshGitCommit != "" {
		t.Fatalf("LastRefreshGitCommit = %q, want empty outside git", status.LastRefreshGitCommit)
	}
}

func initGitRepositoryForUpdateTest(t *testing.T, root string) {
	t.Helper()
	runUpdateGit(t, root, "init")
	runUpdateGit(t, root, "config", "user.email", "test@example.com")
	runUpdateGit(t, root, "config", "user.name", "Test User")
	runUpdateGit(t, root, "add", ".")
	runUpdateGit(t, root, "commit", "-m", "baseline")
}

func runUpdateGit(t *testing.T, root string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v failed: %v\n%s", args, err, output)
	}
	return string(output)
}
```

Add `os/exec` to the `state_test.go` imports if it is not already present:

```go
	"os/exec"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/update -run 'Test(CompleteRefreshRecordsGitBaselineCommit|RecordRefreshRecordsGitBaselineCommitWhenGitExists|RecordRefreshDoesNotFailOutsideGitRepository)' -count=1
```

Expected: FAIL because `rt.Status` has no `LastRefreshGitCommit` or `LastRefreshGitBranch` fields.

- [ ] **Step 3: Add status fields**

In `tools/project-cognition/internal/runtime/status.go`, add these fields after `LastRefreshBasis`:

```go
	LastRefreshGitCommit         string   `json:"last_refresh_git_commit,omitempty"`
	LastRefreshGitBranch         string   `json:"last_refresh_git_branch,omitempty"`
```

- [ ] **Step 4: Record Git baseline in refresh finalizers**

In `tools/project-cognition/internal/update/state.go`, add this helper near `RecordRefresh`:

```go
func recordGitRefreshBaseline(paths rt.Paths, status *rt.Status) {
	if !rt.GitAvailable(paths.Root) {
		status.LastRefreshGitCommit = ""
		status.LastRefreshGitBranch = ""
		return
	}
	if commit, err := rt.GitHead(paths.Root); err == nil {
		status.LastRefreshGitCommit = commit
	}
	if branch, err := rt.GitBranch(paths.Root); err == nil {
		status.LastRefreshGitBranch = branch
	}
}
```

Call it in `RecordRefresh` immediately after setting `LastRefreshBasis`:

```go
	status.LastRefreshReason = reason
	status.LastRefreshBasis = "recorded"
	recordGitRefreshBaseline(paths, &status)
```

Call it in `CompleteRefresh` immediately after setting `LastRefreshBasis`:

```go
	status.LastRefreshBasis = basis
	recordGitRefreshBaseline(paths, &status)
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/update -run 'Test(CompleteRefreshRecordsGitBaselineCommit|RecordRefreshRecordsGitBaselineCommitWhenGitExists|RecordRefreshDoesNotFailOutsideGitRepository)' -count=1
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add tools/project-cognition/internal/runtime/status.go tools/project-cognition/internal/update/state.go tools/project-cognition/internal/update/state_test.go
git commit -m "feat: record project cognition git refresh baseline"
```

## Task 2: Implement `internal/changes`

**Files:**
- Create: `tools/project-cognition/internal/changes/changes.go`
- Create: `tools/project-cognition/internal/changes/changes_test.go`

- [ ] **Step 1: Write failing tests for the changes package**

Create `tools/project-cognition/internal/changes/changes_test.go`:

```go
package changes

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/update"
)

func TestRunReportsWorkingTreeChangesWithRuntimePathKnowledge(t *testing.T) {
	root, paths := setupChangesRuntime(t)
	initChangesGit(t, root)

	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package main\n\nfunc main() {}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := Run(paths, Input{IncludeWorkingTree: true, IncludeUntracked: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "ok" {
		t.Fatalf("status = %q, want ok; payload=%#v", payload.Status, payload)
	}
	if payload.HeadCommit == "" || payload.BaselineCommit == "" {
		t.Fatalf("missing git commits: %#v", payload)
	}
	if payload.NextAction != "affected_closure" {
		t.Fatalf("NextAction = %q, want affected_closure; payload=%#v", payload.NextAction, payload)
	}
	got := findChange(payload.Changes, "src/app.go")
	if got == nil {
		t.Fatalf("missing src/app.go change: %#v", payload.Changes)
	}
	if !got.KnownToRuntime || got.NodeID != "N-app" {
		t.Fatalf("known runtime fields = known:%v node:%q", got.KnownToRuntime, got.NodeID)
	}
	if got.GitStatus != "M" {
		t.Fatalf("GitStatus = %q, want M", got.GitStatus)
	}
	if got.ChangeLevel != "mapped_change" {
		t.Fatalf("ChangeLevel = %q, want mapped_change", got.ChangeLevel)
	}
}

func TestRunFiltersCognitionIgnoredPaths(t *testing.T) {
	root, paths := setupChangesRuntime(t)
	initChangesGit(t, root)

	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("scratch/\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, root, "add", ".cognitionignore")
	runGit(t, root, "commit", "-m", "ignore scratch")
	if _, err := update.CompleteRefresh(paths, "map-build"); err != nil {
		t.Fatalf("CompleteRefresh after ignore commit: %v", err)
	}
	if err := os.MkdirAll(filepath.Join(root, "scratch"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "scratch", "out.log"), []byte("ignored\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := Run(paths, Input{IncludeWorkingTree: true, IncludeUntracked: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if len(payload.Changes) != 0 {
		t.Fatalf("changes = %#v, want none after ignore filter", payload.Changes)
	}
	if !containsString(payload.IgnoredPaths, "scratch/out.log") {
		t.Fatalf("IgnoredPaths = %#v, want scratch/out.log", payload.IgnoredPaths)
	}
	if payload.NextAction != "no_op" {
		t.Fatalf("NextAction = %q, want no_op", payload.NextAction)
	}
}

func TestRunReportsCommitRangeChanges(t *testing.T) {
	root, paths := setupChangesRuntime(t)
	initChangesGit(t, root)
	base := gitHead(t, root)

	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package main\n\nfunc main() {}\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, root, "add", "src/app.go")
	runGit(t, root, "commit", "-m", "update app")
	head := gitHead(t, root)

	payload, err := Run(paths, Input{Since: base, Head: head, IncludeWorkingTree: false})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	got := findChange(payload.Changes, "src/app.go")
	if got == nil {
		t.Fatalf("missing src/app.go change: %#v", payload.Changes)
	}
	if got.GitStatus != "M" {
		t.Fatalf("GitStatus = %q, want M", got.GitStatus)
	}
	if !containsString(got.Sources, "committed") {
		t.Fatalf("Sources = %#v, want committed", got.Sources)
	}
	if payload.BaselineCommit != base || payload.HeadCommit != head {
		t.Fatalf("commits = base:%q head:%q, want %q..%q", payload.BaselineCommit, payload.HeadCommit, base, head)
	}
}

func TestRunMarksUnknownNewPathAsPartialRefresh(t *testing.T) {
	root, paths := setupChangesRuntime(t)
	initChangesGit(t, root)

	if err := os.WriteFile(filepath.Join(root, "src", "new.go"), []byte("package main\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	payload, err := Run(paths, Input{IncludeWorkingTree: true, IncludeUntracked: true})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	got := findChange(payload.Changes, "src/new.go")
	if got == nil {
		t.Fatalf("missing src/new.go change: %#v", payload.Changes)
	}
	if got.KnownToRuntime {
		t.Fatalf("KnownToRuntime = true, want false")
	}
	if got.ChangeLevel != "new_path" {
		t.Fatalf("ChangeLevel = %q, want new_path", got.ChangeLevel)
	}
	if payload.NextAction != "partial_refresh" {
		t.Fatalf("NextAction = %q, want partial_refresh", payload.NextAction)
	}
}

func setupChangesRuntime(t *testing.T) (string, rt.Paths) {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "src"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package main\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { _ = st.Close() })
	_, err = st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-changes",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID: "E-app", SourceKind: "source", SourcePath: "src/app.go",
			CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-app",
		}},
		Nodes: []store.NodeImport{{
			ID: "N-app", Type: "capability", Title: "App",
			Confidence: "verified", EvidenceIDs: []string{"E-app"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID: "P-app", Path: "src/app.go", NodeID: "N-app",
			Relation: "owns", Confidence: "verified", EvidenceID: "E-app",
		}},
		Aliases: []store.AliasImport{{
			ID: "ALIAS-app-title", Alias: "App", NormalizedAlias: "app",
			TargetType: "node", TargetID: "N-app", Source: "node_title",
			Confidence: "verified",
		}},
	})
	if err != nil {
		t.Fatalf("ImportGeneration: %v", err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), "GEN-changes", rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatalf("PublishRuntimeMetadata: %v", err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-changes"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatalf("WriteStatus: %v", err)
	}
	if _, err := update.CompleteRefresh(paths, "map-build"); err != nil {
		t.Fatalf("CompleteRefresh: %v", err)
	}
	return root, paths
}

func initChangesGit(t *testing.T, root string) {
	t.Helper()
	runGit(t, root, "init")
	runGit(t, root, "config", "user.email", "test@example.com")
	runGit(t, root, "config", "user.name", "Test User")
	runGit(t, root, "add", ".")
	runGit(t, root, "commit", "-m", "baseline")
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := update.CompleteRefresh(paths, "map-build"); err != nil {
		t.Fatalf("CompleteRefresh after git init: %v", err)
	}
}

func runGit(t *testing.T, root string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v failed: %v\n%s", args, err, output)
	}
	return string(output)
}

func gitHead(t *testing.T, root string) string {
	t.Helper()
	head, err := rt.GitHead(root)
	if err != nil {
		t.Fatalf("GitHead: %v", err)
	}
	return head
}

func findChange(changes []Change, path string) *Change {
	for i := range changes {
		if changes[i].Path == path {
			return &changes[i]
		}
	}
	return nil
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/changes -count=1
```

Expected: FAIL because the `changes` package and types do not exist.

- [ ] **Step 3: Implement the changes package types and entrypoint**

Create `tools/project-cognition/internal/changes/changes.go`:

```go
package changes

import (
	"context"
	"errors"
	"path/filepath"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/ignore"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

type Input struct {
	Since              string
	Head               string
	IncludeWorkingTree bool
	IncludeUntracked   bool
	ExplicitPaths      []string
	Intent             string
}

type Summary struct {
	Total   int `json:"total"`
	Included int `json:"included"`
	Ignored int `json:"ignored"`
	Known   int `json:"known"`
	Unknown int `json:"unknown"`
	Deleted int `json:"deleted"`
	Renamed int `json:"renamed"`
}

type Change struct {
	Path              string   `json:"path"`
	OldPath           string   `json:"old_path,omitempty"`
	GitStatus         string   `json:"git_status"`
	Sources           []string `json:"sources"`
	Tracked           bool     `json:"tracked"`
	WorkingTreeDirty  bool     `json:"working_tree_dirty"`
	IgnoredByCognition bool     `json:"ignored_by_cognition"`
	KnownToRuntime    bool     `json:"known_to_runtime"`
	NodeID            string   `json:"node_id,omitempty"`
	ChangeLevel       string   `json:"change_level"`
	RecommendedAction string   `json:"recommended_action"`
	Reason            []string `json:"reason"`
}

type Payload struct {
	Status           string   `json:"status"`
	Readiness        string   `json:"readiness"`
	BaselineCommit   string   `json:"baseline_commit,omitempty"`
	HeadCommit       string   `json:"head_commit,omitempty"`
	WorkingTreeDirty bool     `json:"working_tree_dirty"`
	NextAction       string   `json:"next_action"`
	Summary          Summary  `json:"summary"`
	Changes          []Change `json:"changes"`
	IgnoredPaths     []string `json:"ignored_paths"`
	UnknownPaths     []string `json:"unknown_paths"`
	Warnings         []string `json:"warnings"`
	Errors           []string `json:"errors"`
}

type accumulator struct {
	entry   rt.GitStatusEntry
	sources map[string]bool
}

type Entry struct {
	rt.GitStatusEntry
	Sources []string
}

func Run(paths rt.Paths, input Input) (Payload, error) {
	status, err := rt.ReadStatus(paths)
	if err != nil {
		if errors.Is(err, rt.ErrUnsupportedLegacy) {
			return Payload{
				Status: "blocked", Readiness: rt.UnsupportedReadiness,
				NextAction: "needs_rebuild",
				Errors: []string{"unsupported legacy project cognition runtime"},
				Warnings: []string{},
			}, nil
		}
		return Payload{}, err
	}
	payload := Payload{
		Status: "ok", Readiness: status.Readiness,
		BaselineCommit: status.LastRefreshGitCommit,
		Warnings: []string{}, Errors: []string{},
		Changes: []Change{}, IgnoredPaths: []string{}, UnknownPaths: []string{},
	}
	if !rt.GitAvailable(paths.Root) {
		payload.Status = "blocked"
		payload.NextAction = "blocked"
		payload.Errors = append(payload.Errors, "git repository unavailable")
		return payload, nil
	}
	head := strings.TrimSpace(input.Head)
	if head == "" {
		head, _ = rt.GitHead(paths.Root)
	}
	payload.HeadCommit = head
	if strings.TrimSpace(input.Since) != "" {
		payload.BaselineCommit = strings.TrimSpace(input.Since)
	}
	if payload.BaselineCommit == "" {
		payload.Warnings = append(payload.Warnings, "no refresh git baseline recorded; using working tree status only")
	}

	entries, err := collectGitEntries(paths.Root, input, payload.BaselineCommit, payload.HeadCommit)
	if err != nil {
		return Payload{}, err
	}
	matcher := ignore.Load(paths.Root)
	pathNodeIDs := loadPathNodeIDs(paths, entryPaths(entries))
	for _, entry := range entries {
		if matcher.Ignored(entry.Path) {
			payload.IgnoredPaths = append(payload.IgnoredPaths, entry.Path)
			continue
		}
		change := changeFromEntry(entry, pathNodeIDs[entry.Path])
		payload.Changes = append(payload.Changes, change)
		if !change.KnownToRuntime {
			payload.UnknownPaths = append(payload.UnknownPaths, change.Path)
		}
	}
	sortChanges(payload.Changes)
	payload.IgnoredPaths = uniqueSorted(payload.IgnoredPaths)
	payload.UnknownPaths = uniqueSorted(payload.UnknownPaths)
	payload.WorkingTreeDirty = hasWorkingTreeDirty(payload.Changes)
	payload.Summary = summarize(payload)
	payload.NextAction = nextAction(payload)
	return payload, nil
}

func collectGitEntries(root string, input Input, baselineCommit string, headCommit string) ([]Entry, error) {
	byPath := map[string]accumulator{}
	if baselineCommit != "" && headCommit != "" {
		entries, err := rt.GitDiffNameStatus(root, baselineCommit, headCommit)
		if err != nil {
			return nil, err
		}
		for _, entry := range entries {
			addEntry(byPath, entry, "committed")
		}
	}
	if input.IncludeWorkingTree || input.IncludeUntracked {
		entries, err := rt.GitStatusEntries(root)
		if err != nil {
			return nil, err
		}
		for _, entry := range entries {
			if entry.Code == "??" && !input.IncludeUntracked {
				continue
			}
			addEntry(byPath, entry, "working_tree")
		}
	}
	for _, path := range input.ExplicitPaths {
		path = normalizePath(path)
		if path == "" {
			continue
		}
			addEntry(byPath, rt.GitStatusEntry{Code: "explicit", Path: path}, "explicit")
	}
	out := make([]Entry, 0, len(byPath))
	for _, item := range byPath {
		entry := item.entry
		entry.Code = strings.TrimSpace(entry.Code)
		out = append(out, Entry{GitStatusEntry: entry, Sources: sourceList(item.sources)})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Path < out[j].Path })
	return out, nil
}

func addEntry(byPath map[string]accumulator, entry rt.GitStatusEntry, source string) {
	entry.Path = normalizePath(entry.Path)
	entry.OldPath = normalizePath(entry.OldPath)
	if entry.Path == "" {
		return
	}
	item := byPath[entry.Path]
	if item.sources == nil {
		item.sources = map[string]bool{}
		item.entry = entry
	}
	if item.entry.Code == "" || item.entry.Code == "explicit" {
		item.entry.Code = entry.Code
	}
	if item.entry.OldPath == "" {
		item.entry.OldPath = entry.OldPath
	}
	item.sources[source] = true
	byPath[entry.Path] = item
}

func sourceList(sources map[string]bool) []string {
	out := make([]string, 0, len(sources))
	for source := range sources {
		out = append(out, source)
	}
	sort.Strings(out)
	return out
}

func loadPathNodeIDs(paths rt.Paths, changed []string) map[string]string {
	out := map[string]string{}
	st, err := store.OpenExisting(paths)
	if err != nil {
		return out
	}
	defer st.Close()
	values, err := st.NodeIDsForExactPaths(context.Background(), changed)
	if err != nil {
		return out
	}
	return values
}

func entryPaths(entries []Entry) []string {
	out := make([]string, 0, len(entries))
	for _, entry := range entries {
		out = append(out, entry.Path)
	}
	return uniqueSorted(out)
}

func changeFromEntry(entry Entry, nodeID string) Change {
	level := changeLevel(entry, nodeID)
	reasons := changeReasons(entry, nodeID)
	return Change{
		Path: entry.Path, OldPath: entry.OldPath, GitStatus: entry.Code,
		Sources: append([]string{}, entry.Sources...),
		Tracked: entry.Code != "??",
		WorkingTreeDirty: containsSource(entry.Sources, "working_tree"),
		IgnoredByCognition: false,
		KnownToRuntime: nodeID != "",
		NodeID: nodeID,
		ChangeLevel: level,
		RecommendedAction: recommendedAction(level),
		Reason: reasons,
	}
}

func containsSource(sources []string, want string) bool {
	for _, source := range sources {
		if source == want {
			return true
		}
	}
	return false
}

func changeLevel(entry Entry, nodeID string) string {
	code := strings.TrimSpace(entry.Code)
	if strings.HasPrefix(code, "D") {
		return "deleted_path"
	}
	if strings.HasPrefix(code, "R") {
		return "renamed_path"
	}
	if code == "??" || strings.HasPrefix(code, "A") {
		return "new_path"
	}
	if nodeID != "" {
		return "mapped_change"
	}
	return "unknown_path"
}

func recommendedAction(level string) string {
	switch level {
	case "mapped_change", "deleted_path", "renamed_path":
		return "affected_closure"
	default:
		return "partial_refresh"
	}
}

func changeReasons(entry Entry, nodeID string) []string {
	if nodeID != "" {
		return []string{"path exists in active runtime path_index"}
	}
	if entry.Code == "??" || strings.HasPrefix(entry.Code, "A") {
		return []string{"path is not in active runtime path_index"}
	}
	return []string{"changed path lacks active runtime path_index coverage"}
}

func summarize(payload Payload) Summary {
	summary := Summary{Total: len(payload.Changes) + len(payload.IgnoredPaths), Included: len(payload.Changes), Ignored: len(payload.IgnoredPaths)}
	for _, change := range payload.Changes {
		if change.KnownToRuntime {
			summary.Known++
		} else {
			summary.Unknown++
		}
		if change.ChangeLevel == "deleted_path" {
			summary.Deleted++
		}
		if change.ChangeLevel == "renamed_path" {
			summary.Renamed++
		}
	}
	return summary
}

func nextAction(payload Payload) string {
	if payload.Status != "ok" {
		return payload.NextAction
	}
	if payload.Readiness == rt.NeedsRebuildReadiness || payload.Readiness == rt.UnsupportedReadiness {
		return "needs_rebuild"
	}
	if len(payload.Changes) == 0 {
		return "no_op"
	}
	if len(payload.UnknownPaths) > 0 {
		return "partial_refresh"
	}
	return "affected_closure"
}

func hasWorkingTreeDirty(changes []Change) bool {
	for _, change := range changes {
		if change.WorkingTreeDirty {
			return true
		}
	}
	return false
}

func sortChanges(values []Change) {
	sort.Slice(values, func(i, j int) bool { return values[i].Path < values[j].Path })
}

func uniqueSorted(values []string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, value := range values {
		value = normalizePath(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}

func normalizePath(path string) string {
	path = filepath.ToSlash(strings.TrimSpace(strings.TrimPrefix(path, "./")))
	if path == "." {
		return ""
	}
	return path
}
```

- [ ] **Step 4: Run package tests**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/changes -count=1
```

Expected: PASS.

- [ ] **Step 5: Run related store/update tests**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/store ./internal/update -count=1
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add tools/project-cognition/internal/changes/changes.go tools/project-cognition/internal/changes/changes_test.go
git commit -m "feat: add project cognition change planning"
```

## Task 3: Add `project-cognition changes` CLI

**Files:**
- Modify: `tools/project-cognition/internal/cli/cli.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Add failing CLI tests**

In `tools/project-cognition/internal/cli/cli_test.go`, add these tests near other command-level tests:

```go
func TestChangesCommandAppearsInHelp(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"--help"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	if !strings.Contains(stdout.String(), "changes") {
		t.Fatalf("help does not mention changes:\n%s", stdout.String())
	}
}

func TestChangesCommandReturnsWorkingTreeJSON(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	initCLIGit(t, root)
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package main\n\nfunc main() {}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"changes", "--format", "json"}, &stdout, &stderr, "test")
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
	if payload["next_action"] != "affected_closure" {
		t.Fatalf("next_action = %#v, payload=%#v", payload["next_action"], payload)
	}
	changes, ok := payload["changes"].([]any)
	if !ok || len(changes) != 1 {
		t.Fatalf("changes = %#v", payload["changes"])
	}
	change := changes[0].(map[string]any)
	if change["path"] != "src/app.go" {
		t.Fatalf("change = %#v", change)
	}
	if change["known_to_runtime"] != true {
		t.Fatalf("known_to_runtime = %#v", change["known_to_runtime"])
	}
}

func TestChangesCommandSupportsExplicitChangedPath(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	initCLIGit(t, root)

	var stdout, stderr bytes.Buffer
	code := Run([]string{"changes", "--changed-path", "src/app.go", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["next_action"] != "affected_closure" {
		t.Fatalf("payload = %#v", payload)
	}
}

func initCLIGit(t *testing.T, root string) {
	t.Helper()
	runCLIGit(t, root, "init")
	runCLIGit(t, root, "config", "user.email", "test@example.com")
	runCLIGit(t, root, "config", "user.name", "Test User")
	runCLIGit(t, root, "add", ".")
	runCLIGit(t, root, "commit", "-m", "baseline")
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := update.CompleteRefresh(paths, "map-build"); err != nil {
		t.Fatalf("CompleteRefresh: %v", err)
	}
}

func runCLIGit(t *testing.T, root string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	output, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v failed: %v\n%s", args, err, output)
	}
	return string(output)
}
```

If helper names collide with existing helpers, keep the existing helper and update the test calls to use it. Do not duplicate helper names.

Add this import to `tools/project-cognition/internal/cli/cli_test.go` because `initCLIGit` calls the refresh finalizer directly:

```go
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/update"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/cli -run 'TestChangesCommand' -count=1
```

Expected: FAIL with `unknown command: changes` and missing help text.

- [ ] **Step 3: Add import and dispatch**

In `tools/project-cognition/internal/cli/cli.go`, add:

```go
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/changes"
```

Add a switch case before `update`:

```go
	case "changes":
		return changesCommand(args[1:], stdout, stderr, paths)
```

Update `printHelp` command text to include `changes`:

```go
	fmt.Fprintln(w, "Commands: status, check, init-empty, generate-ignore, mark-dirty, clear-dirty, record-refresh, complete-refresh, refresh-topics, validate-scan, validate-build, build-from-scan, import-scan, rebuild-from-scan, publish-runtime-metadata, changes, update, lexicon, query, compass, expand, discover, read, doctor, rebuild, delta")
```

- [ ] **Step 4: Add `changesCommand`**

In `tools/project-cognition/internal/cli/cli.go`, place this function before `updateCommand`:

```go
func changesCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("changes", flag.ContinueOnError)
	fs.SetOutput(stderr)
	var changed stringList
	fs.Var(&changed, "changed-path", "Explicit changed path")
	fs.Var(&changed, "changed-paths", "Explicit changed path")
	since := fs.String("since", "", "Baseline commit")
	head := fs.String("head", "", "Head commit")
	includeWorkingTree := fs.Bool("include-working-tree", true, "Include working tree changes")
	includeUntracked := fs.Bool("include-untracked", true, "Include untracked paths")
	intent := fs.String("intent", "", "Agent intent")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := changes.Run(paths, changes.Input{
		Since: *since,
		Head: *head,
		IncludeWorkingTree: *includeWorkingTree,
		IncludeUntracked: *includeUntracked,
		ExplicitPaths: changed,
		Intent: *intent,
	})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}
```

- [ ] **Step 5: Run CLI tests**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/cli -run 'TestChangesCommand' -count=1
```

Expected: PASS.

- [ ] **Step 6: Run full Go test suite**

Run:

```powershell
Set-Location tools/project-cognition
go test ./... -count=1
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/cli/cli_test.go
git commit -m "feat: expose project cognition changes command"
```

## Task 4: Require `changes` in Runtime Compatibility Checks

**Files:**
- Modify: `src/specify_cli/project_cognition_runtime.py`
- Modify: `tests/test_project_cognition_runtime_install.py`

- [ ] **Step 1: Add failing Python test assertions**

In `tests/test_project_cognition_runtime_install.py`, update `test_project_cognition_required_commands_include_compass_and_expand`:

```python
def test_project_cognition_required_commands_include_compass_and_expand():
    assert "build-from-scan" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "init-empty" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "generate-ignore" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "changes" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "lexicon --mode" in project_cognition_runtime.REQUIRED_COMMANDS
    assert (
        "compass --semantic-intake-file --query-plan-file"
        in project_cognition_runtime.REQUIRED_COMMANDS
    )
    assert "expand --section" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "update --payload-file --verification" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "delta append --verification --generated-surface" in project_cognition_runtime.REQUIRED_COMMANDS
```

Add this test after `test_project_cognition_binary_support_requires_compass_and_expand`:

```python
def test_project_cognition_binary_support_requires_changes(monkeypatch, tmp_path: Path):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, generate-ignore, update, lexicon, compass, "
            "expand, delta\n"
        )
        stderr = ""

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[1:] == ["--help"]:
            return RootHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False
    assert calls == [[str(binary), "--help"]]
```

Update every successful `RootHelpResult.stdout` in the remaining binary-support tests to include `changes`:

```python
stdout = (
    "Commands: status, build-from-scan, init-empty, generate-ignore, changes, update, lexicon, compass, "
    "expand, delta\n"
)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
pytest tests/test_project_cognition_runtime_install.py -q
```

Expected: FAIL because `REQUIRED_COMMANDS` does not include `changes`.

- [ ] **Step 3: Add command requirement**

In `src/specify_cli/project_cognition_runtime.py`, update `REQUIRED_COMMANDS`:

```python
REQUIRED_COMMANDS = (
    "build-from-scan",
    "init-empty",
    "generate-ignore",
    "changes",
    "lexicon --mode",
    "compass --semantic-intake-file --query-plan-file",
    "expand --section",
    "update --payload-file --verification",
    "delta append --verification --generated-surface",
)
```

No subcommand flag probe is needed for `changes` in this phase because root help presence is sufficient. Add a dedicated `changes --help` probe only if a future phase requires a mandatory flag such as `--since`.

- [ ] **Step 4: Run tests**

Run:

```powershell
pytest tests/test_project_cognition_runtime_install.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/specify_cli/project_cognition_runtime.py tests/test_project_cognition_runtime_install.py
git commit -m "feat: require project cognition changes support"
```

## Task 5: Wire `sp-map-update` to `changes`

**Files:**
- Modify: `templates/commands/map-update.md`
- Modify: `tests/test_map_scan_build_template_guidance.py`

- [ ] **Step 1: Add failing template assertions**

In `tests/test_map_scan_build_template_guidance.py`, add this test near existing map-update tests:

```python
def test_map_update_template_uses_git_native_changes_and_finalizers() -> None:
    content = _read("templates/commands/map-update.md")
    lowered = content.lower()

    assert "project-cognition changes --format json" in content
    assert "consume `next_action`" in lowered
    assert "feed `changes[].path`" in lowered
    assert "use the returned `result_state`" in lowered
    assert "must not call `complete-refresh` when `result_state` is `partial_refresh`" in lowered
    assert "project-cognition complete-refresh --format json" in content
    assert "project-cognition record-refresh --reason \"map-update\" --format json" in content
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py::test_map_update_template_uses_git_native_changes_and_finalizers -q
```

Expected: FAIL because the template does not call `changes`.

- [ ] **Step 3: Update Git Delta Intake wording**

In `templates/commands/map-update.md`, replace the first two bullets under `## Git Delta Intake` with:

```markdown
- Start from Git, not memory: first run `{{specify-subcmd:project-cognition changes --format json}}` unless the caller supplied a narrower explicit changed-path list or commit range. For explicit paths, pass each path with `--changed-path`; for a commit range, pass `--since <base> --head <head>`.
- Consume `next_action`, `changes[].path`, `ignored_paths`, `unknown_paths`, `baseline_commit`, and `head_commit` from the `changes` payload before querying or patching the runtime. Feed `changes[].path` into the update payload's `changed_paths`; keep `ignored_paths` out of update records, known unknowns, `minimal_live_reads`, graph evidence, and route indexes.
- Filter changed paths through `.cognitionignore` before querying or patching the runtime. The `changes` helper performs the first filter pass; if the agent adds user-supplied paths later, re-check root `.cognitionignore` and `.specify/project-cognition/.cognitionignore`. Both use gitignore-compatible syntax.
```

- [ ] **Step 4: Tighten result-state finalizer wording**

In `templates/commands/map-update.md`, under the existing `project-cognition update --payload-file ...` block, replace the sentence beginning `Use the returned` with:

```markdown
Use the returned `result_state` as the completion gate, not `status=ok` alone. `ready` plus passing `validate-build` may call `complete-refresh`; `no_op` may call `record-refresh` when only freshness metadata needs to be updated; `partial_refresh` must preserve review data and must not call `complete-refresh`; `needs_rebuild` must route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; `blocked` must report the blocker and recovery condition.
```

Add this bullet near the existing complete-refresh bullets:

```markdown
- `sp-map-update` must not call `complete-refresh` when `result_state` is `partial_refresh`, `needs_rebuild`, or `blocked`; those states are useful recorded outcomes, not fresh completed baselines.
```

- [ ] **Step 5: Run template test**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py::test_map_update_template_uses_git_native_changes_and_finalizers -q
```

Expected: PASS.

- [ ] **Step 6: Run full template guidance test file**

Run:

```powershell
pytest tests/test_map_scan_build_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add templates/commands/map-update.md tests/test_map_scan_build_template_guidance.py
git commit -m "docs: route map update through git-native changes"
```

## Task 6: Update Docs and Handbook Contract Surfaces

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_runtime_handbook_contract.py`

- [ ] **Step 1: Locate project-cognition command lists**

Run:

```powershell
rg -n "project-cognition|build-from-scan|generate-ignore|delta append|complete-refresh|record-refresh" README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_runtime_handbook_contract.py
```

Expected: output identifies the exact command-list sections to edit. Only edit sections that already enumerate runtime commands or generated workflow expectations.

- [ ] **Step 2: Add failing docs contract assertion**

If `tests/test_runtime_handbook_contract.py` already has a command-list assertion, add `changes` to that assertion. If it does not, add this focused test:

```python
def test_runtime_handbook_mentions_changes_command() -> None:
    for path in [
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
    ]:
        content = Path(path).read_text(encoding="utf-8")
        assert "project-cognition changes" in content
```

Ensure `Path` is imported:

```python
from pathlib import Path
```

- [ ] **Step 3: Run docs contract test to verify failure**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py -q
```

Expected: FAIL until docs mention the new command where command lists exist.

- [ ] **Step 4: Update command-list docs**

In every existing command-list section located in Step 1, add a concise entry:

```markdown
- `project-cognition changes --format json` - Git-native change plan for `sp-map-update`; reports included, ignored, known, unknown, and recommended next action before incremental update recording.
```

If `README.md` has no project-cognition command list, do not create one. Add the command only if the nearby docs already enumerate peer commands such as `status`, `build-from-scan`, `update`, or `delta`.

- [ ] **Step 5: Run docs contract tests**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_runtime_handbook_contract.py
git commit -m "docs: document project cognition changes command"
```

## Task 7: End-to-End Verification

**Files:**
- No planned source edits. Fix only failures caused by this implementation.

- [ ] **Step 1: Run full Go runtime tests**

Run:

```powershell
Set-Location tools/project-cognition
go test ./... -count=1
```

Expected: PASS.

- [ ] **Step 2: Run focused Python regression tests**

Run:

```powershell
Set-Location F:\github\spec-kit-plus
pytest tests/test_project_cognition_runtime_install.py tests/test_map_scan_build_template_guidance.py tests/test_runtime_handbook_contract.py -q
```

Expected: PASS.

- [ ] **Step 3: Run whitespace check on branch changes**

Run:

```powershell
git show --check --stat --oneline HEAD
```

Expected: no whitespace warnings. If this plan is implemented as several commits, run `git show --check --stat --oneline HEAD` after each commit and `git diff --check HEAD~6..HEAD` before final review.

- [ ] **Step 4: Review final diff against approved design**

Run:

```powershell
git diff --stat HEAD~6..HEAD
git diff -- docs/superpowers/specs/2026-06-22-agent-native-project-cognition-design.md tools/project-cognition src/specify_cli templates/commands/map-update.md tests README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md
```

Expected:
- Runtime has a new `changes` command.
- `changes` uses Git and `.cognitionignore`.
- Refresh finalizers record Git baseline metadata.
- `sp-map-update` starts from `changes`.
- Completion is gated by `result_state`, `validate-build`, and finalizers.
- Runtime installer rejects binaries that lack `changes`.

- [ ] **Step 5: Final commit if fixes were needed**

If Step 1 or Step 2 required follow-up fixes, commit only those files:

```powershell
git add tools/project-cognition/internal/changes/changes.go tools/project-cognition/internal/changes/changes_test.go tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/cli/cli_test.go tools/project-cognition/internal/runtime/status.go tools/project-cognition/internal/update/state.go tools/project-cognition/internal/update/state_test.go src/specify_cli/project_cognition_runtime.py tests/test_project_cognition_runtime_install.py templates/commands/map-update.md tests/test_map_scan_build_template_guidance.py README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_runtime_handbook_contract.py
git commit -m "test: cover git-native project cognition changes"
```

If no fixes were needed, do not create an empty commit.

## Implementation Notes

- Keep `.cognitionignore` a hard exclusion for `changes`: ignored paths belong only in `ignored_paths`, not `changes`, `unknown_paths`, update records, minimal reads, or graph indexes.
- Do not make `changes` perform closure expansion. It should tell the agent what changed and whether paths are known to the active runtime. Existing `update`, `query`, `compass`, and future packetization own closure expansion.
- Do not fail `RecordRefresh` or `CompleteRefresh` outside Git. Generated projects may exist before first commit, and runtime status should remain usable.
- Preserve backward compatibility for existing status files by using `omitempty` fields and not changing `RuntimeSchema` for this metadata-only addition.
- Task 2's `changes.go` code carries source labels from the accumulator into each `Change.Sources`; keep that behavior intact when simplifying or refactoring.

## Self-Review

- Spec coverage: This plan covers the approved design's first runtime slice: Git-aware update detection, `.cognitionignore` hard boundary, update-style `result_state` gate, refresh finalizers, and runtime compatibility checks. The broader inventory, extraction, packetization, and normalization commands are explicitly deferred.
- Placeholder scan: No placeholder markers or unspecified test steps remain. Every code-changing task names files, code, commands, and expected results.
- Type consistency: `LastRefreshGitCommit`, `LastRefreshGitBranch`, `Input`, `Payload`, `Change`, `Summary`, `Run`, and `changesCommand` are consistently named across tests, implementation, and CLI wiring.

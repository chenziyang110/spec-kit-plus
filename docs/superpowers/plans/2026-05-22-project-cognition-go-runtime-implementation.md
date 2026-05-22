# Project Cognition Go Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Python `project-cognition` runtime/helper implementation with a standalone Go `project-cognition` executable while preserving `sp-map-scan`, `sp-map-build`, and `sp-map-update` prompt semantics.

**Architecture:** Add an independent Go module at `tools/project-cognition/` that owns `.specify/project-cognition/` runtime state, JSON command contracts, validation, query, lexicon, update, reference discovery, and release artifacts. Keep Python responsible for template generation and install packaging only: render `{{specify-subcmd:project-cognition ...}}` to direct `project-cognition ...`, retarget generated helper scripts to the binary, remove Python runtime subcommands, and update docs/tests for the hard switch.

**Tech Stack:** Go 1.21, SQLite via Go `database/sql` and `modernc.org/sqlite`, Python 3.11+ Typer CLI for remaining `specify` surfaces, pytest, bash, PowerShell, GitHub Actions.

---

## Reference Spec

- `docs/superpowers/specs/2026-05-22-project-cognition-go-runtime-design.md`

## Scope Notes

- This is a breaking runtime switch. Existing Python-era `.specify/project-cognition/` runtime state is rejected, not migrated.
- Prompt-owned scan/build workbench artifacts remain stable: evidence, provisional, coverage, map-state, coverage ledger, scan packets, repository universe, capability/control ledgers, and worker results.
- `project-map` alias compatibility is removed from the runtime path.
- `specify cognition discover/read` move to `project-cognition discover/read`.
- The upstream `simplify-sp-specify` changes pulled on 2026-05-22 do not change the Go runtime design, but docs/tests touched by that work must be included in the final documentation sweep.

## File Structure

Create the Go runtime:

- `tools/project-cognition/go.mod`: independent Go module, matching the `tools/spec-lint/` pattern.
- `tools/project-cognition/main.go`: executable entrypoint with version injection and top-level dispatch.
- `tools/project-cognition/internal/cli/cli.go`: argument parsing, command routing, format handling, exit code mapping.
- `tools/project-cognition/internal/runtime/paths.go`: project root discovery and `.specify/project-cognition/` path helpers.
- `tools/project-cognition/internal/runtime/status.go`: Go-owned status model, runtime marker, JSON read/write, unsupported legacy detection.
- `tools/project-cognition/internal/runtime/git.go`: git baseline and changed-path discovery for `update`.
- `tools/project-cognition/internal/ignore/ignore.go`: `.cognitionignore` loading and path filtering.
- `tools/project-cognition/internal/store/schema.go`: SQLite schema creation, schema marker, active generation metadata.
- `tools/project-cognition/internal/store/store.go`: database access helpers.
- `tools/project-cognition/internal/validation/scan.go`: `validate-scan` workbench artifact gate.
- `tools/project-cognition/internal/validation/build.go`: `validate-build` runtime and query smoke gate.
- `tools/project-cognition/internal/query/lexicon.go`: `lexicon` payload generation.
- `tools/project-cognition/internal/query/query.go`: `query` payload generation and query-plan parsing.
- `tools/project-cognition/internal/update/update.go`: `update`, dirty, refresh, and metadata state transitions.
- `tools/project-cognition/internal/reference/discover.go`: cross-project reference discovery.
- `tools/project-cognition/internal/reference/read.go`: fresh-only reference reads.
- `tools/project-cognition/install.sh`: standalone installer script.
- `tools/project-cognition/install.ps1`: Windows installer script.
- `tools/project-cognition/Makefile`: build, test, and cross-compile shortcuts.
- `tools/project-cognition/testdata/`: small valid/legacy runtime fixtures.

Modify Python integration and generated scripts:

- `src/specify_cli/launcher.py`: render `project-cognition` placeholders to direct binary invocations.
- `src/specify_cli/__init__.py`: remove runtime `project_cognition_app`, `project_map_app`, and `cognition discover/read` implementations; keep unrelated CLI surfaces intact.
- `scripts/bash/project-cognition-freshness.sh`: invoke `PROJECT_COGNITION_BIN` or `project-cognition` directly.
- `scripts/powershell/project-cognition-freshness.ps1`: invoke `PROJECT_COGNITION_BIN` or `project-cognition` directly.
- `scripts/bash/common.sh` and `scripts/powershell/common.ps1`: keep helper paths, updating comments only if they mention Specify launcher semantics.
- `pyproject.toml`: do not package the Go binary or installer scripts in the Python wheel. Keep Go releases external and document the `PROJECT_COGNITION_BIN`/PATH requirement.

Modify release and docs:

- `.github/workflows/release-project-cognition.yml`: build and upload `project-cognition` binaries.
- `.github/workflows/release.yml`: add release notes/install guidance for `project-cognition`.
- `README.md`, `PROJECT-HANDBOOK.md`, `docs/installation.md`, `docs/quickstart.md`, `templates/project-handbook-template.md`: replace launcher-backed/legacy alias guidance with direct binary guidance.

Modify tests:

- Add Go tests under `tools/project-cognition/internal/**`.
- Add Python integration tests for placeholder rendering, helper scripts, removed runtime aliases, and generated docs.
- Update existing project cognition/map tests that currently assert Python command behavior.

---

### Task 1: Add Go CLI Skeleton And Runtime Format Marker

**Files:**
- Create: `tools/project-cognition/go.mod`
- Create: `tools/project-cognition/main.go`
- Create: `tools/project-cognition/internal/cli/cli.go`
- Create: `tools/project-cognition/internal/runtime/paths.go`
- Create: `tools/project-cognition/internal/runtime/status.go`
- Create: `tools/project-cognition/internal/runtime/status_test.go`
- Create: `tools/project-cognition/Makefile`

- [ ] **Step 1: Create the Go module**

Create `tools/project-cognition/go.mod`:

```go
module github.com/chenziyang110/spec-kit-plus/tools/project-cognition

go 1.21
```

- [ ] **Step 2: Add the executable entrypoint**

Create `tools/project-cognition/main.go`:

```go
package main

import (
	"os"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/cli"
)

var version = "dev"

func main() {
	os.Exit(cli.Run(os.Args[1:], os.Stdout, os.Stderr, version))
}
```

- [ ] **Step 3: Add runtime path helpers**

Create `tools/project-cognition/internal/runtime/paths.go`:

```go
package runtime

import (
	"os"
	"path/filepath"
)

const (
	SpecifyDir     = ".specify"
	CognitionDir   = "project-cognition"
	StatusFileName = "status.json"
	DBFileName     = "project-cognition.db"
)

type Paths struct {
	Root         string
	RuntimeDir   string
	StatusPath   string
	DatabasePath string
}

func ResolvePaths(start string) (Paths, error) {
	root, err := FindProjectRoot(start)
	if err != nil {
		return Paths{}, err
	}
	dir := filepath.Join(root, SpecifyDir, CognitionDir)
	return Paths{
		Root:         root,
		RuntimeDir:   dir,
		StatusPath:   filepath.Join(dir, StatusFileName),
		DatabasePath: filepath.Join(dir, DBFileName),
	}, nil
}

func FindProjectRoot(start string) (string, error) {
	if start == "" {
		start = "."
	}
	abs, err := filepath.Abs(start)
	if err != nil {
		return "", err
	}
	info, err := os.Stat(abs)
	if err == nil && !info.IsDir() {
		abs = filepath.Dir(abs)
	}
	for {
		if _, err := os.Stat(filepath.Join(abs, SpecifyDir)); err == nil {
			return abs, nil
		}
		parent := filepath.Dir(abs)
		if parent == abs {
			return filepath.Abs(start)
		}
		abs = parent
	}
}
```

- [ ] **Step 4: Add status model and legacy detection**

Create `tools/project-cognition/internal/runtime/status.go`:

```go
package runtime

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

const (
	RuntimeFormat       = "project-cognition-go"
	RuntimeSchema       = 1
	ErrLegacyCode       = "unsupported_legacy_runtime"
	MissingFreshness    = "missing"
	ReadyFreshness      = "fresh"
	BlockedReadiness    = "blocked"
	UnsupportedReadiness = "unsupported_runtime"
)

var ErrUnsupportedLegacy = errors.New("unsupported legacy project cognition runtime")

type Status struct {
	RuntimeFormat                 string   `json:"runtime_format"`
	RuntimeSchema                 int      `json:"runtime_schema"`
	Status                        string   `json:"status"`
	Freshness                     string   `json:"freshness"`
	Readiness                     string   `json:"readiness"`
	RecommendedNextAction         string   `json:"recommended_next_action"`
	StatusPath                    string   `json:"status_path"`
	GraphStorePath                string   `json:"graph_store_path"`
	Dirty                         bool     `json:"dirty"`
	DirtyReasons                  []string `json:"dirty_reasons"`
	DirtyOriginCommand            string   `json:"dirty_origin_command"`
	DirtyOriginFeatureDir         string   `json:"dirty_origin_feature_dir"`
	DirtyOriginLaneID             string   `json:"dirty_origin_lane_id"`
	DirtyScopePaths               []string `json:"dirty_scope_paths"`
	StalePaths                    []string `json:"stale_paths"`
	StaleReasons                  []string `json:"stale_reasons"`
	LastRefreshReason             string   `json:"last_refresh_reason"`
	LastRefreshBasis              string   `json:"last_refresh_basis"`
	LastRefreshChangedFilesBasis  []string `json:"last_refresh_changed_files_basis"`
	LastUpdateID                  string   `json:"last_update_id"`
	UpdatedAt                     string   `json:"updated_at"`
}

type ErrorPayload struct {
	Status                string   `json:"status"`
	Readiness             string   `json:"readiness"`
	ErrorCode             string   `json:"error_code"`
	RecommendedNextAction string   `json:"recommended_next_action"`
	Errors                []string `json:"errors"`
	StatusPath            string   `json:"status_path,omitempty"`
}

func DefaultStatus(paths Paths) Status {
	return Status{
		RuntimeFormat:         RuntimeFormat,
		RuntimeSchema:         RuntimeSchema,
		Status:                "missing",
		Freshness:             MissingFreshness,
		Readiness:             "needs_rebuild",
		RecommendedNextAction: "run_map_scan_build",
		StatusPath:            filepath.ToSlash(paths.StatusPath),
		GraphStorePath:        ".specify/project-cognition/project-cognition.db",
		DirtyReasons:          []string{},
		DirtyScopePaths:       []string{},
		StalePaths:            []string{},
		StaleReasons:          []string{},
		LastRefreshChangedFilesBasis: []string{},
		UpdatedAt:             time.Now().UTC().Format(time.RFC3339),
	}
}

func ReadStatus(paths Paths) (Status, error) {
	data, err := os.ReadFile(paths.StatusPath)
	if errors.Is(err, os.ErrNotExist) {
		return DefaultStatus(paths), nil
	}
	if err != nil {
		return Status{}, fmt.Errorf("read status: %w", err)
	}
	var raw map[string]any
	if err := json.Unmarshal(data, &raw); err != nil {
		return Status{}, fmt.Errorf("parse status: %w", err)
	}
	if raw["runtime_format"] != RuntimeFormat {
		return Status{}, ErrUnsupportedLegacy
	}
	var status Status
	if err := json.Unmarshal(data, &status); err != nil {
		return Status{}, fmt.Errorf("decode status: %w", err)
	}
	return status, nil
}

func WriteStatus(paths Paths, status Status) error {
	status.RuntimeFormat = RuntimeFormat
	status.RuntimeSchema = RuntimeSchema
	status.StatusPath = filepath.ToSlash(paths.StatusPath)
	status.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
	if err := os.MkdirAll(paths.RuntimeDir, 0o755); err != nil {
		return fmt.Errorf("create runtime dir: %w", err)
	}
	data, err := json.MarshalIndent(status, "", "  ")
	if err != nil {
		return fmt.Errorf("encode status: %w", err)
	}
	return os.WriteFile(paths.StatusPath, append(data, '\n'), 0o644)
}

func UnsupportedLegacyPayload(paths Paths) ErrorPayload {
	return ErrorPayload{
		Status:                "blocked",
		Readiness:             UnsupportedReadiness,
		ErrorCode:             ErrLegacyCode,
		RecommendedNextAction: "run_map_scan_build",
		Errors:                []string{"existing .specify/project-cognition runtime is not a Go project-cognition runtime; remove or archive it and run sp-map-scan followed by sp-map-build"},
		StatusPath:            filepath.ToSlash(paths.StatusPath),
	}
}
```

- [ ] **Step 5: Add CLI routing for help, status, check, doctor, rebuild**

Create `tools/project-cognition/internal/cli/cli.go`:

```go
package cli

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

func Run(args []string, stdout io.Writer, stderr io.Writer, version string) int {
	if len(args) == 0 || args[0] == "--help" || args[0] == "-h" {
		printHelp(stdout, version)
		return 0
	}
	if args[0] == "--version" || args[0] == "version" {
		fmt.Fprintln(stdout, version)
		return 0
	}

	paths, err := rt.ResolvePaths(".")
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}

	switch args[0] {
	case "status", "check", "doctor":
		return statusCommand(args[1:], stdout, stderr, paths)
	case "rebuild":
		fmt.Fprintln(stdout, "Run /sp-map-scan, then /sp-map-build to rebuild project cognition.")
		return 0
	default:
		fmt.Fprintf(stderr, "unknown command: %s\n", args[0])
		return 2
	}
}

func printHelp(w io.Writer, version string) {
	fmt.Fprintf(w, "project-cognition %s\n\n", version)
	fmt.Fprintln(w, "Usage: project-cognition <command> [options]")
	fmt.Fprintln(w, "Commands: status, check, doctor, rebuild")
}

func statusCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("status", flag.ContinueOnError)
	fs.SetOutput(stderr)
	format := fs.String("format", "json", "Output format: json or text")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	status, err := rt.ReadStatus(paths)
	if errors.Is(err, rt.ErrUnsupportedLegacy) {
		return writeJSON(stdout, rt.UnsupportedLegacyPayload(paths))
	}
	if err != nil {
		fmt.Fprintf(stderr, "project-cognition: %v\n", err)
		return 1
	}
	if *format != "json" {
		fmt.Fprintf(stdout, "%s %s\n", status.Freshness, status.Readiness)
		return 0
	}
	return writeJSON(stdout, status)
}

func writeJSON(w io.Writer, payload any) int {
	encoder := json.NewEncoder(w)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(payload); err != nil {
		fmt.Fprintf(os.Stderr, "project-cognition: encode json: %v\n", err)
		return 1
	}
	return 0
}
```

- [ ] **Step 6: Add status tests**

Create `tools/project-cognition/internal/runtime/status_test.go`:

```go
package runtime

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestReadStatusReturnsDefaultWhenMissing(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	status, err := ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.RuntimeFormat != RuntimeFormat {
		t.Fatalf("RuntimeFormat = %q", status.RuntimeFormat)
	}
	if status.Readiness != "needs_rebuild" {
		t.Fatalf("Readiness = %q", status.Readiness)
	}
}

func TestReadStatusRejectsLegacyRuntime(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	legacy := map[string]any{"freshness": "fresh", "graph_ready": true}
	data, _ := json.Marshal(legacy)
	if err := os.WriteFile(filepath.Join(dir, "status.json"), data, 0o644); err != nil {
		t.Fatal(err)
	}
	paths, err := ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	_, err = ReadStatus(paths)
	if !errors.Is(err, ErrUnsupportedLegacy) {
		t.Fatalf("expected ErrUnsupportedLegacy, got %v", err)
	}
}
```

- [ ] **Step 7: Add Makefile**

Create `tools/project-cognition/Makefile`:

```makefile
.PHONY: test build vet fmt

test:
	go test ./...

build:
	go build -o bin/project-cognition .

vet:
	go vet ./...

fmt:
	gofmt -w .
```

- [ ] **Step 8: Verify Go skeleton**

Run:

```powershell
cd tools/project-cognition
go test ./...
go vet ./...
go build -o bin/project-cognition.exe .
```

Expected: all commands pass and `bin/project-cognition.exe` exists on Windows.

- [ ] **Step 9: Commit**

```powershell
git add tools/project-cognition
git commit -m "feat: add project cognition go cli skeleton"
```

### Task 2: Implement Runtime State Commands

**Files:**
- Modify: `tools/project-cognition/internal/cli/cli.go`
- Modify: `tools/project-cognition/internal/runtime/status.go`
- Create: `tools/project-cognition/internal/update/state.go`
- Create: `tools/project-cognition/internal/update/state_test.go`

- [ ] **Step 1: Add tests for dirty and refresh transitions**

Create `tools/project-cognition/internal/update/state_test.go` with tests covering:

```go
package update

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

func TestMarkDirtyPreservesOriginMetadata(t *testing.T) {
	paths := testPaths(t)
	status, err := MarkDirty(paths, DirtyInput{
		Reason: "workflow contract changed",
		OriginCommand: "implement",
		OriginFeatureDir: ".specify/features/001-demo",
		OriginLaneID: "lane-1",
		ScopePaths: []string{"src/auth/login.ts"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if !status.Dirty {
		t.Fatal("expected dirty status")
	}
	if status.DirtyOriginCommand != "implement" {
		t.Fatalf("origin command = %q", status.DirtyOriginCommand)
	}
	if got := status.DirtyScopePaths; len(got) != 1 || got[0] != "src/auth/login.ts" {
		t.Fatalf("scope paths = %#v", got)
	}
}

func TestCompleteRefreshClearsDirtyState(t *testing.T) {
	paths := testPaths(t)
	if _, err := MarkDirty(paths, DirtyInput{Reason: "manual"}); err != nil {
		t.Fatal(err)
	}
	status, err := CompleteRefresh(paths, "map-build")
	if err != nil {
		t.Fatal(err)
	}
	if status.Dirty {
		t.Fatal("dirty should be false")
	}
	if status.Freshness != rt.ReadyFreshness {
		t.Fatalf("freshness = %q", status.Freshness)
	}
}
```

- [ ] **Step 2: Implement state transitions**

Create `tools/project-cognition/internal/update/state.go`:

```go
package update

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

type DirtyInput struct {
	Reason           string
	OriginCommand    string
	OriginFeatureDir string
	OriginLaneID     string
	ScopePaths       []string
}

func MarkDirty(paths rt.Paths, input DirtyInput) (rt.Status, error) {
	if input.Reason == "" {
		return rt.Status{}, fmt.Errorf("dirty reason is required")
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return rt.Status{}, err
	}
	status.Dirty = true
	status.Freshness = "stale"
	status.Readiness = "blocked"
	status.RecommendedNextAction = "run_map_update"
	status.DirtyReasons = appendUnique(status.DirtyReasons, input.Reason)
	status.DirtyOriginCommand = input.OriginCommand
	status.DirtyOriginFeatureDir = input.OriginFeatureDir
	status.DirtyOriginLaneID = input.OriginLaneID
	status.DirtyScopePaths = appendUnique(status.DirtyScopePaths, input.ScopePaths...)
	return status, rt.WriteStatus(paths, status)
}

func ClearDirty(paths rt.Paths) (rt.Status, error) {
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return rt.Status{}, err
	}
	status.Dirty = false
	status.DirtyReasons = []string{}
	status.DirtyOriginCommand = ""
	status.DirtyOriginFeatureDir = ""
	status.DirtyOriginLaneID = ""
	status.DirtyScopePaths = []string{}
	return status, rt.WriteStatus(paths, status)
}

func RecordRefresh(paths rt.Paths, reason string, changed []string) (rt.Status, error) {
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return rt.Status{}, err
	}
	status.LastRefreshReason = defaultString(reason, "manual")
	status.LastRefreshBasis = status.LastRefreshReason
	status.LastRefreshChangedFilesBasis = appendUnique(nil, changed...)
	return status, rt.WriteStatus(paths, status)
}

func CompleteRefresh(paths rt.Paths, reason string) (rt.Status, error) {
	status, err := RecordRefresh(paths, defaultString(reason, "map-build"), nil)
	if err != nil {
		return rt.Status{}, err
	}
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = "ready"
	status.RecommendedNextAction = "retry_current_workflow"
	status.Dirty = false
	status.DirtyReasons = []string{}
	status.DirtyScopePaths = []string{}
	status.StalePaths = []string{}
	status.StaleReasons = []string{}
	return status, rt.WriteStatus(paths, status)
}

func ScopePathsFromPacket(path string) ([]string, error) {
	if path == "" {
		return nil, nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(data, &payload); err != nil {
		return nil, err
	}
	var paths []string
	collectStringList(payload, []string{"scope", "write_scope"}, &paths)
	collectStringList(payload, []string{"scope", "read_scope"}, &paths)
	return appendUnique(nil, paths...), nil
}

func collectStringList(payload map[string]any, keys []string, out *[]string) {
	var current any = payload
	for _, key := range keys {
		obj, ok := current.(map[string]any)
		if !ok {
			return
		}
		current = obj[key]
	}
	items, ok := current.([]any)
	if !ok {
		return
	}
	for _, item := range items {
		if value, ok := item.(string); ok && value != "" {
			*out = append(*out, value)
		}
	}
}

func appendUnique(base []string, values ...string) []string {
	seen := map[string]bool{}
	var result []string
	for _, value := range append(base, values...) {
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		result = append(result, value)
	}
	sort.Strings(result)
	return result
}

func defaultString(value string, fallback string) string {
	if value == "" {
		return fallback
	}
	return value
}
```

- [ ] **Step 3: Wire commands into CLI**

Update `tools/project-cognition/internal/cli/cli.go` to route:

- `mark-dirty`
- `clear-dirty`
- `record-refresh`
- `complete-refresh`
- `refresh-topics`

Use `flag.FlagSet` for each command. For `mark-dirty`, accept a positional reason and `--reason`, `--origin-command`, `--origin-feature-dir`, `--origin-lane-id`, and `--packet-file`.

- [ ] **Step 4: Verify state commands**

Run:

```powershell
cd tools/project-cognition
go test ./...
go build -o bin/project-cognition.exe .
New-Item -ItemType Directory -Force tmp-proj/.specify | Out-Null
Push-Location tmp-proj
../bin/project-cognition.exe mark-dirty --reason "workflow contract changed" --origin-command implement --format json
../bin/project-cognition.exe status --format json
Pop-Location
```

Expected: JSON includes `dirty=true`, the dirty reason, and `dirty_origin_command="implement"`.

- [ ] **Step 5: Commit**

```powershell
git add tools/project-cognition
git commit -m "feat: implement project cognition state commands"
```

### Task 3: Implement SQLite Store And Validation Gates

**Files:**
- Modify: `tools/project-cognition/go.mod`
- Create: `tools/project-cognition/internal/store/schema.go`
- Create: `tools/project-cognition/internal/store/store.go`
- Create: `tools/project-cognition/internal/store/schema_test.go`
- Create: `tools/project-cognition/internal/validation/scan.go`
- Create: `tools/project-cognition/internal/validation/build.go`
- Create: `tools/project-cognition/internal/validation/validation_test.go`
- Modify: `tools/project-cognition/internal/cli/cli.go`

- [ ] **Step 1: Add SQLite dependency**

Use `modernc.org/sqlite` so release builds stay pure Go and keep `CGO_ENABLED=0`:

```powershell
cd tools/project-cognition
go get modernc.org/sqlite
go mod tidy
```

If `modernc.org/sqlite` cannot build in this repository, stop and revise this plan before implementation continues. Do not switch to CGO or a different SQLite driver inside the implementation task.

- [ ] **Step 2: Add store schema tests**

Create tests that assert:

- `Ensure` creates `.specify/project-cognition/project-cognition.db`.
- required tables exist: `metadata`, `generations`, `nodes`, `edges`, `claims`, `path_index`, `alias_index`, `updates`.
- metadata includes `runtime_format=project-cognition-go` and `runtime_schema=1`.

- [ ] **Step 3: Implement `internal/store`**

Implement:

```go
func Ensure(paths runtime.Paths) (*sql.DB, error)
func Open(paths runtime.Paths) (*sql.DB, error)
func RequiredTables() []string
func ActiveGenerationID(db *sql.DB) (string, error)
func PublishRuntimeMetadata(paths runtime.Paths) (map[string]any, error)
```

Use `database/sql`, wrap errors with command context, and keep SQL schema in one file.

- [ ] **Step 4: Add validation test fixtures**

Under `tools/project-cognition/testdata/`, create:

- `scan-ready/.specify/project-cognition/...` with minimal required workbench JSON.
- `legacy-runtime/.specify/project-cognition/status.json` without `runtime_format`.
- `build-ready/.specify/project-cognition/project-cognition.db` generated by test setup. Do not commit binary DB fixtures.

- [ ] **Step 5: Implement `validate-scan`**

`validate-scan --format json` must check the stable prompt-owned workbench artifacts:

- `status.json` exists or can be treated as missing baseline for scan stage.
- `evidence/` exists and has at least one file.
- `provisional/nodes.json`, `provisional/edges.json`, `provisional/observations.json`, and `coverage.json` are valid JSON objects.
- `coverage.json.rows` is a non-empty array.
- `workbench/coverage-ledger.json` is a valid JSON object.
- `workbench/scan-packets/` has at least one file.
- `.specify/**` and `.cognitionignore`-excluded paths are rejected from graph evidence fields.

Return the contract:

```json
{
  "status": "ok",
  "gate": "scan_acceptance",
  "readiness": "scan_ready",
  "errors": [],
  "warnings": [],
  "checked_paths": [],
  "details": {}
}
```

- [ ] **Step 6: Implement `validate-build` and `publish-runtime-metadata`**

`validate-build --format json` must:

- reject unsupported legacy status.
- verify DB exists and opens.
- verify required tables.
- verify active generation exists when query-ready.
- smoke `lexicon` and `query` contracts enough to prove payload fields exist.

`publish-runtime-metadata --format json` must:

- read DB metadata.
- write status fields that point to the Go runtime format.
- return `metadata`, `status_path`, and `graph_store_path`.

- [ ] **Step 7: Wire validation commands into CLI**

Add command routing for:

- `validate-scan`
- `validate-build`
- `publish-runtime-metadata`

- [ ] **Step 8: Verify validation**

Run:

```powershell
cd tools/project-cognition
go test ./...
go vet ./...
go build -o bin/project-cognition.exe .
```

Expected: all pass.

- [ ] **Step 9: Commit**

```powershell
git add tools/project-cognition
git commit -m "feat: add project cognition validation gates"
```

### Task 4: Implement Query, Lexicon, Update, Discover, And Read

**Files:**
- Create: `tools/project-cognition/internal/query/query.go`
- Create: `tools/project-cognition/internal/query/lexicon.go`
- Create: `tools/project-cognition/internal/query/query_test.go`
- Create: `tools/project-cognition/internal/update/update.go`
- Create: `tools/project-cognition/internal/ignore/ignore.go`
- Create: `tools/project-cognition/internal/reference/discover.go`
- Create: `tools/project-cognition/internal/reference/read.go`
- Create: `tools/project-cognition/internal/reference/reference_test.go`
- Modify: `tools/project-cognition/internal/cli/cli.go`

- [ ] **Step 1: Add query-plan parsing tests**

Tests must cover:

- inline valid JSON
- `--query-plan-file`
- `--query-plan @file`
- `path_hints` normalized into `paths`
- `reason` normalized into `selection_reason`
- selected and rejected concepts echoed in query payload

- [ ] **Step 2: Implement query-plan parsing**

Implement a strict JSON parser first. Also add a small targeted parser only for the current known shell-stripped shape:

```text
{selected_concepts:[capability:auth.login],rejected_concepts:[capability:legacy.login],expanded_queries:[login],path_hints:[src\auth\login.ts],reason:selected from project-cognition lexicon}
```

Do not add a broad JSON5 dependency in Go.

- [ ] **Step 3: Implement lexicon**

Return the required fields:

- `readiness`
- `recommended_next_action`
- `intent`
- `query`
- `terms`
- `available_terms`
- `concept_candidates`
- `query_planning_contract`

Use DB tables `nodes`, `alias_index`, `path_index`, and query examples if present.

- [ ] **Step 4: Implement query**

Return the required fields:

- `baseline_health`
- `query_coverage`
- `workflow_requirement`
- `path_adoption`
- `readiness`
- `recommended_next_action`
- `intent`
- `query`
- `query_plan`
- `selected_concepts`
- `rejected_concepts`
- `selection_reason`
- `capability_candidates`
- `symptom_candidates`
- `affected_nodes`
- `minimal_live_reads`
- `missing_coverage`
- `route_pack`
- `subgraph`

For the first Go runtime release, keep the route algorithm conservative: use selected concepts, path indexes, alias matches, and minimal live reads. Do not invent graph closure when the DB cannot prove it.

- [ ] **Step 5: Implement `.cognitionignore` filtering**

Implement enough gitignore-compatible behavior for project cognition:

- comments and blank lines
- directory patterns ending in `/`
- simple glob patterns
- `**`
- `!` re-includes

Use tests with root `.cognitionignore` and `.specify/project-cognition/.cognitionignore`.

- [ ] **Step 6: Implement update**

`update` must:

- accept repeated `--changed-paths` and `--scope`.
- derive changed paths from git when omitted.
- filter ignored paths.
- record update payload in DB/status.
- return `adopted_paths`, `review_paths`, `unadoptable_paths`, `known_unknowns`, `minimal_live_reads`, and `path_adoption`.

- [ ] **Step 7: Implement discover/read**

`discover --root` must find nested directories with `.specify/project-cognition/status.json` and the Go runtime marker.

`read --project --slice --include-graph` must:

- require `freshness=fresh`
- require graph readiness
- read `.specify/project-cognition/slices/<slice>.json`
- read requested graph JSON files
- return `admission`, `slice`, `graph`, `provenance`, and `minimal_read_order`

- [ ] **Step 8: Wire commands into CLI and verify**

Run:

```powershell
cd tools/project-cognition
go test ./...
go vet ./...
go build -o bin/project-cognition.exe .
```

Expected: all pass.

- [ ] **Step 9: Commit**

```powershell
git add tools/project-cognition
git commit -m "feat: implement project cognition query runtime"
```

### Task 5: Retarget Placeholder Rendering And Generated Helper Scripts

**Files:**
- Modify: `src/specify_cli/launcher.py`
- Modify: `scripts/bash/project-cognition-freshness.sh`
- Modify: `scripts/powershell/project-cognition-freshness.ps1`
- Modify: `tests/test_project_map_freshness_scripts.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add failing placeholder rendering test**

Add or update a test so:

```python
rendered = render_project_launcher_placeholders(
    tmp_path,
    "{{specify-subcmd:project-cognition validate-build --format json}}",
)
assert rendered == "project-cognition validate-build --format json"
```

Also assert a non-cognition subcommand still uses the existing Specify launcher behavior:

```python
assert "specify learning start" in render_project_launcher_placeholders(
    tmp_path,
    "{{specify-subcmd:learning start --command plan --format json}}",
)
```

- [ ] **Step 2: Update renderer**

In `src/specify_cli/launcher.py`, change `render_project_launcher_placeholders()` so the `replace()` function returns `render_command(tokens)` when `tokens[0] == "project-cognition"`, independent of `.specify/config.json`.

- [ ] **Step 3: Retarget bash helper**

In `scripts/bash/project-cognition-freshness.sh`:

- remove `CONFIG_PATH`, `python_cmd`, launcher JSON parsing, and `normalize_pythonpath_for_shell`.
- add `PROJECT_COGNITION_BIN` resolution:

```bash
project_cognition_bin() {
    if [[ -n "${PROJECT_COGNITION_BIN:-}" ]]; then
        printf '%s\n' "$PROJECT_COGNITION_BIN"
        return 0
    fi
    if command -v project-cognition >/dev/null 2>&1; then
        command -v project-cognition
        return 0
    fi
    echo "Cannot run project-cognition: set PROJECT_COGNITION_BIN or install project-cognition on PATH." >&2
    return 127
}

run_project_cognition() {
    local bin
    bin="$(project_cognition_bin)" || return $?
    (cd "$REPO_ROOT" && "$bin" "$@")
}
```

- [ ] **Step 4: Retarget PowerShell helper**

In `scripts/powershell/project-cognition-freshness.ps1`:

- remove `Get-SpecifyLauncherArgv`.
- resolve `$env:PROJECT_COGNITION_BIN` first.
- fall back to `Get-Command project-cognition`.
- call `& $projectCognition @ProjectCognitionArgs`.
- emit `Cannot run project-cognition: set PROJECT_COGNITION_BIN or install project-cognition on PATH.` when missing.

- [ ] **Step 5: Update helper script tests**

In `tests/test_project_map_freshness_scripts.py`, replace fake Specify launcher tests with fake `project-cognition` binary tests. The fake binary should assert it receives command args like `mark-dirty --reason ... --format json` without a leading `project-cognition` subcommand.

- [ ] **Step 6: Update generated integration tests**

Update integration tests that assert generated command content still references launcher-backed `project-cognition`. Expected generated text should contain direct `project-cognition ...` commands.

- [ ] **Step 7: Verify**

Run:

```powershell
pytest tests/test_project_map_freshness_scripts.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```powershell
git add src/specify_cli/launcher.py scripts/bash/project-cognition-freshness.sh scripts/powershell/project-cognition-freshness.ps1 tests
git commit -m "feat: route project cognition helpers to go binary"
```

### Task 6: Remove Python Runtime Commands And Cross-Project Python Helpers

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Create: `src/specify_cli/project_cognition_tool.py`
- Modify: `src/specify_cli/hooks/project_cognition.py`
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `src/specify_cli/hooks/preflight.py`
- Modify: `src/specify_cli/hooks/engine.py`
- Delete: `src/specify_cli/hooks/project_map.py`
- Delete: `src/specify_cli/cognition/**`
- Delete: `src/specify_cli/project_cognition_status.py`
- Delete: `src/specify_cli/project_map_status.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/test_project_cognition_*.py`
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/hooks/test_project_map_hooks.py`
- Modify: `tests/contract/test_hook_cli_surface.py`
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `tests/hooks/test_hook_engine.py`

- [ ] **Step 1: Add failing tests for removed Python runtime surfaces**

In `tests/integrations/test_cli.py`, update help tests:

```python
def test_specify_no_longer_exposes_project_cognition_runtime_commands():
    runner = CliRunner()
    result = runner.invoke(app, ["project-cognition", "--help"])
    assert result.exit_code != 0
    result = runner.invoke(app, ["project-map", "--help"])
    assert result.exit_code != 0
```

For `cognition`, assert `discover` and `read` are absent, or remove the namespace if no non-runtime commands remain.

- [ ] **Step 2: Add a thin binary invocation helper**

Create `src/specify_cli/project_cognition_tool.py`. This module may resolve and execute the external binary; it must not read or write `.specify/project-cognition/` runtime truth directly.

Required public functions:

```python
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


class ProjectCognitionToolUnavailable(RuntimeError):
    pass


class ProjectCognitionToolError(RuntimeError):
    def __init__(self, message: str, *, returncode: int, stdout: str, stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def resolve_project_cognition_bin(env: Mapping[str, str] | None = None) -> str:
    env = env or os.environ
    explicit = str(env.get("PROJECT_COGNITION_BIN") or "").strip()
    if explicit:
        return explicit
    found = shutil.which("project-cognition")
    if found:
        return found
    raise ProjectCognitionToolUnavailable(
        "Cannot run project-cognition: set PROJECT_COGNITION_BIN or install project-cognition on PATH."
    )


def run_project_cognition(project_root: Path, args: Sequence[str]) -> dict[str, Any]:
    binary = resolve_project_cognition_bin()
    completed = subprocess.run(
        [binary, *args],
        cwd=project_root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise ProjectCognitionToolError(
            completed.stderr.strip() or completed.stdout.strip() or "project-cognition failed",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ProjectCognitionToolError(
            f"project-cognition returned invalid JSON: {exc}",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        ) from exc
    if not isinstance(payload, dict):
        raise ProjectCognitionToolError(
            "project-cognition returned a non-object JSON payload",
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    return payload
```

- [ ] **Step 3: Remove Typer apps**

In `src/specify_cli/__init__.py`:

- remove `project_cognition_app` and `project_map_app` creation and registration.
- remove `@project_cognition_app` and `@project_map_app` command functions.
- remove `@cognition_app.command("discover")` and `@cognition_app.command("read")`.
- keep unrelated command descriptions for `map-scan`, `map-build`, and `map-update` workflow entrypoints.

- [ ] **Step 4: Replace hook runtime logic with binary calls**

In `src/specify_cli/hooks/project_cognition.py`:

- replace imports from `specify_cli.cognition` and `specify_cli.project_cognition_status` with `run_project_cognition`.
- `project_cognition_freshness_result()` must call `run_project_cognition(project_root, ["status", "--format", "json"])`.
- `mark_dirty_hook()` must call `run_project_cognition(project_root, ["mark-dirty", "--reason", reason, "--format", "json", ...])`, including origin fields and `--packet-file` when payload fields are present.
- `complete_refresh_hook()` must call `validate-build --format json`; when validation returns `status=ok`, call `complete-refresh --format json`; when validation fails, call `record-refresh --reason acceptance-blocked --format json` and return a blocked hook result using validation errors.
- keep the existing `project_cognition.*` hook event names.
- remove `project_map_freshness_result()`.

In `src/specify_cli/hooks/artifact_validation.py`:

- remove direct imports of `validate_scan_acceptance` and `validate_build_acceptance`.
- call `run_project_cognition(project_root, ["validate-scan", "--format", "json"])` for scan artifact checks.
- call `run_project_cognition(project_root, ["validate-build", "--format", "json"])` for build artifact checks.
- convert `ProjectCognitionToolUnavailable` into validation errors that tell the user to set `PROJECT_COGNITION_BIN` or install `project-cognition` on PATH.

In `src/specify_cli/hooks/engine.py` and `src/specify_cli/hooks/events.py`:

- remove `project_map.mark_dirty` and `project_map.complete_refresh` compatibility event registration.
- keep `project_cognition.mark_dirty` and `project_cognition.complete_refresh`.

- [ ] **Step 5: Delete Python runtime modules**

After hook/preflight imports are moved to `project_cognition_tool.py`, delete:

- `src/specify_cli/cognition/`
- `src/specify_cli/project_cognition_status.py`
- `src/specify_cli/project_map_status.py`
- `src/specify_cli/hooks/project_map.py`

Run `rg -n "specify_cli\\.cognition|project_cognition_status|project_map_status|project_map_freshness_result" src tests` and remove or rewrite every active import.

- [ ] **Step 6: Update hook/preflight tests**

Tests that currently call Python project cognition status helpers must be rewritten to use a fake `project-cognition` binary. The fake binary should read arguments and emit JSON for:

- `status --format json`
- `mark-dirty --reason ... --format json`
- `validate-scan --format json`
- `validate-build --format json`
- `record-refresh --reason acceptance-blocked --format json`
- `complete-refresh --format json`

Set `PROJECT_COGNITION_BIN` with `monkeypatch.setenv()` in tests.

- [ ] **Step 7: Verify Python CLI**

Run:

```powershell
pytest tests/integrations/test_cli.py tests/hooks/test_project_map_hooks.py tests/contract/test_hook_cli_surface.py -q
```

Expected: tests pass with Python asserting external binary invocation and removed runtime aliases.

- [ ] **Step 8: Commit**

```powershell
git add src/specify_cli tests
git commit -m "refactor: remove python project cognition runtime"
```

### Task 7: Update Documentation And Generated Guidance

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `docs/installation.md`
- Modify: `docs/quickstart.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/planning-context-loading-gradient.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_project_handbook_templates.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Replace legacy runtime guidance**

Replace all current user-facing guidance that says:

- `specify project-cognition ...`
- `specify project-map ...`
- `specify_launcher.argv` for project cognition
- `cognition discover --root`
- PATH `specify` fallback for project cognition

with:

- `project-cognition ...`
- `PROJECT_COGNITION_BIN` or PATH `project-cognition`
- `project-cognition discover --root`
- `project-cognition read --project ... --slice ...`

- [ ] **Step 2: Keep historical project-map references scoped**

Do not delete every mention of `templates/project-map/**`; those templates remain legacy compatibility/export review surfaces. Update docs/tests so `project-map` is described as historical support only, not a runtime alias.

- [ ] **Step 3: Update docs tests**

Update assertions in:

- `tests/test_specify_guidance_docs.py`
- `tests/test_project_handbook_templates.py`
- `tests/test_alignment_templates.py`

Expected assertions:

```python
assert "project-cognition validate-build --format json" in content
assert "specify project-cognition" not in content
assert "specify project-map" not in content
assert "project-cognition discover --root" in content
```

- [ ] **Step 4: Verify docs**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py tests/test_project_handbook_templates.py tests/test_alignment_templates.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add README.md PROJECT-HANDBOOK.md docs templates tests
git commit -m "docs: document standalone project cognition runtime"
```

### Task 8: Add Release Packaging And Installers

**Files:**
- Create: `.github/workflows/release-project-cognition.yml`
- Modify: `.github/workflows/release.yml`
- Create: `tools/project-cognition/install.sh`
- Create: `tools/project-cognition/install.ps1`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `docs/installation.md`
- Add or modify tests for release workflow text if present.

- [ ] **Step 1: Add installer scripts**

Model the scripts after `tools/spec-lint/install.sh` and `tools/spec-lint/install.ps1`, but install `project-cognition` binaries from release assets named:

```text
project-cognition-linux-amd64
project-cognition-linux-arm64
project-cognition-darwin-amd64
project-cognition-darwin-arm64
project-cognition-windows-amd64.exe
```

Install into `~/.specify/bin` by default and print PATH instructions.

- [ ] **Step 2: Add release workflow**

Create `.github/workflows/release-project-cognition.yml` using the `release-spec-lint.yml` pattern:

- trigger on published releases.
- setup Go 1.21.
- working directory `tools/project-cognition`.
- build targets linux/amd64, linux/arm64, darwin/amd64, darwin/arm64, windows/amd64.
- use `CGO_ENABLED=0` for every target.
- upload `tools/project-cognition/bin/*`.

- [ ] **Step 3: Update release notes**

In `.github/workflows/release.yml`, add a `project-cognition` install section:

```markdown
### project-cognition runtime

Generated project cognition workflows require the standalone `project-cognition` binary.

Linux / macOS:
curl -sSL https://raw.githubusercontent.com/chenziyang110/spec-kit-plus/main/tools/project-cognition/install.sh | bash

Windows PowerShell:
irm https://raw.githubusercontent.com/chenziyang110/spec-kit-plus/main/tools/project-cognition/install.ps1 | iex

Go users:
go install github.com/chenziyang110/spec-kit-plus/tools/project-cognition@${VERSION}
```

- [ ] **Step 4: Verify release text and Go build**

Run:

```powershell
cd tools/project-cognition
go test ./...
go build -o bin/project-cognition.exe .
cd ..\..
pytest tests/test_specify_guidance_docs.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add .github/workflows/release-project-cognition.yml .github/workflows/release.yml tools/project-cognition docs PROJECT-HANDBOOK.md tests
git commit -m "ci: release project cognition binary"
```

### Task 9: Full Regression And Cleanup

**Files:**
- No planned new file ownership. Touch only files already named in Tasks 1-8 when a regression exposes a missed contract.

- [ ] **Step 1: Run Go verification**

```powershell
cd tools/project-cognition
gofmt -w .
go test ./...
go vet ./...
go build -o bin/project-cognition.exe .
cd ..\..
```

Expected: pass.

- [ ] **Step 2: Run focused Python regressions**

```powershell
pytest tests/test_project_map_freshness_scripts.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py tests/test_specify_guidance_docs.py tests/test_project_handbook_templates.py tests/test_alignment_templates.py -q
```

Expected: pass.

- [ ] **Step 3: Run broader affected regressions**

```powershell
pytest tests/integrations/test_cli.py tests/hooks tests/contract/test_hook_cli_surface.py tests/test_project_cognition_runtime.py tests/test_project_cognition_validation.py tests/test_project_cognition_query.py -q
```

Expected: pass after Python tests assert external binary invocation and removed runtime aliases.

- [ ] **Step 4: Inspect for forbidden runtime references**

Run:

```powershell
rg -n "specify project-cognition|specify project-map|cognition discover|cognition read|specify_launcher\\.argv.*project-cognition|PATH specify" README.md PROJECT-HANDBOOK.md docs templates scripts src tests
```

Expected: no matches except historical migration notes or tests explicitly asserting removal.

- [ ] **Step 5: Review diff**

```powershell
git diff --stat
git diff --check
```

Expected: no whitespace errors; diff matches the planned runtime extraction.

- [ ] **Step 6: Final commit**

If Task 9 produced cleanup changes:

```powershell
git add .
git commit -m "test: align project cognition runtime regressions"
```

If there are no cleanup changes, skip the commit.

## Self-Review

- Spec coverage: The plan covers the Go module, hard runtime marker, preserved workflow flags, namespace move for discover/read, stable workbench artifacts, helper launcher change, Python runtime removal, docs, release packaging, and regression checks.
- Placeholder scan: No task uses TBD/TODO/fill-in placeholders; implementation tasks name concrete files, commands, expected fields, and validation commands.
- Type consistency: The plan consistently uses `project-cognition`, `PROJECT_COGNITION_BIN`, `runtime_format`, `runtime_schema`, `status_path`, `graph_store_path`, `query_plan`, `path_adoption`, and the approved command names.

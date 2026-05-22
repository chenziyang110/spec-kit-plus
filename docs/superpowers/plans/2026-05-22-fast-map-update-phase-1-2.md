# Fast Map Update Phase 1-2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1-2 foundation for fast full-fidelity project cognition updates: durable delta sessions, config-gated auto-commit policy, git boundary selection, workflow-owned path computation, and non-overclaiming update outcome labels.

**Architecture:** Keep this slice inside the Go `project-cognition` runtime. Add focused packages for config, delta sessions, and git boundary/safety logic, then expose them through new CLI subcommands and the existing `update` command. This plan intentionally stops before Phase 3 DB graph patching; Phase 1-2 outcomes may record deltas and resolve boundaries, but must not claim `ready`, `review`, `partial_refresh`, or full-fidelity graph updates.

**Tech Stack:** Go 1.21, standard library JSON/filesystem/exec packages, existing `tools/project-cognition` runtime, existing `go test ./...` verification.

---

## File Structure

- Create `tools/project-cognition/internal/config/config.go`: load `.specify/config.json` project cognition settings and environment overrides.
- Create `tools/project-cognition/internal/config/config_test.go`: verify auto-commit defaults and disable paths.
- Create `tools/project-cognition/internal/delta/delta.go`: durable delta session begin/append/load/summarize functions and JSON structs.
- Create `tools/project-cognition/internal/delta/delta_test.go`: verify session persistence, event appends, path normalization, and corrupted payload errors.
- Create `tools/project-cognition/internal/boundary/boundary.go`: git boundary selection, workflow-owned path computation, initial dirty exclusion, and Phase 1-2 outcome payloads.
- Create `tools/project-cognition/internal/boundary/boundary_test.go`: verify clean path ownership, initial dirty exclusion, intentionally claimed dirty paths, ambiguous path fallback, and env/config auto-commit disable behavior.
- Modify `tools/project-cognition/internal/runtime/git.go`: add git helpers for current branch, HEAD, status entries with status codes, diff name-status, and repository availability checks.
- Modify `tools/project-cognition/internal/runtime/status.go`: add `LastDeltaSessionID`, `LastUpdateOutcome`, and `LastUpdateBoundary` fields to status JSON.
- Modify `tools/project-cognition/internal/update/state.go`: accept delta session ids and commit ranges, call boundary resolution, and return Phase 1-2 labels without claiming graph patches.
- Modify `tools/project-cognition/internal/cli/cli.go`: add `delta begin`, `delta append`, `delta append --packet-file`, `delta status`, `update --delta-session`, and `update --commit-range` command parsing.
- Modify `tools/project-cognition/internal/cli/cli_test.go`: add CLI coverage for delta and update boundary commands.

## Phase Boundary

This implementation must ship only Phase 1-2 behavior from the spec.

Allowed outcome labels:

- `dirty`
- `recorded_delta`
- `boundary_resolved`
- `commit_created`
- `commit_skipped`

Forbidden outcome labels in this plan:

- `ready`
- `review`
- `partial_refresh`

Forbidden claims:

- Do not say graph records were patched.
- Do not mark project cognition freshness as `fresh` because a delta session or boundary was recorded.
- Do not add broad workflow template integration yet.

### Task 1: Runtime Config Loader

**Files:**
- Create: `tools/project-cognition/internal/config/config.go`
- Test: `tools/project-cognition/internal/config/config_test.go`

- [ ] **Step 1: Write failing config tests**

Create `tools/project-cognition/internal/config/config_test.go`:

```go
package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadDefaultsAutoCommitEnabled(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	cfg, err := Load(root)
	if err != nil {
		t.Fatal(err)
	}
	if !cfg.ProjectCognition.AutoCommit {
		t.Fatalf("AutoCommit = false, want true")
	}
}

func TestLoadConfigDisablesAutoCommit(t *testing.T) {
	root := t.TempDir()
	specifyDir := filepath.Join(root, ".specify")
	if err := os.Mkdir(specifyDir, 0o755); err != nil {
		t.Fatal(err)
	}
	data := []byte(`{"project_cognition":{"auto_commit":false}}`)
	if err := os.WriteFile(filepath.Join(specifyDir, "config.json"), data, 0o644); err != nil {
		t.Fatal(err)
	}
	cfg, err := Load(root)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.ProjectCognition.AutoCommit {
		t.Fatalf("AutoCommit = true, want false")
	}
}

func TestEnvironmentDisablesAutoCommit(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("SPECIFY_PROJECT_COGNITION_AUTO_COMMIT", "0")
	cfg, err := Load(root)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.ProjectCognition.AutoCommit {
		t.Fatalf("AutoCommit = true, want false")
	}
}

func TestLoadRejectsMalformedConfig(t *testing.T) {
	root := t.TempDir()
	specifyDir := filepath.Join(root, ".specify")
	if err := os.Mkdir(specifyDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(specifyDir, "config.json"), []byte(`{bad json`), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(root); err == nil {
		t.Fatal("expected malformed config error")
	}
}
```

- [ ] **Step 2: Run config tests and verify failure**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/config
```

Expected: FAIL because package `internal/config` does not exist.

- [ ] **Step 3: Implement config loader**

Create `tools/project-cognition/internal/config/config.go`:

```go
package config

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type Config struct {
	ProjectCognition ProjectCognitionConfig `json:"project_cognition"`
}

type ProjectCognitionConfig struct {
	AutoCommit bool `json:"auto_commit"`
}

type rawConfig struct {
	ProjectCognition *rawProjectCognitionConfig `json:"project_cognition"`
}

type rawProjectCognitionConfig struct {
	AutoCommit *bool `json:"auto_commit"`
}

func Load(root string) (Config, error) {
	cfg := Config{ProjectCognition: ProjectCognitionConfig{AutoCommit: true}}
	path := filepath.Join(root, ".specify", "config.json")
	data, err := os.ReadFile(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			applyEnv(&cfg)
			return cfg, nil
		}
		return Config{}, fmt.Errorf("read config: %w", err)
	}
	var raw rawConfig
	if err := json.Unmarshal(data, &raw); err != nil {
		return Config{}, fmt.Errorf("parse config: %w", err)
	}
	if raw.ProjectCognition != nil && raw.ProjectCognition.AutoCommit != nil {
		cfg.ProjectCognition.AutoCommit = *raw.ProjectCognition.AutoCommit
	}
	applyEnv(&cfg)
	return cfg, nil
}

func applyEnv(cfg *Config) {
	value := strings.TrimSpace(os.Getenv("SPECIFY_PROJECT_COGNITION_AUTO_COMMIT"))
	if value == "0" || strings.EqualFold(value, "false") || strings.EqualFold(value, "no") {
		cfg.ProjectCognition.AutoCommit = false
	}
}
```

- [ ] **Step 4: Run config tests and verify pass**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/config
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add tools/project-cognition/internal/config/config.go tools/project-cognition/internal/config/config_test.go
git commit -m "feat: add project cognition config loader"
```

Expected: commit succeeds.

### Task 2: Delta Session Storage

**Files:**
- Create: `tools/project-cognition/internal/delta/delta.go`
- Test: `tools/project-cognition/internal/delta/delta_test.go`

- [ ] **Step 1: Write failing delta tests**

Create `tools/project-cognition/internal/delta/delta_test.go`:

```go
package delta

import (
	"os"
	"path/filepath"
	"testing"
)

func TestBeginCreatesSessionWithNormalizedInitialDirtyPaths(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	session, err := Begin(BeginInput{
		Root:              root,
		RuntimeDir:        runtimeDir,
		OriginCommand:     "quick",
		OriginFeatureDir:  ".specify/features/001-demo",
		OriginLaneID:      "lane-1",
		BaseCommit:        "abc123",
		Branch:            "main",
		InitialDirtyPaths: []string{"./src/b.go", "src/a.go", "src/a.go"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if session.SessionID == "" {
		t.Fatal("SessionID is empty")
	}
	if got := session.Git.InitialDirtyPaths; len(got) != 2 || got[0] != "src/a.go" || got[1] != "src/b.go" {
		t.Fatalf("InitialDirtyPaths = %#v", got)
	}
	if _, err := os.Stat(filepath.Join(runtimeDir, "delta-sessions", session.SessionID, "session.json")); err != nil {
		t.Fatal(err)
	}
}

func TestAppendEventPersistsNormalizedPaths(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	session, err := Begin(BeginInput{Root: root, RuntimeDir: runtimeDir, OriginCommand: "quick"})
	if err != nil {
		t.Fatal(err)
	}
	event, err := Append(AppendInput{
		RuntimeDir:        runtimeDir,
		SessionID:         session.SessionID,
		EventType:         "worker_result",
		OriginCommand:     "quick",
		OriginLaneID:      "lane-1",
		Phase:             "execute",
		ChangedPaths:      []string{"./src/a.go", "src/a.go"},
		ReadPaths:         []string{"tests/a_test.go"},
		BehaviorSurfaces:  []string{"cli:update"},
		KnownUnknowns:     []string{"consumer edge not proven"},
		Verification:      []string{"go test ./... PASS"},
		GeneratedSurfaces: []string{"templates/commands/quick.md"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if event.EventID == "" {
		t.Fatal("EventID is empty")
	}
	loaded, err := Load(runtimeDir, session.SessionID)
	if err != nil {
		t.Fatal(err)
	}
	if len(loaded.Events) != 1 {
		t.Fatalf("events = %d", len(loaded.Events))
	}
	if got := loaded.Events[0].ChangedPaths; len(got) != 1 || got[0] != "src/a.go" {
		t.Fatalf("ChangedPaths = %#v", got)
	}
}

func TestAppendPacketFilePersistsEvent(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	session, err := Begin(BeginInput{Root: root, RuntimeDir: runtimeDir, OriginCommand: "quick"})
	if err != nil {
		t.Fatal(err)
	}
	packet := filepath.Join(root, "packet.json")
	data := []byte(`{"event_type":"worker_result","changed_paths":["src/a.go"],"verification_evidence":["go test ./... PASS"]}`)
	if err := os.WriteFile(packet, data, 0o644); err != nil {
		t.Fatal(err)
	}
	event, err := AppendPacketFile(runtimeDir, session.SessionID, packet)
	if err != nil {
		t.Fatal(err)
	}
	if event.EventType != "worker_result" {
		t.Fatalf("EventType = %q", event.EventType)
	}
	if got := event.ChangedPaths; len(got) != 1 || got[0] != "src/a.go" {
		t.Fatalf("ChangedPaths = %#v", got)
	}
}

func TestLoadMissingSessionFails(t *testing.T) {
	root := t.TempDir()
	runtimeDir := filepath.Join(root, ".specify", "project-cognition")
	if err := os.MkdirAll(runtimeDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(runtimeDir, "missing-session"); err == nil {
		t.Fatal("expected missing session error")
	}
}
```

- [ ] **Step 2: Run delta tests and verify failure**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/delta
```

Expected: FAIL because package `internal/delta` does not exist.

- [ ] **Step 3: Implement delta package**

Create `tools/project-cognition/internal/delta/delta.go`:

```go
package delta

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type BeginInput struct {
	Root              string
	RuntimeDir        string
	OriginCommand     string
	OriginFeatureDir  string
	OriginLaneID      string
	BaseCommit        string
	Branch            string
	InitialDirtyPaths []string
}

type AppendInput struct {
	RuntimeDir        string
	SessionID         string
	EventType         string
	OriginCommand     string
	OriginLaneID      string
	Phase             string
	ChangedPaths      []string
	ReadPaths         []string
	BehaviorSurfaces  []string
	GraphSemantics    map[string]any
	GeneratedSurfaces []string
	OwnerConsumers    []string
	KnownUnknowns     []string
	Verification      []string
	Confidence        string
}

type packetEvent struct {
	EventType         string         `json:"event_type"`
	OriginCommand     string         `json:"origin_command"`
	OriginLaneID      string         `json:"origin_lane_id"`
	Phase             string         `json:"phase"`
	ChangedPaths      []string       `json:"changed_paths"`
	ReadPaths         []string       `json:"read_paths"`
	BehaviorSurfaces  []string       `json:"behavior_surfaces"`
	GraphSemantics    map[string]any `json:"graph_semantics"`
	GeneratedSurfaces []string       `json:"generated_surface_notes"`
	OwnerConsumers    []string       `json:"owner_consumer_notes"`
	KnownUnknowns     []string       `json:"known_unknowns"`
	Verification      []string       `json:"verification_evidence"`
	Confidence        string         `json:"confidence"`
}

type Session struct {
	SessionID     string        `json:"session_id"`
	OriginCommand string        `json:"origin_command"`
	OriginContext OriginContext `json:"origin_context"`
	Git           GitContext    `json:"git"`
	CreatedAt     string        `json:"created_at"`
}

type OriginContext struct {
	FeatureDir string `json:"feature_dir,omitempty"`
	LaneID     string `json:"lane_id,omitempty"`
}

type GitContext struct {
	Available         bool     `json:"available"`
	BaseCommit        string   `json:"base_commit,omitempty"`
	Branch            string   `json:"branch,omitempty"`
	InitialDirtyPaths []string `json:"initial_dirty_paths"`
}

type Event struct {
	EventID           string         `json:"event_id"`
	SessionID         string         `json:"session_id"`
	EventType         string         `json:"event_type"`
	OriginCommand     string         `json:"origin_command,omitempty"`
	OriginLaneID      string         `json:"origin_lane_id,omitempty"`
	Phase             string         `json:"phase,omitempty"`
	ChangedPaths      []string       `json:"changed_paths"`
	ReadPaths         []string       `json:"read_paths"`
	BehaviorSurfaces  []string       `json:"behavior_surfaces"`
	GraphSemantics    map[string]any `json:"graph_semantics,omitempty"`
	GeneratedSurfaces []string       `json:"generated_surface_notes"`
	OwnerConsumers    []string       `json:"owner_consumer_notes"`
	KnownUnknowns     []string       `json:"known_unknowns"`
	Verification      []string       `json:"verification_evidence"`
	Confidence        string         `json:"confidence,omitempty"`
	CreatedAt         string         `json:"created_at"`
}

type Bundle struct {
	Session Session `json:"session"`
	Events  []Event `json:"events"`
}

func Begin(input BeginInput) (Session, error) {
	now := time.Now().UTC()
	sessionID := fmt.Sprintf("delta-%s", now.Format("20060102T150405.000000000Z"))
	session := Session{
		SessionID:     sessionID,
		OriginCommand: strings.TrimSpace(input.OriginCommand),
		OriginContext: OriginContext{
			FeatureDir: strings.TrimSpace(input.OriginFeatureDir),
			LaneID:     strings.TrimSpace(input.OriginLaneID),
		},
		Git: GitContext{
			Available:         input.BaseCommit != "" || input.Branch != "",
			BaseCommit:        strings.TrimSpace(input.BaseCommit),
			Branch:            strings.TrimSpace(input.Branch),
			InitialDirtyPaths: normalizePaths(input.InitialDirtyPaths),
		},
		CreatedAt: now.Format(time.RFC3339Nano),
	}
	dir := sessionDir(input.RuntimeDir, sessionID)
	if err := os.MkdirAll(filepath.Join(dir, "events"), 0o755); err != nil {
		return Session{}, fmt.Errorf("create delta session: %w", err)
	}
	if err := writeJSON(filepath.Join(dir, "session.json"), session); err != nil {
		return Session{}, err
	}
	return session, nil
}

func Append(input AppendInput) (Event, error) {
	if strings.TrimSpace(input.SessionID) == "" {
		return Event{}, fmt.Errorf("session id is required")
	}
	if _, err := os.Stat(filepath.Join(sessionDir(input.RuntimeDir, input.SessionID), "session.json")); err != nil {
		return Event{}, fmt.Errorf("load delta session: %w", err)
	}
	now := time.Now().UTC()
	event := Event{
		EventID:           fmt.Sprintf("event-%s", now.Format("20060102T150405.000000000Z")),
		SessionID:         input.SessionID,
		EventType:         strings.TrimSpace(input.EventType),
		OriginCommand:     strings.TrimSpace(input.OriginCommand),
		OriginLaneID:      strings.TrimSpace(input.OriginLaneID),
		Phase:             strings.TrimSpace(input.Phase),
		ChangedPaths:      normalizePaths(input.ChangedPaths),
		ReadPaths:         normalizePaths(input.ReadPaths),
		BehaviorSurfaces:  normalizeStrings(input.BehaviorSurfaces),
		GraphSemantics:    input.GraphSemantics,
		GeneratedSurfaces: normalizePaths(input.GeneratedSurfaces),
		OwnerConsumers:    normalizeStrings(input.OwnerConsumers),
		KnownUnknowns:     normalizeStrings(input.KnownUnknowns),
		Verification:      normalizeStrings(input.Verification),
		Confidence:        strings.TrimSpace(input.Confidence),
		CreatedAt:         now.Format(time.RFC3339Nano),
	}
	path := filepath.Join(sessionDir(input.RuntimeDir, input.SessionID), "events", event.EventID+".json")
	if err := writeJSON(path, event); err != nil {
		return Event{}, err
	}
	return event, nil
}

func AppendPacketFile(runtimeDir string, sessionID string, packetFile string) (Event, error) {
	data, err := os.ReadFile(packetFile)
	if err != nil {
		return Event{}, fmt.Errorf("read packet file: %w", err)
	}
	var packet packetEvent
	if err := json.Unmarshal(data, &packet); err != nil {
		return Event{}, fmt.Errorf("parse packet file: %w", err)
	}
	return Append(AppendInput{
		RuntimeDir:        runtimeDir,
		SessionID:         sessionID,
		EventType:         packet.EventType,
		OriginCommand:     packet.OriginCommand,
		OriginLaneID:      packet.OriginLaneID,
		Phase:             packet.Phase,
		ChangedPaths:      packet.ChangedPaths,
		ReadPaths:         packet.ReadPaths,
		BehaviorSurfaces:  packet.BehaviorSurfaces,
		GraphSemantics:    packet.GraphSemantics,
		GeneratedSurfaces: packet.GeneratedSurfaces,
		OwnerConsumers:    packet.OwnerConsumers,
		KnownUnknowns:     packet.KnownUnknowns,
		Verification:      packet.Verification,
		Confidence:        packet.Confidence,
	})
}

func Load(runtimeDir string, sessionID string) (Bundle, error) {
	dir := sessionDir(runtimeDir, sessionID)
	data, err := os.ReadFile(filepath.Join(dir, "session.json"))
	if err != nil {
		return Bundle{}, fmt.Errorf("read delta session: %w", err)
	}
	var session Session
	if err := json.Unmarshal(data, &session); err != nil {
		return Bundle{}, fmt.Errorf("parse delta session: %w", err)
	}
	entries, err := os.ReadDir(filepath.Join(dir, "events"))
	if err != nil {
		return Bundle{}, fmt.Errorf("read delta events: %w", err)
	}
	var events []Event
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}
		data, err := os.ReadFile(filepath.Join(dir, "events", entry.Name()))
		if err != nil {
			return Bundle{}, fmt.Errorf("read delta event: %w", err)
		}
		var event Event
		if err := json.Unmarshal(data, &event); err != nil {
			return Bundle{}, fmt.Errorf("parse delta event: %w", err)
		}
		events = append(events, event)
	}
	sort.Slice(events, func(i, j int) bool { return events[i].CreatedAt < events[j].CreatedAt })
	return Bundle{Session: session, Events: events}, nil
}

func sessionDir(runtimeDir string, sessionID string) string {
	return filepath.Join(runtimeDir, "delta-sessions", filepath.Base(sessionID))
}

func writeJSON(path string, value any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return fmt.Errorf("create parent dir: %w", err)
	}
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return fmt.Errorf("encode json: %w", err)
	}
	return os.WriteFile(path, append(data, '\n'), 0o644)
}

func normalizePaths(paths []string) []string {
	out := make([]string, 0, len(paths))
	seen := map[string]bool{}
	for _, path := range paths {
		path = filepath.ToSlash(strings.TrimSpace(strings.TrimPrefix(path, "./")))
		if path == "" || seen[path] {
			continue
		}
		seen[path] = true
		out = append(out, path)
	}
	sort.Strings(out)
	return out
}

func normalizeStrings(values []string) []string {
	out := make([]string, 0, len(values))
	seen := map[string]bool{}
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	sort.Strings(out)
	return out
}
```

- [ ] **Step 4: Run delta tests and verify pass**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/delta
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

Run:

```powershell
git add tools/project-cognition/internal/delta/delta.go tools/project-cognition/internal/delta/delta_test.go
git commit -m "feat: add project cognition delta sessions"
```

Expected: commit succeeds.

### Task 3: Git Helpers for Status and Diff Boundaries

**Files:**
- Modify: `tools/project-cognition/internal/runtime/git.go`
- Test: `tools/project-cognition/internal/runtime/git_test.go`

- [ ] **Step 1: Write failing git helper tests**

Create `tools/project-cognition/internal/runtime/git_test.go`:

```go
package runtime

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func initGitRepo(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	runGit(t, root, "init")
	runGit(t, root, "config", "user.email", "test@example.com")
	runGit(t, root, "config", "user.name", "Test User")
	if err := os.WriteFile(filepath.Join(root, "README.md"), []byte("base\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, root, "add", "README.md")
	runGit(t, root, "commit", "-m", "initial")
	return root
}

func runGit(t *testing.T, root string, args ...string) {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("git %v failed: %v\n%s", args, err, string(out))
	}
}

func TestGitHeadAndBranch(t *testing.T) {
	root := initGitRepo(t)
	head, err := GitHead(root)
	if err != nil {
		t.Fatal(err)
	}
	if head == "" {
		t.Fatal("head is empty")
	}
	branch, err := GitBranch(root)
	if err != nil {
		t.Fatal(err)
	}
	if branch == "" {
		t.Fatal("branch is empty")
	}
}

func TestGitStatusEntriesIncludeStatusCodes(t *testing.T) {
	root := initGitRepo(t)
	if err := os.WriteFile(filepath.Join(root, "src.go"), []byte("package demo\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "README.md"), []byte("changed\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	entries, err := GitStatusEntries(root)
	if err != nil {
		t.Fatal(err)
	}
	byPath := map[string]GitStatusEntry{}
	for _, entry := range entries {
		byPath[entry.Path] = entry
	}
	if byPath["src.go"].Code != "??" {
		t.Fatalf("src.go status = %#v", byPath["src.go"])
	}
	if byPath["README.md"].Code == "" {
		t.Fatalf("README.md status missing: %#v", entries)
	}
}

func TestGitDiffNameStatus(t *testing.T) {
	root := initGitRepo(t)
	base, err := GitHead(root)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "feature.txt"), []byte("new\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	runGit(t, root, "add", "feature.txt")
	runGit(t, root, "commit", "-m", "feature")
	head, err := GitHead(root)
	if err != nil {
		t.Fatal(err)
	}
	entries, err := GitDiffNameStatus(root, base, head)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 1 || entries[0].Path != "feature.txt" || entries[0].Code != "A" {
		t.Fatalf("entries = %#v", entries)
	}
}
```

- [ ] **Step 2: Run runtime tests and verify failure**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/runtime
```

Expected: FAIL because `GitHead`, `GitBranch`, `GitStatusEntries`, and `GitDiffNameStatus` are undefined.

- [ ] **Step 3: Extend git helpers**

Modify `tools/project-cognition/internal/runtime/git.go` by adding these exported types and functions below existing imports:

```go
type GitStatusEntry struct {
	Code    string
	Path    string
	OldPath string
}

func GitAvailable(root string) bool {
	cmd := exec.Command("git", "rev-parse", "--is-inside-work-tree")
	cmd.Dir = root
	data, err := cmd.Output()
	return err == nil && strings.TrimSpace(string(data)) == "true"
}

func GitHead(root string) (string, error) {
	cmd := exec.Command("git", "rev-parse", "HEAD")
	cmd.Dir = root
	data, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(data)), nil
}

func GitBranch(root string) (string, error) {
	cmd := exec.Command("git", "branch", "--show-current")
	cmd.Dir = root
	data, err := cmd.Output()
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(data)), nil
}

func GitStatusEntries(root string) ([]GitStatusEntry, error) {
	cmd := exec.Command("git", "status", "--porcelain=v1", "--untracked-files=all")
	cmd.Dir = root
	data, err := cmd.Output()
	if err != nil {
		return nil, err
	}
	return parseStatusEntries(string(data)), nil
}

func GitDiffNameStatus(root string, base string, head string) ([]GitStatusEntry, error) {
	cmd := exec.Command("git", "diff", "--name-status", base+".."+head)
	cmd.Dir = root
	data, err := cmd.Output()
	if err != nil {
		return nil, err
	}
	return parseNameStatusEntries(string(data)), nil
}

func parseStatusEntries(output string) []GitStatusEntry {
	var entries []GitStatusEntry
	for _, line := range strings.Split(output, "\n") {
		if len(line) < 4 {
			continue
		}
		code := strings.TrimSpace(line[:2])
		path := strings.TrimSpace(line[3:])
		oldPath := ""
		if strings.Contains(path, " -> ") {
			parts := strings.Split(path, " -> ")
			oldPath = filepath.ToSlash(parts[0])
			path = parts[len(parts)-1]
		}
		entries = append(entries, GitStatusEntry{Code: code, Path: filepath.ToSlash(path), OldPath: oldPath})
	}
	return entries
}

func parseNameStatusEntries(output string) []GitStatusEntry {
	var entries []GitStatusEntry
	for _, line := range strings.Split(output, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		parts := strings.Split(line, "\t")
		if len(parts) < 2 {
			continue
		}
		entry := GitStatusEntry{Code: parts[0], Path: filepath.ToSlash(parts[len(parts)-1])}
		if len(parts) > 2 {
			entry.OldPath = filepath.ToSlash(parts[1])
		}
		entries = append(entries, entry)
	}
	return entries
}
```

Keep the existing `GitChangedPaths`, `parseGitStatusShort`, and `normalizeGitLines` functions for compatibility.

- [ ] **Step 4: Run runtime tests and verify pass**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/runtime
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git add tools/project-cognition/internal/runtime/git.go tools/project-cognition/internal/runtime/git_test.go
git commit -m "feat: add git boundary helpers"
```

Expected: commit succeeds.

### Task 4: Boundary Resolution and Workflow-Owned Paths

**Files:**
- Create: `tools/project-cognition/internal/boundary/boundary.go`
- Test: `tools/project-cognition/internal/boundary/boundary_test.go`

- [ ] **Step 1: Write failing boundary tests**

Create `tools/project-cognition/internal/boundary/boundary_test.go`:

```go
package boundary

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/config"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
)

func TestWorkflowOwnedPathsExcludeInitialDirty(t *testing.T) {
	bundle := delta.Bundle{
		Session: delta.Session{Git: delta.GitContext{InitialDirtyPaths: []string{"src/user.go"}}},
		Events: []delta.Event{{
			ChangedPaths: []string{"src/task.go", "src/user.go"},
		}},
	}
	result := Resolve(ResolveInput{
		Config:          config.Config{ProjectCognition: config.ProjectCognitionConfig{AutoCommit: true}},
		Bundle:          bundle,
		GitDiffPaths:    []string{"src/task.go", "src/user.go"},
		ExplicitArtifacts: []string{"docs/task.md"},
	})
	if result.AutoCommitDecision != "commit_skipped" {
		t.Fatalf("AutoCommitDecision = %q", result.AutoCommitDecision)
	}
	if !contains(result.WorkflowOwnedPaths, "src/task.go") {
		t.Fatalf("WorkflowOwnedPaths = %#v", result.WorkflowOwnedPaths)
	}
	if contains(result.WorkflowOwnedPaths, "src/user.go") {
		t.Fatalf("initial dirty path should be excluded: %#v", result.WorkflowOwnedPaths)
	}
	if !contains(result.AmbiguousPaths, "src/user.go") {
		t.Fatalf("AmbiguousPaths = %#v", result.AmbiguousPaths)
	}
}

func TestClaimedInitialDirtyPathCanBeOwned(t *testing.T) {
	bundle := delta.Bundle{
		Session: delta.Session{Git: delta.GitContext{InitialDirtyPaths: []string{"src/user.go"}}},
		Events: []delta.Event{{
			ChangedPaths: []string{"src/user.go"},
			GraphSemantics: map[string]any{
				"claimed_initial_dirty_paths": []any{"src/user.go"},
			},
		}},
	}
	result := Resolve(ResolveInput{
		Config:       config.Config{ProjectCognition: config.ProjectCognitionConfig{AutoCommit: true}},
		Bundle:       bundle,
		GitDiffPaths: []string{"src/user.go"},
	})
	if result.AutoCommitDecision != "commit_created" {
		t.Fatalf("AutoCommitDecision = %q", result.AutoCommitDecision)
	}
	if !contains(result.WorkflowOwnedPaths, "src/user.go") {
		t.Fatalf("WorkflowOwnedPaths = %#v", result.WorkflowOwnedPaths)
	}
}

func TestAutoCommitDisabledByConfig(t *testing.T) {
	result := Resolve(ResolveInput{
		Config: config.Config{ProjectCognition: config.ProjectCognitionConfig{AutoCommit: false}},
		Bundle: delta.Bundle{Events: []delta.Event{{ChangedPaths: []string{"src/a.go"}}}},
	})
	if result.AutoCommitDecision != "commit_skipped" {
		t.Fatalf("AutoCommitDecision = %q", result.AutoCommitDecision)
	}
	if result.Outcome != "boundary_resolved" {
		t.Fatalf("Outcome = %q", result.Outcome)
	}
}

func TestResolveUsesDeltaPathsWhenGitDiffEmpty(t *testing.T) {
	result := Resolve(ResolveInput{
		Config: config.Config{ProjectCognition: config.ProjectCognitionConfig{AutoCommit: true}},
		Bundle: delta.Bundle{Events: []delta.Event{{ChangedPaths: []string{"src/a.go"}}}},
	})
	if !contains(result.ChangedPaths, "src/a.go") {
		t.Fatalf("ChangedPaths = %#v", result.ChangedPaths)
	}
}

func TestIgnoredPathsAreRemoved(t *testing.T) {
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, ".cognitionignore"), []byte("vendor/\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	result := Resolve(ResolveInput{
		Root:   root,
		Config: config.Config{ProjectCognition: config.ProjectCognitionConfig{AutoCommit: true}},
		Bundle: delta.Bundle{Events: []delta.Event{{ChangedPaths: []string{"src/a.go", "vendor/a.go"}}}},
	})
	if contains(result.ChangedPaths, "vendor/a.go") {
		t.Fatalf("ignored path leaked into changed paths: %#v", result.ChangedPaths)
	}
	if !contains(result.IgnoredPaths, "vendor/a.go") {
		t.Fatalf("IgnoredPaths = %#v", result.IgnoredPaths)
	}
}

func contains(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
```

- [ ] **Step 2: Run boundary tests and verify failure**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/boundary
```

Expected: FAIL because package `internal/boundary` does not exist.

- [ ] **Step 3: Implement boundary package**

Create `tools/project-cognition/internal/boundary/boundary.go`:

```go
package boundary

import (
	"path/filepath"
	"sort"
	"strings"

	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/config"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/ignore"
)

type ResolveInput struct {
	Root              string
	Config            config.Config
	Bundle            delta.Bundle
	GitDiffPaths      []string
	ExplicitArtifacts []string
}

type Result struct {
	Outcome            string   `json:"outcome"`
	AutoCommitDecision string   `json:"auto_commit_decision"`
	BoundarySource     string   `json:"boundary_source"`
	ChangedPaths       []string `json:"changed_paths"`
	WorkflowOwnedPaths []string `json:"workflow_owned_paths"`
	AmbiguousPaths     []string `json:"ambiguous_paths"`
	IgnoredPaths       []string `json:"ignored_paths"`
	Warnings           []string `json:"warnings"`
}

func Resolve(input ResolveInput) Result {
	candidates := normalizePaths(input.GitDiffPaths)
	boundarySource := "git_diff"
	if len(candidates) == 0 {
		candidates = eventChangedPaths(input.Bundle.Events)
		boundarySource = "delta_journal"
	}
	candidates = appendUnique(candidates, input.ExplicitArtifacts...)
	kept, ignored := ignore.Load(input.Root).Filter(candidates)
	initialDirty := toSet(input.Bundle.Session.Git.InitialDirtyPaths)
	claimed := claimedInitialDirty(input.Bundle.Events)

	var owned []string
	var ambiguous []string
	for _, path := range kept {
		if initialDirty[path] && !claimed[path] {
			ambiguous = append(ambiguous, path)
			continue
		}
		owned = append(owned, path)
	}
	owned = normalizePaths(owned)
	ambiguous = normalizePaths(ambiguous)
	decision := "commit_created"
	if !input.Config.ProjectCognition.AutoCommit || len(owned) == 0 || len(ambiguous) > 0 {
		decision = "commit_skipped"
	}
	return Result{
		Outcome:            "boundary_resolved",
		AutoCommitDecision: decision,
		BoundarySource:     boundarySource,
		ChangedPaths:       normalizePaths(kept),
		WorkflowOwnedPaths: owned,
		AmbiguousPaths:     ambiguous,
		IgnoredPaths:       normalizePaths(ignored),
		Warnings:           warnings(decision, ambiguous),
	}
}

func eventChangedPaths(events []delta.Event) []string {
	var paths []string
	for _, event := range events {
		paths = append(paths, event.ChangedPaths...)
	}
	return normalizePaths(paths)
}

func claimedInitialDirty(events []delta.Event) map[string]bool {
	claimed := map[string]bool{}
	for _, event := range events {
		raw, ok := event.GraphSemantics["claimed_initial_dirty_paths"]
		if !ok {
			continue
		}
		switch typed := raw.(type) {
		case []any:
			for _, item := range typed {
				if text, ok := item.(string); ok {
					claimed[normalizePath(text)] = true
				}
			}
		case []string:
			for _, item := range typed {
				claimed[normalizePath(item)] = true
			}
		}
	}
	return claimed
}

func warnings(decision string, ambiguous []string) []string {
	var out []string
	if decision == "commit_skipped" {
		out = append(out, "auto-commit skipped; update can continue from boundary metadata")
	}
	if len(ambiguous) > 0 {
		out = append(out, "ambiguous initial dirty paths excluded from workflow-owned paths")
	}
	return out
}

func appendUnique(existing []string, values ...string) []string {
	out := append([]string{}, existing...)
	seen := toSet(out)
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

func toSet(values []string) map[string]bool {
	out := map[string]bool{}
	for _, value := range values {
		value = normalizePath(value)
		if value != "" {
			out[value] = true
		}
	}
	return out
}

func normalizePaths(paths []string) []string {
	out := make([]string, 0, len(paths))
	seen := map[string]bool{}
	for _, path := range paths {
		path = normalizePath(path)
		if path == "" || seen[path] {
			continue
		}
		seen[path] = true
		out = append(out, path)
	}
	sort.Strings(out)
	return out
}

func normalizePath(path string) string {
	return filepath.ToSlash(strings.TrimSpace(strings.TrimPrefix(path, "./")))
}
```

- [ ] **Step 4: Run boundary tests and verify pass**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/boundary
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

Run:

```powershell
git add tools/project-cognition/internal/boundary/boundary.go tools/project-cognition/internal/boundary/boundary_test.go
git commit -m "feat: resolve project cognition update boundaries"
```

Expected: commit succeeds.

### Task 5: CLI Delta Commands

**Files:**
- Modify: `tools/project-cognition/internal/cli/cli.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Add failing CLI tests for delta commands**

Append these tests to `tools/project-cognition/internal/cli/cli_test.go`:

```go
func TestDeltaBeginCommandCreatesSession(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["session_id"] == "" {
		t.Fatalf("payload = %#v", payload)
	}
}

func TestDeltaAppendCommandWritesEvent(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var beginOut, beginErr bytes.Buffer
	if code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &beginOut, &beginErr, "test"); code != 0 {
		t.Fatalf("begin failed: %s", beginErr.String())
	}
	var begin map[string]any
	if err := json.Unmarshal(beginOut.Bytes(), &begin); err != nil {
		t.Fatal(err)
	}
	sessionID := begin["session_id"].(string)

	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "append", "--session", sessionID, "--event-type", "worker_result", "--changed-path", "src/a.go", "--verification", "go test ./... PASS", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var event map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &event); err != nil {
		t.Fatal(err)
	}
	if event["event_id"] == "" {
		t.Fatalf("event = %#v", event)
	}
}

func TestDeltaAppendCommandAcceptsPacketFile(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var beginOut, beginErr bytes.Buffer
	if code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &beginOut, &beginErr, "test"); code != 0 {
		t.Fatalf("begin failed: %s", beginErr.String())
	}
	var begin map[string]any
	if err := json.Unmarshal(beginOut.Bytes(), &begin); err != nil {
		t.Fatal(err)
	}
	sessionID := begin["session_id"].(string)
	packet := filepath.Join(root, "packet.json")
	data := []byte(`{"event_type":"worker_result","changed_paths":["src/a.go"],"verification_evidence":["go test ./... PASS"]}`)
	if err := os.WriteFile(packet, data, 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"delta", "append", "--session", sessionID, "--packet-file", packet, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var event map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &event); err != nil {
		t.Fatal(err)
	}
	if event["event_type"] != "worker_result" {
		t.Fatalf("event = %#v", event)
	}
}
```

- [ ] **Step 2: Run CLI tests and verify failure**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/cli -run "TestDelta"
```

Expected: FAIL because `delta` command is unknown.

- [ ] **Step 3: Add CLI command routing and handlers**

Modify `tools/project-cognition/internal/cli/cli.go`:

1. Add import:

```go
"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
```

2. Add command case in `Run`:

```go
case "delta":
	return deltaCommand(args[1:], stdout, stderr, paths)
```

3. Add `"delta"` to help text command list.

4. Add these functions near other command handlers:

```go
func deltaCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	if len(args) == 0 {
		fmt.Fprintln(stderr, "delta requires subcommand: begin, append, status")
		return 2
	}
	switch args[0] {
	case "begin":
		return deltaBeginCommand(args[1:], stdout, stderr, paths)
	case "append":
		return deltaAppendCommand(args[1:], stdout, stderr, paths)
	case "status":
		return deltaStatusCommand(args[1:], stdout, stderr, paths)
	default:
		fmt.Fprintf(stderr, "unknown delta subcommand: %s\n", args[0])
		return 2
	}
}

func deltaBeginCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("delta begin", flag.ContinueOnError)
	fs.SetOutput(stderr)
	originCommand := fs.String("origin-command", "", "Origin workflow command")
	originFeatureDir := fs.String("origin-feature-dir", "", "Origin feature directory")
	originLaneID := fs.String("origin-lane-id", "", "Origin lane id")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	head, _ := rt.GitHead(paths.Root)
	branch, _ := rt.GitBranch(paths.Root)
	initialDirty, _ := rt.GitChangedPaths(paths.Root)
	session, err := delta.Begin(delta.BeginInput{
		Root:              paths.Root,
		RuntimeDir:        paths.RuntimeDir,
		OriginCommand:     *originCommand,
		OriginFeatureDir:  *originFeatureDir,
		OriginLaneID:      *originLaneID,
		BaseCommit:        head,
		Branch:            branch,
		InitialDirtyPaths: initialDirty,
	})
	return writeCommandResult(stdout, stderr, paths, session, err)
}

func deltaAppendCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("delta append", flag.ContinueOnError)
	fs.SetOutput(stderr)
	sessionID := fs.String("session", "", "Delta session id")
	packetFile := fs.String("packet-file", "", "Packet JSON file")
	eventType := fs.String("event-type", "event", "Delta event type")
	originCommand := fs.String("origin-command", "", "Origin workflow command")
	originLaneID := fs.String("origin-lane-id", "", "Origin lane id")
	phase := fs.String("phase", "", "Workflow phase")
	confidence := fs.String("confidence", "", "Confidence")
	var changed stringList
	var reads stringList
	var behavior stringList
	var unknowns stringList
	var verification stringList
	var generated stringList
	fs.Var(&changed, "changed-path", "Changed path")
	fs.Var(&reads, "read-path", "Read path")
	fs.Var(&behavior, "behavior-surface", "Behavior surface")
	fs.Var(&unknowns, "known-unknown", "Known unknown")
	fs.Var(&verification, "verification", "Verification evidence")
	fs.Var(&generated, "generated-surface", "Generated surface")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if *packetFile != "" {
		event, err := delta.AppendPacketFile(paths.RuntimeDir, *sessionID, *packetFile)
		return writeCommandResult(stdout, stderr, paths, event, err)
	}
	event, err := delta.Append(delta.AppendInput{
		RuntimeDir:        paths.RuntimeDir,
		SessionID:         *sessionID,
		EventType:         *eventType,
		OriginCommand:     *originCommand,
		OriginLaneID:      *originLaneID,
		Phase:             *phase,
		ChangedPaths:      changed,
		ReadPaths:         reads,
		BehaviorSurfaces:  behavior,
		KnownUnknowns:     unknowns,
		Verification:      verification,
		GeneratedSurfaces: generated,
		Confidence:        *confidence,
	})
	return writeCommandResult(stdout, stderr, paths, event, err)
}

func deltaStatusCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("delta status", flag.ContinueOnError)
	fs.SetOutput(stderr)
	sessionID := fs.String("session", "", "Delta session id")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	bundle, err := delta.Load(paths.RuntimeDir, *sessionID)
	return writeCommandResult(stdout, stderr, paths, bundle, err)
}
```

- [ ] **Step 4: Run CLI delta tests and verify pass**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/cli -run "TestDelta"
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

Run:

```powershell
git add tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/cli/cli_test.go
git commit -m "feat: add project cognition delta CLI"
```

Expected: commit succeeds.

### Task 6: Update Command Phase 1-2 Boundary Outcomes

**Files:**
- Modify: `tools/project-cognition/internal/update/state.go`
- Modify: `tools/project-cognition/internal/update/state_test.go`
- Modify: `tools/project-cognition/internal/cli/cli.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`
- Modify: `tools/project-cognition/internal/runtime/status.go`

- [ ] **Step 1: Add failing update boundary tests**

Append these tests to `tools/project-cognition/internal/update/state_test.go`:

```go
func TestRunUpdateWithDeltaSessionReturnsBoundaryResolved(t *testing.T) {
	paths := testPaths(t)
	session, err := delta.Begin(delta.BeginInput{
		Root:              paths.Root,
		RuntimeDir:        paths.RuntimeDir,
		OriginCommand:     "quick",
		InitialDirtyPaths: []string{},
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir:    paths.RuntimeDir,
		SessionID:     session.SessionID,
		EventType:     "worker_result",
		ChangedPaths:  []string{"src/a.go"},
		Verification:  []string{"go test ./... PASS"},
	}); err != nil {
		t.Fatal(err)
	}
	payload, err := RunUpdate(paths, UpdateInput{DeltaSessionID: session.SessionID, Reason: "workflow-finalize"})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Readiness == rt.ReadyReadiness {
		t.Fatalf("phase 1-2 update must not claim ready: %#v", payload)
	}
	if payload.UpdateOutcome != "boundary_resolved" {
		t.Fatalf("UpdateOutcome = %q", payload.UpdateOutcome)
	}
	if payload.Boundary == nil || payload.Boundary.BoundarySource != "delta_journal" {
		t.Fatalf("Boundary = %#v", payload.Boundary)
	}
}

func TestRunUpdateWithDeltaSessionRecordsStatusMetadata(t *testing.T) {
	paths := testPaths(t)
	session, err := delta.Begin(delta.BeginInput{
		Root:          paths.Root,
		RuntimeDir:    paths.RuntimeDir,
		OriginCommand: "quick",
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := delta.Append(delta.AppendInput{
		RuntimeDir:   paths.RuntimeDir,
		SessionID:    session.SessionID,
		ChangedPaths: []string{"src/a.go"},
	}); err != nil {
		t.Fatal(err)
	}
	if _, err := RunUpdate(paths, UpdateInput{DeltaSessionID: session.SessionID, Reason: "workflow-finalize"}); err != nil {
		t.Fatal(err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	if status.LastDeltaSessionID != session.SessionID {
		t.Fatalf("LastDeltaSessionID = %q", status.LastDeltaSessionID)
	}
	if status.LastUpdateOutcome != "boundary_resolved" {
		t.Fatalf("LastUpdateOutcome = %q", status.LastUpdateOutcome)
	}
}
```

Also add imports to `state_test.go`:

```go
"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
```

- [ ] **Step 2: Run update tests and verify failure**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/update
```

Expected: FAIL because `UpdateInput.DeltaSessionID`, `UpdatePayload.UpdateOutcome`, `UpdatePayload.Boundary`, and status fields are undefined.

- [ ] **Step 3: Extend status fields**

Modify `tools/project-cognition/internal/runtime/status.go` by adding fields to `Status`:

```go
LastDeltaSessionID string `json:"last_delta_session_id"`
LastUpdateOutcome  string `json:"last_update_outcome"`
LastUpdateBoundary string `json:"last_update_boundary"`
```

Do not change `DefaultStatus` behavior beyond leaving these fields empty by default.

- [ ] **Step 4: Extend update input and payload**

Modify `tools/project-cognition/internal/update/state.go`:

1. Add imports:

```go
"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/boundary"
"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/config"
"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/delta"
```

2. Add fields:

```go
type UpdateInput struct {
	ChangedPaths   []string
	ScopePaths     []string
	Reason         string
	DeltaSessionID string
	CommitRange    string
}
```

3. Add payload fields:

```go
UpdateOutcome string           `json:"update_outcome"`
Boundary      *boundary.Result `json:"boundary,omitempty"`
```

4. At the start of `RunUpdate`, before existing changed-path derivation, add this branch:

```go
if input.DeltaSessionID != "" {
	cfg, err := config.Load(paths.Root)
	if err != nil {
		return UpdatePayload{}, err
	}
	bundle, err := delta.Load(paths.RuntimeDir, input.DeltaSessionID)
	if err != nil {
		return UpdatePayload{}, err
	}
	var gitDiff []string
	if input.CommitRange != "" {
		parts := strings.Split(input.CommitRange, "..")
		if len(parts) == 2 {
			entries, err := rt.GitDiffNameStatus(paths.Root, parts[0], parts[1])
			if err != nil {
				return UpdatePayload{}, err
			}
			for _, entry := range entries {
				gitDiff = append(gitDiff, entry.Path)
			}
		}
	}
	result := boundary.Resolve(boundary.ResolveInput{
		Root:         paths.Root,
		Config:       cfg,
		Bundle:       bundle,
		GitDiffPaths: gitDiff,
	})
	updateID := "upd-" + time.Now().UTC().Format("20060102T150405.000000000Z")
	changedJSON, _ := json.Marshal(result.ChangedPaths)
	st, err := store.Open(paths)
	if err != nil {
		return UpdatePayload{}, err
	}
	defer st.Close()
	if err := st.RecordUpdate(context.Background(), updateID, input.Reason, string(changedJSON)); err != nil {
		return UpdatePayload{}, err
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return UpdatePayload{}, err
	}
	status.LastUpdateID = updateID
	status.LastDeltaSessionID = input.DeltaSessionID
	status.LastUpdateOutcome = result.Outcome
	status.LastUpdateBoundary = result.BoundarySource
	status.LastRefreshChangedFilesBasis = result.ChangedPaths
	status.Dirty = true
	status.Status = "stale"
	status.Freshness = rt.StaleFreshness
	status.Readiness = rt.BlockedReadiness
	status.RecommendedNextAction = "review_project_cognition_update"
	if err := rt.WriteStatus(paths, status); err != nil {
		return UpdatePayload{}, err
	}
	return UpdatePayload{
		Readiness:               status.Readiness,
		RecommendedNextAction:   status.RecommendedNextAction,
		UpdateID:                updateID,
		UpdateOutcome:           result.Outcome,
		ChangedPaths:            result.ChangedPaths,
		IgnoredPaths:            result.IgnoredPaths,
		ReviewPaths:             result.AmbiguousPaths,
		KnownUnknowns:           result.Warnings,
		MinimalLiveReads:        result.WorkflowOwnedPaths,
		PathAdoption:            map[string]any{"phase": "boundary_only", "auto_commit_decision": result.AutoCommitDecision},
		LastRefreshChangedBasis: result.ChangedPaths,
		Boundary:                &result,
	}, nil
}
```

This branch intentionally keeps `Readiness` blocked/stale because Phase 1-2 has not patched graph records.

- [ ] **Step 5: Extend CLI update flags**

Modify `updateCommand` in `tools/project-cognition/internal/cli/cli.go`:

```go
deltaSession := fs.String("delta-session", "", "Delta session id")
commitRange := fs.String("commit-range", "", "Commit range base..head")
```

Pass them to `update.RunUpdate`:

```go
payload, err := update.RunUpdate(paths, update.UpdateInput{
	ChangedPaths:   changed,
	ScopePaths:     scopes,
	Reason:         *reason,
	DeltaSessionID: *deltaSession,
	CommitRange:    *commitRange,
})
```

- [ ] **Step 6: Add CLI update delta test**

Append to `tools/project-cognition/internal/cli/cli_test.go`:

```go
func TestUpdateCommandAcceptsDeltaSession(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var beginOut, beginErr bytes.Buffer
	if code := Run([]string{"delta", "begin", "--origin-command", "quick", "--format", "json"}, &beginOut, &beginErr, "test"); code != 0 {
		t.Fatalf("begin failed: %s", beginErr.String())
	}
	var begin map[string]any
	if err := json.Unmarshal(beginOut.Bytes(), &begin); err != nil {
		t.Fatal(err)
	}
	sessionID := begin["session_id"].(string)
	var appendOut, appendErr bytes.Buffer
	if code := Run([]string{"delta", "append", "--session", sessionID, "--changed-path", "src/a.go", "--format", "json"}, &appendOut, &appendErr, "test"); code != 0 {
		t.Fatalf("append failed: %s", appendErr.String())
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"update", "--delta-session", sessionID, "--reason", "workflow-finalize", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["update_outcome"] != "boundary_resolved" {
		t.Fatalf("payload = %#v", payload)
	}
	if payload["readiness"] == "query_ready" {
		t.Fatalf("phase 1-2 update must not claim ready: %#v", payload)
	}
}
```

- [ ] **Step 7: Run focused update and CLI tests**

Run:

```powershell
Set-Location tools/project-cognition
go test ./internal/update ./internal/cli
```

Expected: PASS.

- [ ] **Step 8: Commit Task 6**

Run:

```powershell
git add tools/project-cognition/internal/update/state.go tools/project-cognition/internal/update/state_test.go tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/cli/cli_test.go tools/project-cognition/internal/runtime/status.go
git commit -m "feat: resolve update boundaries from delta sessions"
```

Expected: commit succeeds.

### Task 7: Whole Runtime Verification

**Files:**
- No new files.

- [ ] **Step 1: Run gofmt**

Run:

```powershell
Set-Location tools/project-cognition
gofmt -w internal/config internal/delta internal/boundary internal/runtime internal/update internal/cli
```

Expected: no output.

- [ ] **Step 2: Run full Go test suite**

Run:

```powershell
Set-Location tools/project-cognition
go test ./...
```

Expected: PASS.

- [ ] **Step 3: Run go vet**

Run:

```powershell
Set-Location tools/project-cognition
go vet ./...
```

Expected: PASS with no output.

- [ ] **Step 4: Build binary**

Run:

```powershell
Set-Location tools/project-cognition
go build -o bin/project-cognition.exe .
```

Expected: command exits 0 and `tools/project-cognition/bin/project-cognition.exe` exists.

- [ ] **Step 5: Commit verification cleanup if gofmt changed files**

Run:

```powershell
git status --short
```

If files are modified by gofmt, commit:

```powershell
git add tools/project-cognition
git commit -m "chore: format project cognition runtime"
```

Expected: either no changes, or one formatting commit.

## Plan Self-Review

Spec coverage:

- Delta journal begin/append/load is covered by Tasks 2 and 5.
- Auto-commit default and disable paths are covered by Task 1 and Task 4.
- Workflow-owned path computation is covered by Task 4.
- Staged delivery labels are covered by Task 6.
- Metadata commit policy is not implemented in Phase 1-2 because no metadata commit command is added in this slice; this is intentionally left for workflow integration or Phase 3+ metadata handling.
- Live-read budget is not implemented in Phase 1-2 because no bounded live reads happen before DB graph patching; this belongs in Phase 3.

Placeholder scan:

- No implementation step uses TBD/TODO/fill-in wording.
- Phase 3+ responsibilities are explicitly excluded from this plan rather than left ambiguous.

Type consistency:

- `config.Config.ProjectCognition.AutoCommit` is defined in Task 1 and reused by Task 4.
- `delta.Bundle`, `delta.Session`, and `delta.Event` are defined in Task 2 and reused by Tasks 4 and 6.
- `boundary.Result` is defined in Task 4 and embedded in `update.UpdatePayload` in Task 6.

## Execution Notes

- This plan is intentionally runtime-only. Do not edit workflow templates in this execution pass.
- This plan should leave the runtime in a truthful Phase 1-2 state: it can record delta sessions and resolve update boundaries, but it cannot claim graph freshness.
- Use frequent commits exactly as listed so later phases can use commit ranges as test data.

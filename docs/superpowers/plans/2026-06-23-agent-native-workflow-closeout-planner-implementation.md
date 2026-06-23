# Agent-Native Workflow Closeout Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `project-cognition closeout-plan` and wire ordinary workflow-owned mutation closeout through a deterministic planner while preserving delta-session closeout and verified new-path adoption.

**Architecture:** Add a focused Go package under `tools/project-cognition/internal/closeout` that wraps the existing `changes` primitive and returns a planner-only JSON contract. The CLI exposes it as `project-cognition closeout-plan`; generated workflow guidance consumes `update_mode` and agent-owned required fields before calling the existing `project-cognition update` engine.

**Tech Stack:** Go 1.21 project-cognition runtime, Python pytest for Specify CLI/template tests, Markdown generated workflow templates and passive skills.

---

## File Structure

- Create `tools/project-cognition/internal/closeout/plan.go`: planner package, JSON contract structs, workflow canonicalization, mode selection, draft payload creation, unknown-path disposition queue.
- Create `tools/project-cognition/internal/closeout/plan_test.go`: package-level tests for payload mode, delta mode, unknown path disposition schema, canonical workflow aliases, and blocked unknown workflow names.
- Modify `tools/project-cognition/internal/cli/cli.go`: import closeout package, add `closeout-plan` dispatch, help text, and flag parser.
- Modify `tools/project-cognition/internal/cli/cli_test.go`: CLI help and JSON contract tests.
- Modify `src/specify_cli/project_cognition_runtime.py`: require `closeout-plan` support from cached/release binaries.
- Modify `tests/test_project_cognition_runtime_install.py`: compatibility tests for the new command and installer script text checks.
- Modify `tools/project-cognition/install.sh` and `tools/project-cognition/install.ps1`: verify downloaded binaries expose `closeout-plan --workflow --delta-session`.
- Modify `templates/command-partials/common/inline-project-cognition-update.md`: planner-first closeout contract.
- Modify `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md` and `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: passive routing mirrors for planner-first closeout.
- Modify `templates/project-handbook-template.md`, `PROJECT-HANDBOOK.md`, `README.md`, `docs/quickstart.md`, and `docs/installation.md`: operator docs for planner-first closeout.
- Modify `.github/workflows/release.yml`: release notes mention `closeout-plan`.
- Modify focused tests under `tests/test_alignment_templates.py`, `tests/test_specify_guidance_docs.py`, and `tests/test_runtime_handbook_contract.py`.

---

### Task 1: Runtime Planner Tests

**Files:**
- Create: `tools/project-cognition/internal/closeout/plan_test.go`

- [ ] **Step 1: Write failing package tests**

Create `tools/project-cognition/internal/closeout/plan_test.go` with this content:

```go
package closeout

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/update"
)

func TestRunPlansPayloadModeForKnownMappedChange(t *testing.T) {
	root, paths := initCloseoutFixture(t)
	writeCloseoutFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"v2\" }\n")

	payload, err := Run(paths, Input{
		Workflow:           "implement",
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
		PayloadPath:        ".specify/project-cognition/updates/custom.json",
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "ok" {
		t.Fatalf("Status = %q, errors=%#v", payload.Status, payload.Errors)
	}
	if payload.Workflow != "sp-implement" || payload.WorkflowCanonical != "sp-implement" {
		t.Fatalf("workflow fields = %q/%q", payload.Workflow, payload.WorkflowCanonical)
	}
	if payload.UpdateMode != "payload_file" {
		t.Fatalf("UpdateMode = %q, want payload_file", payload.UpdateMode)
	}
	if payload.PayloadDraft == nil {
		t.Fatal("PayloadDraft is nil")
	}
	if payload.PayloadDraft.Workflow != "sp-implement" {
		t.Fatalf("draft workflow = %q", payload.PayloadDraft.Workflow)
	}
	if !reflect.DeepEqual(payload.PayloadDraft.ChangedPaths, []string{"src/app.go"}) {
		t.Fatalf("ChangedPaths = %#v", payload.PayloadDraft.ChangedPaths)
	}
	if !reflect.DeepEqual(payload.KnownPaths, []string{"src/app.go"}) {
		t.Fatalf("KnownPaths = %#v", payload.KnownPaths)
	}
	if len(payload.UnknownPathDispositions) != 0 {
		t.Fatalf("UnknownPathDispositions = %#v, want none", payload.UnknownPathDispositions)
	}
	wantArgv := []string{"project-cognition", "update", "--payload-file", ".specify/project-cognition/updates/custom.json", "--reason", "workflow-finalize", "--format", "json"}
	if !reflect.DeepEqual(payload.UpdateArgv, wantArgv) {
		t.Fatalf("UpdateArgv = %#v", payload.UpdateArgv)
	}
	if !containsCloseoutString(payload.RequiredAgentFields, "verification") || !containsCloseoutString(payload.RequiredAgentFields, "behavior_surfaces") {
		t.Fatalf("RequiredAgentFields = %#v", payload.RequiredAgentFields)
	}
}

func TestRunQueuesUnknownPathDispositionWithoutBlockingKnownUnknown(t *testing.T) {
	root, paths := initCloseoutFixture(t)
	writeCloseoutFile(t, root, "src/new-feature.go", "package app\n\nfunc NewFeature() string { return \"new\" }\n")

	payload, err := Run(paths, Input{
		Workflow:           "quick",
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Workflow != "sp-quick" {
		t.Fatalf("Workflow = %q", payload.Workflow)
	}
	if !reflect.DeepEqual(payload.UnknownPaths, []string{"src/new-feature.go"}) {
		t.Fatalf("UnknownPaths = %#v", payload.UnknownPaths)
	}
	if len(payload.UnknownPathDispositions) != 1 {
		t.Fatalf("UnknownPathDispositions = %#v", payload.UnknownPathDispositions)
	}
	disposition := payload.UnknownPathDispositions[0]
	if disposition.Path != "src/new-feature.go" {
		t.Fatalf("Disposition path = %q", disposition.Path)
	}
	if disposition.ChangeLevel != "new_path" {
		t.Fatalf("ChangeLevel = %q, want new_path", disposition.ChangeLevel)
	}
	wantAllowed := []string{"adoptable", "review_only", "ignored", "blocking_known_unknown"}
	if !reflect.DeepEqual(disposition.AllowedDispositions, wantAllowed) {
		t.Fatalf("AllowedDispositions = %#v", disposition.AllowedDispositions)
	}
	if disposition.AgentDisposition != nil {
		t.Fatalf("AgentDisposition = %#v, want nil", disposition.AgentDisposition)
	}
	if !disposition.RequiredAgentDecision {
		t.Fatal("RequiredAgentDecision = false, want true")
	}
	if len(disposition.PlannerReason) == 0 {
		t.Fatal("PlannerReason is empty")
	}
	if payload.PayloadDraft == nil {
		t.Fatal("PayloadDraft is nil")
	}
	if len(payload.PayloadDraft.KnownUnknowns) != 0 {
		t.Fatalf("draft KnownUnknowns = %#v, want none", payload.PayloadDraft.KnownUnknowns)
	}
	if !containsCloseoutString(payload.RequiredAgentFields, "unknown_path_dispositions") {
		t.Fatalf("RequiredAgentFields = %#v, want unknown_path_dispositions", payload.RequiredAgentFields)
	}
}

func TestRunPreservesDeltaSessionMode(t *testing.T) {
	root, paths := initCloseoutFixture(t)
	writeCloseoutFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"delta\" }\n")

	payload, err := Run(paths, Input{
		Workflow:           "/sp.quick",
		DeltaSessionID:     "D-session",
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Workflow != "sp-quick" {
		t.Fatalf("Workflow = %q", payload.Workflow)
	}
	if payload.UpdateMode != "delta_session" {
		t.Fatalf("UpdateMode = %q", payload.UpdateMode)
	}
	if payload.DeltaSessionID == nil || *payload.DeltaSessionID != "D-session" {
		t.Fatalf("DeltaSessionID = %#v", payload.DeltaSessionID)
	}
	if payload.PayloadDraft != nil {
		t.Fatalf("PayloadDraft = %#v, want nil in delta mode", payload.PayloadDraft)
	}
	if payload.DeltaAppendDraft == nil {
		t.Fatal("DeltaAppendDraft is nil")
	}
	if !reflect.DeepEqual(payload.UpdateArgv, []string{"project-cognition", "update", "--delta-session", "D-session", "--reason", "workflow-finalize", "--format", "json"}) {
		t.Fatalf("UpdateArgv = %#v", payload.UpdateArgv)
	}
	if payload.RecommendedNextCommand != "fill_delta_append_draft_then_update" {
		t.Fatalf("RecommendedNextCommand = %q", payload.RecommendedNextCommand)
	}
}

func TestRunBlocksUnknownWorkflowName(t *testing.T) {
	_, paths := initCloseoutFixture(t)

	payload, err := Run(paths, Input{
		Workflow:           "custom-flow",
		IncludeWorkingTree: true,
		IncludeUntracked:   true,
	})
	if err != nil {
		t.Fatalf("Run returned error: %v", err)
	}

	if payload.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked", payload.Status)
	}
	if len(payload.Errors) == 0 || !strings.Contains(payload.Errors[0], "unknown workflow") {
		t.Fatalf("Errors = %#v", payload.Errors)
	}
	if payload.UpdateCommand != "" {
		t.Fatalf("UpdateCommand = %q, want empty", payload.UpdateCommand)
	}
}

func initCloseoutFixture(t *testing.T) (string, rt.Paths) {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatalf("create .specify: %v", err)
	}
	writeCloseoutFile(t, root, ".cognitionignore", ".specify/\n")
	writeCloseoutFile(t, root, "src/app.go", "package app\n\nfunc App() string { return \"v1\" }\n")
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatalf("ResolvePaths: %v", err)
	}
	seedCloseoutRuntimePathIndex(t, paths)
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.GraphReady = true
	status.ActiveGenerationID = "GEN-closeout"
	status.BaselineKind = rt.BaselineKindBrownfieldFull
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatalf("WriteStatus: %v", err)
	}
	runCloseoutGit(t, root, "init")
	runCloseoutGit(t, root, "config", "user.email", "test@example.com")
	runCloseoutGit(t, root, "config", "user.name", "Test User")
	runCloseoutGit(t, root, "add", ".")
	runCloseoutGit(t, root, "commit", "-m", "baseline")
	if _, err := update.CompleteRefresh(paths, "map-build"); err != nil {
		t.Fatalf("CompleteRefresh: %v", err)
	}
	return root, paths
}

func seedCloseoutRuntimePathIndex(t *testing.T, paths rt.Paths) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatalf("store.Open: %v", err)
	}
	defer st.Close()
	if _, err := st.ImportGeneration(context.Background(), store.ImportInput{
		GenerationID: "GEN-closeout",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-app",
			SourceKind:  "file",
			SourcePath:  "src/app.go",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-app",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "App",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-app"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-app",
			Path:       "src/app.go",
			NodeID:     "N-app",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-app",
		}},
		Aliases: []store.AliasImport{{
			ID:              "ALIAS-app",
			Alias:           "App",
			NormalizedAlias: "app",
			TargetType:      "node",
			TargetID:        "N-app",
			Source:          "node_title",
			Confidence:      "verified",
		}},
	}); err != nil {
		t.Fatalf("ImportGeneration: %v", err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), "GEN-closeout", rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatalf("PublishRuntimeMetadata: %v", err)
	}
}

func writeCloseoutFile(t *testing.T, root string, rel string, content string) {
	t.Helper()
	path := filepath.Join(root, rel)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("mkdir %s: %v", filepath.Dir(path), err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", rel, err)
	}
}

func runCloseoutGit(t *testing.T, dir string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	data, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v failed: %v\n%s", args, err, data)
	}
	return string(data)
}

func containsCloseoutString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
```

- [ ] **Step 2: Run tests and confirm the package is missing**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/closeout
Pop-Location
```

Expected: fail because `./internal/closeout` does not exist or because `Run` and `Input` are undefined.

- [ ] **Step 3: Commit failing tests**

```powershell
git add tools/project-cognition/internal/closeout/plan_test.go
git commit -m "test: define closeout planner runtime contract"
```

---

### Task 2: Runtime Planner Implementation

**Files:**
- Create: `tools/project-cognition/internal/closeout/plan.go`
- Test: `tools/project-cognition/internal/closeout/plan_test.go`

- [ ] **Step 1: Create the planner implementation**

Create `tools/project-cognition/internal/closeout/plan.go` with this content:

```go
package closeout

import (
	"fmt"
	"path/filepath"
	"sort"
	"strings"

	changespkg "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/changes"
	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

const (
	ReasonWorkflowFinalize = "workflow-finalize"

	UpdateModePayloadFile   = "payload_file"
	UpdateModeDeltaSession  = "delta_session"
	NextNoOp               = "no_op"
	NextDraftUpdate        = "draft_update"
	NextFillAgentFields    = "fill_required_agent_fields"
	NextAppendDeltaUpdate  = "fill_delta_append_draft_then_update"
	NextWritePayloadUpdate = "write_payload_then_update"
	NextRouteMapScanBuild  = "route_map_scan_build"
	NextMarkDirtyFallback  = "mark_dirty_fallback"
	NextBlocked            = "blocked"
)

var allowedWorkflows = map[string]bool{
	"sp-implement":     true,
	"sp-debug":         true,
	"sp-fast":          true,
	"sp-quick":         true,
	"sp-analyze":       true,
	"sp-specify":       true,
	"sp-clarify":       true,
	"sp-plan":          true,
	"sp-tasks":         true,
	"sp-deep-research": true,
	"sp-map-update":    true,
}

var allowedUnknownDispositions = []string{
	"adoptable",
	"review_only",
	"ignored",
	"blocking_known_unknown",
}

type Input struct {
	Workflow           string
	Reason             string
	Intent             string
	ExplicitPaths      []string
	Since              string
	Head               string
	PayloadPath        string
	DeltaSessionID     string
	IncludeWorkingTree bool
	IncludeUntracked   bool
}

type Payload struct {
	Status                  string                   `json:"status"`
	WorkflowInput           string                   `json:"workflow_input"`
	Workflow                string                   `json:"workflow"`
	WorkflowCanonical       string                   `json:"workflow_canonical"`
	Reason                  string                   `json:"reason"`
	Readiness               string                   `json:"readiness"`
	BaselineCommit          string                   `json:"baseline_commit,omitempty"`
	HeadCommit              string                   `json:"head_commit,omitempty"`
	WorkingTreeDirty        bool                     `json:"working_tree_dirty"`
	NextAction              string                   `json:"next_action"`
	UpdateMode              string                   `json:"update_mode,omitempty"`
	Changes                 []changespkg.Change      `json:"changes"`
	IgnoredPaths            []string                 `json:"ignored_paths"`
	UnknownPaths            []string                 `json:"unknown_paths"`
	UnknownPathDispositions []UnknownPathDisposition `json:"unknown_path_dispositions"`
	KnownPaths              []string                 `json:"known_paths"`
	DeltaSessionID          *string                  `json:"delta_session_id"`
	DeltaAppendCommand      string                   `json:"delta_append_command"`
	DeltaAppendDraft        *DeltaAppendDraft        `json:"delta_append_draft"`
	PayloadPath             string                   `json:"payload_path,omitempty"`
	PayloadDraft            *PayloadDraft            `json:"payload_draft"`
	RequiredAgentFields     []string                 `json:"required_agent_fields"`
	RecommendedNextCommand  string                   `json:"recommended_next_command"`
	UpdateCommand           string                   `json:"update_command"`
	UpdateArgv              []string                 `json:"update_argv"`
	FinalizerPolicy         map[string]string        `json:"finalizer_policy"`
	Warnings                []string                 `json:"warnings"`
	Errors                  []string                 `json:"errors"`
}

type UnknownPathDisposition struct {
	Path                  string   `json:"path"`
	ChangeLevel           string   `json:"change_level"`
	AllowedDispositions   []string `json:"allowed_dispositions"`
	AgentDisposition      *string  `json:"agent_disposition"`
	RequiredAgentDecision bool     `json:"required_agent_decision"`
	PlannerReason         []string `json:"planner_reason"`
}

type PayloadDraft struct {
	Workflow          string         `json:"workflow"`
	Reason            string         `json:"reason"`
	ChangedPaths      []string       `json:"changed_paths"`
	ScopePaths        []string       `json:"scope_paths"`
	BehaviorSurfaces  []string       `json:"behavior_surfaces"`
	GeneratedSurfaces []string       `json:"generated_surfaces"`
	StateContracts    []string       `json:"state_contracts"`
	Verification      []any          `json:"verification"`
	KnownUnknowns     []string       `json:"known_unknowns"`
	ConfidenceNotes   []string       `json:"confidence_notes"`
	UserDecisions     []string       `json:"user_decisions"`
	Boundary          map[string]any `json:"boundary"`
}

type DeltaAppendDraft struct {
	EventType              string   `json:"event_type"`
	OriginCommand          string   `json:"origin_command"`
	Phase                  string   `json:"phase"`
	ChangedPaths           []string `json:"changed_paths"`
	RequiredAgentFields    []string `json:"required_agent_fields"`
	RequiredEvidenceResult string   `json:"required_evidence_result"`
	ArgvPrefix             []string `json:"argv_prefix"`
	ArgvPlaceholders       []string `json:"argv_placeholders"`
}

func Run(paths rt.Paths, input Input) (Payload, error) {
	reason := strings.TrimSpace(input.Reason)
	if reason == "" {
		reason = ReasonWorkflowFinalize
	}
	workflowInput := strings.TrimSpace(input.Workflow)
	workflow, ok := CanonicalWorkflow(workflowInput)
	if !ok {
		return blockedPayload(workflowInput, reason, fmt.Sprintf("unknown workflow %q", workflowInput)), nil
	}

	changePayload, err := changespkg.Run(paths, changespkg.Input{
		Since:              input.Since,
		Head:               input.Head,
		IncludeWorkingTree: input.IncludeWorkingTree,
		IncludeUntracked:   input.IncludeUntracked,
		ExplicitPaths:      append([]string{}, input.ExplicitPaths...),
		Intent:             input.Intent,
	})
	if err != nil {
		return Payload{}, err
	}

	payload := Payload{
		Status:                  changePayload.Status,
		WorkflowInput:           workflowInput,
		Workflow:                workflow,
		WorkflowCanonical:       workflow,
		Reason:                  reason,
		Readiness:               changePayload.Readiness,
		BaselineCommit:          changePayload.BaselineCommit,
		HeadCommit:              changePayload.HeadCommit,
		WorkingTreeDirty:        changePayload.WorkingTreeDirty,
		Changes:                 append([]changespkg.Change{}, changePayload.Changes...),
		IgnoredPaths:            append([]string{}, changePayload.IgnoredPaths...),
		UnknownPaths:            append([]string{}, changePayload.UnknownPaths...),
		UnknownPathDispositions: unknownPathDispositions(changePayload.Changes),
		KnownPaths:              knownPaths(changePayload.Changes),
		DeltaSessionID:          nil,
		DeltaAppendCommand:      "",
		RequiredAgentFields:     []string{},
		FinalizerPolicy:         finalizerPolicy(),
		Warnings:                append([]string{}, changePayload.Warnings...),
		Errors:                  append([]string{}, changePayload.Errors...),
	}

	if changePayload.Status != "ok" {
		payload.NextAction = blockedNextAction(changePayload.NextAction)
		payload.RecommendedNextCommand = payload.NextAction
		return payload, nil
	}

	switch changePayload.NextAction {
	case "no_op":
		payload.NextAction = NextNoOp
		payload.RecommendedNextCommand = NextNoOp
		return payload, nil
	case "needs_rebuild":
		payload.NextAction = NextRouteMapScanBuild
		payload.RecommendedNextCommand = NextRouteMapScanBuild
		return payload, nil
	case "blocked":
		payload.Status = "blocked"
		payload.NextAction = NextBlocked
		payload.RecommendedNextCommand = NextBlocked
		return payload, nil
	}

	changed := includedChangedPaths(changePayload.Changes)
	payload.RequiredAgentFields = requiredAgentFields(payload.UnknownPathDispositions)

	if strings.TrimSpace(input.DeltaSessionID) != "" {
		sessionID := strings.TrimSpace(input.DeltaSessionID)
		payload.UpdateMode = UpdateModeDeltaSession
		payload.DeltaSessionID = &sessionID
		payload.DeltaAppendCommand = "display only: project-cognition delta append --session <delta_session_id> --event-type workflow_closeout ...agent evidence flags... --format json"
		payload.DeltaAppendDraft = deltaAppendDraft(sessionID, workflow, changed, payload.RequiredAgentFields)
		payload.UpdateCommand = "display only: project-cognition update --delta-session <delta_session_id> --reason <reason> --format json"
		payload.UpdateArgv = []string{"project-cognition", "update", "--delta-session", sessionID, "--reason", reason, "--format", "json"}
		payload.RecommendedNextCommand = "fill_delta_append_draft_then_update"
	} else {
		payload.UpdateMode = UpdateModePayloadFile
		payload.PayloadPath = payloadPath(input.PayloadPath, workflow, changePayload.HeadCommit)
		payload.PayloadDraft = &PayloadDraft{
			Workflow:          workflow,
			Reason:            reason,
			ChangedPaths:      changed,
			ScopePaths:        append([]string{}, changed...),
			BehaviorSurfaces:  []string{},
			GeneratedSurfaces: []string{},
			StateContracts:    []string{},
			Verification:      []any{},
			KnownUnknowns:     []string{},
			ConfidenceNotes:   []string{},
			UserDecisions:     []string{},
			Boundary:          map[string]any{},
		}
		payload.UpdateCommand = "display only: project-cognition update --payload-file <payload_path> --reason <reason> --format json"
		payload.UpdateArgv = []string{"project-cognition", "update", "--payload-file", payload.PayloadPath, "--reason", reason, "--format", "json"}
		payload.RecommendedNextCommand = NextWritePayloadUpdate
	}

	if len(payload.UnknownPathDispositions) > 0 {
		payload.NextAction = NextFillAgentFields
	} else {
		payload.NextAction = NextDraftUpdate
	}
	return payload, nil
}

func CanonicalWorkflow(input string) (string, bool) {
	value := strings.TrimSpace(input)
	value = strings.TrimPrefix(value, "/")
	value = strings.ReplaceAll(value, ".", "-")
	if value == "" {
		return "", false
	}
	if !strings.HasPrefix(value, "sp-") {
		value = "sp-" + value
	}
	if !allowedWorkflows[value] {
		return value, false
	}
	return value, true
}

func blockedPayload(workflowInput string, reason string, message string) Payload {
	return Payload{
		Status:                  "blocked",
		WorkflowInput:           workflowInput,
		Reason:                  reason,
		NextAction:              NextBlocked,
		Changes:                 []changespkg.Change{},
		IgnoredPaths:            []string{},
		UnknownPaths:            []string{},
		UnknownPathDispositions: []UnknownPathDisposition{},
		KnownPaths:              []string{},
		DeltaSessionID:          nil,
		DeltaAppendCommand:      "",
		PayloadDraft:            nil,
		RequiredAgentFields:     []string{},
		RecommendedNextCommand:  NextBlocked,
		FinalizerPolicy:         finalizerPolicy(),
		Warnings:                []string{},
		Errors:                  []string{message},
	}
}

func unknownPathDispositions(changes []changespkg.Change) []UnknownPathDisposition {
	out := []UnknownPathDisposition{}
	for _, change := range changes {
		if change.KnownToRuntime {
			continue
		}
		out = append(out, UnknownPathDisposition{
			Path:                  change.Path,
			ChangeLevel:           change.ChangeLevel,
			AllowedDispositions:   append([]string{}, allowedUnknownDispositions...),
			AgentDisposition:      nil,
			RequiredAgentDecision: true,
			PlannerReason:         append([]string{}, change.Reason...),
		})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Path < out[j].Path })
	return out
}

func knownPaths(changes []changespkg.Change) []string {
	out := []string{}
	for _, change := range changes {
		if change.KnownToRuntime {
			out = append(out, change.Path)
		}
	}
	sort.Strings(out)
	return out
}

func includedChangedPaths(changes []changespkg.Change) []string {
	out := []string{}
	for _, change := range changes {
		out = append(out, change.Path)
	}
	sort.Strings(out)
	return out
}

func requiredAgentFields(dispositions []UnknownPathDisposition) []string {
	fields := []string{"verification", "behavior_surfaces"}
	if len(dispositions) > 0 {
		fields = append(fields, "unknown_path_dispositions")
	}
	return fields
}

func finalizerPolicy() map[string]string {
	return map[string]string{
		"ready":           "clean_closeout_after_verification",
		"no_op":           "clean_closeout_when_no_project_mutation",
		"partial_refresh": "report_partial_and_minimal_live_reads",
		"needs_rebuild":   "route_map_scan_then_map_build",
		"blocked":         "report_blocker_or_mark_dirty_when_no_useful_update_recorded",
	}
}

func blockedNextAction(next string) string {
	if next == "needs_rebuild" {
		return NextRouteMapScanBuild
	}
	if next == "" {
		return NextBlocked
	}
	return next
}

func payloadPath(explicit string, workflow string, head string) string {
	if strings.TrimSpace(explicit) != "" {
		return filepath.ToSlash(strings.TrimSpace(explicit))
	}
	suffix := "working-tree"
	if strings.TrimSpace(head) != "" {
		suffix = strings.TrimSpace(head)
		if len(suffix) > 12 {
			suffix = suffix[:12]
		}
	}
	name := workflow + "-" + suffix + ".json"
	return filepath.ToSlash(filepath.Join(".specify", "project-cognition", "updates", name))
}

func deltaAppendDraft(sessionID string, workflow string, changed []string, requiredFields []string) *DeltaAppendDraft {
	prefix := []string{"project-cognition", "delta", "append", "--session", sessionID, "--event-type", "workflow_closeout", "--origin-command", workflow, "--phase", "closeout"}
	for _, path := range changed {
		prefix = append(prefix, "--changed-path", path)
	}
	return &DeltaAppendDraft{
		EventType:              "workflow_closeout",
		OriginCommand:          workflow,
		Phase:                  "closeout",
		ChangedPaths:           append([]string{}, changed...),
		RequiredAgentFields:    append([]string{}, requiredFields...),
		RequiredEvidenceResult: "passed",
		ArgvPrefix:             prefix,
		ArgvPlaceholders:       []string{"--verification", "<agent-owned passing verification evidence>", "--format", "json"},
	}
}
```

- [ ] **Step 2: Run package tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/closeout
Pop-Location
```

Expected: pass.

- [ ] **Step 3: Run existing update adoption regression**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/update -run TestRunUpdateAdoptsVerifiedUnindexedPath -count=1
Pop-Location
```

Expected: pass. This proves the planner package did not break verified new-path adoption.

- [ ] **Step 4: Commit runtime planner**

```powershell
git add tools/project-cognition/internal/closeout/plan.go tools/project-cognition/internal/closeout/plan_test.go
git commit -m "feat: add project cognition closeout planner"
```

---

### Task 3: CLI Command Surface

**Files:**
- Modify: `tools/project-cognition/internal/cli/cli.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Add failing CLI tests**

Append these tests near the existing update/changes CLI tests in `tools/project-cognition/internal/cli/cli_test.go`:

```go
func TestRootHelpListsCloseoutPlan(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"--help"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	if !strings.Contains(stdout.String(), "closeout-plan") {
		t.Fatalf("help = %q, want closeout-plan", stdout.String())
	}
}

func TestCloseoutPlanCommandEmitsPayloadDraft(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	initCLIGit(t, root)
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package main\n\nfunc main() {}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"closeout-plan",
		"--workflow", "implement",
		"--payload-path", ".specify/project-cognition/updates/cli-test.json",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}

	var result map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result["workflow"] != "sp-implement" {
		t.Fatalf("workflow = %#v", result["workflow"])
	}
	if result["update_mode"] != "payload_file" {
		t.Fatalf("update_mode = %#v", result["update_mode"])
	}
	if result["payload_draft"] == nil {
		t.Fatalf("payload = %#v, want payload_draft", result)
	}
	updateArgv, ok := result["update_argv"].([]any)
	if !ok || len(updateArgv) == 0 {
		t.Fatalf("update_argv = %#v", result["update_argv"])
	}
}

func TestCloseoutPlanCommandEmitsDeltaSessionMode(t *testing.T) {
	root := setupReadyMinimalCLIRuntime(t)
	initCLIGit(t, root)
	if err := os.WriteFile(filepath.Join(root, "src", "app.go"), []byte("package main\n\nfunc main() {}\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{
		"closeout-plan",
		"--workflow", "sp-quick",
		"--delta-session", "D-cli",
		"--format", "json",
	}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}

	var result map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if result["update_mode"] != "delta_session" {
		t.Fatalf("payload = %#v, want delta_session mode", result)
	}
	if result["delta_session_id"] != "D-cli" {
		t.Fatalf("delta_session_id = %#v", result["delta_session_id"])
	}
	if result["delta_append_draft"] == nil {
		t.Fatalf("delta_append_draft = %#v", result["delta_append_draft"])
	}
	updateArgv, ok := result["update_argv"].([]any)
	if !ok || len(updateArgv) == 0 {
		t.Fatalf("update_argv = %#v", result["update_argv"])
	}
}
```

- [ ] **Step 2: Run CLI tests and confirm failure**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/cli -run "TestRootHelpListsCloseoutPlan|TestCloseoutPlanCommand" -count=1
Pop-Location
```

Expected: fail because `closeout-plan` is not dispatched.

- [ ] **Step 3: Wire `closeout-plan` into `cli.go`**

In `tools/project-cognition/internal/cli/cli.go`, add the import:

```go
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/closeout"
```

Add this switch case after the `changes` case:

```go
	case "closeout-plan":
		return closeoutPlanCommand(args[1:], stdout, stderr, paths)
```

Update `printHelp` so the command list contains `closeout-plan` immediately after `changes`:

```go
	fmt.Fprintln(w, "Commands: status, check, init-empty, generate-ignore, mark-dirty, clear-dirty, record-refresh, complete-refresh, refresh-topics, validate-scan, validate-build, build-from-scan, import-scan, rebuild-from-scan, publish-runtime-metadata, changes, closeout-plan, update, lexicon, query, compass, expand, discover, read, doctor, rebuild, delta")
```

Add this function after `changesCommand`:

```go
func closeoutPlanCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("closeout-plan", flag.ContinueOnError)
	fs.SetOutput(stderr)
	var changed stringList
	fs.Var(&changed, "changed-path", "Explicit changed path")
	fs.Var(&changed, "changed-paths", "Explicit changed path")
	workflow := fs.String("workflow", "", "Workflow name or alias")
	reason := fs.String("reason", "workflow-finalize", "Update reason")
	intent := fs.String("intent", "", "Agent intent")
	since := fs.String("since", "", "Baseline commit")
	head := fs.String("head", "", "Head commit")
	payloadPath := fs.String("payload-path", "", "Recommended payload path")
	deltaSession := fs.String("delta-session", "", "Delta session id")
	includeWorkingTree := fs.Bool("include-working-tree", true, "Include working tree changes")
	includeUntracked := fs.Bool("include-untracked", true, "Include untracked paths")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := closeout.Run(paths, closeout.Input{
		Workflow:           *workflow,
		Reason:             *reason,
		Intent:             *intent,
		ExplicitPaths:      changed,
		Since:              *since,
		Head:               *head,
		PayloadPath:        *payloadPath,
		DeltaSessionID:     *deltaSession,
		IncludeWorkingTree: *includeWorkingTree,
		IncludeUntracked:   *includeUntracked,
	})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}
```

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/cli -run "TestRootHelpListsCloseoutPlan|TestCloseoutPlanCommand" -count=1
Pop-Location
```

Expected: pass.

- [ ] **Step 5: Run project-cognition package tests touched so far**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/closeout ./internal/cli ./internal/changes ./internal/update
Pop-Location
```

Expected: pass.

- [ ] **Step 6: Commit CLI command surface**

```powershell
git add tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/cli/cli_test.go
git commit -m "feat: expose closeout planner command"
```

---

### Task 4: Runtime Compatibility and Installers

**Files:**
- Modify: `src/specify_cli/project_cognition_runtime.py`
- Modify: `tests/test_project_cognition_runtime_install.py`
- Modify: `tools/project-cognition/install.sh`
- Modify: `tools/project-cognition/install.ps1`

- [ ] **Step 1: Add failing Python compatibility tests**

In `tests/test_project_cognition_runtime_install.py`, update `test_project_cognition_required_commands_include_runtime_commands` with:

```python
    assert "closeout-plan" in project_cognition_runtime.REQUIRED_COMMANDS
```

Add these tests near the existing `_binary_supports_required_commands` tests:

```python
def test_project_cognition_binary_support_requires_closeout_plan(monkeypatch, tmp_path: Path):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, "
            "update, lexicon, compass, expand, delta\n"
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


def test_project_cognition_binary_support_requires_closeout_plan_flags(monkeypatch, tmp_path: Path):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, "
            "closeout-plan, update, lexicon, compass, expand, delta\n"
        )
        stderr = ""

    class UpdateHelpResult:
        stdout = "Usage of update:\n  -payload-file value\n  -verification value\n"
        stderr = ""

    class LexiconHelpResult:
        stdout = "Usage of lexicon:\n  -mode value\n"
        stderr = ""

    class CompassHelpResult:
        stdout = "Usage of compass:\n  -semantic-intake-file value\n  -query-plan-file value\n"
        stderr = ""

    class ExpandHelpResult:
        stdout = "Usage of expand:\n  -section value\n"
        stderr = ""

    class DeltaAppendHelpResult:
        stdout = "Usage of delta append:\n  -verification value\n  -generated-surface value\n"
        stderr = ""

    class CloseoutHelpResult:
        stdout = "Usage of closeout-plan:\n  -workflow value\n"
        stderr = ""

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[1:] == ["--help"]:
            return RootHelpResult()
        if command[1:] == ["update", "--help"]:
            return UpdateHelpResult()
        if command[1:] == ["lexicon", "--help"]:
            return LexiconHelpResult()
        if command[1:] == ["compass", "--help"]:
            return CompassHelpResult()
        if command[1:] == ["expand", "--help"]:
            return ExpandHelpResult()
        if command[1:] == ["delta", "append", "--help"]:
            return DeltaAppendHelpResult()
        if command[1:] == ["closeout-plan", "--help"]:
            return CloseoutHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False
    assert calls[-1] == [str(binary), "closeout-plan", "--help"]


def test_project_cognition_install_scripts_verify_closeout_plan_flags():
    shell_script = Path("tools/project-cognition/install.sh").read_text(encoding="utf-8")
    powershell_script = Path("tools/project-cognition/install.ps1").read_text(encoding="utf-8")

    assert "closeout-plan --help" in shell_script
    assert "-workflow" in shell_script
    assert "-delta-session" in shell_script
    assert '@("closeout-plan", "--help")' in powershell_script
    assert "-workflow" in powershell_script
    assert "-delta-session" in powershell_script
```

- [ ] **Step 2: Run Python tests and confirm failure**

Run:

```powershell
pytest tests/test_project_cognition_runtime_install.py -q
```

Expected: fail on the missing required command and installer checks.

- [ ] **Step 3: Update Python runtime compatibility**

In `src/specify_cli/project_cognition_runtime.py`, add `"closeout-plan"` to `REQUIRED_COMMANDS` immediately after `"changes"`:

```python
    "changes",
    "closeout-plan",
    "lexicon --mode",
```

After the delta append help check in `_binary_supports_required_commands`, replace the final return with:

```python
    if "-verification" not in delta_append_output or "-generated-surface" not in delta_append_output:
        return False

    try:
        closeout_result = subprocess.run(
            [str(binary), "closeout-plan", "--help"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    closeout_output = f"{closeout_result.stdout}\n{closeout_result.stderr}"
    return "-workflow" in closeout_output and "-delta-session" in closeout_output
```

- [ ] **Step 4: Update shell installers**

In `tools/project-cognition/install.sh`, after the delta append check, add:

```bash
closeout_plan_help="$("$target" closeout-plan --help 2>&1 || true)"
if [[ "$closeout_plan_help" != *"-workflow"* || "$closeout_plan_help" != *"-delta-session"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required closeout-plan flags." >&2
  echo "Expected 'project-cognition closeout-plan --help' to include -workflow and -delta-session." >&2
  exit 1
fi
```

In `tools/project-cognition/install.ps1`, after the delta append check, add:

```powershell
$closeoutPlanHelp = Get-NativeHelpOutput -Command $target -Arguments @("closeout-plan", "--help")
if (($closeoutPlanHelp -notmatch '-workflow') -or ($closeoutPlanHelp -notmatch '-delta-session')) {
    Write-Host "Error: downloaded project-cognition binary is missing required closeout-plan flags."
    Write-Host "Expected 'project-cognition closeout-plan --help' to include -workflow and -delta-session."
    exit 1
}
```

- [ ] **Step 5: Run compatibility tests**

Run:

```powershell
pytest tests/test_project_cognition_runtime_install.py -q
```

Expected: pass.

- [ ] **Step 6: Commit compatibility changes**

```powershell
git add src/specify_cli/project_cognition_runtime.py tests/test_project_cognition_runtime_install.py tools/project-cognition/install.sh tools/project-cognition/install.ps1
git commit -m "feat: require closeout planner runtime support"
```

---

### Task 5: Generated Workflow Guidance

**Files:**
- Modify: `templates/command-partials/common/inline-project-cognition-update.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add failing template assertions**

In `tests/test_alignment_templates.py`, extend `test_inline_cognition_closeout_partial_has_agent_owned_payload_fields` with:

```python
    assert "project-cognition closeout-plan --workflow" in shared
    assert "--delta-session" in shared
    assert "update_mode=delta_session" in shared
    assert "update_mode=payload_file" in shared
    assert "unknown_path_dispositions" in shared
    assert "agent_disposition" in shared
    assert "blocking_known_unknown" in shared
```

In `test_inline_cognition_closeout_shared_surfaces_are_consistent`, add:

```python
        assert "closeout-plan" in content, path
        assert "unknown_path_dispositions" in content, path
```

- [ ] **Step 2: Run template tests and confirm failure**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_inline_cognition_closeout_partial_has_agent_owned_payload_fields tests/test_alignment_templates.py::test_inline_cognition_closeout_shared_surfaces_are_consistent -q
```

Expected: fail because the templates still describe direct delta/payload update without the planner.

- [ ] **Step 3: Replace shared inline closeout partial**

Replace `templates/command-partials/common/inline-project-cognition-update.md` with:

````markdown
### Inline Project Cognition Update

Workflow-owned mutation closeout is not an external map-maintenance handoff and is not external map maintenance. It is the workflow-local form of `{{invoke:map-update}}`. If this workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, shared surfaces, or behavior-bearing docs, closeout MUST run inline project cognition update for the workflow-owned changed paths and affected surfaces before claiming clean completion.

Call the planner first:

```text
project-cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --format json
```

When `DELTA_SESSION_ID` exists, pass it into the planner:

```text
project-cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --delta-session "$DELTA_SESSION_ID" --format json
```

Consume `workflow_canonical`, `update_mode`, `payload_draft`, `required_agent_fields`, `ignored_paths`, `unknown_paths`, `unknown_path_dispositions`, `delta_append_draft`, display-only `delta_append_command`, `update_argv`, display-only `update_command`, `recommended_next_command`, and `finalizer_policy`.

Before running `update`, fill every required agent-owned field from live evidence from this workflow:

- `verification`
- `behavior_surfaces`
- `generated_surfaces`
- `state_contracts`
- `known_unknowns`
- `confidence_notes`
- `user_decisions`
- `boundary`

For each `unknown_path_dispositions[]` item, set `agent_disposition` to exactly one allowed value:

- `adoptable`: verified new path inside this workflow-owned scope; it may be recorded in changed/scope paths and must not become a blocking known unknown.
- `review_only`: path informed review but is not adopted into changed coverage.
- `ignored`: path remains excluded and must not enter payloads, records, route indexes, evidence, aliases, or minimal live reads.
- `blocking_known_unknown`: record it as a known unknown and report partial or blocked cognition closeout.

If `update_mode=delta_session`, complete `delta_append_draft.argv_prefix` with agent-owned repeatable flags such as `--behavior-surface`, `--generated-surface`, `--verification`, and accepted `--known-unknown` values from `delta_append_draft.argv_placeholders`. Then append the delta event and run `update_argv`. `delta_append_command` and `update_command` are display-only placeholders, not execution strings.

If `update_mode=payload_file`, write the completed `payload_draft` to the planner's `payload_path`. Then run `update_argv`. `update_command` is a display-only placeholder, not an execution string.

For compatibility with worker handoffs and delta packets, the runtime also accepts `verification_evidence` as an alias for `verification` and `generated_surface_notes` as an alias for `generated_surfaces`. Verification evidence may be an array of objects (`command`, `result`, `artifact`) or an array of command-result strings, but clean closeout still requires passing verification evidence; failed verification cannot produce a clean `ready` closeout.

Clean closeout keys on `result_state`, not `status=ok`, `update_id`, `last_update_id`, or freshness alone:

- `ready` or `no_op`: project cognition closeout may be clean when ordinary verification also passed.
- `partial_refresh`: useful update data was written, but the final workflow state must report partial cognition closeout and the returned `minimal_live_reads`.
- `needs_rebuild`: report the exact rebuild condition and route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- `blocked`: report the runtime or validation blocker and the exact recovery command.
- `recorded`: legacy recorded-only output; treat it as partial or blocked, never as clean completion.

Use `{{specify-subcmd:project-cognition mark-dirty --reason "workflow-closeout-failed" --format json}}` only when inline update cannot complete: when the planner or update command is unavailable, cannot record useful update data, cannot identify workflow-owned scope, or cannot be trusted because verification/workflow completion is not trustworthy. Dirty only when inline update cannot complete.

sp-map-update is for manual/external maintenance and follow-up repair. `{{invoke:map-update}}` remains the external/manual workflow for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. It is not routine cleanup for changes this workflow just made. If `sp-map-update` already ran `project-cognition update --reason map-update` for the same changed paths, do not run a second `workflow-finalize` closeout update for those paths.
````

- [ ] **Step 4: Update passive skills**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, replace the existing inline update bullets around the workflow-owned mutation closeout section with this wording:

```markdown
- Workflow-owned mutation closeout is not an external map-maintenance handoff. If the active workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, or behavior-bearing docs, closeout must run `project-cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --format json` before recording inline project cognition update data.
- When `DELTA_SESSION_ID` exists, pass `--delta-session "$DELTA_SESSION_ID"` to `closeout-plan`. Follow `update_mode=delta_session` by completing `delta_append_draft.argv_prefix` with agent-owned evidence placeholders, appending the workflow closeout delta event, then running structured `update_argv`; `recommended_next_command` may be `fill_delta_append_draft_then_update` while evidence is still missing. Follow `update_mode=payload_file` by writing the completed `payload_draft`, then running structured `update_argv`. `update_command` and `delta_append_command` are display-only placeholders, not execution strings.
- Before update recording, resolve `unknown_path_dispositions` by setting `agent_disposition` to `adoptable`, `review_only`, `ignored`, or `blocking_known_unknown`. Verified `adoptable` paths do not become blocking `known_unknowns`. Only `blocking_known_unknown` dispositions become payload or delta known unknowns.
- Clean closeout keys on `result_state`, not `status=ok`, `update_id`, `last_update_id`, or freshness alone; `recorded` is legacy recorded-only partial/blocked output. Use `project-cognition mark-dirty --reason "workflow-closeout-failed" --format json` only when planner/update is unavailable, fails before recording useful update data, cannot safely identify workflow-owned scope, is blocked by runtime state, or verification/workflow completion is not trustworthy.
```

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, replace the existing inline update bullets with the same planner-first contract.

- [ ] **Step 5: Run template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_inline_cognition_closeout_partial_has_agent_owned_payload_fields tests/test_alignment_templates.py::test_inline_cognition_closeout_shared_surfaces_are_consistent tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py -q
```

Expected: pass.

- [ ] **Step 6: Commit generated workflow guidance**

```powershell
git add templates/command-partials/common/inline-project-cognition-update.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/test_alignment_templates.py
git commit -m "feat: route workflow closeout through planner guidance"
```

---

### Task 6: Docs, Handbook, and Release Text

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/installation.md`
- Modify: `.github/workflows/release.yml`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_runtime_handbook_contract.py`

- [ ] **Step 1: Add failing docs assertions**

In `tests/test_specify_guidance_docs.py`, extend `test_readme_documents_inline_project_cognition_closeout`:

```python
    assert "project-cognition closeout-plan --workflow" in readme
    assert "update_mode=delta_session" in readme
    assert "update_mode=payload_file" in readme
    assert "unknown_path_dispositions" in readme
```

In `test_quickstart_skill_map_and_guidance_use_canonical_names_not_claude_syntax`, add:

```python
    assert "project-cognition closeout-plan --workflow" in quickstart_lower
    assert "unknown_path_dispositions" in quickstart_lower
```

In `tests/test_runtime_handbook_contract.py`, extend `test_handbook_project_cognition_guidance_matches_runtime_contract` with:

```python
    assert "project-cognition closeout-plan --workflow" in lowered
    assert "unknown_path_dispositions" in lowered
    assert "update_mode=delta_session" in lowered
    assert "update_mode=payload_file" in lowered
```

- [ ] **Step 2: Run docs tests and confirm failure**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py::test_readme_documents_inline_project_cognition_closeout tests/test_specify_guidance_docs.py::test_quickstart_skill_map_and_guidance_use_canonical_names_not_claude_syntax tests/test_runtime_handbook_contract.py::test_handbook_project_cognition_guidance_matches_runtime_contract -q
```

Expected: fail on missing planner wording.

- [ ] **Step 3: Update docs with planner-first wording**

In each of `README.md`, `PROJECT-HANDBOOK.md`, `templates/project-handbook-template.md`, `docs/quickstart.md`, and `docs/installation.md`, replace the direct inline closeout wording with this compact contract, adjusted only for surrounding grammar:

```markdown
Workflow-owned mutation closeout is planner-first: source-changing `sp-*` workflows run `project-cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --format json`, passing `--delta-session "$DELTA_SESSION_ID"` when a delta session exists. The planner returns `update_mode=delta_session` or `update_mode=payload_file`, required agent-owned fields, `unknown_path_dispositions`, and the exact update command to run after the agent fills verification and behavior evidence. Verified `adoptable` unknown paths can be recorded without becoming blocking `known_unknowns`; only `blocking_known_unknown` dispositions become payload or delta known unknowns. Clean closeout still gates on `result_state=ready` or `result_state=no_op`, not `status=ok`, `update_id`, `last_update_id`, or freshness alone.
```

In `.github/workflows/release.yml`, update the project-cognition release note paragraph to:

```markdown
Generated project cognition workflows require the standalone `project-cognition` binary. This release publishes prebuilt binaries for Windows, Linux, and macOS. The runtime includes the default compass/expand navigation commands, the advanced lexicon/query planning commands, and `closeout-plan` for planner-first workflow-owned mutation closeout.
```

- [ ] **Step 4: Run docs tests**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py::test_readme_documents_inline_project_cognition_closeout tests/test_specify_guidance_docs.py::test_quickstart_skill_map_and_guidance_use_canonical_names_not_claude_syntax tests/test_runtime_handbook_contract.py::test_handbook_project_cognition_guidance_matches_runtime_contract -q
```

Expected: pass.

- [ ] **Step 5: Commit docs and release wording**

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md docs/quickstart.md docs/installation.md .github/workflows/release.yml tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py
git commit -m "docs: document planner-first cognition closeout"
```

---

### Task 7: End-to-End Verification and Release Readiness

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run Go tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./...
Pop-Location
```

Expected: pass.

- [ ] **Step 2: Run focused Python regression tests**

Run:

```powershell
pytest tests/test_project_cognition_runtime_install.py tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py -q
```

Expected: pass.

- [ ] **Step 3: Build the runtime binary and verify command help**

Run:

```powershell
Push-Location tools/project-cognition
go build -o project-cognition-test.exe .
.\project-cognition-test.exe --help
.\project-cognition-test.exe closeout-plan --help
Remove-Item .\project-cognition-test.exe
Pop-Location
```

Expected: root help includes `closeout-plan`; closeout help includes `-workflow` and `-delta-session`.

- [ ] **Step 4: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 5: Stop on verification failures**

If a verification command fails, stop the plan execution, inspect the exact failing command output, make the smallest fix, rerun the failed command, then rerun Task 7 from Step 1. Do not publish or report release readiness while any Task 7 command is failing.

- [ ] **Step 6: Prepare release command after merge**

After these implementation commits are merged to `main`, publish a new release because the project-cognition command surface changed. Use the repository's existing release workflow:

```powershell
gh workflow run release.yml -f tag=v0.5.13
```

After the release completes, verify the latest release binary exposes the new command:

```powershell
$tmp = Join-Path $env:TEMP "project-cognition-v0.5.13.exe"
Invoke-WebRequest -Uri "https://github.com/chenziyang110/spec-kit-plus/releases/download/v0.5.13/project-cognition-windows-amd64.exe" -OutFile $tmp
& $tmp --version
& $tmp closeout-plan --help
Remove-Item $tmp
```

Expected: version prints `v0.5.13`; closeout help includes `-workflow` and `-delta-session`.

---

## Self-Review Checklist

- Spec coverage:
  - `closeout-plan` command surface: Tasks 1-3.
  - Payload and delta modes: Tasks 1-3 and 5.
  - Unknown path disposition queue and verified adoption preservation: Tasks 1-2 and 5.
  - Workflow alias canonicalization: Tasks 1-2.
  - Runtime compatibility, installers, and release assets: Tasks 4 and 7.
  - Generated workflow guidance and docs: Tasks 5-6.

- Verification commands:
  - Go: `go test ./...` in `tools/project-cognition`.
  - Python: focused pytest suite in Task 7.
  - Binary: `go build` plus `closeout-plan --help`.
  - Git hygiene: `git diff --check`.

- Commit boundaries:
  - Runtime tests.
  - Runtime implementation.
  - CLI command.
  - Compatibility/installers.
  - Generated workflow guidance.
  - Docs/release wording.
  - Verification-only fixes only when needed.

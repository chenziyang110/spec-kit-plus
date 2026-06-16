# Project Cognition Compass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `project-cognition compass` and `project-cognition expand` so generated workflows get a compact, coverage-aware first evidence route by default while retaining explicit expansion and the advanced `lexicon -> semantic_intake -> query` path.

**Architecture:** Keep the current schema v2 graph and alias runtime as the data source, but add a new compass packet layer in the Go `query` package. The compass layer classifies graph candidates into route lanes, coverage diagnostics, and expansion-only sections; generated workflows consume top-level `minimal_live_reads` first, then read lane-level `first_pass_paths` reasons for why those files are first-pass evidence.

**Tech Stack:** Go `project-cognition` runtime, SQLite-backed schema v2 store, Python launcher/runtime installer, Markdown command templates/passive skills, Go unit tests, pytest template and integration tests.

---

## Reference Spec

- `docs/superpowers/specs/2026-06-15-project-cognition-compass-architecture-design.md`
- Related: `docs/superpowers/specs/2026-06-12-agent-owned-cognition-normalization-design.md`
- Related: `docs/superpowers/specs/2026-06-03-cognition-intake-experience-alignment-implementation.md`

## Non-Negotiable Contracts

- Runtime readiness values stay in the existing enum: `query_ready`, `review`, `needs_rebuild`, `blocked`, `unsupported_runtime`.
- `compass_state` carries compass-specific advice such as `usable_with_review`, `needs_semantic_intake`, `needs_expansion_before_fix_claim`, and `stale_expansion`.
- `--query` is mechanical draft mode. It may rank and group, but it labels facets as `mechanical_query_facets` and never claims agent-owned semantic coverage.
- `--semantic-intake-file` and `--query-plan-file` are precision modes. Strict facet coverage only applies to those agent-authored inputs.
- Top-level `minimal_live_reads` is the first workflow read list. Lane-level `first_pass_paths` explains why each path is first-pass evidence.
- `minimal_live_reads` and `first_pass_paths` are not final edit scope.
- Broad fallback suppression is structural. Do not match display titles such as `Coverage paths not in existing nodes`.
- Expansion is normal continuation, not failure. Stale expansion returns structured recovery guidance instead of stale route material.

## File Structure

Runtime:

- Create `tools/project-cognition/internal/query/compass.go`
  - Own compass payload types, route candidate classification, mechanical/precision facet accounting, lane construction, top-level `minimal_live_reads`, and expansion reference creation.
- Create `tools/project-cognition/internal/query/expansion.go`
  - Own expansion bundle storage, section loading, stale/missing expansion recovery payloads, and safe expansion IDs.
- Create `tools/project-cognition/internal/query/compass_test.go`
  - Runtime tests for compact compass packets, mechanical draft mode, precision mode, fallback suppression, CJK agent normalization, and output budget behavior.
- Create `tools/project-cognition/internal/query/expansion_test.go`
  - Runtime tests for section expansion, stale generation/version behavior, and missing expansion recovery.
- Modify `tools/project-cognition/internal/query/query.go`
  - Fix the existing generation-mismatch readiness drift from `ambiguous` to `review`.
  - Reuse existing helpers such as `NormalizePlan`, `termsFrom`, `newRankedConceptCandidate`, `normalizePaths`, and `uniqueStrings` from the same package.
- Modify `tools/project-cognition/internal/query/lexicon.go`
  - Reuse `AgentNormalizationDiagnostic` from compass packets.
  - Keep `CandidateUniverseVersion = 1` as the expansion freshness contract.
- Modify `tools/project-cognition/internal/cli/cli.go`
  - Add `compass` and `expand` command routing.
  - Add command help support for root, `compass --help`, and `expand --help`.
- Modify `tools/project-cognition/internal/cli/cli_test.go`
  - Add command-surface tests and CLI JSON smoke tests.
- Modify `tools/project-cognition/install.sh`
- Modify `tools/project-cognition/install.ps1`
  - Verify release binaries expose `compass` and `expand`.

Python launcher/runtime:

- Modify `src/specify_cli/project_cognition_runtime.py`
  - Add `compass` and `expand` to compatibility probes.
- Modify `src/specify_cli/launcher.py` only if launcher rendering fails for quoted `--query-plan-file` or `--semantic-intake-file` invocations.
- Modify `tests/test_project_cognition_runtime_install.py`
- Modify `tests/test_project_cognition_launcher_rendering.py`

Workflow and generated guidance:

- Modify `src/specify_cli/integrations/base.py`
  - Update generated integration advisory gates to call `project-cognition compass` by default.
  - Preserve the advanced `lexicon -> semantic_intake -> query` route as the precision/escalation path.
- Modify shared command partials:
  - `templates/command-partials/common/context-loading-gradient.md`
  - `templates/command-partials/common/planning-context-loading-gradient.md`
  - `templates/command-partials/common/navigation-check.md`
- Modify passive skills:
  - `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
  - `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify direct command templates found by the sweep, expected at least:
  - `templates/commands/analyze.md`
  - `templates/commands/checklist.md`
  - `templates/commands/clarify.md`
  - `templates/commands/debug.md`
  - `templates/commands/deep-research.md`
  - `templates/commands/fast.md`
  - `templates/commands/implement.md`
  - `templates/commands/map-build.md`
  - `templates/commands/plan.md`
  - `templates/commands/prd-scan.md`
  - `templates/commands/quick.md`
  - `templates/commands/specify.md`
  - `templates/commands/tasks.md`
- Modify `templates/project-handbook-template.md`
- Modify `README.md`
- Modify `PROJECT-HANDBOOK.md`

Tests:

- Modify `tests/test_map_runtime_template_guidance.py`
- Modify `tests/test_alignment_templates.py`
- Modify focused integration rendering tests only when the shared `base.py` change is not covered by the two tests above.

---

## Task 1: Fix Existing Readiness Drift Before Adding Compass

**Files:**
- Modify: `tools/project-cognition/internal/query/query.go`
- Modify: `tools/project-cognition/internal/query/query_test.go`

- [ ] **Step 1: Write the failing generation-mismatch readiness test**

In `tools/project-cognition/internal/query/query_test.go`, update `TestRunReportsLexiconGenerationMismatch` so it asserts the current runtime enum. Replace the readiness assertion block with:

```go
if payload.Readiness != rt.ReviewReadiness {
	t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.ReviewReadiness)
}
if payload.RecommendedNextAction != "rerun_project_cognition_lexicon" {
	t.Fatalf("RecommendedNextAction = %q", payload.RecommendedNextAction)
}
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query -run TestRunReportsLexiconGenerationMismatch -count=1
Pop-Location
```

Expected: FAIL because `generationMismatchPayload` currently returns `Readiness: "ambiguous"`.

- [ ] **Step 3: Change the implementation**

In `tools/project-cognition/internal/query/query.go`, edit `generationMismatchPayload`:

```go
Readiness:             rt.ReviewReadiness,
RecommendedNextAction: "rerun_project_cognition_lexicon",
```

Do not introduce a new readiness value. Keep `lexicon_generation_mismatch` in `MissingCoverage`.

- [ ] **Step 4: Run the focused test and query package tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query -run TestRunReportsLexiconGenerationMismatch -count=1
go test ./internal/query -count=1
Pop-Location
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tools/project-cognition/internal/query/query.go tools/project-cognition/internal/query/query_test.go
git commit -m "fix: keep project cognition query readiness in runtime enum"
```

---

## Task 2: Add Compass Payload Types And Mechanical Draft Tests

**Files:**
- Create: `tools/project-cognition/internal/query/compass.go`
- Create: `tools/project-cognition/internal/query/compass_test.go`

- [ ] **Step 1: Add the failing compact-packet test**

Create `tools/project-cognition/internal/query/compass_test.go` with package `query`. Add this test and helper fixture:

```go
package query

import (
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

func TestCompassQueryDraftReturnsCompactPacketAndTopLevelMinimalReads(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent: "debug",
		Query:  "切模型 failed runtimeOverride deepseek 方块 屏幕小",
	})
	if err != nil {
		t.Fatal(err)
	}

	if payload.Mode != "compass" {
		t.Fatalf("Mode = %q, want compass", payload.Mode)
	}
	if payload.Readiness != rt.ReadyReadiness {
		t.Fatalf("Readiness = %q, want %q", payload.Readiness, rt.ReadyReadiness)
	}
	if payload.FacetSource != "mechanical_query_facets" {
		t.Fatalf("FacetSource = %q, want mechanical_query_facets", payload.FacetSource)
	}
	if len(payload.EvidenceLanes) < 2 {
		t.Fatalf("EvidenceLanes = %#v, want provider/runtime and UI readability lanes", payload.EvidenceLanes)
	}
	if len(payload.MinimalLiveReads) == 0 || len(payload.MinimalLiveReads) > 15 {
		t.Fatalf("MinimalLiveReads = %#v, want compact non-empty list", payload.MinimalLiveReads)
	}
	wantReads := dedupeCompassLanePaths(payload.EvidenceLanes)
	if !equalStrings(payload.MinimalLiveReads, wantReads) {
		t.Fatalf("MinimalLiveReads = %#v, want lane path union %#v", payload.MinimalLiveReads, wantReads)
	}
	if compassLaneTitleContains(payload.EvidenceLanes, "Runtime Surface Index") {
		t.Fatalf("fallback title appeared as route lane: %#v", payload.EvidenceLanes)
	}
	if !compassDiagnosticsContain(payload.CoverageDiagnostics, "broad_fallback_suppressed") {
		t.Fatalf("CoverageDiagnostics = %#v, want broad fallback diagnostic", payload.CoverageDiagnostics)
	}
	if payload.QueryFingerprint == "" {
		t.Fatalf("QueryFingerprint is empty")
	}
}

func seedCompassModelSwitchGraph(t *testing.T, paths rt.Paths) {
	t.Helper()
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-compass-model-switch",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{
			{ID: "E-model-selector", SourceKind: "source", SourcePath: "desktop/src/components/controls/ModelSelector.tsx", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-model"},
			{ID: "E-ws-handler", SourceKind: "source", SourcePath: "src/server/ws/handler.ts", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-ws"},
			{ID: "E-fonts", SourceKind: "source", SourcePath: "desktop/src/styles/global.css", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-fonts"},
			{ID: "E-window", SourceKind: "source", SourcePath: "desktop/src-tauri/tauri.conf.json", CommitSHA: "abc123", Extractor: "test", ContentHash: "hash-window"},
		},
		Nodes: []store.NodeImport{
			{
				ID: "N-provider-runtime", Type: "capability", Title: "Provider Runtime Override", Confidence: "verified", EvidenceIDs: []string{"E-model-selector", "E-ws-handler"},
				Attrs: map[string]any{
					"aliases":             []any{"runtimeOverride", "provider model switch", "deepseek model id", "CLI startup failure"},
					"owner":               "runtime-session",
					"domain":              "provider-runtime",
					"verification_hints":  []any{"server runtime override rollback regression"},
					"before_fix_claim":    []any{"Confirm provider registry is not the owner.", "Confirm failed switch does not poison next startup truth."},
					"followup_surfaces":   []any{"provider registry", "session resume", "startup diagnostics redaction"},
				},
			},
			{
				ID: "N-ui-readability", Type: "ui", Title: "Desktop UI Readability", Confidence: "verified", EvidenceIDs: []string{"E-fonts", "E-window"},
				Attrs: map[string]any{
					"aliases":            []any{"square glyphs", "font fallback", "small viewport", "window minimum size"},
					"owner":              "desktop-shell",
					"domain":             "desktop-ui",
					"verification_hints": []any{"desktop rendering smoke test"},
					"followup_surfaces":  []any{"chat error rendering", "zoom persistence"},
				},
			},
			{
				ID: "N-fallback", Type: "coverage_fallback", Title: "Runtime Surface Index", Confidence: "low",
				Attrs: map[string]any{
					"aliases":             []any{"runtimeOverride", "deepseek", "desktop"},
					"fallback_provenance": "coverage_paths_without_existing_nodes",
					"path_count":          3000,
				},
			},
		},
		PathIndex: []store.PathIndexImport{
			{ID: "P-model-selector", Path: "desktop/src/components/controls/ModelSelector.tsx", NodeID: "N-provider-runtime", Relation: "owns", Confidence: "verified", EvidenceID: "E-model-selector"},
			{ID: "P-ws-handler", Path: "src/server/ws/handler.ts", NodeID: "N-provider-runtime", Relation: "owns", Confidence: "verified", EvidenceID: "E-ws-handler"},
			{ID: "P-fonts", Path: "desktop/src/styles/global.css", NodeID: "N-ui-readability", Relation: "owns", Confidence: "verified", EvidenceID: "E-fonts"},
			{ID: "P-window", Path: "desktop/src-tauri/tauri.conf.json", NodeID: "N-ui-readability", Relation: "owns", Confidence: "verified", EvidenceID: "E-window"},
		},
	})
}
```

Add these helper assertions in the same file:

```go
func dedupeCompassLanePaths(lanes []EvidenceLane) []string {
	values := []string{}
	for _, lane := range lanes {
		for _, path := range lane.FirstPassPaths {
			values = appendMissingCoverage(values, path.Path)
		}
	}
	return values
}

func compassLaneTitleContains(lanes []EvidenceLane, title string) bool {
	for _, lane := range lanes {
		if lane.Title == title {
			return true
		}
	}
	return false
}

func compassDiagnosticsContain(diagnostics []CoverageDiagnostic, kind string) bool {
	for _, diagnostic := range diagnostics {
		if diagnostic.Kind == kind {
			return true
		}
	}
	return false
}
```

- [ ] **Step 2: Run the focused test and confirm it fails to compile**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query -run TestCompassQueryDraftReturnsCompactPacketAndTopLevelMinimalReads -count=1
Pop-Location
```

Expected: FAIL with undefined `Compass`, `CompassInput`, `EvidenceLane`, and `CoverageDiagnostic`.

- [ ] **Step 3: Add payload types and constants**

Create `tools/project-cognition/internal/query/compass.go` with these type names and JSON fields:

```go
package query

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/store"
)

const (
	compassMode                         = "compass"
	compassFacetSourceMechanical        = "mechanical_query_facets"
	compassFacetSourceSemanticIntake    = "semantic_intake.intent_facets"
	compassFacetSourceQueryPlan         = "query_plan.intent_facets"
	compassStateUsable                  = "usable"
	compassStateUsableWithReview        = "usable_with_review"
	compassStateNeedsSemanticIntake     = "needs_semantic_intake"
	compassStateNeedsExpansionBeforeFix = "needs_expansion_before_fix_claim"
	compassStateBlocked                 = "blocked"
	maxCompassLanes                     = 3
	maxCompassReads                     = 15
	maxCompassPathsPerLane              = 6
	broadFallbackPathThreshold          = 50
)

type CompassInput struct {
	Intent          string
	Query           string
	Plan            Plan
	PlanDiagnostics PlanDiagnostics
	InputMode        string
}

type CompassPayload struct {
	Readiness                string                         `json:"readiness"`
	CompassState            string                         `json:"compass_state"`
	Mode                    string                         `json:"mode"`
	FacetSource             string                         `json:"facet_source"`
	ActiveGenerationID      string                         `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion int                            `json:"candidate_universe_version"`
	QueryFingerprint        string                         `json:"query_fingerprint"`
	Summary                 string                         `json:"summary"`
	IntentFacets            []CompassIntentFacet           `json:"intent_facets"`
	EvidenceLanes           []EvidenceLane                 `json:"evidence_lanes"`
	MinimalLiveReads        []string                       `json:"minimal_live_reads"`
	CoverageDiagnostics     []CoverageDiagnostic           `json:"coverage_diagnostics"`
	ExpansionRef            ExpansionRef                   `json:"expansion_ref"`
	AgentNormalization      *AgentNormalizationDiagnostic  `json:"agent_normalization,omitempty"`
	Warnings                []string                       `json:"warnings,omitempty"`
	RepairHints             []string                       `json:"repair_hints,omitempty"`
	RecommendedNextAction   string                         `json:"recommended_next_action,omitempty"`
	BaselineKind            string                         `json:"baseline_kind,omitempty"`
}

type CompassIntentFacet struct {
	Name     string `json:"name"`
	Coverage string `json:"coverage"`
	Risk     string `json:"risk,omitempty"`
}

type EvidenceLane struct {
	ID                string          `json:"id"`
	Title             string          `json:"title"`
	Coverage          string          `json:"coverage"`
	Confidence        string          `json:"confidence"`
	FirstPassPaths    []FirstPassPath `json:"first_pass_paths"`
	VerificationHints []string        `json:"verification_hints"`
	FollowupSurfaces  []string        `json:"followup_surfaces"`
	BeforeFixClaim    []string        `json:"before_fix_claim"`
}

type FirstPassPath struct {
	Path         string `json:"path"`
	Reason       string `json:"reason"`
	EvidenceHint string `json:"evidence_hint,omitempty"`
}

type CoverageDiagnostic struct {
	Kind              string   `json:"kind"`
	Severity          string   `json:"severity"`
	Message           string   `json:"message"`
	AffectedFacets    []string `json:"affected_facets,omitempty"`
	RecommendedAction string   `json:"recommended_action"`
}

type ExpansionRef struct {
	ID                       string                          `json:"id,omitempty"`
	ActiveGenerationID       string                          `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion int                             `json:"candidate_universe_version,omitempty"`
	QueryFingerprint         string                          `json:"query_fingerprint,omitempty"`
	AvailableSections        map[string]ExpansionSectionMeta `json:"available_sections,omitempty"`
	StaleBehavior            string                          `json:"stale_behavior,omitempty"`
}

type compassCandidate struct {
	row        store.ConceptCandidateRow
	ranked     rankedConceptCandidate
	score      int
	matched    []string
	diagnostic bool
	reason     string
}
```

- [ ] **Step 4: Implement the minimal mechanical compass path**

In the same file, add `Compass`, candidate collection, fallback classification, lane construction, and fingerprint helpers. The implementation must:

- call `blockSplitBrainBaseline(paths)` first
- read `rt.ReadStatus(paths)`
- return `rt.UnsupportedLegacyPayload` only through the CLI error path; runtime function returns errors like existing `Run`
- load `store.AllActiveConceptCandidateRows`
- score rows with existing `newRankedConceptCandidate` and `scoreConceptCandidate`
- suppress fallback candidates using node type, attrs, fallback provenance, or path count
- build top-level `minimal_live_reads` from lane paths
- leave `ExpansionRef` empty in this task; Task 4 wires stored expansion bundles

Use this behavior table:

```text
status.Readiness == query_ready and input mode == query_plan      -> compass_state usable when every facet has coverage
status.Readiness == query_ready and input mode == semantic_intake -> compass_state usable when every facet has coverage
status.Readiness == query_ready and input mode == query           -> compass_state usable_with_review when at least one lane exists
agent_normalization.required == true                             -> compass_state needs_semantic_intake
no lane and at least one uncovered facet                          -> compass_state needs_expansion_before_fix_claim
status.Readiness in needs_rebuild/blocked/unsupported_runtime     -> compass_state blocked
```

Add these function signatures exactly:

```go
func Compass(paths rt.Paths, input CompassInput) (CompassPayload, error)
func compassFingerprint(input CompassInput) string
func compassFacets(input CompassInput, terms []string) ([]string, string)
func compassCandidates(rows []store.ConceptCandidateRow, terms []string) []compassCandidate
func isBroadFallbackCandidate(candidate rankedConceptCandidate) (bool, string)
func evidenceLanesFromCandidates(candidates []compassCandidate, facets []string) []EvidenceLane
func minimalReadsFromLanes(lanes []EvidenceLane) []string
func coverageForFacets(facets []string, lanes []EvidenceLane, diagnostics []CoverageDiagnostic, precision bool) []CompassIntentFacet
```

- [ ] **Step 5: Run the focused test**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query -run TestCompassQueryDraftReturnsCompactPacketAndTopLevelMinimalReads -count=1
Pop-Location
```

Expected: PASS with `QueryFingerprint` populated and `ExpansionRef` still empty. Task 4 adds the stored expansion assertion.

- [ ] **Step 6: Commit**

```powershell
git add tools/project-cognition/internal/query/compass.go tools/project-cognition/internal/query/compass_test.go
git commit -m "feat: add project cognition compass packet model"
```

---

## Task 3: Add Precision Input Semantics To Compass

**Files:**
- Modify: `tools/project-cognition/internal/query/compass.go`
- Modify: `tools/project-cognition/internal/query/compass_test.go`

- [ ] **Step 1: Add semantic-intake precision test**

Append this test to `compass_test.go`:

```go
func TestCompassSemanticIntakeUsesAgentOwnedFacets(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent: "debug",
		Query:  "切模型失败",
		InputMode: "semantic_intake",
		Plan: Plan{
			SemanticIntake: SemanticIntake{
				WorkflowIntent:      "debug",
				NormalizedQuery:     "Investigate provider runtime override failure and desktop readability.",
				IntentFacets:        []string{"provider runtime override", "desktop readability"},
				NegativeConstraints: []string{"not only provider catalog metadata"},
				AliasInterpretations: []AliasInterpretation{
					{Alias: "切模型", Meaning: "provider runtime override", Confidence: "high"},
					{Alias: "方块", Meaning: "desktop readability", Confidence: "medium"},
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.FacetSource != "semantic_intake.intent_facets" {
		t.Fatalf("FacetSource = %q", payload.FacetSource)
	}
	if len(payload.IntentFacets) != 2 {
		t.Fatalf("IntentFacets = %#v, want two agent-owned facets", payload.IntentFacets)
	}
	for _, facet := range payload.IntentFacets {
		if facet.Coverage == "missing" {
			t.Fatalf("facet unexpectedly missing: %#v", payload.IntentFacets)
		}
	}
	if payload.CompassState != "usable" {
		t.Fatalf("CompassState = %q, want usable", payload.CompassState)
	}
}
```

- [ ] **Step 2: Add query-plan precision test**

Add this test:

```go
func TestCompassQueryPlanUsesConceptDecisionsAndPaths(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	payload, err := Compass(paths, CompassInput{
		Intent: "debug",
		Query:  "provider switch startup failure",
		InputMode: "query_plan",
		Plan: Plan{
			LexiconGenerationID: "GEN-compass-model-switch",
			SelectedConcepts: []string{"concept:GEN-compass-model-switch:N-provider-runtime"},
			ConceptDecisions: []ConceptDecision{{
				ConceptID:     "concept:GEN-compass-model-switch:N-provider-runtime",
				Decision:      "selected",
				CoveredFacets: []string{"provider runtime override", "startup failure"},
				MatchSources:  []string{"semantic_intake", "alias"},
				Confidence:    "high",
				Paths:         []string{"src/server/ws/handler.ts"},
			}},
			SemanticIntake: SemanticIntake{
				IntentFacets: []string{"provider runtime override", "startup failure"},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.FacetSource != "query_plan.intent_facets" {
		t.Fatalf("FacetSource = %q", payload.FacetSource)
	}
	if !hasString(payload.MinimalLiveReads, "src/server/ws/handler.ts") {
		t.Fatalf("MinimalLiveReads = %#v, want selected concept path", payload.MinimalLiveReads)
	}
	if payload.CompassState != "usable" {
		t.Fatalf("CompassState = %q, want usable", payload.CompassState)
	}
}
```

- [ ] **Step 3: Run tests and confirm failure**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query -run "TestCompass(SemanticIntake|QueryPlan)" -count=1
Pop-Location
```

Expected: FAIL until precision input logic is implemented.

- [ ] **Step 4: Implement precision facet selection**

In `compass.go`, update `compassFacets`:

```go
func compassFacets(input CompassInput, terms []string) ([]string, string) {
	plan := NormalizePlan(input.Plan)
	switch input.InputMode {
	case "query_plan":
		if len(plan.SemanticIntake.IntentFacets) > 0 {
			return append([]string{}, plan.SemanticIntake.IntentFacets...), compassFacetSourceQueryPlan
		}
		if len(plan.IntentFacets) > 0 {
			return append([]string{}, plan.IntentFacets...), compassFacetSourceQueryPlan
		}
	case "semantic_intake":
		if len(plan.SemanticIntake.IntentFacets) > 0 {
			return append([]string{}, plan.SemanticIntake.IntentFacets...), compassFacetSourceSemanticIntake
		}
	}
	return mechanicalFacetNames(terms), compassFacetSourceMechanical
}
```

Add `mechanicalFacetNames`:

```go
func mechanicalFacetNames(terms []string) []string {
	facets := []string{}
	for _, term := range terms {
		if len([]rune(term)) < 2 {
			continue
		}
		facets = appendMissingCoverage(facets, term)
		if len(facets) >= 8 {
			break
		}
	}
	if len(facets) == 0 {
		return []string{"raw query"}
	}
	return facets
}
```

Make candidate scoring include `plan.SemanticIntake.NormalizedQuery`, `plan.SemanticIntake.IntentFacets`, `plan.RepositorySearchTerms`, `ConceptDecision.Paths`, and `Plan.Paths` in addition to raw query terms.

- [ ] **Step 5: Run precision and full query tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query -run "TestCompass(SemanticIntake|QueryPlan|QueryDraft)" -count=1
go test ./internal/query -count=1
Pop-Location
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add tools/project-cognition/internal/query/compass.go tools/project-cognition/internal/query/compass_test.go
git commit -m "feat: support precision facets in project cognition compass"
```

---

## Task 4: Add Expansion Bundle Storage And Expand Runtime

**Files:**
- Create: `tools/project-cognition/internal/query/expansion.go`
- Create: `tools/project-cognition/internal/query/expansion_test.go`
- Modify: `tools/project-cognition/internal/query/compass.go`
- Modify: `tools/project-cognition/internal/query/compass_test.go`

- [ ] **Step 1: Add expansion tests**

Create `tools/project-cognition/internal/query/expansion_test.go`:

```go
package query

import (
	"os"
	"path/filepath"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

func TestCompassWritesExpansionBundleAndExpandReturnsSection(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)

	compass, err := Compass(paths, CompassInput{Intent: "debug", Query: "runtimeOverride deepseek 方块"})
	if err != nil {
		t.Fatal(err)
	}
	if compass.ExpansionRef.ID == "" {
		t.Fatalf("ExpansionRef = %#v, want id", compass.ExpansionRef)
	}

	payload, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID, Section: "raw_candidates"})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "ok" {
		t.Fatalf("Status = %q, payload = %#v", payload.Status, payload)
	}
	if payload.Section != "raw_candidates" {
		t.Fatalf("Section = %q", payload.Section)
	}
	if payload.Data == nil {
		t.Fatalf("Data = nil, payload = %#v", payload)
	}
	if payload.QueryFingerprint != compass.QueryFingerprint {
		t.Fatalf("QueryFingerprint = %q, want %q", payload.QueryFingerprint, compass.QueryFingerprint)
	}
}

func TestExpandReturnsStaleExpansionForGenerationMismatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedCompassModelSwitchGraph(t, paths)
	compass, err := Compass(paths, CompassInput{Intent: "debug", Query: "runtimeOverride"})
	if err != nil {
		t.Fatal(err)
	}

	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	status.ActiveGenerationID = "GEN-new"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}

	payload, err := Expand(paths, ExpandInput{ID: compass.ExpansionRef.ID, Section: "raw_candidates"})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "stale_expansion" {
		t.Fatalf("Status = %q, payload = %#v", payload.Status, payload)
	}
	if payload.CompassState != "stale_expansion" {
		t.Fatalf("CompassState = %q", payload.CompassState)
	}
	if payload.RecommendedNextAction != "rerun_project_cognition_compass" {
		t.Fatalf("RecommendedNextAction = %q", payload.RecommendedNextAction)
	}
}

func TestExpandReturnsMissingExpansionRecovery(t *testing.T) {
	paths := queryTestPaths(t)

	payload, err := Expand(paths, ExpandInput{ID: "exp-missing", Section: "raw_candidates"})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Status != "missing_expansion" {
		t.Fatalf("Status = %q, payload = %#v", payload.Status, payload)
	}
	if payload.RecommendedNextAction != "rerun_project_cognition_compass" {
		t.Fatalf("RecommendedNextAction = %q", payload.RecommendedNextAction)
	}
}

func TestExpansionBundlePathStaysInsideRuntimeDir(t *testing.T) {
	paths := queryTestPaths(t)
	got, err := expansionBundlePath(paths, "../outside")
	if err == nil {
		t.Fatalf("expansionBundlePath returned %s, want error", got)
	}
	if _, err := os.Stat(filepath.Join(paths.RuntimeDir, "workbench", "expansions")); err != nil && !os.IsNotExist(err) {
		t.Fatal(err)
	}
}
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query -run "Test(CompassWritesExpansion|ExpandReturns|ExpansionBundlePath)" -count=1
Pop-Location
```

Expected: FAIL with undefined `Expand`, `ExpandInput`, and `expansionBundlePath`.

- [ ] **Step 3: Add expansion runtime types**

Create `tools/project-cognition/internal/query/expansion.go`:

```go
package query

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

type ExpansionSectionMeta struct {
	State          string `json:"state"`
	EstimatedItems int   `json:"estimated_items"`
}

type ExpansionBundle struct {
	ID                       string                          `json:"id"`
	ActiveGenerationID       string                          `json:"active_generation_id"`
	CandidateUniverseVersion int                             `json:"candidate_universe_version"`
	QueryFingerprint         string                          `json:"query_fingerprint"`
	Sections                 map[string]ExpansionSectionMeta `json:"sections"`
	SectionPayloads          map[string]any                  `json:"section_payloads"`
	CreatedAt                string                          `json:"created_at"`
}

type ExpandInput struct {
	ID      string
	Section string
}

type ExpandPayload struct {
	Status                   string                          `json:"status"`
	Readiness                string                          `json:"readiness"`
	CompassState            string                          `json:"compass_state"`
	ID                       string                          `json:"id"`
	Section                  string                          `json:"section,omitempty"`
	Data                     any                             `json:"data,omitempty"`
	ActiveGenerationID       string                          `json:"active_generation_id,omitempty"`
	CandidateUniverseVersion int                             `json:"candidate_universe_version,omitempty"`
	QueryFingerprint         string                          `json:"query_fingerprint,omitempty"`
	AvailableSections        map[string]ExpansionSectionMeta `json:"available_sections,omitempty"`
	RecommendedNextAction    string                          `json:"recommended_next_action,omitempty"`
	Errors                   []string                        `json:"errors,omitempty"`
	Warnings                 []string                        `json:"warnings,omitempty"`
}
```

- [ ] **Step 4: Implement storage and stale recovery**

In `expansion.go`, implement:

```go
func writeExpansionBundle(paths rt.Paths, bundle ExpansionBundle) (ExpansionRef, error)
func Expand(paths rt.Paths, input ExpandInput) (ExpandPayload, error)
func expansionBundlePath(paths rt.Paths, id string) (string, error)
func staleExpansionPayload(id string, bundle ExpansionBundle, status rt.Status, reason string) ExpandPayload
func missingExpansionPayload(id string, reason string) ExpandPayload
```

Implementation rules:

- `expansionBundlePath` accepts only IDs matching `exp-[A-Za-z0-9._-]+`.
- Store files under `.specify/project-cognition/workbench/expansions/<id>.json`.
- `writeExpansionBundle` creates the directory with `0o755` and writes indented JSON with trailing newline.
- `Expand` trims `input.Section`; default section is `related_paths`.
- `Expand` returns `missing_expansion` for absent bundle files and for invalid IDs.
- `Expand` reads `rt.ReadStatus(paths)` and compares:
  - `bundle.ActiveGenerationID` to `status.ActiveGenerationID`
  - `bundle.CandidateUniverseVersion` to `CandidateUniverseVersion`
  - non-empty `bundle.QueryFingerprint`
- On mismatch, return `Status: "stale_expansion"`, `Readiness: rt.ReviewReadiness`, `CompassState: "stale_expansion"`, and `RecommendedNextAction: "rerun_project_cognition_compass"`.
- On missing section, return `Status: "missing_section"` and include `AvailableSections`.

- [ ] **Step 5: Wire compass to write expansion bundles**

In `Compass`, build an expansion bundle after lanes and diagnostics are computed:

```go
bundle := ExpansionBundle{
	ID:                       "exp-" + strings.TrimPrefix(payload.QueryFingerprint, "qf-"),
	ActiveGenerationID:       status.ActiveGenerationID,
	CandidateUniverseVersion: CandidateUniverseVersion,
	QueryFingerprint:         payload.QueryFingerprint,
	Sections: map[string]ExpansionSectionMeta{
		"related_paths":  {State: "available", EstimatedItems: len(payload.MinimalLiveReads)},
		"raw_candidates": {State: "available", EstimatedItems: len(candidates)},
		"coverage_gaps":  {State: "available", EstimatedItems: len(payload.CoverageDiagnostics)},
		"graph_neighbors": {State: "available", EstimatedItems: 0},
	},
	SectionPayloads: map[string]any{
		"related_paths":   payload.MinimalLiveReads,
		"raw_candidates":  candidatesForExpansion(candidates),
		"coverage_gaps":   payload.CoverageDiagnostics,
		"graph_neighbors": []map[string]any{},
	},
	CreatedAt: time.Now().UTC().Format(time.RFC3339),
}
payload.ExpansionRef, err = writeExpansionBundle(paths, bundle)
if err != nil {
	payload.Warnings = appendDiagnosticString(payload.Warnings, "expansion_bundle_write_failed:"+err.Error())
}
```

Add helper functions with deterministic output:

```go
func candidatesForExpansion(candidates []compassCandidate) []map[string]any
func appendDiagnosticString(values []string, value string) []string
```

- [ ] **Step 6: Run expansion tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query -run "Test(CompassWritesExpansion|ExpandReturns|ExpansionBundlePath)" -count=1
go test ./internal/query -count=1
Pop-Location
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add tools/project-cognition/internal/query/compass.go tools/project-cognition/internal/query/compass_test.go tools/project-cognition/internal/query/expansion.go tools/project-cognition/internal/query/expansion_test.go
git commit -m "feat: add project cognition expansion bundles"
```

---

## Task 5: Add CLI Commands, Help, And Command-Surface Tests

**Files:**
- Modify: `tools/project-cognition/internal/cli/cli.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Add CLI help tests**

In `tools/project-cognition/internal/cli/cli_test.go`, add:

```go
func TestRootHelpListsCompassAndExpand(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"--help"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s", code, stderr.String())
	}
	output := stdout.String()
	for _, command := range []string{"compass", "expand"} {
		if !strings.Contains(output, command) {
			t.Fatalf("help output missing %s: %s", command, output)
		}
	}
}

func TestCompassHelpListsPrecisionFlags(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"compass", "--help"}, &stdout, &stderr, "test")
	if code != 2 && code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	output := stdout.String() + stderr.String()
	for _, flag := range []string{"-query", "-semantic-intake-file", "-query-plan-file"} {
		if !strings.Contains(output, flag) {
			t.Fatalf("compass help missing %s: %s", flag, output)
		}
	}
}

func TestExpandHelpListsSectionFlag(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"expand", "--help"}, &stdout, &stderr, "test")
	if code != 2 && code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	output := stdout.String() + stderr.String()
	if !strings.Contains(output, "-section") {
		t.Fatalf("expand help missing -section: %s", output)
	}
}
```

- [ ] **Step 2: Add CLI JSON smoke tests**

Add:

```go
func TestCompassCommandEmitsCompactPacket(t *testing.T) {
	setupReadyMinimalCLIRuntime(t)

	var stdout, stderr bytes.Buffer
	code := Run([]string{"compass", "--intent", "debug", "--query", "App GUI", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["mode"] != "compass" {
		t.Fatalf("payload = %#v", payload)
	}
	if _, ok := payload["minimal_live_reads"].([]any); !ok {
		t.Fatalf("minimal_live_reads missing from payload = %#v", payload)
	}
	if _, ok := payload["evidence_lanes"].([]any); !ok {
		t.Fatalf("evidence_lanes missing from payload = %#v", payload)
	}
}

func TestExpandCommandReturnsStoredSection(t *testing.T) {
	setupReadyMinimalCLIRuntime(t)

	var compassStdout, compassStderr bytes.Buffer
	compassCode := Run([]string{"compass", "--intent", "debug", "--query", "App GUI", "--format", "json"}, &compassStdout, &compassStderr, "test")
	if compassCode != 0 {
		t.Fatalf("compass code = %d stderr=%s stdout=%s", compassCode, compassStderr.String(), compassStdout.String())
	}
	var compassPayload map[string]any
	if err := json.Unmarshal(compassStdout.Bytes(), &compassPayload); err != nil {
		t.Fatal(err)
	}
	expansionRef := compassPayload["expansion_ref"].(map[string]any)
	id := expansionRef["id"].(string)

	var stdout, stderr bytes.Buffer
	code := Run([]string{"expand", "--id", id, "--section", "related_paths", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("expand code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "ok" || payload["section"] != "related_paths" {
		t.Fatalf("payload = %#v", payload)
	}
}
```

- [ ] **Step 3: Run CLI tests and confirm failures**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/cli -run "Test(RootHelpListsCompass|CompassHelp|ExpandHelp|CompassCommand|ExpandCommand)" -count=1
Pop-Location
```

Expected: FAIL until CLI command routing exists.

- [ ] **Step 4: Add command routing**

In `tools/project-cognition/internal/cli/cli.go`:

- Add `compass` and `expand` to `printHelp`.
- Add switch cases:

```go
case "compass":
	return compassCommand(args[1:], stdout, stderr, paths)
case "expand":
	return expandCommand(args[1:], stdout, stderr, paths)
```

- Add command functions:

```go
func compassCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("compass", flag.ContinueOnError)
	fs.SetOutput(stderr)
	intent := fs.String("intent", "", "Intent")
	text := fs.String("query", "", "Query text")
	semanticIntakeFile := fs.String("semantic-intake-file", "", "Semantic intake file")
	planFile := fs.String("query-plan-file", "", "Query plan file")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}

	plan := query.Plan{}
	diagnostics := query.PlanDiagnostics{}
	inputMode := "query"
	if *planFile != "" {
		parsed, parsedDiagnostics, err := query.ParsePlanWithDiagnostics("", *planFile)
		if err != nil {
			var planErr *query.PlanParseError
			if errors.As(err, &planErr) {
				return writeErrorJSON(stdout, map[string]any{
					"status":         "error",
					"readiness":      rt.BlockedReadiness,
					"errors":         planErr.Errors,
					"warnings":       planErr.Warnings,
					"repair_hints":   planErr.RepairHints,
					"expected_shape": planErr.ExpectedShape,
				})
			}
			fmt.Fprintf(stderr, "project-cognition: %v\n", err)
			return 1
		}
		plan = parsed
		diagnostics = parsedDiagnostics
		inputMode = "query_plan"
	} else if *semanticIntakeFile != "" {
		intake, err := query.ParseSemanticIntakeFile(*semanticIntakeFile)
		if err != nil {
			fmt.Fprintf(stderr, "project-cognition: %v\n", err)
			return 1
		}
		plan.SemanticIntake = intake
		inputMode = "semantic_intake"
	}

	payload, err := query.Compass(paths, query.CompassInput{
		Intent:          *intent,
		Query:           *text,
		Plan:            plan,
		PlanDiagnostics: diagnostics,
		InputMode:       inputMode,
	})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}

func expandCommand(args []string, stdout io.Writer, stderr io.Writer, paths rt.Paths) int {
	fs := flag.NewFlagSet("expand", flag.ContinueOnError)
	fs.SetOutput(stderr)
	id := fs.String("id", "", "Expansion id")
	section := fs.String("section", "related_paths", "Expansion section")
	_ = fs.String("format", "json", "Output format")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	payload, err := query.Expand(paths, query.ExpandInput{ID: *id, Section: *section})
	return writeCommandResult(stdout, stderr, paths, payload, err)
}
```

Add `ParseSemanticIntakeFile` in `compass.go` or a focused helper file:

```go
func ParseSemanticIntakeFile(path string) (SemanticIntake, error)
```

It should accept either a direct `SemanticIntake` JSON object or `{ "semantic_intake": { ... } }`.

- [ ] **Step 5: Run CLI and full Go tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/cli -run "Test(RootHelpListsCompass|CompassHelp|ExpandHelp|CompassCommand|ExpandCommand)" -count=1
go test ./...
Pop-Location
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/cli/cli_test.go tools/project-cognition/internal/query/compass.go
git commit -m "feat: expose project cognition compass cli"
```

---

## Task 6: Update Runtime Compatibility Probes, Installers, And Launcher Tests

**Files:**
- Modify: `src/specify_cli/project_cognition_runtime.py`
- Modify: `tests/test_project_cognition_runtime_install.py`
- Modify: `tests/test_project_cognition_launcher_rendering.py`
- Modify: `tools/project-cognition/install.sh`
- Modify: `tools/project-cognition/install.ps1`

- [ ] **Step 1: Add failing Python tests for required commands**

In `tests/test_project_cognition_runtime_install.py`, update `test_project_cognition_required_commands_include_init_empty`:

```python
def test_project_cognition_required_commands_include_compass_and_expand():
    assert "build-from-scan" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "init-empty" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "lexicon --mode" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "compass --semantic-intake-file --query-plan-file" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "expand --section" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "update --payload-file --verification" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "delta append --verification --generated-surface" in project_cognition_runtime.REQUIRED_COMMANDS
```

Add a focused compatibility-probe test:

```python
def test_project_cognition_binary_support_requires_compass_and_expand(monkeypatch, tmp_path: Path):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = "Commands: status, build-from-scan, init-empty, update, lexicon, delta\n"
        stderr = ""

    def fake_run(command, **kwargs):
        if command[1:] == ["--help"]:
            return RootHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False
```

- [ ] **Step 2: Add launcher rendering tests**

In `tests/test_project_cognition_launcher_rendering.py`, add:

```python
def test_project_cognition_compass_subcommand_renders_with_persisted_binary(tmp_path: Path):
    binary = tmp_path / ".specify" / "bin" / "project-cognition"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    from specify_cli import project_cognition_runtime

    project_cognition_runtime.write_project_launcher_config(tmp_path, binary)

    rendered = render_project_launcher_placeholders(
        tmp_path,
        '{{specify-subcmd:project-cognition compass --intent debug --query="$ARGUMENTS" --format json}}',
    )

    assert rendered == f'{binary} compass --intent debug --query="$ARGUMENTS" --format json'


def test_project_cognition_expand_subcommand_renders_with_persisted_binary(tmp_path: Path):
    binary = tmp_path / ".specify" / "bin" / "project-cognition"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    from specify_cli import project_cognition_runtime

    project_cognition_runtime.write_project_launcher_config(tmp_path, binary)

    rendered = render_project_launcher_placeholders(
        tmp_path,
        "{{specify-subcmd:project-cognition expand --id exp-qf-test --section raw_candidates --format json}}",
    )

    assert rendered == f"{binary} expand --id exp-qf-test --section raw_candidates --format json"
```

- [ ] **Step 3: Run tests and confirm failures**

Run:

```powershell
pytest tests/test_project_cognition_runtime_install.py tests/test_project_cognition_launcher_rendering.py -q
```

Expected: FAIL until `REQUIRED_COMMANDS` and probe logic include `compass` and `expand`.

- [ ] **Step 4: Update Python compatibility probe**

In `src/specify_cli/project_cognition_runtime.py`, update:

```python
REQUIRED_COMMANDS = (
    "build-from-scan",
    "init-empty",
    "lexicon --mode",
    "compass --semantic-intake-file --query-plan-file",
    "expand --section",
    "update --payload-file --verification",
    "delta append --verification --generated-surface",
)
```

Add helper probes after the lexicon probe:

```python
    try:
        compass_result = subprocess.run(
            [str(binary), "compass", "--help"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    compass_output = f"{compass_result.stdout}\n{compass_result.stderr}"
    if "-semantic-intake-file" not in compass_output or "-query-plan-file" not in compass_output:
        return False

    try:
        expand_result = subprocess.run(
            [str(binary), "expand", "--help"],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    expand_output = f"{expand_result.stdout}\n{expand_result.stderr}"
    if "-section" not in expand_output:
        return False
```

- [ ] **Step 5: Update shell installers**

In `tools/project-cognition/install.sh`, after the lexicon check add:

```bash
compass_help="$("$target" compass --help 2>&1 || true)"
if [[ "$compass_help" != *"-semantic-intake-file"* || "$compass_help" != *"-query-plan-file"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required compass precision flags." >&2
  echo "Expected 'project-cognition compass --help' to include -semantic-intake-file and -query-plan-file." >&2
  exit 1
fi
expand_help="$("$target" expand --help 2>&1 || true)"
if [[ "$expand_help" != *"-section"* ]]; then
  echo "Error: downloaded project-cognition binary is missing required expand section flag." >&2
  echo "Expected 'project-cognition expand --help' to include -section." >&2
  exit 1
fi
```

In `tools/project-cognition/install.ps1`, after the lexicon check add:

```powershell
$compassHelp = & $target compass --help 2>&1
if (($compassHelp -notmatch '-semantic-intake-file') -or ($compassHelp -notmatch '-query-plan-file')) {
    Write-Host "Error: downloaded project-cognition binary is missing required compass precision flags."
    Write-Host "Expected 'project-cognition compass --help' to include -semantic-intake-file and -query-plan-file."
    exit 1
}
$expandHelp = & $target expand --help 2>&1
if ($expandHelp -notmatch '-section') {
    Write-Host "Error: downloaded project-cognition binary is missing required expand section flag."
    Write-Host "Expected 'project-cognition expand --help' to include -section."
    exit 1
}
```

- [ ] **Step 6: Run Python tests**

Run:

```powershell
pytest tests/test_project_cognition_runtime_install.py tests/test_project_cognition_launcher_rendering.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add src/specify_cli/project_cognition_runtime.py tests/test_project_cognition_runtime_install.py tests/test_project_cognition_launcher_rendering.py tools/project-cognition/install.sh tools/project-cognition/install.ps1
git commit -m "feat: require compass-capable project cognition runtime"
```

---

## Task 7: Update Workflow Guidance To Consume Compass By Default

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/planning-context-loading-gradient.md`
- Modify: `templates/command-partials/common/navigation-check.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify direct command templates listed in the File Structure section
- Modify: `tests/test_map_runtime_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Run the surface sweep**

Run:

```powershell
rg -n "project-cognition lexicon|project-cognition query|minimal_live_reads|ready`|ambiguous`|needs_update`|query_plan|semantic_intake" templates src tests README.md PROJECT-HANDBOOK.md
```

Expected: command exits `0` and prints all current project-cognition guidance surfaces. Use the output as the checklist for this task.

- [ ] **Step 2: Update failing template assertions**

In `tests/test_map_runtime_template_guidance.py`, change `test_workflows_use_project_cognition_query_instead_of_raw_graph_reads` into `test_workflows_use_project_cognition_compass_as_default_intake`.

The assertions must require:

```python
assert "project-cognition compass" in content
assert f"project-cognition compass --intent {intent}" in content
assert "minimal_live_reads" in content
assert "first_pass_paths" in content
assert "coverage_diagnostics" in content
assert "lexicon -> semantic_intake -> query" in content or "lexicon -> semantic_intake -> project-cognition query" in content
assert "project-cognition query --intent" in content
```

Replace the readiness state list:

```python
readiness_states = ["query_ready", "review", "needs_rebuild", "blocked", "unsupported_runtime"]
```

Add checks:

```python
assert "`ambiguous`" not in content
assert "`needs_update`" not in content
assert "read top-level `minimal_live_reads` first" in content
assert "then use lane-level `first_pass_paths`" in content
```

- [ ] **Step 3: Run template tests and confirm failures**

Run:

```powershell
pytest tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: FAIL because templates still describe the old default `lexicon -> query` flow and old readiness values.

- [ ] **Step 4: Update shared guidance text**

In both context-loading partials and both passive skills, replace the default intake wording with this contract:

```markdown
Default project cognition intake is `project-cognition compass --intent <intent> --query="$ARGUMENTS" --format json`.

Consume the packet in this order:

1. Read top-level `minimal_live_reads` first and use those files as the bounded first live evidence route.
2. Then use lane-level `first_pass_paths` for reasons, evidence hints, verification hints, follow-up surfaces, and `before_fix_claim` checks.
3. Treat `coverage_diagnostics` as confidence and closeout signals, never as route candidates.
4. Treat `expansion_ref` as a normal continuation path. Run `project-cognition expand --id <id> --section <section> --format json` only when coverage state or live evidence requires more map detail.
5. Do not infer final edit scope from `minimal_live_reads` or `first_pass_paths`.

Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`. Compass-specific advice is in `compass_state` and `recommended_next_action`.

When `compass_state=needs_semantic_intake`, the agent writes `semantic_intake` from project vocabulary and reruns compass with `--semantic-intake-file`, or uses the advanced `lexicon -> semantic_intake -> query` path when explicit concept decisions are needed.
```

Keep the advanced path in the same files:

```markdown
Advanced routing remains available as `project-cognition lexicon --mode catalog`, agent-authored `semantic_intake` and `concept_decisions`, then `project-cognition query --query-plan`. Use it when the first compass packet is too draft-like, a workflow needs explicit concept decisions, or coverage cannot be resolved from the default packet.
```

- [ ] **Step 5: Update `src/specify_cli/integrations/base.py`**

Replace `_project_cognition_query_gate_line` output with a compass-first gate. Keep the function name for a small diff unless the implementation also updates all call sites.

The returned string must include:

```python
f"run `{{{{specify-subcmd:project-cognition compass --intent {intent} --query=\"$ARGUMENTS\" --format json}}}}` {command_step}"
"Read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons"
"coverage_diagnostics"
"expansion_ref"
"lexicon -> semantic_intake -> query"
"query_ready"
"unsupported_runtime"
```

Remove old default-readiness guidance for `ready`, `ambiguous`, and `needs_update`.

- [ ] **Step 6: Update direct command templates**

For every direct command template from the sweep, apply the same default:

```markdown
{{specify-subcmd:project-cognition compass --intent <intent> --query="$ARGUMENTS" --format json}}
```

Then include the same consuming order:

```markdown
- Read top-level `minimal_live_reads` first.
- Then use lane-level `first_pass_paths` reasons, `verification_hints`, `followup_surfaces`, and `before_fix_claim`.
- Do not treat first-pass reads as the final edit scope.
- Use `project-cognition expand` only when the packet's coverage state or live evidence requires it.
- Preserve the advanced `lexicon -> semantic_intake -> query` flow for explicit concept decisions.
```

- [ ] **Step 7: Run template tests**

Run:

```powershell
pytest tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: PASS. If `tests/test_alignment_templates.py` still expects `_launcher_lexicon` and `_launcher_query` as default, update its helper assertions to require `_launcher_compass(intent)` and require the advanced flow text separately.

- [ ] **Step 8: Run integration rendering smoke tests**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_skills.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add src/specify_cli/integrations/base.py templates tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py
git commit -m "docs: make workflow cognition intake compass-first"
```

---

## Task 8: Update User Docs And Handbook Template

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `.github/workflows/release.yml` only if release notes should name the new commands
- Modify: `.github/workflows/release-project-cognition.yml` only if command verification is added there

- [ ] **Step 1: Add doc assertions if no existing test covers docs**

In `tests/test_map_runtime_template_guidance.py`, add:

```python
def test_docs_describe_compass_default_and_advanced_query_path() -> None:
    for path in ["README.md", "PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"]:
        content = _compact(_read(path).lower())
        assert "project-cognition compass" in content, path
        assert "minimal_live_reads" in content, path
        assert "first_pass_paths" in content, path
        assert "lexicon -> semantic_intake -> query" in content, path
        assert "final edit scope" in content, path
```

- [ ] **Step 2: Run the doc test and confirm failure**

Run:

```powershell
pytest tests/test_map_runtime_template_guidance.py -q
```

Expected: FAIL until docs are updated.

- [ ] **Step 3: Update docs**

In `README.md`, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md`, replace default brownfield cognition guidance with:

```markdown
Generated workflows use `project-cognition compass --intent <intent> --query "$ARGUMENTS" --format json` as the default brownfield navigation intake. The packet returns readiness, `compass_state`, top-level `minimal_live_reads`, lane-level `first_pass_paths` with reasons, `coverage_diagnostics`, and `expansion_ref`.

Agents read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons and `before_fix_claim` checks to prove or reject the route from live repository evidence. These paths are first evidence, not final edit scope.

When the compass packet is draft-like, localized, missing coverage, or needs explicit concept decisions, the advanced path remains `project-cognition lexicon --mode catalog` -> agent-authored `semantic_intake` and `concept_decisions` -> `project-cognition query --query-plan`.
```

Keep install docs aligned with release assets and the pinned binary behavior.

- [ ] **Step 4: Update release notes text if present**

In `.github/workflows/release.yml`, update the project-cognition runtime release note paragraph to mention:

```text
The runtime includes the default compass/expand navigation commands plus the advanced lexicon/query planning commands used by generated workflows.
```

No build job changes are needed unless command verification is added to the workflow itself.

- [ ] **Step 5: Run doc/template tests**

Run:

```powershell
pytest tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_map_runtime_template_guidance.py .github/workflows/release.yml
git commit -m "docs: document project cognition compass intake"
```

---

## Task 9: Full Verification And Downstream Experience Check

**Files:**
- Read-only unless a focused regression fails.

- [ ] **Step 1: Run Go runtime tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./...
go vet ./...
go build -o $env:TEMP\project-cognition-compass-test.exe .
Pop-Location
```

Expected: all commands exit `0`.

- [ ] **Step 2: Run Python focused tests**

Run:

```powershell
pytest tests/test_project_cognition_runtime_install.py tests/test_project_cognition_launcher_rendering.py tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 3: Run integration smoke tests**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py -q
```

Expected: PASS.

- [ ] **Step 4: Run a local runtime smoke test**

From the repository root after building:

```powershell
$bin = Join-Path $env:TEMP "project-cognition-compass-test.exe"
& $bin --help
& $bin compass --help
& $bin expand --help
```

Expected:

- root help contains `compass` and `expand`
- compass help contains `-semantic-intake-file` and `-query-plan-file`
- expand help contains `-section`

- [ ] **Step 5: Run optional downstream smoke against `F:\github\cc-jiangxia` if available**

Only run this if the directory exists and has `.specify/project-cognition/`:

```powershell
$bin = Join-Path $env:TEMP "project-cognition-compass-test.exe"
Push-Location F:\github\cc-jiangxia
& $bin compass --intent debug --query "会话界面切模型失败 Failed to switch provider/model CLI exited during startup code 143 DeepSeek 方块 屏幕很小" --format json | Tee-Object -Variable compassJson
Pop-Location
```

Expected:

- output is a compact JSON packet, not a 20k-line dump
- output includes `minimal_live_reads`
- output includes `evidence_lanes`
- output includes `coverage_diagnostics` if broad fallback material matched
- output includes `expansion_ref`

Do not commit downstream files from `F:\github\cc-jiangxia`.

- [ ] **Step 6: Check for old default-readiness wording**

Run:

```powershell
rg -n "readiness.*`ready`|`ambiguous`|`needs_update`|project-cognition lexicon --intent .*default|project-cognition query --intent .*default" templates src README.md PROJECT-HANDBOOK.md docs/superpowers/specs docs/superpowers/plans
```

Expected: no hits that describe default compass routing with old readiness values. Hits inside historical specs or quoted advanced-flow text are acceptable only when the surrounding sentence explicitly marks them as old or advanced.

- [ ] **Step 7: Check git state and final diff**

Run:

```powershell
git status --short
git diff --check
git log --oneline -n 8
```

Expected:

- no whitespace errors
- only intended modified files are staged or committed
- `.superpowers/` may remain untracked if it is still temporary companion output

- [ ] **Step 8: Final commit if verification fixes changed files**

If Step 1 through Step 7 required small follow-up fixes:

```powershell
git add <changed-files>
git commit -m "test: verify project cognition compass rollout"
```

If no files changed after the previous commits, do not create an empty commit.

---

## Implementation Notes

- Prefer focused files. Keep `compass.go` and `expansion.go` separate instead of growing `query.go`.
- Do not change the SQLite schema for this first compass implementation. Use existing `nodes`, `path_index`, `alias_index`, observations, and attrs.
- Do not parse fallback state from display titles. Use `node.type`, `attrs.fallback_provenance`, `attrs.coverage_fallback`, `attrs.path_count`, and path count thresholds.
- Preserve `lexicon` and `query` command behavior except for the readiness drift fix in Task 1.
- If a command template needs both default and advanced routes, put default compass first and advanced `lexicon -> semantic_intake -> query` second.
- Treat `minimal_live_reads` as a route constraint for first evidence, never as complete edit scope.

## Self-Review Checklist

- Spec coverage:
  - `compass` command: Task 2, Task 3, Task 5
  - precision inputs: Task 3, Task 5
  - top-level `minimal_live_reads`: Task 2, Task 7
  - expansion stale behavior: Task 4, Task 5
  - structural broad fallback suppression: Task 2
  - runtime readiness enum: Task 1, Task 2, Task 7
  - distribution/runtime wiring: Task 6, Task 8, Task 9
- Type consistency:
  - Runtime packet field names match the approved spec: `readiness`, `compass_state`, `minimal_live_reads`, `evidence_lanes`, `first_pass_paths`, `coverage_diagnostics`, `expansion_ref`.
  - Expansion metadata field names match the approved spec: `active_generation_id`, `candidate_universe_version`, `query_fingerprint`, `available_sections`.
  - Workflow consumption order is explicit: read top-level `minimal_live_reads` first, then lane-level `first_pass_paths` reasons.
- Verification coverage:
  - Go runtime package tests cover query, compass, and expansion behavior.
  - Go CLI tests cover command help and JSON smoke.
  - Python tests cover runtime compatibility and launcher rendering.
  - Template tests cover compass default wording and advanced path preservation.

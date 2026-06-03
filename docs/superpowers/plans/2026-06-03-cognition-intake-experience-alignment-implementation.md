# Cognition Intake Experience Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every generated brownfield `sp-*` workflow use the same semantic cognition intake experience: lexicon first, agent-written `semantic_intake`, facet-covered concept selection, query-plan diagnostics, readiness-driven `minimal_live_reads`, and non-blocking passive learning preflight.

**Architecture:** Add behavior tests before prompt/runtime changes, then converge the shared template contract, Go query-plan parser, Python learning-start parser, and generated integration renderers around one machine-readable diagnostics model. Keep project cognition advisory: map output routes work, live source evidence proves behavior.

**Tech Stack:** Go `project-cognition` runtime, Python Typer learning CLI, pytest template/integration tests, Markdown command templates and passive skills.

---

## Reference Spec

- `docs/superpowers/specs/2026-06-03-cognition-intake-experience-alignment-design.md`
- Related design: `docs/superpowers/specs/2026-06-02-shared-semantic-cognition-intake-design.md`

## Scope Notes

- Start with an audit. Do not patch `debug.md` alone.
- Treat `sp-debug` as the incident sample, not the only target.
- Preserve the existing semantic intake model. This plan only aligns experience, diagnostics, and generated guidance.
- Use coercion with warning diagnostics for the common string-array `alias_interpretations` mistake. Reject unsupported shapes with structured JSON under `--format json`.
- Passive learning is required to attempt where workflows call it, but a legacy learning-index parse failure must not terminate the primary workflow.
- Work in small commits. Red-gate test additions should not be committed until
  the matching implementation task returns the targeted tests to green.

## Initial Audit Matrix

| Surface group | Current risk | Required fix | Durable test |
| --- | --- | --- | --- |
| Shared cognition partials | They describe fields but do not provide a compact copyable query-plan skeleton. | Add one canonical skeleton with object-shaped `alias_interpretations` and `concept_decisions`. | Template tests assert the skeleton and field shapes. |
| Workflow templates | Individual commands can drift from the shared intake contract or over-route `needs_update`/`review`. | Reference the shared contract and preserve intent-specific constraints only. | Tests cover `debug`, one planning workflow, one execution workflow, `prd-scan`, `map-build`, and `checklist`. |
| Go query parser | `encoding/json` struct unmarshal errors can leak raw implementation details. | Parse through a tolerant normalization layer and emit structured diagnostics. | Query/CLI tests cover inline JSON, `@file`, and `--query-plan-file`. |
| Query route behavior | Localized or informal prompts can be treated as raw keyword matching instead of semantic facets. | Keep facet coverage as route truth and surface partial coverage. | Runtime test uses localized and informal input with facet decisions. |
| Python learning start | Missing legacy fields such as `learning_type` can raise `KeyError`. | Normalize or skip malformed entries and return warnings/diagnostics. | Learning CLI tests cover `debug`, `constitution`, `map-scan`, and `map-build`. |
| Generated integrations | Markdown/TOML/skills renderers can lose or mutate the shared guidance. | Add generated-output parity checks for cognition and learning guidance. | Integration tests cover Markdown, TOML, skills, Codex, and Claude Agent Teams where relevant. |

## File Structure

Runtime query diagnostics:

- `tools/project-cognition/internal/query/query.go`: query-plan diagnostics structs, tolerant parser, normalized warnings, query payload diagnostics.
- `tools/project-cognition/internal/query/query_test.go`: parser, semantic-intake, localized/informal prompt, and diagnostics unit tests.
- `tools/project-cognition/internal/cli/cli.go`: structured JSON parse-error payload for `project-cognition query --format json`.
- `tools/project-cognition/internal/cli/cli_test.go`: CLI parse-path tests for `--query-plan`, `--query-plan @file`, and `--query-plan-file`.

Learning hardening:

- `src/specify_cli/learnings.py`: tolerant index-entry loading, warning diagnostics, and start payload fields.
- `tests/test_learning_cli.py`: legacy/malformed index tests across cognition and non-cognition workflows.
- `templates/passive-skills/spec-kit-project-learning/SKILL.md`: clarify that required preflight means required to attempt and report, not allowed to block primary workflow on legacy parser failures.

Generated workflow guidance:

- `templates/command-partials/common/context-loading-gradient.md`: canonical query-plan skeleton and shared advisory intake wording.
- `templates/command-partials/common/planning-context-loading-gradient.md`: planning copy of the skeleton or direct shared wording equivalent.
- `templates/command-partials/common/senior-consequence-analysis-gate.md`: ensure `review` routes to returned `minimal_live_reads`.
- `templates/commands/{discussion,specify,clarify,deep-research,plan,tasks,analyze,fast,quick,implement,debug,checklist,prd-scan,map-build,map-update}.md`: reduce drift and preserve shared intake references.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: canonical query-plan shape and diagnostics guidance.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: route guidance stays aligned with semantic intake and map-update-first policy.
- `src/specify_cli/integrations/base.py`: generated addenda preserve the shared contract.
- `src/specify_cli/integrations/claude/templates/implement-teams.md`: Claude Agent Teams context bundle preserves `sp-implement` cognition bundle and diagnostics.

Regression tests:

- `tests/test_alignment_templates.py`
- `tests/test_debug_template_guidance.py`
- `tests/test_fast_template_guidance.py`
- `tests/test_quick_template_guidance.py`
- `tests/test_map_runtime_template_guidance.py`
- `tests/test_passive_skill_guidance.py`
- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_toml.py`
- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_integration_codex.py`
- `tests/integrations/test_integration_claude.py`

---

## Task 1: Add Experience Audit And Template Contract Tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_map_runtime_template_guidance.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`

- [ ] **Step 1: Add failing shared skeleton assertions**

In `tests/test_alignment_templates.py`, add focused tests that assert both common cognition partials contain one canonical query-plan skeleton with these required fields:

```text
"raw_query"
"semantic_intake"
"workflow_intent"
"normalized_query"
"intent_facets"
"negative_constraints"
"alias_interpretations"
"open_semantic_questions"
"selected_concepts"
"rejected_concepts"
"concept_decisions"
"covered_facets"
"missing_facets"
"match_sources"
"lexicon_generation_id"
"expanded_queries"
"paths"
```

Assert the skeleton uses an object-shaped alias interpretation:

```json
{"alias": "...", "meaning": "...", "confidence": "medium"}
```

and does not show `alias_interpretations` as a string array.

- [ ] **Step 2: Add affected workflow drift assertions**

In the same test file, add a table for the affected command templates:

```python
COGNITION_INTAKE_COMMANDS = (
    "discussion",
    "specify",
    "clarify",
    "deep-research",
    "plan",
    "tasks",
    "analyze",
    "fast",
    "quick",
    "implement",
    "debug",
    "checklist",
    "prd-scan",
    "map-build",
    "map-update",
)
```

For each existing template in that table, assert that it mentions the shared intake sequence or includes the required cognition terms:

- `project-cognition lexicon`
- `semantic_intake`
- `concept_decisions`
- `lexicon_generation_id`
- `project-cognition query`
- `--query-plan`
- `minimal_live_reads`

For `map-update`, allow the test to focus on map-maintenance query/update guidance if it does not perform ordinary user-intent intake.

- [ ] **Step 3: Add readiness review assertion**

Assert shared readiness guidance says `review` inspects only or first the returned `minimal_live_reads` before expanding. Include `senior-consequence-analysis-gate.md`, `context-loading-gradient.md`, and `planning-context-loading-gradient.md`.

- [ ] **Step 4: Add learning-start scope assertion**

Add a test that discovers every template with `learning start --command` and asserts the set includes at least:

```python
{"debug", "plan", "implement", "constitution", "map-scan", "map-build"}
```

This test documents why learning hardening is not limited to cognition workflows.

- [ ] **Step 5: Run the failing tests**

Run:

```powershell
uv run pytest tests/test_alignment_templates.py tests/test_passive_skill_guidance.py tests/test_map_runtime_template_guidance.py -q
uv run pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py -q
```

Expected: FAIL on missing canonical skeleton and any generated-output parity gaps.

- [ ] **Step 6: Keep the red-gate changes uncommitted**

Do not commit this failing test baseline by itself. Keep the test changes in the
worktree, then complete Task 2 and commit the now-green template contract and
tests together.

## Task 2: Normalize Shared Template Guidance

**Files:**
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/planning-context-loading-gradient.md`
- Modify: `templates/command-partials/common/senior-consequence-analysis-gate.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify as needed: affected templates under `templates/commands/*.md`

- [ ] **Step 1: Add the canonical query-plan skeleton**

Add this compact skeleton to both shared context-loading partials. Keep it short enough that generated commands remain usable:

```json
{
  "raw_query": "$ARGUMENTS",
  "semantic_intake": {
    "workflow_intent": "<active workflow intent>",
    "normalized_query": "<project-language interpretation>",
    "intent_facets": ["<facet the selected concept must cover>"],
    "negative_constraints": ["<scope boundary not to treat as route truth>"],
    "alias_interpretations": [
      {"alias": "<user term>", "meaning": "<project term>", "confidence": "medium"}
    ],
    "open_semantic_questions": []
  },
  "selected_concepts": ["<concept id from lexicon payload>"],
  "rejected_concepts": ["<considered concept id>"],
  "concept_decisions": [
    {
      "concept_id": "<concept id>",
      "decision": "selected",
      "selection_reason": "<facet-coverage rationale>",
      "covered_facets": ["<covered facet>"],
      "missing_facets": [],
      "match_sources": ["alias", "semantic_intake"],
      "confidence": "medium",
      "risk": ""
    }
  ],
  "lexicon_generation_id": "<lexicon_generation_id from lexicon payload>",
  "expanded_queries": ["<normalized project-language query>"],
  "paths": ["<justified path hint>"]
}
```

Make clear that `alias_interpretations` is an array of objects, not strings.

- [ ] **Step 2: Align readiness wording**

In `senior-consequence-analysis-gate.md` and the two context-loading partials, keep this behavior:

- `ready`: continue with the returned bundle.
- `review`: inspect the returned `minimal_live_reads` before expanding.
- `ambiguous`: ask a bounded clarification.
- `needs_update`: use `map-update` only when updated runtime coverage is needed; otherwise carry stale/weak coverage and prove claims from live evidence.
- `needs_rebuild`: reserve `map-scan -> map-build` for documented rebuild triggers.
- `blocked`: report the runtime state; continue with live evidence only when the active workflow allows degraded advisory navigation.

- [ ] **Step 3: Update passive skills**

Update `spec-kit-project-cognition-gate` and `spec-kit-workflow-routing` so passive guidance matches the skeleton and says parser diagnostics may include:

- `warnings`
- `repair_hints`
- normalized `query_plan`
- structured `errors`
- `expected_shape`

- [ ] **Step 4: Reduce command-template drift**

Sweep the affected command templates and replace local prose that teaches a different query-plan shape with references to the shared skeleton. Preserve intent-specific command invocations, such as:

- `--intent discussion`
- `--intent plan`
- `--intent research`
- `--intent implement`
- `--intent debug`

- [ ] **Step 5: Run template tests**

Run:

```powershell
uv run pytest tests/test_alignment_templates.py tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_passive_skill_guidance.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add templates/command-partials/common/context-loading-gradient.md templates/command-partials/common/planning-context-loading-gradient.md templates/command-partials/common/senior-consequence-analysis-gate.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md templates/commands tests
git commit -m "docs: align shared cognition intake guidance"
```

## Task 3: Add Query-Plan Diagnostics To The Go Runtime

**Files:**
- Modify: `tools/project-cognition/internal/query/query.go`
- Modify: `tools/project-cognition/internal/query/query_test.go`
- Modify: `tools/project-cognition/internal/cli/cli.go`
- Modify: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Add failing parser tests**

In `query_test.go`, add tests for:

1. Top-level string-array aliases are coerced:

```json
{"alias_interpretations": ["PE程序"], "normalized_query": "WinPE driver download stall"}
```

Expected normalized alias:

```json
{"alias": "PE程序", "meaning": "PE程序", "confidence": "low"}
```

2. Nested `semantic_intake.alias_interpretations` string arrays are coerced the same way.
3. Nested aliases remain preferred when nested and top-level aliases conflict.
4. Missing `lexicon_generation_id` produces a warning but does not reject the query plan.
5. Unsupported alias shapes return a structured plan parse error with `expected_shape`.

- [ ] **Step 2: Add failing CLI parse-path tests**

In `cli_test.go`, add a helper that runs the same malformed-but-recoverable query plan through:

```powershell
project-cognition query --intent debug --query-plan "<json>" --format json
project-cognition query --intent debug --query-plan "@path/to/query-plan.json" --format json
project-cognition query --intent debug --query-plan-file "path/to/query-plan.json" --format json
```

Assert all three payloads include:

- exit code `0`
- `warnings` or `repair_hints`
- normalized `query_plan.semantic_intake.alias_interpretations[0]` as an object

Add one unrecoverable-shape test and assert:

- non-zero exit code
- stdout JSON has `status="error"`
- `errors` array
- `warnings` array
- `repair_hints`
- `expected_shape`
- stderr is concise and not the only diagnostics channel

- [ ] **Step 3: Implement parser diagnostics without breaking existing callers**

Keep `ParsePlan(value, file) (Plan, error)` for existing tests and compatibility, but implement it through a new helper:

```go
type PlanDiagnostics struct {
    Warnings      []string       `json:"warnings,omitempty"`
    RepairHints   []string       `json:"repair_hints,omitempty"`
    ExpectedShape map[string]any `json:"expected_shape,omitempty"`
}

type PlanParseError struct {
    Errors        []string
    Warnings      []string
    RepairHints   []string
    ExpectedShape map[string]any
}

func ParsePlanWithDiagnostics(value, file string) (Plan, PlanDiagnostics, error)
```

Use an intermediate `map[string]any` normalization pass before unmarshalling into `Plan`.

- [ ] **Step 4: Normalize common legacy shapes**

During the map normalization pass:

- If top-level `alias_interpretations` is `[]string`, convert each item to `{alias, meaning, confidence:"low"}`.
- If nested `semantic_intake.alias_interpretations` is `[]string`, convert it the same way.
- If aliases are already object arrays, preserve them.
- If aliases are mixed or unsupported shapes, return `PlanParseError`.
- If `lexicon_generation_id` is missing, add a warning such as `query_plan_missing_lexicon_generation_id`.

- [ ] **Step 5: Add diagnostics to successful query payloads**

Extend `QueryInput` and `QueryPayload` so CLI callers can receive diagnostics:

```go
PlanDiagnostics PlanDiagnostics
Warnings []string `json:"warnings,omitempty"`
RepairHints []string `json:"repair_hints,omitempty"`
```

The returned `query_plan` must show the normalized shape used by the runtime.

- [ ] **Step 6: Emit structured JSON errors in CLI**

In `queryCommand`, call `ParsePlanWithDiagnostics`. On `PlanParseError`, write stdout JSON:

```json
{
  "status": "error",
  "readiness": "blocked",
  "errors": ["..."],
  "warnings": [],
  "repair_hints": ["..."],
  "expected_shape": {"alias_interpretations": [{"alias": "...", "meaning": "...", "confidence": "medium"}]}
}
```

Return a non-zero exit code. Stderr may repeat one concise line.

- [ ] **Step 7: Run Go tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query ./internal/cli -count=1
Pop-Location
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add tools/project-cognition/internal/query/query.go tools/project-cognition/internal/query/query_test.go tools/project-cognition/internal/cli/cli.go tools/project-cognition/internal/cli/cli_test.go
git commit -m "fix: return query plan diagnostics from project cognition"
```

## Task 4: Prove Semantic Intake Drives Runtime Selection

**Files:**
- Modify: `tools/project-cognition/internal/query/query_test.go`
- Modify if needed: `tools/project-cognition/internal/query/query.go`
- Modify if needed: `tools/project-cognition/internal/query/lexicon.go`

- [ ] **Step 1: Add localized prompt runtime test**

Add a test that builds or reuses a ready minimal runtime with at least two candidate concepts, then runs a query plan whose raw query is localized and informal:

```text
PE程序下驱动下载目前好像有点问题，现象就是卡在进度95卡了很久很久 排查下问题
```

The plan should include normalized project-language facets like:

- `WinPE runtime`
- `driver download`
- `progress reporting`
- `95 percent stall`
- `download completion transition`

Assert selected and rejected concept decisions reflect facet coverage, not raw keyword overlap alone.

- [ ] **Step 2: Add informal English prompt runtime test**

Add a second test using an informal English query, such as:

```text
installer hangs right before finishing the driver fetch
```

Assert the selected concept covers completion/driver-download facets and a tempting but incomplete concept is rejected with `missing_facets`.

- [ ] **Step 3: Preserve partial coverage behavior**

If the runtime already reports `semantic_intake_partial_facet_coverage`, keep that behavior. Do not change it into unconditional `ready`.

- [ ] **Step 4: Run query tests**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query -run "SemanticIntake|Facet|Localized|Informal|ParsePlan" -count=1
Pop-Location
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tools/project-cognition/internal/query/query.go tools/project-cognition/internal/query/query_test.go tools/project-cognition/internal/query/lexicon.go
git commit -m "test: prove semantic intake facet selection"
```

## Task 5: Harden Passive Learning Start

**Files:**
- Modify: `src/specify_cli/learnings.py`
- Modify: `tests/test_learning_cli.py`
- Modify: `templates/passive-skills/spec-kit-project-learning/SKILL.md`

- [ ] **Step 1: Add failing malformed-index tests**

In `tests/test_learning_cli.py`, add tests that write machine data in `.specify/memory/learnings/INDEX.md` with:

- one valid entry
- one legacy entry missing `learning_type`
- one legacy entry missing `problem` but containing `summary`
- one malformed entry that cannot be recovered

Run `learning start --command debug --format json` and assert:

- exit code `0`
- valid and recoverable entries still surface
- malformed entries are skipped
- payload includes warning diagnostics, for example `learning_index_warnings` or `skipped_malformed_index_entries`

- [ ] **Step 2: Add non-cognition workflow coverage**

Parametrize the same malformed-index test over:

```python
("constitution", "map-scan", "map-build")
```

Assert each command exits `0` and returns the same diagnostics shape.

- [ ] **Step 3: Implement tolerant loading**

Replace any list-comprehension style loading that calls `LearningIndexEntry.from_payload(payload)` directly with an iterative loader that collects diagnostics:

```python
entries = []
diagnostics = []
for index, payload in enumerate(payloads):
    try:
        normalized_payload, item_warnings = normalize_learning_index_payload(payload)
        entries.append(LearningIndexEntry.from_payload(normalized_payload))
        diagnostics.extend(item_warnings)
    except Exception as exc:
        diagnostics.append({...})
```

Keep valid entries normal. For recoverable legacy entries:

- missing `problem`: derive from `summary`, `lesson`, `id`, or `recurrence_key`
- missing `lesson`: derive from `evidence` or `problem`
- missing `learning_type`: default to `workflow_gap` and warn
- missing `source_command`: derive from first `applies_to` item when possible, otherwise skip with warning
- invalid `applies_to`: coerce to an empty list

Do not swallow file-level JSON syntax errors silently; return a warning payload that tells the workflow to fall back to direct memory reads.

- [ ] **Step 4: Surface diagnostics in start payload**

Extend `start_learning_session()` output with stable fields:

```json
{
  "warnings": ["..."],
  "learning_index_diagnostics": {
    "normalized_legacy_entries": 1,
    "skipped_malformed_entries": 1,
    "details": [...]
  }
}
```

Keep existing output fields stable for older tests.

- [ ] **Step 5: Align passive learning wording**

Update `spec-kit-project-learning/SKILL.md` so "required preflight memory" means:

- run or attempt `learning start`
- read direct memory files if the helper reports warnings or is unavailable
- never let legacy index parser failures mask the primary workflow unless a command explicitly declares learning as a hard gate

- [ ] **Step 6: Run learning tests**

Run:

```powershell
uv run pytest tests/test_learning_cli.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add src/specify_cli/learnings.py tests/test_learning_cli.py templates/passive-skills/spec-kit-project-learning/SKILL.md
git commit -m "fix: tolerate legacy learning index entries"
```

## Task 6: Preserve Generated Integration Parity

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/claude/templates/implement-teams.md`
- Modify as needed: integration-specific renderers under `src/specify_cli/integrations/**`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Add generated-output assertions**

Assert generated Markdown, TOML, and skill outputs preserve:

- `project-cognition lexicon`
- `semantic_intake`
- object-shaped `alias_interpretations`
- `concept_decisions`
- `covered_facets`
- `missing_facets`
- `match_sources`
- `lexicon_generation_id`
- `project-cognition query`
- `--query-plan`
- `minimal_live_reads`

- [ ] **Step 2: Add Claude Agent Teams parity assertion**

Extend `test_claude_generated_sp_implement_teams_skill_uses_agent_teams_surface` to assert `/sp-implement-teams` includes the same cognition bundle contract as `sp-implement`, including:

- lexicon result
- generated `semantic_intake`
- generated `query_plan`
- warnings or repair hints from `project-cognition query`
- returned readiness
- task-local bundle
- returned `minimal_live_reads`

- [ ] **Step 3: Update renderer/addenda text**

If any generated output lacks the shared contract, update the smallest renderer surface. Prefer shared integration addenda in `base.py`; keep integration-specific edits only for integration-specific surfaces such as Claude Agent Teams.

- [ ] **Step 4: Run integration tests**

Run:

```powershell
uv run pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/specify_cli/integrations tests/integrations
git commit -m "test: preserve cognition intake in generated integrations"
```

## Task 7: Final Cross-Surface Verification

**Files:**
- Review: all modified files
- Modify if needed: `README.md`, `PROJECT-HANDBOOK.md`, `templates/project-handbook-template.md`

- [ ] **Step 1: Run repo search for drift**

Run:

```powershell
rg -n "alias_interpretations|semantic_intake|concept_decisions|lexicon_generation_id|minimal_live_reads|learning start" templates src tests tools README.md PROJECT-HANDBOOK.md
```

Check for:

- string-array examples for `alias_interpretations`
- stale `review` guidance that ignores `minimal_live_reads`
- learning-start wording that says parser failure can block ordinary workflows
- generated integration addenda that omit facet coverage

- [ ] **Step 2: Run targeted verification**

Run:

```powershell
Push-Location tools/project-cognition
go test ./internal/query ./internal/cli -count=1
Pop-Location
uv run pytest tests/test_alignment_templates.py tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_map_runtime_template_guidance.py tests/test_passive_skill_guidance.py tests/test_learning_cli.py -q
uv run pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

- [ ] **Step 3: Run broader smoke if time allows**

Run:

```powershell
uv run pytest tests/test_project_cognition_launcher_rendering.py tests/test_runtime_handbook_contract.py tests/test_specify_guidance_docs.py -q
```

- [ ] **Step 4: Review diff and commit final docs or cleanup**

Run:

```powershell
git diff --check
git status --short
git diff --stat
```

If documentation needed alignment after implementation, commit it:

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests
git commit -m "docs: document cognition intake diagnostics alignment"
```

- [ ] **Step 5: Final acceptance report**

Final implementation closeout must report:

- runtime query diagnostics behavior
- learning-start malformed-index behavior
- template and generated integration coverage
- exact tests run
- any skipped tests and why
- remaining known gaps, especially if any unsupported query-plan shape is intentionally rejected

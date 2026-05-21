# Simplify sp-specify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current lock-kernel-heavy `sp-specify` workflow with a concise Superpowers-style collaborative specification flow while preserving first-release compatibility outputs.

**Architecture:** Rewrite the `sp-specify` command template and shell partial as the product contract, then align the artifact templates, minimal compatibility handoff JSON, docs, and generated integration tests around that contract. Keep `spec.md`, `alignment.md`, `context.md`, `workflow-state.md`, `checklists/requirements.md`, and a minimal `brainstorming/handoff-to-specify.json` as stable outputs; remove the old lock-kernel and lossless-state wording from the normal path.

**Tech Stack:** Python test suite with `pytest`; markdown/json templates under `templates/`; integration generation through `src/specify_cli/integrations/*`.

---

## File Structure

Modify these source templates:

- `templates/commands/specify.md`: primary rewrite from the current long lock-kernel contract to the simplified collaborative flow.
- `templates/command-partials/specify/shell.md`: concise generated-summary contract for the same flow.
- `templates/spec-template.md`: remove lock/lossless sections and keep clean product requirement sections.
- `templates/alignment-template.md`: make semantic traceability the main alignment surface.
- `templates/context-template.md`: remove lock/lossless context and keep planning context.
- `templates/workflow-state-template.md`: simplify `sp-specify` state fields while preserving shared fields other commands still use.
- `templates/checklist-template.md`: keep checklist generation but remove lossless-state checklist items.
- `templates/brainstorming-handoff-specify-template.json`: keep a minimal compatibility handoff with source-file sweep and source-signal disposition fields.
- `README.md`: update current mainline docs away from lossless `sp-specify` state.
- `PROJECT-HANDBOOK.md`: update source-of-truth workflow surface descriptions.
- `templates/project-handbook-template.md`: update generated-project handbook wording if it mirrors old `sp-specify` guidance.

Modify these tests:

- `tests/test_alignment_templates.py`: replace lock-kernel assertions with simplified-flow assertions and artifact-template assertions.
- `tests/integrations/test_integration_base_skills.py`: update generated skill assertions for `sp-specify`.
- `tests/integrations/test_integration_base_markdown.py`: update Markdown integration assertions for discussion handoff intake.
- `tests/integrations/test_integration_base_toml.py`: update TOML integration assertions for discussion handoff intake.
- `tests/integrations/test_integration_codex.py`: update Codex generated `sp-specify` wording assertions.
- `tests/test_specify_guidance_docs.py`: update README/handbook expectations if old lossless wording is asserted.

Do not change `sp-plan`, `sp-tasks`, or `sp-implement` behavior in this pass. Only adjust downstream wording or references if needed to keep the simplified `sp-specify` handoff compatible.

## Task 1: Convert Template Tests To The New sp-specify Contract

**Files:**
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Replace the fixed-heavy lifecycle test**

In `tests/test_alignment_templates.py`, replace `test_specify_template_locks_fixed_heavy_discovery_lifecycle_contract` with a test named:

```python
def test_specify_template_uses_simplified_collaborative_spec_flow() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert "explore project context" in lowered
    assert "one high-impact question at a time" in lowered
    assert "2-3 approaches" in lowered or "two or three approaches" in lowered
    assert "semantic term" in lowered
    assert "user review" in lowered
    assert "source_signal_disposition" in content
    assert "discussion-log.md" in content
    assert "requirements.md" in content
    assert "open-questions.md" in content
    assert "brainstorming/handoff-to-specify.json" in content
    assert "checklists/requirements.md" in content
    assert "facts-lock" not in content
    assert "route-lock" not in content
    assert "intent-lock" not in content
    assert "complexity-lock" not in content
    assert "brainstorming/journal.ndjson" not in content
    assert "stage-manifest.json" not in content
```

- [ ] **Step 2: Replace artifact-template fixed-heavy shape assertions**

Replace `test_specify_artifact_templates_lock_fixed_heavy_discovery_shapes` with:

```python
def test_specify_artifact_templates_use_semantic_traceability_surfaces() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    workflow_state = _read("templates/workflow-state-template.md")
    checklist = _read("templates/checklist-template.md")

    assert "Semantic Term Decisions" in alignment
    assert "Upstream Intent Disposition" in alignment
    assert "Out-Of-Scope Conflicts" in alignment
    assert "User Confirmation" in alignment
    assert "Confirmed Scope" in spec
    assert "Acceptance Proof" in spec
    assert "Planning Context" in context
    assert "last_user_reviewed_artifact_state" in workflow_state
    assert "checklists/requirements.md" in _read("templates/commands/specify.md")

    combined = "\n".join([spec, alignment, context, workflow_state, checklist])
    assert "brainstorming/journal.ndjson" not in combined
    assert "stage-manifest.json" not in combined
    assert "`compiled_from`" not in combined
```

- [ ] **Step 3: Replace lossless source map test**

Replace `test_compiled_artifact_templates_preserve_lossless_source_maps` with:

```python
def test_compiled_artifact_templates_do_not_require_lossless_source_maps() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    checklist = _read("templates/checklist-template.md")

    for content in (spec, alignment, context, checklist):
        assert "Lossless Source Map" not in content
        assert "brainstorming/journal.ndjson" not in content
        assert "brainstorming/stage-manifest.json" not in content
        assert "EVT-" not in content
        assert "EVD-" not in content
        assert "`compiled_from`" not in content
```

- [ ] **Step 4: Strengthen the discussion handoff test**

Update `test_specify_consumes_confirmed_unified_discussion_handoff_without_repair` so it no longer expects `blocked_by_handoff_integrity` or "handoff integrity error" as the core behavior. It should assert the source-file sweep:

```python
assert "read the handoff-declared source files" in lowered
assert "discussion-log.md" in content
assert "requirements.md" in content
assert "open-questions.md" in content
assert "technical-options.md" in content
assert "project-context.md" in content
assert "source_signal_disposition" in content
assert "source_files_read" in content
assert "capability-like" in lowered
assert "not only the handoff summary" in lowered
```

Keep assertions for `entry_source: sp-discussion`, `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count`.

- [ ] **Step 5: Run the targeted tests and confirm RED**

Run:

```powershell
pytest tests/test_alignment_templates.py -q
```

Expected: FAIL. The failures should be caused by the old `sp-specify` templates still containing lock-kernel/lossless wording and missing the new semantic traceability sections.

## Task 2: Rewrite the sp-specify Command And Shell Partial

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/command-partials/specify/shell.md`

- [ ] **Step 1: Replace `templates/command-partials/specify/shell.md`**

Rewrite the file to this concise contract:

```markdown
{{spec-kit-include: ../common/user-input.md}}

## Objective

Turn a new or changed feature request into a reviewed, planning-ready specification package through a concise collaborative flow: understand context, clarify one high-impact question at a time, compare approaches, confirm the spec shape, write artifacts, self-review, and ask the user to review before planning.

## Context

- Primary inputs: the user's request, current repository context, passive memory, project cognition only as advisory navigation, and discussion source files when a discussion handoff is supplied.
- Authoritative outputs: `spec.md`, `alignment.md`, `context.md`, `references.md` when useful, `workflow-state.md`, `checklists/requirements.md`, and a minimal `brainstorming/handoff-to-specify.json` compatibility handoff.
- This command is specification-only. It is not permission to implement code.

## Process

- Create or resume the feature workspace and `workflow-state.md`.
- Explore only enough project context to understand ownership, constraints, adjacent surfaces, and source evidence.
- If invoked from `sp-discussion`, read `handoff-to-specify.md` and `.json` when present, then read the handoff-declared source files. At minimum inspect `discussion-log.md`, `requirements.md`, and `open-questions.md` when they exist; inspect `technical-options.md` and `project-context.md` when present or named.
- Extract every upstream capability-like signal from those sources and assign exactly one disposition: `preserved`, `in_scope`, `deferred`, `dropped`, or `clarification_blocker`.
- Ask one high-impact question at a time when the answer can change scope, acceptance, architecture, compatibility, security, data shape, external integration, or downstream planning.
- Decompose ambiguous terms such as capability, real, usable, works, end-to-end, fetch, probe, health, model, endpoint, integration, auth, `能力`, `真实`, and `可用` before compiling the spec.
- Present two or three approaches with trade-offs and a recommendation before committing to the spec shape.
- Present the spec sections for user approval before final artifact release.
- Write the artifact package, then self-review for placeholders, contradictions, ambiguous requirements, silent scope narrowing, dropped upstream signals, out-of-scope conflicts, missing acceptance proof, and unconfirmed product minimization.
- Ask the user to review the written artifacts before recommending exactly one next command: `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.

## Output Contract

- Write or update `spec.md`, `alignment.md`, `context.md`, `workflow-state.md`, `checklists/requirements.md`, and `references.md` when useful.
- Write or update a minimal `brainstorming/handoff-to-specify.json` compatibility handoff with `version`, `status`, `entry_source`, `source_handoff`, `source_handoff_json`, `source_files_read`, `source_signal_disposition`, `must_preserve`, `coverage_status`, `planning_gate_status`, `hard_unknown_count`, `open_conflict_count`, and `quality_gate`.
- `alignment.md` must record `Semantic Term Decisions`, `Upstream Intent Disposition`, and `Out-Of-Scope Conflicts` when relevant.
- Do not recommend `/sp.plan` while a capability-like upstream signal lacks disposition, an ambiguous high-impact term lacks confirmation, or an out-of-scope conflict lacks user confirmation.
- Report what was confirmed, what remains open, what was deferred or dropped, and the single valid next command.

## Guardrails

- Do not edit source code, tests, or implementation files from `sp-specify`.
- Do not treat the discussion handoff summary as complete when discussion source files exist.
- Do not silently narrow user scope, redefine broad capability terms, or convert the request into a smaller delivery without user confirmation.
- Do not require `brainstorming/journal.ndjson`, `stage-manifest.json`, `facts.json`, `route.json`, `intent.json`, `complexity.json`, or `domains.json` for normal `sp-specify` completion.
- Do not treat this summary block as the workflow itself; the detailed contract below remains authoritative.
```

- [ ] **Step 2: Replace `templates/commands/specify.md` body**

Keep the YAML frontmatter and handoff entries, but update `workflow_contract.primary_outputs` to:

```yaml
primary_outputs: '`FEATURE_DIR/spec.md`, `FEATURE_DIR/alignment.md`, `FEATURE_DIR/context.md`, `FEATURE_DIR/references.md` when useful, `FEATURE_DIR/workflow-state.md`, `FEATURE_DIR/checklists/requirements.md`, and the minimal compatibility handoff `FEATURE_DIR/brainstorming/handoff-to-specify.json`.'
default_handoff: 'After user review, recommend exactly one next command: `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.'
```

Then replace the old detailed body after the common includes with sections matching the design:

- `## Pre-Execution Checks`
- `## Passive Project Learning Layer`
- `## Project Context Intake`
- `## Discussion Source-File Sweep`
- `## Clarification Loop`
- `## Semantic Term Decomposition`
- `## Approach Comparison`
- `## Spec Section Approval`
- `## Artifact Writing Contract`
- `## Artifact Self-Review`
- `## User Review Gate`
- `## Completion Report`
- `## Extension Hooks`
- `## Quick Guidelines`

The command must include the literal strings that tests expect:

- `explore project context`
- `one high-impact question at a time`
- `two or three approaches`
- `Semantic Term Decisions`
- `Upstream Intent Disposition`
- `Out-Of-Scope Conflicts`
- `source_files_read`
- `source_signal_disposition`
- `discussion-log.md`
- `requirements.md`
- `open-questions.md`
- `technical-options.md`
- `project-context.md`
- `checklists/requirements.md`
- `brainstorming/handoff-to-specify.json`

The command must not contain:

- `facts-lock`
- `route-lock`
- `intent-lock`
- `complexity-lock`
- `brainstorming/journal.ndjson`
- `stage-manifest.json`
- `Lossless Source Map`
- `compiled_from`

- [ ] **Step 3: Run focused template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -q
```

Expected: Some tests may still fail because artifact templates are not updated yet. The failures should no longer be from `templates/commands/specify.md` requiring old lock-kernel wording.

## Task 3: Simplify Spec, Alignment, Context, Workflow State, Checklist, And Handoff Templates

**Files:**
- Modify: `templates/spec-template.md`
- Modify: `templates/alignment-template.md`
- Modify: `templates/context-template.md`
- Modify: `templates/workflow-state-template.md`
- Modify: `templates/checklist-template.md`
- Modify: `templates/brainstorming-handoff-specify-template.json`

- [ ] **Step 1: Rewrite `templates/spec-template.md`**

Remove sections named `Brainstorming Truth Inputs`, `Lossless Source Map`, route/complexity lock references, and `compiled_from`.

Keep or add these sections:

```markdown
## Overview *(mandatory)*
### Feature Goal
### Intended Users and Value

## Confirmed Scope *(mandatory)*
### In Scope
### Out of Scope
### Deferred Or Future Scope

## Scenarios and Usage Paths *(mandatory)*
### Primary Scenario - [Brief Title]
### Secondary Scenario - [Brief Title]
### Edge Cases and Failure Paths

## Capability Decomposition *(mandatory)*
### Capability Map
### Capability Relationships

## Requirements *(mandatory)*
### Functional Requirements
### Non-Functional Requirements
### Boundary Constraints

## Acceptance Proof *(mandatory)*
### Acceptance Signals
### Measurable Success Criteria

## Decision Capture *(mandatory)*
### Locked Decisions
### User-Confirmed Deferrals
### Canonical References

## Risks and Gaps *(mandatory)*
```

- [ ] **Step 2: Rewrite `templates/alignment-template.md`**

Replace route/complexity/lossless sections with:

```markdown
# Specification Alignment Report: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`
**Created**: [DATE]
**Status**: [Aligned: ready for plan | Needs clarification | Needs deep research | Force proceed with known risks]

## Current Understanding
## Confirmed Facts
## Low-Risk Assumptions
## Open Questions
## Semantic Term Decisions
| Term | Possible Meanings | Selected Meanings | Excluded Meanings | User Confirmation |
| --- | --- | --- | --- | --- |
## Upstream Intent Disposition
| Signal | Source | Disposition | Artifact Location | User Confirmed | Reopen Trigger |
| --- | --- | --- | --- | --- | --- |
## Deferred Or Dropped Intent
## Out-Of-Scope Conflicts
| Upstream Signal | Source | Spec Disposition | Reason | User Confirmation | Reopen Trigger |
| --- | --- | --- | --- | --- | --- |
## Must-Preserve Coverage
## Readiness Decision
```

Keep `MP-###`, `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` language because the minimal compatibility handoff still uses it.

- [ ] **Step 3: Rewrite `templates/context-template.md`**

Remove duplicate `Brainstorming-Derived Execution Context` sections and `Lossless Source Map`.

Use:

```markdown
# Planning Context: [FEATURE NAME]

## Planning Context
## Relevant Repository Context
## Existing Patterns And Reuse Notes
## Integration Boundaries
## Product Boundary Constraints
## Change Propagation Matrix
## Locked Decisions Carry-Forward
## Canonical References
## Outstanding Questions
## Deferred / Future Ideas
```

Keep consequence sections only if they remain required by existing tests:

- `Affected Object Map`
- `Dependency Impact Table`
- `CA-###`

- [ ] **Step 4: Simplify `templates/workflow-state-template.md`**

Keep shared fields for all commands but change specify-oriented values:

- `current_stage` list should include `context-intake`, `clarification`, `approach-comparison`, `section-approval`, `artifact-writing`, `artifact-review`, `user-review`, plus existing non-specify stages for other commands.
- Remove `Lossless Resume State`, `Legacy Fixed-Heavy Compatibility Labels`, and `Brainstorming Locks`.
- Add:

```markdown
## Review State

- last_user_reviewed_artifact_state: [not-requested | requested | changes-requested | approved]
- source_files_read: [none | discussion source files read | repo context read]
- source_signal_disposition_status: [not-applicable | incomplete | complete]
```

- [ ] **Step 5: Simplify `templates/checklist-template.md`**

Remove `## Lossless State Traceability` and replace it with:

```markdown
## Specification Review

- [ ] No placeholders or unresolved clarification markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Confirmed scope, out-of-scope items, and deferrals are explicit
- [ ] Ambiguous semantic terms have user-confirmed meanings
- [ ] Discussion-originated upstream signals have disposition rows when applicable
- [ ] Out-of-scope conflicts have user confirmation or block planning
```

- [ ] **Step 6: Update `templates/brainstorming-handoff-specify-template.json`**

Keep existing compatibility fields that downstream validators expect, but add:

```json
"source_files_read": [],
"source_signal_disposition": [],
"source_signal_disposition_contract": {
  "required_fields": [
    "signal",
    "source",
    "disposition",
    "artifact_location",
    "user_confirmed",
    "reopen_trigger"
  ],
  "allowed_dispositions": [
    "preserved",
    "in_scope",
    "deferred",
    "dropped",
    "clarification_blocker"
  ]
}
```

Remove or null old normal-path references to `facts_file`, `route_file`, `intent_file`, `complexity_file`, and `compiled_from` only if artifact validation accepts their absence. If validation currently requires them, leave them as compatibility fields but mark them `null` or compatibility-only in the template.

- [ ] **Step 7: Run template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -q
```

Expected: PASS for the updated tests in this file, or limited failures identifying remaining outdated assertions to update in the same file.

## Task 4: Update Integration Tests For Generated sp-specify Surfaces

**Files:**
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Update skills integration assertions**

In `tests/integrations/test_integration_base_skills.py`, replace generated `sp-specify` tests that assert:

- `brainstorming kernel`
- `facts-lock`
- `route-lock`
- `intent-lock`
- `complexity-lock`

with assertions for:

```python
assert "explore project context" in content
assert "one high-impact question at a time" in content
assert "two or three approaches" in content or "2-3 approaches" in content
assert "semantic term" in content
assert "source_signal_disposition" in content
assert "discussion-log.md" in content
assert "requirements.md" in content
assert "open-questions.md" in content
assert "facts-lock" not in content
assert "route-lock" not in content
assert "intent-lock" not in content
assert "complexity-lock" not in content
```

Update `test_specify_skill_preserves_discussion_fidelity_contract` to expect source-file sweep behavior instead of "missing json is a hard handoff integrity blocker".

- [ ] **Step 2: Update Markdown and TOML integration assertions**

In `tests/integrations/test_integration_base_markdown.py` and `tests/integrations/test_integration_base_toml.py`, update `test_specify_command_rejects_bad_discussion_handoffs` to a new name such as `test_specify_command_reads_discussion_sources_for_signal_disposition`.

Assert:

```python
assert "discussion-log.md" in content
assert "requirements.md" in content
assert "open-questions.md" in content
assert "source_signal_disposition" in content
assert "source_files_read" in content
assert "not only the handoff summary" in lowered
assert "handoffs/<candidate_id>" not in content
```

Do not assert `missing json is a hard handoff integrity blocker`, `quality_gate.status`, `current_project_roles`, or `do not reconstruct` unless those phrases remain in the new compatibility language.

- [ ] **Step 3: Update Codex integration assertions**

In `tests/integrations/test_integration_codex.py`, replace `test_codex_generated_sp_specify_uses_brainstorming_kernel_wording` expectations with the simplified flow strings.

Keep negative assertions for obsolete internal routing labels such as `active_profile`, `coverage_mode`, `observer gate`, and `leader-inline-fallback` if still relevant.

- [ ] **Step 4: Run integration test subset**

Run:

```powershell
pytest tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS after template generation emits the simplified `sp-specify` contract.

## Task 5: Update README And Handbook Guidance

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Update docs wording**

Replace statements that describe `sp-specify` as:

- lossless-state backed
- trusted recovery from `brainstorming/journal.ndjson`
- JSON stage artifacts indexed by `stage-manifest.json`
- deterministic `facts-lock`, `route-lock`, `intent-lock`, `complexity-lock`

with:

- collaborative reviewed specification flow
- context exploration
- one-question-at-a-time clarification
- approach comparison
- semantic term decomposition
- written artifact self-review
- user review before `/sp.plan`
- minimal compatibility `brainstorming/handoff-to-specify.json`

- [ ] **Step 2: Keep discussion docs accurate**

Do not rewrite `sp-discussion` as part of this task. Keep its unified handoff pair docs, but add that `sp-specify` reads discussion source files to catch upstream signals missing from the handoff summary.

- [ ] **Step 3: Update docs tests**

In `tests/test_specify_guidance_docs.py`, add or update tests to assert:

```python
assert "one-question-at-a-time" in lowered or "one question at a time" in lowered
assert "approach comparison" in lowered or "two or three approaches" in lowered
assert "semantic term" in lowered
assert "user review" in lowered
assert "brainstorming/journal.ndjson" not in lowered
assert "stage-manifest.json" not in lowered
assert "facts-lock" not in lowered
```

Scope the negative assertions to `README.md`, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md` sections that describe current `sp-specify`, not the historical design docs under `docs/superpowers/specs/`.

- [ ] **Step 4: Run docs tests**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

## Task 6: Validate Compatibility With Scaffolding And Artifact Hooks

**Files:**
- Modify only if needed: `src/specify_cli/hooks/artifact_validation.py`
- Modify only if needed: `tests/hooks/test_artifact_hooks.py`
- Modify only if needed: `scripts/bash/create-new-feature.sh`
- Modify only if needed: `scripts/powershell/create-new-feature.ps1`

- [ ] **Step 1: Run hook and scaffolding tests before changing runtime code**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py tests/integrations/test_cli.py -q
```

Expected: Either PASS, or failures showing validators/scaffolding still require removed fields. Do not remove `brainstorming/handoff-to-specify.json` or `checklists/requirements.md`.

- [ ] **Step 2: If artifact validation fails on removed lock-only fields**

Prefer compatibility over runtime rewrite. Keep required fields in `templates/brainstorming-handoff-specify-template.json` as null or compatibility-only unless the validator can be safely relaxed for missing fields without affecting `sp-plan`.

Only patch `artifact_validation.py` if a check explicitly requires `journal.ndjson`, `stage-manifest.json`, or `compiled_from` for normal `sp-specify` readiness. The patch should allow the simplified first-release compatibility handoff while preserving existing `must_preserve`, `coverage_status`, `planning_gate_status`, hard unknown, conflict, and source evidence validation.

- [ ] **Step 3: Re-run hook and scaffolding tests**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py tests/integrations/test_cli.py -q
```

Expected: PASS.

## Task 7: Final Regression Run And Review

**Files:**
- No planned edits unless prior tasks expose a missed reference.

- [ ] **Step 1: Run focused full regression set**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py tests/hooks/test_artifact_hooks.py tests/integrations/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 2: Search for obsolete current-mainline wording**

Run:

```powershell
rg -n "brainstorming kernel|facts-lock|route-lock|intent-lock|complexity-lock|brainstorming/journal.ndjson|stage-manifest.json|Lossless Source Map|compiled_from" templates README.md PROJECT-HANDBOOK.md tests/integrations tests/test_alignment_templates.py tests/test_specify_guidance_docs.py
```

Expected: No hits in current `sp-specify` guidance or tests. Hits are acceptable only where they refer to unrelated historical docs, package inclusion of compatibility templates, or non-specify workflows that still legitimately use those terms.

- [ ] **Step 3: Review diff for scope creep**

Run:

```powershell
git diff --stat
git diff -- templates/commands/specify.md templates/command-partials/specify/shell.md templates/spec-template.md templates/alignment-template.md templates/context-template.md templates/workflow-state-template.md templates/checklist-template.md templates/brainstorming-handoff-specify-template.json README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md
```

Expected: The diff should only implement the simplified `sp-specify` contract, semantic traceability, minimal compatibility handoff, and doc/test alignment. It should not change `sp-plan`, `sp-tasks`, or `sp-implement` behavior.

- [ ] **Step 4: Commit implementation**

Run:

```powershell
git status --short
git add templates tests README.md PROJECT-HANDBOOK.md
git commit -m "refactor: simplify sp-specify workflow"
```

Expected: Commit succeeds after all targeted tests pass.

## Self-Review Checklist

- Spec coverage: Tasks cover the simplified collaborative flow, source-file sweep, source signal disposition, first-release checklist retention, minimal compatibility handoff retention, docs, tests, and validation compatibility.
- Placeholder scan: This plan contains no `TBD`, `TODO`, "implement later", or unspecified file paths.
- Scope control: The plan does not change `sp-plan`, `sp-tasks`, or `sp-implement` behavior except for compatibility references if required by tests.
- TDD order: Tests are updated before template implementation, then run red/green in focused groups.

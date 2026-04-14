# Phase 12 Research: State Surfaces and End-to-End Verification

## Objective

Research how to reflect the leader/worker runtime truth that now exists in Phase 11 across planning artifacts, shipped implement surfaces, release-facing documentation, and end-to-end verification without redesigning the runtime itself.

## Current Baseline

- Phase 10 established the leader-only `sp-implement` contract in the shared template and generated Codex skill path.
- Phase 11 added persisted runtime truth for:
  - batch classification (`strict` / `mixed_tolerance`)
  - `safe_preparation`
  - join-point metadata
  - `failure_class`
  - `retry_count` / `retry_budget`
  - `retry_pending`
  - `blocker_id`
- Those runtime fields now live primarily in:
  - `src/specify_cli/codex_team/runtime_state.py`
  - `src/specify_cli/codex_team/manifests.py`
  - `src/specify_cli/codex_team/runtime_bridge.py`
  - `src/specify_cli/codex_team/batch_ops.py`
  - `src/specify_cli/codex_team/auto_dispatch.py`
- The planning artifacts and release-facing docs are behind that runtime reality:
  - `.planning/STATE.md` and `.planning/PROJECT.md` still summarize the runtime at a coarse phase-level only
  - `README.md` documents the Codex team runtime surface and lifecycle, but not the new failure/join-point semantics in `sp-implement`
  - generated `sp-implement` surfaces talk about leader-only orchestration and `specify team`, but not the richer batch state truth
- Existing tests already cover many runtime primitives independently, but there is no strong cross-layer regression that says:
  - the runtime state fields exist
  - the planning/artifact surfaces expose them
  - the shared and generated implement surfaces describe them truthfully
  - the whole loop behaves coherently end-to-end

## What Phase 12 Still Needs

### 1. Planning Artifact Surfacing

The project requirement `STAT-01` is not about adding more runtime mechanics. It is about exposing the mechanics that already exist.

Needed artifact-level outcomes:

- planning artifacts should show which workers ran
- open join points should be visible
- advanced tasks/phases should be visible
- blockers and retry states should be visible

The natural targets are:

- `.planning/STATE.md`
- `.planning/PROJECT.md`
- possibly generated status/readout helpers in `src/specify_cli/` if planning artifacts are produced through CLI commands rather than handwritten docs only

This should be built from existing Codex-team runtime files under `.specify/codex-team/state/`, not from a duplicate state source.

### 2. Surface Alignment Across Shared and Generated Implement Outputs

Requirement `STAT-02` implies a stronger drift-prevention matrix:

- shared template: `templates/commands/implement.md`
- generated Codex mirror: `.agents/skills/sp-implement/SKILL.md`
- generated-at-init path: `src/specify_cli/integrations/codex/__init__.py`
- runtime behavior: `codex_team/*`

The current tests already cover some of this, but they focus mostly on:

- leader-only contract
- strategy vocabulary
- `specify team` escalation

Phase 12 should add focused assertions for:

- join-point awareness
- blocker/retry truth
- state-surface phrasing that matches the actual runtime

### 3. Release-Facing Guidance

Requirement `STAT-03` is currently under-served. README already documents `specify team`, but it does not yet clearly teach `/sp.implement` as:

- a milestone-level orchestration leader
- with delegated execution
- with join points and blocker handling
- with mixed failure semantics

Likely documentation targets:

- `README.md`
- possibly `docs/quickstart.md` or other release-facing docs if they mention implement/runtime behavior

Keep this aligned to the shared template rather than inventing a separate documentation story.

### 4. End-to-End Verification

There is still no strong end-to-end check that Phase 10 + 11 + 12 surfaces form a coherent product story.

A useful E2E slice for this repo likely verifies:

- Codex init generates the expected runtime assets
- generated `sp-implement` contains the leader-only + join-point/blocker story
- runtime state payloads round-trip the right fields
- planning/summary/verification artifacts surface those same concepts

This does not need a full interactive runtime simulation if a realistic contract-level integration test can cover the flow.

## Natural Extension Points

### Runtime truth source

- `src/specify_cli/codex_team/runtime_state.py`
- `src/specify_cli/codex_team/manifests.py`
- `src/specify_cli/codex_team/batch_ops.py`
- `src/specify_cli/codex_team/runtime_bridge.py`

### Planning/document surfaces

- `.planning/STATE.md`
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md` only if traceability text needs tightening
- CLI status/help surfaces in `src/specify_cli/__init__.py` if they produce human-readable summaries

### Shared/generated implement surfaces

- `templates/commands/implement.md`
- `.agents/skills/sp-implement/SKILL.md`
- `src/specify_cli/integrations/codex/__init__.py`
- `tests/test_alignment_templates.py`
- `tests/integrations/test_integration_codex.py`

### E2E / contract verification

- `tests/contract/`
- `tests/integrations/`
- potentially a new focused state-surface regression test file rather than overloading unrelated suites

## Risks and Traps

### Trap 1: Re-implementing Phase 11 in Phase 12

Phase 12 should surface and validate runtime truth, not rebuild dispatch/blocker mechanics. If implementation starts changing failure policy again, the phase is drifting backwards.

### Trap 2: Making docs more detailed than the actual product

The README and generated skill surfaces must not describe a richer UX than the runtime can actually provide. The docs should reflect:

- what the leader does
- what `specify team` does
- what runtime state is visible

But should avoid implying a polished runtime dashboard that does not exist.

### Trap 3: Creating a second source of truth

Planning artifacts should derive from the existing runtime state and shared template. If Phase 12 adds independent prose that can drift from runtime files, `STAT-02` will never stay stable.

### Trap 4: Weak end-to-end tests

If E2E coverage only checks file existence, it will miss semantic drift. At least one verification path should assert concrete strings/fields that link runtime state, generated surfaces, and artifact summaries together.

## Planning Implications

### Recommended split is correct

#### 12-01: Persist runtime state and align shipped implement surfaces

This plan should focus on:

- surfacing runtime truth in planning/project state artifacts
- aligning shared template and generated Codex surface wording to the now-shipped runtime semantics
- adding targeted regression coverage for that alignment

Most likely files:

- `.planning/STATE.md`
- `.planning/PROJECT.md`
- `templates/commands/implement.md`
- `.agents/skills/sp-implement/SKILL.md`
- `src/specify_cli/integrations/codex/__init__.py`
- `README.md`
- alignment/integration tests

#### 12-02: Add end-to-end verification and release-facing guidance

This plan should focus on:

- release-facing docs for the leader/worker runtime
- cross-layer regression tests
- end-to-end verification that the milestone-level loop expectations are coherent

Most likely files:

- `README.md`
- docs under `docs/` if implement/runtime guidance appears there
- `tests/contract/`
- `tests/integrations/`
- possibly a new focused `tests/test_runtime_state_surfaces.py` or similar

## Verification Expectations

Phase 12 should prove:

1. Planning artifacts surface worker outcomes, join points, and blockers
2. Shared and generated implement surfaces match runtime truth
3. Release-facing docs describe the same runtime truth
4. End-to-end verification catches drift across these layers

## Recommendation Summary

Implement Phase 12 in this order:

1. Surface runtime truth into planning/project artifacts and status surfaces
2. Align shared template and generated Codex surfaces to that truth
3. Update release-facing docs
4. Add cross-layer and end-to-end verification last

That ordering minimizes rework and matches the user’s chosen priority.

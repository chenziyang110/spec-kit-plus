# Unified Scan Freshness / Git Baseline Design

**Date:** 2026-05-04
**Status:** Approved
**Owner:** Codex
**Scope:** Introduce a shared git-based freshness contract for `sp-map-scan`,
`sp-prd-scan`, and `sp-test-scan`; reduce correctness dependence on
`mark-dirty` hooks; and add workflow-specific incremental classifiers and
status surfaces across CLI, templates, docs, and tests
**Primary goal:** Make scan freshness and incremental refresh detection derive
from repository reality instead of hook reliability

## Summary

This design standardizes freshness detection for the three repository-scan
workflows:

```text
sp-map-scan
sp-prd-scan
sp-test-scan
```

The core decision is simple:

- freshness truth comes from `git` plus the current working tree
- hook-triggered `mark-dirty` becomes a manual override, not the primary source
  of truth
- each scan workflow gets a stable status file that stores its last successful
  refresh baseline and incremental refresh metadata

The incremental comparison model is:

```text
last_refresh_commit -> current working tree
```

where "current working tree" includes:

- committed changes after the baseline commit
- staged changes
- unstaged changes
- untracked files

This is intentionally stronger than comparing only the current branch tip or
only `HEAD`, because scan freshness must not miss unfinished local changes.

`project-map` already approximates this model through
`.specify/project-map/index/status.json` and git diff-based freshness helpers.
This design generalizes that pattern into a shared contract, preserves
project-map compatibility, and extends equivalent incremental detection to PRD
and testing scans.

## Problem Statement

The repository now has an inconsistent freshness model across scan workflows.

### 1. `project-map` has a stronger freshness model than the other scan lanes

`project-map` already stores refresh metadata and compares a saved commit
against the current repository state. That makes it possible to detect stale
atlas content even when no explicit "dirty" marker was written.

By contrast, `sp-prd-scan` and `sp-test-scan` have run-state artifacts, but no
equivalent stable git-baseline freshness contract. They can produce excellent
scan packages, yet they do not have a first-class, durable way to answer:

- what repository baseline was this scan based on?
- what changed since then?
- does the existing scan output remain trustworthy?
- is the next scan a targeted refresh or a full refresh?

### 2. `mark-dirty` is useful but not reliable enough to be the truth source

The current `mark-dirty` path depends on workflow discipline and installation
quality:

- an agent must remember to call it
- the generated integration must expose the right command surface
- the active runtime or CLI must actually support the intended hook path
- the hook must fire in the expected execution path

That is good enough for an early warning signal, but not good enough for the
primary correctness boundary. If repository truth changed and the hook did not
run, freshness detection must still fail closed.

### 3. Branch-only or commit-only comparisons are too weak

A branch pointer or branch hash alone misses important realities:

- local staged changes
- unstaged edits
- newly created untracked files

Those are exactly the kinds of changes that can invalidate map, PRD, or
testing scan outputs during real development. A freshness model that ignores
them is not strong enough.

## Goals

- Standardize freshness detection for `sp-map-scan`, `sp-prd-scan`, and
  `sp-test-scan`.
- Use git-baseline diffing as the canonical freshness truth source.
- Preserve compatibility with the current `project-map` status file while
  moving its core logic toward a shared contract.
- Add first-class stable freshness state for PRD and testing scan workflows.
- Support incremental refresh decisions:
  - `fresh`
  - `targeted-stale`
  - `full-stale`
- Keep workflow-specific classifiers separate from the shared git-baseline
  engine.
- Downgrade `mark-dirty` from correctness dependency to manual override.
- Preserve fail-soft behavior for non-git repositories without falsely
  reporting `fresh`.
- Roll the change out across code, templates, CLI surfaces, docs, and tests.

## Non-Goals

- Do not remove `mark-dirty` or `complete-refresh` entirely.
- Do not replace workflow run-state files such as
  `.specify/testing/testing-state.md` or
  `.specify/prd-runs/<run-id>/workflow-state.md`.
- Do not require every scan workflow to share identical classifiers. The shared
  model is the git baseline contract, not the stale-surface policy.
- Do not define content-level semantic diffs for every file type. Path-driven
  incremental classification is sufficient for this stage.
- Do not claim exact targeted-refresh support for every future scan variant on
  day one. The design allows phased classifier depth.

## User-Approved Direction

This design reflects the following explicit review decisions:

1. `sp-prd-scan` and `sp-test-scan` should gain incremental freshness
   detection, not only `project-map`.
2. The recommended comparison basis is the strongest option:
   `last_refresh_commit -> current working tree`, including tracked and
   untracked local changes.
3. `mark-dirty` should no longer be the primary freshness truth source for
   `map-scan/build`.
4. If git-based diffing is robust enough, it should become the main freshness
   model across the scan workflows.
5. The implementation plan should optimize for quality rather than minimum
   code churn.

## Decision Summary

Ship a shared scan freshness contract built on git-baseline diffing.

### Canonical model

For every supported scan family:

- record the last successful refresh baseline commit
- inspect the current working tree against that baseline
- classify changed paths into workflow-specific impact buckets
- return one of:
  - `fresh`
  - `targeted-stale`
  - `full-stale`

### Stable status surfaces

- `project-map`
  - keep `.specify/project-map/index/status.json`
- `test-scan`
  - add `.specify/testing/status.json`
- `prd-scan`
  - add `.specify/prd/status.json`

### Hook role

- keep `mark-dirty`
- keep `complete-refresh`
- redefine `mark-dirty` as a manual stale override path
- keep hook usage as a convenience path and early warning signal
- remove correctness dependence on hook execution

## Approaches Considered

### Approach A: Keep hook-driven `mark-dirty` as the primary freshness signal

Use `mark-dirty` as the main invalidation mechanism and keep git diffing as a
secondary aid.

**Pros**

- smallest implementation delta
- preserves existing operator mental model
- avoids introducing new status surfaces immediately

**Cons**

- still depends on hook availability and agent behavior
- still allows freshness false negatives when hooks do not run
- does not solve the missing incremental contract for PRD and testing scans

**Decision**

Rejected.

### Approach B: Shared git-baseline contract plus workflow-specific classifiers

Use git-baseline diffing as the primary freshness engine. Let each scan family
map changed paths to its own targeted/full refresh decision.

**Pros**

- strongest correctness model
- works even when hooks are unavailable or skipped
- aligns naturally with the existing `project-map` direction
- creates one reusable freshness engine with three policy layers
- supports targeted refresh expansion over time

**Cons**

- larger initial implementation surface
- requires new status files for PRD and testing
- requires careful classifier tests to avoid excessive full rescans

**Decision**

Accepted.

### Approach C: Content-hash snapshots without git dependency

Maintain custom path/hash manifests per scan workflow instead of relying on git
history and working-tree diffs.

**Pros**

- could theoretically work outside git
- independent of repository VCS conventions

**Cons**

- duplicates capabilities git already provides
- more state to maintain and validate
- weaker ergonomics for a repository that already assumes git in many flows

**Decision**

Rejected.

## Architecture Overview

The design splits freshness into three layers.

### 1. Shared git-baseline engine

This layer owns:

- reading and writing stable status files
- resolving the baseline commit and branch metadata
- collecting changed files from:
  - `baseline_commit..HEAD`
  - staged diff
  - unstaged diff
  - untracked files
- normalizing changed path lists
- returning a common freshness payload

This layer does not decide workflow-specific meaning beyond generic freshness
structure.

### 2. Workflow-specific classifiers

Each scan family adds a classifier that maps changed paths into:

- affected surfaces
- affected modules or capability groups
- refresh scope recommendation:
  - `none`
  - `targeted`
  - `full`
- reasons

These classifiers are intentionally separate because map, PRD, and testing
scans care about different repository truths.

### 3. Workflow-facing command and template surfaces

CLI commands, shell helpers, templates, and hooks consume the shared engine and
workflow-specific classifiers to:

- display freshness status
- decide whether a scan can be resumed or trusted
- route the user to targeted refresh or full refresh
- finalize a successful refresh by updating the baseline

## Shared Freshness Contract

Every scan family should expose the same conceptual status payload.

### Required persisted fields

- `version`
- `last_refresh_commit`
- `last_refresh_branch`
- `last_refresh_at`
- `last_refresh_scope`
- `last_refresh_basis`
- `last_refresh_changed_files_basis`
- `manual_force_stale`
- `manual_force_stale_reasons`

### Optional persisted fields

- `latest_run_id`
- `latest_artifact_set`
- `last_refresh_topics`
- `last_refresh_modules`
- `last_refresh_capabilities`

The optional fields allow targeted refresh semantics without forcing all
workflow families to carry identical scopes.

### Required computed output

Every freshness check should be able to return:

- `status_path`
- `has_git`
- `head_commit`
- `last_refresh_commit`
- `freshness`
- `changed_files`
- `affected_surfaces`
- `affected_units`
- `recommended_refresh_scope`
- `reasons`
- `manual_force_stale`
- `manual_force_stale_reasons`

### Freshness values

- `fresh`
  - no relevant differences invalidate the prior scan baseline
- `targeted-stale`
  - differences exist, but classifier scope can stay localized
- `full-stale`
  - differences invalidate the scan family broadly enough that a full refresh
    is required
- `possibly-stale`
  - non-git or baseline-missing fail-soft result; not safe to claim `fresh`

`possibly-stale` remains necessary for non-git or incomplete-baseline cases,
but the primary design target is the stronger three-way incremental decision
above.

## Git Comparison Model

The canonical changed-file set is the union of:

1. `git diff --name-status --find-renames <baseline_commit>..HEAD`
2. `git diff --name-status --find-renames --cached`
3. `git diff --name-status --find-renames`
4. `git ls-files --others --exclude-standard`

This model is intentionally chosen because it captures:

- committed changes after the last successful scan baseline
- staged changes not yet committed
- working tree edits not yet staged
- newly created untracked files

### Why branch hash is metadata, not truth

The branch name and current branch tip remain useful to persist and display, but
they are not sufficient as the correctness boundary. A user can invalidate scan
outputs without changing the saved branch pointer in any durable way.

Therefore:

- persist `last_refresh_branch` for operator clarity
- persist `last_refresh_commit` as the real baseline
- derive freshness from diff-to-working-tree, not branch-pointer drift

## Workflow-Specific Status Surfaces

### `project-map`

Keep the existing status file:

```text
.specify/project-map/index/status.json
```

This file remains the stable atlas freshness entry point. The implementation
should migrate its git-baseline and status semantics onto the new shared engine
without breaking the existing command surface.

### `test-scan`

Add:

```text
.specify/testing/status.json
```

This file owns testing scan freshness only. It does not replace:

```text
.specify/testing/testing-state.md
```

`testing-state.md` remains the workflow execution/resume file. `status.json`
becomes the durable freshness baseline file.

### `prd-scan`

Add:

```text
.specify/prd/status.json
```

This file owns PRD scan freshness only. It does not replace:

```text
.specify/prd-runs/<run-id>/workflow-state.md
```

Run-local state remains per-run; freshness baseline remains stable and
cross-run.

## Workflow-Specific Classifier Policy

### 1. `project-map` classifier

The map classifier already has strong topic-based routing. Preserve that model
and adapt it to the shared engine.

Typical `full-stale` triggers:

- workflow/command surface changes
- integration boundary changes
- architecture/documentation truth surface changes
- dependency/config/runtime-shape changes
- atlas-owned source-of-truth file changes

Typical `targeted-stale` triggers:

- limited source-tree changes that map cleanly to specific atlas topics
- test-only changes that require `TESTING.md` and related review
- script-only changes that require `OPERATIONS.md` refresh

### 2. `test-scan` classifier

The testing classifier should distinguish between module-local and system-level
testing changes.

Typical `targeted-stale` triggers:

- source changes localized to one module or package
- new or modified tests inside one module boundary
- local fixtures or helper changes with narrow blast radius

Typical `full-stale` triggers:

- test runner, framework, or workspace configuration changes
- CI or presubmit test pipeline changes
- dependency or coverage configuration changes
- module topology or public entrypoint boundary changes that invalidate lane
  assumptions broadly

The classifier should return affected modules and affected testing surfaces so
`sp-test-scan` can choose a targeted scan when safe.

### 3. `prd-scan` classifier

The PRD classifier should map changed paths to:

- capability surfaces
- artifact surfaces
- boundary surfaces

Typical `targeted-stale` triggers:

- bounded feature changes within a known module/capability
- local UI/API/documentation updates that do not change cross-system topology
- tests that reveal a capability-specific behavior update

Typical `full-stale` triggers:

- cross-capability workflow changes
- shared data-model or contract changes
- route/command/integration boundary changes
- module ownership restructuring
- config or runtime changes that alter system-level behavior across multiple
  capabilities

The classifier should return affected capability or boundary identifiers when
safe, but must escalate to `full-stale` when reconstruction confidence becomes
too low.

## `mark-dirty` and Hook Semantics

### New role for `mark-dirty`

`mark-dirty` becomes a manual override, not the primary freshness truth source.

Its allowed purposes are:

- operator forces a workflow family stale
- agent knows a truth surface changed but cannot complete refresh in the
  current pass
- explicit escalation note for a later workflow

It should write:

- `manual_force_stale: true`
- `manual_force_stale_reasons: [...]`

It may also keep compatibility fields required by existing surfaces, but its
semantic meaning is manual override.

### New role for `complete-refresh`

`complete-refresh` remains necessary and becomes the standard baseline finalizer
for a successful refresh.

It should:

- validate that the required canonical outputs exist for that scan family
- write the new `last_refresh_commit`
- write the new `last_refresh_branch`
- write the new `last_refresh_at`
- write scope metadata for targeted refresh support
- clear `manual_force_stale`
- clear `manual_force_stale_reasons`

### Hook posture

Hooks are still valuable, but their role changes:

- good for early warning
- good for workflow convenience
- good for shared generated command surfaces
- not required for correctness

If hooks do not run, the next scan command must still detect stale state from
git diffs alone.

## CLI and Helper Surface Changes

### Shared engine

Introduce a shared freshness module that owns the common git-baseline logic.

`project_map_status.py` should stop being the de facto generic implementation
surface. Instead:

- shared freshness engine owns baseline diffing and generic status contract
- `project_map_status.py` owns project-map-specific policy and compatibility
- test and PRD scan helpers build on the same shared engine

### CLI surface

Add aligned status/check/refresh support for testing and PRD scan families so
operators and templates can query them the same way they query project-map
freshness.

### Shell surface

Keep shell and PowerShell helper entrypoints, but move correctness-critical
logic into the Python shared engine where practical. Shell scripts should become
thin wrappers instead of the primary implementation home for the policy.

## Template and Workflow Contract Changes

### `sp-map-scan` / `sp-map-build`

- keep the current atlas freshness gate
- change the guidance so `mark-dirty` is described as a fallback/manual path
- keep `complete-refresh` as the canonical successful-refresh finalizer

### `sp-test-scan`

- add explicit read of `.specify/testing/status.json`
- check testing freshness before trusting previous scan outputs
- use targeted vs full refresh wording based on classifier output
- continue to treat `PROJECT-HANDBOOK.md` and project-map freshness as upstream
  context inputs, but not as substitutes for testing freshness

### `sp-prd-scan`

- add explicit read of `.specify/prd/status.json`
- decide whether existing reconstruction outputs remain trustworthy
- route to targeted PRD rescan or full PRD rescan based on classifier output
- continue to use project-map freshness as brownfield context, but not as the
  only stale signal

## Migration and Rollout Plan

### Phase 1: Shared engine plus project-map migration

- extract shared git-baseline logic
- migrate `project-map` to use it without breaking current status file
- preserve current CLI behavior while reducing duplicated shell logic

### Phase 2: Testing freshness

- add `.specify/testing/status.json`
- add test-scan classifier
- add testing status/check/finalize support
- update `sp-test-scan` templates and related docs/tests

### Phase 3: PRD freshness

- add `.specify/prd/status.json`
- add PRD scan classifier
- add PRD status/check/finalize support
- update `sp-prd-scan` and related docs/tests

### Phase 4: Hook and documentation convergence

- update wording around `mark-dirty`
- update shared docs and generated templates
- ensure all supported integrations describe git-baseline freshness correctly

## Testing Strategy

The rollout should add regression coverage at three levels.

### 1. Shared engine tests

- baseline commit present vs missing
- git repo vs non-git repo
- committed changes after baseline
- staged-only changes
- unstaged-only changes
- untracked-only changes
- rename handling
- manual stale override behavior

### 2. Workflow classifier tests

- `project-map` targeted vs full refresh routing
- `test-scan` module-local vs system-wide stale routing
- `prd-scan` capability-local vs cross-boundary stale routing

### 3. Contract and template tests

- generated templates read the new status surfaces
- command guidance describes `mark-dirty` as manual override/fallback
- finalization paths use `complete-refresh` semantics consistently
- docs and help text reflect the unified model

## Risks and Mitigations

### Risk: over-classifying into `full-stale`

If PRD or testing classifiers are too coarse, incremental refresh loses value.

**Mitigation**

- start conservative but add explicit targeted cases backed by tests
- return `targeted-stale` only when scope confidence is defensible
- prefer correctness over optimistic narrowing

### Risk: partial refresh metadata becomes ambiguous

If a workflow says it performed a partial refresh but does not persist what it
actually refreshed, later incremental logic can become unsound.

**Mitigation**

- persist explicit scope metadata such as topics, modules, or capabilities
- treat missing scope detail as ineligible for fine-grained targeted reuse

### Risk: duplicated logic remains in shell helpers

If the Python engine and shell helpers both evolve policy independently, drift
returns quickly.

**Mitigation**

- keep shell helpers thin
- centralize comparison and classification logic in Python

### Risk: non-git repositories get misleading results

If non-git mode reports `fresh`, the contract becomes unsafe.

**Mitigation**

- never report `fresh` when git baseline truth is unavailable
- return `possibly-stale` and route operators accordingly

## Acceptance Criteria

This design is complete when the implementation can satisfy all of the
following:

1. `project-map`, `test-scan`, and `prd-scan` each have a stable freshness
   status surface.
2. Freshness is computed from git-baseline diffing against the current working
   tree, not from hook execution alone.
3. `mark-dirty` no longer acts as the primary correctness source.
4. `complete-refresh` finalizes successful scan refreshes by writing new git
   baseline metadata.
5. `sp-test-scan` and `sp-prd-scan` can distinguish targeted stale from full
   stale for at least an initial conservative rule set.
6. Non-git or baseline-missing cases fail soft without claiming `fresh`.
7. Templates, CLI messaging, and tests all reflect the new model consistently.

## Recommended Implementation Order

1. Build the shared freshness engine and migrate `project-map`.
2. Add testing freshness state and classifier support.
3. Add PRD freshness state and classifier support.
4. Converge hooks, templates, docs, and integration tests on the new semantics.

This order keeps the highest-risk correctness layer first, proves the shared
engine against an existing consumer, and then extends the contract across the
remaining scan families.

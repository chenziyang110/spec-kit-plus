# Project Cognition Refresh Contract and Freshness Classification Design

**Date:** 2026-05-10  
**Status:** Approved  
**Owner:** Codex

## Summary

This design fixes a product-contract contradiction in the project cognition
runtime:

- `sp-map-update` can currently report that refresh work completed
- the next workflow preflight can immediately classify the runtime as stale
- the user is then told to run `sp-map-update` again, even when the prior run
  already recorded its update and the real blocker is a different rule

That behavior is not a minor copy issue. It means the command that produces
refresh state and the commands that consume refresh state do not share the same
definition of completion.

The approved direction is:

- make `sp-map-update` completion semantics match the same freshness evaluator
  used by preflight
- separate runtime-truth inputs from tool-managed support inputs and
  reference/export artifacts
- classify stale states by cause instead of treating every meaningful drift as
  the same `stale` outcome
- make next-step guidance depend on the stale class so the system recommends an
  action that can actually change the result

This is a shared runtime fix, not a single-workflow wording change. It must be
implemented in the common freshness, hook, CLI, template, and documentation
surfaces that define project cognition behavior across the product.

## Problem

The current flow has two conflicting success models.

`sp-map-update` behaves like a state producer. It can record an incremental
update, write status data, and present the run as refreshed.

Preflight behaves like a state consumer. It recomputes freshness from the live
working tree and blocks when that recomputation says the runtime remains stale.

Those two models are not aligned. A user can therefore receive all of the
following signals in sequence:

1. refresh work executed
2. status was written
3. refresh was presented as complete
4. the next workflow is blocked as stale
5. the system recommends running the same refresh command again

That contradiction has two root causes.

### 1. Completion is defined by write success, not readiness success

The current contract effectively treats "incremental refresh data was recorded"
as equivalent to "the runtime is now ready for downstream workflows". Those are
different outcomes and must remain separate.

### 2. Freshness classification is too coarse

The current classification model mixes multiple input kinds together. When
tool-managed support files drift, the runtime can still be reported as stale in
the same way as true runtime-truth drift. That forces the same next-step
guidance even when the blocking reason is materially different.

The result is a trust failure:

- the system says refresh succeeded
- the system then says refresh did not succeed
- the system suggests an action that may not resolve the actual cause

## Goals

- Make refresh completion semantics consistent across `sp-map-update`,
  `project-map` inspection, workflow preflight, and brownfield workflow entry.
- Distinguish "refresh data was recorded" from "the runtime is ready for
  downstream workflows".
- Reduce false hard-blocks caused by tool-managed support inputs being treated
  like runtime-truth drift.
- Ensure guidance recommends only actions that are appropriate for the detected
  freshness class.
- Keep the solution shared across CLI integrations and generated workflow
  surfaces.

## Non-Goals

- Do not weaken the requirement for a trustworthy project cognition runtime
  before brownfield planning workflows continue.
- Do not make preflight trust static status files without verification.
- Do not solve every future freshness policy edge case in this change.
- Do not hide partial refresh outcomes behind optimistic success copy.

## Approved Direction

### 1. Shared Completion Contract

`sp-map-update` must stop using "update record written" as its success
definition.

Instead, the command must finish by evaluating the same freshness contract used
by downstream consumers. The terminal outcome must distinguish at least these
states:

- `refresh_applied_and_ready`
- `refresh_recorded_but_blocked`

`refresh_applied_and_ready` means the update was recorded and the shared
freshness evaluator now considers the runtime usable for the intended next-step
workflows.

`refresh_recorded_but_blocked` means the update was recorded but the runtime is
still not ready. That result is still useful and should remain visible, but it
must not be presented as a completed refresh.

The key rule is:

- no command may claim refresh completion unless the shared evaluator agrees the
  runtime is ready

### 2. Freshness Input Model

Freshness classification must distinguish three input layers.

#### Runtime-Truth Inputs

These are inputs that directly affect the meaning or trustworthiness of the
project cognition runtime. Drift here can invalidate downstream reasoning and
may justify a hard block.

#### Tool-Managed Support Inputs

These are inputs related to tooling, templates, generated support surfaces,
maintenance helpers, or other non-truth support assets. Drift here may still be
important, but it should not automatically be treated as equivalent to
runtime-truth invalidation.

By default, this layer should degrade to `support_drift` or
`possibly_stale`-style handling rather than a hard runtime-stale block, unless
the current command explicitly depends on support-surface consistency.

#### Reference and Export Artifacts

These are outputs, records, and derived artifacts that explain or export state
but do not define runtime freshness. They should never be allowed to drive the
primary runtime-stale conclusion by themselves.

### 3. State and Guidance Must Be Separate Fields

Every freshness evaluation should return both:

- a factual `state`
- a policy-derived `recommended_next_action`

The state describes what is true. The recommendation describes the next action
most likely to resolve or correctly handle that state.

The approved state vocabulary is:

- `fresh`
- `runtime_stale`
- `support_drift`
- `missing_baseline`
- `partial_refresh`

The approved next-action vocabulary is:

- `retry_current_workflow`
- `run_map_update`
- `run_map_scan_build`
- `commit_or_ignore_support_files`
- `review_policy_configuration`

The critical rule is that stale guidance must become class-aware:

- recommend `run_map_update` only when the state is truly refreshable through a
  localized runtime update
- recommend `run_map_scan_build` only when the usable baseline is missing or
  must be rebuilt
- recommend support-surface handling when support drift, not runtime-truth
  drift, is the blocker

The system must not recommend `sp-map-update` when re-running that command is
unlikely to change the result.

### 4. Command Semantics

#### `sp-map-update`

`sp-map-update` must:

- record refresh work
- run post-refresh verification through the shared evaluator
- surface terminal status using the shared state vocabulary
- print the correct next action for the detected state

It must not emit "refresh complete" copy when the shared evaluator still
returns a blocked state.

#### Workflow Preflight

Preflight must consume the same state structure and recommendation structure
used by `sp-map-update`.

When preflight blocks, it must explain whether the block came from:

- runtime-truth staleness
- support-surface drift
- missing baseline
- a partial refresh that did not reach ready state

It must then recommend the next action that matches that cause. It must not
collapse every blocked outcome into "run `sp-map-update` again".

#### Inspection Commands

`project-map` inspection commands and any CLI status helpers must expose the
same state classification and next-action classification so that the user sees
one consistent interpretation everywhere.

### 5. Verification and Rollout

This change must be protected by shared regression coverage, not only by manual
testing.

#### Contract Coverage

Tests must verify that `sp-map-update`, preflight, and inspection commands
produce the same state class and next-action class for the same repository
state.

#### Behavior Coverage

Tests must cover at least:

- runtime-truth drift that legitimately requires refresh
- support-only drift that should not be treated as equivalent runtime failure
- missing baseline behavior
- partial refresh behavior where update recording succeeds but readiness does
  not

#### UX Coverage

Tests must assert that:

- ready-state success copy is never emitted for blocked outcomes
- `sp-map-update` is not re-recommended when it is not the appropriate next
  action
- downstream workflows do not contradict a ready-state success that was just
  emitted by the refresh command

#### Documentation Coverage

README, PROJECT-HANDBOOK, relevant templates, and generated guidance must all
describe:

- the difference between recorded refresh and ready refresh
- the freshness state classes
- the allowed next actions for each class

## Files Affected

- `src/specify_cli/project_map_status.py`
- `src/specify_cli/hooks/preflight.py`
- `src/specify_cli/hooks/project_map.py`
- `src/specify_cli/__init__.py`
- shared freshness helper scripts under `scripts/bash/` and
  `scripts/powershell/`
- workflow templates and passive guidance that explain project cognition gates
- README and PROJECT-HANDBOOK
- regression tests for freshness classification, hook behavior, and workflow
  guidance consistency

## Acceptance Criteria

- `sp-map-update` never reports refresh completion unless the shared freshness
  evaluator considers the runtime ready.
- A refresh run that records work but remains blocked is surfaced as a distinct
  partial outcome rather than a false success.
- Tool-managed support drift is not treated by default as the same hard stale
  class as runtime-truth drift.
- Freshness results expose both a factual state and a next-action recommendation.
- `sp-specify` preflight no longer responds to every blocked outcome by
  recommending `sp-map-update`.
- Shared docs and generated workflow guidance describe the new contract
  consistently.

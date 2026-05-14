# Project Cognition Acceptance Gates Design

**Date:** 2026-05-14  
**Status:** Draft for review  
**Scope:** `sp-map-scan`, `sp-map-build`, `sp-map-update`, project cognition validation commands, refresh finalizers, artifact validation, generated workflow guidance, and regression tests  
**Primary goal:** Make the first brownfield cognition build a complete, query-ready baseline, then keep later code changes fast through bounded `sp-map-update` refreshes.

## Summary

Downstream projects should have a simple cognition lifecycle:

1. On first use for an existing codebase, run `sp-map-scan` followed by
   `sp-map-build`.
2. When that pair completes, the repository is fully scanned for the accepted
   scope, the SQLite cognition graph is query-ready, and other workflows can
   proceed without being sent back through the initial rebuild path.
3. After later code changes, use `sp-map-update` for fast incremental
   maintenance.
4. Escalate back to `sp-map-scan -> sp-map-build` only when the baseline is
   missing, unusable, schema-incompatible, or the affected closure cannot be
   bounded safely.

The current system can record freshness without proving query readiness. That
allows a bad state where `status.json` says `fresh` while
`project-cognition query` returns `needs_rebuild`. This design closes that gap
by adding explicit scan and build acceptance gates, then making refresh
finalizers depend on those gates.

## Problem

`sp-map-scan` and `sp-map-build` currently have process-oriented completion
language, but the machine checks are too weak.

Concrete failure mode:

- a project runs `sp-map-scan`
- a project runs `sp-map-build`
- a later `sp-map-update` or refresh finalizer records freshness metadata
- `sp-specify` queries project cognition and receives `needs_rebuild`

From the user's point of view, this is contradictory. They already ran the
initial scan and build. The real issue is that "workflow ran" and "runtime is
query-ready" are not the same state.

The system must prevent these split states:

- `fresh` metadata with no `.specify/project-cognition/project-cognition.db`
- a DB file with no active generation
- a DB file with incompatible or unreadable schema
- `sp-map-update` reporting completion after its update helper returned
  `needs_rebuild`
- `complete-refresh` marking a baseline fresh before query readiness is proven

## Goals

- Define acceptance standards for `sp-map-scan` and `sp-map-build`.
- Make acceptance machine-checkable through public `project-cognition`
  commands.
- Ensure `complete-refresh` cannot write `fresh` unless build acceptance passes.
- Preserve the intended lifecycle: first full build, then fast incremental
  updates.
- Give downstream workflows specific blocked reasons when cognition is not
  ready.
- Keep the acceptance model compatible with existing artifact validation and
  generated workflow templates.

## Non-Goals

- Do not redesign graph extraction, claim synthesis, or query ranking.
- Do not require `sp-map-update` to handle every possible repository change.
  It should escalate when a bounded update cannot be proven safe.
- Do not reintroduce `.specify/project-map/**` as runtime truth.
- Do not make ordinary workflows rebuild cognition opportunistically after
  every change.

## Accepted Lifecycle

### First Brownfield Baseline

The first accepted baseline for an existing downstream project is:

```text
sp-map-scan -> sp-map-build
```

`sp-map-scan` produces a complete scan package for the intended repository
scope. `sp-map-build` consumes that package and publishes the query-backed
SQLite runtime.

After both gates pass, downstream workflows such as `sp-specify`, `sp-plan`,
`sp-tasks`, `sp-implement`, `sp-fast`, `sp-quick`, and `sp-debug` should treat
project cognition as available. They may still perform minimal live reads
returned by `project-cognition query`, but they should not route back to
`sp-map-scan -> sp-map-build` unless a later readiness check proves the baseline
is missing or unusable.

### Ongoing Maintenance

After code changes, the normal path is:

```text
sp-map-update
```

`sp-map-update` computes the touched closure, updates only affected runtime
records when safe, records an update, and rechecks readiness. If the changed
area is not covered, the DB lacks an active generation, or the closure cannot be
bounded, it must report the exact escalation reason instead of pretending the
refresh completed.

## Acceptance Commands

Add two public commands:

```text
specify project-cognition validate-scan --format json
specify project-cognition validate-build --format json
```

Both commands return a stable JSON shape:

```json
{
  "status": "ok|blocked",
  "gate": "scan|build",
  "readiness": "scan_ready|query_ready|blocked",
  "errors": [],
  "warnings": [],
  "checked_paths": [],
  "details": {}
}
```

`status=ok` means the gate passed. `status=blocked` means the workflow must not
claim completion or finalize freshness.

## Scan Acceptance

`validate-scan` checks whether `sp-map-scan` produced a buildable scan package.

Required checks:

- `.specify/project-cognition/status.json` exists and is a JSON object.
- `.specify/project-cognition/evidence/` exists and is non-empty.
- `.specify/project-cognition/provisional/nodes.json` exists and contains a
  top-level node collection.
- `.specify/project-cognition/provisional/edges.json` exists and contains a
  top-level edge collection.
- `.specify/project-cognition/provisional/observations.json` exists and
  contains observations.
- `.specify/project-cognition/coverage.json` exists and contains coverage rows.
- `.specify/project-cognition/workbench/coverage-ledger.json` exists and
  records the scanned universe and critical or important coverage rows.
- `.specify/project-cognition/workbench/scan-packets/` exists and contains at
  least one scan packet for substantive repositories.
- unresolved critical gaps block handoff to `sp-map-build`.

Warnings are allowed for non-critical gaps when they are recorded with owner,
reason, and revisit condition. A warning does not block build handoff.

`sp-map-scan` may report complete only after `validate-scan` returns `ok`.

## Build Acceptance

`validate-build` checks whether `sp-map-build` published a usable query-backed
runtime.

Required checks:

- `.specify/project-cognition/status.json` exists and is a JSON object.
- `.specify/project-cognition/project-cognition.db` exists and is non-empty.
- SQLite opens the DB successfully.
- Required tables exist, including `metadata`, `generations`, `nodes`, `edges`,
  `claims`, `path_index`, `alias_index`, and `updates`.
- `metadata.schema_version` exists and is supported by the current CLI.
- `generations` has exactly one active generation or has a deterministic active
  generation selection rule.
- If `status.json.active_generation_id` is present, it matches the active
  generation in the DB.
- `status.json.graph_ready` is true.
- `status.json.graph_store_path` points to
  `.specify/project-cognition/project-cognition.db`.
- The active generation has queryable records sufficient for downstream route
  selection. At minimum this means non-empty `nodes` and `path_index`, plus
  claims or an explicit minimal-baseline marker.
- A smoke query through `project-cognition query` does not return
  `needs_rebuild`.

`sp-map-build` may report complete only after `validate-build` returns `ok`.

## Refresh Finalizers

`project-cognition complete-refresh` becomes a successful-refresh finalizer, not
a manual freshness override.

Before writing `fresh`, it must run build acceptance. If build acceptance fails:

- do not write `fresh`
- return blocked JSON
- include the failing validation errors
- recommend `sp-map-build` if scan acceptance is still valid
- recommend `sp-map-scan -> sp-map-build` only when scan acceptance is missing
  or unusable

`project-cognition record-refresh` remains a low-level recovery command, but it
must not imply query readiness. If build acceptance fails, it should write or
return `partial_refresh` rather than `fresh`, with validation errors included.

## Map Update Acceptance

`sp-map-update` is accepted only when the update helper and the post-update
build gate agree that the runtime remains usable.

Required checks:

- the DB has an active generation before the update begins
- changed paths are covered or the command records a bounded user-supplied
  correction that creates coverage
- the update writes an update record with `last_update_id`
- the post-update runtime passes `validate-build`
- the post-update `project-cognition query` for the affected scope does not
  return `needs_rebuild`

If the update helper returns `needs_rebuild`, the workflow must not call
`complete-refresh`. It should report that the baseline is unusable and route to
`sp-map-scan -> sp-map-build`.

If the helper returns `needs_update` because specific paths are uncovered, the
workflow should either complete a bounded update for those paths or report the
missing coverage. It should not mark the whole runtime fresh.

## State Semantics

The public states should mean:

- `fresh`: build acceptance passed and the query runtime is ready.
- `partial_refresh`: refresh or update work was recorded, but acceptance did not
  prove query readiness.
- `missing`: required scan or build artifacts are absent.
- `needs_update`: the baseline exists, but the current touched scope lacks
  coverage or requires a bounded update.
- `needs_rebuild`: the baseline is missing, DB schema is invalid, no active
  generation exists, or the graph cannot support query readiness.
- `support_drift`: support files changed, but the query runtime is not
  necessarily stale.

`status.json` freshness and `project-cognition query` readiness must not
contradict each other. If they do, validation must prefer query readiness and
surface the contradiction as blocked.

## Template Changes

Generated workflow guidance should say:

- `sp-map-scan` completion requires `project-cognition validate-scan`.
- `sp-map-build` completion requires `project-cognition validate-build`.
- `complete-refresh` is allowed only after build acceptance.
- ordinary workflows should route to `sp-map-update` for localized stale
  cognition.
- ordinary workflows should route to `sp-map-scan -> sp-map-build` only for
  missing or unusable baselines.

The user-facing wording should avoid telling users they "did not run scan/build"
when validation proves they did. It should say what is actually missing:

- scan acceptance missing
- build acceptance missing
- DB missing
- active generation missing
- schema unsupported
- touched path not covered

## Artifact Validation

Existing hook artifact validation should reuse the same acceptance logic.

- `map-scan` artifact validation should include scan acceptance.
- `map-build` artifact validation should include build acceptance.
- `map-update` artifact validation should include build acceptance plus update
  metadata.

This avoids one validation layer accepting a run that another workflow later
rejects.

## Tests

Required regression coverage:

- `validate-scan` blocks when required scan artifacts are missing.
- `validate-scan` passes for a complete scan package fixture.
- `validate-build` blocks when the DB is missing.
- `validate-build` blocks when the DB is empty.
- `validate-build` blocks when SQLite cannot read the DB.
- `validate-build` blocks when there is no active generation.
- `validate-build` blocks when `status.json.active_generation_id` conflicts
  with the DB active generation.
- `validate-build` passes for a seeded query-ready DB.
- `complete-refresh` does not write `fresh` when build acceptance fails.
- `record-refresh` cannot make an unready runtime look query-ready.
- `sp-map-update` cannot finalize fresh when the update helper returns
  `needs_rebuild`.
- artifact validation for `map-build` rejects a DB file that exists but has no
  active generation.
- `project-cognition query` includes a specific missing-baseline reason when it
  returns `needs_rebuild`.

## Success Criteria

- A downstream project that completes `sp-map-scan -> sp-map-build` and passes
  validation can proceed to `sp-specify` without being sent back through a full
  rebuild.
- A downstream project with later code changes can use `sp-map-update` for fast
  incremental maintenance.
- A bad or incomplete cognition baseline cannot be marked `fresh`.
- Users receive actionable validation errors instead of generic rebuild
  instructions.

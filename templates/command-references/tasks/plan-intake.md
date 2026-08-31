Trigger: before task decomposition or task-layer remediation.

Purpose: validate one ready plan contract and load only the context needed to compile a dependency-safe task graph.

Preserved Contract: tasks remain generation-only, preserve complete confirmed scope, and stop when implementation target or planning truth is invalid.

## Intake

1. Verify the current worktree and durable workflow binding, resolve its active feature subject, and load sparse resume state.
2. Query `plan-contract.json` first through `specify-runtime artifact show`; require ready handoff, valid source revision, locked boundary, and no unresolved blocker.
3. Reuse its context capsule/evidence refs, interfaces, acceptance, constraints, `MP-*`, `CA-###`, fidelity, verification, and stop/reopen refs.
4. Query `plan.md`, conditional design artifacts, and spec views through targeted `specify-runtime artifact show` calls only for a named required ref or stale condition; open normal memory or live source only when that condition requires it.
5. Do not revalidate discussion/specification gates or reconstruct plan decisions.

Query `plan-contract.json#/test_design_gate` through
`specify-runtime artifact show` and interpret it as
`not_selected|selected|required`. For selected/required input, run
`specify-runtime test-design projection-verify --feature-dir <feature-dir>
--projection-ref <project-relative-ref> --expected-sha256 <sha256>` before
reading any Test Design ref. The verified Tasks projection is canonical, typed,
pointer-only, and read-only. Never author or patch its publication, projection,
cases, data, coverage, gaps, audit, or runtime-owned task-index binding. Missing,
active, blocked, unpublished, stale, tampered, or foreign selected/required
input routes to independent `sp-test-design`; `not_selected` with no root is the
only optional skip. Preserve the runtime-verified compatibility Tasks handoff
when binding task-local `test_case_refs` and `test_data_refs`; this pointer-only
test-design handoff remains a runtime-owned compatibility contract.
The Plan projection binding may be all-null pending or Plan-only; it never
authorizes Tasks. Tasks verifies a separate feature projection for read-only
decomposition, while the fresh feature handoff plus runtime task-index binding
owns final authorization and all-and-only ref enforcement.

If task generation discovers a requirement, architecture, feasibility, or user-decision defect, route to the owning upstream phase. Task-layer dependency, granularity, write-scope, or verification defects are repaired locally.

## Phase Lock

Record task-generation-only writes, forbidden implementation, canonical refs, current action, blocker, and next route. Do not copy plan/spec content into workflow state.

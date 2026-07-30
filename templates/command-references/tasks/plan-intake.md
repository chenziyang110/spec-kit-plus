Trigger: before task decomposition or task-layer remediation.

Purpose: validate one ready plan contract and load only the context needed to compile a dependency-safe task graph.

Preserved Contract: tasks remain generation-only, preserve complete confirmed scope, and stop when implementation target or planning truth is invalid.

## Intake

1. Resolve the active feature lane/worktree and sparse resume state.
2. Query `plan-contract.json` first through `specify-runtime artifact show`; require ready handoff, valid source revision, locked boundary, and no unresolved blocker.
3. Reuse its context capsule/evidence refs, interfaces, acceptance, constraints, `MP-*`, `CA-###`, fidelity, verification, and stop/reopen refs.
4. Query `plan.md`, conditional design artifacts, and spec views through targeted `specify-runtime artifact show` calls only for a named required ref or stale condition; open normal memory or live source only when that condition requires it.
5. Do not revalidate discussion/specification gates or reconstruct plan decisions.

If task generation discovers a requirement, architecture, feasibility, or user-decision defect, route to the owning upstream phase. Task-layer dependency, granularity, write-scope, or verification defects are repaired locally.

## Phase Lock

Record task-generation-only writes, forbidden implementation, canonical refs, current action, blocker, and next route. Do not copy plan/spec content into workflow state.

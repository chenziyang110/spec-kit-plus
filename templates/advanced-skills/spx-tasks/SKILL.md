---
name: spx-tasks
description: Dependency-aware task-generation workflow for advanced coding models. Use when a validated plan exists and execution needs concrete outcomes, guardrails, write scopes, batches, and join points.
---

# SPX Tasks

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/project-cognition.md`, using cognition intent `plan`,
`references/task-graph-contract.md`, and `references/consequence-gate.md` only
when the plan carries triggered obligations. Resolve the active feature with the
installed `.specify/scripts/bash/check-prerequisites.sh --json` or PowerShell
equivalent; resolve task-generation inputs and keep implementation blocked.
Transition from the validated `plan` stage into `tasks` through the
workflow runtime before creating task artifacts.
Read `references/ui-quality-gate.md` when the plan carries a UI design contract.

Read `plan-contract.json` first and verify named owners, paths, and verification
entry points against cognition-selected live evidence. If planning truth is
missing or stale, stop and route to `$spx-plan`, `$spx-clarify`, or
`$spx-deep-research`; do not hide design work inside a task.

Run
`{{specify-subcmd:hook validate-state --command tasks --feature-dir <feature-dir> --autofix --format json}}`
and stop if it remains invalid. Require the plan's ready transition to
`sp-tasks`, locked target boundary, current revision, and zero unresolved
planning blockers.

Create `tasks.md` from `assets/tasks.md`. For standard, heavy, delegated,
multi-batch, obligation-rich, or any UI-bearing work, also render the canonical
`task-index.json` from `.specify/templates/task-index-template.json`; only a
non-UI short leader-direct sequence may stay in `tasks.md`. Every task needs a stable ID,
complete outcome, dependencies, likely write scope, acceptance, verification,
and must-preserve obligations. Mark parallel only when inputs are stable and
writes do not overlap; name the join and combined check.

At the task-index root, require `acceptance_refs` to be the complete unique
ordered list `plan-contract.json#/acceptance_refs/0..N-1`; a ready version-2
index may not omit the file or carry copied spec refs or a selected subset.
Compile every official entrypoint record in
`official_entrypoints`, stable
`review_obligations`, and the smallest complete `system_review_scenarios`
matrix that proves startup, every changed
user-observable journey, and affected shared regressions. Each scenario names
its entrypoint, preconditions, actions, observable results, and required
evidence. Compile obligations from every entrypoint, acceptance/capability,
must-preserve, consequence, fidelity, consumer-surface, wiring, and required UI
state source; map every required obligation to one or more scenario ids so
`$spx-review` can enforce zero uncovered scope instead of reconstructing
acceptance from prose. Give every `acceptance_ref` at least one dedicated
required system-review scenario whose required acceptance-source set is
exactly that ref. A broad regression scenario may be additional evidence only;
it cannot serve as a ref's dedicated witness.

Separately freeze a non-empty Human Acceptance Universe in
`human_acceptance_obligations` and `human_acceptance_scenarios`. Cover every
new or changed requirement that a human can perform end to end, retaining its
canonical task-index acceptance ref as the obligation source, a non-empty human
actor, official entrypoint, starting state, human action, observable terminal
outcome, required/optional status, Review-scenario linkage, and obligation
mapping. Every required human scenario links at least one dedicated required
Review scenario for its own `acceptance_ref`. Require zero uncovered required
human obligations. Human
performs these requirement journeys later in `$spx-accept`; do not repeat
System Review by copying its startup, wiring, diagnostics, or broad regression
matrix into human acceptance.

Validate requirement/plan coverage, dependency cycles, write-set safety,
acceptance, and real-entrypoint verification. Generate worker packets later in
`$spx-implement`, from current repository state, rather than pre-authoring a
large packet per task.

For every UI-bearing task, render its detailed block from `assets/ui-task.md`
and copy `assets/ui-task-index-entry.json` into the canonical task-index entry,
filling the complete `ui_contract` as the only UI packet contract. Do not rely on a
global UI coverage table: the just-in-time packet compiler must receive design
sources, task-specific visual constraints, states, and evidence without
re-inferring them.

Before handoff, run
`{{specify-subcmd:hook validate-artifacts --command tasks --feature-dir <feature-dir> --format json}}`
and repair the task graph or reopen its owning upstream phase on failure.

Do not implement or edit production source/tests. This invocation authorizes
only this workflow stage. Stop after reporting the executable graph and
recommend `$spx-implement`; do not invoke `$spx-implement` in this run. A
handoff is not authorization to execute it. Use `$spx-analyze` only when an
independent consistency gate is requested or existing state requires it.

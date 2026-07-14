---
name: spx-tasks
description: Dependency-aware task-generation workflow for advanced coding models. Use when a validated plan exists and execution needs concrete outcomes, guardrails, write scopes, batches, and join points.
---

# SPX Tasks

Read `references/project-cognition.md`, using cognition intent `plan`,
`references/task-graph-contract.md`, and `references/consequence-gate.md` only
when the plan carries triggered obligations. Resolve the active feature with the
installed prerequisite script.
Read `references/ui-quality-gate.md` when the plan carries a UI design contract.

Read `plan-contract.json` first and verify named owners, paths, and verification
entry points against cognition-selected live evidence. If planning truth is
missing or stale, stop and route to `$spx-plan`, `$spx-clarify`, or
`$spx-deep-research`; do not hide design work inside a task.

Create `tasks.md` from `assets/tasks.md`. For standard, heavy, delegated,
multi-batch, obligation-rich, or any UI-bearing work, also render the canonical
`task-index.json` from `.specify/templates/task-index-template.json`; only a
non-UI short leader-direct sequence may stay in `tasks.md`. Every task needs a stable ID,
complete outcome, dependencies, likely write scope, acceptance, verification,
and must-preserve obligations. Mark parallel only when inputs are stable and
writes do not overlap; name the join and combined check.

Validate requirement/plan coverage, dependency cycles, write-set safety,
acceptance, and real-entrypoint verification. Generate worker packets later in
`$spx-implement`, from current repository state, rather than pre-authoring a
large packet per task.

For every UI-bearing task, render its detailed block from `assets/ui-task.md`
and copy `assets/ui-task-index-entry.json` into the canonical task-index entry,
filling both `ui_contract` and `ui_fidelity_requirements`. Do not rely on a
global UI coverage table: the just-in-time packet compiler must receive design
sources, task-specific visual constraints, states, and evidence without
re-inferring them.

Do not implement or edit production source/tests. Hand off to `$spx-implement`
when the graph is executable; use `$spx-analyze` only when an independent
consistency gate is requested or existing state requires it.

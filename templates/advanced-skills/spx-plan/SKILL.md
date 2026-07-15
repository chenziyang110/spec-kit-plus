---
name: spx-plan
description: Lean technical-planning workflow for advanced coding models. Use when a planning-ready specification needs repository-grounded architecture, interfaces, risks, verification, rollout, and rollback decisions.
---

# SPX Plan

Read `references/project-cognition.md`, using cognition intent `plan`.
Read `references/planning-contract.md` and `references/consequence-gate.md` only
on its triggers.
Read `references/ui-quality-gate.md` when the specification is UI-bearing.

Resolve the active feature with the installed
`.specify/scripts/bash/setup-plan.sh --json` or PowerShell equivalent. Start
from `spec-contract.json` when present and verify architecture claims against
the cognition-selected live repository paths.

Render `plan-contract.json` and `plan.md` from
the canonical machine template `.specify/templates/plan-contract-template.json`
and this Skill's compact `assets/plan.md`. Cover affected components and files,
interfaces and data, compatibility or migration, security, verification,
rollout or rollback, and material risks only when relevant.

For UI-bearing work, consume `DESIGN.md`, `ui-brief.md`, original fidelity
sources, and the spec design contract. Set `ui_design_contract.ui_applicable:
true`, preserve `ui_brief_ref`, and record `design_readiness`. Populate it with
the current direction contract, surface/platform classification, approved visual,
reference intents, real content/image plans, design-system adoption, required
states, must-preserve rules, real entry points, and the evidence triad. Carry
verified cognition routes into the compact context capsule. Do not defer these
decisions to tasks.

If design-changing feasibility remains unproven, stop and route the named
question to `$spx-deep-research`; do not hide research inside generic plan
prose. Repair requirement contradictions through `$spx-clarify`.

Validate the plan contract and compact plan view against confirmed requirements
and live owners. Do not create tasks or task artifacts such as `tasks.md` or
`task-index.json`; also do not create checklists, issues, production source,
tests, migrations, or runtime configuration in this workflow. Preserve canonical
`/sp.*` state identifiers. This invocation authorizes only this workflow stage.
Stop after reporting the validated plan and recommend `$spx-tasks` when ready.
Do not invoke `$spx-tasks` in this run; a handoff is not authorization to execute
it.

---
name: spx-plan
description: Lean technical-planning workflow for advanced coding models. Use when a planning-ready specification needs repository-grounded architecture, interfaces, risks, verification, rollout, and rollback decisions.
---

# SPX Plan

Read `references/project-cognition.md`, using cognition intent `plan`.
Read `references/planning-contract.md` and `references/consequence-gate.md` only
on its triggers.

Resolve the active feature with the installed
`.specify/scripts/bash/setup-plan.sh --json` or PowerShell equivalent. Start
from `spec-contract.json` when present and verify architecture claims against
the cognition-selected live repository paths.

Render `plan-contract.json` and `plan.md` from
the canonical machine template `.specify/templates/plan-contract-template.json`
and this Skill's compact `assets/plan.md`. Cover affected components and files,
interfaces and data, compatibility or migration, security, verification,
rollout or rollback, and material risks only when relevant.

If design-changing feasibility remains unproven, stop and route the named
question to `$spx-deep-research`; do not hide research inside generic plan
prose. Repair requirement contradictions through `$spx-clarify`.

Validate the plan contract and compact plan view against confirmed requirements
and live owners. Do not create tasks, checklists, issues, production source,
tests, migrations, or runtime configuration in this workflow. Preserve
canonical `/sp.*` state identifiers and continue with `$spx-tasks` when ready.

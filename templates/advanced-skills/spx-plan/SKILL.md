---
name: spx-plan
description: Lean planning workflow for advanced coding models. Use when a stable specification needs repository-grounded design, research, executable tasks, quality analysis, or explicit issue export.
---

# SPX Plan

Read `references/project-cognition.md`, using cognition intent `plan`.
Read `references/design-and-tasks.md`. Read `references/research-and-risk.md`
and `references/consequence-gate.md` only on their triggers. Read
`references/issue-export.md` only for an explicitly requested tracker export.

Resolve the active feature with the installed
`.specify/scripts/bash/setup-plan.sh --json` or PowerShell equivalent. Start
from `spec-contract.json` when present and verify architecture claims against
the cognition-selected live repository paths.

Render `plan-contract.json` and `plan.md` from
the canonical machine template `.specify/templates/plan-contract-template.json`
and this Skill's compact `assets/plan.md`. Cover affected components and files,
interfaces and data, compatibility or migration, security, verification,
rollout or rollback, and material risks only when relevant. Research or build a
disposable spike only for uncertainty that can change the design.

In the same workflow, use `assets/tasks.md` to create an execution-ready
`tasks.md`; add `task-index.json` from the canonical machine template when scale
or runtime validation requires it. Tasks must express outcomes, dependencies,
likely write scope, acceptance, and verification. Mark parallelism only when
dependencies and write sets are genuinely independent. Use
`assets/checklist.md` only when a focused quality gate adds decision value.

Analyze cross-artifact consistency and generate a focused requirements-quality
checklist when they add decision value. Repair upstream truth instead of
papering over contradictions. Do not edit production source, tests, migrations,
or runtime configuration. Export validated tasks to issues only when explicitly
requested and authorized. Preserve canonical `/sp.*` state identifiers and
continue with `$spx-implement` when ready.

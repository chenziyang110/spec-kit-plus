---
name: spx-specify
description: Lean feature-specification workflow for advanced coding models. Use when a new capability or supplied feature PRD needs planning-ready requirements, acceptance, scope, and constraints.
---

# SPX Specify

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/project-cognition.md`, using cognition intent `plan`.
Read `references/requirements-contract.md`. Read
`references/discussion-handoff.md` when consuming a ready discussion and
`references/ui-and-handoffs.md` plus `references/ui-quality-gate.md` for any
UI-bearing feature, with or without supplied references. Read
`references/consequence-gate.md` only on its triggers.

Inspect project rules, relevant live behavior, a supplied feature PRD, and any
confirmed discussion context. Clarify only decisions that materially change scope, behavior,
interfaces, risk, or acceptance; make safe assumptions explicit. Preserve every
confirmed capability and do not silently reduce the request to an MVP.

For new feature state, run the installed
`.specify/scripts/bash/create-new-feature.sh` or PowerShell equivalent. Render
the authoritative `spec-contract.json` from the canonical machine template
`.specify/templates/spec-contract-template.json`. For a new project-facing
view, use this Skill's compact `assets/spec.md`; preserve existing semantic work
when revising an established spec. Render `assets/ui-brief.md` for substantive
UI work; a narrow existing-pattern adjustment may instead record why a separate
brief adds no decision value.

After the feature directory exists, enter or resume `specify` through the
workflow runtime before substantive artifact work. Keep specification truth in
the contract rather than reconstructing phase state. Create or resume rich
`workflow-state.md` from the installed template for specification evidence,
resume details, and Learning; it does not own phase order or runtime revision.
Run
`{{specify-subcmd:hook validate-state --command specify --feature-dir <feature-dir> --autofix --format json}}`
and stop if the repaired state remains invalid.
Create only specification-stage outputs here: `spec-contract.json`, `spec.md`,
a triggered `ui-brief.md`, and specification evidence or workflow-owned rich state.
Do not create `plan-contract.json`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`, `tasks.md`, or `task-index.json`; `$spx-plan` and
`$spx-tasks` own those downstream artifacts.

An existing PRD used as input to one feature compiles into the ordinary spec
contract with source traceability. Route project-wide principles to
`$spx-constitution`, exploratory ideas to `$spx-discussion`, existing-spec gaps
to `$spx-clarify`, and repository reconstruction to `$spx-prd-scan`.

Make requirements and acceptance observable. Resolve contradictions and
planning-blocking unknowns; ask only the smallest decision batch needed. Run the installed artifact validator when
available and preserve canonical `/sp.*` transition values required by the
runtime.
Before reporting planning-ready, run
`{{specify-subcmd:hook validate-artifacts --command specify --feature-dir <feature-dir> --format json}}`;
fail closed on any blocked result and repair the owning artifact or upstream
handoff.

Do not implement or edit production code, tests, migrations, or runtime
configuration. This invocation authorizes only this workflow stage. Stop after
reporting the specification result and recommend exactly one next workflow. Do
not invoke `$spx-plan`, `$spx-clarify`, `$spx-deep-research`, or any other next
workflow in this run; a handoff is not authorization to execute it.

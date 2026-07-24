---
name: spx-plan
description: Lean technical-planning workflow for advanced coding models. Use when a planning-ready specification needs repository-grounded architecture, interfaces, risks, verification, rollout, and rollback decisions.
---

# SPX Plan

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/project-cognition.md`, using cognition intent `plan`.
Always read `references/planning-contract.md`. Read
`references/consequence-gate.md` only on its triggers.
Read `references/ui-quality-gate.md` when the specification is UI-bearing.

Resolve `FEATURE_DIR` without creating `plan.md`, using an explicit feature
argument, lane state, or the installed prerequisite helper's paths-only mode.
Transition from the validated `specify` stage into `plan` through the workflow
runtime. Only after the transition succeeds, run the installed
`.specify/scripts/bash/setup-plan.sh --json` or PowerShell equivalent to create
or preserve the plan skeleton. Run
`{{specify-subcmd:specify-runtime hook validate-state --command plan --feature-dir <feature-dir> --autofix --format json}}`
and stop if it remains invalid.

Require `spec-contract.json` with `status: planning-ready`, a ready transition
to `sp-plan`, a current source revision, locked target boundary, zero hard
unknowns, and zero open conflicts. Fail closed to the owning upstream workflow
when any gate fails. Verify architecture claims against cognition-selected live
repository paths.

Treat `plan-contract.json#/acceptance_refs` as the exact complete fail-closed
Spec-to-Plan denominator. For a ready version-2 plan it is the unique ordered
list `spec-contract.json#/acceptance_criteria/0..N-1`, covering every live
specification acceptance criterion exactly once; never select a subset,
reconstruct prose labels, or reorder, duplicate, rename, or omit a criterion.

When `deep-research.md` exists, read and validate it before choosing the design.
Consume every `PH-###` Planning Handoff item according to its mandatory,
optional, or user-decision contract. Add a level-2 `## Deep Research
Traceability Matrix` to `plan.md` with `Plan Decision`, `Handoff ID`, `Evidence
/ Spike ID`, `Evidence Quality`, and `Plan Action` columns. Missing mandatory
handoffs or untraceable evidence keep planning blocked; a validated
`**Status**: Not needed` handoff carries no invented PH IDs.

Render `plan-contract.json` and `plan.md` from
the canonical machine template `.specify/templates/plan-contract-template.json`
and this Skill's compact `assets/plan.md`. Cover affected components and files,
interfaces and data, compatibility or migration, security, verification,
rollout or rollback, and material risks only when relevant.

For UI-bearing work, consume `DESIGN.md`, `ui-brief.md`, original fidelity
sources, and the spec design contract. Set `ui_design_contract.ui_applicable:
true`, preserve `ui_brief_ref`, and record `design_readiness`. Populate it with
the current direction contract, surface/platform classification, approved visual,
preview/manifest SHA-256 values, `DS-*` decisions, component/color-mode/
responsive/motion contracts, reference intents, real content/image plans,
design-system adoption, required states, must-preserve rules, real entry points,
viewport/state acceptance matrix, comparison tolerance, accepted deviations,
and the evidence triad. Carry
verified cognition routes into the compact context capsule. Do not defer these
decisions to tasks.

If design-changing feasibility remains unproven, stop and route the named
question to `$spx-deep-research`; do not hide research inside generic plan
prose. Repair requirement contradictions through `$spx-clarify`.

Create conditional outputs only when they carry independent design evidence:
`research.md` for bounded implementation-shaping research, `data-model.md` for
new data/state or persistence design, `contracts/` for external or protocol
interfaces, and `quickstart.md` for a material end-to-end validation scenario.
Otherwise record the skip reason in `plan-contract.json`. Refresh existing agent
contexts with the installed `update-agent-context` script after the plan is
valid.

Validate the plan contract and compact plan view against confirmed requirements
and live owners. Do not create tasks or task artifacts such as `tasks.md` or
`task-index.json`; also do not create checklists, issues, production source,
tests, migrations, or runtime configuration in this workflow. Preserve canonical
`/sp.*` state identifiers. This invocation authorizes only this workflow stage.
Run `{{specify-subcmd:specify-runtime hook validate-artifacts --command plan --feature-dir <feature-dir> --format json}}`
and repair or block on a non-OK result.
Stop after reporting the validated plan and recommend `$spx-tasks` when ready.
Do not invoke `$spx-tasks` in this run; a handoff is not authorization to execute
it.

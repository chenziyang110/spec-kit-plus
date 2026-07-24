---
name: spx-analyze
description: Read-only cross-artifact consistency analysis for advanced coding models. Use when tasks exist and the specification, plan, and task boundaries need an independent gate before or during execution.
---

# SPX Analyze

Read `references/project-learning.md` and apply its consume-only policy.
Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/analysis-gate.md`.
Read `references/ui-quality-gate.md` when the specification or plan is
UI-bearing.
Read `.specify/memory/constitution.md` as the highest local authority; a
conflict is `CRITICAL` and routes to the artifact that violates it.

Resolve the active feature with the installed prerequisite script using
`--require-tasks --include-tasks`. Read machine contracts first, then open
project-facing views only for a named finding or missing contract detail.
Before any report or rich-state write, run
`{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}`.
`FEATURE_DIR/workflow.json` is CLI-owned; this auxiliary skill must not write
it manually, and its only permitted runtime mutation is the evidence-backed
`specify-runtime workflow reopen` operation below. Its expected required-stage owner is `tasks or implement`. On missing,
corrupt, different, or terminal runtime state, remain read-only and stop with
the returned blocker or a typed owner handoff containing the observed stage,
expected owner, highest invalid stage, exact next action, unblock criteria, and
resume argv. Never rewrite phase order to make analysis fit.

Create or resume rich workflow-owned `workflow-state.md` before substantive
analysis, using the installed workflow-state template only when absent. Record
`active_command: sp-analyze`, `phase_mode: analysis-only`, source revision,
target boundary, blocker, and next route. Run
`{{specify-subcmd:specify-runtime hook validate-state --command analyze --feature-dir <feature-dir> --autofix --format json}}`
and stop if the repaired state remains invalid.
Compare confirmed requirements, design decisions, task coverage, dependencies,
write boundaries, consequence obligations, and real-entrypoint verification
against the live repository paths selected by cognition.
For UI work, verify continuity from approved `DESIGN.md` and `ui-brief.md`
through the plan `ui_design_contract`, every UI task contract, and required
real-entrypoint evidence. Missing continuity is an upstream-owned finding.

This is a non-destructive gate. Do not edit `spec.md`, `context.md`, `plan.md`,
`tasks.md`, production source, or tests. You may update the existing
`workflow-state.md` gate result so resume remains truthful. Report only
actionable findings with stable identity, severity, evidence, owner stage, and
the smallest repair route.

If a blocker invalidates upstream truth, select the highest affected workflow:
`$spx-clarify`, `$spx-deep-research`, `$spx-plan`, or `$spx-tasks`. Map clarify
or deep-research to reopen `specify`, plan to reopen `plan`, tasks to reopen
`tasks`, and a completed execution-only owner to reopen `implement`. When that
mapped stage is earlier than the current non-blocked required stage, or is the
same stage with `status: completed`, run
`{{specify-subcmd:specify-runtime workflow reopen --to <mapped-stage> --feature-dir <feature-dir> --expected-revision <revision> --reason <finding-summary> --evidence <finding-id-or-sanitized-evidence> --invalidated-artifacts <artifact> --format json}}`,
repeating evidence and invalidated-artifact flags for the full stale downstream
set. Preserve the returned revision and then hand off. Resolve an existing
runtime blocker through `specify-runtime workflow resolve` before reopen. If the mapped stage is
already active, hand off to that current owner without reopening; if completed,
reactivate it through the same reopen command. Acceptance findings use
`accept route-repair`, never generic reopen. Route an
execution-only defect to `$spx-debug` or `$spx-implement`. When no blocker
remains, explicitly clear implementation to continue. Never repair artifacts
inside the analysis pass. This invocation authorizes only this workflow stage;
report the repair or continuation handoff, but do not invoke another workflow
in this run.
Validate the final state with
`{{specify-subcmd:specify-runtime hook validate-artifacts --command analyze --feature-dir <feature-dir> --format json}}`.

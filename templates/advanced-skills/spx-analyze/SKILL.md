---
name: spx-analyze
description: Read-only cross-artifact consistency analysis for advanced coding models. Use when tasks exist and the specification, plan, and task boundaries need an independent gate before or during execution.
---

# SPX Analyze

Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/analysis-gate.md`.

Resolve the active feature with the installed prerequisite script using
`--require-tasks --include-tasks`. Read machine contracts first, then open
project-facing views only for a named finding or missing contract detail.
Compare confirmed requirements, design decisions, task coverage, dependencies,
write boundaries, consequence obligations, and real-entrypoint verification
against the live repository paths selected by cognition.

This is a non-destructive gate. Do not edit `spec.md`, `context.md`, `plan.md`,
`tasks.md`, production source, or tests. You may update the existing
`workflow-state.md` gate result so resume remains truthful. Report only
actionable findings with stable identity, severity, evidence, owner stage, and
the smallest repair route.

If a blocker invalidates upstream truth, reopen the highest affected workflow:
`$spx-clarify`, `$spx-deep-research`, `$spx-plan`, or `$spx-tasks`. Route an
execution-only defect to `$spx-debug` or `$spx-implement`. When no blocker
remains, explicitly clear implementation to continue. Never repair artifacts
inside the analysis pass.

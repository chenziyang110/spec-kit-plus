---
name: spx-specify
description: Lean feature-specification workflow for advanced coding models. Use when a new capability or supplied feature PRD needs planning-ready requirements, acceptance, scope, and constraints.
---

# SPX Specify

Read `references/project-cognition.md`, using cognition intent `plan`.
Read `references/requirements-contract.md`. Read
`references/discussion-handoff.md` when consuming a ready discussion and
`references/ui-and-handoffs.md` for UI references. Read
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
when revising an established spec. Use `assets/ui-brief.md` only when triggered.
Add other artifacts only when they contain independently useful decisions or
evidence.

An existing PRD used as input to one feature compiles into the ordinary spec
contract with source traceability. Route project-wide principles to
`$spx-constitution`, exploratory ideas to `$spx-discussion`, existing-spec gaps
to `$spx-clarify`, and repository reconstruction to `$spx-prd-scan`.

Make requirements and acceptance observable. Resolve contradictions and
planning-blocking unknowns; ask only the smallest decision batch needed. Run the installed artifact validator when
available and preserve canonical `/sp.*` transition values required by the
runtime.

Do not implement or edit production code, tests, migrations, or runtime
configuration. Planning-ready output continues with `$spx-plan`.

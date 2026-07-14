---
name: spx-specify
description: Lean requirements workflow for advanced coding models. Use when a capability needs planning-ready acceptance, when compiling or reconstructing a PRD, or when revising project-wide rules.
---

# SPX Specify

Read `references/project-cognition.md`, using cognition intent `plan`.
Read `references/requirements-contract.md`. Read
`references/discussion-handoff.md` for recoverable discussion,
`references/ui-and-handoffs.md` for UI references,
`references/project-rules.md` for project-wide governance, and
`references/prd-intake.md` for existing PRDs. Read
`references/consequence-gate.md` only on its triggers.

Inspect project rules, relevant live behavior, and any confirmed discussion
context. Clarify only decisions that materially change scope, behavior,
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

Rules-only work uses the project-rules lane without creating feature state.
An existing PRD used as feature input compiles into the ordinary spec contract.
An explicit repository-reconstruction PRD request instead produces the full
archive defined by `references/prd-intake.md` and stops without an automatic
planning handoff.

Make requirements and acceptance observable. Resolve contradictions and
planning-blocking unknowns; use short iterative discussion inside this workflow
instead of creating ceremony. Run the installed artifact validator when
available and preserve canonical `/sp.*` transition values required by the
runtime.

Do not implement or edit production code, tests, migrations, or runtime
configuration. Planning-ready output continues with `$spx-plan`.

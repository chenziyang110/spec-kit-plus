---
name: "project-to-prd"
description: "Use when an existing repository needs current-state product documentation reverse-extracted into a PRD suite from repository evidence."
origin: spec-kit-plus
---

# Project To PRD

Use this passive skill to recognize existing-project PRD extraction work and
route it to the active `sp-prd` workflow.

`sp-prd` is a peer workflow to `sp-specify`. Use `sp-specify` when the user wants
to align a new or changed feature intent before planning. Use `sp-prd` when the
user wants a professional current-state PRD suite reconstructed from the
repository that already exists.

## Required Behavior

- Route existing-project reverse PRD requests to `sp-prd` before repository
  inspection.
- Ground the PRD in current implementation reality: code, docs, tests, routes,
  UI surfaces, service/API surfaces, configuration, data models, domain terms,
  `PROJECT-HANDBOOK.md`, and project-map evidence when present.
- Preserve the distinction between Evidence, Inference, and Unknown.
- Treat `.specify/prd-runs/<run-id>/workflow-state.md` as the resumable state
  source for the PRD run.
- Keep the default terminal state as completed PRD exports under
  `.specify/prd-runs/<run-id>/`.
- Do not automatically hand off to `sp-plan`, `sp-tasks`, or implementation
  planning.

## Routing Signals

Use `sp-prd` for requests like:

- "write a PRD for this existing app"
- "extract product requirements from this repo"
- "document what this product currently does"
- "turn the current implementation into a product requirements document"
- "generate UI/service PRD docs from the codebase"

Route to `sp-specify` instead when the user is describing a new product idea or
future change that is not grounded in an existing repository surface.

## Output Expectations

The active workflow should produce a current-state PRD suite, typically:

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/coverage-matrix.md`
- `.specify/prd-runs/<run-id>/evidence/`
- `.specify/prd-runs/<run-id>/master/master-pack.md`
- `.specify/prd-runs/<run-id>/exports/prd.md`

Mode-specific exports may include UI, service, flow, data, rule, or internal
brief views when the repository evidence supports them.

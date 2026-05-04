---
name: "project-to-prd"
description: "Use when an existing repository needs current-state product documentation reverse-extracted into a PRD suite from repository evidence."
origin: spec-kit-plus
---

# Project To PRD

Use this passive skill to recognize existing-project PRD extraction work and
route it to `sp-prd-scan`, then `sp-prd-build`.

Use `sp-specify` when the user wants to align a new or changed feature intent
before planning. Use `sp-prd-scan -> sp-prd-build` when the user wants a
professional current-state PRD suite reconstructed from the repository that
already exists. `sp-prd` is deprecated and remains compatibility-only for older
surfaces that have not been updated yet.

## Required Behavior

- Route existing-project reverse PRD requests to `sp-prd-scan`, then
  `sp-prd-build`, before repository inspection.
- Treat `sp-prd-scan -> sp-prd-build` as the depth-aware current-state
  extraction workflow, not a flat repo summary pass.
- Treat `sp-prd` as a deprecated compatibility-only entrypoint that must route
  into the canonical `sp-prd-scan -> sp-prd-build` flow.
- Ground the PRD in current implementation reality: code, docs, tests, routes,
  UI surfaces, service/API surfaces, configuration, data models, domain terms,
  `PROJECT-HANDBOOK.md`, and project-map evidence when present.
- Require capability triage before claiming the PRD suite is complete.
- Use targeted evidence harvest for `critical` and `high` capabilities.
- Keep `critical capabilities` visible until they are depth-aware and
  `depth-qualified` rather than merely surface-covered.
- Preserve the distinction between Evidence, Inference, and Unknown.
- Treat `.specify/prd-runs/<run-id>/workflow-state.md` as the resumable state
  source for the PRD run.
- Keep the default terminal state as completed PRD exports under
  `.specify/prd-runs/<run-id>/`.
- Do not automatically hand off to `sp-plan`, `sp-tasks`, or implementation
  planning.

## Routing Signals

Use `sp-prd-scan`, then `sp-prd-build` for requests like:

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
- `.specify/prd-runs/<run-id>/prd-scan.md`
- `.specify/prd-runs/<run-id>/coverage-ledger.md`
- `.specify/prd-runs/<run-id>/coverage-ledger.json`
- `.specify/prd-runs/<run-id>/capability-ledger.json`
- `.specify/prd-runs/<run-id>/artifact-contracts.json`
- `.specify/prd-runs/<run-id>/reconstruction-checklist.json`
- `.specify/prd-runs/<run-id>/evidence/`
- `.specify/prd-runs/<run-id>/master/master-pack.md`
- `.specify/prd-runs/<run-id>/exports/prd.md`

Mode-specific exports may include UI, service, flow, data, rule, or internal
brief views when the repository evidence supports them. Completion requires
capability triage, targeted evidence harvest, and depth-aware handling for
product-defining capabilities.

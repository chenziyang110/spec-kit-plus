# Project Handbook

**Last Updated:** 2026-08-31
**Purpose:** Root navigation artifact for this repository.

## Scenario-first E2E workflow

`sp-e2e` and the independent `spx-e2e` derive operation-level test obligations
before selecting an execution tool. Clients, web, CLI and services share the
same boundary, state, external-event/checkpoint and recovery analysis. Visual
inspection plus real interaction is first-class; independent effect readback
is required where UI feedback alone cannot prove the outcome. Native runners
and t-way combination planning remain optional, not discovery substitutes.

The source owners are `templates/commands/e2e.md`,
`templates/advanced-skills/spx-e2e/`, and stateless `scripts/shared/e2e_*.py`.
These helpers own ordinary test assets/results, not workflow lifecycle state.
Shared installation copies them under `.specify/scripts/shared/`. Canonical
`sp-e2e` cognition/Learning registration supports scoped test-asset changes;
production behavior, Test Design publications, Review and Accept ownership
remain unchanged. See [usage](docs/sp-e2e.md), [scenario design](docs/sp-e2e-scenarios.md)
and [current validation boundaries](plans/sp-e2e-readiness.md).

## System Summary

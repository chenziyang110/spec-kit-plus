---
description: Use when an existing repository needs reconstruction-grade scan outputs before a PRD suite can be compiled.
workflow_contract:
  when_to_use: Use for an existing repository that needs read-only reconstruction investigation before final PRD synthesis.
  primary_objective: Produce a reconstruction-grade scan package that captures capability, artifact, and boundary truth strongly enough for `sp-prd-build`.
  primary_outputs: '`.specify/prd-runs/<run-id>/workflow-state.md`, `.specify/prd-runs/<run-id>/prd-scan.md`, `.specify/prd-runs/<run-id>/coverage-ledger.md`, `.specify/prd-runs/<run-id>/coverage-ledger.json`, `.specify/prd-runs/<run-id>/capability-ledger.json`, `.specify/prd-runs/<run-id>/artifact-contracts.json`, `.specify/prd-runs/<run-id>/reconstruction-checklist.json`, `.specify/prd-runs/<run-id>/scan-packets/<lane-id>.md`, `.specify/prd-runs/<run-id>/evidence/**`, and `.specify/prd-runs/<run-id>/worker-results/**`.'
  default_handoff: /sp-prd-build after the scan package passes reconstruction readiness checks.
---

# `/sp.prd-scan` Reconstruction Scan

## Workflow Contract Summary

This summary is routing metadata only. The full workflow contract is the frontmatter plus the sections below.

- Use `sp-prd-scan` for read-only reconstruction investigation.
- Primary truth source: current repository reality plus `PROJECT-HANDBOOK.md` and project-map evidence when present.
- Primary terminal state: completed scan package under `.specify/prd-runs/<run-id>/`.
- Stable freshness state: `.specify/prd/status.json`.
- Default handoff: `/sp-prd-build`.

## Objective

[AGENT] Produce a reconstruction-grade scan package that lets `sp-prd-build` compile a PRD suite without rereading the repository.

The scan phase is a read-only reconstruction investigation. It must harvest enough grounded detail about each `capability`, `artifact`, and `boundary` to prove whether the package is reconstruction-ready or blocked-by-gap.
Every consequential claim must preserve `Evidence`, `Inference`, and `Unknown` labeling semantics instead of collapsing them into one unmarked narrative.

## Context

Required context inputs:

- `PROJECT-HANDBOOK.md` as the root navigation artifact.
- `.specify/project-map/index/status.json` and the smallest relevant project-map topics when available.
- `.specify/prd/status.json` as the stable PRD scan freshness record when present.
- Current repository evidence from code, docs, tests, routes, UI surfaces, service surfaces, data models, integrations, configuration, and deployment surfaces.
- Existing `workflow-state.md` under `.specify/prd-runs/<run-id>/` when resuming an interrupted run.

## Hard Boundary

- `sp-prd-scan` must not write `master/master-pack.md`.
- `sp-prd-scan` must not write `exports/**`.
- `sp-prd-scan` must not claim the PRD suite is complete.

## Process

1. Route and initialize the PRD run under `.specify/prd-runs/<run-id>/`.
2. Load brownfield context and select the smallest relevant repository surfaces.
3. Check `.specify/prd/status.json` freshness before scoping the scan.
4. Route `fresh` status to status confirmation only unless the user explicitly requests a new run.
5. Route `targeted-stale` status to a bounded scan of the changed source, test, and documentation surfaces plus any directly adjacent capability boundaries.
6. Route `full-stale` status to a full reconstruction scan across command, workflow, integration, configuration, and shared-runtime surfaces.
7. Triage `capability`, `artifact`, and `boundary` objects before broad synthesis.
8. Assign each capability a tier: `critical`, `high`, `standard`, or `auxiliary`.
9. For `critical` and `high` capabilities, capture stronger reconstruction detail: structure, producers, consumers, constraints, compatibility behavior, and failure behavior.
10. Build `.specify/prd-runs/<run-id>/artifact-contracts.json` and `.specify/prd-runs/<run-id>/reconstruction-checklist.json`.
11. Generate scan packets and evidence notes that explain structure, producers, consumers, constraints, and failure behavior while preserving `Evidence`, `Inference`, and `Unknown`.
12. Refuse handoff if any `critical` capability lacks reconstruction-ready support. `high` capabilities must not be waved through with path-only evidence; keep the status explicit as `blocked-by-gap` when evidence is insufficient.

## Output Contract

The scan phase writes only the reconstruction package:

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/prd-scan.md`
- `.specify/prd-runs/<run-id>/coverage-ledger.md`
- `.specify/prd-runs/<run-id>/coverage-ledger.json`
- `.specify/prd-runs/<run-id>/capability-ledger.json`
- `.specify/prd-runs/<run-id>/artifact-contracts.json`
- `.specify/prd-runs/<run-id>/reconstruction-checklist.json`
- `.specify/prd-runs/<run-id>/scan-packets/<lane-id>.md`
- `.specify/prd-runs/<run-id>/evidence/**`
- `.specify/prd-runs/<run-id>/worker-results/**`
- `.specify/prd/status.json` when initializing a successful scan and the stable status file is absent

## Quality Gates

- Stable Status Gate: `.specify/prd/status.json` must be consulted or initialized, and the run must record whether freshness is `fresh`, `targeted-stale`, or `full-stale`.
- Capability Triage Gate: each capability must be assigned `critical`, `high`, `standard`, or `auxiliary` before scan completion can be claimed.
- Critical Depth Gate: each `critical` capability must be explicitly marked `reconstruction-ready` or `blocked-by-gap`, with structure, producer-consumer, constraint, and failure coverage captured.
- High Capability Gate: each `high` capability must have more than path-only evidence and must record reconstruction-relevant structure and boundary behavior.
- Artifact Contract Gate: important structures must land in `artifact-contracts.json`.
- Checklist Gate: recreation blockers and remaining `Unknown` items must be visible in `reconstruction-checklist.json`.
- Evidence Label Gate: scan outputs must preserve `Evidence`, `Inference`, and `Unknown` labeling semantics.

## Guardrails

- Do not write final PRD exports in `sp-prd-scan`.
- Do not treat path discovery as sufficient reconstruction evidence.
- Do not let `critical` or `high` capabilities pass with shallow evidence only.
- Do not hide unknowns that block a later build step.

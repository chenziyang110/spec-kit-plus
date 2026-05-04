---
description: Use when `sp-prd-scan` has produced a complete reconstruction package and the final PRD suite must be compiled from it.
workflow_contract:
  when_to_use: Use after `sp-prd-scan` for a repository that already has a reconstruction-grade scan package ready for synthesis.
  primary_objective: Validate scan completeness, compile the master pack, render final PRD exports, and prove reverse coverage validation without inventing new facts.
  primary_outputs: '`.specify/prd-runs/<run-id>/workflow-state.md`, `.specify/prd-runs/<run-id>/master/master-pack.md`, `.specify/prd-runs/<run-id>/exports/prd.md`, `.specify/prd-runs/<run-id>/exports/reconstruction-appendix.md`, `.specify/prd-runs/<run-id>/exports/data-model.md`, `.specify/prd-runs/<run-id>/exports/integration-contracts.md`, and `.specify/prd-runs/<run-id>/exports/runtime-behaviors.md`.'
  default_handoff: Completed PRD suite export, or route back to /sp-prd-scan if reconstruction evidence is incomplete.
---

# `/sp.prd-build` Reconstruction Build

## Workflow Contract Summary

This summary is routing metadata only. The full workflow contract is the frontmatter plus the sections below.

- Use `sp-prd-build` after `sp-prd-scan` has produced a validated reconstruction package.
- Primary truth source: the scan package under `.specify/prd-runs/<run-id>/`, not a fresh repository crawl.
- Primary terminal state: completed master pack and exports, or explicit refusal back to `/sp-prd-scan`.

## Objective

[AGENT] Compile the reconstruction package into a delivery-grade PRD suite and prove reverse coverage validation.

`sp-prd-build` must not become a second repository scan. It must not silently fill critical evidence gaps. When the scan package is incomplete, stop and route back to `sp-prd-scan`.
Final outputs must preserve `Evidence`, `Inference`, and `Unknown` labels rather than flattening them during synthesis.

## Context

Required build inputs:

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/prd-scan.md`
- `.specify/prd-runs/<run-id>/coverage-ledger.json`
- `.specify/prd-runs/<run-id>/capability-ledger.json`
- `.specify/prd-runs/<run-id>/artifact-contracts.json`
- `.specify/prd-runs/<run-id>/reconstruction-checklist.json`
- `.specify/prd-runs/<run-id>/scan-packets/<lane-id>.md`
- Project classification from the scan package: `ui`, `service`, or `mixed`.

## Process

1. Validate that the `sp-prd-scan` package is complete enough to build.
2. Compile `.specify/prd-runs/<run-id>/master/master-pack.md` from scan outputs only.
3. Render `.specify/prd-runs/<run-id>/exports/prd.md` and the supporting exports.
4. Respect classification-aware export semantics: `ui`, `service`, and `mixed` runs must keep the final package grounded in the scan classification even when the fixed export set is used.
5. Run reverse coverage validation across capabilities, artifacts, field-level contracts, and `Evidence` / `Inference` / `Unknown` labels.
6. Refuse completion and route back to `sp-prd-scan` when critical gaps remain.

## Output Contract

The build phase writes:

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/master/master-pack.md`
- `.specify/prd-runs/<run-id>/exports/prd.md`
- `.specify/prd-runs/<run-id>/exports/reconstruction-appendix.md`
- `.specify/prd-runs/<run-id>/exports/data-model.md`
- `.specify/prd-runs/<run-id>/exports/integration-contracts.md`
- `.specify/prd-runs/<run-id>/exports/runtime-behaviors.md`

Classification-aware export rule:

- `ui` runs must keep UI-facing behaviors explicit in the exported package.
- `service` runs must keep service, API, CLI, and runtime contract behaviors explicit in the exported package.
- `mixed` runs must preserve both UI and service surfaces rather than collapsing to one side.

## Quality Gates

- No New Facts Gate: final exports must be grounded in the scan package rather than new repository rereads.
- Artifact Landing Gate: critical artifacts from `artifact-contracts.json` must land in the master pack and appropriate exports.
- Field-Level Coverage Gate: field, schema, mapping, and transition details must not be flattened into prose-only summaries.
- Inference Ceiling Gate: inference can summarize evidence, but it cannot replace missing critical facts.
- Evidence Label Gate: outputs and build validation must preserve `Evidence`, `Inference`, and `Unknown` handling.
- Classification Export Gate: `ui`, `service`, and `mixed` classification semantics must survive into the final export package.

## Guardrails

- `sp-prd-build` must not become a second repository scan.
- `sp-prd-build` must not silently fill critical evidence gaps.
- `sp-prd-build` must not strip `Evidence`, `Inference`, or `Unknown` labels from consequential claims.
- If the scan package is incomplete, route back to `sp-prd-scan` instead of guessing.

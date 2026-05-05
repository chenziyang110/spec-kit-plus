---
description: Use when `sp-prd-scan` has produced a complete reconstruction package and the final PRD suite must be compiled from it.
workflow_contract:
  when_to_use: Use after `sp-prd-scan` for a repository that already has a reconstruction-grade scan package ready for synthesis.
  primary_objective: Validate scan completeness, compile the master pack, render final PRD exports, and prove reverse coverage validation without inventing new facts.
  primary_outputs: '`.specify/prd-runs/<run-id>/workflow-state.md`, `.specify/prd-runs/<run-id>/master/master-pack.md`, `.specify/prd-runs/<run-id>/exports/prd.md`, `.specify/prd-runs/<run-id>/exports/reconstruction-appendix.md`, `.specify/prd-runs/<run-id>/exports/data-model.md`, `.specify/prd-runs/<run-id>/exports/integration-contracts.md`, `.specify/prd-runs/<run-id>/exports/runtime-behaviors.md`, `.specify/prd-runs/<run-id>/exports/config-contracts.md`, `.specify/prd-runs/<run-id>/exports/protocol-contracts.md`, `.specify/prd-runs/<run-id>/exports/state-machines.md`, `.specify/prd-runs/<run-id>/exports/error-semantics.md`, `.specify/prd-runs/<run-id>/exports/verification-surface.md`, and `.specify/prd-runs/<run-id>/exports/reconstruction-risks.md`.'
  default_handoff: Completed PRD suite export, or route back to sp-prd-scan if reconstruction evidence is incomplete.
---

# `/sp.prd-build` Reconstruction Build

## Workflow Contract Summary

This summary is routing metadata only. The full workflow contract is the frontmatter plus the sections below.

- Use `sp-prd-build` after `sp-prd-scan` has produced a validated reconstruction package.
- Primary truth source: the scan package under `.specify/prd-runs/<run-id>/`, not a fresh repository crawl.
- Primary terminal state: completed master pack and exports, or explicit refusal back to `sp-prd-scan`.

## Objective

[AGENT] Compile the reconstruction package into a delivery-grade PRD suite and prove reverse coverage validation.

`sp-prd-build` must not become a second repository scan. It must not silently fill critical evidence gaps. When the scan package is incomplete, stop and route back to `sp-prd-scan`.
Final outputs must preserve `Evidence`, `Inference`, and `Unknown` labels rather than flattening them during synthesis.
Before writing exports, the build step must collect and validate the scan evidence bundle: scan packets, worker results, and the machine-readable reconstruction contracts produced by `sp-prd-scan`. That intake includes results returned by mandatory subagents before any export synthesis begins.

## Context

Required build inputs:

- The scan workspace under `.specify/prd-runs/<run-id>/`
- Core scan artifacts:
  - `workflow-state.md`
  - `prd-scan.md`
  - `coverage-ledger.json`
  - `capability-ledger.json`
  - `artifact-contracts.json`
  - `reconstruction-checklist.json`
- Machine-readable reconstruction contracts:
  - `entrypoint-ledger.json`
  - `config-contracts.json`
  - `protocol-contracts.json`
  - `state-machines.json`
  - `error-semantics.json`
  - `verification-surfaces.json`
- Scan packets under `scan-packets/<lane-id>.md`
- Project classification from the scan package: `ui`, `service`, or `mixed`

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed scope, forbidden actions, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

Build-support lanes operate on the run bundle, not the live repository.

## Required Inputs

Before writing final exports, read:

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/prd-scan.md`
- `.specify/prd-runs/<run-id>/coverage-ledger.json`
- `.specify/prd-runs/<run-id>/capability-ledger.json`
- `.specify/prd-runs/<run-id>/artifact-contracts.json`
- `.specify/prd-runs/<run-id>/reconstruction-checklist.json`
- `.specify/prd-runs/<run-id>/entrypoint-ledger.json`
- `.specify/prd-runs/<run-id>/config-contracts.json`
- `.specify/prd-runs/<run-id>/protocol-contracts.json`
- `.specify/prd-runs/<run-id>/state-machines.json`
- `.specify/prd-runs/<run-id>/error-semantics.json`
- `.specify/prd-runs/<run-id>/verification-surfaces.json`
- `.specify/prd-runs/<run-id>/scan-packets/<lane-id>.md`
- `.specify/prd-runs/<run-id>/worker-results/**`

## PRD Run State Protocol

- `workflow-state.md` under `.specify/prd-runs/<run-id>/` is the resumable state surface for `sp-prd-scan` and `sp-prd-build`.
- [AGENT] Create or resume `workflow-state.md` before substantial build work.
- If `workflow-state.md` exists with `active_command: sp-prd-build` and a non-terminal build state, resume from it instead of rebuilding intent from chat memory.
- Track at least:
  - `active_command: sp-prd-build`
  - `status: validating | executing-packets | synthesizing | reverse-validating | blocked | complete`
  - `scan_status`
  - `build_status: pending | executing | blocked | complete`
  - `classification`
  - `current_packet`
  - `accepted_packet_results`
  - `rejected_packet_results`
  - `failed_readiness_checks`
  - `failed_reverse_coverage_checks`
  - `next_action`
  - `next_command`
  - `handoff_reason`
  - `open_gaps`

## Process

1. Validate that the `sp-prd-scan` package is complete enough to build.
2. Perform packet evidence intake across scan packets, ledgers, JSON contracts, and worker results returned by mandatory subagent lanes.
3. Compile `.specify/prd-runs/<run-id>/master/master-pack.md` from scan outputs only.
4. Render `.specify/prd-runs/<run-id>/exports/prd.md` and the supporting exports.
5. Respect classification-aware export semantics: `ui`, `service`, and `mixed` runs must keep the final package grounded in the scan classification even when the fixed export set is used.
6. Run reverse coverage validation across capabilities, artifacts, field-level contracts, and `Evidence` / `Inference` / `Unknown` labels.
7. Refuse completion and route back to `sp-prd-scan` when critical gaps remain.

## Validate Scan Inputs Before Execution

- Refuse build execution if required scan artifacts are missing or malformed.
- Treat the scan workspace under `.specify/prd-runs/<run-id>/` as the only authoritative fact source for `sp-prd-build`.
- Do not reread the repository to fill gaps.

## Compile And Validate PrdBuildPacket Inputs

- [AGENT] Compile a validated `PrdBuildPacket` before dispatch or `subagent-blocked` status.
- A valid `PrdBuildPacket` must include:
  - `lane_id`
  - `mode: bundle_only`
  - `packet_scope`
  - `required_scan_inputs`
  - `required_contract_files`
  - `required_worker_results`
  - `expected_exports`
  - `traceability_targets`
  - `forbidden_actions`
  - `minimum_verification`
  - `result_handoff_path`
- Hard rule: do not dispatch from raw scan prose alone.

## Readiness Refusal Rules

`sp-prd-build` must refuse completion when:

- required scan artifacts are missing or malformed
- worker results are absent or structurally shallow
- critical reconstruction claims cannot be traced back to scan-package evidence
- export landing for critical artifacts is missing
- unresolved critical unknowns remain in the bundle
- the build would need new repository facts to complete honestly

When refusal happens, report the smallest safe repair and route back to `sp-prd-scan`.

## Execution Dispatch

- [AGENT] Before build-support packet dispatch begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="prd-build", snapshot, workload_shape)`.
- Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
- Decision order is fixed:
  - One safe validated intake or validation lane -> `one-subagent` on `native-subagents` when available.
  - Two or more isolated bundle-processing lanes -> `parallel-subagents` on `native-subagents` when available.
  - Any need for new repository facts, missing build packet, or unavailable delegation -> `subagent-blocked` with a recorded reason.

## Build Packet Dispatch

- `subagent-blocked` stops substantive build work. Record the blocker and stop for escalation or recovery. Do not continue by turning `sp-prd-build` into a second repository scan.
- Required join points:
  - before writing `master/master-pack.md`
  - before writing or finalizing `exports/**`
  - before reverse coverage / traceability validation
- Idle subagent output is not an accepted result.
- The leader must wait for every dispatched build-support lane and integrate the returned evidence before writing exports or declaring the build complete.

## Build Worker Result Contract

Every build-support lane result must include:

- `lane_id`
- `reported_status`
- `bundle_inputs_read`
- `traceability_findings`
- `export_landing_findings`
- `confidence`
- `unknowns`
- `recommended_repairs`
- `minimum_verification`
- `result_handoff_path`

Reject any build-lane output that lacks concrete bundle inputs, omits critical unknowns, or relies on live repository rereads instead of bundle inputs.

## Output Contract

The build phase writes:

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/master/master-pack.md`
- `.specify/prd-runs/<run-id>/exports/prd.md`
- `.specify/prd-runs/<run-id>/exports/reconstruction-appendix.md`
- `.specify/prd-runs/<run-id>/exports/data-model.md`
- `.specify/prd-runs/<run-id>/exports/integration-contracts.md`
- `.specify/prd-runs/<run-id>/exports/runtime-behaviors.md`
- `.specify/prd-runs/<run-id>/exports/config-contracts.md`
- `.specify/prd-runs/<run-id>/exports/protocol-contracts.md`
- `.specify/prd-runs/<run-id>/exports/state-machines.md`
- `.specify/prd-runs/<run-id>/exports/error-semantics.md`
- `.specify/prd-runs/<run-id>/exports/verification-surface.md`
- `.specify/prd-runs/<run-id>/exports/reconstruction-risks.md`

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
- Critical Unknown Refusal Gate: unresolved critical unknowns in the validated scan evidence bundle block final export completion.
- Traceability Gate: every reconstruction claim in the master pack and exports must trace back to scan-package evidence.
- Reconstruction Readiness Gate: the compiled archive must preserve enough L4-level detail to recreate critical behavior.

## Traceability Validation

- Every reconstruction claim in the master pack and exports must trace back to scan-package evidence.
- Reject any build-lane output that relies on live repository rereads instead of bundle inputs.

## Report Completion

- Before reporting success, confirm that `workflow-state.md` records the final build status, accepted packet results, rejected packet results, readiness failures, reverse-coverage outcomes, and the final handoff decision.
- Successful completion must name the bundle inputs read, the accepted packet results that informed `master/master-pack.md` and `exports/**`, and any remaining non-critical unknowns.
- Blocked completion must name the failed readiness or traceability check, the affected packet or export target, and the smallest safe repair to resume through `sp-prd-scan` or the current build run.

## Guardrails

- `sp-prd-build` must not become a second repository scan.
- `sp-prd-build` must not silently fill critical evidence gaps.
- `sp-prd-build` must not strip `Evidence`, `Inference`, or `Unknown` labels from consequential claims.
- If the scan package is incomplete, route back to `sp-prd-scan` instead of guessing.

---
description: Use when an existing repository needs reconstruction-grade scan outputs before a PRD suite can be compiled.
workflow_contract:
  when_to_use: Use for an existing repository that needs read-only reconstruction investigation before final PRD synthesis.
  primary_objective: Produce a reconstruction-grade scan package that captures capability, artifact, and boundary truth strongly enough for `sp-prd-build`.
  primary_outputs: '`.specify/prd-runs/<run-id>/workflow-state.md`, `.specify/prd-runs/<run-id>/prd-scan.md`, `.specify/prd-runs/<run-id>/coverage-ledger.md`, `.specify/prd-runs/<run-id>/coverage-ledger.json`, `.specify/prd-runs/<run-id>/capability-ledger.json`, `.specify/prd-runs/<run-id>/artifact-contracts.json`, `.specify/prd-runs/<run-id>/reconstruction-checklist.json`, `.specify/prd-runs/<run-id>/entrypoint-ledger.json`, `.specify/prd-runs/<run-id>/config-contracts.json`, `.specify/prd-runs/<run-id>/protocol-contracts.json`, `.specify/prd-runs/<run-id>/state-machines.json`, `.specify/prd-runs/<run-id>/error-semantics.json`, `.specify/prd-runs/<run-id>/verification-surfaces.json`, `.specify/prd-runs/<run-id>/scan-packets/<lane-id>.md`, `.specify/prd-runs/<run-id>/evidence/**`, and `.specify/prd-runs/<run-id>/worker-results/**`.'
  default_handoff: sp-prd-build after the scan package passes reconstruction readiness checks.
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

The scan phase is a read-only reconstruction investigation. It must harvest enough grounded detail about each `capability`, `artifact`, and `boundary` to prove whether the package is reconstruction-ready or should be marked `blocked-by-gap`.
Every consequential claim must preserve `Evidence`, `Inference`, and `Unknown` labeling semantics instead of collapsing them into one unmarked narrative.

## Context

Required context inputs:

- `PROJECT-HANDBOOK.md` as the root navigation artifact.
- `.specify/project-map/index/status.json` and the smallest relevant project-map topics when available.
- `.specify/prd/status.json` as the stable PRD scan freshness record when present.
- Current repository evidence from code, docs, tests, routes, UI surfaces, service surfaces, data models, integrations, configuration, and deployment surfaces.
- Existing `workflow-state.md` under `.specify/prd-runs/<run-id>/` when resuming an interrupted run.

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read scope, forbidden actions, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.
Each delegated lane produces a `PrdScanPacket`: a read-only evidence packet with enough cited detail for the build step to synthesize the final archive without rereading the repository.

## Unified Critical Item Families

1. Main Capability Chains
2. External Entrypoints and Command Surfaces
3. State Machines and Flow Control
4. Data and Persistence Contracts
5. Configuration and Behavior Switches
6. Protocol and Boundary Contracts
7. Error Semantics and Recovery Behavior
8. Verification and Regression Entrypoints

## Evidence Depth Model

- `L1 Exists`: the item is discovered and tied to at least one repository surface.
- `L2 Surface`: the user-visible, command, API, config, data, or boundary shape is captured.
- `L3 Behavioral`: normal behavior, edge behavior, state changes, and failure behavior are grounded in evidence.
- `L4 Reconstruction-Ready`: enough structure, contracts, and verification evidence exist to recreate the behavior without critical unknowns.

## Hard Boundary

- `sp-prd-scan` must not write `master/master-pack.md`.
- `sp-prd-scan` must not write `exports/**`.
- `sp-prd-scan` must not claim the PRD suite is complete.

## PRD Run State Protocol

- `workflow-state.md` under `.specify/prd-runs/<run-id>/` is the resumable state surface for `sp-prd-scan` and `sp-prd-build`.
- [AGENT] Create or resume `workflow-state.md` before substantial scan work.
- If `workflow-state.md` exists with `active_command: sp-prd-scan` and a non-terminal scan state, resume from it instead of rebuilding intent from chat memory.
- Track at least:
  - `active_command: sp-prd-scan`
  - `status: scanning | synthesizing | blocked | ready-for-build`
  - `scan_status: pending | scanning | blocked | complete`
  - `build_status`
  - `freshness_mode`
  - `classification`
  - `selected_capabilities`
  - `selected_boundaries`
  - `selected_artifacts`
  - `current_packet`
  - `accepted_packet_results`
  - `rejected_packet_results`
  - `failed_readiness_checks`
  - `next_action`
  - `next_command`
  - `handoff_reason`
  - `open_gaps`

## Process

1. Route and initialize the PRD run under `.specify/prd-runs/<run-id>/`.
2. Load brownfield context and select the smallest relevant repository surfaces.
3. Check `.specify/prd/status.json` freshness before scoping the scan.
4. Route `fresh` status to status confirmation only unless the user explicitly requests a new run.
5. Route `targeted-stale` status to a bounded scan of the changed source, test, and documentation surfaces plus any directly adjacent capability boundaries.
6. Route `full-stale` status to a full reconstruction scan across command, workflow, integration, configuration, and shared-runtime surfaces.
7. Triage `capability`, `artifact`, and `boundary` objects before broad synthesis.
8. Assign each capability a tier: `critical`, `high`, `standard`, or `auxiliary`.
9. Before broad scan fan-out begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="prd-scan", snapshot, workload_shape)`.
10. Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
11. Decision order is fixed:
    - One safe validated scan lane -> `one-subagent` on `native-subagents` when available.
    - Two or more safe read-only scan lanes -> `parallel-subagents` on `native-subagents` when available.
    - No safe lane, incomplete packet, or unavailable delegation -> `subagent-blocked` with a recorded reason.
12. Compile a validated `PrdScanPacket` before dispatch or `subagent-blocked` status.
13. For `one-subagent`, dispatch one read-only scan lane once a validated `PrdScanPacket` exists. If the packet is incomplete, compile the missing fields before dispatch; if dispatch is unavailable, record `subagent-blocked` with the blocker and stop for escalation or recovery before broad scan work continues.
14. If collaboration is justified, keep `prd-scan` lanes read-only and limited to reconstruction evidence gathering, tier classification, and packet drafting.
15. Required join points:
    - before freezing ledgers and machine-readable contracts
    - before declaring the package ready for `sp-prd-build`
16. The leader owns final ledger normalization, contract updates, and packet quality even when subagents help with scan work.
17. For `critical` and `high` capabilities, capture stronger reconstruction detail: structure, producers, consumers, constraints, compatibility behavior, and failure behavior.
18. Build `.specify/prd-runs/<run-id>/artifact-contracts.json` and `.specify/prd-runs/<run-id>/reconstruction-checklist.json`.
19. Generate scan packets and evidence notes that explain structure, producers, consumers, constraints, and failure behavior while preserving `Evidence`, `Inference`, and `Unknown`.
20. Refuse handoff if any `critical` capability lacks reconstruction-ready support. `high` capabilities must not be waved through with path-only evidence; keep the status explicit as `blocked-by-gap` when evidence is insufficient.

## Output Contract

The scan phase writes only the reconstruction package:

- `.specify/prd-runs/<run-id>/workflow-state.md`
- `.specify/prd-runs/<run-id>/prd-scan.md`
- `.specify/prd-runs/<run-id>/coverage-ledger.md`
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
- `.specify/prd-runs/<run-id>/evidence/**`
- `.specify/prd-runs/<run-id>/worker-results/**`
- `.specify/prd/status.json` when initializing a successful scan and the stable status file is absent

These artifacts are the authoritative scan bundle for `sp-prd-build`; they are not draft exports.

## Compile And Validate PrdScanPacket Inputs

- [AGENT] Compile a validated `PrdScanPacket` before dispatch or `subagent-blocked` status.
- A valid `PrdScanPacket` must include:
  - `lane_id`
  - `mode: read_only`
  - `scope`
  - `capability_ids`
  - `artifact_ids`
  - `boundary_ids`
  - `required_reads`
  - `excluded_paths`
  - `required_questions`
  - `expected_outputs`
  - `contract_targets`
  - `forbidden_actions`
  - `result_handoff_path`
  - `join_points`
  - `minimum_verification`
  - `blocked_conditions`
- Hard rule: do not dispatch from raw scan prose or broad chat instructions alone.

## PrdScanPacket Dispatch

- If no safe lane exists, the packet is incomplete, or delegation is unavailable, record `subagent-blocked` with the blocker and stop for escalation or recovery before broad scan work continues.
- Raw inventory notes or raw chat summaries are not sufficient subagent inputs or outputs.
- Each dispatched lane needs a validated `PrdScanPacket` and must return a structured handoff with inspected paths, key facts, confidence, blockers, and recommended contract updates.
- Idle subagent output is not an accepted scan result.
- The leader must wait for every dispatched lane and consume its structured handoff before finalizing ledgers, writing scan packets, or marking the scan complete.

## Worker Result Contract

Every scan-lane result must include:

- `lane_id`
- `reported_status: done | done_with_concerns | blocked | needs_context`
- `paths_read`
- `key_facts`
- `evidence_refs`
- `recommended_contract_updates`
- `confidence`
- `unknowns`
- `minimum_verification`
- `result_handoff_path`

Reject results that omit `paths_read`, collapse evidence into prose-only summary, hide `unknowns`, or leave contract impact undefined where one is expected.

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
- When refusal is required, report the smallest safe repair instead of softening the gap into narrative prose.

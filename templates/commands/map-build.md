---
description: Use when `sp-map-scan` has produced a full evidence baseline and you need to reconstruct the project cognition graph, claims, conflicts, and slices.
workflow_contract:
  when_to_use: A graph-native scan baseline exists and the project cognition runtime must be built or rebuilt from that evidence.
  primary_objective: Validate scan evidence, reconstruct graph nodes and edges, synthesize claims, assign confidence, create conflicts, and publish task-oriented cognition slices.
  primary_outputs: '`.specify/project-cognition/status.json`, `.specify/project-cognition/graph/nodes.json`, `.specify/project-cognition/graph/edges.json`, `.specify/project-cognition/graph/claims.json`, `.specify/project-cognition/graph/conflicts.json`, `.specify/project-cognition/graph/updates.json`, and `.specify/project-cognition/slices/`.'
  default_handoff: Return to the blocked brownfield workflow once the graph-native cognition baseline is ready.
---

{{spec-kit-include: ../command-partials/map-build/shell.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

## Objective

Reconstruct or refresh the graph-native project cognition runtime from a completed evidence baseline.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command map-build --format json}}` when available so passive learning files exist and repeated graph-build blind spots can be promoted at start.
- [AGENT] When graph reconstruction friction appears, use the `signal-learning` helper surface: `{{specify-subcmd:hook signal-learning --command map-build --route-changes <n> --artifact-rewrites <n> --validation-failures <n>}}`.
- [AGENT] Before reporting completion or a blocked build, use the `review-learning` helper surface: `{{specify-subcmd:hook review-learning --command map-build --terminal-status <resolved|blocked> --decision <none|captured|deferred> --rationale "<why>"}}`.

## Process

- Start with validation, not writing.
- Run `{{specify-subcmd:hook checkpoint --command map-build}}` before long-running reconstruction, join-point acceptance, or compaction-risk transitions.
- Validate scan inputs before execution and compile/validate `MapBuildPacket` inputs before dispatch.
- Dispatch only validated packetized build lanes as `one-subagent` or `parallel-subagents`.
- If overlap, missing packet data, missing required references, or unsafe acceptance criteria prevent safe dispatch, record `subagent-blocked` and stop for escalation or recovery.
- Use `{{specify-subcmd:hook complete-refresh}}` only after the graph-ready baseline and accepted compatibility/export refresh outputs are complete.

## Hard Boundary

- `sp-map-build` is the command that publishes graph-native cognition truth.
- `sp-map-build` must not fall back to handbook-first runtime output.
- `sp-map-build` owns claim synthesis, `truth_layer` assignment, confidence assignment, conflict construction, and slice publication.
- Existing narratives may inform continuity, but final graph claims must be backed by scan evidence.

## Required Inputs

Before writing graph-native truth, read:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/evidence/`
- `.specify/project-cognition/provisional/nodes.json`
- `.specify/project-cognition/provisional/edges.json`
- `.specify/project-cognition/provisional/observations.json`
- `.specify/project-cognition/coverage.json`
- `.specify/project-map/coverage-ledger.json`
- `.specify/project-map/scan-packets/`

If those artifacts are missing, stop and route back to `/sp-map-scan`.

## Output Contract

The only canonical runtime outputs for this command are:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/graph/nodes.json`
- `.specify/project-cognition/graph/edges.json`
- `.specify/project-cognition/graph/claims.json`
- `.specify/project-cognition/graph/conflicts.json`
- `.specify/project-cognition/graph/updates.json`
- `.specify/project-cognition/slices/`
- join-point `worker-results` evidence for delegated build lanes until the leader accepts the final graph-ready baseline
- `.specify/project-map/worker-results/<packet-id>.json`

Do not publish handbook-first runtime truth from this command.

## Guardrails

- Do not rebuild the scan from chat memory.
- Do not guess and continue when required scan inputs are incomplete.
- Do not treat raw scan prose or raw Markdown checklist items alone as accepted build evidence.
- Do not accept packet results without inspected paths, evidence, and confidence.
- Do not perform a structural-only refresh and call it success.
- If the build lane cannot be safely packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.
- If a delegated lane returns unresolved evidence gaps, preserve the scan gap report and stop for escalation or recovery instead of inventing closure.

## Project Map State Protocol

- Project Map State Protocol remains active during build acceptance.
- Validate Scan Inputs Before Execution.
- Compile And Validate MapBuildPacket Inputs.
- Treat `coverage-ledger.json` as the machine-readable row source.
- `MapBuildPacket` is required for delegated build lanes.
- Raw scan prose or raw Markdown checklist items alone are insufficient.
- raw scan prose or raw Markdown checklist items alone
- Packet evidence intake must reject packet results without paths read.
- Packet evidence intake must reject packet results that only summarize without evidence.
- derived-only evidence is insufficient for final graph acceptance.
- Structural-only refresh is a failed build.
- The build phase is not a scaffold, migration, or file-moving command.
- Treat scan artifacts as inputs, not evidence, until packet evidence is accepted.

## Build Duties

`sp-map-build` must:

- begins with validation, not writing
- validate scan completeness for graph reconstruction
- deduplicate provisional nodes into graph nodes
- convert candidate edges into validated graph edges
- synthesize claims from evidence with explicit `truth_layer`
- assign claim confidence
- create explicit conflict records
- publish graph-native slices for downstream agent work
- produce workflow-operational reachability validation
- produce reverse coverage validation
- do not rebuild the scan from chat memory
- must not guess and continue when required scan inputs are incomplete
- maintain a scan gap report when unresolved critical rows remain

## Required Graph Semantics

Every accepted graph build must make room for:

- nodes
- edges
- claims
- conflicts
- updates
- slices

At minimum, claims must include:

- `backing_evidence_ids`
- `truth_layer`
- `confidence`

## Runtime Compatibility Outputs

- `DEBUG-HANDBOOK.md`
- `BUILD-HANDBOOK.md`
- `DEBUG-WORKFLOW-CONTRACT`
- `BUILD-WORKFLOW-CONTRACT`
- `INVESTIGATION-PLAYBOOKS`
- `IMPLEMENTATION-PLAYBOOKS`

## Dispatch Guidance

- Use `choose_subagent_dispatch(command_name="map-build", snapshot, workload_shape)` before lane execution.
- Dispatch each build lane from a validated `MapBuildPacket`.
- Recommended build lanes include graph normalization, claim synthesis, conflict review, and slice generation.
- The leader owns final graph consistency and readiness state.

## Completion Rule

Before reporting completion:

- use `complete-refresh` once the graph-ready baseline and compatibility/export refresh workbench outputs have been accepted
- use `{{specify-subcmd:hook complete-refresh}}` once the graph-ready baseline and compatibility/export refresh workbench outputs have been accepted
- confirm that graph artifacts were written under `.specify/project-cognition/graph/`
- confirm that slices were published under `.specify/project-cognition/slices/`
- confirm that `status.json` reflects a graph-ready baseline
- confirm that the runtime remains graph-native and does not advertise handbook-first outputs
- report whether follow-on localized maintenance should continue through `map-update` for future touched-area drift
- every `critical` row appears in at least one final handbook target
- every `important` row appears in a final handbook target
- every scan packet is consumed
- every accepted packet result has paths read and confidence
- every final handbook target is backed by at least one accepted packet evidence row
- no final report claims success for a structural-only refresh
- `map_state_file` records accepted packet results
- owner, consumer, change propagation, and verification routes remain explicit
- known unknowns or known-unknowns remain visible
- the excluded bucket has a reason and revisit condition
- every critical shared surface can be discovered from the relevant handbook
- every key verification entry point can be located from the relevant handbook
- required_reads contain only reference-only or hard-excluded exceptions when runtime compatibility outputs are mentioned

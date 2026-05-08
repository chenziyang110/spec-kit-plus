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

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command map-build --format json}}` when available so passive learning files exist and repeated graph-build blind spots can be promoted at start.
- [AGENT] When graph reconstruction friction appears, use the `signal-learning` helper surface: `{{specify-subcmd:hook signal-learning --command map-build --route-changes <n> --artifact-rewrites <n> --validation-failures <n>}}`.
- [AGENT] Before reporting completion or a blocked build, use the `review-learning` helper surface: `{{specify-subcmd:hook review-learning --command map-build --terminal-status <resolved|blocked> --decision <none|captured|deferred> --rationale "<why>"}}`.

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

Do not publish handbook-first runtime truth from this command.

## Build Duties

`sp-map-build` must:

- validate scan completeness for graph reconstruction
- deduplicate provisional nodes into graph nodes
- convert candidate edges into validated graph edges
- synthesize claims from evidence with explicit `truth_layer`
- assign claim confidence
- create explicit conflict records
- publish graph-native slices for downstream agent work

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

## Dispatch Guidance

- Use `choose_subagent_dispatch(command_name="map-build", snapshot, workload_shape)` before lane execution.
- Recommended build lanes include graph normalization, claim synthesis, conflict review, and slice generation.
- The leader owns final graph consistency and readiness state.

## Completion Rule

Before reporting completion:

- confirm that graph artifacts were written under `.specify/project-cognition/graph/`
- confirm that slices were published under `.specify/project-cognition/slices/`
- confirm that `status.json` reflects a graph-ready baseline
- confirm that the runtime remains graph-native and does not advertise handbook-first outputs

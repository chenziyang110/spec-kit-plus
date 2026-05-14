---
description: Use when `sp-map-scan` has produced a full evidence baseline and you need to reconstruct the project cognition SQLite runtime.
workflow_contract:
  when_to_use: A scan baseline exists and the project cognition runtime must be built or rebuilt from that evidence.
  primary_objective: Validate scan evidence, reconstruct graph nodes and edges into the SQLite cognition database, synthesize claims, assign confidence, create conflicts, and publish queryable task-oriented cognition bundles.
  primary_outputs: '`.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, and query/update helper readiness metadata.'
  default_handoff: Return to the blocked brownfield workflow once the query-backed cognition baseline is ready.
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

Reconstruct or refresh the query-backed project cognition runtime from a completed evidence baseline.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command map-build --format json}}` when available so passive learning files exist and repeated graph-build blind spots can be promoted at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader graph-build context.
- Open only learning detail docs linked from map-build-relevant index entries.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- [AGENT] When graph reconstruction friction exposes route changes, artifact rewrites, validation gaps, false starts, hidden dependencies, or reusable constraints, make sure `map-state.md` captures that durable context.
- [AGENT] When durable state does not capture the reusable lesson cleanly, update `.specify/memory/learnings/INDEX.md` and a linked detail document with the command, type, summary, and evidence.

## Process

- Start with validation, not writing.
- Update `map-state.md` before long-running reconstruction, join-point acceptance, compaction-risk transitions, or any stop where resume will depend on more than the visible conversation.
- Validate scan inputs before execution and compile/validate `MapBuildPacket` inputs before dispatch.
- Dispatch only validated packetized build lanes as `one-subagent` or `parallel-subagents`.
- If overlap, missing packet data, missing required references, or unsafe acceptance criteria prevent safe dispatch, record `subagent-blocked` and stop for escalation or recovery.
- Run `{{specify-subcmd:project-cognition validate-build --format json}}` after publishing `.specify/project-cognition/project-cognition.db`.
- Use `{{specify-subcmd:project-cognition complete-refresh --format json}}` only after `validate-build` returns `status=ok` and `readiness=query_ready`.

## Hard Boundary

- `sp-map-build` is the command that publishes query-backed cognition truth.
- `sp-map-build` must not fall back to handbook-first runtime output.
- `sp-map-build` owns claim synthesis, `truth_layer` assignment, confidence assignment, conflict construction, and SQLite runtime publication.
- Existing narratives may inform continuity, but final graph claims must be backed by scan evidence.

## Required Inputs

Before writing query-backed truth, read:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/evidence/`
- `.specify/project-cognition/provisional/nodes.json`
- `.specify/project-cognition/provisional/edges.json`
- `.specify/project-cognition/provisional/observations.json`
- `.specify/project-cognition/coverage.json`
- `.specify/project-cognition/workbench/coverage-ledger.json`
- `.specify/project-cognition/workbench/scan-packets/`

If those artifacts are missing, stop and route back to `/sp-map-scan`.

## Output Contract

The only canonical runtime outputs for this command are:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/project-cognition.db`
- query/update helper readiness metadata
- join-point `worker-results` evidence for delegated build lanes until the leader accepts the final query-ready baseline
- `.specify/project-cognition/workbench/worker-results/<packet-id>.json`

Do not publish handbook-first runtime truth from this command. Do not publish raw graph JSON artifacts or slices as runtime truth.

## Guardrails

- Do not rebuild the scan from chat memory.
- Do not guess and continue when required scan inputs are incomplete.
- Do not treat raw scan prose or raw Markdown checklist items alone as accepted build evidence.
- Do not accept packet results without inspected paths, evidence, and confidence.
- Do not perform a structural-only refresh and call it success.
- If the build lane cannot be safely packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.
- If a delegated lane returns unresolved evidence gaps, preserve the scan gap report and stop for escalation or recovery instead of inventing closure.

## Project Cognition Workbench State Protocol

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
- publish queryable task-oriented bundles for downstream agent work
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
- queryable task-local bundles

At minimum, claims must include:

- `backing_evidence_ids`
- `truth_layer`
- `confidence`

## Dispatch Guidance

- Use `choose_subagent_dispatch(command_name="map-build", snapshot, workload_shape)` before lane execution.
- Dispatch each build lane from a validated `MapBuildPacket`.
- Recommended build lanes include DB normalization, claim synthesis, conflict review, and queryable task-local bundle generation.
- The leader owns final graph consistency and readiness state.

## Completion Rule

Before reporting completion:

- run `{{specify-subcmd:project-cognition validate-build --format json}}` after publishing `.specify/project-cognition/project-cognition.db`
- use `{{specify-subcmd:project-cognition complete-refresh --format json}}` only after `validate-build` returns `status=ok` and `readiness=query_ready`
- confirm that `.specify/project-cognition/project-cognition.db` was written and can be queried through `{{specify-subcmd:project-cognition query --intent implement --query "$ARGUMENTS" --format json}}`
- if `validate-build` returns `status=blocked`, report the specific DB, schema, active generation, status, or smoke-query error and do not mark the baseline fresh
- confirm that `status.json` reflects a query-ready baseline
- confirm that the runtime remains query-backed and does not advertise raw graph JSON or handbook-first outputs as runtime truth
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

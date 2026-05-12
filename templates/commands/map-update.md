---
description: Use when a graph-native project cognition baseline already exists and diff-based evidence refresh or user-supplied corrections must update it incrementally.
workflow_contract:
  when_to_use: A project cognition baseline exists and repository changes or user supplements must update the runtime without a full rebuild.
  primary_objective: Compute impact closure, refresh affected evidence, update claims and conflicts, and rebuild only the affected graph slices.
  primary_outputs: '`.specify/project-cognition/status.json`, `.specify/project-cognition/graph/updates.json`, refreshed graph artifacts, and refreshed slices under `.specify/project-cognition/slices/`.'
  default_handoff: Return to the blocked workflow once the affected slices are green or yellow.
---

## Objective

Refresh the existing graph-native project cognition baseline incrementally from diff-driven evidence or explicit user corrections.

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

## Process

- Read the current graph-native baseline and determine the affected closure before editing runtime outputs.
- Prefer the smallest update that can truthfully restore readiness.
- Treat explicit user corrections and user-supplied scope as first-class routing input; user-supplied scope is authoritative for the touched area unless repository evidence disproves it.
- Dispatch only validated incremental update lanes with bounded affected scope.
- A tiny localized refresh may stay as one bounded lane even when native subagents are available.
- If a safe update lane cannot be packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.
- Rebuild only the affected graph slices when the evidence proves the scoped refresh is sufficient.

## Incremental Rule

- `sp-map-update` is the normal maintenance entrypoint after baseline build.
- It must accept both diff-driven and user-supplement-driven updates.
- It must update graph-native cognition artifacts incrementally.
- It must treat `.specify/project-cognition/status.json` as the runtime truth source for post-update readiness.
- It must not silently escalate to a full rebuild without recording why.
- It must prefer metadata-only or single-slice updates when those are sufficient.
- After recording updates, re-evaluate runtime readiness through the shared freshness contract.
- If the re-evaluated runtime is `fresh` with `readiness=ready`, finalize the successful refresh through `specify project-map complete-refresh` so compatibility freshness metadata cannot remain stale.
- Do not report refresh completion when the runtime remains blocked.
- A recorded refresh is not automatically a ready refresh: `partial_refresh` means update metadata was written but readiness still failed.

## Required Inputs

At minimum, read:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/graph/nodes.json`
- `.specify/project-cognition/graph/edges.json`
- `.specify/project-cognition/graph/claims.json`
- `.specify/project-cognition/graph/conflicts.json`
- `.specify/project-cognition/graph/updates.json` if present
- affected graph slices under `.specify/project-cognition/slices/` when they exist
- relevant existing evidence records under `.specify/project-cognition/evidence/`
- changed paths or changed commit range
- user supplement input if provided

## Output Contract

The canonical outputs for this command are:

- updated `.specify/project-cognition/status.json`
- updated `.specify/project-cognition/graph/updates.json`
- refreshed affected graph artifacts
- refreshed affected slices
- the post-recording freshness result, including `freshness`, `readiness`, and `recommended_next_action`
- when the post-recording freshness result is ready, a completed compatibility finalizer via `specify project-map complete-refresh`

## Guardrails

- Do not silently escalate to a full rebuild without recording why.
- Do not refresh unaffected slices just because the touched area is ambiguous.
- Do not invent closure when changed paths or user supplements do not support the update.
- Do not re-read or rewrite the full graph when status.json, graph/updates.json, and one or two affected slices are sufficient.
- Do not split small localized updates into parallel scan-style lanes just because subagents are available.
- If the affected update lane cannot be safely packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.

## Escalation Boundary

- Escalate to `sp-map-scan`, then `sp-map-build` only when the current baseline is unusable or the affected closure cannot be bounded safely.
- Record the exact reason for escalation, including which closure or readiness fact could not be resolved incrementally.

## Update Duties

`sp-map-update` must:

- compute diff impact closure
- refresh affected evidence
- invalidate stale claims
- update or create conflicts
- rebuild only affected graph slices when safe
- produce an incremental update record
- verify the shared freshness contract after the update record is written
- run the successful-refresh finalizer when that verification proves the runtime ready

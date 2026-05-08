---
description: Use when a graph-native project cognition baseline already exists and diff-based evidence refresh or user-supplied corrections must update it incrementally.
workflow_contract:
  when_to_use: A project cognition baseline exists and repository changes or user supplements must update the runtime without a full rebuild.
  primary_objective: Compute impact closure, refresh affected evidence, update claims and conflicts, and rebuild only the affected graph slices.
  primary_outputs: '`.specify/project-cognition/status.json`, `.specify/project-cognition/graph/updates.json`, refreshed graph artifacts, and refreshed slices under `.specify/project-cognition/slices/`.'
  default_handoff: Return to the blocked workflow once the affected slices are green or yellow.
---

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

## Incremental Rule

- `sp-map-update` is the normal maintenance entrypoint after baseline build.
- It must accept both diff-driven and user-supplement-driven updates.
- It must update graph-native cognition artifacts incrementally.
- It must not silently escalate to a full rebuild without recording why.

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

## Update Duties

`sp-map-update` must:

- compute diff impact closure
- refresh affected evidence
- invalidate stale claims
- update or create conflicts
- rebuild only affected graph slices when safe
- produce an incremental update record

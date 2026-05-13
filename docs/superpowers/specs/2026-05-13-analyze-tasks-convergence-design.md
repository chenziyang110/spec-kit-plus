# Analyze/Tasks Convergence Design

**Date:** 2026-05-13  
**Status:** Approved for implementation planning  
**Scope:** `sp-analyze`, `sp-tasks`, shared task template guidance, workflow-state handoff guidance, README/handbook operator docs, and regression tests that assert generated workflow behavior  
**Primary goal:** Stop normalizing repeated `sp-tasks -> sp-analyze -> sp-tasks` loops by making the first analysis pass expose the full blocker set and making `sp-tasks` self-audit task-layer readiness before it hands off.

## Context

`sp-tasks` currently has a mandatory handoff to `sp-analyze` before implementation. That is the right safety posture: task generation should not authorize implementation until a cross-artifact gate has checked `spec.md`, `context.md`, `plan.md`, and `tasks.md`.

The observed operator failure is different. A user can run `sp-tasks`, get routed to `sp-analyze`, fix what analysis reports, rerun `sp-tasks`, get routed back to `sp-analyze`, and then see a new class of findings. Repeating this several times creates the impression that the workflow is working as designed, when in fact the gate is discovering blockers incrementally.

That incremental discovery is the bug. A healthy analysis gate should find the complete relevant blocker set for the current artifact set. A healthy task-generation workflow should run enough task-layer self-checking that obvious `sp-analyze` task findings are fixed before `sp-tasks` exits.

## Problem

The current contracts allow a multi-cycle loop for four reasons.

First, `sp-analyze` emits exactly one recommended next command based on the highest invalid stage. That is useful for routing, but it can unintentionally encourage agents to stop once they have enough evidence to route backward. When that happens, lower-stage or same-stage blockers are deferred to the next run instead of being reported in the same blocker bundle.

Second, `sp-tasks` carries many obligations: locked planning decisions, implementation constitution rules, guardrail mappings, reference fidelity mappings, parallel write-set safety, validation commands, and dispatch packet readiness. The template tells agents to generate these items, but it does not define an explicit analyze-compatible self-audit that must pass before final handoff.

Third, some findings look like task defects while their root cause is actually upstream. For example, a missing task guardrail may be caused by `plan.md` lacking an implementation constitution or required implementation references. If `sp-tasks` tries to patch around that without escalating, the next `sp-analyze` pass finds the deeper upstream issue.

Fourth, revalidation lacks finding attribution. When a later `sp-analyze` pass reports a new blocker, the workflow does not force an explanation of whether the blocker was missed by the prior analysis, introduced by remediation, caused by an upstream artifact change, or caused by an intentional detector-scope change.

## Goals

- Make the first `sp-analyze` pass produce a complete blocker bundle for the current artifact set instead of reporting only enough to route.
- Preserve the single recommended next command while still reporting all blocking findings grouped by invalid stage.
- Make repeated task/analyze loops abnormal, not an accepted workflow shape.
- Add an analyze-compatible task-layer self-audit to `sp-tasks` so task-only defects are fixed before handoff.
- Make `sp-tasks` fail closed and escalate when a finding cannot be repaired honestly at the task layer.
- Add revalidation attribution for any new finding after remediation.
- Keep `sp-analyze` read-only for planning artifacts.
- Keep `sp-implement` blocked until the analyze gate clears.

## Non-Goals

- Do not remove the mandatory analyze gate after `sp-tasks`.
- Do not let `sp-analyze` edit `spec.md`, `context.md`, `plan.md`, or `tasks.md`.
- Do not make `sp-tasks` repair `spec.md`, `context.md`, or `plan.md`.
- Do not introduce a new public workflow command for this behavior.
- Do not require a full structured database or new runtime service for finding persistence in the first implementation.

## Proposed Design

### 1. Complete Blocker Bundle in `sp-analyze`

`sp-analyze` must complete its detection matrix before selecting the single recommended next command. The command still recommends one re-entry point, but the report must include all blocking findings discovered during the pass.

The mandatory detection matrix is:

- Duplication
- Ambiguity
- Underspecification
- Constitution alignment
- Coverage gaps
- Locked decision drift
- Reference behavior preservation
- Boundary guardrail gaps: `BG1`, `BG2`, `BG3`
- Dispatch packet gaps: `DP1`, `DP2`, `DP3`
- Inconsistency
- Unmapped tasks

The report should add a `Blocker Bundle` section after the findings table. The bundle groups findings by invalid stage:

```markdown
## Blocker Bundle

| Invalid Stage | Blocking Finding IDs | Required Re-entry |
|---------------|----------------------|-------------------|
| plan | BG1-001, LOCKED-002 | sp-plan |
| tasks | BG2-001, DP2-001, COV-003 | sp-tasks |
```

The recommended next command is still based on the highest invalid stage. The difference is that all findings from the pass remain visible, so the user and downstream workflow are not surprised by same-artifact blockers on the next cycle.

### 2. Stable Finding Identity

Findings need stable IDs that survive revalidation. Category-only IDs such as `BG2` are too coarse, but run-local sequence numbers are also not enough because detection order can change. The stable identity contract is fingerprint-first:

1. Build a canonical finding fingerprint from category, invalid stage, artifact, requirement or section key when available, normalized summary, and remediation requirement.
2. Before assigning IDs, load the previous analyze gate ledger from `workflow-state.md`.
3. Match current findings to previous open or recently cleared findings by fingerprint first, and reuse the prior ID when the fingerprint matches.
4. Allocate a new ID only for a genuinely new fingerprint.
5. For new fingerprints, allocate the next unused category sequence after sorting by category, artifact, section key, and normalized summary, or use a short fingerprint-derived suffix if the implementation can do that deterministically.

This keeps examples such as `BG2-001` readable while making the reuse rule explicit. The ID is stable because the prior fingerprint wins, not because the current run happened to discover findings in the same order.

Recommended ID families:

- `DUP-###`
- `AMB-###`
- `UNDER-###`
- `CONST-###`
- `COV-###`
- `LOCKED-###`
- `REF-###`
- `BG1-###`, `BG2-###`, `BG3-###`
- `DP1-###`, `DP2-###`, `DP3-###`
- `INC-###`
- `UNMAPPED-###`

The report should include a compact fingerprint basis for each finding: category, invalid stage, artifact, requirement or section key when available, and a short summary. Exact line numbers may change after remediation, so they should not be the only matching mechanism.

### 3. Revalidation Attribution

When `sp-analyze` runs after a blocked analyze gate, it enters revalidation mode. It first checks previously open findings and then runs the full detection matrix again.

Any finding that appears for the first time during revalidation must include one attribution:

- `missed_by_previous_analyze`: the finding was detectable in the prior artifact set and should have been included in the earlier blocker bundle.
- `introduced_by_remediation`: remediation changed `tasks.md` or downstream state in a way that introduced the issue.
- `upstream_artifact_changed`: `spec.md`, `context.md`, `plan.md`, or another authoritative input changed since the prior analyze pass.
- `detector_scope_changed`: the workflow template or analysis instructions changed the detector scope between runs.

If there is no evidence for `introduced_by_remediation`, `upstream_artifact_changed`, or `detector_scope_changed`, the default attribution is `missed_by_previous_analyze`.

This is intentionally strict. It makes repeated loops diagnosable and discourages partial analysis passes.

### 4. Analyze-Compatible Task Self-Audit in `sp-tasks`

Before `sp-tasks` writes its final report and recommends `sp-analyze`, it must run a task-layer self-audit aligned with the task-related parts of `sp-analyze`.

The self-audit must check:

- Every buildable `FR-*` and buildable success criterion has at least one task, checkpoint, or explicit deferred note.
- Every locked planning decision that affects implementation, compatibility, rollout, validation, sequencing, architecture shape, or guardrails appears in `tasks.md`.
- `Implementation Constitution` rules from `plan.md` are preserved through a guardrail phase, task guardrail index, task notes, or explicit escalation.
- The `Task Guardrail Index` maps applicable guardrails to concrete implementation tasks.
- Each `[P]` task or explicit parallel batch has objective, write set, required references, forbidden drift, validation command, and done condition.
- Task packet readiness covers the `DP1`, `DP2`, and `DP3` families as far as task generation can determine before implementation.
- Reference fidelity behavior items are mapped to task IDs, checkpoints, join points, or explicit deferred notes.
- Unmapped tasks are either justified as setup, polish, verification, or cross-cutting tasks, or removed.
- Task dependencies and parallel batches do not contain obvious write-set conflicts.

If this self-audit finds task-layer defects, `sp-tasks` must repair them before completing. If it finds that the task layer cannot be repaired because upstream artifacts are missing required truth, `sp-tasks` must stop and route to the appropriate upstream stage instead of producing speculative tasks.

### 5. Task Remediation Mode

When `workflow-state.md` records a blocked analyze gate whose next command is `/sp.tasks`, `sp-tasks` enters remediation mode.

In remediation mode, `sp-tasks` must read the prior analyze blocker bundle before regenerating or editing task output. Each task-layer finding receives one disposition:

- `resolved`: fixed in this task pass, with concrete task, guardrail, checkpoint, or packet evidence.
- `deferred`: intentionally deferred with the downstream condition that must clear it.
- `not_applicable`: no longer applicable, with evidence.
- `escalated`: cannot be fixed at the task layer and must reopen `plan`, `clarify`, or `deep-research`.

Escalation is terminal for the current `sp-tasks` run. If `sp-tasks` detects missing upstream truth, it records the escalation evidence in `workflow-state.md` and sets `next_command` directly to the required upstream command (`/sp.plan`, `/sp.clarify`, or `/sp.deep-research`). It must not finish by sending the user back through `/sp.analyze` first. `sp-analyze` remains mandatory after upstream artifacts have been repaired and tasks have been regenerated.

`tasks.md` should include an `Analyze Remediation Mapping` section when remediation mode is active:

```markdown
## Analyze Remediation Mapping

| Finding ID | Disposition | Task/Section Evidence | Notes |
|------------|-------------|-----------------------|-------|
| BG2-001 | resolved | Task Guardrail Index, T004-T009 | Added boundary guardrail mapping |
| DP2-001 | resolved | T006 packet fields | Added required references and forbidden drift |
| COV-001 | resolved | T012, T013 | Added coverage for FR-004 |
```

The final `sp-tasks` report must summarize remediation:

```text
Remediation mode: handled 5 previous analyze findings
resolved: 4
deferred: 0
not_applicable: 0
escalated: 0
next_command: /sp.analyze
```

If a finding is escalated, the final report uses the upstream command instead:

```text
Remediation mode: handled 5 previous analyze findings
resolved: 3
deferred: 0
not_applicable: 0
escalated: 2
next_command: /sp.plan
```

The upstream workflow owns the repair, then `sp-tasks` regenerates from repaired truth and hands off to `sp-analyze` for the normal gate.

### 6. Workflow State Persistence

`workflow-state.md` should persist enough compact information to support revalidation and remediation without relying on chat history.

The first implementation can add a compact section rather than a separate schema file:

```markdown
## Analyze Gate

- gate_status: blocked
- gate_cycle: 1
- highest_invalid_stage: tasks
- blocker_bundle:
  - BG2-001 | tasks | open | tasks.md lacks guardrail mapping for plan constitution rule G-BOUNDARY
  - DP2-001 | tasks | open | parallel batch lacks required references and forbidden drift
- artifact_fingerprint_basis:
  - spec.md: [agent-readable summary or hash when available]
  - context.md: [agent-readable summary or hash when available]
  - plan.md: [agent-readable summary or hash when available]
  - tasks.md: [agent-readable summary or hash when available]
```

This design does not require deterministic hashing in the first pass. If the implementation can safely add hashes later, that can improve attribution. The immediate requirement is durable, readable state.

### 7. Anti-Loop Rule

The generated guidance should state this rule plainly:

```text
No more than one task-layer remediation cycle is expected.
If revalidation finds new task-layer blockers that were detectable before remediation,
classify them as a previous analyze miss or a tasks self-audit failure.
Do not treat repeated task/analyze loops as normal workflow.
```

This rule should appear in `sp-analyze`, `sp-tasks`, and operator documentation. The point is not to hard-abort every second loop mechanically; the point is to change the mental model from "normal closed-loop remediation" to "diagnose why the previous pass failed to converge."

## Data Flow

Normal path:

```text
sp-tasks
  -> analyze-compatible task self-audit
  -> workflow-state next_command: /sp.analyze
  -> sp-analyze full blocker bundle
  -> if no blockers: workflow-state next_command: /sp.implement
```

Task-layer remediation path:

```text
sp-analyze
  -> full blocker bundle includes only tasks-stage blockers
  -> workflow-state next_command: /sp.tasks
  -> sp-tasks remediation mode
  -> tasks.md Analyze Remediation Mapping
  -> sp-tasks self-audit passes
  -> sp-analyze revalidation
  -> sp-implement if cleared
```

Upstream escalation path:

```text
sp-tasks or sp-analyze
  -> detects missing upstream truth
  -> workflow-state next_command: /sp.plan, /sp.clarify, or /sp.deep-research
  -> upstream workflow repairs authoritative truth
  -> sp-tasks regenerates from repaired truth
  -> sp-analyze gate
```

## Files Expected to Change

Primary surfaces:

- `templates/commands/analyze.md`
- `templates/commands/tasks.md`
- `templates/tasks-template.md`
- `templates/workflow-state-template.md`
- `README.md`
- `PROJECT-HANDBOOK.md`
- `tests/test_alignment_templates.py`
- `tests/test_tasks_reporting_guidance.py`

Possible secondary surfaces:

- `tests/integrations/test_integration_codex.py`
- `tests/integrations/test_cli.py`
- `src/specify_cli/hooks/checkpoint_serializers.py`
- related workflow-state serializer or compaction tests

The secondary surfaces should change only if template projection, CLI output tests, or workflow-state serialization paths assert or preserve the older analyze gate shape. If a serializer or compaction helper reads named `workflow-state.md` sections, it must preserve the new `Analyze Gate` section rather than dropping it.

## Acceptance Criteria

- `sp-analyze` guidance requires a complete blocker bundle before selecting the single recommended next command.
- `sp-analyze` guidance requires revalidation attribution for new findings.
- `sp-tasks` guidance requires an analyze-compatible task self-audit before final handoff.
- `sp-tasks` guidance requires remediation mode when returning from a blocked analyze gate.
- `tasks.md` template includes an `Analyze Remediation Mapping` section or equivalent generated-output requirement.
- `templates/workflow-state-template.md` includes an `Analyze Gate` section with gate status, cycle, highest invalid stage, blocker bundle, and artifact fingerprint basis.
- Any workflow-state serializer or compaction path touched by implementation preserves the `Analyze Gate` section.
- README/handbook guidance says repeated task/analyze loops are abnormal and should be diagnosed.
- Regression tests assert the new blocker bundle, self-audit, attribution, remediation mapping, and anti-loop language.
- Existing tests continue to assert that `sp-tasks` hands off to `sp-analyze` and that implementation remains blocked until analyze clears.

## Risks and Mitigations

- **Risk:** The added guidance makes prompts longer.  
  **Mitigation:** Keep the self-audit checklist compact and focused on task-layer checks that map directly to existing analyze findings.

- **Risk:** Agents overfit to the remediation mapping and skip full analysis.  
  **Mitigation:** `sp-analyze` must always rerun the full detection matrix after checking previous findings.

- **Risk:** `sp-tasks` tries to repair upstream defects with speculative task wording.  
  **Mitigation:** Add explicit fail-closed escalation rules when required truth is missing from `plan.md`, `context.md`, or `spec.md`.

- **Risk:** Stable finding IDs are not perfectly deterministic across agents.  
  **Mitigation:** Require enough fingerprint basis in each finding for practical matching, and avoid depending solely on exact line numbers.

## Open Decisions

- Store the first implementation's compact analyze gate state directly in `workflow-state.md`.
- Do not add a separate JSON ledger until there is evidence that markdown state is too weak for projection or tooling.
- Keep `sp-analyze` read-only for planning artifacts.
- Keep `sp-tasks -> sp-analyze` mandatory.
- Treat repeated task-layer loops as a workflow quality failure to diagnose, not as a normal convergence pattern.

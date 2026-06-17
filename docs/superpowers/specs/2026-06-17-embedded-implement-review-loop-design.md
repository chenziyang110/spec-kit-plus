# Embedded Implement Review Loop Design

Date: 2026-06-17

Status: Approved in brainstorming

## Problem

Long `sp-implement` runs can drift after `sp-discussion`, `sp-specify`, `sp-plan`, and `sp-tasks` have produced a large task graph. A feature with dozens of tasks may start from a slightly incomplete or misdirected task package, then keep executing later tasks that depend on earlier incorrect work. The current workflow has useful guardrails, including task self-audit, optional `sp-analyze`, join points, resume audit, and high-risk batch review, but the default path can still behave like a long mechanical queue.

The desired behavior is continuous course correction:

- Review the implementation task package before the first code-writing task starts.
- Review reality after implementation windows and join points.
- Automatically repair task-layer execution artifacts when the goal and plan remain valid.
- Stop only when the issue belongs to upstream truth rather than task execution.

This must not add a user-visible `sp-review` command. Review is an embedded `sp-implement` protocol.

## Goals

- Keep the public workflow as `sp-specify -> sp-plan -> sp-tasks -> sp-implement`.
- Make review mandatory by default inside `sp-implement`.
- Automatically repair remaining task-layer artifacts when the repair is safe.
- Prevent long sequential runs from executing many stale tasks without reassessment.
- Preserve auditability when tasks or packets are automatically rewritten.
- Route back to upstream workflows when review discovers goal, scope, plan, feasibility, or must-preserve conflicts.

## Non-Goals

- Do not introduce a public `/sp.review` workflow or route.
- Do not make `sp-analyze` the default implementation review gate.
- Do not allow embedded review to modify `spec.md`, `alignment.md`, `context.md`, or `plan.md`.
- Do not let review rewrite completed task history.
- Do not require user approval for routine task-layer repairs.

## User-Facing Workflow

The visible flow remains unchanged:

```text
sp-specify -> sp-plan -> sp-tasks -> sp-implement
```

`sp-tasks` still writes `next_command: /sp.implement`. It additionally writes implementation review metadata into task-layer artifacts so `sp-implement` knows the embedded review gate is required.

There is no public `sp-review` command. `sp-auto` should continue routing clean task packages to `sp-implement`; `sp-implement` owns the internal review cycle.

## Internal Execution Model

`sp-implement` runs this loop:

```text
start
-> pre-implement review
-> repair task-layer artifacts when safe
-> execute current window or batch
-> drift review at the window or join point
-> repair remaining tasks or insert repair tasks when safe
-> continue until final validation
-> closeout
```

The embedded review loop has two required gates.

### Pre-Implement Review Gate

This runs before any substantive implementation task. It reviews:

- `tasks.md`
- `task-index.json`
- `task-packets/*.json`
- `handoff-to-implement.json`
- `workflow-state.md`
- upstream read-only truth artifacts needed to verify coverage

It checks whether the task package covers the accepted spec, plan, discussion obligations, consequence obligations, user-observable paths, validation requirements, write sets, dependencies, join points, and packet readiness.

If only task-layer defects are found, it repairs the task artifacts and continues. If upstream truth is invalid or insufficient, it records a blocker and routes to the correct upstream workflow.

### Join-Point Drift Review Gate

This runs after every phase, parallel batch, pipeline stage, join point, and bounded sequential execution window. It reviews:

- actual changed paths
- worker handoffs
- validation evidence
- `implement-tracker.md`
- open gaps and blockers
- remaining tasks and packets

It asks whether the remaining task plan still matches implementation reality. If not, it repairs the remaining task layer before more work continues.

## Review Window Policy

`sp-implement` must not execute a long sequential task list as one unreviewed queue. Default window limits:

```json
{
  "max_completed_tasks_before_review": 5,
  "max_unreviewed_changed_paths": 8,
  "max_unreviewed_validation_failures": 0
}
```

A drift review is required when any limit is reached. Validation failure, worker concerns, open gaps, stale handoffs, or missing real-entrypoint evidence trigger immediate review regardless of task count.

## Safe Repair Boundary

Embedded review may modify task-layer execution artifacts:

- `tasks.md`
- `task-index.json`
- `task-packets/*.json`
- `handoff-to-implement.json`
- `implement-tracker.md`
- `workflow-state.md`
- `implementation-review/*`

It may not modify upstream truth artifacts:

- `spec.md`
- `alignment.md`
- `context.md`
- `plan.md`

Review can change how the accepted work is executed. It cannot change what the accepted work is or why that work is required.

## Repair Categories

### Task-Layer Repairs

These are repaired automatically when they affect incomplete work:

- missing task
- stale task
- wrong dependency
- write-set conflict
- missing validation
- packet field gap
- join-point gap
- task order gap

Examples include inserting a real-entrypoint validation task, updating a packet read scope after a file moved, regenerating dependency order, or serializing tasks that share a registration surface.

### Execution-Layer Repairs

These are repaired by inserting follow-up work before downstream tasks continue:

- implementation gap
- failed validation with known cause
- worker handoff concern
- consumer wiring gap
- real-entrypoint evidence gap

If a completed task is incomplete or wrong, review must not rewrite that task as if it never happened. It inserts a follow-up repair task and preserves the completed-task record.

### Upstream Truth Conflicts

These block automatic repair:

- spec goal conflict
- plan architecture conflict
- scope change required
- must-preserve conflict
- consequence obligation conflict
- unproven implementation chain
- user decision required

The review record must name the highest invalid layer and set the next command to `/sp.clarify`, `/sp.deep-research`, `/sp.plan`, `/sp.tasks`, `/sp.debug`, or `/sp.implement` as appropriate.

## Review Decisions

Every review produces one decision:

- `cleared`
- `repair-and-continue`
- `repair-and-rerun-current-window`
- `blocked-reopen-tasks`
- `blocked-reopen-plan`
- `blocked-reopen-clarify`
- `blocked-deep-research`
- `debug-required`

`cleared` continues normally. Repair decisions update artifacts and continue under the same `sp-implement` run. Blocked decisions update durable state and stop execution.

## Review State

`workflow-state.md`, `handoff-to-implement.json`, task packets, and the implementation execution state should carry review metadata:

```json
{
  "review_gate": {
    "mode": "embedded",
    "status": "pending",
    "scope": "pre-implement",
    "auto_repair_tasks": true,
    "last_reviewed_batch": null
  },
  "review_window_policy": {
    "max_completed_tasks_before_review": 5,
    "max_unreviewed_changed_paths": 8,
    "max_unreviewed_validation_failures": 0
  }
}
```

The state must be updated before crossing a review gate, after any repair, and before stopping for an upstream blocker.

## Audit Artifacts

`sp-implement` writes internal review audit artifacts under:

```text
FEATURE_DIR/implementation-review/
  reviews.ndjson
  repairs.ndjson
  snapshots/
```

`reviews.ndjson` records review inputs, findings, decision, and next action.

`repairs.ndjson` records automatic task-layer changes, changed artifacts, repair operations, and the next selected batch.

`snapshots/` stores lightweight copies of task-layer artifacts before automatic repair, such as:

```text
tasks.before-pre-implement-r1.md
handoff-to-implement.before-pre-implement-r1.json
```

Rules:

- Snapshot before automatic repair.
- Preserve completed tasks as historical facts.
- Only modify incomplete tasks directly.
- Insert follow-up repair tasks for completed-work gaps.
- Revalidate packet readiness after every repair.
- Update `implement-tracker.md` with open gaps, repaired tasks, next action, and review decision.

## Integration Points

### `sp-tasks`

`sp-tasks` should keep recommending `/sp.implement`, while making task packages review-ready:

- write embedded review metadata
- define reviewable join points
- include review window policy
- mark packet regeneration expectations
- preserve task-layer self-audit output for pre-implement review

Generated `tasks.md` should avoid pretending all later tasks are fully known when they depend on earlier implementation evidence. It should use checkpoints and review windows where later work may need refinement.

### `sp-implement`

`sp-implement` owns the embedded review loop:

- run pre-implement review before first implementation task
- run drift review at every join point and review window
- repair task-layer artifacts automatically when safe
- insert follow-up repair tasks instead of rewriting completed work
- route upstream conflicts to the correct workflow
- preserve review records for resume, debug, analyze, and closeout

### Existing Review Helpers

Existing review concepts in `src/specify_cli/orchestration/review_loop.py` and `src/specify_cli/execution/review_schema.py` should be reused or extended. The design should avoid a separate vocabulary for batch review and embedded implementation review when the same finding, review round, severity, and repair-plan ideas apply.

## Error Handling

- If review cannot safely classify a defect, stop as `debug-required` or `blocked-reopen-tasks` rather than guessing.
- If packet regeneration fails, keep the previous snapshot and stop with a task-layer blocker.
- If a repair would change upstream truth, block and route upstream.
- If validation fails for a known implementation defect, insert a repair task and rerun the current window.
- If validation fails for an unknown reason, route to `/sp.debug`.
- If repeated review repair loops occur for the same finding, stop and route to `/sp.debug` or `/sp.tasks` based on whether the failure is execution-side or decomposition-side.

## Testing Strategy

Template and documentation tests should verify:

- `sp-tasks` still recommends `/sp.implement`, not `/sp.review`.
- generated task packages include embedded review metadata.
- `tasks.md` template describes review windows, repair policy, and reviewable join points.
- `implement.md` requires pre-implement review before the first task.
- `implement.md` requires drift review after join points and sequential windows.
- README and `PROJECT-HANDBOOK.md` describe embedded review without changing the public workflow.

Runtime and helper tests should verify:

- sequential windows trigger review after five completed tasks by default.
- review can insert or update incomplete tasks.
- completed tasks are preserved and fixed through follow-up repair tasks.
- review records and repair records are written with snapshots.
- task packet readiness is revalidated after task repair.
- upstream truth conflicts block instead of auto-repairing.
- `sp-auto` continues to route clean task packages to `sp-implement`.

The test suite should prove safety boundaries rather than trying to prove review intelligence.

## Acceptance Criteria

- A clean `sp-tasks` package routes externally to `sp-implement`.
- `sp-implement` cannot start implementation before the pre-implement review gate clears or repairs.
- A long sequential implementation run performs drift review at least every five completed tasks.
- Join points trigger drift review before downstream work continues.
- Safe task-layer defects are repaired automatically.
- Completed task history is never rewritten to hide a correction.
- Review audit artifacts explain why task artifacts changed.
- Upstream truth conflicts stop implementation and name the correct re-entry workflow.
- No public `/sp.review` command appears in user docs, routing docs, or CLI help.

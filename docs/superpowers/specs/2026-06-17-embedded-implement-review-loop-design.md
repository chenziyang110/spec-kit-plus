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
- Preserve upstream-derived workflow state fields through a field-level write allowlist.
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
- selected execution-review fields in `workflow-state.md`
- `implementation-review/*`

It may not modify upstream truth artifacts:

- `spec.md`
- `alignment.md`
- `context.md`
- `plan.md`

Review can change how the accepted work is executed. It cannot change what the accepted work is or why that work is required.

## Workflow State Write Allowlist

`workflow-state.md` is not a general task-layer scratchpad. It carries cross-stage truth, including lifecycle handoff decisions, scenario profile state, required evidence, authoritative files, analyze gate status, and reopen decisions. Embedded review may read those fields as binding inputs but must not rewrite them during automatic task repair.

Embedded review may write only execution-review fields:

- `Embedded Review Gate` or equivalent `review_gate` section
- `review_window_policy`
- `implementation_review` audit pointers, such as latest review id, latest repair id, snapshot paths, and review artifact paths
- execution-review blocker rows produced by the current embedded review
- `next_action` for the current `sp-implement` run
- `blocked_reason` or equivalent current-run blocker summary
- `next_command` only when stopping the current `sp-implement` run with a review decision that routes to `/sp.implement`, `/sp.debug`, `/sp.tasks`, `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`

Embedded review must preserve these upstream-derived or cross-stage fields exactly unless the owning upstream workflow rewrites them:

- `active_profile`
- `required_sections`
- `activated_gates`
- `task_shaping_rules`
- `required_evidence`
- `transition_policy`
- `final_handoff_decision`
- `authoritative_files`
- `allowed_artifact_writes`
- `forbidden_actions`
- existing `Analyze Gate` blocker bundle, attribution, cycle, and status
- existing reopen gate or upstream remediation truth
- source discussion or must-preserve disposition fields

If review discovers that any preserved field is wrong, stale, or insufficient, it records a blocker and routes to the owning workflow. It does not repair those fields inline.

## Task Identity and History Stability

Automatic repair must keep task identity stable enough for trackers, worker results, packet references, dependencies, review records, and audit snapshots.

Rules:

- Completed task IDs are immutable. Do not renumber, reorder by ID, or rewrite completed checklist rows except to preserve their existing checked state.
- Incomplete task IDs should remain stable when their objective remains the same. Repair may update description, dependencies, packet fields, validation, or write scope, but the task keeps its ID.
- New tasks get append-only IDs after the highest existing numeric task ID, for example `T081` after `T080`.
- Follow-up repair tasks for completed-work gaps use append-only IDs and should include a stable repair marker in metadata or description, such as `repair_for: T023` or `refines: T023`.
- If a task must be split, keep the original incomplete task ID for the first or coordinating slice and allocate append-only IDs for added slices. If the original task is completed, do not split it; add follow-up repair tasks instead.
- If a task becomes obsolete before execution, mark it as superseded in `task-index.json`, packet metadata, and review repair records rather than deleting it silently. The checklist row may stay unchecked with a superseded note, or be moved to a superseded section, but references must remain resolvable.
- Dependency order may change, but dependency references must target stable task IDs rather than implied numeric order.
- Every task repair that changes IDs, dependencies, packet names, or task status must update `task-index.json`, affected `task-packets/*.json`, `handoff-to-implement.json`, `implement-tracker.md`, worker-result references when present, and the corresponding review repair record.
- `tasks.md` may remain numerically append-only after repair even when execution order is no longer pure numeric order. The dependency graph and `next_batch` fields become authoritative for execution order after repair.

The implementation plan must decide whether generated task rows use only numeric append IDs or add a stable suffix convention for repair metadata. Either choice must preserve the append-only completed-history rule.

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

Existing review concepts in `src/specify_cli/orchestration/review_loop.py` and `src/specify_cli/execution/review_schema.py` should inform the implementation, but the current schema is not sufficient by itself. The existing batch review model is oriented around Codex team batch records, categories such as `simplify`, `harden`, and `spec`, and decisions such as `approved` or `fix_required`.

Embedded implementation review needs a schema and runtime extension:

- a general `ImplementationReviewFinding` model that covers task-layer, execution-layer, and upstream-conflict finding types
- a `ReviewDecision` enum covering `cleared`, `repair-and-continue`, `repair-and-rerun-current-window`, `blocked-reopen-tasks`, `blocked-reopen-plan`, `blocked-reopen-clarify`, `blocked-deep-research`, and `debug-required`
- a feature-dir scoped review record writer for `FEATURE_DIR/implementation-review/reviews.ndjson`
- a repair record model and writer for `FEATURE_DIR/implementation-review/repairs.ndjson`
- a snapshot writer for task-layer artifacts before automatic repair
- packet regeneration and packet-readiness validation hooks after repair
- an adapter from existing Codex team batch review records into the embedded review record shape when a batch review is the trigger

The implementation should reuse existing finding severity, review-round, and fix-plan concepts where they fit, but must not force embedded review into Codex team state paths or the existing `approved | fix_required` decision vocabulary.

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
- `workflow-state.md` repairs are limited to the embedded-review field allowlist.
- upstream-derived fields such as `active_profile`, `required_evidence`, `final_handoff_decision`, and existing analyze gate state are preserved during automatic repair.
- completed task IDs are never renumbered, and new repair/refinement tasks use append-only IDs or an explicitly stable suffix convention.
- task-index, packets, dependencies, tracker state, and worker-result references stay consistent after task repair.
- embedded review records use feature-dir audit storage, while Codex team batch review remains an adapter source rather than the only persistence model.
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
- Completed task IDs remain stable, and added repair work uses append-only task identity.
- `workflow-state.md` automatic writes are limited to embedded-review execution fields.
- The review runtime has feature-dir audit records and is not coupled only to Codex team batch review state.
- Review audit artifacts explain why task artifacts changed.
- Upstream truth conflicts stop implementation and name the correct re-entry workflow.
- No public `/sp.review` command appears in user docs, routing docs, or CLI help.

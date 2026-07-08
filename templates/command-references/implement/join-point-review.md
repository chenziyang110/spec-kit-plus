Trigger: after ready batches, review windows, or parallel lane join points.

Purpose: preserve embedded implement review loop, review windows, auto-repair, and branch review preparation.

Preserved Contract: review is embedded in implementation and not a separate public command; join points must be reviewed before continuing.

## Embedded Implement Review Loop

This section is **mandatory**. `sp-implement` includes an internal review-and-repair loop. Do not expose, recommend, or route to a separate public review workflow.

### Pre-Implement Review

Before the first implementation task, run a pre-implement review over `tasks.md`, `task-index.json`, `task-packets/*.json`, `handoff-to-implement.json`, `workflow-state.md`, and the upstream read-only truth artifacts needed to verify coverage.

The review must check:

- every buildable requirement, locked planning decision, `MP-*` obligation, `CA-###` obligation, user-observable path, required evidence term, write set, dependency, join point, and packet-readiness condition still has executable coverage
- the first executable batch is still valid from current repository evidence
- downstream tasks do not depend on unverified assumptions from earlier unfinished work

If only task-layer defects exist, repair task-layer artifacts automatically and continue. If the defect changes goal, scope, architecture, required evidence, `MP-*`, `CA-###`, feasibility, or user decision state, stop and route to `/sp.clarify`, `/sp.deep-research`, `/sp.plan`, `/sp.tasks`, or `/sp.debug` as justified.

### Join-Point Drift Review

After every phase, parallel batch, pipeline stage, join point, and sequential review window, run a drift review before downstream work continues.

The drift review reads actual changed paths, worker handoffs, validation evidence, `implement-tracker.md`, open gaps, blockers, remaining tasks, task packets, and review records. It decides whether the remaining task package still matches implementation reality.

### Sequential Review Window

Do not execute a long sequential task list as one unreviewed queue. Run drift review whenever any limit is reached:

```text
max_completed_tasks_before_review = 5
max_unreviewed_changed_paths = 8
max_unreviewed_validation_failures = 0
```

Validation failure, stale handoff, worker concern, open gap, or missing real-entrypoint evidence triggers immediate drift review.

### Review Decisions

Each review must record one decision:

- `cleared`
- `repair-and-continue`
- `repair-and-rerun-current-window`
- `blocked-reopen-tasks`
- `blocked-reopen-plan`
- `blocked-reopen-clarify`
- `blocked-deep-research`
- `debug-required`

### Safe Repair Boundary

Review may repair `tasks.md`, `task-index.json`, `task-packets/*.json`, `handoff-to-implement.json`, `implement-tracker.md`, selected execution-review fields in `workflow-state.md`, and `implementation-review/*`.

Review must not rewrite upstream truth artifacts or upstream-derived workflow-state fields.

### Workflow-State Write Allowlist

The workflow-state write allowlist for embedded review permits only:

- `review_gate`
- `review_window_policy`
- `implementation_review`
- current-run review blocker rows
- `next_action`
- `blocker_reason`
- `blocked_reason`
- `next_command` when stopping the current `sp-implement` run with a review decision

Embedded review must not rewrite:

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
- existing Analyze Gate truth
- existing Reopen Contract truth
- source discussion or must-preserve disposition fields

If any protected field is wrong, stale, or insufficient, record a blocker and route to the owning upstream workflow.

### Task Identity Stability

- Completed task IDs are immutable and must not be renumbered.
- Incomplete task IDs stay stable when their objective remains the same.
- New repair and refinement tasks use append-only IDs after the highest existing numeric ID.
- Completed-work gaps become follow-up repair tasks with `repair_for: T###` or `refines: T###`.
- Superseded incomplete tasks remain traceable through `task-index.json`, task packets, dependencies, repair records, tracker state, and worker-result references.
- After repair, dependency graph and `next_batch` metadata are authoritative for execution order.

### Audit Artifacts

Before automatic repair, snapshot changed task-layer artifacts under `FEATURE_DIR/implementation-review/snapshots/`.

Record every review in `FEATURE_DIR/implementation-review/reviews.ndjson`.

Record every automatic repair in `FEATURE_DIR/implementation-review/repairs.ndjson`.

For every packetized implementation task accepted by `sp-implement`, maintain:

- `FEATURE_DIR/implementation-review/task-briefs/<task-id>.md`
- `FEATURE_DIR/implementation-review/review-packages/<task-id>.md`
- `FEATURE_DIR/implementation-review/task-reviews/<task-id>.json`
- `FEATURE_DIR/implementation-review/ledger.json`

After all tasks are accepted and before closeout, write `FEATURE_DIR/implementation-review/branch-review.md`.

Task acceptance requires an accepted task review. A checked task is a claim; a ledger entry with `status: accepted` plus `task-reviews/<task-id>.json` is reviewed execution evidence. Ordinary task review uses `spec_verdict`, `quality_verdict`, controller checks, UI fidelity result, and final assessment from the task reviewer.

After repair, revalidate task-index consistency, packet readiness, dependencies, tracker state, and worker-result references before continuing.

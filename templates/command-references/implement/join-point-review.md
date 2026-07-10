Trigger: when repository/task-graph drift, a parallel join, write-scope drift, validation failure, worker concern, obligation conflict, or a sequential review-window limit appears.

Purpose: preserve implementation quality with event-triggered review while avoiding repeated full-package audits and per-task artifact fan-out.

Preserved Contract: implementation review remains embedded, repairs task-layer defects safely, protects upstream truth, and blocks unsupported completion claims.

## Embedded Event-Triggered Review Loop

Do not expose or recommend a separate public review workflow. Review is event-triggered inside `sp-implement`.

### Entry Revision Check

Before the first task, validate the canonical task-graph revision, ready-batch dependencies, current repository baseline, and required obligation refs.

- If the revision and relevant repository baseline are unchanged, trust the upstream task-readiness result and continue without rereading the complete spec/plan package.
- If either changed, inspect only the affected tasks and required refs. Reopen the owning upstream phase when goal, scope, architecture, required evidence, `MP-*`, `CA-###`, feasibility, or user decision state changed.

### Review Triggers

Run a drift review when any of these occurs:

- parallel lanes join;
- actual writes exceed or contradict expected write scope;
- validation fails or becomes inconclusive;
- a worker reports a concern, blocker, or required-reference mismatch;
- an `MP-*` or `CA-###` obligation conflicts with implementation evidence;
- dependency or task-order assumptions become false;
- real-entrypoint or consumer evidence is missing;
- the configured sequential window reaches its completed-task or changed-path threshold.

Do not review merely because a phase label, batch label, or pipeline stage ended. A low-risk leader-direct sequence with no trigger may proceed directly to final reconciliation.

At a parallel join, execute the join point validation target and recorded validation command or concrete check; accept only when its pass condition holds. If validation metadata is missing, reopen `sp-tasks` rather than inventing the gate during implementation.

### Review Decisions

Record exactly one decision in the current task lifecycle record or a separate review event when multiple tasks are affected:

- `cleared`
- `repair-and-continue`
- `repair-and-rerun-current-window`
- `blocked-reopen-tasks`
- `blocked-reopen-plan`
- `blocked-reopen-clarify`
- `blocked-deep-research`
- `debug-required`

### Safe Repair Boundary

Review may repair the canonical task graph, just-in-time packet, execution state, and current task lifecycle record. Snapshot only artifacts that will actually be rewritten by automatic repair.

Review must not rewrite upstream truth. If a protected requirement, decision, evidence obligation, or boundary is wrong, record the blocker and route to its owning workflow.

### Task Lifecycle Record

Maintain one agent-only record per executed task containing only:

- task id and canonical task ref;
- packet ref for delegated work, or `leader-direct`;
- result and changed paths;
- validation evidence;
- review trigger and verdict when review ran;
- blockers, recovery action, and stop/reopen condition when not accepted.

Do not create separate task briefs, review packages, or a duplicate task ledger. A human-readable view may be rendered on demand but is not handoff truth.

### Task Identity And Completion

- Completed task IDs are immutable.
- Incomplete task IDs stay stable when their objective is unchanged.
- New repair tasks append after the highest existing ID and reference the task they repair or refine.
- A checked task remains a claim until result, validation, and any triggered review evidence are accepted.
- Before final closeout, reconcile actual changed paths, acceptance coverage, unresolved obligations, and required validation. Run a broad diff review only when a review trigger fired or the changed surface is high risk.

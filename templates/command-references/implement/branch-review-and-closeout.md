Trigger: before choosing a ready task, after an execution result, or before final completion.

Purpose: execute the canonical task graph efficiently while preserving live evidence, recovery, review, and truthful closeout.

Preserved Contract: implementation is task-driven, uses validated packets for delegated work, preserves protected obligations, and cannot claim completion without real verification.

## Execution Loop

1. Resolve the active feature lane/worktree and resume execution state.
2. Read canonical `task-index.json` or the light leader-direct task list, then select the smallest ready task/batch whose dependencies are satisfied.
3. Reuse the task graph's context capsule and required refs. Inspect live source for the current task. Run project cognition only when a selected ref is stale, missing, or the live repository contradicts the task-shaping evidence.
4. Choose execution mode:
   - `leader-direct` for compact, tightly coupled, low-risk work;
   - one delegated lane when a validated current packet has clear benefit;
   - parallel delegated lanes only for isolated write sets and explicit join points.
5. For delegated work, compile and validate a WorkerTaskPacket just in time from the current task, live code, and stable contract refs. Never dispatch raw task text.
6. Establish the required RED/repro baseline for behavior change, implement within scope, run task verification, and record the result.
7. Run event-triggered review when repository/task drift, parallel join, write-scope drift, validation failure, worker concern, obligation conflict, real-entrypoint gap, or review-window threshold requires it.
8. Update one task lifecycle record, execution state, and canonical task status. Continue automatically until complete or genuinely blocked.

## Minimum-Sufficient Packet And Result

Delegated packets contain objective, authoritative refs, bounded read/write scope, forbidden drift, validation, done condition, task-relevant `MP-*`/`CA-###`, consumer evidence, and recovery. Do not copy global policies or unrelated obligations.

Worker results contain status, changed paths, validation results, task-relevant obligation evidence, concerns, and recovery when failed/blocked. The leader validates results before acceptance.

## Obligation And Boundary Integrity

- Preserve task-relevant `MP-*` and `CA-###` IDs through packet, result, review, and closeout.
- If live evidence contradicts a protected requirement, architecture, target boundary, or user decision, stop and route to the owning upstream phase.
- If only task metadata is stale, repair the task graph and regenerate the current packet.
- Require real-entrypoint consumer evidence when the task creates or changes routes, registries, providers, factories, handlers, UI entry points, or reusable integration surfaces.

## Blocker Recovery

Agent-owned technical blockers receive bounded diagnosis and safe retries. Do not retry unchanged failures. Escalate unknown root cause to `{{invoke:debug}}`; route requirement/design/task truth defects to their owning phase.

Every terminal blocker records code/cause, owner, exact next action, evidence ref, unblock criteria, whether other tasks may continue, retry guidance, and stop condition.

## Final Reconciliation And Closeout

Before completion:

- reconcile task graph, execution state, lifecycle records, worker results, and actual changed paths;
- verify every acceptance criterion and open `MP-*`/`CA-###` obligation;
- run required focused and broader validation based on changed surfaces;
- confirm real-entrypoint evidence and no unresolved blocker/open gap;
- perform a broad diff review only when a review trigger fired or the changed surface is high risk; otherwise reuse accepted task validation and lifecycle evidence;
- for UI work, compare the real entry point with `DESIGN.md`/fidelity refs using Playwright screenshots or representative output as applicable; distinguish tests passed from visual/interaction acceptance;
- run `{{specify-subcmd:implement closeout --feature-dir "$FEATURE_DIR" --format json}}` when available;
- update project cognition once from final changed paths and verification evidence when project truth changed.

Write `implementation-summary.md` for project/human value. Keep agent-only lifecycle and transition fields out of the visible reply unless diagnostics are requested.

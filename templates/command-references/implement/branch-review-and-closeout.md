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
6. Establish one change-set RED/repro baseline when required, implement within
   scope, run only cheap task checks per Txx, and record test impact for the next
   Leader-owned validation gate attempt.
7. Run event-triggered review when repository/task drift, parallel join, write-scope drift, validation failure, worker concern, obligation conflict, real-entrypoint gap, or review-window threshold requires it.
8. Update one task lifecycle record, execution state, and canonical task status. Continue automatically until complete or genuinely blocked.

## Minimum-Sufficient Packet And Result

Delegated packets contain objective, authoritative refs, bounded read/write scope, forbidden drift, validation, done condition, task-relevant `MP-*`/`CA-###`, consumer evidence, and recovery. Do not copy global policies or unrelated obligations.

Worker results contain status, changed paths, cheap task checks, test impact,
task-relevant obligation evidence, concerns, and recovery when failed/blocked.
The leader validates results and may advance dependency-safe work, but records
feature verification as pending; a worker result never consumes or approves a
heavyweight gate attempt.

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
- reconcile the validation ledger shared across Implement and Review,
  including each source fingerprint, result, covered Txx ids, and remaining
  attempt history; the combined workflow allows at most three logical gates;
- run required focused and broader validation once for the integrated change-set
  in the next Leader-owned attempt rather than once per Txx;
- confirm real-entrypoint evidence and no unresolved blocker/open gap;
- perform a broad diff review only when a review trigger fired or the changed surface is high risk; otherwise reuse accepted task validation and lifecycle evidence;
- for UI work, run a visual convergence loop in a coordinated integrated attempt
  rather than per microtask: open the real entry point once per applicable
  surface/fingerprint, capture the required viewport/state matrix,
  inspect it against `DESIGN.md`, `ui-brief.md`, and original fidelity refs,
  repair observable drift, and recapture. Use Playwright screenshots or
  representative output as applicable; check overflow, browser
  console, keyboard/focus, and accessibility when triggered; distinguish tests passed from visual/interaction acceptance;
- task lifecycles preserve UI contract coverage and reference the shared attempt;
  persist typed evidence with `evidence_scope: integrated`. Do not run the full
  viewport/state capture loop per Txx. `pending-human-review` blocks verified
  closeout;
- run `{{specify-subcmd:implement closeout --feature-dir "$FEATURE_DIR" --format json}}` when available;
- update project cognition once from final changed paths and verification evidence when project truth changed.

Write `implementation-handoff.json` for the mandatory system Review. Derive it deterministically from accepted lifecycle evidence, actual changed paths, the implementation fingerprint/source revision, official real entrypoints with ready signals, and required system-review scenarios. Validate it against the live Spec, Plan, and Tasks and preserve their exact complete `acceptance_refs` denominator, `acceptance_denominator_sha256`, and frozen Human Acceptance Universe (`human_acceptance_obligations`, `human_acceptance_scenarios`, and `human_acceptance_contract_sha256`) unchanged. Never omit an item, downgrade `required`, or reconstruct the frozen contract from prose. Each Review scenario carries stable acceptance refs, preconditions, actions, observable expected results, and evidence kinds. Keep agent-only lifecycle details by reference instead of reconstructing them in prose.

Carry the validation ledger, logical gates, and attempt history into that
handoff without resetting it. Review owns the delivery gate. Interrupted
attempts may retry inside their gate; never open a fourth logical gate.

Implement does not own runtime identity for human acceptance. Do not create, infer, or prefill `reviewed_runtime_targets`; only `sp-review` creates immutable reviewed targets after the final integrated restart, evidence capture, and snapshot validation.

Successful implementation closeout reports task execution as complete but integrated product Review as pending, recommends `{{invoke:review}}`, and stops. Do not run system Review or human acceptance inside `sp-implement`. `sp-review` owns real-entrypoint startup, user-journey and wiring proof, bounded repair, final implementation summary, and acceptance preparation; `sp-accept` later owns the human verdict.

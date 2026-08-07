Trigger: before dispatching implementation work or accepting a worker result.

Purpose: preserve orchestration, worker packet, native subagent, and structured handoff requirements.

Preserved Contract: choose the lightest safe execution surface; delegated lanes are bounded, packetized just in time, return structured results, and remain subordinate to leader-owned execution state.

## Orchestration Model

Every `sp-implement` run uses `execution_model: adaptive`.

### Leader Responsibilities

You are the workflow leader. You own routing, execution-state truth, acceptance, and recovery whether work is leader-direct or delegated.

- Call `specify-runtime implement task-next` for the canonical ready task and compact execution state; query only its additional required refs through `specify-runtime artifact show`.
- Use `leader-direct` for a small or tightly coupled ready task when delegation would add more coordination than execution value and no high-risk trigger requires an independent lane.
- Use `one-subagent` for one independent bounded task, for dependent ready tasks, or when selected tasks share write scope (serial packets / resume worker).
- Use `parallel-subagents` only for multiple validated lanes with isolated write sets and an explicit join point.
- Use `managed-team` only when the runtime supports it and durable team state, explicit multi-wave join tracking, or lifecycle control is required beyond an in-session subagent burst. It is not an ordinary dispatch fallback.
- Compile and validate a `WorkerTaskPacket` just in time only for delegated work. Leader-direct tasks do not require a packet.
- Use `native-subagents` when selected and available. Re-evaluate the route after drift, failure, or each join instead of treating dispatch preference as a blocker by itself.
- Treat non-empty `$ARGUMENTS` as first-class implementation context, not disposable chat-only guidance

Route in this order: `leader-direct` when it independently qualifies, then `one-subagent` (including write-overlapping serial tasks), then `parallel-subagents` for isolated lanes, or `managed-team` when durable coordination is required. Use `subagent-blocked` only when selected delegated work cannot be made safe and the task does not independently qualify for leader-direct execution.

**Write-scope conflict ≠ leader-direct.** Rejecting parallel dispatch because two tasks touch the same files only forbids `parallel-subagents`. Prefer serial `one-subagent` for those tasks. Do not implement them leader-direct solely because they share a write set, unless each task independently qualifies for leader-direct and that choice is recorded in lifecycle/state.

### Delegated Lane Contract

When delegation is selected, the leader compiles the current packet with `specify-runtime implement packet-compile`, dispatches, waits for the structured result, integrates it, validates the join, and merges it through `specify-runtime implement result-merge` into the same lifecycle.

- Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format
- If the lane is shaped by a PNG, screenshot, mockup, design export, reference image, or UI reference page, the packet must carry the original visual input through stable fidelity refs or a runtime image item/local_image. A leader-authored prose summary is not a substitute.
- If the original visual input exists only in the current conversation, attach it directly to the worker when runtime image payloads are supported; otherwise import the runtime-provided local attachment through `specify-runtime evidence import --file <local-path> --scope ui-reference --source chat-attachment --provenance user-provided` and pass the returned content-addressed `object_ref` plus evidence record. Never copy or materialize a project file directly.
- Use `dispatch_shape: one-subagent | parallel-subagents`
- **HARD RULE**: dispatch only from validated `WorkerTaskPacket` — never from raw task text alone
- If a task packet contains `must_preserve_obligations`, the worker must preserve those `MP-*` items or return a blocked result with the exact stop-and-reopen condition.
- Do not dispatch a packet that drops a task-relevant `MP-*` or `CA-###` ref from the canonical task and plan contracts.
- A successful worker result must include `must_preserve_evidence` for every packet obligation that affects acceptance, references, forbidden drift, or conflict/reopen conditions.
- Packets project only cheap `task_checks` into worker `validation_gates` or
  `verify_commands`. Canonical task-index `verification` and
  `required_validation` remain inputs to the Leader-owned gate attempt. Workers return
  test impact: changed behavior, affected test targets, required heavy gates,
  and expected regression scope. They must not run a test suite, full build,
  service startup, E2E flow, or browser/viewport capture per Txx. The Leader
  alone owns the shared logical gate, validation attempt, and source fingerprint.
- If implementation discovers a conflict with an `MP-*` obligation, stop and return a blocked result; do not silently rewrite the product goal, non-goal, selected decision, or reference obligation.
- [AGENT] The leader must wait for and consume the structured handoff before closing the join point, declaring completion, requesting shutdown, or interrupting subagent execution
- Idle subagent is not an accepted result
- Treat `DONE_WITH_CONCERNS` as completed work plus follow-up concerns, not as silent success
- Treat `NEEDS_CONTEXT` as a blocked handoff that must carry the missing context or failed assumption explicitly

Accept a delegated lane only through a `WorkerTaskResult`-compatible payload containing task ID, status, changed paths, cheap task-check results, test impact, task-relevant obligation evidence, concerns, and blocker/recovery metadata when applicable. Pass it inline to `specify-runtime implement result-merge --result-json`; do not create a result file or a second ledger. A successful implementation result proves the bounded edit only and may advance dependency-safe work; feature verification remains pending instead of duplicating the Leader's heavyweight evidence.

A `success` result must already be task-acceptance-ready: every canonical
`task_checks` entry appears exactly as a passed validation command, every
validation row is passed, and blockers are empty. Record known downstream work
as a separate task, an approved deferral, or a blocked result with recovery;
never encode it as a failed validation row inside a current-task `success`.

Cheap producer-to-consumer wiring evidence remains task-local and required when
the packet names a consumer surface. Only runtime real-entrypoint proof is
deferred to the Leader-owned attempt; do not defer a static "created but not
wired" check merely because `mode: feature_epochs` is active.

### Autonomous Blocker Recovery

If technical blockers arise (build errors, missing toolchain components, environment mismatches), you **MUST** attempt autonomous escalation to a specialist subagent **BEFORE** asking the user for intervention.

- Only stop and ask the user if the specialist lane confirms that manual human action is the ONLY remaining path

### Integrity Rules

- The leader must not edit a delegated lane's write scope while that subagent is active.
- Do not silently fall through from a failed dispatch or a parallel write-scope conflict into local execution. Record the event, re-evaluate route safety, prefer serial `one-subagent`, and use leader-direct only when the task independently qualifies for it with a recorded reason.
- Do not dispatch a subagent when required packet fields or required references are missing — repair the packet first or stop as `subagent-blocked`
- Do not dispatch image-backed UI implementation when the worker cannot inspect the original visual input and the task depends on fidelity. Repair the packet/handoff first, or stop as `subagent-blocked` with the missing image handoff reason.
- Do not bypass lifecycle truth, result handoffs, or verification gates.
- Do not let a worker, passive skill, task transition, join, or resume open an
  extra logical gate. The ledger has three logical gates shared across Implement
  and Review; physical retries remain attempts inside the owning gate. Workers
  never open attempts.
- Do not declare completion because tasks look checked off if the implementation contract is not actually satisfied

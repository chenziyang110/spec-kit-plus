Trigger: before dispatching implementation work or accepting a worker result.

Purpose: preserve orchestration, worker packet, native subagent, and structured handoff requirements.

Preserved Contract: choose the lightest safe execution surface; delegated lanes are bounded, packetized just in time, return structured results, and remain subordinate to leader-owned execution state.

## Orchestration Model

Every `sp-implement` run uses `execution_model: adaptive`.

### Leader Responsibilities

You are the workflow leader. You own routing, execution-state truth, acceptance, and recovery whether work is leader-direct or delegated.

- Read canonical `task-index.json` or the light direct task list, compact execution state, and only the current task's required refs.
- Use `leader-direct` for a small or tightly coupled ready task when delegation would add more coordination than execution value and no high-risk trigger requires an independent lane.
- Use `one-subagent` for one independent bounded task; use `parallel-subagents` only for multiple validated lanes with isolated write sets and an explicit join point.
- Use `managed-team` only when the runtime supports it and durable team state, explicit multi-wave join tracking, or lifecycle control is required beyond an in-session subagent burst. It is not an ordinary dispatch fallback.
- Compile and validate a `WorkerTaskPacket` just in time only for delegated work. Leader-direct tasks do not require a packet.
- Use `native-subagents` when selected and available. Re-evaluate the route after drift, failure, or each join instead of treating dispatch preference as a blocker by itself.
- Treat non-empty `$ARGUMENTS` as first-class implementation context, not disposable chat-only guidance

Route in this order: `leader-direct` when it independently qualifies, then `one-subagent`, `parallel-subagents`, or `managed-team` as their coordination value and state requirements justify. Use `subagent-blocked` only when selected delegated work cannot be made safe and the task does not independently qualify for leader-direct execution.

### Delegated Lane Contract

When delegation is selected, the leader compiles the current packet, dispatches, waits for the structured result, integrates it, validates the join, and updates the same task lifecycle record.

- Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format
- If the lane is shaped by a PNG, screenshot, mockup, design export, reference image, or UI reference page, the packet must carry the original visual input through stable fidelity refs or a runtime image item/local_image. A leader-authored prose summary is not a substitute.
- If the original visual input exists only in the current conversation, materialize it to a stable project-relative artifact path or attach it directly to the worker when the runtime supports image payloads before dispatch.
- Use `dispatch_shape: one-subagent | parallel-subagents`
- **HARD RULE**: dispatch only from validated `WorkerTaskPacket` — never from raw task text alone
- If a task packet contains `must_preserve_obligations`, the worker must preserve those `MP-*` items or return a blocked result with the exact stop-and-reopen condition.
- Do not dispatch a packet that drops a task-relevant `MP-*` or `CA-###` ref from the canonical task and plan contracts.
- A successful worker result must include `must_preserve_evidence` for every packet obligation that affects acceptance, references, forbidden drift, or conflict/reopen conditions.
- If implementation discovers a conflict with an `MP-*` obligation, stop and return a blocked result; do not silently rewrite the product goal, non-goal, selected decision, or reference obligation.
- [AGENT] The leader must wait for and consume the structured handoff before closing the join point, declaring completion, requesting shutdown, or interrupting subagent execution
- Idle subagent is not an accepted result
- Treat `DONE_WITH_CONCERNS` as completed work plus follow-up concerns, not as silent success
- Treat `NEEDS_CONTEXT` as a blocked handoff that must carry the missing context or failed assumption explicitly

Accept a delegated lane only through a `WorkerTaskResult`-compatible payload containing task ID, status, changed paths, validation results, task-relevant obligation evidence, concerns, and blocker/recovery metadata when applicable. Merge that payload into the existing task lifecycle record; do not create a second result ledger.

### Autonomous Blocker Recovery

If technical blockers arise (build errors, missing toolchain components, environment mismatches), you **MUST** attempt autonomous escalation to a specialist subagent **BEFORE** asking the user for intervention.

- Only stop and ask the user if the specialist lane confirms that manual human action is the ONLY remaining path

### Integrity Rules

- The leader must not edit a delegated lane's write scope while that subagent is active.
- Do not silently fall through from a failed dispatch into local execution. Record the event, re-evaluate route safety, and use leader-direct only when the task independently qualifies for it.
- Do not dispatch a subagent when required packet fields or required references are missing — repair the packet first or stop as `subagent-blocked`
- Do not dispatch image-backed UI implementation when the worker cannot inspect the original visual input and the task depends on fidelity. Repair the packet/handoff first, or stop as `subagent-blocked` with the missing image handoff reason.
- Do not bypass lifecycle truth, result handoffs, or verification gates.
- Do not declare completion because tasks look checked off if the implementation contract is not actually satisfied

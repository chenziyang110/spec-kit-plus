Trigger: before dispatching implementation work or accepting a worker result.

Purpose: preserve orchestration, worker packet, native subagent, and structured handoff requirements.

Preserved Contract: worker lanes must be bounded, return structured results, and remain subordinate to leader-owned tracker state.

## Orchestration Model

This section is **mandatory**. Every `sp-implement` run MUST follow this model — deviation is not permitted.

### Leader Responsibilities

You are the workflow **leader and orchestrator** for this run, not the concrete implementer.

- Own routing, task splitting, task contracts, dispatch, join points, integration, verification, and state updates
- Subagents own the substantive task lanes assigned through task contracts
- Recover context, choose the current ready batch, integrate structured handoffs, keep `implement-tracker.md` accurate, and own final validation
- The leader owns sequencing, review, and acceptance.
- Use `execution_model: subagent-mandatory` for ready implementation batches
- Dispatch `one-subagent` when one validated `WorkerTaskPacket` is ready; dispatch `parallel-subagents` when multiple validated packets have isolated write sets
- Use `execution_surface: native-subagents`
- If the subagent-readiness bar is not met, compile the missing context, hard rules, validation gates, or handoff requirements before dispatch
- Treat non-empty `$ARGUMENTS` as first-class implementation context, not disposable chat-only guidance

### Subagent Mandate

All substantive implementation work defaults to and MUST use subagents. Substantive implementation lanes must be delegated. The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

- Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format
- Use `dispatch_shape: one-subagent | parallel-subagents`
- **HARD RULE**: dispatch only from validated `WorkerTaskPacket` — never from raw task text alone
- If a task packet contains `must_preserve_obligations`, the worker must preserve those `MP-*` items or return a blocked result with the exact stop-and-reopen condition.
- Do not dispatch a packet that drops a discussion-derived `MP-*` obligation from `tasks.md`, `plan.md`, or `brainstorming/handoff-to-specify.json`.
- A successful worker result must include `must_preserve_evidence` for every packet obligation that affects acceptance, references, forbidden drift, or conflict/reopen conditions.
- If implementation discovers a conflict with an `MP-*` obligation, stop and return a blocked result; do not silently rewrite the product goal, non-goal, selected decision, or reference obligation.
- [AGENT] The leader must wait for and consume the structured handoff before closing the join point, declaring completion, requesting shutdown, or interrupting subagent execution
- Idle subagent is not an accepted result
- Treat `DONE_WITH_CONCERNS` as completed work plus follow-up concerns, not as silent success
- Treat `NEEDS_CONTEXT` as a blocked handoff that must carry the missing context or failed assumption explicitly

### Autonomous Blocker Recovery (Hard Rule)

If technical blockers arise (build errors, missing toolchain components, environment mismatches), you **MUST** attempt autonomous escalation to a specialist subagent **BEFORE** asking the user for intervention.

- Only stop and ask the user if the specialist lane confirms that manual human action is the ONLY remaining path

### Integrity Rules

- **Hard rule:** The leader must not edit implementation files directly while subagent execution is active
- Do **not** fall through from subagent dispatch into local self-execution just because the implementation looks feasible
- Do not dispatch a subagent when required packet fields or required references are missing — repair the packet first or stop as `subagent-blocked`
- Do not bypass tracker truth, result handoffs, or verification gates
- Do not declare completion because tasks look checked off if the implementation contract is not actually satisfied

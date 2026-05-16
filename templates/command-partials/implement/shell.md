{{spec-kit-include: ../common/user-input.md}}

## Objective

Advance the current feature through tracked implementation batches while keeping execution state, subagent work, verification evidence, and recovery paths explicit.

## Context

- Primary inputs: `tasks.md`, the plan package, `implement-tracker.md`, worker-result handoff files, passive learning files, the task-local project cognition query bundle with readiness and returned `minimal_live_reads`, and the smallest workflow-local state files needed for the touched area.
- The leader owns tracker truth, execution strategy, join points, blocker handling, and final validation.
- Delegated workers own bounded implementation lanes only; they do not own the overall implementation state.

## Process

- Recover tracker state and identify the current ready batch.
- On resume, audit terminal-looking tracker/task state before trusting completion; checked tasks are claims until validation, handoff, join point, and consumer evidence prove them.
- Carry every `CA-###` consequence obligation from packets into dispatch, implementation evidence, result acceptance, tracker open gaps, and stop-and-reopen routing.
- Choose the execution strategy and dispatch subagents or a documented fallback path.
- Integrate structured handoffs, update tracker truth, and keep verification evidence current.
- Continue automatically until the feature is complete or blocked by a real blocker.

## Output Contract

- Produce verified implementation changes plus updated execution-state artifacts for the active feature.
- Keep `implement-tracker.md` and worker-result handoffs aligned with what actually happened.
- Report blockers, retries, and completion honestly rather than inferring success from partial progress.
- Preserve any `MP-*` obligations carried in task packets, implementation state, or result handoff expectations.
- Worker result handoffs must include must-preserve evidence when packet obligations require it.
- If implementation discovers a conflict with an `MP-*` obligation, return a blocked result instead of silently changing the protected discussion decision.

## Guardrails

- Do not dispatch from raw task text alone; compile and validate the packet first.
- Do not bypass tracker truth, result handoffs, or verification gates.
- Do not declare completion because tasks look checked off if the implementation contract is not actually satisfied.

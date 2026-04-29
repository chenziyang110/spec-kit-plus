{{spec-kit-include: ../common/user-input.md}}

## Objective

Advance the current feature through tracked implementation batches while keeping execution state, subagent work, verification evidence, and recovery paths explicit.

## Context

- Primary inputs: `tasks.md`, the plan package, `implement-tracker.md`, worker-result handoff files, passive learning files, and the handbook/project-map set.
- The leader owns tracker truth, execution strategy, join points, blocker handling, and final validation.
- Delegated workers own bounded implementation lanes only; they do not own the overall implementation state.

## Process

- Recover tracker state and identify the current ready batch.
- Choose the execution strategy and dispatch subagents or a documented fallback path.
- Integrate structured handoffs, update tracker truth, and keep verification evidence current.
- Continue automatically until the feature is complete or blocked by a real blocker.

## Output Contract

- Produce verified implementation changes plus updated execution-state artifacts for the active feature.
- Keep `implement-tracker.md` and worker-result handoffs aligned with what actually happened.
- Report blockers, retries, and completion honestly rather than inferring success from partial progress.

## Guardrails

- Do not dispatch from raw task text alone; compile and validate the packet first.
- Do not bypass tracker truth, result handoffs, or verification gates.
- Do not declare completion because tasks look checked off if the implementation contract is not actually satisfied.

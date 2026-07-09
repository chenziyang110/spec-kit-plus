---
description: Use when tasks.md exists and the planned work should be executed through the tracked implementation workflow.
workflow_contract:
  when_to_use: '`tasks.md` is ready and the feature should move from planning into tracked execution batches.'
  primary_objective: Execute the ready batches while preserving tracker state, subagent contracts, verification discipline, and resumability.
  primary_outputs: Verified code, test, and documentation changes plus implementation-tracker, subagent-result artifacts, and `implementation-summary.md` for the active feature.
  default_handoff: Continue with the next ready batch, route blockers into /sp-debug, or report completion only when the implementation contract is actually satisfied.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

{{spec-kit-include: ../command-partials/implement/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

## Main Flow

1. Read `tasks.md`, task packets, tracker state, and current branch/worktree status; implementation is task-only and must not invent work outside the accepted task package.
2. Run the Embedded Implement Review Loop and establish RED-first validation before code changes; do not claim completion from chat narration.
3. Use `choose_subagent_dispatch(command_name="implement", snapshot, workload_shape)` for safe worker lanes, use the current integration's native subagent lifecycle where available, and keep leader ownership of tracker state.
4. Execute the current task or ready batch, update tracker fields, resolve blockers through bounded repair, and route unknown root cause to `{{invoke:debug}}`.
5. Validate, review join points, repair rejected work, and report completion only when changed paths, validation evidence, review status, and mutation closeout are complete.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [task intake and tracker](references/task-intake-and-tracker.md)
- [red first and validation](references/red-first-and-validation.md)
- [subagent worker contract](references/subagent-worker-contract.md)
- [join point review](references/join-point-review.md)
- [safe repair loop](references/safe-repair-loop.md)
- [branch review and closeout](references/branch-review-and-closeout.md)

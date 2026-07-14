---
description: Use when tasks.md exists and the planned work should be executed through the tracked implementation workflow.
workflow_contract:
  when_to_use: '`tasks.md` is ready and the feature should move from planning into tracked execution batches.'
  primary_objective: Execute the ready batches while preserving tracker state, subagent contracts, verification discipline, and resumability.
  primary_outputs: Verified code, test, and documentation changes plus compact execution state, one task lifecycle record per executed task, conditional drift/repair records, and `implementation-summary.md` for the active feature.
  default_handoff: Continue with the next ready batch, route blockers into /sp-debug, or report completion only when the implementation contract is actually satisfied.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

{{spec-kit-include: ../command-partials/implement/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

## Main Flow

1. Run `{SCRIPT}` to resolve the task-bearing feature context, then read canonical `task-index.json` or the light leader-direct task list, compact execution state, and current branch/worktree status. Load the current task plus its required refs; do not ingest the full upstream package when revisions are unchanged.
2. Validate the task-graph revision and current ready batch. Compile delegated WorkerTaskPackets just in time from live code, establish RED-first validation for behavior changes, and do not claim completion from chat narration.
3. Use `choose_subagent_dispatch(command_name="implement", snapshot, workload_shape)` for safe worker lanes, use the current integration's native subagent lifecycle where available, and keep leader ownership of tracker state.
4. Execute the current task or ready batch, update tracker fields, resolve blockers through bounded repair, and route unknown root cause to `{{invoke:debug}}`.
5. Run event-triggered review for repository drift, parallel joins, write-scope drift, validation failure, worker concerns, obligation conflicts, or sequential change-window limits. Maintain one task lifecycle record containing packet/ref, result, validation, review verdict, and recovery; report completion only when changed paths, validation evidence, review status, and mutation closeout are complete.
6. For UI work, record task-lifecycle `ui_verification` with concrete evidence
   refs after the real-entrypoint visual convergence loop. Set
   `evidence_scope: task` and persist typed `structure_snapshot`,
   `visual_capture`, and `runtime_diagnostics` evidence plus passing runtime
   status. Use
   `pending-human-review` only when objective visual evidence cannot close the
   criterion; it blocks accepted closeout until resolved. Route an invalid,
   bootstrap, or missing design source to `sp-design` instead of inventing one.

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [task intake and tracker](references/task-intake-and-tracker.md)
- [red first and validation](references/red-first-and-validation.md)
- [subagent worker contract](references/subagent-worker-contract.md)
- [join point review](references/join-point-review.md)
- [safe repair loop](references/safe-repair-loop.md)
- [final reconciliation and closeout](references/branch-review-and-closeout.md)

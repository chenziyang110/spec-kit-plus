---
description: Use when tasks.md exists and the planned work should be executed through the tracked implementation workflow.
workflow_contract:
  when_to_use: '`tasks.md` is ready and the feature should move from planning into tracked execution batches.'
  primary_objective: Execute the ready batches while preserving tracker state, subagent contracts, verification discipline, and resumability.
  primary_outputs: Verified code, test, and documentation changes plus compact execution state, one task lifecycle record per executed task, conditional drift/repair records, and `implementation-handoff.json` for mandatory system review.
  default_handoff: Continue with the next ready batch, route blockers into /sp-debug, or after technical closeout hand the integrated product to /sp.review and stop.
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
2. Validate the task-graph revision and current ready batch. Compile delegated WorkerTaskPackets just in time from live code. Group behavior-changing Txx items into one coherent change-set, establish its RED/baseline through the Leader-owned validation-epoch contract, and do not claim completion from chat narration.
3. Use `choose_subagent_dispatch(command_name="implement", snapshot, workload_shape)` for safe worker lanes, use the current integration's native subagent lifecycle where available, and keep leader ownership of tracker state.
4. Execute the current task or ready batch, update tracker fields, resolve blockers through bounded repair, and route unknown root cause to `{{invoke:debug}}`.
5. Run event-triggered review for repository drift, parallel joins, write-scope drift, validation failure, worker concerns, obligation conflicts, or sequential change-window limits. Maintain one task lifecycle record containing packet/ref, result, cheap task checks, shared validation-epoch refs, review verdict, and recovery; report completion only when changed paths, validation evidence, review status, and mutation closeout are complete.
6. Persist one validation-epoch ledger shared across Implement and Review. The
   combined workflow permits at most three heavyweight epochs against explicit
   source fingerprints: an optional change-set RED/baseline, Implement
   convergence, and integrated Review/final revalidation. A failed epoch may be
   repaired only when a later epoch remains; the third failed epoch blocks, and
   no agent may reset the ledger or ever start a fourth. Per-Txx workers run only
   cheap task checks and return test impact; the Leader owns every heavyweight
   test, build, startup, E2E, and real-entrypoint epoch.
7. For UI work, preserve task-local design inputs, states, changed surfaces, and
   capture requirements, but do not run the full viewport/state capture loop per
   Txx. Group the matrix by integrated surface and capture typed
   `structure_snapshot`, `visual_capture`, and `runtime_diagnostics` evidence
   with `evidence_scope: integrated` in a Leader-owned epoch. Bind the applicable
   shared evidence refs into each task lifecycle's `ui_verification`; this is
   evidence reuse, not permission to recapture or rerun the matrix per task. Unavailable
   objective comparison remains `pending-human-review`, never an implicit pass.
   Route an invalid, bootstrap, or missing design source to `sp-design` instead
   of inventing one.
8. After successful technical closeout, require the `implementation_summary` and `implementation_handoff` response fields for the preliminary `implementation-summary.md` and deterministic `implementation-handoff.json`, including the unchanged validation-epoch ledger and remaining budget. The summary must explain what changed, how to verify it, and what differs from the previous version using the recorded `git diff --stat` and `git diff --name-status` baseline. Complete only the `implement` stage, recommend `{{invoke:review}}`, and stop. The embedded event-triggered task review remains part of implementation, while `sp-review` spends the remaining shared epoch budget to prove startup, user journeys, interaction, and integrated wiring from real entrypoints. Do not invoke Review inline or claim that task completion equals a usable reviewed product.

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [task intake and tracker](references/task-intake-and-tracker.md)
- [red first and validation](references/red-first-and-validation.md)
- [subagent worker contract](references/subagent-worker-contract.md)
- [join point review](references/join-point-review.md)
- [safe repair loop](references/safe-repair-loop.md)
- [final reconciliation and closeout](references/branch-review-and-closeout.md)

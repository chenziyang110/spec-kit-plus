---
description: Use when implementation already fits sp-implement but requires the Codex-only durable team/runtime surface for coordinated team execution.
workflow_contract:
  when_to_use: The work is already ready for `sp-implement`, but you explicitly want the durable teams runtime as the execution backend.
  primary_objective: Execute the same implementation contract through the Codex-only teams surface rather than through a lighter runtime path.
  primary_outputs: The normal implementation lifecycle artifacts plus team-runtime state, worktrees, and leader-visible progress signals.
  default_handoff: Continue coordinated implementation through the teams runtime; use cleanup or recovery only through the internal surfaces named below.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

# Codex Implement Teams

{{spec-kit-include: ../command-partials/implement-teams/shell.md}}

User-facing workflow skill:

```text
sp-implement-teams
```

## Boundary

1. Codex-only
2. Implementation-phase entry point only; use it after the active execution batch is known
3. On Windows, support only `native Windows + psmux`
4. Requires a clean leader workspace for runtime worktrees
5. This is the user-facing surface; use `sp-teams` as the runtime surface and do not teach extension internals as the primary product surface

## When To Use

Use this when:

1. `sp-implement` would otherwise need `leader-inline-fallback` or an ad hoc implementation flow
2. you want the current feature implemented through durable coordinated team lanes
3. the work has already been decomposed into task-ready execution slices

## Execution Contract

1. Run `{SCRIPT}` from repo root and parse `FEATURE_DIR` and `AVAILABLE_DOCS` list. All paths must be absolute.
2. If the prerequisites output does not resolve a `FEATURE_DIR` with `tasks.md`, stop and run `sp-tasks` first instead of guessing from chat state.
3. Confirm the current project is using the Codex integration.
4. Create or resume `FEATURE_DIR/implement-tracker.md`, then recover the active execution batch from tracker state before trusting `tasks.md`.
5. Treat `FEATURE_DIR/implement-tracker.md` as the implementation-state source of truth and treat `FEATURE_DIR/tasks.md` as planning input only.
6. Confirm the native runtime backend is ready through the official `sp-teams` runtime checks.
7. Run `sp-teams doctor` before the first teams dispatch for the current feature so executor availability, latest transcript, failed dispatches, and team-state evidence are visible up front.
8. When the runtime was newly installed, recently repaired, or still looks suspect after `doctor`, run `sp-teams live-probe` before touching the real implementation batch.
9. On Windows, require the same native shell to resolve `psmux`, `codex`, `node`, `npm`, `cargo`, and `git`.
10. Route durable execution through `sp-teams` and its runtime/API surfaces.
11. Preserve the shared `sp-implement` contract: tracker continuity, validated `WorkerTaskPacket`s, explicit join points, and structured result handoff discipline.
12. If the current feature already has an active runtime session, resume or reuse it. Do not create a second runtime team for the same feature.
13. If a create/start call fails because the feature already has an active runtime leader, treat that as a resume signal: inspect the existing session, reconcile tracker/task state, and continue from the recorded ready batch.
14. Use `sp-teams result-template --request-id <id>` or `sp-teams submit-result --print-schema` for structured result handoff instead of ad hoc JSON guessing. Treat the generated template as a `pending` placeholder only; do not submit it unchanged.
15. Materialize each subagent lane as an explicit execution packet: write set, required references, forbidden drift, validation command, completion-handoff protocol, and platform guardrails must stay visible to the leader and subagent.
16. Treat a blocked baseline build as a pre-dispatch runtime concern; do not mix existing repo compile debt into the current batch verdict.
17. After managed team execution, use `sp-teams sync-back` when leader-visible results need to be promoted from runtime worktrees back into the active workspace.
18. Distinguish lane-local completion from repo-global verification: `DONE_WITH_CONCERNS` means the lane finished with follow-up concerns, while repo-wide failure may still be caused by baseline debt.
19. Every join point that gates downstream work must have an explicit validation target, validation command or check, and pass condition before the runtime crosses it.
20. After each completed join point or ready batch, re-read the tracker and task state, select the next ready batch and continue automatically. Stop only when no ready work remains, a real blocker stops progress, or an explicit human gate is reached.
21. Planned validation tasks are still ready work. If the remaining tasks are executable tests, E2E checks, security verification, quickstart validation, or other scripted validation work already present in `tasks.md`, continue automatically instead of asking whether validation should start.
22. Do not stop to ask whether validation should start unless a manual-only check or approval step is explicitly recorded in the tracker or task plan.
23. Do not stop after a single completed batch just because the current assignee, subagent, or runtime lane has gone idle; idle without remaining-work analysis is not a terminal condition.
24. If a lane flips to `completed` or drifts into `idle` before the promised result handoff or completion evidence arrives, treat it as a stale lane and recover explicitly instead of counting it as finished work.
25. Use the teams runtime as the execution backend for the prepared batch rather than as a replacement for the `sp-implement` contract.
26. If the user only wants to inspect the Codex runtime surface before implementing, redirect them to `sp-teams` or `$sp-teams`.

## Output Expectations

Successful runs should leave the user with:

1. canonical team state under `.specify/teams/state`
2. worker worktrees under `.specify/teams/worktrees` or the active runtime worktree root
3. leader-visible progress through the team mailbox and monitor snapshot
4. the same implementation lifecycle semantics as `sp-implement`, including tracker continuity, join point visibility, and result handoff discipline
5. executor diagnostics and latest transcript evidence available through `sp-teams doctor`
6. a repeatable minimal runtime acceptance check available through `sp-teams live-probe`
7. implementation framed as "teams execution" through the official `sp-teams` runtime rather than extension internals
8. a formal structured result template via `sp-teams result-template`
9. an official sync-back path when worker worktrees and the main workspace diverge
10. batch outcome visibility that distinguishes lane-local completion from repo-global verification blockers

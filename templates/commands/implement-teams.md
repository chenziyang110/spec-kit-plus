---
description: Use when implementation already fits sp-implement but requires the Codex-only durable team/runtime surface for coordinated multi-worker execution.
workflow_contract:
  when_to_use: The work is already ready for `sp-implement`, but you explicitly want the durable teams runtime as the execution backend.
  primary_objective: Execute the same implementation contract through the Codex-only teams surface rather than through a lighter runtime path.
  primary_outputs: The normal implementation lifecycle artifacts plus team-runtime state, worktrees, and leader-visible progress signals.
  default_handoff: Continue coordinated implementation through the teams runtime; use cleanup or recovery only through the internal surfaces named below.
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
4. Requires a clean leader workspace for worker worktrees
5. This is the user-facing surface; use `specify team` as the runtime surface and do not teach extension internals as the primary product surface

## When To Use

Use this when:

1. `sp-implement` would otherwise run a single-agent or ad hoc implementation flow
2. you want the current feature implemented through durable coordinated workers
3. the work has already been decomposed into task-ready execution slices

## Execution Contract

1. Confirm the current project is using the Codex integration.
2. Create or resume `FEATURE_DIR/implement-tracker.md`, then recover the active execution batch from tracker state before trusting `tasks.md`.
3. Treat `FEATURE_DIR/implement-tracker.md` as the implementation-state source of truth and treat `tasks.md` as planning input only.
4. Confirm the native runtime backend is ready through the official `specify team` runtime checks.
5. Run `specify team doctor` before the first teams dispatch for the current feature so executor availability, latest transcript, failed dispatches, and team-state evidence are visible up front.
6. When the runtime was newly installed, recently repaired, or still looks suspect after `doctor`, run `specify team live-probe` before touching the real implementation batch.
7. On Windows, require the same native shell to resolve `psmux`, `codex`, `node`, `npm`, `cargo`, and `git`.
8. Route durable execution through `specify team` and its runtime/API surfaces.
9. Preserve the shared `sp-implement` contract: tracker continuity, validated `WorkerTaskPacket`s, explicit join points, and structured result handoff discipline.
10. Use the teams runtime as the execution backend for the prepared batch rather than as a replacement for the `sp-implement` contract.
11. If the user only wants to inspect the Codex runtime surface before implementing, redirect them to `specify team` or `$sp-team`.

## Output Expectations

Successful runs should leave the user with:

1. canonical team state under `.specify/codex-team/state`
2. worker worktrees under `.specify/codex-team/worktrees` or the active runtime worktree root
3. leader-visible progress through the team mailbox and monitor snapshot
4. the same implementation lifecycle semantics as `sp-implement`, including tracker continuity, join point visibility, and result handoff discipline
5. executor diagnostics and latest transcript evidence available through `specify team doctor`
6. a repeatable minimal runtime acceptance check available through `specify team live-probe`
7. implementation framed as "teams execution" through the official `specify team` runtime rather than extension internals

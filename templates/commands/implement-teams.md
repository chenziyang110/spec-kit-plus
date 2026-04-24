---
description: Execute implementation through the Codex-only team/runtime surface when you explicitly want durable multi-worker execution.
---

# Codex Implement Teams

User-facing workflow skill:

```text
sp-implement-teams
```

## Boundary

1. Codex-only
2. Implementation-phase entry point only; use it after `tasks.md` is ready
3. Requires a tmux-capable environment
4. Requires a clean leader workspace for worker worktrees
5. This is the user-facing surface; do not teach `sp.agent-teams.run` as the primary product surface

## When To Use

Use this when:

1. `sp-implement` would otherwise run a single-agent or ad hoc implementation flow
2. you want the current feature implemented through durable coordinated workers
3. the work has already been decomposed into task-ready execution slices

## Execution Contract

1. Confirm the current project is using the Codex integration and that `tasks.md` is ready.
2. Confirm `tmux` is available and the leader workspace is clean enough for worktree-based execution.
3. Check whether the `agent-teams` extension is installed in this project.
4. If the extension is installed, route the implementation run through `sp.agent-teams.run`.
5. Treat `sp.agent-teams.run` as internal plumbing, not the name you teach users.
6. Use the teams runtime as the execution backend for the prepared batch rather than as a replacement for the `sp-implement` contract.
7. If the extension is not installed, stop and tell the user that `sp-implement-teams` requires the `agent-teams` extension, then suggest:

```text
specify extension add agent-teams
```

8. Use `sp.agent-teams.cleanup` only for cleanup or recovery after interrupted runs.
9. If the user only wants to inspect the Codex runtime surface before implementing, redirect them to `specify team` or `$sp-team`.

## Output Expectations

Successful runs should leave the user with:

1. team state under `.specify/agent-teams/state`
2. worker worktrees under `.specify/agent-teams/worktrees`
3. leader-visible progress through the team mailbox and monitor snapshot
4. the same implementation lifecycle semantics as `sp-implement`, including tracker continuity, join point visibility, and result handoff discipline
5. implementation framed as "teams execution" rather than extension internals

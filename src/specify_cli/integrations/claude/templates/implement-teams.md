---
description: Execute implementation through Claude Code Agent Teams when you explicitly want durable multi-worker execution.
---

# Claude Code Agent Teams

User-facing workflow skill:

```text
/sp-implement-teams
```

## Boundary

1. Claude-only
2. Implementation-phase entry point only; use it after `tasks.md` is ready
3. Use Claude Code's built-in Agent Teams surface, not the Codex runtime surface
4. Keep `sp-team` and Codex extension commands out of Claude guidance

## When To Use

Use this when:

1. `/sp-implement` would otherwise run a single-agent or native delegated flow
2. you want durable coordinated execution with a shared task list and explicit teammate messaging
3. the implementation work is already decomposed into task-ready execution slices

## Execution Contract

1. Confirm the current project is using the Claude integration and that `tasks.md` is ready.
2. Create or resume a Claude Agent Team for the feature:

```text
TeamCreate({
  team_name: "<feature-slug>",
  description: "Implementing <feature>",
  agent_type: "researcher"
})
```

3. Treat the team ledger as shared state:
   - team membership lives in `~/.claude/teams/{team-name}/config.json`
   - shared tasks live under `~/.claude/tasks/{team-name}/`
4. Convert the ready implementation slices into explicit shared tasks with `TaskCreate`.
5. Encode dependencies and ownership with `TaskUpdate`:
   - use `blockedBy` / `blocks` for ordering
   - use `owner` to assign each task to a named teammate
6. Create the teammates with `Agent`:
   - use `subagent_type: "Explore"` for read-only analysis or planning lanes
   - use `subagent_type: "general-purpose"` for implementation lanes
   - set `team_name` so every teammate joins the same shared ledger
   - prefer `run_in_background: true` for long-running execution
   - use `isolation: "worktree"` when the lane needs isolated edits
7. Tell every teammate to call `TaskList`, claim or inspect its assigned work, and use `SendMessage` for coordination instead of silent progress.
8. Track progress through the shared task list:
   - `TaskUpdate({ taskId, status: "in_progress" })`
   - `TaskUpdate({ taskId, status: "completed" })`
   - `TaskList()` and `TaskGet(taskId: "...")` to inspect team state
9. Use `SendMessage` for handoffs, blockers, and dependency releases. Approve structured messages such as `shutdown_request` or `plan_approval_request` when they arrive.
10. Keep the same completion discipline as `/sp-implement`: do not cross the join point or declare completion until structured handoffs are consumed and the tracker/result state is updated.
11. When implementation is done, request shutdown for each teammate, then clean up the team with `TeamDelete()`.

## Output Expectations

Successful runs should leave the user with:

1. a Claude-native team config under `~/.claude/teams/{team-name}/config.json`
2. a shared task ledger under `~/.claude/tasks/{team-name}/`
3. explicit teammate ownership, status transitions, and dependency tracking
4. the same implementation lifecycle semantics as `/sp-implement`, including tracker continuity, join point visibility, and result handoff discipline
5. implementation framed as Claude Code Agent Teams execution, not as Codex runtime or extension plumbing

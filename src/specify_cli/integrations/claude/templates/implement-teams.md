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
2. Confirm Claude Agent Teams is actually enabled before you try to use it:
   - check whether `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is active in the current shell environment or configured under `env` in `~/.claude/settings.json`
   - if the Agent Teams surface is unavailable, or if the first `TeamCreate` / Agent Teams call fails as though the feature is disabled, stop and explicitly remind the user to enable `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` instead of continuing with a broken team setup
   - treat this as a hard prerequisite for `/sp-implement-teams`, not as an optional hint
3. Create or resume a Claude Agent Team for the feature:

```text
TeamCreate({
  team_name: "<feature-slug>",
  description: "Implementing <feature>",
  agent_type: "researcher"
})
```

4. Treat the team ledger as shared state:
   - team membership lives in `~/.claude/teams/{team-name}/config.json`
   - shared tasks live under `~/.claude/tasks/{team-name}/`
5. Convert the ready implementation slices into explicit shared tasks with `TaskCreate`.
6. Encode dependencies and ownership with `TaskUpdate`:
   - use `blockedBy` / `blocks` for ordering
   - use `owner` to assign each task to a named teammate
7. Resolve the current session model before teammate creation:
   - inspect the highest-confidence source first: any runtime-visible active model, then `ANTHROPIC_MODEL` / `CLAUDE_MODEL`, then `~/.claude/settings.json` `model`
   - treat the resolved current-session model string as the default teammate target model for this run unless there is explicit evidence that the lane needs a different class
   - if the current session model cannot be resolved unambiguously, stop and surface the ambiguity instead of silently inventing a teammate model
8. Materialize explicit teammate agent definitions before you create teammates:
   - create or update local `.claude/agents/<team-name>-<role>.md` files for every teammate you intend to launch
   - write the resolved current-session model into the teammate frontmatter as `model: "<resolved-current-model>"`
   - keep the teammate role description in that file so model choice and teammate identity live in one source of truth instead of being split across chat and ad hoc spawn parameters
   - when a pre-existing teammate definition already exists, update its `model` field for the current run instead of assuming stale frontmatter still matches the active session model
9. Create the teammates from those agent definitions:
   - reference the generated teammate definition name instead of relying on prompt-only specialization when the current Claude build supports custom teammate definitions in Agent Teams
   - use read-only style teammate definitions for analysis or planning lanes and implementation-oriented teammate definitions for write lanes
   - set `team_name` so every teammate joins the same shared ledger
   - prefer `run_in_background: true` for long-running execution
   - use `isolation: "worktree"` when the lane needs isolated edits
10. Verify the launched teammate instead of assuming startup succeeded:
   - inspect `~/.claude/teams/{team-name}/config.json` after teammate creation and confirm the recorded `model` for that teammate matches the resolved value you intended to use
   - if the runtime cannot use the generated custom teammate definition, stop and surface that capability gap explicitly instead of silently falling back to a generic teammate
   - if the teammate falls back to an unexpected model, shows `model not found`, or enters `idle` without consuming its first probe message, treat startup as failed rather than successful
   - on failure, recreate or update the teammate with an explicit Claude-supported model value before assigning real implementation work
   - use a minimal readiness probe message before task assignment so an idle lane is detected early and does not silently absorb a real task
11. Tell every teammate to call `TaskList`, claim or inspect its assigned work, and use `SendMessage` for coordination instead of silent progress.
12. Track progress through the shared task list:
   - `TaskUpdate({ taskId, status: "in_progress" })`
   - `TaskUpdate({ taskId, status: "completed" })`
   - `TaskList()` and `TaskGet(taskId: "...")` to inspect team state
13. Use `SendMessage` for handoffs, blockers, and dependency releases. Approve structured messages such as `shutdown_request` or `plan_approval_request` when they arrive.
14. Keep the same completion discipline as `/sp-implement`: do not cross the join point or declare completion until structured handoffs are consumed and the tracker/result state is updated.
15. When implementation is done, request shutdown for each teammate, then clean up the team with `TeamDelete()`.

## Output Expectations

Successful runs should leave the user with:

1. a Claude-native team config under `~/.claude/teams/{team-name}/config.json`
2. a shared task ledger under `~/.claude/tasks/{team-name}/`
3. explicit teammate ownership, status transitions, and dependency tracking
4. the same implementation lifecycle semantics as `/sp-implement`, including tracker continuity, join point visibility, and result handoff discipline
5. implementation framed as Claude Code Agent Teams execution, not as Codex runtime or extension plumbing
6. explicit evidence of the resolved teammate model choice and the generated `.claude/agents/*.md` teammate definitions used for that run

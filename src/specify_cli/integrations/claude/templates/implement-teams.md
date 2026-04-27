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

1. `/sp-implement` would otherwise run a `single-lane` or native delegated flow
2. you want durable coordinated execution with a shared task list and explicit teammate messaging
3. the implementation work is already decomposed into task-ready execution slices

## Execution Contract

1. Confirm the current project is using the Claude integration and that `tasks.md` is ready.
2. Confirm Claude Agent Teams is actually enabled before you try to use it:
   - confirm the current Claude Code configuration enables Agent Teams, whether that configuration lives in `settings.json` or the environment
   - treat `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` as the canonical Claude Code setting/env key for that feature gate when you need to name the switch explicitly
   - if the Agent Teams surface is unavailable, or if the first `TeamCreate` / Agent Teams call fails as though the feature is disabled, stop and explicitly remind the user to enable Agent Teams in Claude Code settings or environment instead of continuing with a broken team setup
   - treat this as a hard prerequisite for `/sp-implement-teams`, not as an optional hint
3. Create or resume a Claude Agent Team for the feature:
   - if a team for the same feature slug is already active, reuse or resume it instead of creating a second parallel team for the same feature
   - if the first `TeamCreate` call fails because you are already leading the team, treat that as a recoverable resume signal rather than a terminal failure
   - inspect the existing team ledger, shared task list, and pending work first, then continue from the recorded ready batch
   - do not create a second parallel team for the same feature just to get unstuck

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
5. Before the first `TaskCreate`, compile an execution context bundle for the current batch:
   - include `PROJECT-HANDBOOK.md`
   - include the smallest relevant `.specify/project-map/*.md` files for the touched subsystem, at minimum `.specify/project-map/WORKFLOWS.md` plus any architecture/operations/testing topics that define the lane boundary
   - include `.specify/testing/TESTING_CONTRACT.md` and `.specify/testing/TESTING_PLAYBOOK.md` when present
   - for each bundled item, preserve the path, why it matters, and a read order so the teammate knows both where the project truth lives and what it is for
6. Convert the ready implementation slices into explicit shared tasks with `TaskCreate`.
   - every shared task must carry the execution context bundle, not just the task summary
   - the task body must tell the teammate which context items are required, what each item is for, and which ones must be read before work starts
   - create the full task set before wiring `blockedBy` / `blocks` dependencies; do not point one task at another task record that does not exist yet
   - every shared task must preserve an explicit execution packet shape, not just prose:
     - task id and subject
     - write set and shared surfaces
     - required references and forbidden drift
     - deliverables
     - explicit verification command or acceptance check
     - canonical result handoff path when the leader expects a file handoff
     - completion protocol covering start, blocker, and final completion evidence
     - platform guardrails such as supported platforms or required conditional compilation for platform-specific code
   - use a standardized task body shape such as:

```text
Task ID: T001
Subject: Protocol update for foreground process payload
Write Set:
- apps/local-agent/src/protocol.rs
- apps/relay-server/src/protocol.rs
Required References:
- PROJECT-HANDBOOK.md
- .specify/project-map/WORKFLOWS.md
Deliverables:
- matching protocol definitions on both sides
- focused tests updated
Verification:
- cargo test -p local-agent
Result Handoff:
- write the normalized result envelope to FEATURE_DIR/worker-results/T001.json when the leader requests a file handoff
Completion Protocol:
1. SendMessage({ type: "task_started", task_id: "T001" })
2. run the required verification
3. TaskUpdate({ taskId: "T001", status: "completed" })
4. SendMessage({ type: "task_completed", task_id: "T001", summary: "...", verification: "...", files_changed: [...] })
Platform Guardrails:
- supported_platforms: windows, linux
- use conditional compilation for platform-specific code instead of assuming unix-only APIs are always available
Join Point:
- Join Point 1.1
```
7. Encode dependencies and ownership with `TaskUpdate`:
   - use `blockedBy` / `blocks` for ordering
   - use `owner` to assign each task to a named teammate
   - finish all `TaskCreate` calls for the current ready batch first, then wire dependency edges and ownership in a second pass so dependency references never point at missing task records
8. Inherit Claude Code's configured subagent model behavior before teammate creation:
   - rely on Claude Code's current subagent configuration instead of resolving teammate model choice manually for this workflow
   - if `CLAUDE_CODE_SUBAGENT_MODEL` is configured in the environment, treat it as the active subagent model hint for this run
   - when subagent model behavior is configured through Claude Code settings, trust that configuration instead of re-deriving or copying model values into teammate setup
   - do not derive teammate model from `ANTHROPIC_MODEL`
   - do not ask the user for an explicit teammate model just to launch the team
   - do not require local `.claude/agents/<team-name>-<role>.md` teammate definitions solely to force a model choice
9. Create the teammates on the native Agent Teams surface:
   - reference a generated teammate definition name when the current Claude build supports it and you genuinely need reusable teammate packaging
   - prompt-only specialization is acceptable when you do not need a persisted custom teammate definition
   - use read-only style teammate definitions for analysis or planning lanes and implementation-oriented teammate definitions for write lanes
   - set `team_name` so every teammate joins the same shared ledger
   - prefer `run_in_background: true` for long-running execution
   - use `isolation: "worktree"` when the lane needs isolated edits
10. Verify the launched teammate instead of assuming startup succeeded:
   - inspect the team ledger and shared task state after teammate creation and confirm the teammate joined the intended team
   - if the runtime cannot use the chosen teammate configuration, simplify the launch path instead of forcing an explicit model override
   - if the teammate enters `idle` without consuming its first probe message, treat startup as failed rather than successful
   - use a minimal readiness probe message before task assignment so an idle lane is detected early and does not silently absorb a real task
   - the readiness probe must confirm the teammate consumed the execution context bundle and can echo a `context_ack` containing the required paths or read-order items before any real work is assigned
11. Tell every teammate to call `TaskList`, claim or inspect its assigned work, and use `SendMessage` for coordination instead of silent progress.
   - ack the context bundle before claiming work; a teammate must not claim work until it has confirmed the required paths
   - after claiming work, the teammate must emit an explicit `task_started` message before settling into background execution so the leader can distinguish real execution from a silent idle lane
12. Track progress through the shared task list:
   - `TaskUpdate({ taskId, status: "in_progress" })`
   - `TaskUpdate({ taskId, status: "completed" })`
   - `TaskList()` and `TaskGet(taskId: "...")` to inspect team state
   - treat `TaskUpdate({ status: "completed" })` as necessary but not sufficient when the task promised a completion handoff, verification summary, or result file
13. Use `SendMessage` for handoffs, blockers, dependency releases, and context acknowledgement receipts. Approve structured messages such as `context_ack`, `shutdown_request`, or `plan_approval_request` when they arrive.
   - when execution actually begins, prefer `task_started` messages with the task id and a short execution note
   - when blocked, require a `task_blocked` message naming the blocker, failed assumption, and smallest safe recovery step
   - when complete, require a `task_completed` message that includes task id, summary, verification run, files changed, and any residual concern even if the task status is already marked `completed`
   - when a result handoff path was promised, the teammate must write that result before entering `idle`; a completion message without the promised handoff is incomplete
14. Keep the same completion discipline as `/sp-implement`: do not cross the join point or declare completion until structured handoffs are consumed, the tracker/result state is updated, and every teammate has confirmed the required context bundle for its lane.
    - after each completed join point or ready batch, immediately re-read the shared task ledger, select the next ready batch and continue automatically
    - stop only when no ready work remains, a real blocker stops progress, or an explicit human approval gate is reached
    - do not stop after a single completed batch just because the current assignee went idle
15. Only after the shared completion contract is fully satisfied may you request shutdown for each teammate, then clean up the team with `TeamDelete()`.
   - if the team has only finished core implementation or is merely ready for integration testing while required E2E, Polish, documentation, or validation tasks remain, report partial progress and keep the remaining work explicit instead of declaring overall feature completion
   - a `shutdown_response` or other approval signal means the teammate accepted shutdown, not that it already left the team; confirm active membership before treating cleanup as complete

## Output Expectations

Successful runs should leave the user with:

1. a Claude-native team config under `~/.claude/teams/{team-name}/config.json`
2. a shared task ledger under `~/.claude/tasks/{team-name}/`
3. explicit teammate ownership, status transitions, and dependency tracking
4. the same implementation lifecycle semantics as `/sp-implement`, including tracker continuity, join point visibility, and result handoff discipline
5. implementation framed as Claude Code Agent Teams execution, not as Codex runtime or extension plumbing
6. explicit evidence that teammates inherited Claude Code's configured subagent model behavior when applicable, without ad hoc model-guessing or forced local teammate model files

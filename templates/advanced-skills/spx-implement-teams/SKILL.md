---
name: spx-implement-teams
description: Durable-team implementation workflow for advanced coding models. Use when work is ready for spx-implement but explicitly requires the installed integration's supported persistent team backend and durable joins.
---

# SPX Implement Teams

Read `references/project-cognition.md`, using cognition intent `implement`.
Treat the ordinary execution contract at
`../spx-implement/references/execution-contract.md` as binding; this workflow
changes orchestration, not task acceptance or lifecycle truth. Read
`references/codex-teams.md` for Codex or `references/claude-agent-teams.md` for
Claude. Read `references/consequence-gate.md` only on its triggers.
Read `references/ui-quality-gate.md` when any dispatched task is UI-bearing.

Select the backend from the agent hosting this Skill and corroborate it with
`.specify/integration.json`; stop on a mismatch. Codex uses the project
launcher-backed `sp-teams` runtime; Claude uses native Agent Teams.
Other integrations have no equivalent durable backend in this profile: stop,
state that boundary, and recommend `$spx-implement` without switching
automatically. Never emulate durable state in chat or substitute ordinary
subagents for an explicitly selected teams run.

Resolve the task-bearing feature with the installed prerequisite script using
`--require-tasks --include-tasks`. Require a clean leader write boundary, valid
ready tasks, isolated worker scopes, explicit joins, and the same acceptance,
must-preserve, RED/baseline, and verification obligations as direct execution.

Recover `workflow-state.md`, implementation state, task lifecycle records, and
task-index `source_revision` before creating or resuming a team. If an Analyze
Gate is required, active, blocked, or stale, or the current task graph cannot
be trusted, hand off to `$spx-analyze` and stop. Do not run analysis inline or
let a worker repair cross-phase truth.

Apply the ordinary external-evidence rules unchanged. A protected-CI or human
blocker keeps its task unchecked and blocked; an authorized commit needed only
to obtain that evidence must pass the `external-evidence-checkpoint` intent and
does not authorize push, CI, or final closeout. If one task is blocked but
dependency-safe work remains, continue: remaining planned validation tasks are
ready work, not an excuse to idle the whole team.

Follow the selected backend reference. Resume the existing feature team when
present. Dispatch only validated bounded packets; await terminal structured
results, validate every join, synchronize managed worktrees when required,
inspect the combined diff, and run fresh real-entrypoint verification.

On resume, reject a stale lane whose task source revision, allowed write scope,
worktree/branch identity, or accepted result no longer matches durable state;
preserve its evidence, mark the recovery boundary, and redispatch only from a
fresh packet. Separate failures introduced by this feature from baseline debt.
Baseline debt must be recorded with evidence and routed explicitly; it never
turns a new regression or an unmet acceptance check into a pass.

Finish through the ordinary implementation closeout and cognition closeout.
Idle workers, terminal-looking trackers, or a successful sync are not feature
completion. Preserve blocked team state and report the exact recovery command.

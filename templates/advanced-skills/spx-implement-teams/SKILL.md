---
name: spx-implement-teams
description: Durable-team implementation workflow for advanced coding models. Use when work is ready for spx-implement but explicitly requires the installed integration's supported persistent team backend and durable joins.
---

# SPX Implement Teams

Read `references/project-cognition.md`, using cognition intent `implement`. Read
`references/codex-teams.md` for Codex or `references/claude-agent-teams.md` for
Claude. Read `references/consequence-gate.md` only on its triggers.

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

Follow the selected backend reference. Resume the existing feature team when
present. Dispatch only validated bounded packets; await terminal structured
results, validate every join, synchronize managed worktrees when required,
inspect the combined diff, and run fresh real-entrypoint verification.

Finish through the ordinary implementation closeout and cognition closeout.
Idle workers, terminal-looking trackers, or a successful sync are not feature
completion. Preserve blocked team state and report the exact recovery command.

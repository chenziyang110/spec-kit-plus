# Durable teams and independent lane integration

Use native in-session subagents for bounded parallel work. Upgrade to the
Codex-only `sp-teams` runtime only when coordination must survive the current
session, requires durable join-point state, or uses managed worker worktrees.
Do not claim this backend exists for another integration.

Before the first durable batch, require a clean leader workspace and run
`sp-teams doctor`. Run `sp-teams live-probe` after install/repair or when the
backend remains uncertain. Reuse or resume an active feature session; never
start a second leader for the same feature. Dispatch only validated task
packets with isolated writes and explicit joins. Generate handoffs with
`sp-teams result-template --request-id <id>` (or inspect
`sp-teams submit-result --print-schema`), await terminal results, validate each
join, and use `sp-teams sync-back` before leader-visible verification when
managed worktrees diverge. Idle execution without the promised result is not
completion.

For independent feature lanes, run `specify integrate` to discover candidates.
For each lane, verify recorded ownership, current branch/worktree state,
dependency order, overlapping writes, drift, required validation, and recovery
state. Resolve conflicts in dependency order. Only after readiness is true and
the integrated result passes the combined real-entrypoint checks may you run
`specify integrate --feature-dir <dir> --close`. Preserve blocked lanes and
their recovery evidence; do not mark a merge or copied files as closeout.

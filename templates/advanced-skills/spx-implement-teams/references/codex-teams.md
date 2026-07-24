# Codex teams execution

Require a clean leader workspace and healthy `.specify/teams/` runtime. Run
`{{specify-subcmd:specify-runtime sp-teams doctor}}` before the first batch and
`{{specify-subcmd:specify-runtime sp-teams live-probe}}` after install/repair or uncertain
health. Resume the existing feature session; never start a second leader.

Use `{{specify-subcmd:specify-runtime sp-teams auto-dispatch --feature-dir <feature-dir>}}` for
an explicit ready parallel batch so validated packets, requests, result paths,
and batch state are compiled by the runtime. Observe with the supported status,
await, or watch surfaces. For structured recovery, generate a handoff with
`{{specify-subcmd:specify-runtime sp-teams result-template --request-id <id>}}` or inspect
`{{specify-subcmd:specify-runtime sp-teams submit-result --print-schema}}`; a pending template
is not a completed result.

Await every request and reject missing, stale, out-of-scope, or unverified
results. Run `{{specify-subcmd:specify-runtime sp-teams complete-batch --batch-id <id>}}` only
after terminal results and accepted joins. Use
`{{specify-subcmd:specify-runtime sp-teams sync-back}}` before leader-visible verification when
managed worktrees diverge. Do not edit an active worker scope or clean state
needed for recovery.

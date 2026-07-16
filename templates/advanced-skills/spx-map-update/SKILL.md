---
name: spx-map-update
description: Lean project-cognition maintenance workflow for advanced coding models. Use for explicit incremental map maintenance, external repository changes, interrupted updates, or a known existing-baseline gap that needs repair.
---

# SPX Map Update

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`. Use this skill for explicit maintenance,
not as a substitute for the automatic closeout performed by writing workflows.
Read `references/update-gates.md`.

Confirm that an active baseline exists and does not require rebuild. Determine
the actual change boundary with
`{{specify-subcmd:project-cognition changes --intent map-update --format json}}`
or explicit `--changed-path` values. Inspect the affected live repository
paths, owners, behavior surfaces, verification routes, and downstream graph
relationships.

Run
`{{specify-subcmd:project-cognition closeout-plan --workflow map-update --intent implement --reason map-update --format json}}`,
passing each accepted path as an explicit `--changed-path` when the runtime
requires it.
Complete its structured payload with changed paths, behavior and generated
surfaces, state contracts, user decisions, known unknowns, confidence, and
fresh verification evidence. Execute `update_argv` using the launcher-token
replacement rule in `references/project-cognition.md`, never the display-only
command string.

Follow the result-state branches in the update reference. Run
`{{specify-subcmd:project-cognition validate-build --format json}}` after an
applied update. A `ready` result plus passing validation must finish with
`{{specify-subcmd:project-cognition complete-refresh --format json}}`; a
`no_op` result may finish freshness metadata with
`{{specify-subcmd:project-cognition record-refresh --reason map-update --format json}}`.
Never finalize `partial_refresh`, `blocked`, or `needs_rebuild` as fresh.

Validate the affected scope with
`{{specify-subcmd:project-cognition compass --intent implement --query "<changed scope>" --format json}}`
and targeted expansion. Route by `recommended_next_action.action_id`, not
`needs_rebuild` alone. Preserve resumable actions such as
`complete_scan_packets`; only `action_id=project_cognition.rebuild` may consume
`rebuild_reasons[]` and the Advanced workflow route to recommend
`$spx-map-rebuild`. Do not invoke `$spx-map-rebuild` in this run. Report the
updated scope, validation, gaps, and recovery state. This invocation authorizes
only this workflow stage; a recovery handoff does not authorize another one.

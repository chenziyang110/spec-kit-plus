---
name: spx-map-update
description: Lean specify-runtime cognition maintenance workflow for advanced coding models. Use for explicit incremental map maintenance, external repository changes, interrupted updates, or a known existing-baseline gap that needs repair.
---

# SPX Map Update

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`. Use this skill for explicit maintenance,
not as a substitute for the automatic closeout performed by writing workflows.
Read `references/update-gates.md`.

Confirm that an active baseline exists and does not require rebuild. Determine
the actual change boundary with
`{{specify-subcmd:specify-runtime cognition changes --intent map-update --format json}}`
or explicit `--changed-path` values. Inspect the affected live repository
paths, owners, behavior surfaces, verification routes, and downstream graph
relationships.

Run
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-map-update --scope-dir .specify/project-cognition --scope-mode explicit --intent implement --reason map-update --format json}}`,
passing each accepted path as an explicit `--changed-path` when the runtime
requires it.
Complete its structured payload with changed paths, behavior and generated
surfaces, state contracts, user decisions, known unknowns, confidence, and
fresh verification evidence. Set each
`unknown_path_dispositions[].agent_disposition`; it binds to the matching
`path_changes[].disposition`, and delta mode must supply every returned
`--path-disposition` placeholder. Missing, duplicate, conflicting, or unmatched
decisions fail before mutation. Execute `apply_argv` using the launcher-token
replacement rule in `references/project-cognition.md`, never the display-only
command string. Shared apply owns update, validation, eligible finalization,
and receipt. An ignored disposition remains in audit-only `path_changes`,
but it must not enter graph-changing `changed_paths` or create graph records.
Legacy or free-text verification is `result=recorded` audit evidence only;
clean closeout requires structured verification with exact `result=passed`.

Follow the shared apply gate in `references/project-cognition.md`. Read
`scope_result_state` separately from project-wide `result_state`. When scope
and global results are `ready|no_op`, it internally
runs `{{specify-subcmd:specify-runtime cognition validate-build --format json}}`
and eligible `{{specify-subcmd:specify-runtime cognition complete-refresh --format json}}`,
then writes the bound receipt. Only `status=ok` with `readiness=query_ready`
may finalize; until it does, the runtime remains `pending finalization`.
`closeout_state=scope_ready` closes the accepted
paths while preserving unrelated global debt. For a scope-level
`partial_refresh`, `blocked`, `needs_rebuild`, or legacy `recorded`, runtime must
not run `complete-refresh` and must preserve the truthful state and recovery
action. `{{specify-subcmd:specify-runtime cognition record-refresh --reason map-update --format json}}`
is reserved for compatibility or explicit metadata recording when a matching
validation receipt already exists; it is not an ordinary closeout branch and
must not bypass receipt-bound `complete-refresh`.

Validate the affected scope with
`{{specify-subcmd:specify-runtime cognition compass --intent implement --query "<changed scope>" --format json}}`
and targeted expansion. Route by `recommended_next_action.action_id`, not
`needs_rebuild` alone. Preserve resumable actions such as
`complete_scan_packets`; only `action_id=project_cognition.rebuild` may consume
`rebuild_reasons[]` and the Advanced workflow route to recommend
`$spx-map-rebuild`. Do not invoke `$spx-map-rebuild` in this run. Report the
updated scope, validation, gaps, and recovery state. This invocation authorizes
only this workflow stage; a recovery handoff does not authorize another one.

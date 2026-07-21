### Inline Project Cognition Update

Workflow-owned mutation closeout is not an external map-maintenance handoff and is not external map maintenance. It is the workflow-local form of `{{invoke:map-update}}`. If this workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, shared surfaces, or behavior-bearing docs, closeout MUST run inline project cognition update for the workflow-owned changed paths and affected surfaces before claiming clean completion.

Call the planner first:

```text
{{specify-subcmd:project-cognition closeout-plan --workflow {{project-cognition-workflow}} --format json}}
```

When `DELTA_SESSION_ID` exists, pass it into the planner:

```text
{{specify-subcmd:project-cognition closeout-plan --workflow {{project-cognition-workflow}} --delta-session "$DELTA_SESSION_ID" --format json}}
```

Consume `workflow_canonical`, `update_mode`, `payload_draft`, `required_agent_fields`, `unknown_paths`, `unknown_path_dispositions`, `delta_append_draft`, display-only `delta_append_command`, `update_argv`, display-only `update_command`, and `recommended_next_command`.

The planner owns both executable update branches, selected by `update_mode` (`delta_session` or `payload_file`). Treat that mode as explanatory metadata, never as authority to construct a replacement command; execute the planner-returned `update_argv` exactly.

Before running `update`, fill the fields listed in `required_agent_fields` from live evidence from this workflow. Supported agent-owned evidence fields include:

- `verification`
- `behavior_surfaces`
- `generated_surfaces`
- `state_contracts`
- `known_unknowns`
- `confidence_notes`
- `user_decisions`
- `boundary`

If a field appears in `required_agent_fields`, provide live-evidence-backed content for it. Fields not listed by `required_agent_fields`, such as `known_unknowns` and `boundary`, are populated only when live evidence supports them; do not invent them to satisfy the shape.
Use `known_unknowns` only for blockers that make the cognition update unsafe to trust. If the working tree contains unrelated dirty/untracked paths and the workflow uses explicit workflow-owned paths, record that as `confidence_notes` or `boundary.initial_dirty_paths`, not as a blocking `known_unknowns` item.

For each `unknown_path_dispositions[]` item, set `agent_disposition` to exactly one allowed value:

- `adoptable`: verified new path inside this workflow-owned scope; it may be recorded in changed/scope paths and verified adoptable paths do not become blocking `known_unknowns`.
- `review_only`: path informed review but is not adopted into changed coverage.
- `ignored`: preserve the disposition in audit-only `path_changes`, but do not place the path in graph-changing `changed_paths`, route indexes, graph evidence, aliases, or minimal live reads.
- `blocking_known_unknown`: record it as a known unknown and report partial or blocked cognition closeout.

The runtime binds each `unknown_path_dispositions[].agent_disposition` to the matching `path_changes[].disposition`; the two views are one decision, not independent fields. If both are populated they must agree, and a missing, duplicate, conflicting, or unmatched decision fails before graph mutation. In delta mode, replace and append every returned `--path-disposition` placeholder so the event records the same resolved typed decision.

`agent_disposition=adoptable` is an agent accounting decision, not proof that runtime indexing already succeeded. Runtime adoption still requires a usable active project-cognition DB, at least one passing verification evidence item, and no blocking `known_unknowns`. After `update_argv` runs, inspect `result_state`, `adopted_paths`, `review_paths`, `minimal_live_reads`, and `partial_refresh_reasons`; do not explain a remaining `partial_refresh` as "path_index missing" until those fields show which adoption gate failed.

If `update_mode=delta_session`, complete `delta_append_draft.argv_prefix` with every required `--path-disposition` plus agent-owned repeatable flags such as `--behavior-surface`, `--generated-surface`, `--verification`, and accepted `--known-unknown` values from `delta_append_draft.argv_placeholders`. Every passing `--verification` value must be one structured JSON object with the planner shape `{"command":"<agent-owned verification command>","result":"passed","artifact":"<optional evidence artifact>"}`; do not pass freeform command-result strings or result aliases. Legacy or free-text verification is audit evidence with `result=recorded` only and cannot satisfy clean closeout; clean closeout requires structured `result=passed`. Then append the delta event and run `update_argv`. `delta_append_command` and `update_command` are display-only placeholders, not execution strings.

If `update_mode=payload_file`, write the completed `payload_draft` to the planner's `payload_path`. Then run `update_argv`. `update_command` is a display-only placeholder, not an execution string.

Completed payload drafts preserve the planner-owned `changed_paths` and `scope_paths` and add agent-owned evidence fields before recording.

Structured `update` invalidates related claims and returns their stable IDs in `affected_graph_claims`. This is separate from update readiness: generic workflow verification and `result_state=ready` must not re-promote stale or contradicted graph claims. Only when this workflow already has decisive claim-specific bounded live evidence for an exact returned claim ID may it submit semantic reconciliation intent and run:

```text
{{specify-subcmd:project-cognition claim-reconcile prepare --input <intent.json> --format json}}
{{specify-subcmd:project-cognition claim-reconcile apply --input <prepared_packet_path> --format json}}
```

Provide only reconciliation intent: workflow, stable `claim_id`, reason, and evidence containing repository-relative `source_path`, bounded line `span`, and `supporting` or `contradicting` role. Add verification only when it is claim-specific. The runtime owns the contract version, active generation, expected state and revision, UTC observation and expiry, source kind, content hashes, repository snapshot, IDs, and prepared packet path. Do not author or edit those integrity fields; execute the returned `apply_argv` exactly. If no such evidence exists, leave the claim stale. If reconciliation returns ready, rerun Compass once so later routing consumes the current evidence basis; partial or blocked reconciliation remains withheld and follows `recommended_next_action`.

For compatibility with worker handoffs and payload packets, the runtime also accepts `verification_evidence` as an alias for `verification` and `generated_surface_notes` as an alias for `generated_surfaces`. Verification evidence must be an array of structured objects with `command`, exact `result` (`passed`, `failed`, or `recorded`), and optional `artifact`; clean closeout requires at least one `result=passed` record, and failed verification cannot produce a clean `ready` closeout.

Clean closeout keys on `result_state`, not `status=ok`, `update_id`, `last_update_id`, or freshness alone:

- `result_state=ready` or `result_state=no_op`: run `{{specify-subcmd:project-cognition validate-build --format json}}` after this latest update. Only a response with `status=ok` and `readiness=query_ready` creates the validate-build receipt bound to the latest update ID, outcome, and active generation. Then, and only then, run `{{specify-subcmd:project-cognition complete-refresh --format json}}`; clean completion requires that receipt-bound finalizer to succeed. Until it succeeds, the runtime gate withholds Compass/query as pending finalization.
- `partial_refresh`: useful update data was written, but the final workflow state must report partial cognition closeout, `partial_refresh_reasons`, and the returned `minimal_live_reads`. If `partial_refresh_reasons` includes `missing_passing_verification_result`, repair the payload or delta evidence and rerun `update_argv` before final closeout; do not route that to `sp-map-update`. If verified workflow-owned paths still remain in `review_paths` after the update, report implementation completion separately from project-cognition maintenance and name `{{invoke:map-update}}` as follow-up repair.
- `needs_rebuild`: report the exact rebuild condition and route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- `blocked`: report the runtime or validation blocker and the exact recovery command.
- `recorded`: legacy recorded-only output; treat it as partial or blocked, never as clean completion.

Never run the `complete-refresh` or `clear-dirty` helper after `result_state=partial_refresh`. The same prohibition applies to `needs_rebuild`, `blocked`, or legacy `recorded`; preserve the truthful state and returned recovery action. A failed, blocked, stale, or non-`query_ready` validate-build result also must not run `complete-refresh`.

Dirty fallback command shape: `{{specify-subcmd:project-cognition mark-dirty --reason "<reason>" --format json}}`.
Use `{{specify-subcmd:project-cognition mark-dirty --reason "workflow-closeout-failed" --format json}}` only when inline update cannot complete: when the planner or update command is unavailable, cannot record useful update data, cannot identify workflow-owned scope, or cannot be trusted because verification/workflow completion is not trustworthy. Dirty only when inline update cannot complete.

sp-map-update is for manual/external maintenance and follow-up repair. `{{invoke:map-update}}` remains the external/manual workflow for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. It is not routine cleanup for changes this workflow just made. If `sp-map-update` already ran `project-cognition update --reason map-update` for the same changed paths, do not run a second `workflow-finalize` closeout update for those paths.

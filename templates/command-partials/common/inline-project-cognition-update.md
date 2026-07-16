### Inline Project Cognition Update

Workflow-owned mutation closeout is not an external map-maintenance handoff and is not external map maintenance. It is the workflow-local form of `{{invoke:map-update}}`. If this workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, shared surfaces, or behavior-bearing docs, closeout MUST run inline project cognition update for the workflow-owned changed paths and affected surfaces before claiming clean completion.

Call the planner first:

```text
project-cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --format json
```

When `DELTA_SESSION_ID` exists, pass it into the planner:

```text
project-cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --delta-session "$DELTA_SESSION_ID" --format json
```

Consume `workflow_canonical`, `update_mode`, `payload_draft`, `required_agent_fields`, `unknown_paths`, `unknown_path_dispositions`, `delta_append_draft`, display-only `delta_append_command`, `update_argv`, display-only `update_command`, and `recommended_next_command`.

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
- `ignored`: path remains excluded and must not enter payloads, records, route indexes, evidence, aliases, or minimal live reads.
- `blocking_known_unknown`: record it as a known unknown and report partial or blocked cognition closeout.

`agent_disposition=adoptable` is an agent accounting decision, not proof that runtime indexing already succeeded. Runtime adoption still requires a usable active project-cognition DB, at least one passing verification evidence item, and no blocking `known_unknowns`. After `update_argv` runs, inspect `result_state`, `adopted_paths`, `review_paths`, `minimal_live_reads`, and `partial_refresh_reasons`; do not explain a remaining `partial_refresh` as "path_index missing" until those fields show which adoption gate failed.

If `update_mode=delta_session`, complete `delta_append_draft.argv_prefix` with agent-owned repeatable flags such as `--behavior-surface`, `--generated-surface`, `--verification`, and accepted `--known-unknown` values from `delta_append_draft.argv_placeholders`. Then append the delta event and run `update_argv`. `delta_append_command` and `update_command` are display-only placeholders, not execution strings.

If `update_mode=payload_file`, write the completed `payload_draft` to the planner's `payload_path`. Then run `update_argv`. `update_command` is a display-only placeholder, not an execution string.

Completed payload drafts preserve the planner-owned `changed_paths` and `scope_paths` and add agent-owned evidence fields before recording.

Structured `update` invalidates related claims and returns their stable IDs in `affected_graph_claims`. This is separate from update readiness: generic workflow verification and `result_state=ready` must not re-promote stale or contradicted graph claims. Only when this workflow already has decisive claim-specific bounded live evidence for an exact returned claim ID may it submit semantic reconciliation intent and run:

```text
project-cognition claim-reconcile prepare --input <intent.json> --format json
project-cognition claim-reconcile apply --input <prepared_packet_path> --format json
```

Provide only reconciliation intent: workflow, stable `claim_id`, reason, and evidence containing repository-relative `source_path`, bounded line `span`, and `supporting` or `contradicting` role. Add verification only when it is claim-specific. The runtime owns the contract version, active generation, expected state and revision, UTC observation and expiry, source kind, content hashes, repository snapshot, IDs, and prepared packet path. Do not author or edit those integrity fields; execute the returned `apply_argv` exactly. If no such evidence exists, leave the claim stale. If reconciliation returns ready, rerun Compass once so later routing consumes the current evidence basis; partial or blocked reconciliation remains withheld and follows `recommended_next_action`.

For compatibility with worker handoffs and delta packets, the runtime also accepts `verification_evidence` as an alias for `verification` and `generated_surface_notes` as an alias for `generated_surfaces`. Verification evidence may be an array of objects (`command`, `result`, `artifact`) or an array of command-result strings, but clean closeout still requires passing verification evidence; failed verification cannot produce a clean `ready` closeout.

Clean closeout keys on `result_state`, not `status=ok`, `update_id`, `last_update_id`, or freshness alone:

- `ready` or `no_op`: project cognition closeout may be clean when ordinary verification also passed.
- `partial_refresh`: useful update data was written, but the final workflow state must report partial cognition closeout, `partial_refresh_reasons`, and the returned `minimal_live_reads`. If `partial_refresh_reasons` includes `missing_passing_verification_result`, repair the payload or delta evidence and rerun `update_argv` before final closeout; do not route that to `sp-map-update`. If verified workflow-owned paths still remain in `review_paths` after the update, report implementation completion separately from project-cognition maintenance and name `{{invoke:map-update}}` as follow-up repair.
- `needs_rebuild`: report the exact rebuild condition and route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- `blocked`: report the runtime or validation blocker and the exact recovery command.
- `recorded`: legacy recorded-only output; treat it as partial or blocked, never as clean completion.

Never run the `complete-refresh` or `clear-dirty` helper after `result_state=partial_refresh`, `needs_rebuild`, `blocked`, or legacy `recorded`; those helpers are only for states that the runtime and validation prove ready.

Dirty fallback command shape: `{{specify-subcmd:project-cognition mark-dirty --reason "<reason>" --format json}}`.
Use `{{specify-subcmd:project-cognition mark-dirty --reason "workflow-closeout-failed" --format json}}` only when inline update cannot complete: when the planner or update command is unavailable, cannot record useful update data, cannot identify workflow-owned scope, or cannot be trusted because verification/workflow completion is not trustworthy. Dirty only when inline update cannot complete.

sp-map-update is for manual/external maintenance and follow-up repair. `{{invoke:map-update}}` remains the external/manual workflow for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. It is not routine cleanup for changes this workflow just made. If `sp-map-update` already ran `project-cognition update --reason map-update` for the same changed paths, do not run a second `workflow-finalize` closeout update for those paths.

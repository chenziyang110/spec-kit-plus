### Inline Project Cognition Update

Workflow-owned mutation closeout is not an external map-maintenance handoff and is not external map maintenance. It is the workflow-local form of `{{invoke:map-update}}`. If this workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, shared surfaces, or behavior-bearing docs, closeout MUST run inline project cognition update for the workflow-owned changed paths and affected surfaces before claiming clean completion.

Call the planner first:

```text
{{specify-subcmd:specify-runtime cognition closeout-plan --workflow {{project-cognition-workflow}} --scope-dir <feature-or-scope> --scope-mode explicit --format json}}
```

Before executing that command, append one `--changed-path <repo-relative-path>` flag for each workflow-owned path changed by this workflow. A rename owns both the old path and the new path: pass both endpoints and preserve both in `boundary.workflow_owned_paths`; a rename with either endpoint outside that boundary is invalid. These explicit paths are the mutation closeout scope; unrelated dirty, untracked, or committed-since-baseline repository paths must not be allowed to enter `changed_paths` for this workflow. If no workflow-owned path can be named, do not broad-scan to guess it; use dirty fallback with an explicit reason that the owned scope could not be identified.

When `DELTA_SESSION_ID` exists, pass it into the planner:

```text
{{specify-subcmd:specify-runtime cognition closeout-plan --workflow {{project-cognition-workflow}} --scope-dir <feature-or-scope> --scope-mode explicit --delta-session "$DELTA_SESSION_ID" --format json}}
```

The same explicit `--changed-path` flags are still required in delta mode; add them to the planner invocation together with `--delta-session`.

Consume `workflow_canonical`, `update_mode`, `payload_draft`, `required_agent_fields`, `unknown_paths`, `unknown_path_dispositions`, `delta_append_draft`, `apply_argv`, display-only `apply_command`, and `recommended_next_command`. `update_argv` remains a low-level compatibility/debug primitive; workflow closeout executes the shared `apply_argv` so update, validation, eligible finalization, and receipt cannot drift apart.

The planner owns both executable closeout branches, selected by `update_mode` (`delta_session` or `inline_json`). Treat that mode as explanatory metadata, never as authority to construct a replacement command. For `inline_json`, the returned `apply_argv` uses `--payload-json -`; serialize the completed in-memory `payload_draft` and write the completed payload JSON to the child process stdin. Never substitute payload JSON into process argv. Otherwise execute the planner-returned argv exactly.

Before running shared closeout apply, fill the fields listed in `required_agent_fields` from live evidence from this workflow. Supported agent-owned evidence fields include:

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

`agent_disposition=adoptable` is an agent accounting decision, not proof that runtime indexing already succeeded. Runtime adoption still requires a usable active specify-runtime cognition DB, at least one passing verification evidence item, and no blocking `known_unknowns`. After `apply_argv` runs, inspect `scope_result_state`, project-wide `result_state`, `global_freshness`, `global_debt_reasons`, `adopted_paths`, `review_paths`, `minimal_live_reads`, and `partial_refresh_reasons`; do not explain a remaining `partial_refresh` as "path_index missing" until those fields show which adoption gate failed.

If `update_mode=delta_session`, complete `delta_append_draft.argv_prefix` with every required `--path-disposition` plus agent-owned repeatable flags such as `--behavior-surface`, `--generated-surface`, `--verification`, and accepted `--known-unknown` values from `delta_append_draft.argv_placeholders`. Every passing `--verification` value must be one structured JSON object with the planner shape `{"command":"<agent-owned verification command>","result":"passed","artifact":"<optional evidence artifact>"}`; do not pass freeform command-result strings or result aliases. Legacy or free-text verification is audit evidence with `result=recorded` only and cannot satisfy clean closeout; clean closeout requires structured `result=passed`. Then append the delta event and run `apply_argv`. The display-only `delta_append_command`, display-only `update_command`, and display-only `apply_command` are placeholders, not execution strings.

If `update_mode=inline_json`, complete `payload_draft` in memory, serialize it once, execute the returned `apply_argv` containing `--payload-json -`, and write the completed payload JSON to stdin. Never replace `-` with inline JSON and never create a payload file. `apply_command` is a display-only placeholder, not an execution string.

Completed payload drafts preserve the planner-owned `changed_paths`, `scope_paths`, `boundary.workflow_owned_paths`, and `boundary.scope_mode=explicit` and add agent-owned evidence fields before recording.

Structured `update` invalidates related claims and returns their stable IDs in `affected_graph_claims`. This is separate from update readiness: generic workflow verification and `result_state=ready` must not re-promote stale or contradicted graph claims. Only when this workflow already has decisive claim-specific bounded live evidence for an exact returned claim ID may it submit semantic reconciliation intent and run:

```text
{{specify-subcmd:specify-runtime cognition claim-reconcile prepare --input-json '<intent-json>' --format json}}
{{specify-subcmd:specify-runtime cognition claim-reconcile apply --input <prepared_packet_path> --format json}}
```

Provide only reconciliation intent in memory: workflow, stable `claim_id`, reason, and evidence containing repository-relative `source_path`, bounded line `span`, and `supporting` or `contradicting` role. Never create an intent file. Add verification only when it is claim-specific. The runtime owns the contract version, active generation, expected state and revision, UTC observation and expiry, source kind, content hashes, repository snapshot, IDs, and prepared packet path. Do not author or edit those integrity fields; execute the returned `apply_argv` exactly. If no such evidence exists, leave the claim stale. If reconciliation returns ready, rerun Compass once so later routing consumes the current evidence basis; partial or blocked reconciliation remains withheld and follows `recommended_next_action`.

For compatibility with worker handoffs and payload packets, the runtime also accepts `verification_evidence` as an alias for `verification` and `generated_surface_notes` as an alias for `generated_surfaces`. Verification evidence must be an array of structured objects with `command`, exact `result` (`passed`, `failed`, or `recorded`), and optional `artifact`; clean closeout requires at least one `result=passed` record, and failed verification cannot produce a clean `ready` closeout.

Shared closeout keys on the current scope separately from the project-wide state. The Agent never manually sequences the deterministic tail:

- `scope_result_state=ready|no_op` and project-wide `result_state=ready|no_op`: `closeout apply` internally runs `{{specify-subcmd:specify-runtime cognition validate-build --format json}}` and then `{{specify-subcmd:specify-runtime cognition complete-refresh --format json}}`. Only `status=ok` plus `readiness=query_ready` creates the validate-build receipt bound to the latest update ID, outcome, and active generation; clean completion requires that receipt-bound finalizer to succeed. Until it succeeds, the runtime gate withholds Compass/query as pending finalization.
- `closeout_state=scope_ready`: this workflow's explicit paths succeeded, while unrelated pre-existing project debt remains in `global_debt_reasons`. The runtime writes a current-update-bound, closeable receipt without falsely finalizing global freshness; report the global debt separately instead of relabeling this workflow's paths as failed.
- `scope_result_state=partial_refresh`: useful update data was written, but the final workflow state must report partial cognition closeout, `partial_refresh_reasons`, and the returned `minimal_live_reads`. Missing `verification[result=passed]` is rejected before mutation as `closeout_status=needs_agent_input`, preventing the old avoidable `missing_passing_verification_result` partial; fill the evidence and rerun `apply_argv`; do not route that defect to `sp-map-update`. If verified workflow-owned paths still remain in `review_paths`, report implementation completion separately from cognition maintenance and name `{{invoke:map-update}}` as follow-up repair.
- `needs_rebuild`: report the exact rebuild condition and route to `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- `blocked`: report the runtime or validation blocker and the exact recovery command.
- `recorded`: legacy recorded-only output; treat it as partial or blocked, never as clean completion.

Shared apply writes a durable mutation intent before recovery and owns the whole
tail under the same update lock: older-intent drain, status projection repair,
one direct predecessor recovery, current update, validation, bound receipt,
eligible finalization, and scope receipt. A crash or another mutation workflow
cannot cross-bind updates; rerunning the same closeout resumes its intent, while
another closeout drains older intents first. When runtime agreement reports
`pending_finalization`, it recovers only the exact `ready|no_op` predecessor and
must not scan older unrelated history or finalize failed/non-`query_ready` validation;
the compact result remains `predecessor_recovery`.

If predecessor recovery blocks, the runtime writes the non-closeable
`predecessor_recovery_blocked` receipt with exact `changed_paths` and keeps the
mutation intent, so current mutation accounting remains durable. Keep the parent workflow active. For a bounded path-led
identity blocker, run returned `specify-runtime cognition identity-repair plan`,
then its digest-bound `specify-runtime cognition identity-repair apply`; after
the repair, run `specify-runtime cognition closeout replay --scope-dir
<feature-or-scope> --format json`. Only a successful replay replaces the blocked
receipt. Do not use standalone `mark-dirty` to bypass a replayable closeout or
ask the user to invoke `{{invoke:map-update}}` for an agent-repairable
predecessor.

Never run `update`, `validate-build`, `complete-refresh`, or `mutation-receipt` individually as a substitute for `closeout apply`. The runtime must not run `complete-refresh` after a scope-level `partial_refresh`, `needs_rebuild`, `blocked`, or legacy `recorded`; it preserves the truthful state and returned recovery action. A failed, blocked, stale, or non-`query_ready` validate-build result also must not run `complete-refresh`.

Dirty fallback command shape: `{{specify-subcmd:specify-runtime cognition mark-dirty --reason "<reason>" --format json}}`.
Use `{{specify-subcmd:specify-runtime cognition mark-dirty --reason "workflow-closeout-failed" --format json}}` only when no trustworthy mutation intent can be formed: the planner/runtime is unavailable, workflow-owned scope is unknown, or verification/workflow completion is untrustworthy. A persisted replay intent is not a dirty-fallback case.
Dirty only when inline update cannot complete and no trustworthy mutation intent exists.

Greenfield / empty-graph minimum: when the baseline is `greenfield_empty` or compass returns no adoptable paths, agents must still record a terminal cognition outcome (`no_op` or `mark-dirty` with reason). Skipping because “there is no graph to update” is not compliant.

### Durable mutation receipt (all source-changing workflows)

Successful `closeout apply` records the durable receipt itself **before** any terminal close (`quick close … resolved`, `implement closeout`, `workflow complete-stage` for implement/review, or claiming fast/debug complete). Do not stamp a second receipt. Only the `mark-dirty` fallback uses the standalone compatibility command:

```text
{{specify-subcmd:specify-runtime cognition mutation-receipt --workflow {{project-cognition-workflow}} --feature-dir <feature-or-scope> --result-state mark-dirty --reason "<text>" --format json}}
```

- Feature workflows obtain `<feature-dir>/cognition-closeout.json` only through
  the cognition/mutation-receipt runtime owners (never hand-authored).
- Quick may use the same runtime-owned file under the quick workspace, or
  `quick cognition-closeout` (wrapper).
- Runtime **blocks** implement closeout and implement/review `complete-stage` without an allowed receipt.
- Product goal: a greenfield project’s project-cognition graph **keeps growing** with every real code change. Prefer `ready` after shared apply; `scope_ready` is valid only when current paths succeeded and unrelated global debt remains. Use `mark-dirty`/`no_op` only with an explicit reason; treat repeated dirty-only closeouts as a process defect to repair on the next mutation.

sp-map-update is for manual/external maintenance and follow-up repair. `{{invoke:map-update}}` remains the external/manual workflow for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. It is not routine cleanup for changes this workflow just made. If `sp-map-update` already ran `specify-runtime cognition update --reason map-update` for the same changed paths, do not run a second `workflow-finalize` closeout update for those paths.

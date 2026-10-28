# Mutation closeout and recovery

- Workflow-owned mutation closeout is not an external map-maintenance handoff. If the active mutation workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, or behavior-bearing docs, follow its rendered planner-first closeout command with the registry-owned literal `sp-*` workflow ID and explicit workflow-owned paths; never derive the ID from an environment variable.
- Pass `--scope-dir <feature-or-scope> --scope-mode explicit` plus one explicit `--changed-path` per workflow-owned path to `closeout-plan`; a rename owns both its old and new endpoint, so pass and preserve both in `boundary.workflow_owned_paths`. When `DELTA_SESSION_ID` exists, also pass `--delta-session "$DELTA_SESSION_ID"`. Fill fields listed in `required_agent_fields` from live evidence; optional payload/delta fields such as `known_unknowns` and `boundary` are populated only when evidence supports them. Follow `update_mode=delta_session` by completing `delta_append_draft.argv_prefix` with evidence placeholders, appending the workflow closeout delta event, then running structured `apply_argv`. Follow `update_mode=inline_json` by completing `payload_draft` in memory, executing the returned `apply_argv` with `--payload-json -`, and writing the completed payload JSON to stdin; never place the JSON in process argv or create a payload file. `update_argv` is compatibility/debug only. The display-only `update_command`, display-only `delta_append_command`, and display-only `apply_command` placeholders are not execution strings.
- Use `known_unknowns` only for blockers that make the cognition update unsafe to trust. If the working tree contains unrelated dirty/untracked paths and the workflow uses explicit workflow-owned paths, record that as `confidence_notes` or `boundary.initial_dirty_paths`, not as a blocking `known_unknowns` item.
- Before closeout apply, resolve `unknown_path_dispositions` by setting `agent_disposition` to `adoptable`, `review_only`, `ignored`, or `blocking_known_unknown`. Verified `adoptable` paths do not become blocking `known_unknowns`. Only `blocking_known_unknown` dispositions become payload or delta known unknowns. `agent_disposition=adoptable` is an agent accounting decision, not proof that runtime indexing already succeeded; after `apply_argv` runs, inspect `scope_result_state`, project-wide `result_state`, `global_freshness`, `global_debt_reasons`, `adopted_paths`, `review_paths`, `minimal_live_reads`, and `partial_refresh_reasons`.
- Shared closeout keys on the current scope separately from project-wide state. `apply_argv` owns update, validate-build, eligible complete-refresh, and receipt. `closeout_state=scope_ready` closes successful owned paths without hiding unrelated global debt. Missing passing verification returns `closeout_status=needs_agent_input` before mutation instead of creating `missing_passing_verification_result`. `recorded` remains legacy partial/blocked output. Use `specify-runtime cognition mark-dirty --reason "workflow-closeout-failed" --format json` only when shared apply is unavailable, fails before useful update data, cannot identify workflow-owned scope, is blocked by runtime state, or verification/workflow completion is untrustworthy.
- Shared apply first persists a mutation intent and owns older-intent drain, status repair, one direct predecessor, current update, validation, finalization, and the scope receipt under the same update lock; an unfinished predecessor remains `pending_finalization`, the compact recovery result remains `predecessor_recovery`, and it must not scan older unrelated history. If recovery blocks, `predecessor_recovery_blocked` is non-closeable and keeps exact paths plus the replay intent so current mutation accounting remains durable. For bounded path-led debt run returned `specify-runtime cognition identity-repair plan` and digest-bound `specify-runtime cognition identity-repair apply`, then `specify-runtime cognition closeout replay --scope-dir <scope> --format json`. Another mutation closeout drains older intents automatically. Never downgrade a replayable intent to `mark-dirty` or ask the user to invoke map-update for agent-repairable recovery.
- On `repair_update_or_replay_intent` or a blocked queued intent, keep the parent
  workflow active. Stop retrying the same failing apply while the intent and cause
  are unchanged. Execute returned `recovery_argv` or
  `{{specify-subcmd:specify-runtime cognition closeout inspect --intent-id <blocked_intent_id> --format json}}`;
  omit the ID only to list compact pending cards. This read-only inspection needs
  no blocked scope receipt. Select the exact `blocked_intent_id` and inspect scope,
  workflow, state, `input_digest`, verification diagnostics, and
  `recommended_next_action`; never infer the intent from an older successful receipt
  or guess `--scope-dir .`. If inspect directly offers `replay_argv`, execute it
  unchanged without requiring repair or replacement fields. Execute applicable
  `repair_argv` unchanged. A new repair
  uses `cognition closeout repair --intent-id <ID> --expected-digest <input_digest>
  --verification-json - --format json` with the complete truthful structured
  verification array on stdin (`command`, exact `result`, optional `artifact`).
  Never invent verification commands or passing results; first run needed checks
  or recover trustworthy evidence. Empty stdin cannot initiate repair; only an
  already journaled repair may resume without resupplying evidence when runtime
  permits it. Repair archives the original and creates a digest-bound successor
  only for defective verification on an uncommitted intent, preserving other
  payload semantics, scope, paths, and delta content. `intent_repaired` is not
  readiness: use returned `replacement_intent_id`, `replacement_input_digest`, and
  `replay_argv`; exact replay uses `cognition closeout replay --intent-id <ID>
  --expected-digest <SHA256>`, with any supplied scope matching the intent. Legacy
  scope replay requires a matching blocked receipt. Reinspect after digest drift;
  after replay resume the original closeout and verify its own allowed receipt.
  Do not edit or delete intent JSON, fabricate receipts, bypass the queue, or use
  `mark-dirty`; do not rebuild merely because verification was malformed. If no safe
  action is available, name the exact blocker, needed evidence, and resume action.

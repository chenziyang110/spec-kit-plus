When closeout reports `repair_update_or_replay_intent` or a blocked queued
intent, keep the parent workflow active. Stop retrying the same failing apply
while the intent and cause are unchanged:

1. Execute returned `recovery_argv`, or run
   `{{specify-subcmd:specify-runtime cognition closeout inspect --intent-id <blocked_intent_id> --format json}}`.
   Without `--intent-id`, inspect lists compact pending cards. Select the exact
   `blocked_intent_id`, not the current scope or an inferred latest intent.
   Inspect is read-only and does not require a blocked scope receipt; an absent
   receipt or an older successful receipt is not a reason to use `--scope-dir .`.
2. Check the selected scope, workflow, state, `input_digest`, verification
   diagnostics, and `recommended_next_action`. If inspect offers `replay_argv`
   directly, execute it unchanged; that intent does not require verification
   repair or replacement fields. Otherwise execute an applicable returned
   `repair_argv` unchanged. For a new repair its `cognition closeout repair --intent-id <ID>
   --expected-digest <input_digest> --verification-json - --format json` arguments
   require the complete truthful structured verification array on stdin. Every record
   needs an actual `command`, exact `result`, and optional `artifact`. Never
   invent verification commands or passing results to satisfy validation; run
   needed checks or recover trustworthy evidence first. Do not execute a new
   repair with empty stdin. Only an already journaled repair may resume without
   resupplying evidence when runtime permits it.
3. Repair only replaces defective verification on an uncommitted intent through
   a runtime-archived, digest-bound successor; it preserves other payload
   semantics, scope, paths, and delta content. `closeout_status=intent_repaired`
   is not readiness. Use returned `replacement_intent_id`,
   `replacement_input_digest`, and `replay_argv`; exact replay uses
   `cognition closeout replay --intent-id <ID> --expected-digest <SHA256>`.
   If supplied, a scope must match the intent. Legacy scope replay remains only
   for a matching blocked receipt. Inspect again after digest drift; never
   substitute a new digest without checking the new state.
4. After the older intent is replayed, resume the original closeout
   and verify its own allowed receipt. Do not edit or delete intent JSON,
   fabricate a receipt, bypass the queue, or downgrade it to `mark-dirty`;
   do not rebuild merely because verification was malformed. If no safe action
   is available, report the exact remaining blocker, evidence needed, and resume
   action instead of repeating the same failure or claiming completion.

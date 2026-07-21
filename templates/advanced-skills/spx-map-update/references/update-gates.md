# Incremental update gates

Use the exact changed paths from the runtime or explicit user scope. Pass them
individually to the closeout plan; do not let unrelated dirty work expand the
update boundary. Include `--reason map-update` when supported.

After executing structured `update_argv`, branch on `result_state`:

- `result_state=ready` or `result_state=no_op` requires `validate-build`; only
  `status=ok` and `readiness=query_ready` creates the receipt bound to the
  latest update ID, outcome, and active generation, after which
  `complete-refresh` must consume that receipt; until then the runtime gate
  withholds Compass/query as pending finalization;
- `partial_refresh` or `blocked`: preserve the recorded state and gaps; never
  call `complete-refresh`;
- `needs_rebuild` or legacy `recorded`: preserve the state, never call
  `complete-refresh`, and stop
  with a handoff to `spx-map-rebuild`.

`record-refresh` is a compatibility or explicit metadata-recording entrypoint
only when a matching validation receipt already exists. It is not an ordinary
closeout branch and cannot bypass receipt-bound `complete-refresh`.

Use bounded identity repair only for the affected scope. When the update marks
graph claims stale or contradicted, generic test success cannot re-promote them.
Prepare and apply claim-specific reconciliation only with exact current evidence
and the runtime-returned argv.

Small updates remain leader-direct. Delegate only multiple independent evidence
closures; workers do not publish graph state.

# Incremental update gates

Use the exact changed paths from the runtime or explicit user scope. Pass them
individually to the closeout plan; do not let unrelated dirty work expand the
update boundary. Include `--reason map-update` when supported.

After executing structured `update_argv`, branch on `result_state`:

- `ready` requires passing `validate-build` before `complete-refresh`; validate
  the resulting build/query surface and complete incremental freshness only
  after agreement is proven;
- `no_op` may use `record-refresh` when only freshness metadata must advance;
  otherwise report why nothing changed;
- `partial_refresh` or `blocked`: preserve the recorded state and gaps; never
  call `complete-refresh`;
- `needs_rebuild`: preserve the state, never call `complete-refresh`, and stop
  with a handoff to `spx-map-rebuild`.

Use bounded identity repair only for the affected scope. When the update marks
graph claims stale or contradicted, generic test success cannot re-promote them.
Prepare and apply claim-specific reconciliation only with exact current evidence
and the runtime-returned argv.

Small updates remain leader-direct. Delegate only multiple independent evidence
closures; workers do not publish graph state.

# Build gates

The accepted and validated scan workbench is the sole build input. Build must
not create missing evidence, widen scan scope, or strengthen worker confidence.
Any scan coverage or evidence gap returns to `$spx-map-scan`.

Run `{{specify-subcmd:specify-runtime cognition validate-scan --format json}}`
before `build-from-scan`. If `validate-scan` returns `status=blocked`, stop,
report the exact blocking errors, preserve the runtime's typed recovery signal,
and do not proceed to `build-from-scan`.
Do not say the format issues are harmless or that they do not affect
completeness.

For a V2 workbench, scan validation requires the runtime-owned per-packet
`workbench/acceptance-receipts/<packet-id>.json` and frozen submission digest
before it can issue the generation-level `scan-receipt.json`. Never hand-author
or normalize either receipt layer.

`build-from-scan` deterministically resolves packet evidence into graph nodes,
edges, observations, typed claims, path and alias indexes, lifecycle state, and
published runtime metadata. `validate-build` verifies the database, schema,
indexes, baseline identity, and query readiness. Never reproduce these rules in
a model-authored database or parallel graph.
Even successful construction reports `stage_state=validation_required`,
`completion_allowed=false`, and `completion_gate=validate_build`; it is not a
completion result.

A successful command is insufficient when validation or a representative
Compass route fails. Preserve failed build artifacts for diagnosis and report
the runtime's recovery signal rather than hiding it with incremental update.
A blocked `validate-build` result sets `completion_allowed=false`,
`bypass_allowed=false`, and `error_classification=build_integrity`; it is not
eligible for degraded publication or a completion report.
The runtime-only build chain is `validate-scan -> build-from-scan ->
validate-build -> compass`; do not introduce leader-authored parallel graph
construction lanes or legacy packetized build contracts. Do not write
normalize/rebuild helper scripts.

# Build gates

The accepted and validated scan workbench is the sole build input. Build must
not create missing evidence, widen scan scope, or strengthen worker confidence.
Any scan coverage or evidence gap returns to `$spx-map-scan`.

`build-from-scan` deterministically resolves packet evidence into graph nodes,
edges, observations, typed claims, path and alias indexes, lifecycle state, and
published runtime metadata. `validate-build` verifies the database, schema,
indexes, baseline identity, and query readiness. Never reproduce these rules in
a model-authored database or parallel graph.

A successful command is insufficient when validation or a representative
Compass route fails. Preserve failed build artifacts for diagnosis and report
the runtime's recovery signal rather than hiding it with incremental update.

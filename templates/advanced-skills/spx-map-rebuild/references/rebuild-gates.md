# Rebuild gates

Rebuild only for a first brownfield baseline, missing or unusable database,
unsupported schema, invalid baseline identity, missing required indexes, or an
explicit rebuild request. A localized stale route belongs in `spx-map-update`;
an empty greenfield baseline is not a rebuild reason by itself.

Before scan, respect root and runtime `.cognitionignore`; `.specify/**`, secrets,
vendor/build output, and binary assets must not become graph evidence unless an
explicit supported scope requires them.

Treat the runtime-produced canonical scan set as an already-filtered baseline
universe. Every assigned path must be read by a low-cost worker and represented
by evidence plus `nodes[].paths`. Cost control comes from bounded low-tier
packets and no second model-driven build, not from silently sampling files out
of a reconstruction baseline.

Workers propose evidence-backed nodes with concrete `nodes[].paths`; coverage
alone cannot create `path_index`. Workers may propose claims but cannot publish
or self-promote lifecycle state.

An edge may cross packet boundaries only by naming the external endpoint with
a concrete path from the canonical scan set while keeping at least one endpoint
packet-local. The deterministic build resolves that path after every packet's
nodes have been accepted.

Use `scan-prepare` to create the canonical workbench and queue, then
`scan-accept` to validate and merge each packet-local result. After all packet
acceptance, require `validate-scan`, deterministic
`build-from-scan`, and `validate-build`. Build already publishes the graph and
status; do not run incremental `complete-refresh` as a rebuild finalizer.

The runtime defaults to at most 25 concrete paths per packet for lower-tier
workers. Reduce `--packet-size` further when individual files or evidence
surfaces are unusually large; do not enlarge it merely to reduce lane count.

Preparation never replaces an existing workbench by default. Resume compatible
pending packets; use `scan-prepare --force` only when the old workbench is
explicitly abandoned because it discards both accepted and pending results.

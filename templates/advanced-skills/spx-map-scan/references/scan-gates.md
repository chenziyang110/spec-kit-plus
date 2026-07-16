# Scan gates

Scan only for a first brownfield baseline, missing/unusable database,
unsupported schema, invalid baseline identity, missing required indexes, or an
explicit full rebuild. A localized stale route belongs in `$spx-map-update`.

Respect root and runtime `.cognitionignore`; secrets, vendor/build output,
binaries, and `.specify/**` are not ordinary graph evidence. The runtime's scan
set is the authoritative already-filtered universe. Every assigned path must be
accounted for by a packet result; cost control comes from bounded low-tier
workers, not silent sampling.

`scan-prepare` owns packet IDs, queue, result skeletons, and the canonical
workbench. Preparation never replaces an existing workbench by default. Packet
acceptance must preserve assigned paths, path ledger, evidence, coverage, and
concrete `nodes[].paths`; cross-packet edges may name a concrete external path
but cannot justify reading outside the packet.

Scan completion requires `validate-scan` with ready status. It does not publish
the graph and must not call incremental refresh as a substitute for build.

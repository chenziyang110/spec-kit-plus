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
workbench. It sizes packets by the effective worker context budget after
instruction, inherited-context, reasoning, tool-output, checkpoint,
result-output, and safety reserves. Estimated token cost is the primary packing
constraint; path count and bytes are secondary guards. Preparation never
replaces an existing workbench by default.

When model capacity is known, pass `--context-window-tokens` and the actual
inherited/system-skill/reasoning/tool/result reserves to `scan-prepare`. Use
`--worker-budget-tokens` only for an already-computed effective budget; do not
treat the advertised context window as wholly available scan input.

Drive the workbench only through
`{{specify-subcmd:project-cognition scan-status}}`,
`{{specify-subcmd:project-cognition scan-lease}}`,
`{{specify-subcmd:project-cognition scan-checkpoint}}`,
`{{specify-subcmd:project-cognition scan-yield}}`, and
`{{specify-subcmd:project-cognition scan-accept}}`. The leased packet's
CLI-generated self-contained task brief is authoritative. Dispatch it with the
minimum inherited conversation context the platform permits, and debit any
unavoidable inherited material from the effective budget. Checkpoints preserve
validated packet-local progress. On yield or partial return, the runtime
computes the authoritative remaining set as assigned paths minus
runtime-accepted terminal paths and requeues it for a new subagent. If a worker
is interrupted before yielding, the leader recovers the active lease identity
from `scan-status` and calls `scan-requeue`; no implicit clock-based expiry is
assumed. An oversized packet requires a worker whose effective capacity meets
the estimate plus an explicit `--worker-capacity-tokens` lease override, or
re-planning. Packet
acceptance must preserve assigned paths, path results, evidence, coverage, and
concrete `nodes[].paths`; cross-packet edges may name a concrete external path
but cannot justify reading outside the packet.

Only the runtime may merge or update global queue, handoff, coverage, evidence,
provisional, and status artifacts. Leaders and workers must not hand-write them,
patch SQLite, infer acceptance from natural-language completion claims, or
replace a missing checkpoint with a summary.

Scan completion requires `validate-scan` with ready status. For a v2 workbench,
validation writes `scan-receipt.json` bound to the generation, scan set,
current source-file bytes, and canonical scan artifacts; any later source or
canonical mutation invalidates it. Scan
validation does not publish the graph and must not call incremental refresh as
a substitute for build.

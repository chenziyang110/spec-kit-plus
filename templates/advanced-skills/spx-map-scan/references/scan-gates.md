# Scan gates

Scan only for a first brownfield baseline, missing/unusable database,
unsupported schema, invalid baseline identity, missing required indexes, or an
explicit full rebuild. A localized stale route belongs in `$spx-map-update`.

Respect root and runtime `.cognitionignore`; secrets, vendor/build output,
binaries, and `.specify/**` are not ordinary graph evidence. The runtime's scan
set is the authoritative already-filtered universe. `scan-prepare` applies the
deterministic value classifier and owns `repository-universe.json`,
`scan-targets.json`, and the queue. Audit those projections, but do not
hand-write, rename fields in, or reclassify them. Every assigned path must be
accounted for by a packet result; low-value `P3` paths remain inventory-only
boundary accounting and receive no packet, evidence, or graph-facing coverage.
Auth, security, payment, integration, end-to-end, contract, and smoke
verification paths are deep-read rather than silently sampled.

`scan-prepare` owns packet IDs, queue, result skeletons, and the canonical
workbench. It sizes packets by the effective worker context budget after
instruction, inherited-context, reasoning, tool-output, checkpoint,
result-output, and safety reserves. Estimated token cost is the primary packing
constraint; path count and bytes are secondary guards. Preparation never
replaces an existing workbench by default.
If preparation or status returns
`error_classification=scan_workbench_contract`, preserve its
`recovery_action`, `recovery_detail`, and `recovery_argv`. Back up a legacy or
incompatible workbench before using the returned `scan-prepare --force` action,
and do so only after explicitly abandoning accepted and pending results. Never
hand-edit queue JSON or write a normalization script.

The queue assigned-path union must exactly equal
`scan-targets.json.selected_paths`; `inventory_only_paths` must be disjoint.
`validate-scan` verifies both target projections against the canonical boundary
before it evaluates packet evidence.

When model capacity is known, pass `--context-window-tokens` and the actual
inherited/system-skill/reasoning/tool/result reserves to `scan-prepare`. Use
`--worker-budget-tokens` only for an already-computed effective budget; do not
treat the advertised context window as wholly available scan input.

Drive the workbench only through
`{{specify-subcmd:specify-runtime cognition scan-status}}`,
`{{specify-subcmd:specify-runtime cognition scan-lease}}`,
`{{specify-subcmd:specify-runtime cognition scan-checkpoint}}`,
`{{specify-subcmd:specify-runtime cognition scan-yield}}`, and
`{{specify-subcmd:specify-runtime cognition scan-accept}}`. The leased packet's
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

Every V2 `scan-accept` or accepted `scan-yield` freezes the submitted partial
result under `workbench/accepted-submissions/` and creates a digest-bound
`workbench/acceptance-receipts/<packet-id>.json` for its generation, packet,
attempt, sequence, submission, and canonical result. `validate-scan` requires
both runtime-owned surfaces. Never hand-author, copy, normalize, or repair
them; absence or digest/identity drift is an evidence-integrity blocker.

Only the runtime may merge or update global queue, handoff, coverage, evidence,
provisional, and status artifacts. Leaders and workers must not hand-write them,
patch SQLite, infer acceptance from natural-language completion claims, or
replace a missing checkpoint with a summary.

`scan-status status=ok` is workbench control health, not completion. After every
packet is accepted it reports `stage_state=validation_required`,
`completion_allowed=false`, and `completion_gate=validate_scan`.

Scan completion requires `validate-scan` with `status=ok` and
`readiness=scan_ready`. If validation returns `status=blocked`, treat schema,
identity, path-accounting, and evidence-reference defects as evidence-integrity
blockers. The machine result sets `completion_allowed=false`,
`bypass_allowed=false`, and
`error_classification=scan_evidence_integrity`; report the typed recovery action
and stop. Do not call them harmless format issues, hand off to build, normalize
the artifacts with a helper script, or bypass the gate.

For a v2 workbench, successful validation writes `scan-receipt.json` bound to
the generation, scan set, current source-file bytes, and canonical scan
artifacts; any later source or canonical mutation invalidates it. Scan
validation does not publish the graph and must not call incremental refresh as
a substitute for build.

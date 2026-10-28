# Scan gates

Scan only for a first brownfield baseline, missing/unusable database,
unsupported schema, invalid baseline identity, missing required indexes, or an
explicit full rebuild. A localized stale route belongs in `$spx-map-update`.

Respect root and runtime `.cognitionignore`; secrets, vendor/build output,
binaries, and `.specify/**` are not ordinary graph evidence. The runtime's scan
set is the authoritative already-filtered universe. `scan-formats` groups that
universe by detected format, family, path kind, top-level directory, and Git
state, with aggregate counts and at most three representatives per cohort. The
Agent proposes one cohort-level policy over every runtime-issued `cohort_id`;
it may select known or custom code for semantic scan, sample uncertainty, and
leave non-code inventory-only or excluded. It cannot submit path overrides.
`scan-policy-stage` validates exact cohort coverage, and
`scan-policy-confirm` activates only the exact user-confirmed policy digest.
Inventory drift while a proposal is staged, tampering, incompleteness, or
`split_required` blocks preparation until a new or refined proposal is
confirmed. After confirmation, content or membership drift inside a known
stable cohort reuses its decision; a newly observed cohort requires review and
confirmation.

`scan-prepare` detects file format before value classification and owns
`repository-universe.json`, `scan-targets.json`, and the queue. It requires the
confirmed policy and freezes that inventory and policy into the workbench.
Audit those projections, but do not hand-write, rename fields in, or reclassify
them. Directory and Git metadata remain guardrails: they may demote known
artifact families but cannot prove an unknown path is code. Every assigned path must be
accounted for by a packet result; low-value `P3` paths remain inventory-only
boundary accounting and receive no packet, evidence, or graph-facing coverage.
Auth, security, payment, integration, end-to-end, contract, and smoke
verification paths are deep-read rather than silently sampled.

`scan-prepare` owns packet IDs, queue, result skeletons, and the canonical
workbench. It sizes packets by the effective worker context budget after
instruction, inherited-context, reasoning, tool-output, checkpoint,
result-output, and safety reserves. Estimated token cost is the primary packing
constraint; path count and bytes are secondary guards. Preparation never
replaces incompatible or in-progress workbench state by default.

Preparation has two reuse layers. An identical `preparation_digest` resumes the
current workbench. After successful `validate-scan`, the runtime keeps validated
path-scope row bundles under its persistent cognition cache, keyed by source
SHA-256, effective per-path policy, result/workbench contract, and graph schema.
On a later generation it creates fresh `reuse-*` packet, attempt, acceptance,
and scan receipts; old queue or receipt identity is never copied. A source,
policy, or contract miss queues that whole dependency scope, and a cross-path
edge joins both endpoint scopes. Workers must materialize shared nodes,
cross-path edges, and multi-path evidence or claims; unrecorded coupling cannot
participate in invalidation. Cache lineage must cover every current accepted
packet/path before automatic generation replacement; older cache cannot discard
newer unvalidated work. Dispatch only the returned
`pending_path_count`. `--force` replaces incompatible current state
but retains eligible validated cache; `--full-rebuild` is the explicit cache
bypass.

If preparation or status returns
`error_classification=scan_workbench_contract`, preserve its
`recovery_action`, `recovery_detail`, and `recovery_argv`. Back up a legacy or
incompatible workbench before using the returned `scan-prepare --force` action,
and do so only after explicitly abandoning accepted and pending workbench
results. Never
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
`error_classification=scan_evidence_integrity`; keep build handoff suspended and
execute authorized stage-local typed recovery, repair and reaccept affected
packets, then rerun validation in the same invocation. Do not call them harmless format issues, hand off to build, normalize
the artifacts with a helper script, or bypass the gate.

For a v2 workbench, successful validation writes `scan-receipt.json` bound to
the generation, scan set, current source-file bytes, and canonical scan
artifacts; any later source or canonical mutation invalidates it. Scan
validation does not publish the graph and must not call incremental refresh as
a substitute for build.

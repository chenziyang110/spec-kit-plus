---
name: spx-map-scan
description: Low-cost specify-runtime cognition scan workflow for advanced coding models. Use when a new or explicitly rebuilt baseline needs canonical repository evidence before deterministic graph construction.
---

# SPX Map Scan

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` before dispatching scan workers.
Read `references/project-cognition.md` for its evidence boundary, then
`references/scan-gates.md` and `references/scan-worker.md`. Do not run Compass
intake while the baseline is missing or invalid. This skill writes only
cognition scan/workbench artifacts; product source remains read-only.

Confirm scan/rebuild need with
`{{specify-subcmd:specify-runtime cognition status --format json}}`. Then:

1. Run `{{specify-subcmd:specify-runtime cognition generate-ignore --format json}}`.
   If it returns `review_required=true`, obtain user review before scanning. Use
   `{{specify-subcmd:specify-runtime cognition confirm-ignore --all-suggested --format json}}`
   only when every returned suggestion was approved; otherwise pass the approved
   subset through repeated exact `--pattern` flags. Require
   `status=confirmed`; chat confirmation alone does not activate a rule, and the
   leader must not open or edit the runtime-owned ignore file. A created starter
   with `review_required=false` needs no confirmation.
2. Create the canonical boundary with
   `{{specify-subcmd:specify-runtime cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json}}`.
   Never substitute raw repository globs.
3. Run `{{specify-subcmd:specify-runtime cognition scan-formats --format json}}`.
   The runtime inventories every repository-specific format cohort with aggregate
   counts and at most three representative paths.
4. The Agent proposes cohort-level decisions for every runtime-issued
   `cohort_id`: `semantic_scan`, `sample`, `inventory_only`, `exclude`, or
   `split_required`. It must not submit path-level overrides. Submit the exact,
   complete proposal with
   `{{specify-subcmd:specify-runtime cognition scan-policy-stage --proposal-json '<inline-json>' --format json}}`.
5. Present the staged summary, reasons, and bounded representatives. Wait until
   the user confirms the exact `proposal_digest`, then run
   `{{specify-subcmd:specify-runtime cognition scan-policy-confirm --proposal-digest <exact-digest> --format json}}`.
   Chat approval alone is not an active policy. Refine `split_required` before
   confirmation. If staging/confirmation reports `format inventory changed`,
   restart at `scan-formats`. A confirmed decision remains reusable for content
   or membership drift inside the same stable cohort; a newly reported cohort
   requires a new proposal and exact confirmation.
6. Run
   `{{specify-subcmd:specify-runtime cognition scan-prepare --scan-set .specify/project-cognition/tmp/scan-files.json --format json}}`.
   scan-prepare requires the confirmed policy and rejects missing, tampered,
   stale, or incomplete policy state.
   Resume a compatible queue: the same `preparation_digest` preserves current
   accepted/pending work. After a validated scan, matching source SHA-256,
   effective policy, and scan contract replay path-scope bundles into new
   generation-bound `reuse-*` packets; dispatch only `pending_path_count`.
   Cross-path edges share one invalidation scope; require workers to materialize
   shared nodes, edges, and multi-path evidence or claims so invalidation can
   see the coupling. Cache lineage must cover every current accepted
   packet/path before automatic generation replacement; older cache cannot
   discard newer unvalidated work. Old packet/attempt/receipt identity is never
   reused. Use
   `--force` only after explicitly abandoning the old workbench: its accepted
   and pending results are discarded, though validated cache may still be
   replayed. Use `--full-rebuild`
   only for an explicit no-reuse rebuild. Give
   the runtime the selected worker/model capacity when supported. It must pack
   by effective context budget and estimated token cost, with path count and
   bytes only as secondary guards.
   The baseline serves code navigation: ordinary untracked source stays
   eligible, while untracked `.gitignore` matches, local runtime
   vendor/data/log payloads, and generated agent/workflow artifacts default to
   `P3` inventory-only. Use `--include-gitignored` only after reviewing a
   genuinely required ignored source path; it does not promote known artifact
   families.
   The runtime detects special filenames, extensions, and shebangs before value
   ranking. Directory/Git state is a guardrail, not source-code proof. The
   confirmed cohort policy may select known or custom code for semantic scan,
   sample uncertainty, and leave non-code inventory-only or excluded.
7. Keep the advanced model as leader. Inspect
   `{{specify-subcmd:specify-runtime cognition scan-status --format json}}`, use
   `{{specify-subcmd:specify-runtime cognition scan-lease --worker-id <worker-id> --format json}}` to claim one prepared
   packet/attempt, and dispatch its CLI-generated self-contained task brief with
   `references/scan-worker.md` to the lowest-cost capable worker/model. The
   leader owns boundaries and escalation—not bulk reads or scheduler state.
   Limit every wave to currently available worker slots. The runtime caps
   `recommended_parallel_workers` at four, and the platform may require a
   smaller wave; pending packet count is not permission to oversubscribe the
   agent runtime.
   Never dispatch a packet whose estimate exceeds that worker's effective
   capacity. An oversized packet requires a sufficiently capable worker and an
   explicit `--worker-capacity-tokens <tokens>` lease override, or re-planning.
8. Require useful packet-local progress through
   `{{specify-subcmd:specify-runtime cognition scan-checkpoint}}`. A worker nearing
   context/tool/result capacity must checkpoint completed work and call
   `{{specify-subcmd:specify-runtime cognition scan-yield}}`; the runtime preserves
   accepted progress, computes the remaining paths, and requeues them for a new
   subagent. If a worker stops before yielding, recover its packet/attempt from
   compact `scan-status` and call `scan-requeue`; then lease the exact remainder
   to a new worker.
9. Accept a complete returned attempt with
   `{{specify-subcmd:specify-runtime cognition scan-accept --packet-id <packet-id> --attempt-id <attempt-id> --format json}}`.
   Repair or escalate rejected packets through the runtime. Repeat
   `scan-status -> scan-lease -> checkpoint/yield/accept` until no pending,
   leased, yielded, or blocked high-value packet remains.
10. Run `{{specify-subcmd:specify-runtime cognition validate-scan --format json}}` and
   repair every blocking coverage/evidence gap.

If a prepared packet cannot be dispatched safely, preserve the queue, repair
the packet or invocation, join capacity-limited work, and resume or redispatch a
safe serial worker in this invocation. Only if no safe authorized recovery
remains, persist `subagent_blocked` through the runtime in the canonical workbench
state and gap/coverage surfaces with packet, blocked scope, owner,
`recovery_condition`, and exact resume action. Do not replace the missing worker with leader bulk reads or
discard accepted/pending packet state. The leader and workers must not hand-edit
global queue, handoff, coverage, evidence, provisional, status, or SQLite
surfaces; only runtime commands may mutate them.

Stop when validation reports the scan package ready. Do not run
`build-from-scan`, publish a database, or claim the cognition baseline is
queryable. This invocation authorizes only this workflow stage. Hand off to
`$spx-map-build`, but do not invoke `$spx-map-build`; the explicit
`$spx-map-rebuild` orchestrator owns that continuation when it was the
user-authorized entrypoint.

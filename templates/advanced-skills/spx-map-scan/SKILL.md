---
name: spx-map-scan
description: Low-cost specify-runtime cognition scan workflow for advanced coding models. Use when a new or explicitly rebuilt baseline needs canonical repository evidence before deterministic graph construction.
---

# SPX Map Scan

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md` for its evidence boundary, then
`references/scan-gates.md` and `references/scan-worker.md`. Do not run Compass
intake while the baseline is missing or invalid. This skill writes only
cognition scan/workbench artifacts; product source remains read-only.

Confirm scan/rebuild need with
`{{specify-subcmd:specify-runtime cognition status --format json}}`. Then:

1. Run `{{specify-subcmd:specify-runtime cognition generate-ignore --format json}}`.
   If it creates an ignore file, obtain user review before scanning.
2. Create the canonical boundary with
   `{{specify-subcmd:specify-runtime cognition scan-set --out .specify/project-cognition/tmp/scan-files.json --format json}}`.
   Never substitute raw repository globs.
3. Run
   `{{specify-subcmd:specify-runtime cognition scan-prepare --scan-set .specify/project-cognition/tmp/scan-files.json --format json}}`.
   Resume a compatible queue. Use `--force` only after explicitly abandoning
   the old workbench, because accepted and pending results are discarded. Give
   the runtime the selected worker/model capacity when supported. It must pack
   by effective context budget and estimated token cost, with path count and
   bytes only as secondary guards.
4. Keep the advanced model as leader. Inspect
   `{{specify-subcmd:specify-runtime cognition scan-status --format json}}`, use
   `{{specify-subcmd:specify-runtime cognition scan-lease --worker-id <worker-id> --format json}}` to claim one prepared
   packet/attempt, and dispatch its CLI-generated self-contained task brief with
   `references/scan-worker.md` to the lowest-cost capable worker/model. The
   leader owns boundaries and escalation—not bulk reads or scheduler state.
   Limit every wave to currently available worker slots; pending packet count
   is not permission to oversubscribe the agent runtime.
   Never dispatch a packet whose estimate exceeds that worker's effective
   capacity. An oversized packet requires a sufficiently capable worker and an
   explicit `--worker-capacity-tokens <tokens>` lease override, or re-planning.
5. Require useful packet-local progress through
   `{{specify-subcmd:specify-runtime cognition scan-checkpoint}}`. A worker nearing
   context/tool/result capacity must checkpoint completed work and call
   `{{specify-subcmd:specify-runtime cognition scan-yield}}`; the runtime preserves
   accepted progress, computes the remaining paths, and requeues them for a new
   subagent. If a worker stops before yielding, recover its packet/attempt from
   compact `scan-status` and call `scan-requeue`; then lease the exact remainder
   to a new worker.
6. Accept a complete returned attempt with
   `{{specify-subcmd:specify-runtime cognition scan-accept --packet-id <packet-id> --attempt-id <attempt-id> --format json}}`.
   Repair or escalate rejected packets through the runtime. Repeat
   `scan-status -> scan-lease -> checkpoint/yield/accept` until no pending,
   leased, yielded, or blocked high-value packet remains.
7. Run `{{specify-subcmd:specify-runtime cognition validate-scan --format json}}` and
   repair every blocking coverage/evidence gap.

If no capable worker is available or a prepared packet cannot be dispatched
safely, preserve the prepared queue and persist `subagent_blocked` in the
canonical workbench state and gap/coverage surfaces with packet, blocked scope,
owner, and `recovery_condition`. Keep the workbench resumable and stop with that
recovery action. Do not replace the missing worker with leader bulk reads or
discard accepted/pending packet state. The leader and workers must not hand-edit
global queue, handoff, coverage, evidence, provisional, status, or SQLite
surfaces; only runtime commands may mutate them.

Stop when validation reports the scan package ready. Do not run
`build-from-scan`, publish a database, or claim the cognition baseline is
queryable. This invocation authorizes only this workflow stage. Hand off to
`$spx-map-build`, but do not invoke `$spx-map-build`; the explicit
`$spx-map-rebuild` orchestrator owns that continuation when it was the
user-authorized entrypoint.

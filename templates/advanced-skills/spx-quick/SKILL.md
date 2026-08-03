---
name: spx-quick
description: Tracked direct-delivery workflow for advanced coding models. Use when non-trivial work of any size needs resumable planning, implementation, and verification without first creating a formal feature specification.
---

# SPX Quick

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `implement`.
Read `references/run-bootstrap.md`.
Read `references/human-confirmation.md`, then `references/task-contract.md`.
Read `references/worker-contract.md` only
when delegating. Read `references/consequence-gate.md` when work can affect
lifecycle operations, running objects, concurrent work, destructive behavior,
shared state, downstream consumers, compatibility, security-sensitive behavior,
or multiple plausible product behaviors.
Read `references/ui-quality-gate.md` for any user-visible UI change.

`$spx-quick` always starts a new run. Record that new run with `specify-runtime run create`, then execute only through `specify-runtime run supervise`; do not resume another workflow's run.

Accept non-trivial direct-delivery work whose outcome can be confirmed at the
Quick Checkpoint. Task size, capability count, architecture, migration,
compatibility, rollout, shared-state impact, and acceptance depth do not limit
Quick eligibility. Route unknown failure mechanisms to `$spx-debug`; do not
route to `$spx-specify` because the implementation grows. That formal
specification workflow is a separate user-selected path.
Quick can handle larger tasks through deeper task-local planning, multiple
batches, explicit joins, and acceptance coverage, including multi-capability
work.
Record every consequence obligation in `STATUS.md` or referenced task-local
`PLAN.md` with affected objects, recovery, verification, and stop conditions.
Broad consequences increase planning, batching, and evidence depth inside
Quick; do not shrink the request or hand it to `$spx-specify`.

Query `.specify/memory/constitution.md` through `specify-runtime artifact show` as governance. Consume project rules and
task-relevant Learning only through the project-learning CLI intake.

Create new state deterministically with
`{{specify-subcmd:specify-runtime artifact scaffold --kind quick-status --path ".planning/quick/<id>-<slug>/STATUS.md" --vars "<compact-json>"}}`
and fill only the returned semantic anchors. Resume an existing
`.planning/quick/<id>-<slug>/STATUS.md` instead of replacing it. Use the project launcher-backed
`{{specify-subcmd:specify-runtime quick list}}`, `{{specify-subcmd:specify-runtime quick status <id>}}`, and
`{{specify-subcmd:specify-runtime quick resume <id>}}` helpers for deterministic discovery.
Keep state compact and ask the user only for decisions the repository cannot
supply.

Initialize or preserve the unconfirmed intake state and render the Quick card
from `references/human-confirmation.md`. For applicable UI work, append its UI
implementation proposal, then ask once for both decisions. Wait for user
confirmation before broad source or test reads, delegation, implementation, or
validation. Persist the main and UI confirmations separately only after
confirmation; keep the technical execution plan agent-owned.

When intake names `.specify/discussions/<slug>/handoff-to-specify.json`, query it through `specify-runtime artifact show` and consume
it only when it is handoff-ready, its digests are current, it has zero blocking
decisions, and `consumer_eligibility.sp-quick.status: ready`, except for the
legacy size/breadth-only override below. With no semantic
delta, bind confirmation to the handoff review digest; otherwise present the
changed checkpoint. A legacy size-, capability-, architecture-, migration-,
acceptance-, or consequence-breadth-only Quick block is obsolete routing advice:
keep the source immutable, present a fresh Quick checkpoint bound to its digest,
and continue only after the user's explicit Quick confirmation. Return to
discussion for an unconfirmed, contradictory, or decision-blocked contract.
Honor `$spx-specify` only when the user explicitly selected the formal spec-first
path, not as an automatic upgrade.
After binding a confirmed discussion contract and its `review_digest` into the
Quick `STATUS.md`, run
`{{specify-subcmd:specify-runtime discussion mark-consumed <slug> --feature-dir <quick-workspace>}}`.
The `--feature-dir` spelling is retained for compatibility and accepts the Quick
workspace; do not mark consumption before the binding evidence exists.

Inspect the current diff and cognition-selected paths, then implement the full
confirmed scope. When durable planning no longer fits compact state, create an
absent task-local `PLAN.md` with `specify-runtime artifact scaffold --kind
quick-plan`, query it on resume, and patch only named sections; never submit or
reconstruct the whole plan. Scale that plan, dependency-aware lanes, and
multiple ready batches to the workload. Delegate only independent lanes that
improve throughput or confidence; do not manufacture packets for leader-direct work. A behavior
change must run and record RED before production edits. If no reliable
automated surface exists, build the smallest viable harness as its own Quick
lane or batch; if that work is concretely blocked, record the blocker rather
than replacing evidence with a `$spx-specify` handoff. For a propagating change, record a minimal sweep before
editing and prove full affected-surface or callsite coverage across consumers,
generated/mirrored copies, registrations, and verification entry points;
sampling or an unverified surface leaves the task blocked.

For UI work, record design sources, affected states/viewports, visual
acceptance, direction source/signature, reference intents, real content/image
sources, and the structure/visual/runtime evidence triad in `STATUS.md`. Preserve original visual references and
run the UI gate's real-entrypoint capture/inspect/refine loop. Escalate a new
visual direction to `$spx-design`. Keep multi-surface or acceptance-heavy UI in
Quick and expand its task-local plan, batches, viewport/state matrix, and
evidence; do not shrink the UI outcome.

Patch `STATUS.md` at meaningful transitions through leased `specify-runtime artifact patch` calls. Create an absent `SUMMARY.md` with `artifact scaffold --kind quick-summary`, query it on resume, and patch only its named terminal sections through fresh leases; never submit or reconstruct the whole summary. Close with
`{{specify-subcmd:specify-runtime quick close <id>}}` only after terminal truth is recorded;
archive later only with `{{specify-subcmd:specify-runtime quick archive <id>}}`.
After verified repository changes, run
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-quick --intent implement --format json}}`
with explicit workflow-owned paths, fill returned agent-owned fields, and execute
structured `update_argv`. Apply the receipt-bound finalizer gate in
`references/project-cognition.md` before any clean claim. Report changed paths, evidence, and remaining risk. This invocation
authorizes only this workflow stage; report any explicit user-selected workflow
change as a handoff and do not invoke another workflow in this run.

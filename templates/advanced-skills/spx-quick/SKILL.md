---
name: spx-quick
description: Lean tracked-change workflow for advanced coding models. Use when work is small but non-trivial and needs lightweight scope, resumability, implementation, and verification without a full feature specification.
---

# SPX Quick

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `implement`.
Read `references/human-confirmation.md`, then `references/task-contract.md`.
Read `references/worker-contract.md` only
when delegating. Read `references/consequence-gate.md` when work can affect
lifecycle operations, running objects, concurrent work, destructive behavior,
shared state, downstream consumers, compatibility, security-sensitive behavior,
or multiple plausible product behaviors. Resolve `assets/` paths relative to
this Skill.
Read `references/ui-quality-gate.md` for any user-visible UI change.

Accept bounded work that is too coupled or uncertain for `$spx-fast` but does
not need feature-level requirements and architecture. Route unresolved failures
to `$spx-debug` and acceptance-heavy or multi-capability work to
`$spx-specify`.
Record bounded consequence obligations in `STATUS.md` with their affected
objects, recovery, verification, and stop conditions. Route unbounded
consequences to `$spx-specify`; do not shrink them to remain quick.

Read `.specify/memory/constitution.md` as governance. Consume project rules and
task-relevant Learning only through the project-learning CLI intake.

Create new state deterministically with
`{{specify-subcmd:artifact scaffold --kind quick-status --out ".planning/quick/<id>-<slug>/STATUS.md" --vars "<compact-json>" --format json}}`
and fill only the returned semantic anchors. Resume an existing
`.planning/quick/<id>-<slug>/STATUS.md` instead of replacing it. The bundled
`assets/status.md` remains a compatibility example, not the authoritative
scaffold. Use the project launcher-backed
`{{specify-subcmd:quick list}}`, `{{specify-subcmd:quick status <id>}}`, and
`{{specify-subcmd:quick resume <id>}}` helpers for deterministic discovery.
Keep state compact and ask the user only for decisions the repository cannot
supply.

Initialize or preserve the unconfirmed intake state and render the Quick card
from `references/human-confirmation.md`. For applicable UI work, append its UI
implementation proposal, then ask once for both decisions. Wait for user
confirmation before broad source or test reads, delegation, implementation, or
validation. Persist the main and UI confirmations separately only after
confirmation; keep the technical execution plan agent-owned.

When intake names `.specify/discussions/<slug>/handoff-to-specify.json`, consume
it only when it is handoff-ready, its digests are current, it has zero blocking
decisions, and `consumer_eligibility.sp-quick.status: ready`. With no semantic
delta, bind confirmation to the handoff review digest; otherwise present the
changed checkpoint. If the handoff selects `$spx-specify` or must return to
discussion, hand off and stop rather than switching workflows inline.

Inspect the current diff and cognition-selected paths, then implement the full
bounded scope. Delegate only independent lanes that improve throughput or
confidence; do not manufacture packets for leader-direct work. A behavior
change must run and record RED before production edits. If no reliable
automated surface exists, build a bounded harness or hand off to
`$spx-specify` and stop. For a propagating change, record a minimal sweep before
editing and prove full affected-surface or callsite coverage across consumers,
generated/mirrored copies, registrations, and verification entry points;
sampling or an unverified surface leaves the task blocked.

For bounded UI work, record design sources, affected states/viewports, visual
acceptance, direction source/signature, reference intents, real content/image
sources, and the structure/visual/runtime evidence triad in `STATUS.md`. Preserve original visual references and
run the UI gate's real-entrypoint capture/inspect/refine loop. Escalate a new
visual direction to `$spx-design` and multi-surface or acceptance-heavy UI to
`$spx-specify`; do not shrink the UI outcome to remain quick.

Update `STATUS.md` at meaningful transitions and render `SUMMARY.md` from
`assets/summary.md` on completion or blockage. Close with
`{{specify-subcmd:quick close <id>}}` only after terminal truth is recorded;
archive is a separate explicit action.
After verified repository changes, close out cognition with canonical workflow
`quick`. Report changed paths, evidence, and remaining risk. This invocation
authorizes only this workflow stage; report any escalation as a handoff and do
not invoke another workflow in this run.

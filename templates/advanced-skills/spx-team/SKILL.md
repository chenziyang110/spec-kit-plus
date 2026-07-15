---
name: spx-team
description: Codex teams runtime entrypoint for advanced coding models. Use when the operator needs to inspect, diagnose, resume, watch, or manage the supported durable team surface rather than execute a feature workflow.
---

# SPX Team

Read `references/project-cognition.md` for its evidence boundary and
`references/runtime-boundary.md`. Do not run cognition intake for pure runtime
status or lifecycle operations; use it only when the question includes
repository impact or workflow routing.

This skill operates the Codex-only runtime; it does not replace
`$spx-implement-teams`. Start with `{{specify-subcmd:sp-teams status}}`. Use
`{{specify-subcmd:sp-teams doctor}}` for configuration/state diagnostics and
`{{specify-subcmd:sp-teams live-probe}}` only when install or runtime health
needs an active proof.

Inspection and diagnosis authorize only `status` and `doctor`. Never run
`live-probe` implicitly: it may create transient runtime state and requires
explicit operator authorization.

Perform the explicit runtime action requested by the operator—status, watch,
await, resume, sync-back, shutdown, or cleanup—after checking its help and
current state. Prefer recovery-preserving actions. Do not dispatch feature work
without a validated implementation task packet, do not clean active state, and
do not claim this backend exists for an integration where the launcher reports
it unavailable.

Report the runtime state and supported next action. Route ready feature
execution to `$spx-implement-teams` and ordinary bounded parallelism to
`$spx-implement` as explicit handoffs. This invocation authorizes only this
workflow stage; do not invoke another workflow in this run.

---
name: spx-review
description: Advanced system review and repair workflow. Use after implementation to prove the product starts from its real entrypoint, completes required user journeys, has no disconnected controls or registrations, and is ready for human acceptance.
---

# SPX Review

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/workflow-runtime.md` and let its CLI own phase state. Read
`references/project-cognition.md`, using cognition intent `implement`. Read
`references/review-contract.md`; read `references/worker-contract.md` only when
delegating. Read `references/ui-quality-gate.md` for UI-bearing scenarios and
`references/blocker-resolution.md` when a blocked exit becomes possible.

Resolve exactly one implementation-complete feature. Require a trusted
`implementation-handoff.json`, current implementation evidence, and the
official real entrypoint. Transition from the validated `implement` stage into
`review` through the workflow runtime before editing review state, source, or
tests. Then run
`{{specify-subcmd:review prepare --feature-dir <feature-dir> --expected-revision <revision> --format json}}`.
Treat the resulting `review-state.json` as the canonical resumable Review state;
do not reconstruct its stable schema from prose.

On an uncertain or terminal-looking resume, run
`{{specify-subcmd:review resume-audit --feature-dir <feature-dir> --format json}}`
before reusing evidence or editing. Continue from its exact scenario/finding
cursor and repair every reported freshness gap.

This is a mandatory system-level usability and wiring gate, not a second copy
of task-level code review. Prove that the integrated product starts, becomes
ready, exposes every required user journey, and produces the expected
observable result. Inspect the complete path when applicable: button or command
to route, handler/controller, service or provider, persistence/external
dependency, and user-visible feedback. Detect implemented-but-unused code,
unregistered routes or providers, dead controls, broken navigation, missing
state propagation, and blocking runtime diagnostics.

Execute every required scenario from its real entrypoint. UI-bearing scenarios
must capture fresh integrated `structure_snapshot`, `visual_capture`, and
`runtime_diagnostics` evidence and visually inspect the required states. Passing
unit tests, existing files, synthetic-only checks, or an isolated component do
not prove the product works.

Use adaptive execution. The leader owns the running instance, ports, test data,
scenario cursor, findings, repair acceptance, and final verdict. Delegate only
independent bounded audits or disjoint repair writes through a just-in-time
`SystemReviewPacket`; a worker cannot declare the whole product passed. Keep
shared browser, database, account, and runtime-instance journeys serial. After
all joins, inspect the integrated diff and restart the official entrypoint.

Record every failure as a finding. Repair an understood, bounded defect inside
the approved implementation scope, add or strengthen regression coverage, and
rerun the exact failed journey plus affected scenarios. Hand off an unknown
mechanism to `$spx-debug` and stop; after diagnosis, resume this Review at the
preserved scenario. Reopen `$spx-implement`, `$spx-tasks`, `$spx-plan`,
`$spx-specify`, or `$spx-design` only when the finding belongs to that upstream
owner. Do not hide missing implementation by reducing the Review matrix.

Do not push, deploy, trigger protected CI, use production data, or perform an
external write without explicit authority. Exhaust safe local recovery first;
when required external or human evidence remains unavailable, persist the full
structured blocker and exact Review resume point.

Before approval, run fresh integrated regression from a restarted entrypoint,
then run
`{{specify-subcmd:review validate --feature-dir <feature-dir> --format json}}`.
Approval requires every mandatory scenario passed, zero blocking findings,
required evidence present, clean blocking diagnostics, and a fresh final source
fingerprint after all Review repairs. Copy validation's `current_fingerprint`
into `final.reviewed_snapshot_sha256` before setting `status: approved`; never
invent or reuse that digest. Any later production or configuration
change makes the verdict stale.

After verified Review-owned changes, close out cognition with canonical
workflow `review`, then run
`{{specify-subcmd:review closeout --feature-dir <feature-dir> --expected-revision <revision> --format json}}`.
Execute only the successful response's revision-bound workflow completion argv.
Recommend `$spx-accept` and stop; do not run human acceptance inline. Never
claim completion from worker reports, stale evidence, skipped required
scenarios, or unresolved blocking findings.

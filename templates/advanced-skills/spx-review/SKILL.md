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

Compile the Review Universe from authoritative obligations, handoff scenarios,
changed consumer surfaces, runtime-discovered controls/registrations, and
affected regression paths. Use independent coverage discovery so an omission
in the supplied matrix cannot silently narrow Review. The leader orchestrates
subagents through a read-only Review/Audit wave, joins and reconciles every
result, then requires zero uncovered obligations and surfaces before approval.
An audit worker cannot declare coverage complete or edit product code.

After the audit join, run an independent Fix wave. The leader gives Fix workers
accepted finding ids, authoritative expected behavior, bounded non-overlapping
write scopes, forbidden truth artifacts, and exact regression obligations.
Every approved-scope defect stays inside Review regardless of repair size:
missing code, a task omission, incomplete tests, broken wiring, and an unknown
root cause are not reasons to exit. For an unknown root cause, dispatch a
read-only diagnostic packet; Review remains the stage owner, accepts the
diagnosis, and directs its own Fix worker. Keep shared browser, database,
account, registry, and runtime-instance writes serial.

Join and inspect every repair result, restart the integrated product, and run
an independent revalidation wave over the failed journey, dependency paths,
and credible regression set. A repair author must not verify its own finding;
the leader or a different read-only subagent performs revalidation. The leader
owns the running instance, ports, test data, coverage reconciliation, all
packet joins, repair acceptance, and final verdict.

Only a proven upstream truth gap permits a handoff: missing or contradictory
requirement truth routes to `$spx-specify`, missing or contradictory design
truth routes to `$spx-design`, and architecture truth that must change before
any conforming fix routes to `$spx-plan`. Missing code is not an upstream truth
gap. Do not hide omitted implementation by reducing the Review Universe.

Do not push, deploy, trigger protected CI, use production data, or perform an
external write without explicit authority. Exhaust safe local recovery first;
when required external or human evidence remains unavailable, persist the full
structured blocker and exact Review resume point.

Before approval, run fresh integrated regression from a restarted entrypoint,
then run
`{{specify-subcmd:review validate --feature-dir <feature-dir> --format json}}`.
Approval requires the Review Universe at zero uncovered, all packets joined,
every mandatory scenario passed, zero blocking findings, required evidence
present, clean blocking diagnostics, and a fresh final source fingerprint after
all Review repairs. Copy validation's `current_fingerprint`
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

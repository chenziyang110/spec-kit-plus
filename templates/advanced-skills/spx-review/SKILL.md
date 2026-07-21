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
official real entrypoint. Initial Review transitions from validated `implement`;
an acceptance repair arrives through CLI-owned `accept route-repair` with
`review` already active. Then run
`{{specify-subcmd:review prepare --feature-dir <feature-dir> --expected-revision <revision> --format json}}`.
Treat the resulting `review-state.json` as the canonical resumable Review state;
do not reconstruct its stable schema from prose. An acceptance repair must
create the next cycle bound to the previous approved Review digest and routed
finding; never edit or reapprove the old cycle.

Continue the validation-epoch ledger shared across Implement and Review; do not
reset it on phase entry, resume, worker dispatch, or Review-cycle creation. The
combined flow permits at most three heavyweight epochs, each bound to one source
fingerprint. Before executing tests, builds, startup, E2E, real scenarios, or UI
capture, the Leader opens the next available epoch. Multiple commands and
read-only observation slices against that fingerprint share it. The third failed
epoch blocks with exact evidence and recovery criteria; never start a fourth.

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

Execute every required scenario from its official real entrypoint inside the
current Leader-owned epoch. UI-bearing scenarios
must capture fresh integrated `structure_snapshot`, `visual_capture`, and
`runtime_diagnostics` evidence and visually inspect the required states. Passing
unit tests, existing files, synthetic-only checks, or an isolated component do
not prove the product works. Group capture by integrated surface and source
fingerprint; do not run the full viewport/state capture loop per Txx.

Compile the Review Universe from authoritative obligations, handoff scenarios,
changed consumer surfaces, runtime-discovered controls/registrations, and
affected regression paths. Use independent coverage discovery so an omission
in the supplied matrix cannot silently narrow Review. The leader orchestrates
subagents through a read-only Review/Audit wave inside the already-open epoch,
joins and reconciles every
result, then requires zero uncovered obligations and surfaces before approval.
An audit worker cannot declare coverage complete or edit product code. In an
acceptance repair cycle, an accepted read-only diagnostic Review assignment
must own the routed observation. Record its packet lane as `diagnostic`, but
persist the `review-state.json` assignment with `kind: scenario_review` and
`read_only: true`; `diagnostic` is not a state kind. Store new scenario evidence under
`review-evidence/cycle-<n>/` and packet/results under
`review-results/cycle-<n>/`; earlier-cycle evidence cannot close the new cycle.

After the audit join, run an independent Fix wave only when another validation
epoch remains. The leader gives Fix workers
accepted finding ids, authoritative expected behavior, bounded non-overlapping
write scopes, forbidden truth artifacts, cheap task checks, and exact regression
obligations. Fix workers return test impact and must not independently execute a
heavyweight gate per Txx.
Every approved-scope defect stays inside Review regardless of repair size:
missing code, a task omission, incomplete tests, broken wiring, and an unknown
root cause are not reasons to exit. For an unknown root cause, dispatch a
read-only diagnostic packet; Review remains the stage owner, accepts the
diagnosis, and directs its own Fix worker. Keep shared browser, database,
account, registry, and runtime-instance writes serial.

Join and inspect every repair result, then, only when budget remains, open the
next validation epoch, restart the integrated product, and run an independent
revalidation wave over the failed journey, dependency paths,
and credible regression set. A repair author must not verify its own finding;
the leader or a different read-only subagent performs revalidation. The leader
owns the running instance, ports, test data, coverage reconciliation, all
packet joins, repair acceptance, and final verdict. The bounded set scopes
finding-level revalidation only. After any Fix, rerun every required Review
scenario and recapture all required evidence against the single final reviewed
snapshot. Persist the complete accepted Fix-set digest and an exact byte-bound
full-matrix scenario-evidence manifest in the final revalidation; no pre-Fix,
partial, missing, extra, or relabeled evidence can satisfy approval. Apply path,
cycle-id, and byte-digest validation to cycle 1 as well as later cycles.
If the failed epoch consumed the final slot, preserve the finding and block
without an unprovable repair or revalidation.

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
all Review repairs. It also requires a non-reset validation-epoch ledger with at
most three entries and a passing latest required epoch. Copy validation's `current_fingerprint`
into `final.reviewed_snapshot_sha256` before setting `status: approved`; never
invent or reuse that digest. Any later production or configuration
change makes the verdict stale.

Also reconcile the frozen Human Acceptance Universe against every new or
changed requirement and require zero uncovered required human obligations.
Verify `human_acceptance_obligations` and `human_acceptance_scenarios`, then
create non-empty `reviewed_runtime_targets` covering every required human
scenario. Bind each target to its official entrypoint, exact
environment/instance/configuration, final reviewed snapshot, applicable
artifact/deployment/version identity, linked Review scenarios, and existing
fresh ready evidence. Write one exact identity JSON projection per target under
`review-evidence/` and, in repair cycle 2+, under
`review-evidence/cycle-<n>/`; record its feature-relative
`identity_evidence_ref` and the SHA-256 of its current bytes as
`identity_evidence_sha256`. This valid JSON has top-level `version` equal to
`1`, `status` equal to `"ready"`, and a `target` object containing exactly
`id`, `mode`, `entrypoint_id`, `environment_ref`, `instance_ref`,
`configuration_ref`, `reviewed_snapshot_sha256`, `artifact_ref`,
`artifact_sha256`, `deployment_id`, `observed_version`, `review_scenario_ids`,
and `ready_evidence_refs`, copied exactly from the reviewed target.
For `build` and `deployment`, require `artifact_ref` to name an existing
feature-relative product/build file included in the implementation snapshot,
never `review-evidence/`, `review-results/`, or another snapshot-excluded path;
capture it before the final fingerprint and require `artifact_sha256` to match
its current bytes. Then
compute `final.runtime_targets_sha256`. The
Review-to-Accept handoff contains those obligations, scenarios, targets, and
digest. Accept preserves both identity-evidence fields read-only, may add only
session readiness/actions, and Review never prefills
human PASS. After an acceptance repair, every human scenario is reset and must
be rerun; preserve no earlier PASS.

After verified Review-owned changes, run
`{{specify-subcmd:project-cognition closeout-plan --workflow sp-review --intent implement --format json}}`
with explicit Review-owned paths, fill returned agent-owned fields, and execute
structured `update_argv`. Apply the receipt-bound finalizer gate in
`references/project-cognition.md` before any clean claim; then run
`{{specify-subcmd:review closeout --feature-dir <feature-dir> --expected-revision <revision> --format json}}`.
Execute only the successful response's revision-bound workflow completion argv.
Recommend `$spx-accept` and stop; do not run human acceptance inline. Never
claim completion from worker reports, stale evidence, skipped required
scenarios, or unresolved blocking findings.

---
name: spx-review
description: Advanced system review and repair workflow. Use after implementation to prove the product starts from its real entrypoint, completes required user journeys, has no disconnected controls or registrations, and is ready for human acceptance.
---

# SPX Review

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when Review, Fix, or revalidation lanes are delegated.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/run-bootstrap.md`.
Read
`references/project-cognition.md`, using cognition intent `implement`. Read
`references/review-contract.md`; read `references/worker-contract.md` only when
delegating. Read `references/ui-quality-gate.md` for UI-bearing scenarios and
`references/blocker-resolution.md` when a blocked exit becomes possible.

`$spx-review` starts from the exact immutable Candidate built from eligible implementation Results. Inspect it with `specify-runtime candidate show` and run integrated proof with `specify-runtime candidate review`. Bind frozen product targets through `specify-runtime review target-bind`. Any accepted code repair runs through `specify-runtime run supervise` as a new repair Run, seals a new Result, and requires a newly built and reviewed Candidate; never mutate or directly integrate the old Candidate.

When the upstream gate is `selected` or `required`, or the canonical task index
has a Test Design binding, require a producer-built Review projection and
verify it first with
`{{specify-subcmd:specify-runtime test-design projection-verify --feature-dir <feature-dir> --projection-ref <project-relative-ref> --expected-sha256 <sha256> --format json}}`.
Consume that canonical typed pointer-only projection read-only as an oracle and
coverage input. Never create, patch, replace, weaken, or copy the Test Design
publication, projection, cases, data, coverage, gaps, or audit. Missing, stale,
tampered, foreign, active, blocked, or unpublished selected/required input
routes to the independent `$spx-test-design` producer and stops. **Test Design
is not PASS evidence** and does not prove the implementation passes. Review
still performs independent coverage discovery and captures fresh integrated
evidence at every applicable real entrypoint against the final snapshot.

Resolve exactly one implementation-complete feature. Require a trusted
`implementation-handoff.json`, current implementation evidence, and the
official real entrypoint. Initial Review transitions from validated `implement`;
an acceptance repair arrives through CLI-owned `accept route-repair` with
`review` already active. Then run
`{{specify-subcmd:specify-runtime review prepare --feature-dir <feature-dir> --expected-revision <revision> --format json}}`.
Treat the resulting `review-state.json` as the canonical resumable Review state;
if preparation reports stale or malformed Review-owned state outside an
acceptance-repair cycle, rerun it with `--restart-stale` so the runtime archives
the exact old bytes and starts a fresh evidence cycle. Do not
reconstruct its stable schema from prose. An acceptance repair must
create the next cycle bound to the previous approved Review digest and routed
finding; never edit or reapprove the old cycle.
When `review prepare`, `review validate`, or `review resume-audit` returns
`recovery_owner=review` for `implementation-snapshot-drift`, treat the snapshot
drift as Review-owned recovery and immediately execute
its structured `next_argv` (`review prepare ... --restart-stale`). The runtime
returns that owner only after comparing a byte-bound per-path snapshot manifest
and proving every changed path belongs to a current-cycle accepted Fix assignment
whose independent finding chain and packet/result digests are intact; never
synthesize or hand-edit that authorization. It preserves the immutable handoff,
archives stale Review evidence, binds the current scoped implementation snapshot,
and starts the next evidence cycle without consuming another logical validation
gate. Current scoped snapshots exclude unrelated repository state and
workflow/cognition metadata, while accepted in-scope Review repairs use this recovery. Do not
ask the user to choose `stop` or `authorize-later-cycle` for internal recovery.
Escalate only for runtime-identified unattributed or concurrent owned-path drift,
a true external boundary, or a proven upstream truth gap.
When the runtime returns `recovery_reason=legacy-snapshot-quarantine`, immediately
execute its structured `next_argv`; it archives the manifest-less legacy Review
state and opens a fresh evidence cycle without claiming the old drift was an
accepted Fix. If preparation succeeds with `source.snapshot_reconciliation` set
to `initial-review-rebaseline` or `legacy-review-rebaseline`, continue directly
into a full Review from official entrypoints and recapture all current-cycle
integrated evidence. Continuity with the old scalar fingerprint is deliberately
unproven, so these modes grant neither approval nor reusable evidence and must
not become a user recovery menu.

Continue the validation ledger shared across Implement and Review; do not reset
it on phase entry, resume, worker dispatch, or Review-cycle creation. It has
three logical gates, while physical retries are attempts inside a gate. Before
work, run
`{{specify-subcmd:specify-runtime implement validation-status --feature-dir <feature-dir> --format json}}`
and follow `attempt_decision`. `remaining_epochs`/`remaining_gate_slots` count
only unopened logical gates: zero does not block `retry_same_gate`, while
`repair_before_retry` requires diagnosis and a changed fingerprint. Before
executing tests, builds, startup, E2E, real scenarios, or UI capture, the Leader
opens an attempt in the delivery gate. Multiple commands and read-only
observation slices against that fingerprint share it. Interruption may retry the
same fingerprint; a real failure requires repair and a new fingerprint. Never
open a fourth logical gate. A status reason of
`review-owned-repair-needs-delivery-proof` means Review changed the product
after convergence but before delivery: open delivery at that repaired
fingerprint, never retry convergence or reopen Implement.

On an uncertain or terminal-looking resume, run
`{{specify-subcmd:specify-runtime review resume-audit --feature-dir <feature-dir> --format json}}`
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
current Leader-owned delivery attempt. UI-bearing scenarios
must capture fresh integrated `structure_snapshot`, `visual_capture`, and
`runtime_diagnostics` evidence and visually inspect the required states against
approved design DNA, anti-slop, hierarchy, and the exact `style_authority`—not
code correctness alone. Treat any unapproved drift from cited live UI as
blocking under `inherit-existing`, especially on protected `global-shell` and
`shared-components`; permit a style delta only on the exact complete-page
surface named by `page-overhaul-authorized`. A
UI Review scenario executes the exact `interaction_matrix` and
`data_state_matrix` rows and their risk-based combinations: pointer/mouse,
keyboard/focus, applicable touch/shortcut/command input; exact event sequence,
immediate feedback, focus, repeat, cancellation, and pending behavior; empty and populated
data plus declared degraded/recovery states; and continuous stretch,
compression, reflow, and overflow while active context is preserved. Missing
retry, undo, recovery, permission, offline, focus, selection, scroll, overlay,
or unsaved-input behavior remains uncovered. A
passing comparison calls `specify-runtime evidence visual-compare` with compact observed matrix/evidence input; the runtime derives and atomically owns the task-bound `spec-kit-visual-comparison-v1` report, approved preview/manifest/handoff bindings, exact `DS-*`/`DH-*` coverage, tolerance, deviations, path, and digest. Passing unit
tests, existing files, synthetic-only checks, or an isolated component do
not prove the product works. Group capture by integrated surface and source
fingerprint; do not run the full viewport/state capture loop per Txx. Required
source-grounded tasks additionally run `specify-runtime evidence
source-continuity-manifest`, inspect the live inventory, then call
`source-continuity-adapter-bridge`; it maps signals through
`source-continuity-adapter-catalog` and owns inventory, Probe, and Plan.
`source-continuity-adapter-probe` and `source-continuity-adapter-plan` remain
lower-level fallbacks. Compile `source-continuity-adapter-execution` and require
the exact ten-lane packets, business targets, typed evidence, permissions,
preconditions, stop conditions, and `adapter:<adapter_id>` provenance. Submit independent
source/target discovery, action, side-effect, final-state, and asset
observations through `specify-runtime evidence
source-continuity-validate --feature-dir <feature-dir> --task-id <Txxx>
--manifest <manifest-ref> --adapter-plan <adapter-plan-ref>
--adapter-execution <adapter-execution-ref> --input-json
'<observed-result-json>'`. Bind the runtime-owned
`source_continuity_adapter_plan_ref`/SHA-256,
`source_continuity_adapter_execution_ref`/SHA-256,
`source_continuity_lab_report_ref`/SHA-256, and exact three-axis
coverage in `ui_verification`; self-declared coverage, a handwritten report, or
visual similarity cannot replace this behavioral parity gate.

Compile the Review Universe from authoritative obligations, handoff scenarios,
changed consumer surfaces, runtime-discovered controls/registrations, and
affected regression paths. Use independent coverage discovery so an omission
in the supplied matrix cannot silently narrow Review. The leader orchestrates
subagents through a read-only Review/Audit wave inside the already-open attempt,
joins and reconciles every
result, then requires zero uncovered obligations and surfaces before approval.
An audit worker cannot declare coverage complete or edit product code. In an
acceptance repair cycle, an accepted read-only diagnostic Review assignment
must own the routed observation. Record its packet lane as `diagnostic`, but
patch the `review-state.json` assignment through a leased `specify-runtime artifact patch` with `kind: scenario_review` and
`read_only: true`; `diagnostic` is not a state kind. Import external, binary,
or large proof through `specify-runtime evidence`. Materialize each required
current-cycle JSON record under `review-evidence/` through `artifact prepare`
plus inline `artifact submit`; the content-addressed evidence command does not
create that feature-local path. Submit packet/results inline through
`specify-runtime result submit --command review`; earlier-cycle evidence cannot close the new cycle.

After the audit join, run an independent Fix wave. The leader gives Fix workers
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
Never reopen `implement` for these defects; the runtime rejects that route.

Join and inspect every repair result, then open a new attempt in the same
delivery gate, restart the integrated product, and run an independent
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
A real failure remains blocking until a repaired fingerprint passes a later
delivery attempt; an interruption never becomes a pass or assertion failure.
Exclude from that executable matrix only scenarios covered by a current
human-confirmed `hardware_unavailable` exception; they remain `waived`, never
PASS, and require the qualified `pass_with_waivers` final verdict.
Unit tests alone cannot substitute for official real-entrypoint delivery proof,
and a repeated unit-only pass does not satisfy the Review delivery attempt. A
`pass` status cannot stand alone: every required non-waived scenario carries
current-cycle integrated evidence bound to the reviewed snapshot and current
artifact bytes.

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
`{{specify-subcmd:specify-runtime review validate --feature-dir <feature-dir> --format json}}`.
Approval requires the Review Universe at zero uncovered, all packets joined,
every mandatory scenario passed or explicitly waived through the
human-confirmed hardware-only lane in `references/review-contract.md`, zero blocking findings, required evidence
present, every Implement DEF resolved with current-cycle byte-bound evidence,
clean blocking diagnostics, and a fresh final source fingerprint after all
Review repairs. It also requires a non-reset validation ledger with at most
three logical gates and a passing latest delivery attempt. Let `review target-bind`
derive `final.reviewed_snapshot_sha256` from that fingerprint; never author,
patch, invent, or reuse the digest. Any later production or configuration
change makes the verdict stale.

Also reconcile the frozen Human Acceptance Universe against every new or
changed requirement and require zero uncovered required human obligations.
Verify `human_acceptance_obligations` and `human_acceptance_scenarios`, then
bind one compact semantic target per required human scenario with
`specify-runtime review target-bind --feature-dir <feature-dir> --input-json '<compact-target-json>' --format json`. Include only its id, mode, official entrypoint, exact
environment/instance/configuration, applicable
artifact/deployment/version identity, linked Review scenarios, and existing
fresh ready evidence. Do not supply status, snapshot, identity refs/bytes/digests,
or the complete target digest. The Review CLI verifies the semantic input and
atomically derives those fields plus the current-cycle identity JSON under
`review-evidence/` or `review-evidence/cycle-<n>/`, including
`identity_evidence_ref` and `identity_evidence_sha256`.
For `build` and `deployment`, require `artifact_ref` to name an existing
feature-relative product/build file included in the implementation snapshot,
never `review-evidence/`, `review-results/`, or another snapshot-excluded path;
capture it before target binding and require `artifact_sha256` to match
its current bytes. The runtime computes `final.runtime_targets_sha256`. The
Review-to-Accept handoff contains those obligations, scenarios, targets, and
digest. Accept preserves both identity-evidence fields read-only, may add only
session readiness/actions, and Review never prefills
human PASS. After an acceptance repair, every human scenario is reset and must
be rerun; preserve no earlier PASS.

After verified Review-owned changes, run
`{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-review --scope-dir <feature-dir> --scope-mode explicit --intent implement --format json}}`
with explicit Review-owned paths, fill returned agent-owned fields, and execute
structured `apply_argv`; it owns update, validation, eligible finalization, and
receipt. Apply the gate in
`references/project-cognition.md` before any clean claim; then run
`{{specify-subcmd:specify-runtime review closeout --feature-dir <feature-dir> --expected-revision <revision> --format json}}`.
Execute only the successful response's revision-bound workflow completion argv.
Recommend `$spx-accept` and stop; do not run human acceptance inline. Never
claim completion from worker reports, stale evidence, unconfirmed skipped required
scenarios, or unresolved blocking findings.

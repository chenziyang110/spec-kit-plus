# System Review contract

## Readiness and owned state

Review starts only after implementation closeout has produced a trusted
`implementation-handoff.json` and the CLI runtime permits the `implement` to
`review` transition. The handoff identifies the implementation fingerprint,
official entrypoints, required system Review scenarios, and the validation
ledger shared across Implement and Review. Reject a missing,
ambiguous, or stale handoff; do not infer completion from task checkboxes.

Read any `user_confirmed_deferrals` in the handoff before allocation. Each DEF
is unresolved scope whose ownership expires into Review. Restore its exact
blocker/task/acceptance/validation refs, keep the listed claims withheld, and
rerun it. Resolve its `review-state.json.implementation_deferrals` entry only
with `status: resolved`, outcome `passed|fixed`, a nonblank summary,
current-cycle evidence refs and byte digests, current `review_cycle_id`, and the
final implementation fingerprint. A DEF is not prior PASS evidence and cannot
be forwarded silently to Accept.

Continue that ledger without resetting it. The combined flow owns three logical
gates (`baseline`, `convergence`, `delivery`), while physical retries are
attempts inside a gate. Commands, scenarios, and read-only observation lanes
against one fingerprint share one attempt. Runner timeout/termination is
`interrupted`, not failed; it may retry the same delivery gate and fingerprint.
A real failure requires repair and a new fingerprint. Never open a fourth
logical gate. After timeout, isolate the last active scenario/test with
open-handle/process-exit diagnostics; repair a hang, or split a legitimately
long matrix into deterministic bounded shards inside the same delivery gate.

Its canonical ref is `implementation-review/validation-runs.json`. Call
`{{specify-subcmd:specify-runtime implement validation-status --feature-dir <feature-dir> --format json}}`
before Review work. Before the Leader starts a delivery scenario wave, call
`{{specify-subcmd:specify-runtime implement validation-start --feature-dir <feature-dir> --stage review --purpose delivery --command '<cmd>' [--command '<cmd2>'] [--task-id T001] [--task-id T002] [--fingerprint <sha>] --format json}}`;
omit `--fingerprint` to bind the current implementation snapshot. After the wave,
call
`{{specify-subcmd:specify-runtime implement validation-finish --feature-dir <feature-dir> --run-id <Vn> --status <passed|failed|interrupted> [--failure-kind <assertion|verification|harness|environment|runner_timeout|runner_terminated|cancelled|unknown>] --evidence-ref <ref> [--evidence-ref <ref2>] --summary '<text>' --format json}}`.
Use the runtime-returned gate/attempt ids and counts; do not hand-edit or
reconstruct the ledger.

`review prepare` compiles or freshness-checks the resumable
`review-state.json`. If it reports stale or malformed Review-owned state
outside an acceptance-repair cycle, rerun with `--restart-stale`; the runtime
archives the exact old bytes under `review-history/` and creates a fresh
evidence cycle. The installed template/schema and runtime are authoritative
for stable fields. Review owns that state, `review-evidence/**`, Review result
records, bounded source/test repairs, and Review-owned rich workflow-state
fields. It must not silently rewrite specification, plan, tasks, task lifecycle
acceptance, or CLI-owned `workflow.json`.

On resume, validate the persisted source revision, handoff digest, current
implementation/configuration fingerprint, Review cycle id, prior approved
Review digest when acceptance reopened the stage, scenario cursor, finding
status, and evidence paths before reusing any result. If the handoff changed, a Review
repair changed covered source, or another actor changed the product after
validation, mark prior approval stale and rerun every affected scenario. The
final reviewed fingerprint covers the integrated source/configuration snapshot
after all Review repairs; it is the input trust boundary for human acceptance.
Use `{{specify-subcmd:specify-runtime review resume-audit --feature-dir <feature-dir> --format json}}`
to recover the exact cursor and freshness gaps; do not infer them from prose.
An acceptance repair creates cycle 2 or later and seeds a Review finding linked
to the routed human finding. Assign it to an accepted read-only diagnostic
worker. `diagnostic` is the packet lane; persist the corresponding
`review-state.json` assignment with `kind: scenario_review` and
`read_only: true`, never `kind: diagnostic`. Store new scenario evidence under `review-evidence/cycle-<n>/` and all
Review/Fix/revalidation packet results under `review-results/cycle-<n>/`;
earlier-cycle evidence cannot close the current cycle.

## Mandatory scenario matrix

The leader compiles the Review Universe from authoritative acceptance and
design/architecture obligations, handoff scenarios, changed consumer surfaces,
runtime-discovered controls/registrations, and affected shared paths. Use
independent coverage discovery before reading the supplied matrix when
practical, then reconcile the two views. The deterministic scenarios from the
handoff are the minimum, never a reason to ignore an observable gap discovered
at the real entrypoint. Cover:

- installation/build/startup through each official entrypoint and its ready or
  health signal;
- required user journeys, navigation, routes, commands, and state transitions;
- every relevant button, link, menu, form, shortcut, or CLI action and its
  observable result;
- UI/command to handler/controller, service/provider, persistence or external
  dependency, and feedback wiring where applicable;
- registration and consumption of routes, handlers, providers, factories,
  adapters, jobs, commands, generated clients, and configuration;
- persistence/reload plus relevant empty, error, permission, and unavailable
  states;
- blocking browser console, network, process, application-log, and runtime
  diagnostics;
- affected shared-surface regression and the integrated final journey.

For UI scenarios, evidence uses only canonical kinds
`structure_snapshot`, `visual_capture`, and `runtime_diagnostics`, with
`evidence_scope: integrated`, plus visual comparison or explicit human review.
Persist a `spec-kit-visual-comparison-v1` report for every pass; bind the
approved preview/manifest digests, required captures, applicable `DS-*`
decisions, comparison tolerance, and approved deviations.
Use stable real content and the required viewport/state matrix. Isolated task
evidence may guide Review but cannot close a system scenario. Group the matrix
by integrated surface and fingerprint; do not run the full viewport/state
capture loop per Txx.

Coverage closes only at zero uncovered obligations and surfaces after all
packets joined. A worker cannot declare coverage complete; the leader owns the
universe, dispositions, joins, and final coverage verdict.

## Findings and repair routing

Record a finding with its scenario, classification, severity/blocking status,
expected and observed results, sanitized evidence, suspected ownership, and
revalidation scope. Never convert a failed observation into a pass by weakening
the expectation.

Also record `gap_classification`: `implementation_gap` for missing/incorrect
code, wiring, or tests under clear upstream truth; `traceability_gap` for
missing task/CA/scenario mapping under clear upstream truth; or
`upstream_truth_gap` for missing or contradictory requirement, design, or
architecture truth. Implementation and traceability gaps remain in Review for
repair and revalidation. Only a proven upstream truth gap may leave Review.

- Every approved-scope defect remains in Review regardless of repair size.
  Missing code, a task omission, incomplete tests, broken wiring, and
  registration/configuration defects are not upstream truth gaps; decompose
  them into bounded Fix packets and add regression protection.
- An unknown root cause or intermittent mechanism remains in Review. Preserve
  the failed scenario, dispatch a read-only diagnostic packet, and let the
  leader accept the diagnosis before compiling the Fix wave. Review remains the
  stage owner throughout diagnosis, repair, and revalidation.
- Only a proven upstream truth gap is a handoff-and-stop boundary: missing or
  contradictory requirement truth routes to `$spx-specify`; missing or
  contradictory design truth routes to `$spx-design`; architecture truth that
  must change before any conforming fix routes to `$spx-plan`.
- Human-only system, account, device, protected CI, or visual judgment: retain a
  blocked Review with the full Human Action Guide and exact resume point.

For a proven truth gap, use the runtime-provided reopen argv when present.
Otherwise use `specify-runtime workflow reopen` with current revision, compact reason,
sanitized evidence, and the complete invalidated-artifact set. The upstream
workflow never declares Review passed; return to the reopened Review owner for
scenario revalidation.

## Revalidation and approval

After the audit join, use a separate Fix wave for accepted findings. Fix workers
run cheap task checks, return test impact, and must not execute heavyweight
gates per Txx. Join the complete repair batch before the Leader opens a new
attempt in the delivery gate; do not open an attempt per finding or per repair.
Run that independent revalidation wave over the exact failed step, its
complete user journey, every scenario sharing the changed dependency, and the
smallest credible regression set. A repair author must not verify its own
finding; use the leader or a different read-only subagent. Recapture stale
UI/runtime evidence. That subset scopes finding-level revalidation only. After
any Fix, restart from a clean supported state, rerun every required Review
scenario, and recapture every required evidence record against the single final
reviewed snapshot. No pre-Fix scenario evidence can satisfy approval.

A real failure remains blocking until a repaired fingerprint passes a later
delivery attempt. Any source change requires a later attempt before approval;
do not reset the ledger or retry a real failure against the unchanged
fingerprint. Runner interruption may retry the same fingerprint.

If the Fix set is non-empty, write one final full-matrix revalidation. Its
`fix_assignment_ids` and canonical `fix_assignments_sha256` cover every accepted
Fix, `scenario_ids` is exactly every required scenario, and its final snapshot
and cycle ids are current. Byte-bind `evidence_manifest_ref` through
`evidence_refs`/`evidence_sha256`. That JSON manifest contains exactly
`version`, `revalidation_id`, `review_cycle_id`, `snapshot_sha256`,
`fix_assignments_sha256`, and `scenario_evidence`; the last field contains one
`{scenario_id, kind, path, artifact_sha256}` record for every required evidence
kind of every required scenario. A partial, stale, extra, missing, or relabeled
matrix blocks approval.

Require path confinement, current `review_cycle_id`, and byte SHA-256 binding in
cycle 1 too: scenario evidence uses `artifact_sha256`; Review/Fix packets and
results use packet/result SHA fields; revalidation evidence uses
`evidence_sha256`. Repair cycles additionally stay inside their `cycle-<n>/`
subtrees.

`review validate` may approve only when:

- the Review Universe has zero uncovered obligations/surfaces and all packets joined;
- every required scenario is `pass`;
- no blocking finding remains open or merely asserted resolved;
- required evidence exists, is integrated, and matches the current snapshot;
- startup/readiness and material runtime diagnostics pass;
- each repair has fresh revalidation evidence;
- the shared validation ledger contains at most three logical gates, was not
  reset after Implement, and its latest delivery attempt passed;
- the final source fingerprint is current;
- every required Human Acceptance scenario has a ready reviewed runtime target
  whose immutable identity, linked Review scenarios, and ready evidence match
  that final fingerprint, whose identity-evidence path and byte digest are
  current, and the target digest is current;
- every `build` or `deployment` target references an existing feature-relative
  artifact whose `artifact_sha256` matches its current bytes.

After the final integrated validation, copy the deterministic
`current_fingerprint` into `final.reviewed_snapshot_sha256`, then set
`status: approved`. Do not approve from an earlier digest.

`review closeout` prepares or refreshes the final implementation summary and
human-acceptance handoff, but it does not transition phase state itself. Before
closeout, reconcile the frozen Human Acceptance Universe against every new or
changed requirement and require zero uncovered required human obligations.
Create `reviewed_runtime_targets` before validation. Each target records its
official entrypoint, exact environment/instance/configuration, final snapshot,
applicable artifact/deployment/version identity, linked Review scenarios, and
existing fresh ready evidence. For every target, write an identity JSON claim
under `review-evidence/` (`review-evidence/cycle-<n>/` in repair cycle 2+) that
has top-level `version` equal to `1`, `status` equal to `"ready"`, and a `target`
object containing exactly `id`, `mode`, `entrypoint_id`, `environment_ref`,
`instance_ref`, `configuration_ref`, `reviewed_snapshot_sha256`, `artifact_ref`,
`artifact_sha256`, `deployment_id`, `observed_version`, `review_scenario_ids`, and
`ready_evidence_refs`, with each value copied exactly from the reviewed target.
Record its feature-relative path as `identity_evidence_ref` and its current-byte
SHA-256 as `identity_evidence_sha256`. For `build` and `deployment`, require an
existing feature-relative product/build `artifact_ref` included in the
implementation snapshot and a byte-matching `artifact_sha256`; it must not live
under `review-evidence/`, `review-results/`, or another snapshot-excluded path,
and it must exist before the final fingerprint is captured.
The Review-to-Accept handoff contains
`human_acceptance_obligations`, `human_acceptance_scenarios`, those targets, and
their final digest. Accept preserves both identity-evidence fields read-only
and may add only session readiness/actions; it does not
prefill human PASS or duplicate the System Review matrix. After an acceptance
repair, reset every human scenario and preserve no earlier PASS. Execute only the returned
revision-bound completion argv. The separately invoked `$spx-accept` claims the
next stage and owns the human verdict.

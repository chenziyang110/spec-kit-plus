{{spec-kit-include: ../common/user-input.md}}

## Objective

Prove that the integrated implementation is an operable product from its official real entrypoints, repair bounded implementation defects, and preserve enough evidence to resume or make the final review claim honestly.

## Process

## Intake And Runtime Ownership

- Resolve exactly one feature and inspect `specify-runtime workflow show` before mutation. Transition from completed `implement` to `review` with the runtime-returned revision; do not hand-edit `workflow.json`.
- Run `{{specify-subcmd:specify-runtime review prepare --feature-dir <feature-dir> --expected-revision <revision> --format json}}`. Treat `implementation-handoff.json` as the implementation-to-review source contract and `review-state.json` as Review's resumable truth. If preparation reports stale or malformed Review-owned state outside an acceptance-repair cycle, rerun the same command with `--restart-stale`; the runtime archives the exact old bytes under `review-history/` and creates a fresh evidence cycle. When `accept route-repair` reopens Review, preparation creates a new cycle bound to the prior approved Review digest and routed acceptance finding; never restart, edit, or reapprove the old accepted cycle.
- Read `implementation-handoff.json.user_confirmed_deferrals` before allocation.
  Every DEF is unresolved scope transferred from Implement: restore its exact
  blocker/task/acceptance/validation refs, keep its listed claims withheld, and
  rerun it in Review. Resolve its `review-state.json.implementation_deferrals`
  entry only with `status: resolved`, outcome `passed|fixed`, a nonblank summary,
  current-cycle evidence refs and byte digests, current `review_cycle_id`, and
  the final implementation fingerprint. A DEF is never prior PASS evidence and
  cannot be silently carried into Review approval.
- The Leader owns `review-state.json`, the official runtime instances, ports, test data, finding lifecycle, repair acceptance, and final verdict.
- Continue the validation ledger shared across Implement and Review. Do not
  reset it on Review entry, resume, or repair-cycle creation. It has at most
  three logical gates; Review retries stay inside the delivery gate.
- The canonical ledger is
  `implementation-review/validation-runs.json`. Before Review work run
  `{{specify-subcmd:specify-runtime implement validation-status --feature-dir <feature-dir> --format json}}`.
  Before the Leader starts a delivery scenario wave, run
  `{{specify-subcmd:specify-runtime implement validation-start --feature-dir <feature-dir> --stage review --purpose delivery --command '<cmd>' [--command '<cmd2>'] [--task-id T001] [--task-id T002] [--fingerprint <sha>] --format json}}`;
  omit `--fingerprint` to bind the current implementation snapshot. Afterward run
  `{{specify-subcmd:specify-runtime implement validation-finish --feature-dir <feature-dir> --run-id <Vn> --status <passed|failed|interrupted> [--failure-kind <assertion|verification|harness|environment|runner_timeout|runner_terminated|cancelled|unknown>] --evidence-ref <ref> [--evidence-ref <ref2>] --summary '<text>' --format json}}`.
  Use the runtime-returned ids and budget; never hand-edit the file.
- On resume, run `{{specify-subcmd:specify-runtime review resume-audit --feature-dir <feature-dir> --format json}}` when available. Continue from the exact scenario/finding cursor and invalidate evidence whose implementation fingerprint, source revision, or Review cycle is stale. Repair-cycle evidence belongs under `review-evidence/cycle-<n>/` and packet/results under `review-results/cycle-<n>/`; an earlier cycle cannot close the current one.

## System Review Loop

1. Compile the Review Universe and use independent coverage discovery to reconcile authoritative obligations with actual consumer and runtime surfaces.
2. Open the Leader-owned delivery gate attempt, start each official entrypoint,
   then run a read-only Review/Audit wave whose workers inspect assigned coverage
   slices and return evidence/findings without edits. All commands, scenarios,
   and captures against that fingerprint share the one gate attempt.
3. The Leader joins all audit packets, rejects stale or incomplete results, resolves coverage gaps, and freezes the accepted finding set.
4. Run a separate Fix wave for accepted findings. Fix workers receive isolated write scopes, run cheap task
   checks, return test impact, and may change implementation/tests but never
   upstream truth or execute heavyweight gates.
5. Join and inspect every repair, then open a new attempt in the same delivery gate, restart the
   real product, and run an independent revalidation wave. The repair author must
   not verify its own finding.
6. A source change invalidates prior proof and requires another attempt for
   approval. Retry an interrupted attempt in the same gate/fingerprint; retry a
   real assertion or verification failure only after a new fingerprint. Never
   record runner timeout/termination as failed or passed: interrupted is not
   failed. After timeout, isolate the last active scenario/test with
   open-handle/process-exit diagnostics; repair a hang, or split a legitimately
   long matrix into deterministic bounded shards inside the same delivery gate.
   Never open a fourth logical gate.

UI-bearing scenarios require real-entrypoint `structure_snapshot`, `visual_capture`, and `runtime_diagnostics` evidence with `evidence_scope: integrated`. Group the viewport/state matrix by integrated surface and source fingerprint; do not run the full viewport/state capture loop per Txx. Validate interaction, navigation, loading, empty, error, permission, persistence/reload, responsive, keyboard/focus, console, network, and runtime states when applicable. A passing visual judgment also requires a `spec-kit-visual-comparison-v1` report derived from `.specify/templates/visual-comparison-template.json`: it binds approved preview/manifest digests to implementation captures, covers every applicable `DS-*` decision, applies the preserved tolerance, and lists only approved deviations. Automated behavior checks remain distinct from visual and interaction acceptance.

## Delegation

- The Leader orchestrates subagents across the Review/Audit wave, Fix wave, and independent revalidation wave; direct execution is reserved for compact, tightly coupled steps.
- Audit workers are read-only. Fix workers receive finding-bound, non-overlapping write scopes. Revalidation workers are read-only and independent from the repair author.
- Compile each `SystemReviewPacket` just in time from current state and live code. Never dispatch a raw checklist or the entire feature package.
- Serialize paths sharing one browser session, database state, service instance, port, or write set. Integrate worker results before accepting a repair.
- A worker result is evidence only. A worker cannot declare coverage complete or the whole system approved; the Leader owns all joins, zero-uncovered coverage, repair acceptance, and the final verdict after an integrated restart and required regression.
- Workers do not open logical gates or validation attempts. The Leader may coordinate read-only
  observation slices inside one already-open attempt, but must not let scenario,
  worker, or Txx boundaries multiply heavyweight runs.

## Output Contract

- Keep `review-state.json` fresh and schema-valid with scenario results, findings, repair/revalidation evidence, cursor, blockers, and next action.
- Store evidence under `review-evidence/` and reference it compactly from state; do not paste large logs or screenshots into agent state.
- Before the handoff, verify that `human_acceptance_obligations` and `human_acceptance_scenarios` still cover the frozen Human Acceptance Universe for every new or changed requirement with zero uncovered required obligations. Create `reviewed_runtime_targets` covering every required human scenario, with immutable official entrypoint, environment/instance/configuration, final snapshot, applicable artifact/deployment/version identity, linked Review scenarios, and existing fresh ready evidence. For each target, write the exact runtime identity JSON projection under `review-evidence/` and, for repair cycle 2+, under `review-evidence/cycle-<n>/`; record its feature-relative `identity_evidence_ref` and byte-exact `identity_evidence_sha256`. A `build` or `deployment` target also requires an existing feature-relative product/build `artifact_ref`, created before the final fingerprint, included in the implementation snapshot, outside `review-evidence/`, `review-results/`, and every other snapshot-excluded path, whose current bytes match `artifact_sha256`. Bind the exact target list with `final.runtime_targets_sha256`. Accept receives these targets, preserves both identity-evidence fields read-only, and may add only session readiness/actions.
- After the final integrated restart, run `{{specify-subcmd:specify-runtime review validate --feature-dir <feature-dir> --format json}}`, bind its `current_fingerprint` to `final.reviewed_snapshot_sha256`, and only then set Review `status: approved`. Run `{{specify-subcmd:specify-runtime review closeout --feature-dir <feature-dir> --format json}}` only after all required scenarios pass, all required evidence is integrated and fresh, and blocking findings are zero.
- On successful Review closeout, update Review-owned rich state truthfully, execute the returned revision-bound `specify-runtime workflow complete-stage` argv separately, hand off to `{{invoke:accept}}`, and stop. The Review-to-Accept handoff carries obligations, human scenarios, immutable reviewed targets, and their digest; it does not prefill human PASS. After an acceptance repair, Acceptance reruns every frozen scenario and preserves no old PASS. Do not enter acceptance in this invocation.

## Guardrails

- `sp-review` is not permission to change approved product scope or upstream truth. Every approved-scope defect stays in Review regardless of repair size, including missing code, task omission, and unknown root cause; use a diagnostic packet before a Fix packet when needed.
- Review remains the stage owner through diagnosis, repair, and revalidation. Only a proven requirement truth, design truth, or architecture truth gap may produce an upstream handoff; missing code is not an upstream truth gap.
- Keep the existing event-triggered task review embedded in `sp-implement`; do not duplicate its task lifecycle ledger here.
- Do not claim success because the build passes, tasks are checked, files exist, or a worker says PASS.
- Do not let a passive testing skill, worker, resume, or completion claim start
  an extra logical gate or attempt. Review owns the reserved delivery gate and
  retries only inside it.
- Do not push, deploy, modify protected systems, use real customer data, or perform external writes without explicit authority. Use isolated test data and the shared blocker contract for genuine external boundaries.

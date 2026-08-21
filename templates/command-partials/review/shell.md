{{spec-kit-include: ../common/user-input.md}}

{{spec-kit-include: ../common/design-intelligence.md}}

## Objective

Prove that the integrated implementation is an operable product from its official real entrypoints, repair bounded implementation defects, and preserve enough evidence to resume or make the final review claim honestly.

## Process

## Intake And Runtime Ownership

- Resolve exactly one feature and inspect `specify-runtime workflow show` before mutation. Transition from completed `implement` to `review` with the runtime-returned revision; do not hand-edit `workflow.json`.
- Run `{{specify-subcmd:specify-runtime review prepare --feature-dir <feature-dir> --expected-revision <revision> --format json}}`. Treat `implementation-handoff.json` as the implementation-to-review source contract and `review-state.json` as Review's resumable truth. If preparation reports stale or malformed Review-owned state outside an acceptance-repair cycle, rerun the same command with `--restart-stale`; the runtime archives the exact old bytes under `review-history/` and creates a fresh evidence cycle. When `accept route-repair` reopens Review, preparation creates a new cycle bound to the prior approved Review digest and routed acceptance finding; never restart, edit, or reapprove the old accepted cycle.
- When `review prepare`, `review validate`, or `review resume-audit` returns `recovery_owner=review` for `implementation-snapshot-drift`, treat the snapshot drift as Review-owned recovery and immediately execute its structured `next_argv` (`review prepare ... --restart-stale`). The runtime returns that owner only after comparing a byte-bound per-path snapshot manifest and proving every changed path belongs to a current-cycle accepted Fix assignment whose independent finding chain and packet/result digests are intact; never synthesize or hand-edit that authorization. It preserves the immutable handoff, archives stale Review evidence, binds the current scoped implementation snapshot, and starts the next evidence cycle without consuming another logical validation gate. Current scoped snapshots exclude unrelated repository state and workflow/cognition metadata, while accepted in-scope Review repairs use this recovery. Do not ask the user to choose `stop` or `authorize-later-cycle` for internal recovery. Escalate only when the runtime identifies unattributed or concurrent owned-path drift, a true external boundary, or a proven upstream truth gap.
- When the runtime returns `recovery_reason=legacy-snapshot-quarantine`, immediately execute its structured `next_argv`; this archives the manifest-less legacy Review state and opens a fresh evidence cycle without claiming the old drift was an accepted Fix. If preparation succeeds with `source.snapshot_reconciliation` equal to `initial-review-rebaseline` or `legacy-review-rebaseline`, continue directly into a full Review from official entrypoints and recapture all current-cycle integrated evidence. Continuity with the old scalar fingerprint is deliberately unproven, so these modes grant neither approval nor reusable evidence and must not become a user recovery menu.
- Query `/user_confirmed_deferrals` with `specify-runtime artifact show --path <feature-dir>/implementation-handoff.json --json-pointer /user_confirmed_deferrals` before allocation.
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
  Treat `remaining_epochs` and `remaining_gate_slots` as capacity for new
  logical gates only. Follow the returned `attempt_decision`: zero remaining
  slots never blocks `retry_same_gate`; `repair_before_retry` means diagnose
  and change the implementation fingerprint first. Do not infer a stop from
  the raw epoch count or create a replacement gate. If Review repairs the
  product after Implement convergence but before delivery was opened, the
  runtime returns reason
  `review-owned-repair-needs-delivery-proof`: open the Review delivery gate at
  the repaired fingerprint; never retry convergence or reopen Implement.
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
   Never open a fourth logical gate. Unit tests alone cannot substitute for
   official real-entrypoint delivery proof, and a repeated unit-only pass does
   not satisfy the Review delivery attempt. A `pass` status also cannot stand
   alone: every required non-waived scenario must carry current-cycle integrated
   evidence bound to the reviewed snapshot and the current artifact bytes.

Hardware-only exception lane:

- When a required scenario cannot run solely because specific physical
  hardware is absent, first record current-cycle evidence of the missing
  resource and the bounded alternatives attempted. This is not eligible for
  credentials, protected CI, ordinary environment setup, flaky tests, visual
  judgment, or an implementation failure.
- Register the missing-resource observations as current-cycle evidence, then pass a compact in-memory proposal directly to the Review CLI with
  `kind: hardware_unavailable`, exact affected scenario/obligation ids,
  `required_resource`, `unavailable_evidence_refs`,
  `attempted_alternatives`, `claims_withheld`, `residual_risk`, and
  `risk_severity`. Run
  `{{specify-subcmd:specify-runtime review exception-propose --feature-dir <feature-dir> --input-json '<proposal-json>' --format json}}`.
  Build the proposal in memory; never create a proposal file.
  Show the human the exact scope, withheld claims, residual risk, exception id,
  and proposal digest. Only an explicit human decision may continue through
  `{{specify-subcmd:specify-runtime review exception-confirm --feature-dir <feature-dir> --exception-id <REX-id> --proposal-sha256 <sha> --confirmation-source human-reply --statement '<exact human statement>' --format json}}`.
- A confirmed exception records scenario result `waived`, obligation status
  `waived`, and final verdict/coverage verdict `pass_with_waivers`; it never
  records PASS. Exclude only those confirmed waived scenarios from executable
  full-matrix evidence, bind the complete ledger with
  `final.review_exceptions_sha256`, and preserve the ledger and withheld claims
  in the implementation summary and Accept handoff. Unconfirmed, stale, or
  tampered proposals remain blocking.

UI-bearing scenarios require real-entrypoint `structure_snapshot`, `visual_capture`, and `runtime_diagnostics` evidence with `evidence_scope: integrated`. Group the risk-based input × data × size matrix by integrated surface and source fingerprint; do not run the full matrix per Txx or explode it into an unbounded Cartesian product. Execute every declared `interaction_matrix`, `editing_matrix`, and `data_state_matrix` row: pointer/mouse, keyboard/focus, applicable touch/shortcut/command event sequence, immediate feedback, focus, repeat, cancellation, and pending behavior; IME composition, paste/autofill, caret/selection, validation, dirty/persistence, undo/redo, conflict, read-only/disabled, and submission behavior; empty and populated data plus declared loading, partial, error, permission, offline, pending, retry, undo, and recovery states; and continuous stretch/compression/reflow/overflow while preserving focus, selection, scroll, overlays, and unsaved input. A populated pointer happy path cannot substitute for those rows. Validate navigation, persistence/reload, console, network, and runtime states when applicable. For each passing task-bound visual judgment, call `specify-runtime evidence visual-compare --feature-dir <feature-dir> --task-id <Txxx> --input-json '<observed-comparison-json>' --format json`; the runtime binds the approved preview/manifest/handoff truth, exact `DS-*`/`DH-*` coverage, tolerance, and deviations to the observed matrix and returns the canonical report ref/digest. Never read the stable template or author/patch the report. Automated behavior checks remain distinct from visual and interaction acceptance.

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
- Import external, binary, or large proof into the content-addressed store through `specify-runtime evidence import/register`. When the Review contract requires a current-cycle feature-local JSON record under `review-evidence/`, materialize that bounded semantic record through `artifact prepare` plus inline `artifact submit`, and patch it only through a fresh lease; the evidence store does not invent that feature-local path. Reference returned evidence records/objects compactly and never paste large logs or screenshots into agent state.
- Before handoff, pass each compact semantic target to `specify-runtime review target-bind --feature-dir <feature-dir> --input-json '<compact-target-json>' --format json`. Never author the target row or identity JSON: the Review CLI verifies current-cycle evidence and product artifacts, derives the current snapshot, identity path/bytes, byte digest, and complete target digest, and atomically updates both registered artifacts. Preserve the frozen Human Acceptance Universe with zero uncovered required obligations.
- After the final integrated restart and all `review target-bind` calls, patch only agent-authored verdict fields and `status: approved` through the leased artifact CLI; never patch runtime-derived snapshots, targets, identity fields, or target digests. Then run `{{specify-subcmd:specify-runtime review validate --feature-dir <feature-dir> --format json}}` and treat any failure as blocked. Run `{{specify-subcmd:specify-runtime review closeout --feature-dir <feature-dir> --expected-revision <revision> --format json}}` only after every required scenario either passes with fresh integrated evidence or carries a current human-confirmed hardware exception, and blocking findings are zero.
- On successful Review closeout, update Review-owned rich state truthfully, execute the returned revision-bound `specify-runtime workflow complete-stage` argv separately, hand off to `{{invoke:accept}}`, and stop. The Review-to-Accept handoff carries obligations, human scenarios, immutable reviewed targets, and their digest; it does not prefill human PASS. After an acceptance repair, Acceptance reruns every frozen scenario and preserves no old PASS. Do not enter acceptance in this invocation.

## Guardrails

- `sp-review` is not permission to change approved product scope or upstream truth. Every approved-scope defect stays in Review regardless of repair size, including missing code, task omission, and unknown root cause; use a diagnostic packet before a Fix packet when needed.
- Review remains the stage owner through diagnosis, repair, and revalidation. Only a proven requirement truth, design truth, or architecture truth gap may produce an upstream handoff; missing code is not an upstream truth gap.
- Never reopen `implement` for a Review finding. The runtime rejects that route;
  Review's Leader dispatches its own diagnostic, Fix, join, and independent
  revalidation waves. A proven truth gap reopens the stage that owns that truth,
  not the old implementation workflow.
- Keep the existing event-triggered task review embedded in `sp-implement`; do not duplicate its task lifecycle ledger here.
- Do not claim success because the build passes, tasks are checked, files exist, or a worker says PASS.
- Do not let a passive testing skill, worker, resume, or completion claim start
  an extra logical gate or attempt. Review owns the reserved delivery gate and
  retries only inside it.
- Do not push, deploy, modify protected systems, use real customer data, or perform external writes without explicit authority. Use isolated test data and the shared blocker contract for genuine external boundaries.

## Professional UI Contract Continuity

Review the integrated product against every exact applicable `surface_catalog`,
`scenario_matrix`, `interaction_matrix`, `editing_matrix`, `data_state_matrix`,
`accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, and `usability_validation` row/object plus component
governance.
For Web UI, exercise every routed `smoothness_acceptance_id` and bind its result
to the existing integrated structure, visual, runtime, and visual-comparison or
human-review evidence; ordinary screenshots cannot close interaction checks.
Enforce the exact `style_authority`: under `inherit-existing`, any
unapproved visual-language drift from the cited live UI, especially in
`global-shell` or `shared-components`, is a blocking finding; under
`page-overhaul-authorized`, accept style delta only on the exact authorized
complete-page surface. Execute risk-based
or pairwise real-entrypoint scenarios rather than an unbounded Cartesian
product. Automated tests and screenshots cannot close required target-user
human review.

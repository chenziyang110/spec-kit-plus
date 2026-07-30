Trigger: before setting Review approved, completing the runtime stage, or recommending human acceptance.

Purpose: make system usability claims revision-bound and prevent stale or partial evidence from reaching `sp-accept`.

## Final Claim Gate

The Leader may issue the final verdict only when all of the following are true:

- the Review Universe reports zero uncovered obligations and surfaces after independent coverage discovery;
- all packets joined, every result was accepted or explicitly requeued, and no audit, diagnostic, Fix, or revalidation lane remains active;
- the implementation handoff, implementation fingerprint, source revision, and current reviewed code/config snapshot are fresh;
- every mandatory scenario passes from its official real entrypoint or is explicitly `waived` by a current, hash-bound, human-confirmed hardware-unavailability exception;
- every passing scenario contains its required evidence, with UI evidence captured at integrated scope; each waived scenario instead has current byte-bound hardware-unavailability evidence and human confirmation;
- no open blocking finding, unresolved mandatory blocker, pending repair, or unvalidated worker result remains;
- every repaired scenario and affected regression path was rerun after the last relevant change;
- the validation ledger shared across Implement and Review was not reset,
  contains at most three logical gates, and its latest delivery attempt passed;
  interruptions were not mislabeled as failures or passes;
- each repaired finding was checked in an independent revalidation wave by the Leader or a read-only subagent other than its repair author;
- final runtime diagnostics contain no unexplained blocking error;
- every required Human Acceptance scenario has a ready `reviewed_runtime_targets` record bound to its official entrypoint, final snapshot, linked Review scenarios, and fresh ready evidence; every target has byte-bound `identity_evidence_ref` and `identity_evidence_sha256`; `build` and `deployment` artifact refs exist and their `artifact_sha256` values bind current bytes; and `final.runtime_targets_sha256` matches the exact target list.

Do not claim Review completion from partial coverage, unjoined worker narration,
the repair author's own assertion, or evidence captured before the final
integrated fingerprint.

Any production or relevant configuration change after evidence capture makes the affected result stale. Reopen its scenario and recapture evidence; never reuse a prior pass merely because the intended behavior did not change.

If that change leaves no passing final delivery attempt, preserve the finding
and block rather than claiming completion or reusing stale evidence.

After the final integrated restart and all target bindings, use leased JSON-pointer `specify-runtime artifact patch` calls only for agent-authored verdict fields and the `approved` status. Never patch `final.reviewed_snapshot_sha256`, target rows, identity fields, or `final.runtime_targets_sha256`; `review target-bind` already derives them from the current fingerprint and exact bytes. Then run `{{specify-subcmd:specify-runtime review validate --feature-dir <feature-dir> --format json}}` and treat any failure as blocked rather than proceeding to closeout. Before closeout, reconcile the frozen Human Acceptance Universe against every new or changed requirement and require zero uncovered required obligations.

Define immutable reviewed targets covering every required human scenario, with exact environment/instance/configuration and applicable artifact/deployment/version identity. For each target, pass only compact semantic input (`id`, `mode`, `entrypoint_id`, environment/instance/configuration refs, optional artifact/deployment/version identity, test-data refs, linked Review scenario ids, and fresh ready-evidence refs) to `specify-runtime review target-bind --feature-dir <feature-dir> --input-json '<compact-target-json>' --format json`. Never author or generically prepare, submit, or patch the target row or identity JSON. The Review CLI verifies current-cycle evidence and product artifacts, then atomically derives `status: ready`, `reviewed_snapshot_sha256`, the canonical identity path and exact bytes, `identity_evidence_ref`, `identity_evidence_sha256`, and `final.runtime_targets_sha256` while updating both registered artifacts.

For `build` and `deployment`, `artifact_ref` must name an existing feature-relative product/build file created before the final fingerprint, included in the implementation snapshot, and outside `review-evidence/`, `review-results/`, and every other snapshot-excluded path; `artifact_sha256` must bind its current bytes.

Run `{{specify-subcmd:specify-runtime review closeout --feature-dir <feature-dir> --expected-revision <revision> --format json}}`. On success, closeout transactionally refreshes `implementation-summary.md` and prepares `human-acceptance.json`. Its Review-to-Accept handoff preserves `human_acceptance_obligations`, `human_acceptance_scenarios`, `reviewed_runtime_targets`, identity-evidence fields, the immutable confirmed exception ledger, withheld claims, and their digests without prefilling human PASS. Accept keeps the waiver and identity-evidence fields read-only and may add only session readiness/actions. Execute only the returned revision-bound `specify-runtime workflow complete-stage` argv, recommend `{{invoke:accept}}`, and stop. Human product acceptance remains a separate stage; Review must not conduct that conversation inline.

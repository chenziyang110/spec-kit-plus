Trigger: before setting Review approved, completing the runtime stage, or recommending human acceptance.

Purpose: make system usability claims revision-bound and prevent stale or partial evidence from reaching `sp-accept`.

## Final Claim Gate

The Leader may issue the final verdict only when all of the following are true:

- the Review Universe reports zero uncovered obligations and surfaces after independent coverage discovery;
- all packets joined, every result was accepted or explicitly requeued, and no audit, diagnostic, Fix, or revalidation lane remains active;
- the implementation handoff, implementation fingerprint, source revision, and current reviewed code/config snapshot are fresh;
- every mandatory scenario passes from its official real entrypoint;
- every scenario contains its required evidence, with UI evidence captured at integrated scope;
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

Run `{{specify-subcmd:specify-runtime review validate --feature-dir <feature-dir> --format json}}` after the final integrated restart. Copy its `current_fingerprint` into `final.reviewed_snapshot_sha256`, then set `status: approved`; do not invent or reuse that digest. Before closeout, reconcile the frozen Human Acceptance Universe against every new or changed requirement and require zero uncovered required obligations. Create immutable reviewed targets covering every required human scenario, with exact environment/instance/configuration and applicable artifact/deployment/version identity. For each target, write a feature-relative identity claim under `review-evidence/` (`review-evidence/cycle-<n>/` for repair cycle 2+). This valid JSON has top-level `version` equal to `1`, `status` equal to `"ready"`, and a `target` object containing exactly `id`, `mode`, `entrypoint_id`, `environment_ref`, `instance_ref`, `configuration_ref`, `reviewed_snapshot_sha256`, `artifact_ref`, `artifact_sha256`, `deployment_id`, `observed_version`, `review_scenario_ids`, and `ready_evidence_refs`, copied exactly from the reviewed target. Store its path and current byte digest as `identity_evidence_ref` and `identity_evidence_sha256`. For `build` and `deployment`, `artifact_ref` must name an existing feature-relative product/build file, created before the final fingerprint, included in the implementation snapshot, and outside `review-evidence/`, `review-results/`, and every other snapshot-excluded path; `artifact_sha256` must bind its current bytes. Then bind the targets with `final.runtime_targets_sha256`. Run `{{specify-subcmd:specify-runtime review closeout --feature-dir <feature-dir> --format json}}`. On success, it refreshes `implementation-summary.md` and prepares `human-acceptance.json`; the Review-to-Accept handoff contains `human_acceptance_obligations`, `human_acceptance_scenarios`, `reviewed_runtime_targets`, their identity-evidence fields, and their digest, and does not prefill human PASS. Accept preserves `identity_evidence_ref` and `identity_evidence_sha256` read-only and may add only session readiness/actions. Execute only the returned revision-bound `specify-runtime workflow complete-stage` argv. Recommend `{{invoke:accept}}` and stop. Human product acceptance is a separate stage; Review must not conduct the acceptance conversation inline.

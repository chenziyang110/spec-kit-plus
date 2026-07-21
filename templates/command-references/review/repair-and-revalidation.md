Trigger: when a required scenario fails, a blocking diagnostic appears, or consumer wiring is incomplete.

Purpose: turn system-review findings into bounded repairs with exact proof, while keeping unknown mechanisms under Review ownership and routing only proven upstream truth gaps to their proper owners.

## Finding And Repair Loop

Record the expected behavior, observed behavior, scenario id, sanitized evidence, classification, affected scope, suspected owner, status, and exact next action before editing.

Record an orthogonal `gap_classification`: `implementation_gap` when approved behavior lacks correct code/wiring/tests, `traceability_gap` when approved behavior lacks task/CA/scenario mapping, or `upstream_truth_gap` when requirement, design, or architecture truth is missing or contradictory. Findings classified as `implementation_gap` or `traceability_gap` remain in Review for bounded repair and revalidation. Only a proven `upstream_truth_gap` may leave Review through a handoff-and-stop boundary.

- Every approved-scope defect is Review-owned regardless of repair size. Missing code, a task omission, incomplete tests, broken wiring, and registration/configuration defects are not upstream truth gaps; the Leader decomposes them into one or more bounded Fix packets.
- An unknown root cause or intermittent mechanism remains inside Review. Preserve the exact failed scenario and dispatch a read-only diagnostic packet; Review remains the stage owner, accepts or rejects the diagnosis, and then compiles the Fix wave.
- Only a proven upstream truth gap is a handoff-and-stop boundary: missing or contradictory requirement truth routes to `sp-clarify`/`sp-specify`, missing or contradictory design truth routes to `sp-design`, and architecture truth that must change before any conforming fix is possible routes to `sp-plan`.
- Human/external authority, credentials, protected service, physical device, or unavailable comparison: persist a structured blocker and full Human Action Guide with observable unblock criteria and exact Review resume point.

Continue the validation-epoch ledger shared across Implement and Review; do not
reset it. After the audit join, run a separate Fix wave with finding-bound write
scopes only when a later epoch remains. Fix workers perform cheap task checks and
return test impact, but must not run heavyweight validation per Txx. Join the
complete repair batch before the Leader opens one next epoch; do not open an
epoch per finding or per repair. The Leader restarts the official real entrypoint
when process/configuration state may be affected, and runs an independent
revalidation wave over the exact failed action sequence, all scenarios depending
on the repaired surface, and the smallest credible regression set. That subset
scopes finding-level attribution only. Approval after any Fix requires every
required Review scenario and must recapture all required evidence records against the one final reviewed
snapshot in that epoch; no pre-Fix scenario evidence can close Review. A repair
author must not verify its own finding; use the Leader or a different read-only
subagent. A source diff, unit test, or worker assertion alone cannot resolve the
finding. The third failed epoch blocks with exact evidence and recovery criteria;
never start a fourth validation epoch.

When any Fix assignment exists, persist one final full-matrix revalidation record. Its `fix_assignment_ids` and canonical `fix_assignments_sha256` cover the complete accepted Fix set; `scenario_ids` is exactly every required Review scenario; `snapshot_sha256` and `review_cycle_id` bind the final snapshot/cycle; and `evidence_manifest_ref` names a current-cycle JSON manifest also listed and byte-bound in `evidence_refs` / `evidence_sha256`. The manifest contains exactly `version`, `revalidation_id`, `review_cycle_id`, `snapshot_sha256`, `fix_assignments_sha256`, and `scenario_evidence`; the final array has one `{scenario_id, kind, path, artifact_sha256}` item for every required evidence kind of every required scenario. Recompute the Fix-set digest and manifest from the joined records. Missing, extra, stale, partial, or relabeled evidence blocks approval.

This byte binding applies to cycle 1 as well as repair cycles: every scenario evidence record carries the current `review_cycle_id` and `artifact_sha256`; every Review/Fix packet and result carries its current-cycle id plus packet/result SHA-256; every revalidation evidence ref carries its current byte digest. Keep cycle-1 refs inside `review-evidence/` or `review-results/` and repair-cycle refs inside their `cycle-<n>/` subtree.

When Review was reopened from failed human acceptance, `review prepare` must create a new cycle bound to the prior approved Review digest and routed acceptance finding. Assign that finding to an accepted read-only diagnostic Review worker before Fix. Store scenario evidence under `review-evidence/cycle-<n>/` and Review/Fix/revalidation packet results under `review-results/cycle-<n>/`; never reuse an earlier cycle to close the new one. A successful repair resets every frozen Human Acceptance scenario; the failed cursor is only the first retest point, not permission to preserve other PASS results.

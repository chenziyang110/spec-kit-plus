Trigger: before setting Review approved, completing the runtime stage, or recommending human acceptance.

Purpose: make system usability claims revision-bound and prevent stale or partial evidence from reaching `sp-accept`.

## Final Claim Gate

The Leader may issue the final verdict only when all of the following are true:

- the implementation handoff, implementation fingerprint, source revision, and current reviewed code/config snapshot are fresh;
- every mandatory scenario passes from its official real entrypoint;
- every scenario contains its required evidence, with UI evidence captured at integrated scope;
- no open blocking finding, unresolved mandatory blocker, pending repair, or unvalidated worker result remains;
- every repaired scenario and affected regression path was rerun after the last relevant change;
- final runtime diagnostics contain no unexplained blocking error.

Any production or relevant configuration change after evidence capture makes the affected result stale. Reopen its scenario and recapture evidence; never reuse a prior pass merely because the intended behavior did not change.

Run `{{specify-subcmd:review validate --feature-dir <feature-dir> --format json}}` after the final integrated restart. Copy its `current_fingerprint` into `final.reviewed_snapshot_sha256`, then set `status: approved`; do not invent or reuse that digest. Run `{{specify-subcmd:review closeout --feature-dir <feature-dir> --format json}}`. On success, it refreshes `implementation-summary.md` and `human-acceptance.json`; execute only the returned revision-bound `workflow complete-stage` argv. Recommend `{{invoke:accept}}` and stop. Human product acceptance is a separate stage; Review must not pre-fill a human verdict or conduct the acceptance conversation inline.

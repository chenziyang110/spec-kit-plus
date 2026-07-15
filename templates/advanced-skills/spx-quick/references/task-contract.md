# Quick task contract

Keep one resumable truth surface in `STATUS.md` and one terminal account in
`SUMMARY.md`. Create `STATUS.md` through the deterministic `quick-status`
artifact scaffold and create `SUMMARY.md` from `assets/summary.md`; resolve the
asset path relative to this Skill.

`STATUS.md` must keep only information needed to resume safely:

- intent and observable acceptance;
- in-scope and explicitly excluded behavior;
- expected or changed paths;
- current focus, next action, blocker, and material decisions;
- verification commands/results and remaining risk.

`understanding_confirmed: false` blocks broad investigation, delegation,
implementation, and validation until the user confirms the checkpoint. A
confirmed discussion handoff digest may satisfy the checkpoint only when quick
introduces no semantic delta.

Update it at scope changes, before/after delegated joins, on blockers, and at
terminal verification—not after every command. Repository evidence may resolve
technical questions; ask the user only for product choices or authority the
repository cannot supply.

Escalate when the task develops cross-capability behavior, architectural or
migration decisions, unsafe write overlap, an unknown root cause, or acceptance
that cannot be stated compactly. Do not shrink the request to remain in quick.

At closeout, `SUMMARY.md` records outcome, changed paths, verification actually
run, skipped checks, residual risk, and recovery state. `STATUS.md` points to it
and reaches `resolved` or `blocked` truthfully.

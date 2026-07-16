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

The user-facing checkpoint is the Quick card in
`references/human-confirmation.md`, followed conditionally by its UI card. Store
the user-owned decisions and `ui_confirmation` separately from the
`agent_execution_plan`; one reply confirms both cards when UI applies.

`understanding_confirmed: false` blocks broad investigation, delegation,
implementation, and validation until the user confirms the checkpoint. A
confirmed discussion handoff digest may satisfy the checkpoint only when quick
introduces no semantic delta.

Do not reopen confirmation when repository evidence only adds files, call
sites, tests, or implementation detail needed for the same confirmed outcome
within the confirmed boundary, risk, and authority. Update state and continue.
Reopen only for a material change to outcome, boundaries, confirmed UI
direction, user-visible behavior, risk, authority, migration or compatibility
obligations, an independent capability, or an explicit stop condition; first set
`understanding_confirmed: false` and pause substantive work.

Before presenting the amendment, explain in user-facing prose the new evidence,
why the previous confirmation no longer covers the work, the consequence of
omitting it, the current mutation state and safe pause point, and the exact
incremental decision the user owns. Only after that explanation, present
`## Quick Checkpoint Amendment` with only the changed rows or decisions and an
`Unchanged` statement; do not repeat the full initial Quick Checkpoint. Persist
the confirmed delta before resuming, and do not request duplicate confirmation
when the user already approved that exact delta.

For a UI-only material delta, keep the Quick amendment heading, include only
the changed UI Confirmation rows. State that the main checkpoint is unchanged.
The reason-first explanation remains mandatory; do not replay either complete initial table.

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

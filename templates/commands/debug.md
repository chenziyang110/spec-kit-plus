---
description: Use when a bug, regression, failed verification, or unexpected runtime behavior needs a resumable investigation and fix workflow.
workflow_contract:
  when_to_use: A defect or failed verification needs structured root-cause investigation instead of ad hoc fixes.
  primary_objective: Build a resumable debug session that delivers the confirmed diagnosis scope, or applies and verifies an authorized causal fix.
  primary_outputs: Debug-session state, revision-bound diagnostic findings, verified fix artifacts when authorized and justified, and an honest investigating/awaiting-human/resolved/blocked outcome.
  default_handoff: Continue agent-owned investigation and recovery; pause only for a required human checkpoint or an exhausted authorized recovery path. Return to execution only after the defect contract is satisfied.
---

{{spec-kit-include: ../command-partials/debug/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}
{{spec-kit-include: ../command-partials/common/execution-bootstrap.md}}
{{spec-kit-include: ../command-partials/common/autonomous-blocker-recovery.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

[AGENT] Apply the Pre-Intake Context Sufficiency Gate first. The full Debug
branch creates or resumes its debug session in the current worktree, with task
identity `debug:<session-slug>`. The explicit user-selected context-direct
branch creates no debug session; both routes use the shared execution bootstrap.

[AGENT] Once the complete repair scope is proven, announce that scope, checkpoint
selection, refresh the overview, and require the all-or-none
`specify-runtime execution guard` before the first source write, including any
supporting test, harness, configuration, or instrumentation mutation. Renew the
guard after relevant scope expansion or source drift. Context-direct
uses the same guarded Work/Activity lifecycle before its bounded fix; skipping
Debug state does not skip write coordination. Checkpoint validation and call
`specify-runtime execution complete` only after fresh passing validation and
terminal workflow state.

## Main Flow

The steps below own only the full Debug branch. A user-selected context-direct
branch is legal only when the failure mechanism is already proven by evidence
in the conversation; it performs the bounded fix, RED/reproduction, fresh
verification, and exact-path mutation closeout without entering this flow.
Clean closeout keys on `result_state`; not `status=ok`, `update_id`, `last_update_id`, or freshness alone. Do not present `status=ok` alone as proof
of cognition freshness or mutation closeout.

1. Resolve the exact session through its CLI owner. On resume, read `references/debug-state.md`, retain valid confirmations and artifacts, and identify the earliest unsatisfied gate; do not restart a completed intake or select a session by recency alone.
2. Run the Debug Cognition Gate and confirm the Debug Understanding Checkpoint before reproduction, logs, source reads, evidence collection, delegation, edits, or validation. A branch choice is not that confirmation.
3. Build or reuse the complete map-backed intake; use Stage 1A then Stage 1B only when needed. The leader schedules these dependent stages from accepted artifacts, not from an assumed graph-engine callback. Preserve every framing gate before evidence work.
4. Choose `leader-inline` or `subagent-assisted` from current capabilities and safe evidence lanes. Read `references/hypothesis-and-root-cause.md` before dispatch, join, or a causal decision. Keep one active causal decision; independent falsifiers may run in parallel without competing production edits.
5. Establish the original failure and causal evidence. For a confirmed `diagnose only` request, follow Diagnosis-Only Delivery in `references/debug-state.md`, deliver the requested diagnosis, and return without claiming the defect `resolved`. For authorized repair, read `references/fix-gate.md` before any source, test, harness, configuration, or instrumentation write; establish target-specific RED, apply the minimum guarded fix, and recover permitted supporting failures inside Debug.
6. For an authorized fix, re-run the original reproduction, regression and related-risk checks on the final changed revision, including instrumentation cleanup and UI recapture when applicable. Reject stale, missing, skipped, or wrong-failure evidence. Repair and resume the interrupted gate in the same invocation while any safe authorized action remains.
7. Persist the complete evidence and exact next action through leased artifact patches. For an authorized fix, agent verification leads to `awaiting_human_verify`, not `resolved`. Read `references/regression-validation-and-closeout.md`; explicit human confirmation, current evidence, and the existing cognition/execution closeout gates are all required for a clean completion claim.

If repair is authorized and no reliable automated test surface exists, guard
the declared supporting write scope and build the smallest viable test harness.
If that expands beyond the first debug fix lane, preserve the debug
session, expand the registered causal scope, and
repair the harness inside the active Debug recovery lane.
Do not invoke another user-invoked workflow automatically. Verify it, then return to the reproduction and resume the original reproduction and verification path in the same invocation.
Use `/sp-specify` only when the user explicitly chooses a formal spec-first path. Unfamiliarity, scope
growth, or unavailable delegation does not by itself justify a blocked Debug
close.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [intake and debug checkpoint](references/intake-and-debug-checkpoint.md)
- [reproduction and evidence](references/reproduction-and-evidence.md)
- [hypothesis and root cause](references/hypothesis-and-root-cause.md)
- [fix gate](references/fix-gate.md)
- [regression validation and closeout](references/regression-validation-and-closeout.md)
- [debug state](references/debug-state.md)

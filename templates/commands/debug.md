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

On resume, read `references/debug-state.md`, retain still-valid confirmation and
framing, select the exact session without recency guessing, and resume the earliest
unsatisfied gate. For `diagnose only`, follow Diagnosis-Only Delivery in that
reference; deliver the requested diagnosis without claiming the defect `resolved`.

For an authorized fix, final integrated verification leads to
`awaiting_human_verify`; require explicit human confirmation of the current fix
and successful cognition/execution closeout before claiming completion.

1. Choose `leader-inline`, `subagent-assisted`, or `blocked` based on investigation size, safety, and packetizability; keep the leader responsible for session state and root-cause decisions.
2. Create or resume the debug session through its CLI owner, query required workflow context through `specify-runtime artifact show`, run the Debug Cognition Gate, and understand the report; ask for missing reporter facts only when they block diagnosis.
3. Build the causal map, investigation contract, log plan, observer framing, and first evidence path; do not form a final root cause before reproduction and evidence.
4. Investigate one active hypothesis at a time, record eliminated alternatives, confirm root cause, and reject surface-only fixes.
5. Present the evidence-backed Debug Understanding Checkpoint: explain the discovered problem and decisive evidence, concrete repair and affected scope, expected outcome, risks, and verification. Wait for the user's confirmation before any repair write or fix-worker dispatch. Then apply the minimum safe fix through the selected execution model, verify with reproduction and tests, review related risks, patch the debug session only through leased `specify-runtime artifact patch` calls, and close only as resolved or blocked after the existing final human-verification gate.

If no reliable automated test surface exists, include the smallest viable
harness in the concrete repair approval. Reuse that approval when its exact
scope already covers the harness; do not ask again. If the gap prevents
diagnosis itself, obtain bounded diagnostic-write authority through the same
checkpoint before building the harness. Diagnostic-only authority does not approve a
production fix: return to evidence investigation and obtain concrete repair
confirmation first. If that expands beyond the first debug fix lane, preserve the debug
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

---
description: Use when a bug, regression, failed verification, or unexpected runtime behavior needs a resumable investigation and fix workflow.
workflow_contract:
  when_to_use: A defect or failed verification needs structured root-cause investigation instead of ad hoc fixes.
  primary_objective: Build a resumable debug session that gathers evidence, identifies root cause, applies a fix, and verifies the result.
  primary_outputs: Debug-session state, evidence, verified fix artifacts when justified, and an honest blocked/resolved status.
  default_handoff: Stay inside the debug session until resolved or blocked; route back to execution only after the defect contract is satisfied.
---

{{spec-kit-include: ../command-partials/debug/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}
{{spec-kit-include: ../command-partials/common/run-bootstrap.md}}
{{spec-kit-include: ../command-partials/common/autonomous-blocker-recovery.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

[AGENT] Apply the Pre-Intake Context Sufficiency Gate first. The full Debug
branch always starts a new Run: when its exact metadata and child argv are ready,
use `specify-runtime run launch` as the single call that records and supervises
it; do not resume another workflow's Run. Older runtimes without `run.launch`
fall back to `specify-runtime run create` followed by `specify-runtime run
supervise`. The explicit user-selected context-direct branch is the sole
exception and creates no run or debug session.

[AGENT] Launch the full branch with task identity `debug:<session-slug>` and a
confirmed initial scope; zero confirmed scope blocks before the child starts.
Once the complete repair scope is proven, call `specify-runtime work claim
--task-ref debug:<session-slug> --write-scope-json <complete-json-array>
--format json` and require `data.work_claim` before the first source write. The
context-direct exception still uses the shared context-direct Work registration
and `work claim` gate before its bounded fix; it skips Debug state, not write
coordination.

## Main Flow

The steps below own only the full Debug branch. A user-selected context-direct
branch is legal only when the failure mechanism is already proven by evidence
in the conversation; it performs the bounded fix, RED/reproduction, fresh
verification, and exact-path mutation closeout without entering this flow.
Clean closeout keys on `result_state`; not `status=ok`, `update_id`, `last_update_id`, or freshness alone. Do not present `status=ok` alone as proof
of cognition freshness or mutation closeout.

1. Choose `leader-inline`, `subagent-assisted`, or `blocked` based on investigation size, safety, and packetizability; keep the leader responsible for session state and root-cause decisions.
2. Create or resume the debug session through its CLI owner, query required workflow context through `specify-runtime artifact show`, run the Debug Cognition Gate, and confirm the Debug Understanding Checkpoint before reproduction, logs, source reads, code edits, or validation.
3. Build the causal map, investigation contract, log plan, observer framing, and first evidence path; do not form a final root cause before reproduction and evidence.
4. Investigate one active hypothesis at a time, record eliminated alternatives, confirm root cause, and reject surface-only fixes.
5. Apply the minimum safe fix through the selected execution model, verify with reproduction and tests, review related risks, patch the debug session only through leased `specify-runtime artifact patch` calls, and close only as resolved or blocked.

If no reliable automated test surface exists, build the smallest viable test
harness. If that expands beyond the first debug fix lane, preserve the debug
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

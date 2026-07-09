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

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

## Main Flow

1. Choose `leader-inline`, `subagent-assisted`, or `blocked` based on investigation size, safety, and packetizability; keep the leader responsible for session state and root-cause decisions.
2. Create or resume the debug session, read required context, run the Debug Cognition Gate, and confirm the Debug Understanding Checkpoint before reproduction, logs, source reads, code edits, or validation.
3. Build the causal map, investigation contract, log plan, observer framing, and first evidence path; do not form a final root cause before reproduction and evidence.
4. Investigate one active hypothesis at a time, record eliminated alternatives, confirm root cause, and reject surface-only fixes.
5. Apply the minimum safe fix through the selected execution model, verify with reproduction and tests, review related risks, update the debug file, and close only as resolved or blocked.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [intake and debug checkpoint](references/intake-and-debug-checkpoint.md)
- [reproduction and evidence](references/reproduction-and-evidence.md)
- [hypothesis and root cause](references/hypothesis-and-root-cause.md)
- [fix gate](references/fix-gate.md)
- [regression validation and closeout](references/regression-validation-and-closeout.md)
- [debug state](references/debug-state.md)

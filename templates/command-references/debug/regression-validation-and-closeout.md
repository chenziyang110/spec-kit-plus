Trigger: before session closeout, related-risk review, or blocked/resolved status.

Purpose: preserve consequence loop, checkpoint protocol, regression validation, and closeout rules.

Preserved Contract: debug closeout requires reproduction proof, related-risk review, verification evidence, and terminal state.

Session mutation contract: `SESSION PATCH <fields-or-sections>` means build the bounded change in memory, run `specify-runtime artifact prepare --path .planning/debug/[slug].md`, then apply it with `specify-runtime artifact patch --lease <lease-id>` using `--frontmatter-json` or `--section`. Every debug-state update below means `SESSION PATCH`; never edit the Markdown file directly.

## Debug Consequence Loop

When a defect touches lifecycle, running-state, shared-state, destructive behavior, downstream consumers, compatibility, security, or multiple plausible behavior choices, run the Senior Consequence Analysis Gate as part of the investigation contract.

- Model the dependency loop from trigger to affected objects to control state to observation state to downstream consumers.
- Use the Affected Object Map to separate truth owners, cached projections, queues, workers, artifacts, commands, APIs, and adjacent risk targets.
- Extend the State-Behavior Matrix with the failing lifecycle state and the expected behavior after the fix.
- Use the Dependency Impact Table to identify adjacent risk targets and related-risk review scope before closeout.
- Preserve the Recovery And Validation Contract as loop restoration proof, including repro, regression tests, observability, cleanup, idempotency, and rollback evidence.
- Persist Coverage Gaps and `CA-###` obligations through a fresh `specify-runtime artifact patch` lease when the debug session exposes missing product semantics that must be reopened upstream.
- Reject surface-only fixes: a fix that only changes observation state without repairing the dependency loop, affected objects, or owning control state cannot satisfy the debug consequence loop.

## Checkpoint Protocol

Return a `## CHECKPOINT REACHED` block when user action or confirmation is required.

- **Type**: `human-verify`, `human-action`, or `decision`
- **Progress**: concise summary of the root cause, key evidence, and eliminated hypotheses
- **Awaiting**: exactly what the user must do next

Use `human-verify` after the agent has verified the fix and needs the user to confirm the bug is resolved in their environment.

To begin the debug session:
`EXECUTE_COMMAND: debug`

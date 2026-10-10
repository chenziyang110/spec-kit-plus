Trigger: before session closeout, related-risk review, or blocked/resolved status.

Purpose: preserve consequence loop, checkpoint protocol, regression validation, and closeout rules.

Preserved Contract: debug closeout requires reproduction proof, related-risk review, verification evidence, and terminal state.

Session mutation contract: `SESSION PATCH <fields-or-sections>` means build the bounded same-checkpoint delta in memory. When one semantic boundary updates multiple debug-session frontmatter fields or sections and `api list` exposes `artifact.patch-batch`, prefer one `specify-runtime artifact prepare --path .planning/debug/[slug].md` plus one `specify-runtime artifact patch-batch --lease <lease-id>` that aggregates those updates. For a single target update, or on older runtimes, fall back to one leased `specify-runtime artifact patch` using `--frontmatter-json` or `--section`. Every debug-state update below means `SESSION PATCH`; never edit the Markdown file directly.

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

## Final-Revision Verification and Closeout

Before `awaiting_human_verify`, bind each required verification row to the
current source revision or relevant file digests, environment, command/manual
sequence, expected and observed outcome, and inspectable evidence reference.
Cover the original reproduction, target regression, owning control loop,
nearest-neighbor risks, and affected consumers. For UI work, recapture the same
real entrypoint, input event, data, viewport/resize path and state against the
confirmed baseline. Source-only checks do not prove a visual defect resolved.

Keep failed, skipped, unavailable and stale rows explicit. No aggregate PASS,
worker summary, fixture existence, or accepted failure report can replace a
required passing check. Review the final integrated diff, remove only owned
temporary instrumentation/resources, and revalidate affected rows after cleanup.
A later source or accepted-output change invalidates affected verification and
consumer acceptance; preserve unaffected evidence and failure history.

Agent GREEN plus related-risk review leads to `awaiting_human_verify`, not
`resolved`. Provide the exact reproduction/check, expected behavior, validated
revision and remaining uncertainty to the user. Classification into
`same_issue`, `derived_issue`, or `unrelated_issue` is routing only, not approval.
A linked child's resolution does not close its parent; return to the parent's
own human verification. Explicit human confirmation must match the current fix;
feedback about an older patch cannot approve a newer one.

Preserve the existing cognition refresh/receipt and Learning gates from
`references/fix-gate.md`. Recover their failures inside the same session; do not
repeat human verification when neither the verified fix nor its evidence changed.
A clean claim requires current verification, explicit human confirmation, and
the required successful closeout receipt, not `status=ok` alone. Mark resolved
only when the lifecycle gates pass; complete the guarded execution lifecycle
only with fresh validation and terminal workflow state. Archive only when
requested, through the runtime owner after confirmation and closeout.

An agent-capable blocker stays in the recovery loop: retain the failed gate,
attempts and outcomes, continue independent ready work, repair, and rerun the
original gate in the same invocation. A genuine external/authority/capability
limit uses the shared Blocked Exit Contract after safe authorized alternatives
are exhausted. Neither a dispatch failure nor an arbitrary retry count proves
that boundary. Report completed work, unresolved rows, withheld claims, and an
exact resume action; never present partial work as a resolved bug.

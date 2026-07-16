{{spec-kit-include: ../common/user-input.md}}

## Objective

Drive a resumable debugging workflow that finds the real failure mechanism before any fix is accepted.

## Context

- Primary inputs: the user's report, the active debug-session state, the failing runtime or verification evidence, and the task-local project cognition query bundle with readiness and returned `minimal_live_reads`.
- The debug session file under `.planning/debug/` is the durable state source of truth for this workflow.
- Delegated helpers are evidence collectors, not owners of the overall investigation.
- Debug execution is complexity-based: small focused investigations may stay leader-inline, while broad or independent evidence lanes use one or more subagents.
- Before substantive investigation, present one Debug Understanding Checkpoint covering user-owned problem facts, expected behavior, occurrence conditions, investigation boundary, explicit fix authority, assumptions to correct, and reconfirmation triggers. Technical hypotheses and the evidence sequence belong to the agent. For applicable UI symptoms, append the independent UI Confirmation target baseline and ask for one combined confirmation; record both decisions in the debug session file.
- Treat that as the one initial full checkpoint. If later evidence materially changes the confirmed boundary or authority, use the delta-only Debug Checkpoint Amendment contract after first explaining why the prior confirmation is no longer sufficient.

## Debug Checkpoint Card

{{spec-kit-include: checkpoint-card.md}}

## Process

- Recover or initialize the debug session and current hypothesis.
- Gather evidence through the current investigation strategy.
- For consequence-sensitive failures, trace affected objects, dependency loops, control/observation states, adjacent risk targets, and any `CA-###` stop-and-reopen conditions before accepting a fix.
- Apply a fix only after the failure mechanism is understood well enough to justify it.
- Verify the result and update the session state before any resolution claim.

## Output Contract

- Keep the debug session state, current hypothesis, evidence, and verification outcome explicit.
- Produce a verified fix only when the evidence supports it.
- Report blocked or unresolved states honestly when the investigation cannot yet close.

## Guardrails

- No speculative fixes before evidence supports the failure mechanism.
- No final resolution without fresh verification evidence.
- No subagent may take ownership of the debug session state.
- No subagent-assisted work may continue without a safe lane; blocked debug execution records `subagent-blocked`, `execution_surface: none`, and a concrete blocked reason.

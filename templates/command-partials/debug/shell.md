{{spec-kit-include: ../common/user-input.md}}

## Objective

Drive a resumable debugging workflow that finds the real failure mechanism before any fix is accepted.

## Context

- Primary inputs: the user's report, the active debug-session state, the failing runtime or verification evidence, and the handbook/project-map set.
- The debug session file under `.planning/debug/` is the durable state source of truth for this workflow.
- Delegated helpers are evidence collectors, not owners of the overall investigation.

## Process

- Recover or initialize the debug session and current hypothesis.
- Gather evidence through the current investigation strategy.
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

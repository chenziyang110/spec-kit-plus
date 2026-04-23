# Implementer Worker Prompt

Use this template when the leader dispatches a concrete implementation lane for `sp-implement`.

## Controller Requirements

- Provide the **full task text**. Do not tell the worker to go read `tasks.md` or `plan.md` on its own just to discover the assignment.
- Provide the compiled worker packet or an equivalent summary of:
  - hard rules
  - required references
  - verification gates
  - done criteria
- Name the write set, shared surfaces, and forbidden drift explicitly.

## Worker Contract

- Implement exactly the requested lane, not neighboring work.
- Read only the minimum additional repository context needed to execute safely.
- Follow the referenced boundary pattern instead of inventing a parallel one.
- Report back in this exact status family: `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`.
- Prefer `DONE_WITH_CONCERNS` over silent guessing when the work is complete but confidence is mixed.

## Minimum Return Payload

- Status: `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`
- What changed
- Files changed
- Verification run
- Remaining concern, blocker, or missing context
- When the runtime supports structured delegated results, format the handoff as a `WorkerTaskResult`-style payload with validation evidence and explicit blocker metadata.
- When the leader provides a delegated result handoff path, write the normalized result envelope there instead of replying with freeform prose only.

## Guardrails

- Do not widen scope.
- Do not silently skip packet rules.
- Do not claim verification that was not run.
- If a required decision is missing, stop and return `NEEDS_CONTEXT`.

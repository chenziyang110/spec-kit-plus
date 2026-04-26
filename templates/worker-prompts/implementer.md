# Implementer Worker Prompt

Use this template when the leader dispatches a concrete implementation lane for `sp-implement`.

## Controller Requirements

- Provide the **full task text**. Do not tell the worker to go read `tasks.md` or `plan.md` on its own just to discover the assignment.
- Provide the compiled worker packet or an equivalent summary of:
  - hard rules
  - required references
  - verification gates
  - done criteria
- Provide platform guardrails and completion-handoff expectations explicitly when the lane depends on supported-platform constraints, conditional compilation, runtime-managed result channels, or a promised result handoff path.
- Name the write set, shared surfaces, and forbidden drift explicitly.
- For every behavior-changing task, bug fix, or refactor, tell the worker to write the failing test first, capture the RED state, and return the GREEN rerun evidence for the same gate after the fix.

## Worker Contract

- Implement exactly the requested lane, not neighboring work.
- Read only the minimum additional repository context needed to execute safely.
- Follow the referenced boundary pattern instead of inventing a parallel one.
- For behavior changes, bug fixes, and refactors, follow RED -> GREEN -> REFACTOR:
  - write the failing test first
  - verify the RED state before editing production code
  - rerun the same gate and capture the GREEN state before reporting success
- Report back in this exact status family: `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`.
- Prefer `DONE_WITH_CONCERNS` over silent guessing when the work is complete but confidence is mixed.

## Minimum Return Payload

- Status: `DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT`
- What changed
- Files changed
- Verification run
- RED state evidence when the lane changed behavior
- GREEN state evidence for the same gate after the fix
- Remaining concern, blocker, or missing context
- When the runtime supports structured delegated results, format the handoff as a `WorkerTaskResult`-style payload with validation evidence and explicit blocker metadata.
- When the leader provides a delegated result handoff path, write the normalized result envelope there instead of replying with freeform prose only.
- If the delegated lane requires lifecycle signals such as `task_started`, `task_blocked`, or `task_completed`, emit them as part of the promised completion-handoff protocol instead of assuming a status flip is enough.
- The worker must not enter `idle` before the required handoff is written or returned.
- If the handoff channel fails, return that failure explicitly instead of idling silently.

## Guardrails

- Do not widen scope.
- Do not silently skip packet rules.
- Do not ignore platform guardrails or conditional-compilation requirements carried by the packet.
- Do not claim verification that was not run.
- Do not edit production code until the RED state is verified.
- Do not report success without explicit GREEN state evidence for the same gate you used during RED.
- If a required decision is missing, stop and return `NEEDS_CONTEXT`.

# Quick Worker Prompt

Use this template when the quick-task leader dispatches a bounded execution lane for `sp-quick`.

## Controller Requirements

- Provide the smallest safe lane description and its acceptance check.
- Name the touched files or surfaces.
- State whether the lane is part of a larger join point or is the only active lane.

## Worker Contract

- Complete one smallest safe lane only.
- Keep implementation and verification scoped to that lane.
- Return enough detail for the leader to update `STATUS.md`.
- If this lane is a bug fix, do not hide the symptom with a surface-only or symptom-only change when the root cause is still unknown. Return a blocker or a narrower diagnostic split and route the investigation toward `/sp-debug`.
- `STATUS.md` remains leader-owned; the worker must not become the resume authority.
- STATUS.md remains leader-owned; the worker must not become the resume authority.
- In plain terms: `STATUS.md` remains leader-owned even when delegated execution succeeds.

## Minimum Return Payload

- Lane goal
- What changed
- Verification run
- Files or surfaces touched
- Recommended next action
- Blocker or concern
- When structured delegated results are available, return a `WorkerTaskResult`-style payload so the leader can merge execution state without reinterpreting prose.
- When the leader provides a delegated result handoff path, write the normalized result envelope there instead of replying with freeform prose only.
- The worker must not enter `idle` before the required handoff is written or returned.
- If the handoff channel fails, return that failure explicitly instead of idling silently.

## Guardrails

- Do not widen the quick task into full feature work.
- Do not rewrite adjacent surfaces without explicit instruction.
- Do not use a surface-only or symptom-only patch as a substitute for root-cause work on a bug fix.
- If the lane is too large, stop and return a narrower proposed split.

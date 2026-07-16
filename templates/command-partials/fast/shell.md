{{spec-kit-include: ../common/user-input.md}}

## Objective

Execute a trivial, low-risk task directly in the current context without entering the full `specify -> plan -> tasks` workflow.

Use this for small fixes that are faster to execute than to plan: typo fixes, tiny config changes, missing imports, narrow doc edits, small bug fixes, and similarly bounded adjustments.

## Context

- Primary inputs: the user's request, the smallest relevant local files, and the project cognition safety gate. Fast skips Learning unless it escalates.
- This path exists only for truly local work; the moment that assumption breaks, the task must leave the fast lane.
- Fast-path output is intentionally small and should not spawn planning artifacts.
- Fast-path source/runtime/template/config/test/generated-asset changes follow the shared inline closeout contract:

{{spec-kit-include: ../common/inline-project-cognition-update.md}}
- Upgrade out of fast immediately when senior consequence analysis triggers for lifecycle, running-state, destructive-operation, shared-state, downstream consumer, compatibility, security, or multiple-behavior impact; record only the stand-down reason if it does not trigger.

{{spec-kit-include: ../common/user-input.md}}

## Objective

Execute a trivial, low-risk task directly in the current context without entering the full `specify -> plan -> tasks` workflow.

Use this for small fixes that are faster to execute than to plan: typo fixes, tiny config changes, missing imports, narrow doc edits, small bug fixes, and similarly bounded adjustments.

Fast keeps Quick's core direct-delivery sequence where it adds safety—bounded
intake, Learning, Project Cognition, RED-first execution, verification,
review, and closeout—but removes Quick workspace state, worker packets, and
subagent dispatch. The same leader implements and performs one Lightweight
Review.

## Context

- Primary inputs: the user's request, consume-only Project Learning, the smallest relevant local files, and the Project Cognition safety gate.
- This path exists only for truly local work; the moment that assumption breaks, the task must leave the fast lane.
- Fast-path output is intentionally small and should not spawn planning artifacts.
- Fast-path source/runtime/template/config/test/generated-asset changes follow the shared inline closeout contract:

{{spec-kit-include: ../common/inline-project-cognition-update.md}}
- Upgrade out of fast immediately when senior consequence analysis triggers for lifecycle, running-state, destructive-operation, shared-state, downstream consumer, compatibility, security, or multiple-behavior impact; record only the stand-down reason if it does not trigger.

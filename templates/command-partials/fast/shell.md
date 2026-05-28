{{spec-kit-include: ../common/user-input.md}}

## Objective

Execute a trivial, low-risk task directly in the current context without entering the full `specify -> plan -> tasks` workflow.

Use this for small fixes that are faster to execute than to plan: typo fixes, tiny config changes, missing imports, narrow doc edits, small bug fixes, and similarly bounded adjustments.

## Context

- Primary inputs: the user's request, the smallest relevant local files, passive learning files, and the project cognition safety gate.
- This path exists only for truly local work; the moment that assumption breaks, the task must leave the fast lane.
- Fast-path output is intentionally small and should not spawn planning artifacts.
- Workflow-owned mutation closeout is not external map maintenance. If fast-path work changes project-related source, runtime, templates, config, tests, generated assets, or behavior-bearing docs, run inline project cognition update from the changed paths before completion; use `project-cognition mark-dirty` only when inline update cannot complete. `sp-map-update` is for manual/external maintenance and follow-up repair, not routine cleanup for changes this workflow just made. In shared routing summaries, sp-map-update is for manual/external maintenance.
- Upgrade out of fast immediately when senior consequence analysis triggers for lifecycle, running-state, destructive-operation, shared-state, downstream consumer, compatibility, security, or multiple-behavior impact; record only the stand-down reason if it does not trigger.

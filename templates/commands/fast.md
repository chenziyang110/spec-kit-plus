---
description: Execute a trivial task directly without entering the full specify-plan workflow.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

## User Input

```text
$ARGUMENTS
```

## Objective
Execute a trivial, low-risk task directly in the current context without entering the full `specify -> plan -> tasks` workflow.

Use this for small fixes that are faster to execute than to plan: typo fixes, tiny config changes, missing imports, narrow doc edits, small bug fixes, and similarly bounded adjustments.

## Scope Gate

Before changing anything, decide whether this task is truly fast-path work.

Use `sp-fast` only when all of these are true:
- The task is clear in one sentence.
- The work should touch at most 3 files.
- No new dependencies are needed.
- No architecture changes are required.
- No API changes are required.
- No architecture, API, template system, roadmap, or spec workflow changes are required.
- No research or deep design work is needed.
- No subagents or parallel execution are needed.

If any of those checks fail:
- Use `/sp-quick` for small but non-trivial work.
- Use `/sp-specify` for work that needs full design and planning.

## Upgrade Triggers

Upgrade to `/sp-quick` immediately if:
- The work expands to more than 3 files.
- The change touches a shared surface such as a router table, registration file, export barrel, template registry, or other coordination point.
- The task stops being obvious and needs research or clarification to proceed safely.
- The task needs delegated execution, resumable tracking, or a written quick-task summary artifact.

Upgrade to `/sp-specify` immediately if:
- The request introduces a new workflow, role boundary, or user-visible behavior that needs explicit acceptance criteria.
- The change carries compatibility, migration, rollout, or neighboring-workflow risk.
- The task is no longer a bounded local fix and now changes architecture, APIs, long-lived templates, or planning assumptions.

## Process

1. **Scope gate**
   - Confirm the task fits the fast-path constraints above.
   - If not, stop and redirect to the right workflow instead of forcing the task through `sp-fast`.

2. **Read the routing layer**
   - Read `PROJECT-HANDBOOK.md`.
   - Use `Shared Surfaces` and `Risky Coordination Points` to decide whether the task is truly local.
   - If `PROJECT-HANDBOOK.md` or `.specify/project-map/` is missing, stop and redirect to `/sp-quick` so the navigation system can be rebuilt safely.
   - If the requested change touches a shared surface or risky coordination point, stop and redirect to `/sp-quick`.

3. **Execute inline**
   - Read the relevant file(s).
   - Do the work directly in the current context.
   - Keep the change as small and local as possible.

4. **Verify**
   - Run the smallest meaningful verification for the change.
   - Prefer targeted existing tests or a direct sanity check over broad workflows.

5. **Report**
   - Summarize what changed, what was verified, and any remaining risk.

## Guardrails

- No spec.md creation.
- No plan.md creation.
- No tasks.md creation.
- Do not spawn subagents.
- Do not add planning artifacts just to satisfy process formality.
- If the task grows while working, stop and redirect to `/sp-quick`.

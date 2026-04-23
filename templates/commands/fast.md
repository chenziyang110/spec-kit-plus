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
- The handbook says the touched area is a change-propagation hotspot, has explicit verification entry points beyond a trivial local check, or carries known unknowns that make direct execution unsafe.
- The task stops being obvious and needs research or clarification to proceed safely.
- The task needs delegated execution, resumable tracking, or a written quick-task summary artifact.

Upgrade to `/sp-specify` immediately if:
- The request introduces a new workflow, role boundary, or user-visible behavior that needs explicit acceptance criteria.
- The change carries compatibility, migration, rollout, or neighboring-workflow risk.
- The task is no longer a bounded local fix and now changes architecture, APIs, long-lived templates, or planning assumptions.

## Passive Project Learning Layer

- Before local execution, run `specify learning start --command fast --format json` when available so passive learning files exist, the current fast-path run sees relevant shared project memory, and repeated non-high-signal candidates can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader command-local context.
- Review `.planning/learnings/candidates.md` only when it still contains fast-path-relevant candidate learnings after the passive start step, especially repeated local pitfalls, routing constraints, or project defaults that affect whether the task should stay on `sp-fast`.
- Treat this as passive shared memory, not as a separate user-visible workflow.

## Process

1. **Scope gate**
   - Confirm the task fits the fast-path constraints above.
   - If not, stop and redirect to the right workflow instead of forcing the task through `sp-fast`.

2. **Read the routing layer**
   - Check whether `.specify/project-map/status.json` exists.
   - If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
   - If freshness is `missing` or `stale`, stop and redirect to `/sp-quick` or `/sp-map-codebase` so the navigation system can be rebuilt safely before fast-path execution.
   - If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If `must_refresh_topics` is non-empty for the current task, or if `review_topics` overlap shared surfaces, change-propagation hotspots, verification entry points, or known unknowns, stop and redirect to `/sp-quick`.
   - Read `PROJECT-HANDBOOK.md`.
   - Use `Shared Surfaces`, `Risky Coordination Points`, `Change-Propagation Hotspots`, `Verification Entry Points`, and `Known Unknowns` to decide whether the task is truly local.
   - If `PROJECT-HANDBOOK.md` or `.specify/project-map/` is missing, stop and redirect to `/sp-quick` so the navigation system can be rebuilt safely.
   - If the requested change touches a shared surface, risky coordination point, propagation hotspot, non-trivial verification entry point, or known-unknown-heavy area, stop and redirect to `/sp-quick`.

3. **Execute inline**
   - Read the relevant file(s).
   - Do the work directly in the current context.
   - Keep the change as small and local as possible.

4. **Verify**
   - Run the smallest meaningful verification for the change.
   - Prefer targeted existing tests or a direct sanity check over broad workflows.

5. **Report**
   - Summarize what changed, what was verified, and any remaining risk.
   - Before the final report, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning through `specify learning capture --command fast ...`.
   - Keep lower-signal items as candidates and use `specify learning promote --target learning ...` only after explicit confirmation or proven recurrence.
   - Only ask for confirmation when a new learning is highest-signal, such as an explicit user default, clear cross-stage reuse, or repeated recurrence that should become shared project memory.
   - If the fast-path change unexpectedly touched truth-owning surfaces, shared surfaces, command/route/contract boundaries, verification entry points, runtime assumptions, or other map-level coverage facts, and verification is truthfully green and no explicit blocker prevents completion, run `/sp-map-codebase` before the final report so `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, and `.specify/project-map/status.json` are refreshed in the same pass.
   - If that refresh would break the fast-path scope or cannot be completed safely in the current pass, mark `.specify/project-map/status.json` dirty through the project-map freshness helper and recommend `/sp-map-codebase`.

## Guardrails

- No spec.md creation.
- No plan.md creation.
- No tasks.md creation.
- Do not spawn subagents.
- Do not add planning artifacts just to satisfy process formality.
- If the task grows while working, stop and redirect to `/sp-quick`.

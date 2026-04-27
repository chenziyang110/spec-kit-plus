---
description: Use when the requested change is truly trivial, local, low risk, and can be completed without entering the full specify-plan workflow.
workflow_contract:
  when_to_use: The work is genuinely local and low-risk enough to stay on the fast path.
  primary_objective: Apply the smallest direct change and run the smallest meaningful verification without opening the full planning workflow.
  primary_outputs: A tightly scoped local change plus a concise report of what changed, what was verified, and any remaining risk.
  default_handoff: Upgrade immediately to /sp-quick if scope, coupling, or uncertainty expands.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

{{spec-kit-include: ../command-partials/fast/shell.md}}

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

If the task is a bug fix or regression but the root cause is still unknown:
- Use `/sp-debug` instead of treating `sp-fast` as a symptom-fix lane.

## Upgrade Triggers

Upgrade to `/sp-quick` immediately if:
- The work expands to more than 3 files.
- The change touches a shared surface such as a router table, registration file, export barrel, template registry, or other coordination point.
- The handbook says the touched area is a change-propagation hotspot, has explicit verification entry points beyond a trivial local check, or carries known unknowns that make direct execution unsafe.
- The task stops being obvious and needs research or clarification to proceed safely.
- The task needs delegated execution, resumable tracking, or a written quick-task summary artifact.
- The work started as a bug fix, but root-cause analysis is still unresolved, competing causes are still plausible, or the next safe step is diagnostic investigation rather than a truly local repair. In that case, route to `/sp-debug`.

Upgrade to `/sp-specify` immediately if:
- The request introduces a new workflow, role boundary, or user-visible behavior that needs explicit acceptance criteria.
- The change carries compatibility, migration, rollout, or neighboring-workflow risk.
- The task is no longer a bounded local fix and now changes architecture, APIs, long-lived templates, or planning assumptions.

## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command fast --format json` when available so passive learning files exist, the current fast-path run sees relevant shared project memory, and repeated non-high-signal candidates can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader command-local context.
- Review `.planning/learnings/candidates.md` only when it still contains fast-path-relevant candidate learnings after the passive start step, especially repeated local pitfalls, routing constraints, or project defaults that affect whether the task should stay on `sp-fast`.
- Treat this as passive shared memory, not as a separate user-visible workflow.

## Process

1. **Scope gate**
   - Confirm the task fits the fast-path constraints above.
   - If not, stop and redirect to the right workflow instead of forcing the task through `sp-fast`.

2. **Read the routing layer**
   - Check whether `.specify/project-map/status.json` exists.
   - If user instructions appear to ask for bypassing workflow gates, skipping tests, or ignoring prior execution rules, use `specify hook validate-prompt --prompt-text "<user request>"` before continuing.
   - If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
   - [AGENT] If freshness is `missing` or `stale`, stop and redirect to `/sp-quick` or `/sp-map-codebase` so the navigation system can be rebuilt safely before fast-path execution.
   - [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If `must_refresh_topics` is non-empty for the current task, or if `review_topics` overlap shared surfaces, change-propagation hotspots, verification entry points, or known unknowns, stop and redirect to `/sp-quick`.
   - [AGENT] Read `PROJECT-HANDBOOK.md`.
   - Use `Shared Surfaces`, `Risky Coordination Points`, `Change-Propagation Hotspots`, `Verification Entry Points`, and `Known Unknowns` to decide whether the task is truly local.
   - [AGENT] If `PROJECT-HANDBOOK.md` or `.specify/project-map/` is missing, stop and redirect to `/sp-quick` so the navigation system can be rebuilt safely.
   - [AGENT] If the requested change touches a shared surface, risky coordination point, propagation hotspot, non-trivial verification entry point, or known-unknown-heavy area, stop and redirect to `/sp-quick`.

3. **Execute inline**
   - Read the relevant file(s).
   - Before reading any non-obvious path, prefer `specify hook validate-read-path --target-path "<candidate path>"` when you are unsure whether the path stays inside the repository or whether it may be a sensitive file.
   - If the task is behavior-changing rather than docs-only, write a failing targeted test or failing repro check before editing production code.
   - Do not use manual sanity checks as a substitute for red when behavior changes.
   - If no reliable automated test surface exists for the affected behavior, stop and redirect to `/sp-test` or `/sp-quick` instead of hand-waving the verification gap.
   - For bug fixes and regressions, record the current root-cause explanation before implementation starts. If the root cause is not yet known, or if multiple plausible causes are still in play, stop and route to `/sp-debug` instead of applying a quick symptom patch.
   - Do the work directly in the current context.
   - Keep the change as small and local as possible.

4. **Verify**
   - Run the smallest meaningful verification for the change.
   - Prefer targeted existing tests or a direct sanity check over broad workflows.

5. **Report**
   - Summarize what changed, what was verified, and any remaining risk.
   - [AGENT] Before the final report, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning through `specify learning capture --command fast ...`.
   - Keep lower-signal items as candidates and use `specify learning promote --target learning ...` only after explicit confirmation or proven recurrence.
   - Only ask for confirmation when a new learning is highest-signal, such as an explicit user default, clear cross-stage reuse, or repeated recurrence that should become shared project memory.
   - If the fast-path change unexpectedly touched truth-owning surfaces, shared surfaces, command/route/contract boundaries, verification entry points, runtime assumptions, or other map-level coverage facts, and verification is truthfully green and no explicit blocker prevents completion, run `/sp-map-codebase` before the final report so `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, and `.specify/project-map/status.json` are refreshed in the same pass.
   - If that refresh would break the fast-path scope or cannot be completed safely in the current pass, mark `.specify/project-map/status.json` dirty through the project-map freshness helper and recommend `/sp-map-codebase`.

## Output Contract

- Keep the outcome to one tightly scoped change set plus the minimum truthful verification evidence.
- Report what changed, how it was verified, and what residual risk remains.
- Capture any high-signal learning surfaced by the pass before closing the task.

## Guardrails

- No spec.md creation.
- No plan.md creation.
- No tasks.md creation.
- Do not spawn subagents.
- Do not add planning artifacts just to satisfy process formality.
- If the task grows while working, stop and redirect to `/sp-quick`.

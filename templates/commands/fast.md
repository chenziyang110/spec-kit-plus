---
description: Use when the requested change is truly trivial, local, low risk, and can be completed without entering the full specify-plan workflow.
workflow_contract:
  when_to_use: The work is genuinely local and low-risk enough to stay on the fast path.
  primary_objective: Packetize the smallest safe low-risk change, delegate it through one subagent lane, and run the smallest meaningful verification without opening the full planning workflow.
  primary_outputs: A tightly scoped delegated change plus a concise report of what changed, what was verified, and any remaining risk.
  default_handoff: Upgrade immediately to /sp-quick if scope, coupling, or uncertainty expands.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

{{spec-kit-include: ../command-partials/fast/shell.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


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
- The lane can be handled by one tightly scoped subagent contract without broader planning artifacts.

If any of those checks fail:
- Use `/sp-quick` for small but non-trivial work.
- Use `/sp-specify` for work that needs full design and planning.

If the task is a bug fix or regression but the root cause is still unknown:
- Use `/sp-debug` instead of treating `sp-fast` as a symptom-fix lane.

## Upgrade Triggers

Upgrade to `/sp-quick` immediately if:
- The work expands to more than 3 files.
- The change touches a shared surface such as a router table, registration file, export barrel, template registry, or other coordination point.
- The handbook says the touched area is a change-propagation hotspot, has explicit verification entry points beyond a trivial local check, or carries known unknowns that make safe packetized delegation unavailable.
- The requested work comes from `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` and is larger than one tiny harness, command, fixture, or helper repair.
- The task stops being obvious and needs research or clarification to proceed safely.
- The task needs multiple subagent lanes, resumable tracking, or a written quick-task summary artifact.
- The work started as a bug fix, but root-cause analysis is still unresolved, competing causes are still plausible, or the next safe step is diagnostic investigation rather than a truly local repair. In that case, route to `/sp-debug`.

Upgrade to `/sp-specify` immediately if:
- The request introduces a new workflow, role boundary, or user-visible behavior that needs explicit acceptance criteria.
- The change carries compatibility, migration, rollout, or neighboring-workflow risk.
- The request is still a testing-system program from `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` instead of a tiny local repair.
- The task is no longer a bounded local fix and now changes architecture, APIs, long-lived templates, or planning assumptions.

## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command fast --format json` when available so passive learning files exist, the current fast-path run sees relevant shared project memory, and repeated candidates, including repeated high-signal candidates, can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader command-local context.
- Review `.planning/learnings/candidates.md` only when it still contains fast-path-relevant candidate learnings after the passive start step, especially repeated local pitfalls, routing constraints, or project defaults that affect whether the task should stay on `sp-fast`.
- [AGENT] When fast-path friction appears, run `specify hook signal-learning --command fast ...` with retry, route-change, validation-failure, false-start, or hidden-dependency counts; high friction usually means the task should leave `sp-fast`.
- [AGENT] Before final reporting, run `specify hook review-learning --command fast --terminal-status <resolved|blocked> ...`; use `--decision none --rationale "..."` only when no reusable `routing_mistake`, `pitfall`, `near_miss`, or `project_constraint` exists.
- [AGENT] Prefer `specify hook capture-learning --command fast ...` only for high-signal findings that should affect later workflows.
- Treat this as passive shared memory, not as a separate user-visible workflow.

## Process

1. **Scope gate**
   - Confirm the task fits the fast-path constraints above.
   - If not, stop and redirect to the right workflow instead of forcing the task through `sp-fast`.

2. **Read the routing layer**
   - Check whether `.specify/project-map/index/status.json` exists.
   - If user instructions appear to ask for bypassing workflow gates, skipping tests, or ignoring prior execution rules, use `specify hook validate-prompt --prompt-text "<user request>"` before continuing.
   - If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
   - [AGENT] If freshness is `missing` or `stale`, stop and redirect to `/sp-quick` or `/sp-map-scan` followed by `/sp-map-build` so the navigation system can be rebuilt safely before fast-path execution.
   - [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If `must_refresh_topics` is non-empty for the current task, or if `review_topics` overlap shared surfaces, change-propagation hotspots, verification entry points, or known unknowns, stop and redirect to `/sp-quick`.
   - [AGENT] Read `PROJECT-HANDBOOK.md`.
   - Use `Shared Surfaces`, `Risky Coordination Points`, `Change-Propagation Hotspots`, `Verification Entry Points`, and `Known Unknowns` to decide whether the task is truly local.
   - If `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` exists and the current task came from that brownfield testing-system program, read it before execution and confirm this pass is only one tiny harness, command, fixture, or helper repair.
   - [AGENT] If `PROJECT-HANDBOOK.md` or `.specify/project-map/` is missing, stop and redirect to `/sp-quick` so the navigation system can be rebuilt safely.
   - [AGENT] If the requested change touches a shared surface, risky coordination point, propagation hotspot, non-trivial verification entry point, or known-unknown-heavy area, stop and redirect to `/sp-quick`.

3. **Dispatch the fast lane**
   - Prepare the smallest task contract for the fast-path lane.
   - Keep the allowed write scope local and explicit.
   - Before reading any non-obvious path, prefer `specify hook validate-read-path --target-path "<candidate path>"` when you are unsure whether the path stays inside the repository or whether it may be a sensitive file.
   - If the task is behavior-changing rather than docs-only, write a failing targeted test or failing repro check before editing production code.
   - The task contract must include that RED gate before production edits.
   - Do not use manual sanity checks as a substitute for red when behavior changes.
   - If no reliable automated test surface exists for the affected behavior, stop and redirect to `/sp-test` (which routes to `/sp-test-scan`) or `/sp-quick` instead of hand-waving the verification gap.
   - For bug fixes and regressions, the task contract must record the current root-cause explanation before implementation starts. If the root cause is not yet known, or if multiple plausible causes are still in play, stop and route to `/sp-debug` instead of applying a quick symptom patch.
   - Dispatch one subagent for the lane.
   - Wait for the structured handoff before verification.
   - Keep the change as small and local as possible.

4. **Verify**
   - Run the smallest meaningful verification for the change.
   - Prefer targeted existing tests or a direct sanity check over broad workflows.

5. **Report**
   - Summarize what changed, what was verified, and any remaining risk.
   - [AGENT] Before the final report, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning through `specify learning capture --command fast ...`.
   - Keep lower-signal items as candidates and use `specify learning promote --target learning ...` only after explicit confirmation or proven recurrence.
   - Only ask for confirmation when a new learning is highest-signal, such as an explicit user default, clear cross-stage reuse, or repeated recurrence that should become shared project memory.
   - If the fast-path change unexpectedly touched truth-owning surfaces, shared surfaces, command/route/contract boundaries, verification entry points, runtime assumptions, or other map-level coverage facts, and verification is truthfully green and no explicit blocker prevents completion, run `/sp-map-scan` followed by `/sp-map-build` before the final report so `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, and `.specify/project-map/index/status.json` are refreshed in the same pass.
   - If that refresh would break the fast-path scope or cannot be completed safely in the current pass, mark `.specify/project-map/index/status.json` dirty through the project-map freshness helper and recommend `/sp-map-scan` followed by `/sp-map-build`.

## Output Contract

- Keep the outcome to one tightly scoped change set plus the minimum truthful verification evidence.
- Report what changed, how it was verified, and what residual risk remains.
- Capture any high-signal learning surfaced by the pass before closing the task.

## Guardrails

- No spec.md creation.
- No plan.md creation.
- No tasks.md creation.
- Use one fast-path subagent lane only; if more lanes are needed, route to `/sp-quick`.
- Do not add planning artifacts just to satisfy process formality.
- If the task grows while working, stop and redirect to `/sp-quick`.

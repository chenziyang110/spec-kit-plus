---
description: Use when the requested change is truly trivial, local, low risk, and can be completed without entering the full specify-plan workflow.
workflow_contract:
  when_to_use: The work is genuinely local and low-risk enough to stay on the fast path.
  primary_objective: Complete the smallest safe low-risk change directly and run the smallest meaningful verification without opening the full planning workflow.
  primary_outputs: A tightly scoped direct change plus a concise report of what changed, what was verified, and any remaining risk.
  default_handoff: Upgrade immediately to /sp-quick if scope, coupling, or uncertainty expands.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

{{spec-kit-include: ../command-partials/fast/shell.md}}

## Execution Mode

{{spec-kit-include: ../command-partials/common/dispatch-mode-gradient.md}}

**This command tier: trivial. Dispatch mode: leader-direct.**

The leader performs the change directly. No subagent dispatch. No task contract needed.


## Scope Gate

Use `sp-fast` only when ALL of:
- ≤3 files touched
- No shared registration surface (router table, export barrel, template registry)
- No protocol/contract boundary crossed
- No dependency changes
- Task is clear in one sentence
- Root cause known (if bug fix)

If any check fails → upgrade to `/sp-quick`.
If scope >10 files or crosses module boundary → upgrade to `/sp-specify`.

## Upgrade Triggers

Upgrade to `/sp-quick` immediately if:
- The work expands to more than 3 files.
- The change touches a shared surface such as a router table, registration file, export barrel, template registry, or other coordination point.
- The handbook says the touched area is a change-propagation hotspot, has explicit verification entry points beyond a trivial local check, or carries known unknowns that make safe direct execution unavailable.
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

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

**This command tier: trivial.** Skip all learning hooks. Do not read constitution, project-rules, or project-learnings. Do not run learning start, signal, review, or capture.

## Process

1. **Scope gate**
   - Confirm the task fits the fast-path constraints above.
   - If not, stop and redirect to the right workflow instead of forcing the task through `sp-fast`.

2. **Pass the atlas gate**
   - {{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}
   - **Project-map hard gate:** you must pass an atlas gate before reading
     implementation source, running reproduction, or preparing a fix.
   - **This command tier: trivial.** Pass the atlas gate by reading:
     1. `PROJECT-HANDBOOK.md`
     2. `atlas.entry`
     3. `atlas.index.status`
     4. `atlas.index.atlas`
     5. at least one relevant root topic document
     6. at least one relevant module overview document
   - Only after the atlas gate passes may you read the source files to change.

3. **Execute the fast lane**
   - Perform the fast-path change directly.
   - Keep the allowed write scope local and explicit.
   - Before reading any non-obvious path, prefer `{{specify-subcmd:hook validate-read-path --target-path "<candidate path>"}}` when you are unsure whether the path stays inside the repository or whether it may be a sensitive file.
   - If the task is behavior-changing rather than docs-only, write a failing targeted test or failing repro check before editing production code.
   - The direct execution notes must include that RED gate before production edits.
   - Do not use manual sanity checks as a substitute for red when behavior changes.
   - If no reliable automated test surface exists for the affected behavior, stop and redirect to `/sp-test-scan` or `/sp-quick` instead of hand-waving the verification gap.
   - If `.specify/testing/TESTING_PLAYBOOK.md` defines command-tier expectations for `fast smoke`, `focused`, and `full`, use fast smoke only as the cheapest early signal, run the focused tier as the fast-lane acceptance check, and reserve full for broader regression or final verification.
   - For bug fixes and regressions, record the current root-cause explanation before implementation starts. If the root cause is not yet known, or if multiple plausible causes are still in play, stop and route to `/sp-debug` instead of applying a quick symptom patch.
   - Keep the change as small and local as possible.

4. **Verify**
   - If playbook command tiers exist, focused is the fast-lane acceptance check.
   - Otherwise run the smallest meaningful local verification for the change.
   - Prefer targeted existing tests or a direct sanity check over broad workflows.

5. **Report**
   - Summarize what changed, what was verified, and any remaining risk.
   - [AGENT] Keep the fast-path closeout truthful: report the exact verification you ran and any residual risk instead of implying broader validation.
   - Treat git-baseline freshness in `.specify/project-map/index/status.json` as the truth source for the handbook/project-map atlas.
   - If the fast-path change unexpectedly touched truth-owning surfaces, shared surfaces, command/route/contract boundaries, verification entry points, runtime assumptions, or other map-level coverage facts, and verification is truthfully green and no explicit blocker prevents completion, run `/sp-map-scan` followed by `/sp-map-build` before the final report so `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, and `.specify/project-map/index/status.json` are refreshed in the same pass; then run `{{specify-subcmd:hook complete-refresh}}` as the successful-refresh finalizer.
   - If a full refresh can be completed now, do it; otherwise use `{{specify-subcmd:hook mark-dirty --reason "<reason>"}}` as the manual override/fallback and recommend `/sp-map-scan` followed by `/sp-map-build`.

## Output Contract

- Keep the outcome to one tightly scoped change set plus the minimum truthful verification evidence.
- Report what changed, how it was verified, and what residual risk remains.

## Guardrails

- No spec.md creation.
- No plan.md creation.
- No tasks.md creation.
- Use leader-direct execution only; if subagent lanes are needed, route to `/sp-quick`.
- Do not add planning artifacts just to satisfy process formality.
- If the task grows while working, stop and redirect to `/sp-quick`.

---
description: Use when you need a compatibility entrypoint that routes project-level testing-system work into scan or build phases.
workflow_contract:
  when_to_use: The user asks for `sp-test`, project-level testing bootstrap, testing-system refresh, testing coverage audit, or a brownfield unit-test program without naming whether they need scan or build.
  primary_objective: Route testing-system work to `/sp-test-scan` for evidence and build planning, or `/sp-test-build` for leader-managed execution from existing scan artifacts.
  primary_outputs: 'A truthful routing decision recorded in `.specify/testing/testing-state.md`, with handoff to `/sp-test-scan` or `/sp-test-build`; this compatibility command does not directly build the testing system.'
  default_handoff: /sp-test-scan when scan artifacts are missing or stale; /sp-test-build when scan/build-plan artifacts are ready and the user intends execution.
---

{{spec-kit-include: ../command-partials/test/shell.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command test --format json` when available so passive learning files exist and this compatibility route can reuse project testing learnings.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before routing when they exist.
- Review `.planning/learnings/candidates.md` only when it still contains testing-routing-relevant candidate learnings after the passive start step.
- [AGENT] When this compatibility entrypoint exposes a reusable route gap, run `specify hook signal-learning --command test ...` with route-change, false-start, or hidden-dependency counts.
- [AGENT] Before final routing or blocked reporting, run `specify hook review-learning --command test --terminal-status <resolved|blocked> ...`; use `--decision none --rationale "..."` only when no reusable `workflow_gap`, `routing_mistake`, or `state_surface_gap` exists.
- [AGENT] Prefer `specify learning capture-auto --command test --format json` when `testing-state.md` already captures the route reason or follow-up command. Fall back to `specify hook capture-learning --command test ...` when the durable state does not capture the reusable lesson cleanly.
- Treat this as passive shared memory, not as a separate user-visible workflow.

## Testing State Protocol

- `TESTING_STATE_FILE=.specify/testing/testing-state.md` is the compatibility routing state for `sp-test`.
- [AGENT] Create or resume `TESTING_STATE_FILE` before routing when `.specify/testing/` exists or can be safely created.
- Read `.specify/templates/testing/testing-state-template.md` when available.
- Record at least:
  - `active_command: sp-test`
  - `status: routing`
  - `scan_status`
  - `build_status`
  - `next_action`
  - `next_command`
  - `handoff_reason`

## Outline

1. **Establish repository context**
   - Confirm the repository root and treat this command as project-level.
   - Check whether `.specify/project-map/index/status.json` exists.
   - If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
   - [AGENT] If freshness is `missing` or `stale`, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
   - [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths, reasons, `must_refresh_topics`, and `review_topics`. If the testing surfaces are stale or weak, run `/sp-map-scan` followed by `/sp-map-build` before continuing. Otherwise review the relevant topic files before trusting the current map.
   - [AGENT] If `PROJECT-HANDBOOK.md` or the required `.specify/project-map/` files are missing, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
   - Treat testing-surface coverage as insufficient when the current handbook/project-map set cannot yet tell you:
     - which modules or packages own the main truth-bearing logic
     - which test frameworks and conventions already govern those modules
     - which workflows or integration seams are regression-sensitive
     - which startup, CI, or operator commands are required to run tests safely
   - [AGENT] If testing-surface coverage is insufficient for the current repository, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
   - [AGENT] Read `PROJECT-HANDBOOK.md`.
   - Read the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/STRUCTURE.md`, `.specify/project-map/root/CONVENTIONS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md`.
   - Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` when present.

2. **Inspect testing-system artifacts**
   - Check for `.specify/testing/TEST_SCAN.md`.
   - Check for `.specify/testing/TEST_BUILD_PLAN.md`.
   - Check for `.specify/testing/TEST_BUILD_PLAN.json`.
   - Check for `.specify/testing/TESTING_CONTRACT.md`.
   - Check for `.specify/testing/TESTING_PLAYBOOK.md`.
   - Check for `.specify/testing/COVERAGE_BASELINE.json`.
   - Check for `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md`.
   - Check for `.specify/testing/testing-state.md`.

3. **Classify user intent**
   - If the user asks for scan, audit, inventory, assessment, plan, blueprint, coverage gap analysis, or "what should we test", route to `/sp-test-scan`.
   - If the user asks to build, add tests, create fixtures, install/adopt framework config, raise coverage, or execute the testing-system plan, route to `/sp-test-build` only when scan/build-plan artifacts are ready.
   - If intent is ambiguous and scan artifacts are missing, route to `/sp-test-scan`.
   - If intent is ambiguous and scan/build-plan artifacts are ready, prefer `/sp-test-build` only when the user explicitly asked to make repository changes; otherwise route to `/sp-test-scan --refresh` semantics.

4. **Apply route gates**
   - Route to `/sp-test-scan` when:
     - `TEST_SCAN.md` is missing
     - `TEST_BUILD_PLAN.md` and `TEST_BUILD_PLAN.json` are missing
     - artifacts are stale relative to changed modules
     - existing scan lacks module-level evidence, lane readiness, write sets, or validation commands
     - the user requested report-only or audit-only behavior
   - Route to `/sp-test-build` when:
     - a scan exists
     - a build plan exists
     - at least one lane is `ready`
     - the user requested actual testing-system construction or refresh
   - Route to `/sp-map-scan` followed by `/sp-map-build` first when brownfield context is missing or stale enough that scan/build routing would be guesswork.

5. **Persist the route**
   - Update `TESTING_STATE_FILE` with:
     - `active_command: sp-test`
     - `status: routing`
     - `next_command: /sp-test-scan` or `next_command: /sp-test-build`
     - `handoff_reason`
     - discovered artifact paths
   - Do not write tests, production code, framework config, CI config, or coverage baselines from this compatibility entrypoint.

6. **Report and hand off**
   - Report exactly one next command.
   - Include the one-line reason for the route.
   - If routing to `/sp-test-build`, name the scan/build-plan artifacts being consumed.
   - If routing to `/sp-test-scan`, name the missing or stale evidence that makes scanning necessary.
   - [AGENT] Before final routing output, capture any new `routing_mistake`, `workflow_gap`, or `state_surface_gap` learning through `specify learning capture --command test ...` when the route exposed reusable workflow friction.

## Operating Rules

- `sp-test` is a compatibility router, not the testing-system builder.
- Do not collapse scan and build into one pass from this command.
- Do not ask whether to proceed when the route is obvious from artifacts and user intent.
- Use the user's current language for explanatory text while preserving literal command names, file paths, and status values exactly as written.

{{spec-kit-include: ../common/user-input.md}}

## Objective

Deep-scan the repository's testing surface and produce a build-ready unit-test system blueprint without changing code, tests, dependencies, or final testing contracts.

## Context

- This command is project-level, not feature-level. It operates on repository modules, test frameworks, public contracts, risk tiers, and coverage gaps.
- Primary inputs are live source/test files, manifest/config files, `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, existing `.specify/testing/` artifacts, and project memory.
- Primary outputs are `TEST_SCAN.md`, `TEST_BUILD_PLAN.md`, `TEST_BUILD_PLAN.json`, `UNIT_TEST_SYSTEM_REQUEST.md`, and `testing-state.md`.
- Treat bundled `*-testing` skills as built-in language testing guidance, not as external recommendations.

## Process

- Seed the scan with `specify testing inventory --format json`.
- Prioritize modules by risk tier before deep scanning.
- Dispatch read-only subagents for independent module, framework, coverage-command, or risk-review lanes when safe.
- Require concrete evidence from every scout: inspected files, public entrypoints, existing tests, missing scenarios, validation commands, and blockers.
- Compile build-ready lanes with readiness, write set, validation command, done condition, and join-point requirements.
- Write human-readable and machine-readable build plans for `/sp-test-build`.

## Output Contract

- Write `.specify/testing/TEST_SCAN.md`.
- Write `.specify/testing/TEST_BUILD_PLAN.md`.
- Write `.specify/testing/TEST_BUILD_PLAN.json`.
- Write `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md`.
- Update `.specify/testing/testing-state.md` with scan status, artifacts, ready lanes, and next command.
- Recommend exactly one next command.

## Guardrails

- This is read-only against repository implementation surfaces. Do not edit source code, tests, fixtures, framework config, dependency files, CI, final testing contracts, playbooks, or coverage baselines.
- Do not accept a scan lane that lacks inspected files and concrete missing scenarios unless it records an explicit blocker.
- Do not let raw coverage percentage outrank critical public-contract, error-path, state-transition, and regression-seam coverage.
- Do not dispatch subagents without a `TestScanPacket`.
- The leader owns synthesis; subagent results are evidence, not final policy.

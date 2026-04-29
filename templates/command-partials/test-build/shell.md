{{spec-kit-include: ../common/user-input.md}}

## Objective

Build or refresh the repository's unit testing system from scan-approved lanes through a leader-managed execution workflow.

## Context

- This command is project-level, not feature-level. It consumes `TEST_SCAN.md`, `TEST_BUILD_PLAN.md`, and preferably `TEST_BUILD_PLAN.json`.
- Primary inputs are scan artifacts, existing tests, live source files needed as read refs, testing templates, project map artifacts, and project memory.
- Durable outputs are repository-local tests/fixtures/config changes authorized by lane packets plus `TESTING_CONTRACT.md`, `TESTING_PLAYBOOK.md`, `COVERAGE_BASELINE.json`, and `testing-state.md`.
- Treat bundled `*-testing` skills as built-in language testing guidance selected by scan/build evidence.

## Process

- Validate scan/build-plan artifacts before selecting work.
- Choose the current ready wave and compile `TestBuildPacket` inputs for every executable lane.
- Dispatch subagents for bounded test-building lanes when packets are valid and write sets are isolated.
- Keep shared config, global fixture, CI, dependency, and production-code testability changes on serial leader-owned lanes unless explicitly authorized.
- Join every subagent result, run targeted validation, perform test-quality review, and update state before starting the next wave.
- Publish the final testing contract, playbook, and coverage baseline only after truthful validation evidence exists or explicit blockers are recorded.

## Output Contract

- Add or update tests, fixtures, helpers, or local test config only as authorized by ready build lanes.
- Write `.specify/testing/TESTING_CONTRACT.md`.
- Write `.specify/testing/TESTING_PLAYBOOK.md`.
- Write `.specify/testing/COVERAGE_BASELINE.json`.
- Update `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` when build evidence changes the brownfield testing program.
- Update `.specify/testing/testing-state.md` with current wave, lane, accepted/rejected results, validation evidence, open gaps, and next command.

## Guardrails

- Do not start without `TEST_SCAN.md` and a build plan unless the only safe action is routing back to `/sp-test-scan`.
- Do not dispatch subagents without a validated `TestBuildPacket`.
- Do not let subagents edit files outside their write set.
- Do not edit production code by default. Any testability refactor must be a leader-owned serial lane with an explicit reason and regression validation.
- Do not mark build complete without actual command evidence or a recorded blocker.

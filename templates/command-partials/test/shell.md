{{spec-kit-include: ../common/user-input.md}}

## Objective

Route project-level testing-system work into the right phase: `/sp-test-scan` for read-only evidence and build planning, or `/sp-test-build` for leader-managed construction from existing scan artifacts.

## Context

- This command is project-level, not feature-level. It operates on the repository's testing-system lifecycle rather than on a single `FEATURE_DIR`.
- Primary inputs are user intent, existing `.specify/testing/` artifacts, `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, and any project memory files.
- Scan outputs live under `.specify/testing/TEST_SCAN.md`, `.specify/testing/TEST_BUILD_PLAN.md`, `.specify/testing/TEST_BUILD_PLAN.json`, and `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md`.
- Build outputs live under `.specify/testing/TESTING_CONTRACT.md`, `.specify/testing/TESTING_PLAYBOOK.md`, `.specify/testing/COVERAGE_BASELINE.json`, and repository-local test assets.
- Treat the bundled `*-testing` skills as the built-in Spec Kit testing language lane. In the Spec Kit Plus source repo they live under `templates/passive-skills/*-testing/`; in generated projects they live under `.specify/templates/passive-skills/*-testing/`.

## Process

- Inspect user intent and existing testing artifacts.
- Route to `/sp-test-scan` when evidence, risk ranking, or build-ready lanes are missing or stale.
- Route to `/sp-test-build` when scan/build-plan artifacts are ready and the user intends actual repository changes.
- Route to `/sp-map-scan` followed by `/sp-map-build` first when brownfield navigation evidence is too stale or missing for a reliable testing-system decision.
- Persist the chosen route in `.specify/testing/testing-state.md`.

## Output Contract

- Write only routing state in `.specify/testing/testing-state.md`.
- Report exactly one next command: `/sp-test-scan`, `/sp-test-build`, or `/sp-map-scan` followed by `/sp-map-build`.
- Preserve compatibility for users who still invoke `/sp-test` while making the two-phase lifecycle explicit.

## Guardrails

- Do not edit tests, source code, framework config, CI, dependencies, coverage baselines, or final testing contracts from this compatibility router.
- Do not collapse scan and build into one pass.
- Prefer `/sp-test-scan` when the safe route is unclear.
- Keep the scope on unit-testing and unit-test-adjacent integration surfaces that strengthen TDD.

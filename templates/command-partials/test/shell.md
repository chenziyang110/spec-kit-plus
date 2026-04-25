{{spec-kit-include: ../common/user-input.md}}

## Objective

Bootstrap or refresh a durable project-wide unit testing system that future Spec Kit Plus workflows can rely on by default.

## Context

- This command is project-level, not feature-level. It operates on the repository's testing surface rather than on a single `FEATURE_DIR`.
- Primary inputs are the live repository, manifest/config files, existing tests, `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, and any project memory files.
- Durable outputs live under `.specify/testing/`, especially `TESTING_CONTRACT.md`, `TESTING_PLAYBOOK.md`, `COVERAGE_BASELINE.json`, and `testing-state.md`.
- Use the bundled language testing skills under `.specify/templates/passive-skills/*-testing/` as the framework-specific source of truth instead of improvising per-language test guidance.

## Process

- Inventory repository languages, modules, existing test frameworks, test commands, and coverage surfaces.
- Decide whether the run is `bootstrap`, `refresh`, or `audit-only` based on repository evidence and explicit user input.
- Select the appropriate bundled language testing skill for each module that needs test-system work.
- Establish or repair test framework config, supporting helpers, foundational unit tests, and coverage/report commands without rewriting stable user-owned tests unnecessarily.
- Generate a project-level testing contract and playbook that later workflows can consume automatically.
- Feed the testing contract back into planning, task generation, implementation, and debugging so testing remains current after this bootstrap pass.

## Output Contract

- Write or update `.specify/testing/TESTING_CONTRACT.md`, `.specify/testing/TESTING_PLAYBOOK.md`, `.specify/testing/COVERAGE_BASELINE.json`, and `.specify/testing/testing-state.md`.
- Record a module inventory showing language, adopted framework, current test surface, coverage status, key gaps, and the selected language testing skill.
- Produce a standard build/run/test/coverage workflow that later `sp-*` commands can reference without rediscovering local test conventions.

## Guardrails

- Do not delete existing user tests or replace a working framework unless repository evidence shows it is broken or missing a required baseline.
- Prefer extending an existing test layout over introducing a second parallel layout for the same module.
- Use `audit-only` behavior when the user explicitly asks for scan/report mode or when the repository evidence is too weak for safe automated changes.
- Keep the scope on unit-testing and unit-test-adjacent integration surfaces that strengthen TDD. Do not silently expand this workflow into broad E2E/browser/performance suites.
- Build a coverage baseline first and tighten enforcement through the generated contract instead of inventing unsupported global thresholds.

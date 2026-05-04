# Testing Playbook

This playbook defines the canonical local and CI testing workflow for this repository.

Control-plane role: newcomer-usable operating guide for where tests belong and which commands to run. Keep binding policy in `TESTING_CONTRACT.md`; keep scan evidence in `TEST_SCAN.md`.

## Environment Setup

- Required toolchains:
- Required package managers:
- Required environment variables:
- Optional local helpers:

## Install & Build

- Install dependencies:
- Build / compile / typecheck:
- Prepare fixtures or services:

## Run Tests

- fast smoke:
- focused:
- full:
- Run all unit tests:
- Run one module/package:
- Run one file:
- Run one test name/filter:

## Add New Tests

- Where tests belong:
  - small tests:
  - medium tests:
  - large tests:
- Naming conventions for new test files:
- Shared fixtures, mocks, or factories to reuse:
- Smallest RED-first command to run before implementation:
- Full validation command after adding tests:

## Coverage

- Generate coverage:
- Open or inspect coverage output:
- Record baseline updates:

## TDD Workflow

1. Write the failing test for the affected module or behavior.
2. Run the narrowest test command and confirm it fails for the expected reason.
3. Implement the smallest change that satisfies the test.
4. Re-run the narrow test, then the broader module command.
5. Run the full project validation command before claiming completion.

## CI / Release Validation

- CI unit-test command:
- CI coverage command:
- Required junit or machine-readable outputs:
- Release-blocking validation rules:

## Module Notes

### [Module Name]

- Framework:
- Test path:
- fast smoke command:
- focused command:
- full command:
- Coverage notes:

## Known Gaps

- Gap:
  - affected module:
  - impact:
  - recommended follow-up:

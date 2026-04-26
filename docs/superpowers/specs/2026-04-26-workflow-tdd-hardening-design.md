# Workflow TDD Hardening Design

**Date:** 2026-04-26  
**Status:** Implemented  
**Owner:** Codex

## Summary

This design hardens the executable `sp-*` workflows so Test-Driven Development is no
longer a passive suggestion that can be bypassed by template wording.

The repository already included a passive `test-driven-development` skill that says:

- `sp-implement` must start with a failing test
- `sp-debug` must start with a failing repro test
- `sp-fast` and `sp-quick` should still write tests first for bounded fixes

The problem was that the active workflow templates only partially reflected that
contract. In several places, they still allowed “edit first, verify later” behavior.

This hardening work makes the active execution workflows align with the existing TDD
skill and the repository’s intended quality bar.

## Problem Statement

Before this change, the workflow stack had an internal contradiction:

- the passive TDD skill enforced failing-test-first discipline
- the active execution templates did not consistently do so

The drift showed up in four ways:

1. `sp-fast` and `sp-quick` could move straight into edits and only verify after the
   change.
2. `sp-debug` required evidence and regression protection, but not a failing repro test
   before code changes.
3. `sp-implement` said “follow TDD” but only made the stronger test obligation
   explicit when a testing contract already existed.
4. `sp-tasks` still treated tests as optional unless the project-level testing
   contract was present, even though the task template itself already modeled RED-first
   sequencing.

This meant the repository claimed stronger TDD discipline than the active workflows
actually enforced.

## Goals

- Make behavior-changing execution workflows fail closed on TDD.
- Require a RED step before production code changes in:
  - `sp-fast`
  - `sp-quick`
  - `sp-implement`
  - `sp-debug`
- Make task generation default to TDD-friendly task ordering for behavior changes,
  bug fixes, and refactors even without a testing contract.
- Preserve `sp-test` as the project-level testing-system bootstrap lane when the
  missing piece is the test surface itself.

## Non-Goals

- Do not force tests for clearly docs-only or text-only changes.
- Do not require one universal test framework across all repositories.
- Do not collapse all testing concerns into `sp-test`; executable workflows should
  remain able to operate once the smallest viable test surface exists.
- Do not turn planning-only workflows such as `sp-specify` or `sp-plan` into code
  execution workflows.

## Approved Direction

The approved hardening model has five rules.

### 1. `sp-fast` Gets a RED Gate

If a fast-path change is behavior-changing rather than docs-only, the workflow must:

- write a failing targeted test or failing repro check first
- refuse to treat manual sanity checks as a substitute for RED
- route to `sp-test` or a heavier workflow if no reliable automated test surface exists

This keeps `sp-fast` lightweight while still preventing non-TDD code edits.

### 2. `sp-quick` Gets a RED Gate

For behavior changes, bug fixes, and refactors, the quick workflow must:

- make the first executable lane produce a failing automated test or failing repro
  check
- refuse production edits until RED is recorded
- bootstrap the smallest viable test surface first, or escalate to `sp-test` if that
  bootstrap is no longer a bounded quick-task step

This keeps quick work resumable and bounded without making it a loophole around TDD.

### 3. `sp-implement` Becomes Fail-Closed

`sp-implement` now treats failing-test-first as a hard execution gate for every
behavior-changing task, bug fix, or refactor.

The testing contract still matters, but it now adds module-specific commands, coverage
rules, and regression obligations. It no longer creates the base obligation to enter
RED first.

### 4. `sp-debug` Requires a Failing Repro Test

`sp-debug` now requires:

- a failing automated repro test before production code changes
- no production edits until RED is proven
- missing test harness setup first, or explicit routing through `sp-test`

This makes debugging consistent with the passive TDD skill instead of treating
regression tests as a post-fix add-on.

### 5. `sp-tasks` Defaults to TDD Task Ordering

Task generation now treats tests as default deliverables for:

- behavior changes
- bug fixes
- refactors

This is true whether or not `.specify/testing/TESTING_CONTRACT.md` already exists.

When the touched area lacks a reliable automated test surface, `sp-tasks` should add
bootstrap tasks early in the task graph instead of silently omitting RED work.

## Role of `sp-test`

`sp-test` remains the project-level testing-system bootstrap and refresh workflow.

Its job is to:

- establish or refresh the durable testing contract
- improve test infrastructure and commands
- route users toward the next workflow once the testing-system gap is understood

It is not the only place where TDD lives. The execution workflows themselves must stay
TDD-safe after this hardening.

## Workflow Effects

### `sp-fast`

- still for trivial local work
- no longer a valid route for “just patch it and sanity-check later”

### `sp-quick`

- still the bounded small-work lane
- no longer a valid route for behavior-changing work without RED first

### `sp-implement`

- still the main execution workflow
- now explicitly treats failing-test-first as a hard batch gate

### `sp-debug`

- still evidence-first and root-cause-driven
- now also enforces a failing repro test before production fixes

### `sp-tasks`

- still decomposes execution work
- now must preserve RED-first sequencing even without a prior testing contract

## Testing Strategy

The implementation should be locked by regression tests in these layers:

- workflow-template guidance tests for `fast`, `quick`, `debug`, and `test`
- testing-workflow guidance tests for `tasks`, `implement`, and `debug`
- skill-mirror tests so generated skills inherit the same hard-TDD language

## Decision

Proceed with shared workflow TDD hardening.

The repository should no longer rely on the passive TDD skill alone. The active
execution workflows themselves must enforce failing-test-first behavior so the system
is internally coherent and truly TDD-aligned.

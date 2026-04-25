# sp-test Testing Workflow Design

**Date:** 2026-04-25
**Status:** Proposed
**Owner:** Codex

## Summary

This design adds a new shared workflow skill, `sp-test`, that bootstraps and refreshes
project-wide unit testing systems for Spec Kit Plus repositories.

`sp-test` is not a one-off "write a few tests" helper. It is a project-level workflow
that:

- scans the repository for language and module boundaries
- chooses the correct bundled language testing skill for each module
- establishes or repairs framework, fixtures, coverage, and test commands
- writes a durable testing contract and playbook under `.specify/testing/`
- pushes that contract back into `sp-plan`, `sp-tasks`, `sp-implement`, and `sp-debug`

The intent is to make unit testing a durable contract that keeps later feature work in
the TDD loop instead of treating tests as an optional afterthought.

## Problem Statement

Spec Kit Plus already contains strong TDD and regression language in the constitution
template and several passive testing-related skills, but the main workflow still has a
gap:

- there is no explicit project-level workflow for bootstrapping a reliable unit testing
  system across an existing repository
- task generation still treats tests as optional unless the user explicitly asks for
  them
- implementation and debugging guidance mention testing, but do not consume a durable
  project-level testing contract
- multi-language testing skills exist outside the main workflow surface instead of being
  orchestrated through a single project-level command

This leaves brownfield projects with weak test baselines and prevents the main
`specify -> plan -> tasks -> implement` flow from naturally sustaining TDD after the
first setup.

## Goals

- Add a new shared `sp-test` workflow available across supported integrations.
- Support two modes:
  - `bootstrap`: establish a testing system where one does not yet exist
  - `refresh`: rescan and improve an existing testing system
- Vendor the prepared multi-language testing skills into bundled passive skills.
- Generate project-level testing assets under `.specify/testing/`.
- Make later workflows consume the testing contract automatically when it exists.
- Keep the implementation cross-CLI by default, with no Codex-only semantics in the
  shared workflow template.

## Non-Goals

- Do not build a new runtime service or separate CLI subcommand just for testing.
- Do not force every repository into one universal test framework.
- Do not delete or rewrite user-authored tests aggressively.
- Do not make coverage thresholds globally uniform across all languages.
- Do not add end-to-end or browser suites as part of the unit-testing contract unless
  the detected language skill explicitly treats them as part of the local testing stack.

## Approved Direction

The approved direction is:

1. Add an explicit shared workflow command: `sp-test`
2. Keep it as a support workflow, not a new mandatory phase between `plan` and `tasks`
3. Treat it as a project-level testing-system builder and refresher
4. Vendor multi-language testing skills into `templates/passive-skills/`
5. Write a durable project-level testing contract consumed by the main workflow

## Architecture Overview

The implementation has four layers.

### 1. Shared Workflow Surface

Add `templates/commands/test.md` plus `templates/command-partials/test/shell.md`.

This command defines:

- when `sp-test` should be used
- what repository evidence it must read
- how it distinguishes `bootstrap`, `refresh`, and `audit-only`
- what files it must generate or update
- what safety rails prevent broad destructive rewrites

### 2. Durable Testing Assets

`sp-test` writes project-level artifacts under `.specify/testing/`:

- `TESTING_CONTRACT.md`
- `TESTING_PLAYBOOK.md`
- `COVERAGE_BASELINE.json`
- `testing-state.md`

These assets become the durable testing truth for later workflows.

### 3. Bundled Language Testing Skills

Vendor the prepared testing skills into `templates/passive-skills/` using their current
language-specific names, for example:

- `python-testing`
- `js-testing`
- `go-testing`
- `java-testing`
- `kotlin-testing`
- `rust-testing`
- `php-testing`
- `ruby-testing`
- `cs-testing`
- `dart-testing`
- `swift-testing`
- `c-testing`
- `cpp-testing`
- `zig-testing`

`sp-test` orchestrates these passive skills rather than duplicating their language-level
guidance.

### 4. Main Workflow Contract Integration

When `.specify/testing/TESTING_CONTRACT.md` exists:

- `sp-plan` must read it and preserve testing strategy in `plan.md`
- `sp-tasks` must default to generating test work for affected modules
- `sp-implement` must treat the testing contract as a binding validation and TDD input
- `sp-debug` must treat regression tests as part of fix completion when the contract
  exists

This is the mechanism that keeps the testing system current after the initial bootstrap.

## Repository Outputs

### New Shared Workflow Assets

- `templates/commands/test.md`
- `templates/command-partials/test/shell.md`

### New Template Assets

- `templates/testing/testing-contract-template.md`
- `templates/testing/testing-playbook-template.md`
- `templates/testing/testing-state-template.md`
- `templates/testing/coverage-baseline-template.json`

### Workflow Documentation Updates

- `README.md`
- `AGENTS.md`
- generated init output strings in `src/specify_cli/__init__.py`

### Passive Skill Updates

- vendored language testing skills under `templates/passive-skills/`
- updated `spec-kit-workflow-routing`
- updated `spec-kit-project-learning`

## Safety Rules

- `sp-test` must support an `audit-only` mode through user input when the operator wants
  inventory and recommendations without file changes.
- It must not delete existing user tests.
- It must not replace a working framework unless repository evidence shows the current
  setup is unusable.
- It must prefer per-module or per-package decisions over all-repo uniform rewrites in
  mixed-language repositories.
- It must build a coverage baseline first and tighten enforcement later, rather than
  inventing unsupported thresholds.

## Follow-on Workflow Behavior

After `sp-test` succeeds, future feature work should behave as follows:

- `sp-specify` remains the feature-requirement entry point
- `sp-test` is the project testing-system setup and refresh lane
- `sp-plan` consumes the testing contract
- `sp-tasks` treats tests as default deliverables when the contract applies
- `sp-implement` keeps test updates and contract verification in the main execution loop
- `sp-debug` requires regression protection when the contract applies

This preserves the current mainline while making testing first-class and durable.

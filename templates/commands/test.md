---
description: Use when you need to bootstrap or refresh the project's unit testing system so later Spec Kit Plus workflows can keep tests current by default.
workflow_contract:
  when_to_use: The repository needs a durable unit testing system, testing contract, or coverage baseline before later feature work can stay reliably inside a TDD loop.
  primary_objective: Inventory the current test surface, establish or refresh framework/config/test coverage, and write a project-level testing contract that later workflows consume automatically.
  primary_outputs: '`.specify/testing/TESTING_CONTRACT.md`, `.specify/testing/TESTING_PLAYBOOK.md`, `.specify/testing/COVERAGE_BASELINE.json`, `.specify/testing/testing-state.md`, plus any repository-local test framework/config updates justified by the audit.'
  default_handoff: Resume `/sp-specify`, `/sp-plan`, `/sp-tasks`, `/sp-implement`, or `/sp-debug` with the generated testing contract in force.
---

{{spec-kit-include: ../command-partials/test/shell.md}}

## Pre-Execution Checks

**Check for extension hooks (before testing bootstrap/refresh)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_test` key.
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the testing inventory.
    ```
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently.

## Passive Project Learning Layer

- [AGENT] Run `specify learning start --command test --format json` when available so passive learning files exist, the current testing-system run sees relevant shared project memory, and repeated non-high-signal candidates can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader testing-system analysis.
- Review `.planning/learnings/candidates.md` only when it still contains testing-relevant candidate learnings after the passive start step, especially repeated flaky areas, framework constraints, or project defaults that should influence the generated testing contract.
- Treat this as passive shared memory, not as a separate user-visible workflow.

## Testing State Protocol

- `TESTING_STATE_FILE=.specify/testing/testing-state.md` is the project-level testing-system source of truth for `sp-test`.
- [AGENT] Create or resume `TESTING_STATE_FILE` before substantial testing analysis.
- Read `.specify/templates/testing/testing-state-template.md`.
- If `TESTING_STATE_FILE` exists and is non-terminal, resume from it instead of rebuilding intent from chat memory.
- Track at least:
  - `status: inventory | bootstrap | refresh | audit-only | validating | blocked | complete`
  - `mode: bootstrap | refresh | audit-only`
  - `selected_modules`
  - `selected_language_skills`
  - `next_action`
  - `open_gaps`
  - `adopted_frameworks`
  - `coverage_notes`

## Outline

1. **Establish repository context**
   - Confirm the repository root and treat this workflow as project-level rather than feature-level.
   - Check whether `.specify/project-map/status.json` exists.
   - If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
   - [AGENT] If freshness is `missing` or `stale`, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts.
   - [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths, reasons, `must_refresh_topics`, and `review_topics`. If the testing surfaces are stale or weak, run `/sp-map-codebase` before continuing. Otherwise review the relevant topic files before trusting the current map.
   - [AGENT] Read `PROJECT-HANDBOOK.md`.
   - Read the smallest relevant combination of `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md`.
   - Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` when present.

2. **Inventory the current testing surface**
   - Run `specify testing inventory --format json` from the repository root.
   - Treat the command output as the canonical starting inventory for:
     - `module_root`
     - `module_name`
     - `module_kind`
     - `language`
     - `manifest_path`
     - `selected_skill`
     - `framework`
     - `framework_confidence`
     - `canonical_test_path`
     - `canonical_test_command`
     - `coverage_command`
     - `state`
     - `classification_reason`
   - If the command returns no modules, fall back to direct repository inspection and record the gap explicitly instead of inventing fake module boundaries.
   - Record the inventory in `TESTING_STATE_FILE`.

3. **Choose the run mode**
   - If the user explicitly requests `audit-only`, `report-only`, or equivalent wording, set mode to `audit-only`.
   - Else if `.specify/testing/TESTING_CONTRACT.md` does not exist, or major modules have no usable unit-test framework/config, set mode to `bootstrap`.
   - Else set mode to `refresh`.

4. **Select bundled language testing skills**
   - Start from `selected_skill` in the `specify testing inventory --format json` payload.
   - Use the inventory result as the default skill choice unless newer repository evidence proves it wrong.
   - If a module already has a stable framework, keep the inventory-selected skill and extend that framework rather than rebuilding from scratch.
   - If the inventory identifies a language but no stable framework, use the selected language testing skill to choose the recommended default.
   - Record the final module -> skill mapping in `TESTING_STATE_FILE`, including any override reason when the runtime selection differs from the inventory payload.

5. **Choose an execution strategy before broad test-system work begins**
   - [AGENT] Before repository fan-out begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_execution_strategy(command_name="test", snapshot, workload_shape)`.
   - Strategy names are canonical and must be used exactly: `single-agent`, `native-multi-agent`, `sidecar-runtime`.
   - Decision order is fixed:
     - If the work does not justify safe fan-out -> `single-agent` (`no-safe-batch`)
     - Else if `snapshot.native_multi_agent` -> `native-multi-agent` (`native-supported`)
     - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime` (`native-missing`)
     - Else -> `single-agent` (`fallback`)
   - If collaboration is justified, keep `sp-test` lanes limited to:
     - repository and module test-surface inventory
     - framework/config adoption decisions
     - coverage baseline collection
     - testing contract and playbook drafting
   - Required join points:
     - before mutating shared repository test framework/config files
     - before writing the consolidated `.specify/testing/*` artifacts
   - Record the chosen strategy, reason, fallback if any, selected lanes, and join points in `TESTING_STATE_FILE`.

6. **Bootstrap or refresh the testing system**
   - For each selected module:
     - define the framework/config files that should exist
     - define the canonical test commands and coverage commands
     - define the minimum baseline test categories needed for safe TDD in that module
     - add or refresh foundational tests, fixtures, and helpers as justified by repository evidence
   - Prefer foundational unit-test coverage for truth-owning surfaces, shared coordination surfaces, validation logic, adapters, and bug-prone seams before broad low-signal test volume.
   - Do not delete or silently rewrite existing user-owned tests unless the user explicitly asks for cleanup.

7. **Generate durable testing assets**
   - Read `.specify/templates/testing/testing-contract-template.md`, `.specify/templates/testing/testing-playbook-template.md`, and `.specify/templates/testing/coverage-baseline-template.json`.
   - Write `.specify/testing/TESTING_CONTRACT.md` with:
     - project testing scope
     - mandatory testing rules for future work
     - module-level framework ownership
     - test update triggers
     - regression-test requirements for bug fixes
     - coverage baseline and threshold policy
   - Write `.specify/testing/TESTING_PLAYBOOK.md` with:
     - environment setup
     - install/build commands
     - run-all-tests command
     - targeted module/file test commands
     - coverage commands
     - CI commands
     - TDD loop guidance for this repository
   - Write `.specify/testing/COVERAGE_BASELINE.json` with current per-module baseline data and explicit unknowns where measurement is not yet reliable.

8. **Push the contract back into the main workflow**
   - Treat the generated testing contract as active project guidance for later `sp-plan`, `sp-tasks`, `sp-implement`, and `sp-debug` runs.
   - If the contract exists after this run, later workflows should no longer treat tests as globally optional for affected behavior changes.

9. **Validation and reporting**
   - Set `TESTING_STATE_FILE` to `validating` while checking:
     - the testing contract and playbook exist
     - the module inventory is complete enough for later workflows
     - canonical test and coverage commands are explicit
     - the selected framework ownership is recorded for each touched module
   - If a module could not be safely updated, record it as an explicit `open_gap` with the next recommended action.
   - Only mark the state `complete` after the contract, playbook, baseline, and inventory are all written truthfully.
   - [AGENT] Before the final completion report, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning through `specify learning capture --command test ...`.

10. **Check for extension hooks**
   - After reporting, check if `.specify/extensions.yml` exists in the project root.
   - If it exists, read it and look for entries under the `hooks.after_test` key.
   - If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
   - Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
   - For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
     - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
     - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
   - For each executable hook, output the same optional/mandatory hook blocks used by other workflows.

## Operating Rules

- Treat `audit-only` as a first-class mode that inventories and recommends without modifying repository files.
- Prefer extending an existing, working test system over replacing it.
- Focus on unit-testing and unit-test-adjacent regression safety for TDD. Do not silently broaden into a large E2E migration.
- If coverage measurement is unavailable for a module, record that explicitly in the baseline and playbook instead of inventing numbers.
- Use the user's current language for explanatory text while preserving literal command names, file paths, and status values exactly as written.

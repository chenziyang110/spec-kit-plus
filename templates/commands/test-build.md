---
description: Use when a completed test-system scan exists and you need to build or refresh the repository's unit testing system through leader-managed execution waves.
workflow_contract:
  when_to_use: A test-system scan has produced build-ready lanes, and the repository needs actual tests, fixtures, coverage commands, framework/config updates, or a durable testing contract.
  primary_objective: Execute the approved test-build waves with leader/subagent coordination, update repository-local test assets, and publish the testing contract, playbook, and baseline that later workflows consume automatically.
  primary_outputs: 'Updated tests/fixtures/config as authorized by `.specify/testing/TEST_BUILD_PLAN.md` or `.specify/testing/TEST_BUILD_PLAN.json`, plus `.specify/testing/TESTING_CONTRACT.md`, `.specify/testing/TESTING_PLAYBOOK.md`, `.specify/testing/COVERAGE_BASELINE.json`, and `.specify/testing/testing-state.md`.'
  default_handoff: 'Resume /sp.specify, /sp.plan, /sp.tasks, /sp.implement, or /sp.debug with the generated testing contract in force; route remaining testing-system waves through /sp-test-build.'
---

{{spec-kit-include: ../command-partials/test-build/shell.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


## Pre-Execution Checks

**Check for extension hooks (before testing build)**:
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

- [AGENT] Run `{{specify-subcmd:learning start --command test-build --format json}}` when available so passive learning files exist, the current testing-system build sees relevant shared project memory, and repeated candidates, including repeated high-signal candidates, can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader testing-system analysis.
- Review `.planning/learnings/candidates.md` only when it still contains testing-relevant candidate learnings after the passive start step, especially repeated flaky areas, framework constraints, or project defaults that should influence the generated testing contract.
- [AGENT] When testing-system build friction appears, use the `signal-learning` helper surface with validation-failure, artifact-rewrite, false-start, or hidden-dependency counts.
  Command shape: `{{specify-subcmd:hook signal-learning --command test-build --validation-failures <n> --artifact-rewrites <n> --false-start "<summary>"}}`
- [AGENT] Before final completion or blocked reporting, use the `review-learning` helper surface; use `--decision none` only when no reusable `verification_gap`, `state_surface_gap`, `pitfall`, `workflow_gap`, or `project_constraint` exists.
  Command shape: `{{specify-subcmd:hook review-learning --command test-build --terminal-status <resolved|blocked> --decision <none|captured|deferred> --rationale "<why>"}}`
- [AGENT] Prefer `{{specify-subcmd:learning capture-auto --command test-build --format json}}` when testing-state already captures reusable gaps, follow-up routing, or validation evidence.
- [AGENT] When `testing-state.md` does not capture the reusable lesson cleanly, use the manual `capture-learning` hook surface.
  Required options: `--command`, `--type`, `--summary`, `--evidence`
- Treat this as passive shared memory, not as a separate user-visible workflow.

## Testing State Protocol

- `TESTING_STATE_FILE=.specify/testing/testing-state.md` is the project-level testing-system source of truth for `sp-test-build`.
- [AGENT] Create or resume `TESTING_STATE_FILE` before substantial testing analysis.
- Read `.specify/templates/testing/testing-state-template.md`.
- If `TESTING_STATE_FILE` exists and is non-terminal, resume from it instead of rebuilding intent from chat memory.
- Track at least:
  - `active_command: sp-test-build`
  - `status: build-planning | executing | joining | validating | blocked | complete`
  - `build_status: pending | executing | blocked | complete`
  - `mode: bootstrap | refresh`
  - `selected_modules`
  - `selected_language_skills`
  - `next_action`
  - `next_command`
  - `handoff_reason`
  - `open_gaps`
  - `adopted_frameworks`
  - `coverage_notes`
  - `unit_test_system_request`
  - `test_scan`
  - `test_build_plan`
  - `test_build_plan_json`
  - `current_wave`
  - `current_lane`
  - `accepted_results`
  - `rejected_results`
  - `failed_validation`

## Outline

1. **Establish repository context**
   - Confirm the repository root and treat this workflow as project-level rather than feature-level.
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

2. **Validate scan/build inputs before execution**
   - [AGENT] Read `.specify/testing/TEST_SCAN.md`, `.specify/testing/TEST_BUILD_PLAN.md`, and `.specify/testing/TEST_BUILD_PLAN.json` before selecting work.
   - If none of those scan/build-plan artifacts exist, stop and route to `{{invoke:test-scan}}`; do not rebuild the scan from chat memory inside `sp-test-build`.
   - Treat `.specify/testing/TEST_BUILD_PLAN.json` as the machine-readable lane source when it exists. Use the Markdown plan only as human-readable context when both exist.
   - Refuse to start concrete build work unless at least one lane is `ready` and each ready lane has:
     - `lane_id`
     - `read_refs`
     - `write_set`
     - `allowed_actions`
     - `forbidden_actions`
     - `validation_command`
     - `done_condition`
   - Treat lanes marked `needs-leader-review`, `needs-research`, or `blocked` as non-executable until the leader resolves the missing decision and records the resolution in `TESTING_STATE_FILE`.
   - If a lane requests shared config, global fixture, CI, dependency, or production-code changes, the leader owns only the coordination, sequencing, review, and acceptance gate. When the change is safe, packetize it as a validated serial subagent lane that runs before any parallel subagent work starts. If a safe serial dispatch cannot be made, record `subagent-blocked` with the escalation or recovery reason and stop instead of making the edit directly.
   - Record the selected `current_wave`, `current_lane`, executable lanes, skipped lanes, and gate failures in `TESTING_STATE_FILE`.

3. **Inventory the current testing surface**
   - Run `{{specify-subcmd:testing inventory --format json}}` from the repository root.
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
     - `command_tiers`
     - `state`
     - `classification_reason`
   - If the command returns no modules, record the inventory gap, create a safe read-only recovery scan lane when one can be packetized, or stop with `subagent-blocked` for escalation instead of inventing fake module boundaries.
   - Record the inventory in `TESTING_STATE_FILE`.

4. **Choose the run mode**
   - If the user explicitly requests `audit-only`, `report-only`, or equivalent wording, stop and route to `{{invoke:test-scan}}`; `sp-test-build` is an execution workflow.
   - Else if `.specify/testing/TESTING_CONTRACT.md` does not exist, or major modules have no usable unit-test framework/config, set mode to `bootstrap`.
   - Else set mode to `refresh`.

5. **Select bundled language testing skills**
   - Start from `selected_skill` in the `{{specify-subcmd:testing inventory --format json}}` payload.
   - Use the inventory result as the default skill choice unless newer repository evidence proves it wrong.
   - Treat each selected `*-testing` skill as part of the built-in Spec Kit testing workflow lane used by `sp-test-scan` and `sp-test-build`, not as a separate plugin hunt or an unrelated optional addon.
   - If a module already has a stable framework, keep the inventory-selected skill and extend that framework rather than rebuilding from scratch.
   - If the inventory identifies a language but no stable framework, use the selected language testing skill to choose the recommended default.
   - When reporting the selection, explicitly tell the user which bundled skill was selected for each module and that the mapping comes from the bundled passive `*-testing` skills shipped with Spec Kit Plus.
   - Record the final module -> skill mapping in `TESTING_STATE_FILE`, including any override reason when the runtime selection differs from the inventory payload.

6. **Choose an execution dispatch shape before broad test-system work begins**
   - [AGENT] Before repository fan-out begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="test-build", snapshot, workload_shape)`.
   - Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
   - Decision order is fixed:
     - One safe validated test-build lane -> `one-subagent` on `native-subagents` when available.
     - Two or more safe isolated test-build lanes -> `parallel-subagents` on `native-subagents` when available.     - No safe lane, overlapping writes, missing packet, or unavailable delegation -> `subagent-blocked` with a recorded reason.
   - If collaboration is justified, keep `sp-test-build` lanes limited to:
     - bounded module test additions
     - local fixtures/helpers authorized by a lane packet
     - module-local coverage command execution
     - read-only test-quality review lanes
   - Required join points:
     - before mutating shared repository test framework/config files
     - after every parallel wave
     - before accepting a subagent result
     - before writing the consolidated `.specify/testing/*` artifacts
   - Record the chosen strategy, reason, any blocked dispatch or escalation decision, selected lanes, and join points in `TESTING_STATE_FILE`.

7. **Compile and validate `TestBuildPacket` inputs**
   - [AGENT] Compile a `TestBuildPacket` for each executable subagent lane before dispatch.
   - [AGENT] Validate each packet before dispatch. A valid `TestBuildPacket` must include:
     - `lane_id`
     - `wave_id`
     - `module`
     - `risk_tier`
     - `read_refs`
     - `write_set`
     - `allowed_actions`
     - `forbidden_actions`
     - `validation_command`
     - `done_condition`
     - `result_handoff_path`
   - Hard rule: do not dispatch from raw scan prose or raw Markdown checklist items alone.
   - Hard rule: a subagent may only edit files inside its `write_set`.
   - Hard rule: shared config, global fixtures, CI/presubmit, dependency, and production-code edits must be delegated through an explicit validated serial `TestBuildPacket` when safe. The leader owns coordination, review, and acceptance only. If the serial lane cannot be safely packetized or dispatched, record `subagent-blocked` and stop for escalation or recovery.
   - Store packet paths or packet summaries in `TESTING_STATE_FILE` before dispatch.
   - Use this packet shape when no runtime-specific packet schema exists:

     ```json
     {
       "lane_id": "build-cli-core-unit-tests-wave-1",
       "wave_id": "wave-1-critical-contracts",
       "module": "src/specify_cli",
       "risk_tier": "P0",
       "read_refs": ["src/specify_cli/__init__.py", ".specify/testing/TEST_BUILD_PLAN.md"],
       "write_set": ["tests/test_cli_core.py"],
       "allowed_actions": ["add tests", "add module-local fixtures"],
       "forbidden_actions": ["edit shared config", "rewrite existing tests", "edit production code"],
       "validation_command": "pytest tests/test_cli_core.py -q",
       "done_condition": "critical public CLI behavior has meaningful assertions and the targeted command passes",
       "result_handoff_path": ".specify/testing/worker-results/build-cli-core-unit-tests-wave-1.json"
     }
     ```

8. **Dispatch subagents and join results**
   - The invoking runtime acts as the test-build leader. It selects the current wave, dispatches bounded lanes, integrates results, and owns validation.
   - For `parallel-subagents`, dispatch subagents for all safe lanes in the current wave before any test-build work begins; if dispatch cannot cover the safe wave, record `subagent-blocked` with the blocker and stop for escalation or recovery.
   - For `one-subagent`, dispatch one subagent when the lane has a validated `TestBuildPacket` and enough context. If the packet is not yet safe, complete the packet before dispatch; if subagent dispatch is unavailable, record `subagent-blocked` with the blocker and stop for escalation or recovery before test-build implementation begins.
   - Subagents must return a structured handoff with:
     - `lane_id`
     - `reported_status: done | done_with_concerns | blocked | needs_context`
     - `changed_files`
     - `tests_added_or_changed`
     - `commands_run`
     - `command_results`
     - `open_gaps`
     - `quality_notes`
   - Idle subagent is not an accepted result.
   - The leader must wait for and consume every structured handoff before closing the join point, starting the next wave, or updating consolidated testing artifacts.
   - Rejected results must be recorded in `TESTING_STATE_FILE` under `rejected_results` with the reason and retry policy.

9. **Bootstrap or refresh the testing system**
   - For each selected module:
     - define the framework/config files that should exist
     - define the canonical test commands and coverage commands
     - define the minimum baseline test categories needed for safe TDD in that module
     - add or refresh foundational tests, fixtures, and helpers as justified by repository evidence
   - Push beyond happy-path-only scaffolding: critical public/module-facing behavior, truth-owning branches, boundary conditions, and known regression-prone error paths should receive meaningful automated coverage unless an explicit gap is recorded.
   - Run coverage after the first meaningful test pass, compare the result to the intended module thresholds, then iterate on uncovered critical paths instead of stopping at the first green run.
   - Keep iterating until thresholds are met or an explicit blocker is recorded with the uncovered hotspot, why it remains open, and the next recommended action.
   - Prefer foundational unit-test coverage for truth-owning surfaces, shared coordination surfaces, validation logic, adapters, and bug-prone seams before broad low-signal test volume.
   - Do not delete or silently rewrite existing user-owned tests unless the user explicitly asks for cleanup.

10. **Run test-quality review lanes**
   - After each wave, run a read-only test-quality review lane when the wave adds or changes non-trivial tests.
   - The reviewer checks:
     - tests assert public contracts or documented boundaries rather than private implementation details
     - assertions are meaningful and not smoke-only
     - mocks/fakes do not hide the behavior under test
     - fixtures are reusable without becoming global coupling
     - tests are not flaky or timing-dependent
     - existing testing style is preserved
   - The leader must either accept the review, repair the lane, or record a deliberate exception before the wave is considered joined.

11. **Generate durable testing assets**
   - Read `.specify/templates/testing/testing-contract-template.md`, `.specify/templates/testing/testing-playbook-template.md`, `.specify/templates/testing/coverage-baseline-template.json`, `.specify/templates/testing/unit-test-system-request-template.md`, `.specify/templates/testing/test-scan-template.md`, `.specify/templates/testing/test-build-plan-template.md`, and `.specify/templates/testing/test-build-plan-template.json`.
   - Write `.specify/testing/TESTING_CONTRACT.md` with:
     - project testing scope
     - covered-module rules, including covered-module status values and the minimum evidence required before a module can be treated as covered
     - mandatory testing rules for future work
     - module-level framework ownership
     - test update triggers
     - regression-test requirements for bug fixes
     - command-tier expectations for `fast smoke`, `focused`, and `full` commands
     - local integration seam expectations for module seams that require local fake/mock or integration-style coverage
     - coverage baseline and threshold policy
   - Write `.specify/testing/TESTING_PLAYBOOK.md` with:
     - environment setup
     - install/build commands
     - run-all-tests command
     - targeted module/file test commands
     - command-tier expectations for `fast smoke`, `focused`, and `full`, including when each tier should be run
     - covered-module rules that explain how to interpret covered-module status when adding or changing tests
     - local integration seam expectations and examples for adapter, filesystem, process, network, database, CLI, or workflow seams
     - coverage commands
     - CI commands
     - TDD loop guidance for this repository
     - where new tests belong, how they should be named, and which helper/fixture layers they should reuse
   - Preserve each lane's canonical `validation_command` when publishing command tiers. `validation_command` remains the lane acceptance command and compatibility field for existing packet consumers; do not replace it with a command-tier map. When command tiers are present, the lane's `focused` command should mirror the canonical `validation_command` unless the build plan records an explicit exception. The lane's `full` command is the broader regression/final-verification tier and must not be treated as the lane acceptance command.
   - Write `.specify/testing/COVERAGE_BASELINE.json` with current per-module baseline data and explicit unknowns where measurement is not yet reliable.
   - Write `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` as the professional-grade brownfield unit-test system request for later planning work. It must capture:
     - current test-surface assessment by module
     - `small / medium / large` test policy and target mix
     - public-contract testing rule plus mock / fake strategy
     - module risk tiers and module priority waves
     - scenario matrix rows for critical public behavior, invalid input, boundary conditions, exception handling, and local integration seams
     - coverage uplift waves, CI/presubmit gate policy, and allowed testability refactors
     - the recommended next workflow route when the work continues beyond this bootstrap pass

12. **Push the contract back into the main workflow**
   - Treat the generated testing contract as active project guidance for later `sp-plan`, `sp-tasks`, `sp-implement`, and `sp-debug` runs.
   - If the contract exists after this run, later workflows should no longer treat tests as globally optional for affected behavior changes.
   - Treat `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` as the primary brownfield testing-program input whenever the repository needs a phased unit-test construction or coverage uplift program.

13. **Validation and reporting**
   - Set `TESTING_STATE_FILE` to `validating` while checking:
     - the testing contract and playbook exist
     - the unit-test system request exists when brownfield test-system work was discovered
     - the module inventory is complete enough for later workflows
     - canonical test and coverage commands are explicit
     - the selected framework ownership is recorded for each touched module
   - Manually execute the canonical test commands and relevant coverage command at least once for each touched module when the environment supports it; if execution is blocked, record the exact blocker instead of pretending validation happened.
   - Record the most recent manual validation run in `TESTING_STATE_FILE`, including the command(s), timestamp, exit status, and a short result summary.
   - If a module could not be safely updated, record it as an explicit `open_gap` with the next recommended action.
   - Only mark the state `complete` after the contract, playbook, baseline, inventory, and successful manual validation evidence are all written truthfully; otherwise leave the run `blocked` or keep explicit open gaps.
   - Classify the next workflow recommendation before the final report.
   - Include the selected bundled language testing skills in the final report and note that they are part of the built-in `sp-test-scan` / `sp-test-build` testing workflow surface.
   - Include the most recent manual validation run in the final report so later workflows can see what was actually executed, not just what was documented.
   - Recommend exactly one next command and persist the recommendation in `TESTING_STATE_FILE` as `next_command`, `next_action`, and `handoff_reason`.
   - Route the recommendation using this order:
     - If no actionable gaps remain and the repository now has a usable testing contract, resume the previous workflow. If no prior workflow context is recoverable, fall back to the metadata default handoff.
     - If the remaining work is a single command, config, or helper repair with obvious local verification, recommend `{{invoke:fast}}`.
     - If the remaining work is a single bounded module or surface, such as one failing test file, one module-specific harness pass, or one local fixture/helper repair, recommend `{{invoke:quick}}`.
     - If the remaining work spans multiple modules, multiple failure classes, a coverage uplift program, or changes that need explicit scope and acceptance planning, recommend `{{invoke:specify}}`.
     - If the remaining work is an execution-time regression inside an already active feature and the failure still needs diagnosis, recommend `{{invoke:debug}}`.
     - If the remaining work is an execution-time regression inside an already active feature and the fix path is already understood and bounded, resume `{{invoke:implement}}`.
   - Include the recommended next command and one-line rationale in the final report so the workflow does not end in a dead-end audit summary.
   - When recommending `{{invoke:specify}}`, explicitly name `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` as required starting context for the brownfield testing-system program.
   - When recommending `{{invoke:quick}}` or `{{invoke:fast}}`, name the single module, risk tranche, coverage wave, or tiny harness/config/helper repair that should be executed next from the request.
- [AGENT] Before the final completion report, if auto-capture did not preserve a reusable `pitfall`, `workflow_gap`, or `project_constraint`, use the manual `learning capture` helper surface.
  Required options: `--command`, `--type`, `--summary`, `--evidence`

14. **Check for extension hooks**
   - After reporting, check if `.specify/extensions.yml` exists in the project root.
   - If it exists, read it and look for entries under the `hooks.after_test` key.
   - If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
   - Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
   - For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
     - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
     - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
   - For each executable hook, output the same optional/mandatory hook blocks used by other workflows.

## Operating Rules

- Treat `audit-only`, `report-only`, and equivalent wording as scan-only requests; route them to `{{invoke:test-scan}}` before any repository-modifying build work.
- Prefer extending an existing, working test system over replacing it.
- Focus on unit-testing and unit-test-adjacent regression safety for TDD. Do not silently broaden into a large E2E migration.
- If coverage measurement is unavailable for a module, record that explicitly in the baseline and playbook instead of inventing numbers.
- Use the user's current language for explanatory text while preserving literal command names, file paths, and status values exactly as written.

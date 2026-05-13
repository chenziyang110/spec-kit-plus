---
description: Use when you need a deep, read-only scan that turns a repository's testing gaps into a build-ready unit-test system plan.
workflow_contract:
  when_to_use: The repository needs evidence-backed testing-system analysis, risk-tiering, module-by-module coverage gaps, or build-ready testing lanes before any test construction begins.
  primary_objective: Coordinate read-only leader/subagent scan lanes, synthesize concrete module evidence, and produce a test-build blueprint that can drive the `sp-test-build` workflow without rediscovering the repository.
  primary_outputs: '`.specify/testing/TEST_SCAN.md`, `.specify/testing/TEST_BUILD_PLAN.md`, `.specify/testing/TEST_BUILD_PLAN.json`, `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md`, and `.specify/testing/testing-state.md`.'
  default_handoff: '/sp-test-build when one or more lanes are ready; /sp.specify, /sp.quick, or /sp.fast when the scan finds a narrower follow-up shape.'
---

{{spec-kit-include: ../command-partials/test-scan/shell.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command test-scan --format json}}` when available so passive learning files exist, the scan sees relevant shared project memory, and repeated testing-system lessons can be surfaced through the learning index at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broad scan work.
- Open only learning detail docs linked from testing-relevant index entries, especially repeated flaky areas, framework constraints, or project defaults that should influence the scan.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- [AGENT] When scan friction exposes route changes, false starts, hidden dependencies, validation gaps, or reusable constraints, make sure `testing-state.md` captures that durable context.
- [AGENT] Prefer `{{specify-subcmd:learning capture-auto --command test-scan --format json}}` when `testing-state.md` already captures reusable gaps, route reasons, or validation evidence.
- [AGENT] When durable state does not capture the reusable lesson cleanly, update `.specify/memory/learnings/INDEX.md` and a linked detail document with the command, type, summary, and evidence.
- Treat this as passive shared memory, not as a separate user-visible workflow.

## Testing State Protocol

- `TESTING_STATE_FILE=.specify/testing/testing-state.md` is the project-level testing-system source of truth for `sp-test-scan`.
- `.specify/testing/status.json` records testing scan freshness. Treat dependency manifests, lockfiles, workflow files, test config, or coverage config changes as `full-stale`; treat `src/**` or `tests/**` module-local files as `targeted-stale`; treat an empty relevant changed-file set as `fresh`.
- [AGENT] Create or resume `TESTING_STATE_FILE` before substantial testing analysis.
- Read `.specify/templates/testing/testing-state-template.md`.
- If `TESTING_STATE_FILE` exists with `active_command: sp-test-scan` and non-terminal scan state, resume from it instead of rebuilding intent from chat memory.
- Track at least:
  - `active_command: sp-test-scan`
  - `status: scanning | synthesizing | blocked | complete`
  - `scan_status: pending | scanning | blocked | complete`
  - `build_status`
  - `selected_modules`
  - `selected_language_skills`
  - `scan_artifacts`
  - `current_wave`
  - `current_lane`
  - `next_action`
  - `next_command`
  - `handoff_reason`
  - `open_gaps`

## Outline

1. **Establish repository context**
   - Confirm the repository root and treat this workflow as project-level rather than feature-level.
   - **Project cognition gate:** query the active project's runtime before broad
     repository reads.

     Run or emulate:

     ```text
     {{specify-subcmd:project-cognition query --intent test --query "$ARGUMENTS" --format json}}
     ```

     Use the returned readiness:

     - `ready`: continue with the returned task-local bundle.
     - `review`: perform only the returned `minimal_live_reads` before continuing.
     - `ambiguous`: ask the user to select the intended candidate.
     - `needs_update`: route through `{{invoke:map-update}}`.
     - `needs_rebuild`: route through `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
     - `blocked`: stop and report the blocking runtime issue.
   - Read `.specify/testing/TESTING_CONTRACT.md` and `.specify/testing/TESTING_PLAYBOOK.md` when present.
   - Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` when present; open only relevant linked learning detail docs.

2. **Run the canonical inventory seed**
   - Run `{{specify-subcmd:testing inventory --format json}}` from the repository root.
   - Treat the command output as the seed inventory for `module_root`, `module_name`, `module_kind`, `language`, `manifest_path`, `selected_skill`, `framework`, `framework_confidence`, `canonical_test_path`, `canonical_test_command`, `coverage_command`, `command_tiers`, `state`, and `classification_reason`.
   - If the command returns no modules, record the inventory gap, create a safe read-only recovery scan lane when one can be packetized, or stop with `subagent-blocked` for escalation instead of inventing fake module boundaries.
   - Record the raw inventory source and initial module list in `TESTING_STATE_FILE`.

3. **Select scan depth and module priority**
   - Classify modules into risk tiers:
     - `P0`: truth-owning logic, public API/CLI, state machines, safety/security boundaries, migration/schema/protocol seams
     - `P1`: adapters, integrations, IO, workflow orchestration, package/runtime boundaries
     - `P2`: helpers, utilities, leaf modules, low-risk internal transforms
     - `P3`: docs, demos, generated files, archived code, low-value surfaces
   - Deep-scan `P0` and `P1` by default.
   - Register `P2` and `P3` with rationale, but avoid spending equal effort on low-risk surfaces unless the repository has no higher-risk modules or the user explicitly requests full coverage.
   - Record why each module is included, deferred, or out of scope.

4. **Choose the scan dispatch shape**
   - [AGENT] Before repository fan-out begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="test-scan", snapshot, workload_shape)`.
   - Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
   - Decision order is fixed:
     - One safe validated scan lane -> `one-subagent` on `native-subagents` when available.
     - Two or more safe read-only testing scan lanes -> `parallel-subagents` on `native-subagents` when available.     - No safe lane, missing packet, or unavailable delegation -> `subagent-blocked` with a recorded reason.
   - Current-runtime native subagents are the default when safe read-only testing scan lanes exist.
   - For `one-subagent`, dispatch one read-only scout once a validated `TestScanPacket` or equivalent scan contract exists. If the packet is incomplete, compile the missing packet fields before dispatch; if dispatch is unavailable, record `subagent-blocked` with the blocker and stop for escalation or recovery before repository fan-out begins.
   - If collaboration is justified, keep `sp-test-scan` lanes read-only and limited to:
     - module test-surface scouting
     - framework/config evidence collection
     - coverage and command discovery
     - risk and scenario matrix discovery
     - read-only completeness review
   - Required join points:
     - before risk tier finalization
     - before writing `TEST_BUILD_PLAN.md` or `TEST_BUILD_PLAN.json`
     - before marking scan complete
   - Record the chosen strategy, reason, selected scan lanes, and join points in `TESTING_STATE_FILE`.

5. **Compile `TestScanPacket` lanes**
   - [AGENT] Compile a `TestScanPacket` for each scan lane before dispatch.
   - Every scan packet must include:
     - `lane_id`
     - `mode: read_only`
     - `scope`
     - `read_refs`
     - `required_outputs`
     - `forbidden_actions`
     - `handoff_path`
   - Required outputs for module scout lanes:
     - `module_boundaries`
     - `truth_owning_files`
     - `public_entrypoints`
     - `existing_test_surface`
     - covered-module status: `covered | partial | missing | unknown`
     - `missing_scenarios`
     - `risk_tier`
     - candidate command tiers: `fast smoke`, `focused`, and `full`
     - candidate layer mix: `small / medium / large`
     - local integration seams and their local integration seam expectations
     - `recommended_build_lanes`
     - `validation_commands`
     - `blockers`
   - Use this shape when no runtime-specific packet schema exists:

     ```json
     {
       "lane_id": "scan-python-cli-core",
       "mode": "read_only",
       "scope": ["src/specify_cli", "tests"],
       "read_refs": [
         "project-cognition query bundle",
         ".specify/testing/TESTING_CONTRACT.md",
         ".specify/testing/TESTING_PLAYBOOK.md"
       ],
       "required_outputs": [
         "module_boundaries",
         "truth_owning_files",
         "public_entrypoints",
         "existing_test_surface",
         "covered_module_status",
         "missing_scenarios",
         "risk_tier",
         "candidate_command_tiers",
         "candidate_layer_mix",
         "local_integration_seam_expectations",
         "recommended_build_lanes",
         "validation_commands",
         "blockers"
       ],
       "forbidden_actions": ["edit files", "install dependencies", "run destructive commands"],
       "handoff_path": ".specify/testing/worker-results/scan-python-cli-core.json"
     }
     ```

6. **Dispatch read-only scan subagents**
   - The invoking runtime acts as the scan leader. It selects lanes, dispatches read-only scouts, integrates results, resolves conflicts, and writes final artifacts.
   - If the selected dispatch shape is `one-subagent` or `parallel-subagents`, dispatch bounded read-only subagents before continuing broad leader analysis.
   - For a multi-module repository, prefer one scout per module, package, service, adapter group, or language boundary.
   - Add an optional framework scout when the testing framework, coverage command, or CI/presubmit path is unclear.
   - Add an optional read-only risk reviewer when the scan touches multiple P0/P1 modules or when scout outputs disagree.
   - Subagents must not edit files, install dependencies, rewrite tests, or update `.specify/testing/*` artifacts.
   - Subagents must return inspected files and concrete scenario evidence. A generic summary without inspected files, public entrypoints, missing scenarios, and recommended lanes is not acceptable.
   - Raw scan notes or raw chat summaries are not sufficient subagent inputs or outputs. Each dispatched lane needs a validated `TestScanPacket` and must return a structured handoff with inspected paths, module evidence, missing scenarios, recommended lanes, confidence, and blockers.
   - Idle subagent output is not an accepted scan result.
   - The leader must wait for every dispatched scan lane and consume its structured handoff before final risk ranking, writing build plans, or marking scan complete.

7. **Build module evidence records**
   - For every selected module, record:
     - module name and root
     - language and framework evidence
     - key files inspected
     - public entrypoints and contracts
     - truth-owning logic and high-risk branches
     - existing test files and helpers
     - covered-module status: `covered | partial | missing | unknown`, with evidence for the status instead of a raw coverage guess
     - missing happy-path, invalid-input, boundary, exception, state-transition, and local-integration scenarios
     - recommended `small / medium / large` test mix
     - candidate layer mix across `small / medium / large` tests for the next build lane
     - candidate command tiers: `fast smoke` for the cheapest confidence check, `focused` for the lane acceptance command, and `full` for the broader regression command
     - local integration seam expectations, including the adapter, filesystem, process, network, database, CLI, or workflow seam that needs local fake/mock or integration-style coverage
     - mock/fake strategy
     - candidate validation and coverage commands
     - blocker or uncertainty when evidence is incomplete
   - Do not mark a module scan complete unless it has concrete inspected-file evidence or an explicit blocker explaining why the scan could not go deeper.

8. **Compile build-ready lanes**
   - For every proposed lane, assign readiness:
     - `ready`: can be passed directly to the canonical `sp-test-build` workflow.
     - `needs-leader-review`: shared config, fixture, CI, dependency, production-code, or architecture decision required
     - `needs-research`: framework or command choice is not proven
     - `blocked`: dependency, environment, ownership, or path uncertainty prevents execution
   - Every `ready` lane must include:
     - `lane_id`
     - `wave_id`
     - objective
     - risk tier
     - read references
     - write set
     - allowed actions
     - forbidden actions
     - validation command
     - done condition
   - Shared config, global fixture, dependency, CI, and production-code testability work must be serial lanes unless explicitly proven parallel-safe.
   - Rank waves by risk-weighted value, not by raw coverage percentage.

9. **Generate scan artifacts**
   - Read `.specify/templates/testing/test-scan-template.md`, `.specify/templates/testing/test-build-plan-template.md`, `.specify/templates/testing/test-build-plan-template.json`, and `.specify/templates/testing/unit-test-system-request-template.md`.
   - Write `.specify/testing/TEST_SCAN.md` with evidence, module risk tiers, module findings, inspected files, missing scenarios, and blockers.
   - Write `.specify/testing/TEST_BUILD_PLAN.md` with human-readable coverage uplift waves, lanes, join points, readiness, validation commands, and done conditions.
   - Write `.specify/testing/TEST_BUILD_PLAN.json` with the same build lanes in a machine-readable shape.
   - Write `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` as the professional-grade brownfield unit-test system request for later planning or scoped follow-up workflows.
   - Do not write `.specify/testing/TESTING_CONTRACT.md`, `.specify/testing/TESTING_PLAYBOOK.md`, or `.specify/testing/COVERAGE_BASELINE.json` as final artifacts from scan. If needed, label proposed values as draft-only inside scan/build-plan artifacts.

10. **Validation and reporting**
   - Validate that `TEST_SCAN.md`, `TEST_BUILD_PLAN.md`, `TEST_BUILD_PLAN.json`, `UNIT_TEST_SYSTEM_REQUEST.md`, and `testing-state.md` exist.
   - Validate that every selected P0/P1 module has either concrete evidence or an explicit blocker.
   - Validate that every `ready` lane has read refs, write set, validation command, and done condition.
   - Validate that `TEST_BUILD_PLAN.json` can be parsed as JSON.
   - Recommend exactly one next command and persist it as `next_command`, `next_action`, and `handoff_reason` in `TESTING_STATE_FILE`.
   - Route recommendation:
     - If one or more lanes are `ready`, recommend `{{invoke:test-build}}`.
     - If only one tiny harness/config/helper repair is needed before build, recommend `{{invoke:fast}}`.
     - If one bounded module needs scope refinement, recommend `{{invoke:quick}}`.
     - If the remaining work spans multiple modules or a larger coverage program, recommend `{{invoke:specify}}` and name `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md` as required starting context.
     - If command/framework behavior is broken and root cause is unclear, recommend `{{invoke:debug}}`.
   - Include selected bundled language testing skills in the final report and note that they are part of the built-in `sp-test-scan` / `sp-test-build` testing workflow surface.
- [AGENT] Before the final completion report, if auto-capture did not preserve a reusable `verification_gap`, `workflow_gap`, `routing_mistake`, or `project_constraint`, use the manual `learning capture` helper surface.
  Required options: `--command`, `--type`, `--summary`, `--evidence`

## Operating Rules

- Treat this as a read-only scan workflow. Do not edit source code, tests, framework config, dependency files, CI, coverage config, or final testing contract/playbook/baseline artifacts.
- Use subagents for depth when the repository has independent module or framework scan lanes.
- Subagent output is evidence, not final policy. The leader owns synthesis, conflict resolution, risk ranking, and artifact truth.
- Prefer risk-weighted scenario coverage over superficial line-coverage chasing.
- Use the user's current language for explanatory text while preserving literal command names, file paths, and status values exactly as written.

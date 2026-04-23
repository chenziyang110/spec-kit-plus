---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).
Treat non-empty `$ARGUMENTS` as first-class implementation context for the current feature execution, not as disposable chat-only guidance.

## Pre-Execution Checks

**Check for extension hooks (before implementation)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_implement` key
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
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
    
    Wait for the result of the hook command before proceeding to the Outline.
    ```
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Passive Project Learning Layer

- Before deeper execution analysis, run `specify learning start --command implement --format json` when available so passive learning files exist and the current implementation run sees relevant shared project memory.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader execution context.
- Review `.planning/learnings/candidates.md` only when it contains implementation-relevant candidate learnings, especially repeated pitfalls, recovery paths, or project constraints for the touched area.
- Treat this as passive shared memory, not as a separate user-visible execution command.

## Implement Tracker Protocol

- `FEATURE_DIR/implement-tracker.md` is the execution-state source of truth for `sp-implement`.
- Create it if missing after `FEATURE_DIR` is known. If it already exists and is not terminal, resume from it instead of restarting from chat memory.
- Treat terminal states as `resolved` or `blocked`. Treat `gathering`, `executing`, `recovering`, `replanning`, and `validating` as resumable states.
- Update the tracker before each material phase transition: after scope recovery, before dispatching a ready batch, after each join point, before validation, when entering replanning, and before final completion reporting.
- The tracker must keep these fields obvious:
  - `status`
  - `current_batch`
  - `next_action`
  - `completed_tasks`
  - `failed_tasks`
  - `retry_attempts`
  - `blockers`
  - `recovery_action`
  - `open_gaps`
  - `user_execution_notes`
  - `resume_decision`
- If the user supplied important execution details in `$ARGUMENTS`, extract and persist them in the tracker before dispatching work. Typical examples include:
  - build or compile order
  - startup commands
  - required environment setup
  - known failing commands to avoid
  - recovery hints the runtime must remember on future resumes
- Treat these notes as binding for the current implementation run unless direct evidence shows they are wrong. Do not drop them silently on resume.
- Use this default structure:

```markdown
---
status: gathering | executing | recovering | replanning | validating | blocked | resolved
feature: [feature slug]
created: [ISO timestamp]
updated: [ISO timestamp]
resume_decision: resume-here | blocked-waiting | resolved
---

## Current Focus
current_batch: [ready batch or validation pass]
goal: [current implementation objective]
next_action: [immediate next step]

## Execution State
completed_tasks:
  - [task ids already completed]
in_progress_tasks:
  - [task ids currently running]
failed_tasks:
  - [task ids that failed in the current pass]
retry_attempts: [0 if none]

## Blockers
- task: [task id]
  type: technical | external | human-action
  evidence: [short command output or observed failure]
  recovery_action: [smallest safe next recovery step]

## Validation
planned_checks:
  - [independent tests, acceptance checks, or validation commands]
completed_checks:
  - [checks already run]
human_needed_checks:
  - [manual verification still required]

## Open Gaps
- type: execution_gap | research_gap | plan_gap | spec_gap
  summary: [what is still not true]
  source: [task id, validation check, or user-visible outcome]
  next_action: [specific next step]

## User Execution Notes
- note: [important user-supplied execution detail from `$ARGUMENTS`]
  source: sp-implement arguments
  priority: high | normal
  applies_to: current feature execution
```

## Outline

1. Run `{SCRIPT}` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Check checklists status** (if FEATURE_DIR/checklists/ exists):
   - Scan all checklist files in the checklists/ directory
   - For each checklist, count:
     - Total items: All lines matching `- [ ]` or `- [X]` or `- [x]`
     - Completed items: Lines matching `- [X]` or `- [x]`
     - Incomplete items: Lines matching `- [ ]`
   - Create a status table:

     ```text
     | Checklist | Total | Completed | Incomplete | Status |
     |-----------|-------|-----------|------------|--------|
     | ux.md     | 12    | 12        | 0          | ✓ PASS |
     | test.md   | 8     | 5         | 3          | ✗ FAIL |
     | security.md | 6   | 6         | 0          | ✓ PASS |
     ```

   - Calculate overall status:
     - **PASS**: All checklists have 0 incomplete items
     - **FAIL**: One or more checklists have incomplete items

   - **If any checklist is incomplete**:
     - Display the table with incomplete item counts
     - **STOP** and ask: "Some checklists are incomplete. Do you want to proceed with implementation anyway? (yes/no)"
     - Wait for user response before continuing
     - If user says "no" or "wait" or "stop", halt execution
     - If user says "yes" or "proceed" or "continue", proceed to step 3

   - **If all checklists are complete**:
     - Display the table showing all checklists passed
     - Automatically proceed to step 3

3. Load and analyze the implementation context:
   - **REQUIRED**: Create or resume `FEATURE_DIR/implement-tracker.md` immediately after `FEATURE_DIR` is known.
   - **IF TRACKER EXISTS WITH STATUS `blocked` OR `replanning`**: Read `blockers`, `open_gaps`, `recovery_action`, and `next_action` first, then continue from that state instead of restarting the workflow from scratch.
   - **IF TRACKER EXISTS WITH STATUS `validating`**: Resume the unfinished validation checks before considering any new implementation work.
   - **IF TRACKER EXISTS WITH STATUS `executing` OR `recovering`**: Resume from the recorded `current_batch`, `failed_tasks`, and `retry_attempts` rather than recomputing progress from chat narration.
   - **IF `$ARGUMENTS` IS NON-EMPTY**: Extract any high-signal execution constraints, environment facts, build instructions, startup instructions, or recovery hints and record them under `## User Execution Notes` in `implement-tracker.md` before choosing the next batch.
   - **REQUIRED**: Check whether `.specify/project-map/status.json` exists.
   - **IF STATUS EXISTS**: Use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
   - **IF FRESHNESS IS `missing` OR `stale`**: Run `/sp-map-codebase` before continuing, then reload the generated handbook/project-map navigation system.
   - **IF FRESHNESS IS `possibly_stale`**: Inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If `must_refresh_topics` is non-empty for the current implementation area, run `/sp-map-codebase` before continuing. If only `review_topics` are non-empty, review those topic files before trusting the current map for implementation decisions.
   - **REQUIRED**: Check whether `PROJECT-HANDBOOK.md` exists at the repository
     root.
   - **REQUIRED**: Check whether `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md` exist.
   - **IF MISSING**: Run `/sp-map-codebase` before continuing, then reload the generated handbook/project-map navigation system.
   - **TREAT TASK-RELEVANT COVERAGE AS INSUFFICIENT** when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
   - **IF TASK-RELEVANT COVERAGE IS INSUFFICIENT**: Run `/sp-map-codebase` before continuing, then reload the generated handbook/project-map navigation system.
   - **REQUIRED**: Read `PROJECT-HANDBOOK.md`.
   - **REQUIRED**: Read the smallest relevant combination of `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md`.
   - **IF TOPICAL COVERAGE IS MISSING/STALE/TOO BROAD OR TASK-RELEVANT COVERAGE IS INSUFFICIENT**: run `/sp-map-codebase` before continuing, then inspect the minimum live files still needed to replace guesswork with evidence.
   - **REQUIRED**: Read `.specify/memory/constitution.md` if present.
   - **REQUIRED**: Read `.specify/memory/project-rules.md` if present.
   - **REQUIRED**: Read `.specify/memory/project-learnings.md` if present.
   - **IF `.planning/learnings/candidates.md` EXISTS**: Inspect only the entries relevant to implementation so repeated pitfalls, recovery paths, and project constraints are not rediscovered from scratch.
   - **REQUIRED**: Read tasks.md for the complete task list and execution plan
   - **REQUIRED**: Read plan.md for tech stack, architecture, and file structure
   - **REQUIRED**: Extract `Implementation Constitution` from `plan.md` when present and treat it as binding execution guidance rather than advisory background
   - **IF EXISTS**: Read data-model.md for entities and relationships
   - **IF EXISTS**: Read contracts/ for API specifications and test requirements
   - **IF EXISTS**: Read research.md for technical decisions and constraints
   - **IF EXISTS**: Read quickstart.md for integration scenarios
   - **IF `Implementation Constitution` NAMES REQUIRED REFERENCES**: Read those boundary-defining files before choosing the next implementation batch
   - **IF THE NEXT READY BATCH TOUCHES AN ESTABLISHED BOUNDARY OR FRAMEWORK**: Record the active boundary framework, preserved pattern, forbidden drift, and required references in `implement-tracker.md` before dispatching work
    - **REQUIRED FOR DELEGATED EXECUTION**: compile a `WorkerTaskPacket` for each delegated task using `.specify/memory/constitution.md`, `plan.md`, and `tasks.md`
    - **REQUIRED FOR DELEGATED EXECUTION**: compile and validate the packet before any delegated work begins
    - **REQUIRED FOR DELEGATED EXECUTION**: Validate each `WorkerTaskPacket` before dispatching work
    - **REQUIRED FOR DELEGATED EXECUTION**: Use `.specify/templates/worker-prompts/implementer.md` as the default implementer worker contract and pair post-implementation reviews with `.specify/templates/worker-prompts/spec-reviewer.md` and `.specify/templates/worker-prompts/code-quality-reviewer.md`
    - **REQUIRED FOR DELEGATED EXECUTION**: Prefer structured handoffs compatible with the shared `WorkerTaskResult` contract whenever the current runtime exposes structured delegated results
    - **REQUIRED FOR DELEGATED EXECUTION**: If the current integration exposes a runtime-managed result channel, use that channel. Otherwise write the normalized delegated result envelope to `FEATURE_DIR/worker-results/<task-id>.json`
    - **REQUIRED FOR DELEGATED EXECUTION**: When the local CLI is available and no runtime-managed result channel exists, prefer `specify result path` to compute the canonical handoff target and `specify result submit` to normalize and write the result envelope
    - **REQUIRED FOR DELEGATED EXECUTION**: Preserve `reported_status` when normalizing worker language such as `DONE_WITH_CONCERNS` or `NEEDS_CONTEXT` into canonical orchestration state
    - **HARD RULE**: dispatch only from validated `WorkerTaskPacket`
    - **HARD RULE**: Do not dispatch from raw task text alone
    - **HARD RULE**: must not dispatch from raw task text alone

4. **Project Setup Verification**:
   - **REQUIRED**: Create/verify ignore files based on actual project setup:

   **Detection & Creation Logic**:
   - Check if the following command succeeds to determine if the repository is a git repo (create/verify .gitignore if so):

     ```sh
     git rev-parse --git-dir 2>/dev/null
     ```

   - Check if Dockerfile* exists or Docker in plan.md → create/verify .dockerignore
   - Check if .eslintrc* exists → create/verify .eslintignore
   - Check if eslint.config.* exists → ensure the config's `ignores` entries cover required patterns
   - Check if .prettierrc* exists → create/verify .prettierignore
   - Check if .npmrc or package.json exists → create/verify .npmignore (if publishing)
   - Check if terraform files (*.tf) exist → create/verify .terraformignore
   - Check if .helmignore needed (helm charts present) → create/verify .helmignore

   **If ignore file already exists**: Verify it contains essential patterns, append missing critical patterns only
   **If ignore file missing**: Create with full pattern set for detected technology

   **Common Patterns by Technology** (from plan.md tech stack):
   - **Node.js/JavaScript/TypeScript**: `node_modules/`, `dist/`, `build/`, `*.log`, `.env*`
   - **Python**: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `*.egg-info/`
   - **Java**: `target/`, `*.class`, `*.jar`, `.gradle/`, `build/`
   - **C#/.NET**: `bin/`, `obj/`, `*.user`, `*.suo`, `packages/`
   - **Go**: `*.exe`, `*.test`, `vendor/`, `*.out`
   - **Ruby**: `.bundle/`, `log/`, `tmp/`, `*.gem`, `vendor/bundle/`
   - **PHP**: `vendor/`, `*.log`, `*.cache`, `*.env`
   - **Rust**: `target/`, `debug/`, `release/`, `*.rs.bk`, `*.rlib`, `*.prof*`, `.idea/`, `*.log`, `.env*`
   - **Kotlin**: `build/`, `out/`, `.gradle/`, `.idea/`, `*.class`, `*.jar`, `*.iml`, `*.log`, `.env*`
   - **C++**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.so`, `*.a`, `*.exe`, `*.dll`, `.idea/`, `*.log`, `.env*`
   - **C**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.a`, `*.so`, `*.exe`, `*.dll`, `autom4te.cache/`, `config.status`, `config.log`, `.idea/`, `*.log`, `.env*`
   - **Swift**: `.build/`, `DerivedData/`, `*.swiftpm/`, `Packages/`
   - **R**: `.Rproj.user/`, `.Rhistory`, `.RData`, `.Ruserdata`, `*.Rproj`, `packrat/`, `renv/`
   - **Universal**: `.DS_Store`, `Thumbs.db`, `*.tmp`, `*.swp`, `.vscode/`, `.idea/`

   **Tool-Specific Patterns**:
   - **Docker**: `node_modules/`, `.git/`, `Dockerfile*`, `.dockerignore`, `*.log*`, `.env*`, `coverage/`
   - **ESLint**: `node_modules/`, `dist/`, `build/`, `coverage/`, `*.min.js`
   - **Prettier**: `node_modules/`, `dist/`, `build/`, `coverage/`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
   - **Terraform**: `.terraform/`, `*.tfstate*`, `*.tfvars`, `.terraform.lock.hcl`
   - **Kubernetes/k8s**: `*.secret.yaml`, `secrets/`, `.kube/`, `kubeconfig*`, `*.key`, `*.crt`

5. Parse tasks.md structure and extract:
   - **Task phases**: Setup, Tests, Core, Integration, Polish
   - **Task dependencies**: Sequential vs parallel execution rules
   - **Task details**: ID, description, file paths, parallel markers [P]
   - **Ready tasks**: Tasks whose prerequisites are complete within the current phase
   - **Parallel batches**: Ready tasks that can execute together without write-set conflicts
   - **Join points**: Synchronization steps that must complete before downstream work starts
   - **Execution flow**: Order and dependency requirements

6. Select an execution strategy for each ready batch before writing code:
   - The invoking runtime acts as the leader: it reads the current planning artifacts, selects the next executable phase and ready batch, and dispatches work instead of performing concrete implementation directly.
   - The shared implement template is the primary source of truth for this leader-only milestone scheduler contract, and integration-specific addenda must preserve the same semantics.
   - Use the shared policy function before each batch with the current agent capability snapshot: `choose_execution_strategy(command_name="implement", snapshot, workload_shape)`
   - Also classify whether the current batch needs a review gate before the join point: `classify_review_gate_policy(workload_shape)`
   - Strategy names are canonical and must be used exactly: `single-agent`, `native-multi-agent`, `sidecar-runtime`
   - Treat `snapshot.delegation_confidence` as a runtime/model reliability signal for native delegation. If confidence is `low`, do not force native worker fan-out just because the integration can theoretically support it.
   - Decision order (must match policy):
      - If `parallel_batches <= 0` or overlapping write sets -> `single-agent` (`no-safe-batch`)
      - Else if `snapshot.native_multi_agent` and `snapshot.delegation_confidence` is not `low` -> `native-multi-agent` (`native-supported`)
      - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime` (`native-missing` or `native-low-confidence`)
      - Else -> `single-agent` (`fallback` or `fallback-low-confidence`)
   - single-agent still means one delegated worker lane, not leader self-execution.
   - Re-evaluate the execution strategy at every new parallel batch or join point instead of choosing once for the whole feature
   - Refine only the current executable window after each join point. Do not pre-expand later batches when their exact shape depends on current batch evidence.
   - Grouped parallelism is the default when multiple ready tasks have isolated write sets and stable upstream inputs.
   - Pipeline execution is preferred when outputs flow stage-by-stage from one bounded task to the next and each stage becomes the next stage's input.
   - Every pipeline stage still needs an explicit checkpoint before downstream work continues.
   - If `classify_review_gate_policy(workload_shape)` requires review, do not cross the join point until the batch has passed worker self-check and leader acceptance.
   - If the policy recommends a peer-review lane and a read-only verification lane is available, run one peer-review lane for the high-risk batch before the leader accepts it.
   - Reserve peer-review lanes for high-risk batches such as shared registration surfaces, schema changes, protocol seams, native/plugin bridges, or generated API surfaces.
   - When `sidecar-runtime` is selected, use the integration's coordinated runtime surface for the current ready batch, report concrete blockers, keep join-point semantics explicit, and surface retry-pending or blocked runtime state truthfully so runtime/API handoffs stay auditable and safe.
    - Before dispatching a concrete implementation batch, answer from repository evidence:
      - What framework or boundary pattern owns the touched surface?
      - Which files define the existing pattern that must be preserved?
      - What implementation drift is forbidden for this batch?
      - Which task or plan item proves that this constraint is intentional rather than inferred?
      - Which compiled `WorkerTaskPacket` captures the hard rules, required references, validation gates, and done criteria for this delegated task?
    - If those answers are not grounded in the current repository files, stop guesswork, read the missing references, and update `implement-tracker.md` before continuing.

7. Execute implementation following the task plan:
   - **Phase-by-phase execution**: Complete each phase before moving to the next
   - **Autonomous Loop**: You **MUST** continue processing the next ready sequential tasks automatically without stopping after a single task. Stop only when you reach a **Join Point** (awaiting parallel task results), or when all tasks in the current phase are complete.
   - **Respect dependencies**: Run sequential tasks in order, and only run [P] tasks inside their declared or inferred parallel batches
   - **Capability-aware execution**: After selecting the strategy, execute the current ready batch through `native-multi-agent` or `sidecar-runtime` when selected by policy; otherwise execute via `single-agent` while preserving join-point semantics through the delegated worker lane.
   - Runtime-visible state should reflect join points, retry-pending work, and blockers rather than hiding those transitions behind chat-only narration.
   - After each completed batch, the leader re-evaluates milestone state, selects the next executable phase and ready batch in roadmap order, and continues automatically until the milestone is complete or blocked.
   - **Follow TDD approach**: Execute test tasks before their corresponding implementation tasks
   - **File-based coordination**: Tasks affecting the same files must run sequentially
   - **Shared-surface coordination**: Treat shared registration files, router tables, export barrels, dependency injection containers, and similar coordination points as write conflicts even if the main feature files differ
   - **Boundary-pattern preservation**: When a task touches an established framework-owned surface, extend the existing pattern instead of introducing a parallel adapter, raw rewrite, or compatibility shim unless `plan.md` explicitly authorizes that change
   - **Validation checkpoints**: Verify each phase completion before proceeding

8. Implementation execution rules:
   - **Setup first**: Initialize project structure, dependencies, configuration
   - **Tests before code**: If you need to write tests for contracts, entities, and integration scenarios
   - **Core development**: Implement models, services, CLI commands, endpoints
   - **Integration work**: Database connections, middleware, logging, external services
   - **Polish and validation**: Unit tests, performance optimization, documentation

9. Progress tracking and error handling:
   - Report progress after each completed task
   - Halt execution if any non-parallel task fails
   - For tasks in parallel batches, continue with successful tasks, report failed ones, and do not cross the batch's join point until the failed work is resolved or explicitly deferred
   - For high-risk batches, treat acceptance as a three-layer check:
     - worker self-check
     - optional read-only peer-review lane when `classify_review_gate_policy(workload_shape)` recommends it
     - leader/orchestrator review before crossing the join point
   - Blocked delegated worker results must include a concrete blocker summary, the failed assumption or dependency, and the smallest safe recovery step before the leader accepts the result.
   - Persist completed work, failed work, blocker evidence, `retry_attempts`, `recovery_action`, and `next_action` in `implement-tracker.md` as soon as they change
   - Before declaring the feature blocked, attempt the smallest safe recovery step that matches the evidence:
     - read the most relevant local implementation context for the failing area
     - run the smallest meaningful repro, failing test, or validation command
     - inspect immediate logs or error output
     - make one focused repair attempt when the evidence is clear
     - if uncertainty remains high, do focused implementation research for the narrow blocker before widening scope
   - If recovery attempts still fail, set tracker status to `blocked`, keep the blocker explicit, and preserve the best known `next_action` for the next `sp-implement` run
   - Provide clear error messages with context for debugging
   - Suggest next steps if implementation cannot proceed
   - **IMPORTANT** For completed tasks, make sure to mark the task off as [X] in the tasks file.

10. Completion validation:
   - Enter tracker status `validating` after the last ready implementation task is complete. `tasks.md` being fully checked off is not sufficient for completion by itself.
   - Verify all required tasks are completed
   - Check that implemented features match the original specification, accepted behavior, and any independent test criteria captured in `tasks.md`
   - Validate that tests pass and coverage meets requirements
   - Confirm the implementation follows the technical plan
   - If validation finds missing user-visible behavior or unmet acceptance criteria, record an `open_gaps` entry instead of silently claiming completion
   - Classify each unresolved gap:
     - `execution_gap`: implementation exists but still behaves incorrectly; continue fixing within the current implementation loop
     - `research_gap`: the blocker is a missing technical decision or evidence gap; update `research.md`, record the new finding in the tracker, then continue
     - `plan_gap`: the current plan/tasks do not cover the work needed to satisfy the feature goal; update `plan.md` and `tasks.md`, set tracker status to `replanning`, then continue from the next ready batch after the replan
     - `spec_gap`: the requirement itself is ambiguous, contradictory, or newly changed; stop autonomous replanning, keep the gap explicit in the tracker, and recommend `/sp.spec-extend`
   - If the completed implementation changed truth-owning surfaces, shared surfaces, command/route/contract boundaries, verification entry points, runtime assumptions, or other map-level coverage facts, and verification is truthfully green and no explicit blocker prevents completion, including unresolved `open_gaps`, run `/sp-map-codebase` before final completion reporting so `PROJECT-HANDBOOK.md`, `.specify/project-map/*.md`, and `.specify/project-map/status.json` are refreshed in the same pass.
   - If you cannot complete that refresh in the current pass, mark `.specify/project-map/status.json` dirty through the project-map freshness helper and recommend `/sp-map-codebase` before the next brownfield workflow proceeds.
   - Only mark the tracker `resolved` after required tasks are complete, blockers are cleared, and the validation pass is truthfully green or explicitly waiting on recorded human verification
   - Before the final completion report, capture any new `pitfall`, `recovery_path`, or `project_constraint` learning through `specify learning capture --command implement ...`.
   - Keep lower-signal items as candidates and use `specify learning promote --target learning ...` only after explicit confirmation or proven recurrence.
   - Only ask for confirmation when a new learning is highest-signal, such as an explicit user default, clear cross-stage reuse, or repeated recurrence that should become shared project memory.
   - Report final status with summary of completed work, remaining human-needed checks, and any unresolved gaps

Note: This command assumes a complete task breakdown exists in tasks.md. If tasks are incomplete or missing, suggest running `/sp.tasks` first to regenerate the task list.

11. **Check for extension hooks**: After completion validation, check if `.specify/extensions.yml` exists in the project root.
    - If it exists, read it and look for entries under the `hooks.after_implement` key
    - If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
    - Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
    - For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
      - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
      - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
    - For each executable hook, output the following based on its `optional` flag:
      - **Optional hook** (`optional: true`):
        ```
        ## Extension Hooks

        **Optional Hook**: {extension}
        Command: `/{command}`
        Description: {description}

        Prompt: {prompt}
        To execute: `/{command}`
        ```
      - **Mandatory hook** (`optional: false`):
        ```
        ## Extension Hooks

        **Automatic Hook**: {extension}
        Executing: `/{command}`
        EXECUTE_COMMAND: {command}
        ```
    - If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

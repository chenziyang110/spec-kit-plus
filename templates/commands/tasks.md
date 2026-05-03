---
description: Use when plan artifacts exist and execution needs dependency-aware tasks, guardrails, and parallelization guidance before implementation.
workflow_contract:
  when_to_use: Planning artifacts already exist and the remaining gap is concrete execution slicing rather than more design work.
  primary_objective: Produce `tasks.md` with dependency ordering, guardrail carry-forward, execution batches, and join points.
  primary_outputs: '`FEATURE_DIR/tasks.md` and the task decomposition metadata needed for later analysis and implementation.'
  default_handoff: '/sp.analyze for cross-artifact drift checks; only continue to /sp.implement after analyze clears upstream drift.'
handoffs: 
  - label: Analyze For Consistency
    agent: sp.analyze
    prompt: Run a project analysis for consistency
    send: true
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

{{spec-kit-include: ../command-partials/tasks/shell.md}}

{{spec-kit-include: ../command-partials/common/subagent-execution.md}}


## Pre-Execution Checks

**Check for extension hooks (before tasks generation)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_tasks` key
{{spec-kit-include: ../command-partials/common/extension-hooks-body.md}}

**Run first-party workflow quality hooks once `FEATURE_DIR` is known**:
- Use `{{specify-subcmd:hook preflight --command tasks --feature-dir "$FEATURE_DIR"}}` before decomposition continues so stale project-map or invalid workflow-entry state is blocked by the shared product guardrail layer.
- After `WORKFLOW_STATE_FILE` is created or resumed, use `{{specify-subcmd:hook validate-state --command tasks --feature-dir "$FEATURE_DIR"}}` so the shared validator confirms `workflow-state.md` matches the `sp-tasks` contract.
- Before final handoff, use `{{specify-subcmd:hook validate-artifacts --command tasks --feature-dir "$FEATURE_DIR"}}` so the required `tasks.md` and `workflow-state.md` outputs are machine-checked instead of inferred from chat progress.
- Before compaction-risk transitions or after major task-batch synthesis, use `{{specify-subcmd:hook checkpoint --command tasks --feature-dir "$FEATURE_DIR"}}` to emit a resume-safe checkpoint payload from `workflow-state.md`.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command tasks --format json}}` when available so passive learning files exist, the current task-generation run sees relevant shared project memory, and repeated candidates, including repeated high-signal candidates, can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader task-generation context.
- Review `.planning/learnings/candidates.md` only when it still contains task-generation-relevant candidate learnings after the passive start step, especially repeated workflow gaps, project constraints, or validation misses that should influence task decomposition.
- [AGENT] When task-shaping friction appears, run `{{specify-subcmd:hook signal-learning --command tasks ...}}` with artifact-rewrite, route-change, false-start, or hidden-dependency counts.
- [AGENT] Before final completion or blocked reporting, run `{{specify-subcmd:hook review-learning --command tasks --terminal-status <resolved|blocked> ...}}`; use `--decision none --rationale "..."` only when no reusable `workflow_gap`, `routing_mistake`, `verification_gap`, `decision_debt`, or `project_constraint` exists.
- [AGENT] Prefer `{{specify-subcmd:learning capture-auto --command tasks --feature-dir "$FEATURE_DIR" --format json}}` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints. Fall back to `{{specify-subcmd:hook capture-learning --command tasks ...}}` when the durable state does not capture the reusable lesson cleanly.
- Treat this as passive shared memory, not as a separate user-visible workflow.

## Workflow Phase Lock

- [AGENT] Create or resume `WORKFLOW_STATE_FILE` before substantial task-generation analysis.
- Read `templates/workflow-state-template.md`.
- If `WORKFLOW_STATE_FILE` is missing, recreate it from the template and the current spec/plan package instead of continuing from chat memory alone.
- Treat `WORKFLOW_STATE_FILE` as the stage-state source of truth on resume after compaction for the current command, allowed artifact writes, forbidden actions, authoritative files, next action, and exit criteria.
- Set or update the state for this run with at least:
  - `active_command: sp-tasks`
  - `phase_mode: task-generation-only`
  - `forbidden_actions: edit source code, edit tests, implement behavior, start execution from task-generation artifacts`
- Do not implement code, edit source files, edit tests, or treat task generation as permission to start execution.
- Implementation remains blocked until `{{invoke:analyze}}` confirms the current task package does not need upstream regeneration.
- Do not hand off directly to `{{invoke:implement}}` from `sp-tasks`; the analyze gate is mandatory unless the user is explicitly resuming a previously cleared execution state.
- When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.

## Outline

1. **Setup**: Run `{SCRIPT}` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").
   - If `FEATURE_DIR` is not already explicit, prefer `{{specify-subcmd:lane resolve --command tasks --ensure-worktree}}` before guessing from branch-only context.
   - When lane resolution returns a materialized lane worktree, continue task generation from that isolated worktree context so downstream execution packets inherit the same lane boundary.
   - Set `WORKFLOW_STATE_FILE` to `FEATURE_DIR/workflow-state.md`.
   - [AGENT] Create or resume `WORKFLOW_STATE_FILE` before substantial task-generation analysis.
   - Read `templates/workflow-state-template.md`.
   - If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid `next_action`, `exit_criteria`, and `next_command` details instead of relying on chat memory alone.
   - Persist at least these fields for the active pass:
     - `active_command: sp-tasks`
     - `phase_mode: task-generation-only`
     - `allowed_artifact_writes: tasks.md, workflow-state.md`
     - `forbidden_actions: edit source code, edit tests, implement behavior, start execution from task-generation artifacts`
     - `authoritative_files: spec.md, alignment.md, context.md, plan.md, tasks.md`
   - When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.

2. **Ensure repository navigation system exists**:
   - Check whether `.specify/project-map/index/status.json` exists.
   - If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
   - [AGENT] If freshness is `missing` or `stale`, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
   - [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If `must_refresh_topics` is non-empty for the current task-generation request, run `/sp-map-scan` followed by `/sp-map-build` before continuing. If only `review_topics` are non-empty, review those topic files before generating task batches.
   - Check whether `PROJECT-HANDBOOK.md` exists at the repository root.
   - Check whether `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/STRUCTURE.md`, `.specify/project-map/root/CONVENTIONS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md` exist.
   - [AGENT] If the navigation system is missing, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
   - Treat task-relevant coverage as insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
   - [AGENT] If task-relevant coverage is insufficient for the current task-generation request, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.

3. **Load design documents**: Read from FEATURE_DIR:
   - **Required**: plan.md (tech stack, libraries, structure), spec.md (user stories with priorities), context.md (implementation context)
   - **Required when present**: alignment.md (locked decisions, outstanding questions, planning gate context)
   - **Required when present**: workflow-state.md (current phase lock, allowed actions, forbidden actions, resume contract, active profile, activated gates, task-shaping rules, and required evidence)
   - **Required when present**: `.specify/testing/TESTING_CONTRACT.md` (project-level testing rules and required regression behavior)
   - **Required when present**: `.specify/testing/TESTING_PLAYBOOK.md` (canonical test and coverage commands)
   - **Required when present**: `.specify/testing/COVERAGE_BASELINE.json` (baseline or threshold context by module)
   - **Optional**: references.md (retained sources, reusable insights, spec impact mapping)
   - **Optional**: data-model.md (entities), contracts/ (interface contracts), research.md (decisions), quickstart.md (test scenarios)
   - **Required when present**: `.specify/memory/constitution.md` (project constitution and mandatory principles that tasks must preserve)
   - **Required when present**: `.specify/memory/project-rules.md` (shared project defaults that task generation should preserve)
   - **Required when present**: `.specify/memory/project-learnings.md` (confirmed reusable project learnings that may shape decomposition, validation, or guardrails)
   - **If `.planning/learnings/candidates.md` exists**: inspect only the entries relevant to task generation so repeated workflow gaps, project constraints, and validation misses are not rediscovered from scratch
   - **Required**: [AGENT] Read `PROJECT-HANDBOOK.md`
   - **Required**: Read the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/STRUCTURE.md`, `.specify/project-map/root/CONVENTIONS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md`
   - **If topical coverage is missing/stale/too broad or task-relevant coverage is insufficient**: run `/sp-map-scan` followed by `/sp-map-build` before continuing, then inspect the minimum live files still needed to replace guesswork with evidence
   - **Required**: Read `templates/workflow-state-template.md`
   - Note: Not all projects have all documents. Generate tasks based on what's available.

{{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}

**Project-map hard gate:** you must pass an atlas gate before task-shaping
analysis, decomposition, or implementation-shaping code reads begin.

**This command tier: heavy.** Pass the atlas gate by reading
`PROJECT-HANDBOOK.md`, `atlas.entry`, `atlas.index.status`,
`atlas.index.atlas`, `atlas.index.modules`, `atlas.index.relations`, the
relevant root topic documents, and the relevant module overview documents
before task breakdown continues. Task generation may stay focused on the plan
artifacts afterward, but it may not skip the atlas gate.

4. **Execute task generation workflow**:
    - [AGENT] Before task decomposition begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="tasks", snapshot, workload_shape)`
    - Before emitting high-risk batches, classify whether they need extra review: `classify_review_gate_policy(workload_shape)`
    - The chosen dispatch shape applies to the **current ready batch**, not automatically to the entire feature or task graph.
    - Primary decomposition goal: maximize safe native-subagent throughput for later `sp-implement` runs by isolating write sets and turning ready work into a dispatch-ready lane packet instead of a vague checklist.
    - Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
    - Decision order is fixed:
      - One safe validated lane -> `one-subagent` on `native-subagents` when available.
      - Two or more safe isolated lanes -> `parallel-subagents` on `native-subagents` when available.
      - No safe lane, overlapping writes, missing contract, or unavailable delegation -> `subagent-blocked` with a recorded reason.
    - If collaboration is justified, keep `tasks` lanes limited to:
      - story and phase decomposition
      - dependency graph analysis
      - write-set and parallel-safety analysis
    - Required join points:
      - before writing `tasks.md`
      - before emitting canonical parallel batches and join points
    - Record the chosen strategy, reason, any blocked dispatch or escalation decision, selected lanes, and join points in the generated report and implementation strategy section.
    - Extract the active profile, activated gates, task-shaping rules, and required evidence obligations from `workflow-state.md`; `sp-tasks` consumes the same profile contract or active profile that `sp-specify`/`sp-plan` persisted, not a newly invented taxonomy.
    - Keep `sp-tasks` aligned with the persisted first-release profile contract: `active_profile` must be one of the two supported profiles, `Standard Delivery` or `Reference-Implementation`.
    - If `workflow-state.md` presents an unsupported `active_profile` during first release, `sp-tasks` stops before decomposition and tells the operator to repair/re-run upstream routing state before task generation continues.
    - Treat `Scenario profile inputs` as task-shaping inputs: active profile, routing reason, activated gates, fidelity obligations, deviation review requirements, and required evidence.
    - Load plan.md and extract tech stack, libraries, project structure
    - Extract `Locked Planning Decisions`, `Implementation Constitution`, `Canonical References`, `Input Risks From Alignment`, and `Decision Preservation Check` from plan.md when present
    - Load spec.md and extract user stories with their priorities (P1, P2, P3, etc.) plus capability decomposition
    - If alignment.md exists: treat `Locked Decisions For Planning`, `Outstanding Questions`, and `Remaining Risks` as task-shaping inputs rather than historical notes
    - If `.specify/memory/constitution.md` exists: treat its MUST/SHOULD principles as task-shaping constraints and preserve them explicitly in execution ordering, validation tasks, or phase notes
    - If references.md exists: use it to preserve source-driven constraints and reusable examples while generating tasks
    - If data-model.md exists: Extract entities and map to user stories
    - If contracts/ exists: Map interface contracts to user stories
    - If research.md exists: Extract decisions for setup tasks
    - If quickstart.md exists: extract validation scenarios that should appear as verification-oriented tasks or explicit task completion criteria
    - If active profile is `Reference-Implementation`, add explicit fidelity checkpoints before implementation batches that can materially change the reference-preserved surface. Each fidelity checkpoint must identify the preserved surface, the reference evidence to compare against, the validation command or manual check, and the pass condition.
    - If implementation may intentionally diverge from the reference contract, add a `Deviation Review` join point before downstream work continues. The join point must capture the divergence rationale, affected contract or reference surface, approval or re-planning requirement, and downstream task adjustments.
    - **Missing design artifacts**: If plan.md's expected artifacts (data-model.md, contracts/, research.md) are absent and the feature would benefit from them, stop and recommend re-running `{{invoke:plan}}` instead of generating tasks from incomplete design context.
    - Generate tasks organized by user story (see Task Generation Rules below)
    - Whether or not `.specify/testing/TESTING_CONTRACT.md` exists, treat tests as default deliverables for behavior changes, bug fixes, and refactors
    - If the testing contract names required regression or coverage work for an affected module, preserve that requirement explicitly in the task list
    - If the touched area lacks a reliable automated test surface, add explicit bootstrap tasks to establish the smallest runnable test surface first before implementation tasks for that slice
    - Top-level tasks should fit one bounded implementation slice: roughly 10-20 minutes, one stable objective, one isolated write set, and one verification path
    - A subagent can still execute the task internally through smaller 2-5 minute atomic steps, but do not explode the public task list into coordinator-hostile micro-tasks
    - Stop decomposition once the current executable window is atomic. Leave later phases at the coarser story or phase level when their exact shape depends on earlier join-point evidence
    - If later work still depends on upstream evidence, add a refinement checkpoint instead of guessing detailed downstream tasks too early
    - Carry profile-required evidence into task completion criteria instead of relying only on generic behavior validation. When the active profile requires screenshots, trace IDs, reference comparisons, migration proof, or other required evidence, attach that evidence obligation to the relevant task done condition or join point pass condition.
    - If `Implementation Constitution` defines boundary-defining references or forbidden drift, add an implementation-guardrails phase before setup so implementers must confirm the existing pattern before changing code
    - **Task Guardrail Index**: Add task-to-guardrail mapping when tasks inherit execution rules from plan.md or constitution.md. Keep the mapping compact so downstream execution can resolve applicable hard rules per task.
    - For every `[P]` task or parallel batch, include: objective, write set, required references, forbidden drift, validation command, and done condition — the information downstream execution needs to dispatch work safely
    - Generate dependency graph showing user story completion order
    - Derive a write set for each task (files or shared registration surfaces it will modify)
    - Group ready tasks into each phase's parallel batches using those write sets
    - Grouped parallelism is the default when multiple ready tasks have isolated write sets and do not depend on each other's outputs
    - Prefer moving shared registrations, export barrels, schema indexes, router tables, and other coordination edits into explicit serial join tasks so the surrounding feature work can stay parallel-ready
    - Pipeline is preferred when outputs flow linearly from one bounded lane to the next, for example transform -> generate -> validate
    - Every pipeline stage still needs an explicit checkpoint before downstream stages continue so stale assumptions do not propagate silently
    - If `classify_review_gate_policy(workload_shape)` requires a review gate, add an explicit high-risk review checkpoint before downstream tasks continue
    - High-risk review gates are usually required for shared registration surfaces, schema or migration changes, protocol seams, native/plugin bridges, or generated API surfaces
    - If a peer-review lane is available and the review can stay read-only, recommend one peer-review lane for the batch; otherwise make the leader responsible only for acceptance criteria, review coordination, and the checkpoint decision
    - Add explicit join points after every parallel batch so downstream tasks know where synchronization happens
    - For every explicit join point, include a validation target, a validation command or concrete manual check, and a pass condition
    - Create parallel execution examples per user story
    - Validate task completeness (each user story has all needed tasks, independently testable)
    - Validate decision preservation: if a locked planning decision or implementation constitution rule affects implementation, compatibility, rollout, validation, sequencing, or architecture shape, at least one task or phase note must preserve it explicitly instead of silently dropping it

    **Feature delivery shape**: Classify the whole task graph in plain language (e.g., `serial phases with intra-phase parallel batches`, `mostly sequential`, `pipeline-heavy`, `parallel-ready after foundational work`). If later batches are parallelizable but the current batch is not, state that explicitly.

5. **Generate tasks.md**: Use `templates/tasks-template.md` as structure, fill with:
   - Correct feature name from plan.md
   - Phase 1: Setup tasks (project initialization)
   - Phase 2: Foundational tasks (blocking prerequisites for all user stories)
   - Phase 3+: One phase per user story (in priority order from spec.md)
   - Each phase includes: story goal, independent test criteria, tests (if requested), implementation tasks
   - Final Phase: Polish & cross-cutting concerns
   - All tasks must follow the strict checklist format (see Task Generation Rules below)
   - Clear file paths for each task
   - Dependencies section showing story completion order
   - Parallel batches and join points for each phase where they matter
   - Join point validation notes whenever a join point gates downstream implementation or shared-surface merge work
   - Scenario profile inputs section showing the active profile, activated gates, task-shaping rules, and required evidence when they materially shape execution
   - Fidelity checkpoints before `Reference-Implementation` batches that can materially change the reference-preserved surface
   - Deviation Review join points before downstream work continues when an implementation may intentionally diverge from the reference contract
   - Task completion criteria that carry required evidence from the active profile instead of relying only on generic behavior validation
   - Parallel execution examples per story
    - Planning inputs section showing locked decisions, carried risks, and required validation references when they materially shape execution
    - Planning inputs section showing implementation constitution rules when they materially shape execution
    - `Task Guardrail Index` entries or equivalent task-to-guardrail mapping when subagent work must inherit explicit execution rules
    - Implementation strategy section (phased delivery, priority-ordered delivery, capability-aware parallel execution)

6. **Report**: Output path to generated tasks.md and summary:
    - Total task count
    - Task count per user story
    - Feature delivery shape (whole task graph)
    - Parallel opportunities identified
    - Parallel batch count and the join points that gate downstream work
    - Independent test criteria for each story
    - Suggested first release scope (based on the smallest coherent release slice, not automatically limited to just User Story 1)
    - Confirm first-release profile scope stayed within the two supported profiles: `Standard Delivery` and `Reference-Implementation`
    - Format validation: Confirm ALL tasks follow the checklist format (checkbox, ID, labels, file paths)
    - workflow-state path
    - Recommended next command: `{{invoke:analyze}}`
    - If the decomposition exposes new shared surfaces, workflow joins, or validation entry points not yet in the handbook/project-map, mark `.specify/project-map/index/status.json` dirty and recommend `/sp-map-scan` followed by `/sp-map-build` before later brownfield implementation proceeds.
   - before final completion text, write or update `WORKFLOW_STATE_FILE` so it records:
     - `active_command: sp-tasks`
     - `phase_mode: task-generation-only`
     - current authoritative files
     - exit criteria for task-generation completion
     - the next action required before handoff
     - `next_command: /sp.analyze`

7. **Check for extension hooks**: After tasks.md is generated, check if `.specify/extensions.yml` exists in the project root.
   - If it exists, read it and look for entries under the `hooks.after_tasks` key
{{spec-kit-include: ../command-partials/common/extension-hooks-after-body.md}}

Context for task generation: {ARGS}

The tasks.md should be immediately executable - each task must be specific enough that an LLM can complete it without additional context.

## Task Generation Rules

**CRITICAL**: Tasks MUST be organized by user story to enable independent implementation and testing.

**Tests are contract-driven**: If `.specify/testing/TESTING_CONTRACT.md` exists, generate test tasks by default for affected behavior changes, bug fixes, and regression-sensitive modules. Only omit tests when the change is clearly docs-only/process-only or the testing contract explicitly allows the omission.

### Checklist Format (REQUIRED)

Every task MUST strictly follow this format:

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

**Format Components**:

1. **Checkbox**: ALWAYS start with `- [ ]` (markdown checkbox)
2. **Task ID**: Sequential number (T001, T002, T003...) in execution order
3. **[P] marker**: Include ONLY if task is parallelizable
   - Parallelizable means the task has an isolated write set, no dependencies on incomplete tasks, stable upstream inputs, and an independent verification path
   - Treat shared registration files, index/exports, router tables, dependency injection containers, and other coordination surfaces as part of the write set
4. **[Story] label**: REQUIRED for user story phase tasks only
   - Format: [US1], [US2], [US3], etc. (maps to user stories from spec.md)
   - Setup phase: NO story label
   - Foundational phase: NO story label  
   - User Story phases: MUST have story label
   - Polish phase: NO story label
5. **Description**: Clear action with exact file path

### Task Granularity Contract

- Top-level tasks should usually fit one bounded implementation slice:
  - roughly 10-20 minutes
  - one stable objective
  - one isolated write set
  - one verification path
- Delegated workers may still break a task into smaller 2-5 minute atomic internal steps, but `tasks.md` should stop at the smallest unit worth explicit coordination.
- If a task can obviously be split into two independently verifiable write sets, split it.
- If splitting further would only create coordination overhead, stop and keep the task atomic.
- When later work depends on upstream execution evidence, keep that future work at the story or phase level and insert a refinement checkpoint instead of guessing detailed downstream tasks too early.

**Examples**:

- ✅ CORRECT: `- [ ] T001 Create project structure per implementation plan`
- ✅ CORRECT: `- [ ] T005 [P] Implement authentication middleware in src/middleware/auth.py`
- ✅ CORRECT: `- [ ] T012 [P] [US1] Create User model in src/models/user.py`
- ✅ CORRECT: `- [ ] T014 [US1] Implement UserService in src/services/user_service.py`
- ❌ WRONG: `- [ ] Create User model` (missing ID and Story label)
- ❌ WRONG: `T001 [US1] Create model` (missing checkbox)
- ❌ WRONG: `- [ ] [US1] Create User model` (missing Task ID)
- ❌ WRONG: `- [ ] T001 [US1] Create model` (missing file path)

### Task Organization

1. **From User Stories (spec.md)** - PRIMARY ORGANIZATION:
   - Each user story (P1, P2, P3...) gets its own phase
   - Map all related components to their story:
     - Models needed for that story
     - Services needed for that story
     - Interfaces/UI needed for that story
     - If `.specify/testing/TESTING_CONTRACT.md` exists or the spec explicitly requires tests: Tests specific to that story
   - Mark story dependencies (most stories should be independent)

2. **From Contracts**:
   - Map each interface contract → to the user story it serves
   - If `.specify/testing/TESTING_CONTRACT.md` exists or the spec explicitly requires tests: Each interface contract → contract test task [P] before implementation in that story's phase

3. **From Data Model**:
   - Map each entity to the user story(ies) that need it
   - If entity serves multiple stories: Put in earliest story or Setup phase
   - Relationships → service layer tasks in appropriate story phase

4. **From Setup/Infrastructure**:
   - Shared infrastructure → Setup phase (Phase 1)
   - Foundational/blocking tasks → Foundational phase (Phase 2)
   - Story-specific setup → within that story's phase

### Parallelization Rules

- Prefer parallel tasks that unblock more downstream work before consumer tasks
- Only place tasks in the same parallel batch when their write sets do not overlap
- Do not batch tasks together if they rely on changing contracts, schemas, or interfaces that are not yet stable
- Grouped parallelism is the default when multiple ready tasks have isolated write sets and stable upstream inputs
- Use a pipeline shape when outputs must flow stage-by-stage from one bounded task to the next
- Even pipeline tasks should still stop at explicit checkpoints between stages before downstream work continues
- Add a high-risk review checkpoint when the batch touches shared registration surfaces, schema changes, protocol seams, native/plugin bridges, or generated API surfaces
- Use a peer-review lane only for those high-risk batches when the review can stay read-only and independent
- Every parallel batch MUST be followed by a join point before dependent tasks continue
- If a task touches a shared registration file, it should usually be the join point task or run after the batch sequentially

### Phase Structure

- **Phase 1**: Setup (project initialization)
- **Phase 2**: Foundational (blocking prerequisites - MUST complete before user stories)
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
  - Within each story: Tests (if requested) → Models → Services → Endpoints → Integration
  - Each phase should be a complete, independently testable increment
- **Final Phase**: Polish & Cross-Cutting Concerns

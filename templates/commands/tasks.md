---
description: Generate an actionable, dependency-ordered tasks.md for the feature based on available design artifacts.
handoffs: 
  - label: Analyze For Consistency
    agent: sp.analyze
    prompt: Run a project analysis for consistency
    send: true
  - label: Implement Project
    agent: sp.implement
    prompt: Start the implementation in phases
    send: true
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before tasks generation)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_tasks` key
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

## Outline

1. **Setup**: Run `{SCRIPT}` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Ensure repository navigation system exists**:
   - Check whether `.specify/project-map/status.json` exists.
   - If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
   - If freshness is `missing` or `stale`, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts.
   - If freshness is `possibly_stale`, inspect the reported changed paths and reasons. If they overlap the current task-generation request, touched area, shared surfaces, change-propagation hotspots, verification entry points, or known unknowns, run `/sp-map-codebase` before continuing.
   - Check whether `PROJECT-HANDBOOK.md` exists at the repository root.
   - Check whether `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md` exist.
   - If the navigation system is missing, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts.
   - Treat task-relevant coverage as insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
   - If task-relevant coverage is insufficient for the current task-generation request, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts.

3. **Load design documents**: Read from FEATURE_DIR:
   - **Required**: plan.md (tech stack, libraries, structure), spec.md (user stories with priorities), context.md (implementation context)
   - **Required when present**: alignment.md (locked decisions, outstanding questions, planning gate context)
   - **Optional**: references.md (retained sources, reusable insights, spec impact mapping)
   - **Optional**: data-model.md (entities), contracts/ (interface contracts), research.md (decisions), quickstart.md (test scenarios)
   - **Required when present**: `.specify/memory/constitution.md` (project constitution and mandatory principles that tasks must preserve)
   - **Required**: Read `PROJECT-HANDBOOK.md`
   - **Required**: Read the smallest relevant combination of `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md`
   - **If topical coverage is missing/stale/too broad or task-relevant coverage is insufficient**: run `/sp-map-codebase` before continuing, then inspect the minimum live files still needed to replace guesswork with evidence
   - Note: Not all projects have all documents. Generate tasks based on what's available.

4. **Execute task generation workflow**:
   - Before task decomposition begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_execution_strategy(command_name="tasks", snapshot, workload_shape)`
   - Strategy names are canonical and must be used exactly: `single-agent`, `native-multi-agent`, `sidecar-runtime`
   - Decision order is fixed:
     - If the work does not justify safe fan-out -> `single-agent` (`no-safe-batch`)
     - Else if `snapshot.native_multi_agent` -> `native-multi-agent` (`native-supported`)
     - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime` (`native-missing`)
     - Else -> `single-agent` (`fallback`)
   - If collaboration is justified, keep `tasks` lanes limited to:
     - story and phase decomposition
     - dependency graph analysis
     - write-set and parallel-safety analysis
   - Required join points:
     - before writing `tasks.md`
     - before emitting canonical parallel batches and join points
   - Record the chosen strategy, reason, fallback if any, selected lanes, and join points in the generated report and implementation strategy section.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.
   - Load plan.md and extract tech stack, libraries, project structure
   - Extract `Locked Planning Decisions`, `Canonical References`, `Input Risks From Alignment`, and `Decision Preservation Check` from plan.md when present
   - Load spec.md and extract user stories with their priorities (P1, P2, P3, etc.) plus capability decomposition
   - If alignment.md exists: treat `Locked Decisions For Planning`, `Outstanding Questions`, and `Remaining Risks` as task-shaping inputs rather than historical notes
   - If `.specify/memory/constitution.md` exists: treat its MUST/SHOULD principles as task-shaping constraints and preserve them explicitly in execution ordering, validation tasks, or phase notes instead of assuming downstream agents will rediscover them
   - If references.md exists: use it to preserve source-driven constraints and reusable examples while generating tasks
   - If data-model.md exists: Extract entities and map to user stories
   - If contracts/ exists: Map interface contracts to user stories
   - If research.md exists: Extract decisions for setup tasks
   - If quickstart.md exists: extract validation scenarios that should appear as verification-oriented tasks or explicit task completion criteria
   - Generate tasks organized by user story (see Task Generation Rules below)
   - Generate dependency graph showing user story completion order
   - Derive a write set for each task (files or shared registration surfaces it will modify)
   - Group ready tasks into each phase's parallel batches using those write sets
   - Add explicit join points after every parallel batch so downstream tasks know where synchronization happens
   - Create parallel execution examples per user story
   - Validate task completeness (each user story has all needed tasks, independently testable)
   - Validate decision preservation: if a locked planning decision affects implementation, compatibility, rollout, validation, or sequencing, at least one task or phase note must preserve it explicitly instead of silently dropping it

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
   - Parallel execution examples per story
   - Planning inputs section showing locked decisions, carried risks, and required validation references when they materially shape execution
   - Implementation strategy section (phased delivery, priority-ordered delivery, capability-aware parallel execution)

6. **Report**: Output path to generated tasks.md and summary:
   - Total task count
   - Task count per user story
   - Parallel opportunities identified
   - Parallel batch count and the join points that gate downstream work
   - Independent test criteria for each story
   - Suggested first release scope (based on the smallest coherent release slice, not automatically limited to just User Story 1)
   - Format validation: Confirm ALL tasks follow the checklist format (checkbox, ID, labels, file paths)

7. **Check for extension hooks**: After tasks.md is generated, check if `.specify/extensions.yml` exists in the project root.
   - If it exists, read it and look for entries under the `hooks.after_tasks` key
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

Context for task generation: {ARGS}

The tasks.md should be immediately executable - each task must be specific enough that an LLM can complete it without additional context.

## Task Generation Rules

**CRITICAL**: Tasks MUST be organized by user story to enable independent implementation and testing.

**Tests are OPTIONAL**: Only generate test tasks if explicitly requested in the feature specification or if user requests TDD approach.

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
     - If tests requested: Tests specific to that story
   - Mark story dependencies (most stories should be independent)

2. **From Contracts**:
   - Map each interface contract → to the user story it serves
   - If tests requested: Each interface contract → contract test task [P] before implementation in that story's phase

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
- Every parallel batch MUST be followed by a join point before dependent tasks continue
- If a task touches a shared registration file, it should usually be the join point task or run after the batch sequentially

### Phase Structure

- **Phase 1**: Setup (project initialization)
- **Phase 2**: Foundational (blocking prerequisites - MUST complete before user stories)
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
  - Within each story: Tests (if requested) → Models → Services → Endpoints → Integration
  - Each phase should be a complete, independently testable increment
- **Final Phase**: Polish & Cross-Cutting Concerns

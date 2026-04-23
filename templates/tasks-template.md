---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Planning Inputs

- **Locked planning decisions**: Copy any non-negotiable implementation, compatibility, rollout, or validation constraints from `plan.md`, `spec.md`, and `alignment.md`
- **Implementation constitution**: Carry forward architecture invariants, boundary ownership, forbidden drift, required references, and review focus from `plan.md`
- **Alignment risks**: Carry forward unresolved but accepted risks so tasks can mitigate or explicitly acknowledge them
- **Validation references**: Preserve `quickstart.md`, canonical references, and research-backed validation notes when they shape task ordering or completion criteria
- Do not silently drop a locked planning decision; if it is deferred, say so explicitly in the phase or dependency notes
- If a feature touches an established framework or boundary pattern, add explicit guardrail tasks before implementation begins

## Task Guardrail Index

- Map each implementation task to the delegated-execution rules it inherits from `plan.md`, `tasks.md`, and `.specify/memory/constitution.md`
- Keep the mapping compact and task-specific so packet compilation can resolve applicable hard rules without copying the full constitution into every task body
- Include task-to-guardrail mapping entries such as ``T017 -> G-PRESERVE-BOUNDARY, G-VALIDATE-AUTH`` when delegated work needs explicit execution constraints

## Task Shaping Rules

- Top-level tasks should stay bounded enough to finish in one coffee break sized implementation slice, usually roughly 10-20 minutes.
- Each task should preserve one stable objective, one isolated write set, and one verification path.
- Delegated workers may still break a task into smaller 2-5 minute atomic internal steps, but `tasks.md` should stop at the smallest unit worth explicit orchestration.
- Stop decomposition once the current executable window is atomic.
- Leave later phases at the coarser story or phase level when their exact shape depends on earlier join points, then refine them after the checkpoint instead of guessing too early.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel only when the task has an isolated write set, no incomplete dependencies, stable upstream inputs, and its own verification path
- **Write set**: Include all files and shared coordination surfaces the task will modify, including routers, registries, export barrels, schema indexes, and dependency injection containers
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /sp.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as a coherent release increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 0: Implementation Guardrails

**Purpose**: Freeze architecture constraints and boundary references before any code-writing batch starts

- [ ] T000 Read the boundary-defining files, contracts, and examples named in `plan.md` under `Required Implementation References`
- [ ] T001 Record the active implementation guardrails for this feature: framework ownership, preserved boundary pattern, forbidden drift, and review checks
- [ ] T002 Confirm the first implementation batch extends the existing boundary pattern instead of creating a parallel one

**Checkpoint**: Implementation guardrails captured - downstream batches now have explicit architecture constraints

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T003 Create project structure per implementation plan
- [ ] T004 Initialize [language] project with [framework] dependencies
- [ ] T005 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T006 Setup database schema and migrations framework
- [ ] T007 [P] Implement authentication/authorization framework
- [ ] T008 [P] Setup API routing and middleware structure
- [ ] T009 Create base models/entities that all stories depend on
- [ ] T010 Configure error handling and logging infrastructure
- [ ] T011 Setup environment configuration management

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) First Release Candidate

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

**Parallel Batch 1.1**: Independent failing tests with non-overlapping write sets
- [ ] T012 [P] [US1] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T013 [P] [US1] Integration test for [user journey] in tests/integration/test_[name].py
**Join Point 1.1**: Confirm both tests fail for the expected reasons before writing production code

### Implementation for User Story 1

**Parallel Batch 1.2**: Independent models or DTOs with isolated write sets
- [ ] T014 [P] [US1] Create [Entity1] model in src/models/[entity1].py
- [ ] T015 [P] [US1] Create [Entity2] model in src/models/[entity2].py
**Join Point 1.2**: Resolve any shared exports, registrations, or schema indexes before service work
- [ ] T016 [US1] Implement [Service] in src/services/[service].py (depends on T014, T015)
- [ ] T017 [US1] Implement [endpoint/feature] in src/[location]/[file].py while preserving the established boundary/framework pattern named in `plan.md`
- [ ] T018 [US1] Add validation and error handling
- [ ] T019 [US1] Add logging for user story 1 operations

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

- [ ] T020 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T021 [P] [US2] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 2

- [ ] T022 [P] [US2] Create [Entity] model in src/models/[entity].py
- [ ] T023 [US2] Implement [Service] in src/services/[service].py
- [ ] T024 [US2] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T025 [US2] Integrate with User Story 1 components (if needed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (OPTIONAL - only if tests requested) ⚠️

- [ ] T026 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T027 [P] [US3] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 3

- [ ] T028 [P] [US3] Create [Entity] model in src/models/[entity].py
- [ ] T029 [US3] Implement [Service] in src/services/[service].py
- [ ] T030 [US3] Implement [endpoint/feature] in src/[location]/[file].py

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Additional unit tests (if requested) in tests/unit/
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority
- Build parallel batches from ready tasks only
- End every parallel batch with a join point before downstream tasks continue
- Do not run tasks from the same batch together if their write sets overlap
- Treat shared registration files and export barrels as write-set conflicts

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

### Parallel Prioritization

- Prefer batches that unblock more downstream tasks before consumer work
- Prefer tasks with stable contracts and schemas before tasks that depend on them
- Prefer tasks with fast, independent verification before long feedback-loop work
- Prefer the longest safe path early so it does not become the final serial tail
- Grouped parallelism is the default when ready tasks have isolated write sets and stable inputs
- Pipeline tasks should still stop at explicit checkpoints between stages before downstream work continues
- Add a high-risk review checkpoint for shared registration surfaces, schema changes, protocol seams, native/plugin bridges, or generated API surfaces
- Use a peer-review lane only when that review can stay read-only and independent from the write lane
- If the current agent cannot truly parallelize, execute each parallel batch sequentially but keep the same join point boundaries

---

## Parallel Example: User Story 1

```bash
# Parallel Batch 1.1: launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Join Point 1.1: verify both tests fail for the expected reasons

# Parallel Batch 1.2: launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"

# Join Point 1.2: update shared exports or registrations before service implementation
```

---

## Implementation Strategy

### First Release Candidate

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Release/demo if ready

### Phased Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Release/Demo if it forms a coherent first release candidate
3. Add User Story 2 → Test independently → Release/Demo
4. Add User Story 3 → Test independently → Release/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Within each story, developers or agents take one parallel batch at a time and merge at each join point
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = isolated write set, stable inputs, no incomplete dependencies, independent verification
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, shared registration file conflicts, and cross-story dependencies that break independence

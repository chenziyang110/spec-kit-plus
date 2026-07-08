---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/.specify/features/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), alignment.md and context.md when present or required for scenario profile inputs, research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are expected by default for affected behavior changes and bug fixes. Only omit them when the plan explicitly justifies the omission.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Planning Inputs

- **Locked planning decisions**: Copy every non-negotiable implementation, compatibility, rollout, or validation constraint from `plan.md`, `spec.md`, and `alignment.md`. Do not silently drop any locked decision.
- **Implementation constitution**: Carry forward all architecture invariants, boundary ownership rules, forbidden drift, required references, and review focus from `plan.md`.
- **Scenario profile inputs**: Record exactly one active profile and carry forward every profile-driven constraint, reference fidelity rule, allowed deviation rule, and required evidence obligation from `plan.md`, `spec.md`, `alignment.md`, and `context.md`.
- **Reference fidelity inventory**: When the spec/plan package defines reference behavior inventory items, map every preserved or redesigned behavior to at least one task, checkpoint, refinement checkpoint, valid blocker, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
- **Alignment risks**: Carry forward unresolved but accepted risks so tasks can mitigate or explicitly acknowledge them
- **Validation references**: Preserve `quickstart.md`, canonical references, and research-backed validation notes when they shape task ordering or completion criteria
- **Must-preserve discussion obligations**: Copy relevant `MP-*` items from `plan.md`, `spec.md`, `alignment.md`, `context.md`, `references.md`, and `brainstorming/handoff-to-specify.json`. Each implementation-shaping item must appear in the Task Guardrail Index, a required reference, a validation checkpoint, a task packet field, a refinement checkpoint, a valid blocker, or a user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
- **Capability operations**: Copy every preserved or in-scope operation-shaped capability from `spec.md`, `alignment.md`, `context.md`, `plan.md#Capability Preservation Plan`, `plan-contract.json`, and `brainstorming/handoff-to-specify.json`. Operation-shaped capabilities include new/create/scaffold/authoring/template creation, CLI path, TUI path, lifecycle action, API entry point, or any user workflow verb that changes implementation or validation shape.
- **User-observable paths**: For any UI, TUI, CLI, API route, installer, registry/factory/config wiring, or generated asset consumed by runtime behavior, record the real entrypoint path from producer data through transformer/state builder to the consumer surface and executor/boundary.
- Do not silently drop a locked planning decision; if a user-confirmed deferral applies, record it in the phase or dependency notes with confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact
- Do not allow command-surface anti-goals to delete capability. Each anti-goal that limits commands, routes, APIs, lifecycle operations, or public surfaces must include a does-not-remove guard naming the preserved operation and selected entry point.
- Detect semantic degradation before handoff: if a create/scaffold capability is represented only by a template-only task, manual copy docs, or an authoring guide with no executable entry point, stop task generation and route back to `sp-plan` or `sp-clarify`.
- If a feature touches an established framework or boundary pattern, guardrail tasks MUST be added before implementation begins.

## Complete-First Delivery Scope

- **Complete-first scope preservation**: Preserve confirmed delivery scope through task generation and downstream execution.
- **Delivery rule**: Task the complete user-confirmed scope from `spec.md`, `alignment.md`, `context.md`, `plan.md`, `plan-contract.json`, and approved handoff files.
- **Complexity response**: Use ordering, dependencies, isolated write sets, parallel batches, join points, refinement tasks, and validation; do not shrink scope because the work is complex.
- **Execution phase policy**: Execution phases are ordering, not delivery deferral.
- **Forbidden reductions**: Do not create an MVP, pilot, prototype, first-release slice, agent-invented `v1/v2`, agent-invented `P0/P1`, or future-work delivery slice unless the user explicitly confirmed that delivery boundary.
- **Priority labels**: User story priorities such as `P1`, `P2`, and `P3` remain ordering labels, not delivery-scope buckets.
- **Adaptive blocker carve-out**: Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and do not reduce scope.

## User-Confirmed Deferral Contract

| Confirmation Source | Exact Excluded Behavior | Residual Risk | Reopen Or Stop Condition | Downstream Artifact |
| --- | --- | --- | --- | --- |
| None | None | None | None | None |

- If the user did not confirm the deferral, task the behavior, create a refinement or
  validation checkpoint, or record a valid hard blocker.

## Task Guardrail Index

- Map each implementation task to the delegated-execution rules it inherits from `plan.md`, `tasks.md`, and `.specify/memory/constitution.md`
- Keep the mapping compact and task-specific so packet compilation can resolve applicable hard rules without copying the full constitution into every task body
- Include task-to-guardrail mapping entries such as ``T017 -> G-PRESERVE-BOUNDARY, G-VALIDATE-AUTH`` when subagent execution needs explicit execution constraints
- Include `MP-*` IDs for any task that carries a discussion-derived goal, non-goal, decision, reference, trade-off, acceptance signal, or stop-and-reopen condition.
- Include capability operation IDs or labels for any task that implements, validates, preserves, defers, or explicitly does not own a new/create/scaffold/authoring workflow.
- For each `[P]` task or explicit parallel batch, include enough detail that the leader can compile a bounded subagent execution packet: objective, write set, required references, forbidden drift, validation command, and done condition

## Capability Operation Coverage

| Operation | Upstream Source | Selected Entry Point | Task IDs / Packet Fields | Validation | Degradation Check |
| --- | --- | --- | --- | --- | --- |
| [create/scaffold operation] | [spec/alignment/plan/handoff] | [TUI route | core API | public CLI | private helper | user-confirmed deferral] | [T###, packet field, refinement checkpoint, valid blocker, or five-field deferral contract row] | [command or manual check] | [not template-only / not manual-copy-only / user-confirmed deferral carries confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact] |

- Template directories, sample files, and authoring documentation are supporting assets. They do not satisfy a confirmed create/scaffold operation unless manual copy was explicitly selected and confirmed upstream.
- A task packet anti-goal such as "do not add public commands" must carry a does-not-remove guard for the underlying operation, for example preserving scaffold through a TUI route or core API.

## User-Observable Path Coverage

| Feature / Surface | Real Entry Point | Producer Data | Transformer / State Builder | Consumer Surface | Executor / Boundary | Task IDs / Packet Fields | Validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [UI/TUI/CLI/API visible behavior] | [route, command, screen, install path, or runtime entry] | [catalog/config/request/source data] | [builder, adapter, reducer, model, or mapper] | [rendered panel, command output, API response, generated file] | [runner, boundary adapter, executor, HTTP handler] | [T### plus `consumer_surfaces` and `required_evidence: real_entrypoint_evidence`] | [test or concrete manual check from the real entrypoint] |

- Use this section when a task changes behavior that a user, command, integration, generated project, or downstream runtime can observe.
- Synthetic component, reducer, helper, or hand-built state tests may support implementation, but they do not satisfy `real_entrypoint_evidence` by themselves.
- Any task listed here must carry `consumer_surfaces` and `required_evidence` including `real_entrypoint_evidence` in its task packet fields.

## Implementation Target Boundary

- **Target root**: [copy from plan-contract.json / plan.md]
- **Target-relative paths**: [verified paths or explicit path discovery tasks]
- **Evidence status**: [target cognition | minimal live reads | user confirmation | explicit assumption | blocked]
- **Boundary constraints**: [current project role, target role, reference-only sources, forbidden drift]
- **MP obligations**: [MP-* IDs that shape implementation location, scope, validation, or stop conditions]
- **Reference-only paths**: [paths used only as transfer evidence, not as implementation write targets]

## Task-Generation Evidence Index

- `task-generation/evidence-index.json`: accepted task-generation lane handoffs and the task, dependency, write-set, batch, join-point, guardrail, or escalation decisions each handoff shaped.
- `task-generation/checkpoints.ndjson`: `task_generation_checkpoint` records written before delegated decomposition lanes, major synthesis points, and compaction-risk stops.
- `task-generation/handoffs/`: one structured handoff per accepted task-generation lane, named by stable lane id.
- Every task, dependency edge, write-set decision, parallel batch, join point, guardrail, or escalation below should be traceable to upstream artifacts and, when delegated lanes were used, to at least one accepted task-generation handoff.
- Every accepted task-generation handoff must have a consumer recorded in `task-generation/evidence-index.json`: a task ID, packet field, dependency edge, write-set decision, join point, guardrail, refinement checkpoint, `user_confirmed_deferrals` entry carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact, escalation, or blocker reason.

## Reference Fidelity Mapping

- Map each preserved or redesigned reference behavior inventory item to the task IDs, checkpoints, or join points that carry it forward.
- If a reference behavior is covered by a user-confirmed deferral, record confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact instead of silently omitting it.
- If a reference behavior is intentionally redesigned, point to the task or review checkpoint that must acknowledge the divergence.

## Consequence Obligation Mapping

| Obligation ID | Task IDs | Affected State / Dependency | Required References | Validation | Stop And Reopen |
| --- | --- | --- | --- | --- | --- |
| CA-### | T### | [state or dependency] | [files or artifacts] | [command or manual check] | [condition] |

## Analyze Remediation Mapping

Use this section only when regenerating tasks after a blocked or explicitly recorded legacy `sp-analyze` gate. Leave it as `No prior analyze blockers for this task package.` for first-pass task generation.

| Finding ID | Disposition | Task/Section Evidence | Notes |
|------------|-------------|-----------------------|-------|
| No prior analyze blockers | not_applicable | First task-generation pass | No remediation mapping required |

Allowed dispositions: `resolved`, `user_confirmed_deferral`, `not_applicable`, `escalated`.
If any finding is `escalated`, stop task generation and set `next_command` directly to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research` in `workflow-state.md`.

## Task Shaping Rules

- Top-level tasks should stay bounded enough to finish in one coffee break sized implementation slice, usually roughly 10-20 minutes.
- Each task should preserve one stable objective, one isolated write set, and one verification path.
- Delegated workers may still break a task into smaller 2-5 minute atomic internal steps, but `tasks.md` should stop at the smallest unit worth explicit orchestration.
- Stop decomposition once the current executable window is atomic.
- Leave later execution phases at the coarser story or phase level only when their exact task shape depends on earlier join points, then refine them after the checkpoint inside the current confirmed delivery instead of guessing too early.
- Every task MUST carry the enriched subagent contract fields defined in the `sp-tasks` shell output contract: agent, depends_on, parallel_safe, context navigation table, scope boundaries (write_scope / read_scope / forbidden), expected outputs, anti_goals, acceptance criteria, verify commands, handoff format, and failure handling (retry_max, escalation).
- Tasks that appear in User-Observable Path Coverage MUST also include `consumer_surfaces` and `required_evidence` with `real_entrypoint_evidence` so `sp-implement` can reject synthetic-only consumer proof.
- Before finalizing a task, confirm the independent-executability gate: a single subagent, reading only this task body plus the pointed-to context files, can complete the work without asking the leader for clarification. If not, the task MUST be refined before `tasks.md` can be finalized.
- If the active profile has a reference fidelity contract, add an explicit Fidelity Checkpoint before any implementation batch that can change fidelity-sensitive behavior, layout, workflow order, naming, or outputs.
- Any task that intentionally departs from the reference object MUST name the allowed deviation, required evidence, reviewer or acceptance condition, and the downstream artifact where the decision is recorded.

## Embedded Implement Review Policy

- `sp-implement` must run an embedded pre-implement review before the first code-writing task.
- `sp-implement` must run join-point drift review after each parallel batch, phase, pipeline stage, and sequential review window.
- Default review window limits: `max_completed_tasks_before_review=5`, `max_unreviewed_changed_paths=8`, `max_unreviewed_validation_failures=0`.
- Automatic task-layer repair is allowed only when the accepted goal and plan remain valid.
- Automatic task-layer repair may not rewrite spec, alignment, context, plan, upstream-derived profile fields, required evidence, final handoff decisions, Analyze Gate, or Reopen Contract.
- Audit records must be written to `implementation-review/reviews.ndjson` and `implementation-review/repairs.ndjson`, with snapshots under `implementation-review/snapshots/`.

### Task Identity Stability

- Completed task IDs are immutable.
- Incomplete task IDs stay stable when the objective remains the same.
- New repair or refinement tasks use append-only IDs.
- Follow-up repair tasks carry `repair_for: T###` or `refines: T###`.
- Superseded incomplete tasks remain traceable through `task-index.json`, `task-packets/` metadata, repair records, dependencies, `implement-tracker.md`, and worker-result references.
- The dependency graph and `next_batch` are authoritative after repair.

## Implementation-Readiness Task Self-Audit

Before final handoff to `sp-implement`, confirm:

- Buildable `FR-*` and buildable success criteria have task, checkpoint, refinement checkpoint, valid blocker, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact coverage.
- Locked planning decisions that affect implementation, compatibility, rollout, validation, sequencing, architecture shape, or guardrails are preserved in this task package.
- `Implementation Constitution` rules from `plan.md` are preserved through the implementation guardrails phase, `Task Guardrail Index`, task notes, or explicit escalation.
- `Task Guardrail Index` entries map applicable guardrails to concrete implementation tasks.
- Preserved capability operations map to implementation tasks, validation tasks, packet fields, refinement checkpoints, valid blockers, or user-confirmed deferrals carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
- User-observable UI/TUI/CLI/API/runtime paths map to at least one real-entrypoint validation task, refinement checkpoint, valid blocker, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
- No operation-shaped create/scaffold capability has degraded to template-only task output, manual copy docs, or an authoring guide without an executable entry point.
- Anti-goals that restrict public surfaces include does-not-remove guards.
- Each `[P]` task or explicit parallel batch has objective, write set, required references, forbidden drift, validation command, and done condition.
- Task packet readiness covers `DP1`, `DP2`, and `DP3` as far as task generation can determine before implementation.
- Reference fidelity behavior items map to task IDs, checkpoints, join points, refinement checkpoints, valid blockers, or user-confirmed deferrals carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
- Unmapped tasks are justified as setup, polish, verification, or cross-cutting work, or removed.
- Task dependencies and parallel batches do not contain obvious write-set conflicts.

Audit status keywords should explicitly cover buildable `FR-*`, locked planning decisions, task guardrails, DP readiness, reference fidelity, unmapped tasks, and write-set conflicts.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel only when the task has an isolated write set, no incomplete dependencies, stable upstream inputs, and its own verification path
- **[AGENT]**: Marks a task or guardrail action the AI must explicitly execute in the contract matrix; it is independent from `[P]` and is not a checklist-row label
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- **Agent role**: Role from the agent-teams pool assigned to this task. Agent roles belong in the task contract matrix and task packet JSON, not in checklist rows. Choose from: `security-reviewer`, `test-engineer`, `style-reviewer`, `performance-reviewer`, `quality-reviewer`, `api-reviewer`, `debugger`, `code-simplifier`, `build-fixer`, `git-master`, `executor`. Default to `executor` when no specialist role matches.
- **Write set**: Include all files and shared coordination surfaces the task will modify, including routers, registries, export barrels, schema indexes, and dependency injection containers
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

**Purpose**: Freeze architecture constraints, scenario profile inputs, required evidence, and boundary references before any code-writing batch starts

- [ ] T000 Read the boundary-defining files, contracts, and examples named in `plan.md` under `Required Implementation References`
- [ ] T001 Record the active implementation guardrails for this feature: framework ownership, preserved boundary pattern, forbidden drift, and review checks
- [ ] T002 Confirm the active scenario profile, reference fidelity contract if present, allowed deviations, and required evidence before implementation batches begin
- [ ] T003 Confirm the first implementation batch extends the existing boundary pattern instead of creating a parallel one

**Checkpoint**: Implementation guardrails captured - downstream batches now have explicit architecture constraints

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T004 Create project structure per implementation plan
- [ ] T005 Initialize [language] project with [framework] dependencies
- [ ] T006 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T007 Setup database schema and migrations framework
- [ ] T008 [P] Implement authentication/authorization framework
- [ ] T009 [P] Setup API routing and middleware structure
- [ ] T010 Create base models/entities that all stories depend on
- [ ] T011 Configure error handling and logging infrastructure
- [ ] T012 Setup environment configuration management

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (required when the testing contract applies) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

**Parallel Batch 1.1**: Independent failing tests with non-overlapping write sets
- [ ] T013 [P] [US1] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T014 [P] [US1] Integration test for [user journey] in tests/integration/test_[name].py
**Join Point 1.1**: Confirm both tests fail for the expected reasons before writing production code
Join Point Validation:
- Validation target: failing contract and integration tests for User Story 1
- Validation command: `pytest tests/contract/test_[name].py tests/integration/test_[name].py -q`
- Pass condition: both tests fail for the expected missing-behavior reasons, not for setup or syntax errors

### Implementation for User Story 1

**Parallel Batch 1.2**: Independent models or DTOs with isolated write sets
- [ ] T015 [P] [US1] Create [Entity1] model in src/models/[entity1].py
- [ ] T016 [P] [US1] Create [Entity2] model in src/models/[entity2].py
**Join Point 1.2**: Resolve any shared exports, registrations, or schema indexes before service work
Join Point Validation:
- Validation target: shared exports, registrations, or schema indexes updated after the parallel model batch
- Validation command: [Smallest trustworthy command or review check for the touched shared surface]
- Pass condition: downstream service work sees one canonical shared surface update with no conflicting registrations or missing exports
- [ ] T017 [US1] Implement [Service] in src/services/[service].py (depends on T015, T016)
- [ ] T018 [US1] Implement [endpoint/feature] in src/[location]/[file].py while preserving the established boundary/framework pattern named in `plan.md`
- [ ] T019 [US1] Add validation and error handling
- [ ] T020 [US1] Add logging for user story 1 operations

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (required when the testing contract applies) ⚠️

- [ ] T021 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T022 [P] [US2] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 2

- [ ] T023 [P] [US2] Create [Entity] model in src/models/[entity].py
- [ ] T024 [US2] Implement [Service] in src/services/[service].py
- [ ] T025 [US2] Implement [endpoint/feature] in src/[location]/[file].py
- [ ] T026 [US2] Integrate with User Story 1 components (if needed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (required when the testing contract applies) ⚠️

- [ ] T027 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T028 [P] [US3] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 3

- [ ] T029 [P] [US3] Create [Entity] model in src/models/[entity].py
- [ ] T030 [US3] Implement [Service] in src/services/[service].py
- [ ] T031 [US3] Implement [endpoint/feature] in src/[location]/[file].py

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
# Parallel Batch 1.1: launch all tests for User Story 1 together when the testing contract or spec requires them:
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Join Point 1.1: verify both tests fail for the expected reasons

# Parallel Batch 1.2: launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"

# Join Point 1.2: update shared exports or registrations before service implementation
```

---

## Implementation Dispatch

### Feature Delivery Shape

- Describe the whole task graph in plain language, for example:
  - serial phases with intra-phase parallel batches
  - mostly sequential
  - pipeline-heavy
  - parallel-ready after foundational work
- Do not use the current batch execution strategy as a blanket label for the whole feature.

### Current Ready Batch Dispatch

- Record the mandatory subagent dispatch decision for the **next executable batch only**:
  - `execution_model: subagent-mandatory`
  - `dispatch_shape: one-subagent | parallel-subagents | subagent-blocked`
  - `execution_surface: native-subagents`
- Also record the policy reason code, for example:
  - `safe-one-subagent`
  - `safe-parallel-subagents`
  - `no-safe-delegated-lane`
  - `packet-not-ready`
  - `runtime-no-subagents`
  - `low-delegation-confidence`
- If later batches are parallelizable but the current batch is not, say that explicitly instead of implying the whole feature has no parallelism.

### Confirmed Delivery Boundary

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete every user story and supporting task included in the confirmed product scope
4. **STOP and VALIDATE**: Run the representative end-to-end validation scenario from `quickstart.md` and the independent tests for each included story
5. Treat delivery as ready only when the user-confirmed scope, quality gates, and regression evidence are complete

### User-Confirmed Delivery Sequence

1. Complete Setup + Foundational → Foundation ready
2. Add each confirmed story in priority order or in the user-approved parallel sequence
3. Test each story independently before dependent work continues
4. Preserve user-confirmed deferrals and non-goals explicitly with confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact; do not infer a smaller release from User Story 1 or any execution phase
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

## Enriched Task Reference Example

Below is a complete enriched task showing every required subagent contract field. Generated `tasks.md` files must use this shape for every implementation task.

```markdown
## T017: Implement JWT auth middleware

### Identity
| Field | Value |
|-------|-------|
| agent | security-reviewer |
| depends_on | [T015: AuthService interface, T016: JWT utility functions] |
| parallel_safe | true |

### Context Navigation
| Need | Find it at |
|------|-----------|
| JWT payload structure | data-model.md#AuthPayload |
| Token expiry strategy | plan.md#token-expiry-strategy |
| Protected route list | contracts/auth-api.md |
| Standard error response format | contracts/error-response.md |
| Reference implementation | src/middleware/ratelimit.ts（same middleware pattern） |

### Scope Boundaries
| Field | Value |
|-------|-------|
| write_scope | [src/middleware/auth.ts, tests/auth/middleware.test.ts] |
| read_scope | [src/auth/types.ts, contracts/auth-api.md, contracts/error-response.md] |
| forbidden | [src/db/, .env, src/config/] |
| does_not_remove | [login capability through middleware contract, scaffold capability through TUI route] |
| capability_operations | [implements auth middleware, does not own scaffold operation] |
| consumer_surfaces | [Protected route middleware invoked through real HTTP request path] |
| required_evidence | [consumer_evidence, real_entrypoint_evidence] |

### Expected Outputs
- src/middleware/auth.ts （新建）
- tests/auth/middleware.test.ts （新建，>=80% coverage）

### Anti-Goals
- Do not introduce new npm dependencies
- Do not access the database directly（use AuthService interface）
- Do not modify existing public types in src/auth/types.ts

### Acceptance Criteria
- [ ] Valid token -> inject AuthPayload into req.context, continue chain
- [ ] Expired token -> return 401 with standard error format
- [ ] Missing Authorization header -> return 401
- [ ] Malformed token -> return 400
- [ ] Whitelist paths pass through untouched
- [ ] Security lint is clean

### Verify Commands
```
npx jest tests/auth/middleware.test.ts --coverage
npx eslint src/middleware/auth.ts
npx tsc --noEmit
```

### Handoff Format
- status: success | failed | blocked
- changed_files: ["src/middleware/auth.ts", "tests/auth/middleware.test.ts"]
- validation_output: {"jest": "PASS", "eslint": "clean", "tsc": "clean"}
- concerns: [] | ["specific concern"]
- recovery_hints: [] | ["suggested recovery direction"]

### Failure Handling
| Field | Value |
|-------|-------|
| retry_max | 2 |
| escalation | debugger（escalate for diagnosis after retries exhausted） |
```

---

## Notes

- [P] tasks = isolated write set, stable inputs, no incomplete dependencies, independent verification
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests are default deliverables for behavior changes, bug fixes, and refactors
- If the touched area lacks a reliable automated test surface, add bootstrap tasks before implementation so RED can be proven honestly
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, shared registration file conflicts, and cross-story dependencies that break independence

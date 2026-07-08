Trigger: before finalizing tasks.md, repairing task-layer defects, or handing off to implementation.

Purpose: preserve complete-first task generation, self-audit, review preparation, remediation, and escalation semantics.

Preserved Contract: implementation remains blocked until the task package passes self-audit and records `next_command: /sp.implement`.

## Complete-First Task Generation

This section defines complete-first scope preservation for generated task packages.

Task generation must cover the complete user-confirmed scope from `spec.md`,
`alignment.md`, `context.md`, `plan.md`, `plan-contract.json`, and approved handoff
files. `sp-tasks` may choose execution phases, dependency order, parallel batches,
join points, and refinement checkpoints, but it must not shrink scope. Do not shrink scope.

- Complexity alone is not a valid reason to split delivery scope, defer, block, or route upstream.
- Handle complex but clear work through dependency ordering, isolated write sets,
  parallel-safe batches, join-point validation, refinement tasks, and verification
  tasks.
- Execution phases are ordering, not delivery deferral.
- Do not move confirmed behavior to an MVP, pilot, prototype, first release,
  future-work delivery slice, agent-invented `v1/v2`, or agent-invented `P0/P1`.
- User story priorities such as `P1`, `P2`, and `P3` remain ordering labels from
  `spec.md`; they are not delivery-scope buckets.
- Runtime capability limits are blockers only under the adaptive execution policy
  for heavy, safety-critical, or unpacketizable work. They are not permission to
  shrink scope.
- Every valid deferral must be user-confirmed and record confirmation source, exact
  excluded behavior, residual risk, reopen or stop condition, and downstream
  artifact.
- If the user did not confirm the deferral, task the behavior, create a refinement
  or validation checkpoint that keeps it inside the current feature, or identify a
  valid hard blocker.

4. **Execute task generation workflow**:
    - [AGENT] Before task decomposition begins, split work only into the supported task-generation lanes: `story and phase decomposition`, `dependency graph analysis`, and `write-set and parallel-safety analysis`.
    - [AGENT] Before dispatch begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="tasks", snapshot, workload_shape)`
    - Before emitting high-risk batches, classify whether they need extra review: `classify_review_gate_policy(workload_shape)`
    - The chosen dispatch shape applies to the **current ready batch**, not automatically to the entire feature or task graph.
    - Do not use the current batch execution strategy as a blanket label for the whole feature.
    - Primary decomposition goal: maximize safe native-subagent throughput for later `sp-implement` runs by isolating write sets and turning ready work into a dispatch-ready lane packet instead of a vague checklist.
    - Persist the adaptive decision fields exactly: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, `workflow_status: ready | blocked`, `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`, `execution_surface: leader-inline | native-subagents | none`, `capability_degraded: false | true`, and `blocked_reason: required when blocked`.
    - Adaptive decision order:
      - If the task-generation workload is lightweight safe, use `execution_mode: light`, `dispatch_shape: leader-inline`, and `execution_surface: leader-inline`; no task-generation lane handoff files are required.
      - If the workload is standard and native subagents are available, dispatch `one-subagent` for exactly one validated isolated lane or `parallel-subagents` for two or more isolated lanes.
      - If the workload is standard, native subagents are unavailable, and no high-risk trigger is present, continue leader-inline with `capability_degraded: true`.
      - If the workload is heavy or safety-critical and native subagents are unavailable, or if heavy task generation cannot be packetized safely, record `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, `execution_surface: none`, and a concrete `blocked_reason`; stop before synthesizing `tasks.md`.
    - Managed-team fallback is not part of adaptive plan/tasks dispatch.
    - Artifact-writing delegated task-generation lanes must be dispatched as writable, execution-capable native subagent lanes. If the runtime exposes role, sandbox, or permission choices, select a role/sandbox that can write the declared handoff file; a read-only lane is not valid for `task-generation/handoffs/<lane-id>.json`.
    - Do not dispatch a read-only explorer, reviewer, or diagnostic lane to satisfy a delegated task-generation lane that must write a handoff. Such lanes may inform the leader only as supplemental evidence, and they do not satisfy `one-subagent` or `parallel-subagents` task-generation handoff requirements.
    - The delegated lane contract's allowed write scope must include the exact expected handoff path, `task-generation/handoffs/<lane-id>.json`, and must forbid writes outside that path unless the lane is explicitly assigned a task-generation artifact.
    - Before dispatching any delegated task-generation lane, persist a `task_generation_checkpoint` record to `task-generation/checkpoints.ndjson` with the lane id, dispatch shape, authoritative inputs, expected handoff path, and current workflow-state summary.
   - Each delegated lane must persist the lane's structured handoff to `task-generation/handoffs/<lane-id>.json` before the leader accepts the lane, waits at a join point, or synthesizes `tasks.md`.
   - Update `task-generation/evidence-index.json` after each accepted delegated lane handoff with lane id, handoff path, source artifacts inspected, decisions or constraints contributed, affected task IDs or batch IDs, blocker status, and integration status.
    - Consume `task-generation/evidence-index.json` before final task synthesis when delegated lanes were used: for every accepted handoff, mark the handoff as `integrated`, assigned to a refinement checkpoint, recorded in `user_confirmed_deferrals` with confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact, or `blocked`, and name the target task ID, dependency edge, write-set decision, parallel batch, join point, guardrail, packet field, or escalation that consumed it.
    - Do not synthesize `tasks.md` from chat-only delegated lane results. If a delegated lane reports only prose, idle state, or an unwritten handoff, mark `subagent-blocked`, write the blocker to `workflow-state.md`, and stop or re-dispatch with a writable lane and a valid handoff path.
    - When resuming after compaction and delegated lanes were used, re-read `workflow-state.md`, `task-generation/checkpoints.ndjson`, `task-generation/evidence-index.json`, and all accepted `task-generation/handoffs/<lane-id>.json` files before continuing task synthesis.
    - Required join points:
      - before writing `tasks.md`
      - before emitting canonical parallel batches and join points
    - Record the chosen dispatch shape, blocked reason if any, selected lanes, and join points in the generated report and implementation strategy section.
    - Extract the active profile, activated gates, task-shaping rules, and required evidence obligations from `workflow-state.md`; `sp-tasks` consumes the same profile contract or active profile that `sp-specify`/`sp-plan` persisted, not a newly invented taxonomy.
    - Read `plan-contract.json` as authoritative task-generation input when present.
    - Read `planning/evidence-index.json` and all accepted `planning/handoffs/*.json` when present; treat accepted planning lane contributions as upstream planning inputs, not discarded background evidence.
    - Emit `handoff-to-tasks.json`, `task-index.json`, and per-task packet JSON under `task-packets/` when standard/heavy mode uses delegated task-generation lanes or downstream delegated implementation needs packets; in light mode, emit only the minimum light-mode `tasks.md` contract unless `task-index.json` is useful.
    - When delegated task-generation handoffs exist, include references in `handoff-to-tasks.json` and `task-index.json` to the accepted `task-generation/handoffs/<lane-id>.json` files that shaped each task, dependency edge, write-set decision, parallel batch, join point, guardrail, or escalation.
    - Do not mark task generation complete while `task-generation/evidence-index.json` contains an accepted handoff without an explicit consuming task, packet field, dependency edge, refinement checkpoint, `user_confirmed_deferrals` entry carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact, escalation, or blocker reason.
    - Carry complexity level, must-preserve invariants, allowed optimization scope, and stop-and-reopen conditions into each task packet.
    - Keep `sp-tasks` aligned with the persisted first-release profile contract: `active_profile` must be one of the two supported profiles, `Standard Delivery` or `Reference-Implementation`.
    - If `workflow-state.md` presents an unsupported `active_profile` during first release, `sp-tasks` stops before decomposition and tells the operator to repair/re-run upstream routing state before task generation continues.
    - Treat `Scenario profile inputs` as task-shaping inputs: active profile, routing reason, activated gates, fidelity obligations, deviation review requirements, and required evidence.
    - **Analyze remediation mode**: If `workflow-state.md` contains an open `Analyze Gate` blocker bundle for `sp-tasks`, map each task-layer finding to exactly one disposition: `resolved | user_confirmed_deferral | not_applicable | escalated`.
    - `resolved`: fix the issue in this task pass and name the task, guardrail, checkpoint, packet field, or section evidence.
    - `user_confirmed_deferral`: keep the issue explicit in `user_confirmed_deferrals` with confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
    - `not_applicable`: state why the prior finding no longer applies and cite the artifact evidence.
    - `escalated`: stop task generation for the current pass because the missing truth belongs to `plan`, `clarify`, or `deep-research`.
    - Escalation is terminal for the current `sp-tasks` run. If required upstream truth is missing, write the escalation evidence into `workflow-state.md` and set `next_command` directly to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`. This sets `next_command` directly to `/sp.plan`, `/sp.clarify`, or `/sp.deep-research` instead of sending the user back through `/sp.analyze` first.
    - Load plan.md and extract tech stack, libraries, project structure
    - Extract `Locked Planning Decisions`, `Implementation Constitution`, `Canonical References`, `Input Risks From Alignment`, `Must-Preserve Carry-Forward`, and `Decision Preservation Check` from plan.md when present
    - Carry implementation-shaping `MP-*` items into task guardrails, required references, validation checkpoints, task packets, refinement checkpoints, valid blockers, or user-confirmed deferrals carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
    - If a task would violate an `MP-*` non-goal, decision, reference obligation, or trade-off rationale, stop and route back to the user conflict decision instead of silently generating divergent tasks.
    - If `Reference Fidelity Inputs` or `Reference Behavior Inventory` exist, map every preserved or redesigned reference behavior to at least one task, checkpoint, join point, refinement checkpoint, valid blocker, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact before `tasks.md` is finalized.
    - **Feature UI brief packet compilation**:
      - When `ui-brief.md` exists, compile its contract into `ui_contract`.
      - Set `ui_fidelity_mode` to `approximate`, `high`, or `inspiration`.
      - Add `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html` to required references.
      - Add required states and evidence to task packet fields.
      - For `approximate` and `high`, include `required_evidence: [reference_source_evidence, ui_fidelity_criteria, real_entrypoint_ui_evidence, visual_comparison_or_human_review]`.
      - For `high`, also include `deviation_log`.
      - Treat those UI-specific labels as task-packet aliases only. Persisted `workflow-state.md` and `Reference-Implementation` `required_evidence` MUST remain canonical: reference source evidence, fidelity criteria, verification entry points, difference inventory, and accepted deviations.
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
    - **Missing design artifacts**: If any design artifact required by the current scope is missing, stop and route back to `{{invoke:plan}}`.
    - Do not generate `tasks.md` from an artifact set that is missing required design inputs.
    - Only optional artifacts may be absent without blocking task generation.
    - Generate tasks organized by user story (see Task Generation Rules below)
    - Treat tests as default deliverables for product behavior changes, bug fixes, refactors with regression risk, public API contracts, persistence/migration changes, security-sensitive behavior, and generated outputs consumed by users or tools
    - If the touched area lacks a reliable automated test surface, add the smallest runnable test surface only when the change risk requires automated proof; otherwise record the no-new-test rationale, replacement validation, and residual risk
    - Top-level tasks should fit one bounded implementation slice: roughly 10-20 minutes, one stable objective, one isolated write set, and one verification path
    - A subagent can still execute the task internally through smaller 2-5 minute atomic steps, but do not explode the public task list into coordinator-hostile micro-tasks
    - Stop decomposition once the current executable window is atomic. Leave later execution phases at the coarser story or phase level only when their exact task shape depends on earlier join-point evidence; this is refinement inside the current confirmed delivery, not delivery deferral or future work.
    - If later work still depends on upstream evidence, add a refinement checkpoint instead of guessing detailed downstream tasks too early
    - Carry profile-required evidence into task completion criteria instead of relying only on generic behavior validation. When the active profile requires screenshots, trace IDs, reference comparisons, migration proof, or other required evidence, attach that evidence obligation to the relevant task done condition or join point pass condition.
    - If `Implementation Constitution` defines boundary-defining references or forbidden drift, add an implementation-guardrails phase before setup so implementers must confirm the existing pattern before changing code
    - **Task Guardrail Index**: Add task-to-guardrail mapping when tasks inherit execution rules from plan.md or constitution.md. Keep the mapping compact so downstream execution can resolve applicable hard rules per task.
    - Treat `[P]` as a lane-level parallel-eligible marker, not as permission to collapse multiple tasks into one batch-owner execution lane.
    - For every `[P]` task or parallel batch, include: objective, write set, required references, forbidden drift, validation command, and done condition — the information downstream execution needs to dispatch work safely
    - Generate dependency graph showing user story completion order
    - Derive a write set for each task (files or shared registration surfaces it will modify)
    - Group ready tasks into each phase's parallel batches using those write sets
    - A `parallel batch` is the current ready set of isolated lane-level tasks bounded by a join point.
    - Batch range labels such as `T012-T021` are summaries, not executable lane identities.
    - Each `[P]` task remains a lane-level execution unit unless an explicit wrapper task defines a serial coordination step.
    - Identify the member lanes of a parallel batch explicitly enough that downstream execution does not infer one batch-owner implementer task from the range label alone.
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
    - **Implementation-Readiness Task Self-Audit**: Before finalizing `tasks.md`, run the task-layer subset of the `sp-analyze` checks against the generated task package.
    - Confirm every buildable `FR-*` and buildable success criterion has at least one task, checkpoint, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
    - Confirm every locked planning decision that affects implementation, compatibility, rollout, validation, sequencing, architecture shape, or guardrails appears in `tasks.md`.
    - Confirm `Implementation Constitution` rules from `plan.md` are preserved through a guardrail phase, `Task Guardrail Index`, task notes, or explicit escalation.
    - Confirm the `Task Guardrail Index` maps applicable guardrails to concrete implementation tasks.
    - Confirm every UI/TUI/CLI/API/runtime-visible path has User-Observable Path Coverage with a real-entrypoint validation task or a user-confirmed deferral carrying the full five-field deferral contract.
    - Confirm each `[P]` task or explicit parallel batch has objective, write set, required references, forbidden drift, validation command, and done condition.
    - Confirm task packet readiness covers `DP1`, `DP2`, and `DP3` as far as task generation can determine before implementation.
    - Confirm reference fidelity behavior items map to task IDs, checkpoints, join points, refinement checkpoints, valid blockers, or user-confirmed deferrals carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
    - Confirm unmapped tasks are justified as setup, polish, verification, or cross-cutting work, or remove them.
    - Confirm task dependencies and parallel batches do not contain obvious write-set conflicts.
    - If the self-audit finds task-layer defects, repair them before completing `sp-tasks`. If the defect requires missing upstream truth, escalate instead of producing speculative tasks.
    - **Embedded Implement Review Preparation**: A clean task package still records `next_command: /sp.implement`; do not add or expose a separate public review workflow. When generating `tasks.md`, `task-index.json`, `task-packets/*.json`, or `handoff-to-implement`, prepare the embedded review contract with `embedded_review_gate: required`, `auto_repair_tasks: true`, default `review_window_policy`, reviewable join points before first code-writing and after each parallel batch, phase, pipeline stage, and sequential review window, plus packet regeneration expectations whenever task-layer repair changes dependencies, write sets, next batches, or packet metadata.
    - Validate task completeness (each user story has all needed tasks, independently testable)
    - Validate decision preservation: if a locked planning decision or implementation constitution rule affects implementation, compatibility, rollout, validation, sequencing, or architecture shape, at least one task or phase note must preserve it explicitly instead of silently dropping it
    - Validate reference behavior preservation: if a preserved or redesigned reference behavior exists in the spec/plan package, at least one task, checkpoint, refinement checkpoint, valid blocker, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact must account for it before task generation can complete

    **Feature delivery shape**: Classify the whole task graph in plain language (e.g., `serial phases with intra-phase parallel batches`, `mostly sequential`, `pipeline-heavy`, `parallel-ready after foundational work`). If later batches are parallelizable but the current batch is not, state that explicitly.

5. **Generate tasks.md**: Use `templates/tasks-template.md` as structure, fill with:
   - Correct feature name from plan.md
   - Phase 1: Setup tasks (project initialization)
   - Phase 2: Foundational tasks (blocking prerequisites for all user stories)
   - Phase 3+: One phase per user story (in priority order from spec.md)
   - Each phase includes: story goal, independent validation criteria, risk-required test tasks, no-new-test rationale where tests are omitted, implementation tasks
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
   - User-Observable Path Coverage section for every UI/TUI/CLI/API/runtime-visible behavior, including task packet fields `consumer_surfaces` and `required_evidence: real_entrypoint_evidence` where required
   - Design Quality Coverage section for user-visible surfaces with surface name, design source, required states, platform coverage, evidence required, and task IDs that implement and verify the surface
   - UI tasks should cover default, hover, focus, disabled, loading, empty, error, and success states when relevant, responsive layout or platform adaptation, accessibility checks, screenshots, terminal samples, recordings, or manual review artifacts, and no-color or narrow-terminal modes for TUI/CLI
   - Analyze Remediation Mapping section when regenerating tasks after a blocked `sp-analyze` gate
   - Parallel execution examples per story
    - Planning inputs section showing locked decisions, carried risks, and required validation references when they materially shape execution
    - Planning inputs section showing implementation constitution rules when they materially shape execution
    - `Task Guardrail Index` entries or equivalent task-to-guardrail mapping when subagent work must inherit explicit execution rules
    - Implementation strategy section (phased delivery, priority-ordered delivery, capability-aware parallel execution)

6. **Report**: Output path to generated tasks.md and summary:
    - Total task count
    - Task count per user story
    - task-generation evidence paths when delegated lanes were used: `task-generation/evidence-index.json`, `task-generation/checkpoints.ndjson`, and accepted `task-generation/handoffs/<lane-id>.json` files; otherwise report `delegated_task_generation_lanes: none`
    - execution_model: adaptive
    - execution_mode: light | standard | heavy
    - workflow_status: ready | blocked
    - dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked
    - execution_surface: leader-inline | native-subagents | none
    - capability_degraded: false | true
    - blocked_reason: required when blocked
    - Feature delivery shape (whole task graph)
    - Parallel opportunities identified
    - Parallel batch count and the join points that gate downstream work
    - Independent validation criteria for each story, including risk and behavior driven validation, no-new-test rationale where tests are omitted, replacement validation, and residual risk
    - Confirmed delivery scope and user-confirmed delivery sequence, including any user-confirmed deferrals or constraint-driven scope adjustments
    - Scope reduction requires user confirmation; do not infer a smaller release from User Story 1 or the smallest independently testable story
    - Confirm first-release profile scope stayed within the two supported profiles: `Standard Delivery` and `Reference-Implementation`
    - Format validation: Confirm ALL tasks follow the checklist format (checkbox, ID, labels, file paths)
    - workflow-state path
    - Analyze remediation summary when remediation mode is active:
      - handled previous analyze findings count
      - resolved count
      - user_confirmed_deferral count
      - not_applicable count
      - escalated count
      - evidence sections or task IDs for resolved findings
    - Implementation-Readiness Task Self-Audit result:
      - coverage mapping status
      - locked decision preservation status
      - guardrail mapping status
      - user-observable path coverage status
      - DP1/DP2/DP3 packet-readiness status
      - reference fidelity mapping status
      - unmapped task status
      - write-set conflict status
    - Embedded implement review preparation:
      - embedded_review_gate: required
      - auto_repair_tasks: true
      - review_window_policy: max_completed_tasks_before_review=5, max_unreviewed_changed_paths=8, max_unreviewed_validation_failures=0
      - visible_review_command: none
      - next_command remains `{{invoke:implement}}`
    - Recommended next command: `{{invoke:implement}}` for normal completed or non-escalated task generation.
    - For escalated remediation: preserve the upstream `next_command` (`/sp.plan`, `/sp.clarify`, or `/sp.deep-research`) and stop without an analyze handoff.
    - cognition follow-up: if artifact-only task generation exposes future shared surfaces, workflow joins, or validation entry points that the current project cognition runtime does not yet encode, record that as an advisory in `workflow-state.md` or `tasks.md`; do not mark project cognition dirty or require a refresh until actual source/runtime changes make the runtime truth out of date.
    - If this workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, follow the shared inline closeout contract:

{{spec-kit-include: ../../command-partials/common/inline-project-cognition-update.md}}
   - before final completion text, write or update `WORKFLOW_STATE_FILE` so it records:
     - `active_command: sp-tasks`
     - `phase_mode: task-generation-only`
     - current authoritative files
     - exit criteria for task-generation completion
     - the next action required before handoff
     - `next_command: /sp.implement` for normal completed or non-escalated task generation
     - escalated remediation preserves the upstream `next_command` (`/sp.plan`, `/sp.clarify`, or `/sp.deep-research`) and stops without an analyze handoff

7. **Check for extension hooks**: After tasks.md is generated, check if `.specify/extensions.yml` exists in the project root.
   - If it exists, read it and look for entries under the `hooks.after_tasks` key
{{spec-kit-include: ../../command-partials/common/extension-hooks-after-body.md}}

Context for task generation: {ARGS}

The tasks.md should be immediately executable - each task must be specific enough that an LLM can complete it without additional context.

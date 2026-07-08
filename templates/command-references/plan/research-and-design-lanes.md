Trigger: when gathering research, preserving complete-first scope, adopting design inputs, or shaping capability plans.

Purpose: preserve complete-first planning, design-system adoption, UI brief adoption, operational consequence design, and capability preservation planning.

Preserved Contract: planning may refine design artifacts but must not reduce confirmed scope or drop operation-shaped capability.

## Complete-First Scope Preservation

The active feature scope is the complete user-confirmed scope from `spec.md`,
`alignment.md`, `context.md`, `plan-contract.json`, and approved discussion or
brainstorming handoffs. `sp-plan` may choose architecture, sequencing, dependency
order, dispatch shape, and validation strategy, but it must not shrink scope.

- Complexity alone is not a valid reason to split, defer, block, or return upstream; do not shrink scope.
- Handle complex but clear work through dependency ordering, implementation
  guardrails, design artifacts, validation paths, and refinement checkpoints.
- Execution phases are ordering, not delivery deferral.
- Do not convert confirmed scope into an MVP, pilot, prototype, first release,
  future-work delivery slice, agent-invented `v1/v2`, or agent-invented `P0/P1`.
- User story priorities such as `P1`, `P2`, and `P3` remain ordering labels from
  `spec.md`; they are not delivery-scope buckets.
- If a deferral is valid, it must be user-confirmed and record confirmation source,
  exact excluded behavior, residual risk, reopen or stop condition, and downstream
  artifact.
- `plan.md` and `plan-contract.json` must carry the same confirmed delivery scope
  and user-confirmed deferral contract, including `confirmed_delivery_scope` and
  `user_confirmed_deferrals`.
- If the user did not confirm the deferral, plan the behavior, create a refinement or validation checkpoint that keeps it inside the current feature, or identify a valid hard blocker.
- Runtime capability limits are blockers only under the adaptive execution policy
  for heavy, safety-critical, or unpacketizable work. They are not permission to
  shrink scope or relabel confirmed behavior as a later version.

## Design System Adoption

For UI-facing features, convert `DESIGN.md` into implementation constraints:

- design-system source and status
- token strategy
- component reuse and extension policy
- platform adaptation strategy
- accessibility requirements
- screenshot or output evidence strategy
- forbidden styling drift

Name where implementers may use judgment and where the design system is binding.

## Feature UI Brief Adoption

When `FEATURE_DIR/ui-brief.md` exists, read it before planning implementation details. Treat it as a planning input alongside `DESIGN.md`, not as optional background.

For `approximate` and `high` fidelity, preserve the existing `Reference-Implementation` profile and promote these UI-specific evidence terms into `Implementation Constitution`:

- `reference_source_evidence`
- `ui_fidelity_criteria`
- `real_entrypoint_ui_evidence`
- `visual_comparison_or_human_review`
- `deviation_log` when fidelity is `high`

Persist canonical `Reference-Implementation` required evidence terms while carrying the UI aliases as mapping notes: `reference_source_evidence` maps to reference source evidence, `ui_fidelity_criteria` maps to fidelity criteria, `real_entrypoint_ui_evidence` maps to verification entry points, `visual_comparison_or_human_review` maps to verification entry points plus difference inventory or human approval, and `deviation_log` maps to difference inventory and accepted deviations.

The plan must state what implementers must preserve, what they may adapt, what they must not copy, and whether visual comparison can be agent-verified or needs human review.

## Operational Consequence Design

Before `sp-tasks`, convert every triggered `CA-###` consequence obligation into concrete operational design.

- Preserve the upstream Affected Object Map, State-Behavior Matrix, Dependency Impact Table, Recovery And Validation Contract, and Coverage Gaps from `spec.md`, `alignment.md`, `context.md`, `references.md`, and machine-readable handoffs.
- For each implementation-shaping `CA-###` obligation, define the operational state machine, ordering, locking or lease behavior, idempotency, concurrency hazards, recovery path, observability, rollout or migration notes, and verification strategy.
- Name behavior for running-state objects explicitly: drain, cancel, force, wait, retry, resume, ignore late result, or preserve until a later lifecycle event.
- Map every dependency impact to plan sections, design artifacts, contracts, data model notes, quickstart validation, refinement checkpoints, valid blockers, or user-confirmed deferrals carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
- Ensure `plan-contract.json` carries the same `CA-###` obligations, operational decisions, unresolved coverage gaps, and stop-and-reopen conditions as the Markdown plan.
- If any `CA-###` obligation cannot be designed safely in `sp-plan`, stop before `sp-tasks` and route back to `{{invoke:specify}}`, `{{invoke:clarify}}`, or `{{invoke:deep-research}}` with the missing decision named.

## Capability Preservation Planning

Before command, route, or contract design is locked, preserve every operation-shaped capability from `spec.md`, `alignment.md`, `context.md`, and `brainstorming/handoff-to-specify.json`.

- Treat new/create/scaffold/authoring/template-creation signals as buildable capability operations when they were preserved or in scope upstream.
- Command-surface minimization must not delete capability. If the plan chooses a small public command surface, perform entry-point remapping: map the capability to a TUI route, core API, public CLI command, private helper invoked by the TUI, refinement checkpoint, valid blocker, or user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
- For every remapped capability, name the selected entry point, owning module or route, design artifact, quickstart or test proof, and any user confirmation for narrowing.
- If the plan removes or defers an upstream operation-shaped capability because of a command-surface constraint, stop and route back to `{{invoke:specify}}` or `{{invoke:clarify}}` unless the user already confirmed that narrowing.
- Record create/scaffold operation mappings in `plan.md#Capability Preservation Plan` and in `plan-contract.json` so `sp-tasks` cannot convert them into template-only or documentation-only work.
- A static template directory, manual copy docs, or authoring guide is support material; it is not an implementation of a confirmed scaffold operation unless the user-confirmed scope says manual copy is the intended entry point.

{{spec-kit-include: ../../command-partials/common/planning-context-loading-gradient.md}}

**Project cognition gate:** query the active project's runtime before broad
repository reads.

Run or emulate:

```text
{{specify-subcmd:project-cognition compass --intent plan --query="$ARGUMENTS" --format json}}
```

After the default compass packet, run the advanced `lexicon -> semantic_intake -> query` path only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, use `project-cognition lexicon --mode catalog` as the alias catalog, write agent-authored `semantic_intake` and `concept_decisions`, then run `project-cognition query --query-plan "<query_plan_json>"`; include `query_plan`, `semantic_intake`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `repository_search_terms`, project-language search terms, and facet coverage; do not search only the raw user words before source search. Agent-owned semantic normalization remains mandatory: `agent_normalization` and raw lexicon ranking are bootstrap signals only; if `agent_normalization` is omitted, treat it as `required=false`; use `write_semantic_intake_from_alias_catalog` when needed. Raw lexicon ranking is only a bootstrap; CJK or mixed CJK/ASCII input still requires agent-owned normalization even when positive raw lexical matches exist. The agent still owns translation. Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`.

Use the returned readiness:

- `query_ready`: read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons.
- `review`: perform only the returned `minimal_live_reads` before continuing and inspect `coverage_diagnostics`.
- `needs_rebuild`: route through `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only for documented brownfield rebuild triggers.
- `blocked`: report the blocking runtime issue and continue with live evidence only where this workflow allows degraded navigation.
- **CARRY FORWARD**: Promote project-cognition facts into planning constraints,
  `Implementation Constitution`, boundary rules, verification strategy, and
  `plan-contract.json` when they affect implementation shape.

4. **Validate alignment status before planning**:
   - If `alignment.md` is missing:
     - ERROR "Missing alignment report. Run {{invoke:specify}} first or re-run it to complete requirement alignment."
   - If `context.md` is missing:
     - ERROR "Missing context artifact. Run {{invoke:specify}} again or {{invoke:clarify}} to rebuild `context.md` before planning."
   - Read `Locked Decisions For Planning`, `Outstanding Questions`, `Remaining Risks`, and `Planning Gate Recommendation` from `alignment.md` when present.
   - Read `Locked Decisions`, `Claude Discretion`, `Canonical References`, `Existing Code Insights`, `Specific User Signals`, and `Outstanding Questions` from `context.md`.
   - If the alignment report status is `Aligned: ready for plan`:
     - continue only if no planning-critical unresolved items remain around scope, workflow behavior, data/state expectations, compatibility, external dependencies, or success criteria
   - If the alignment report status is `Force proceed with known risks`:
     - continue, but carry all remaining risks into planning as explicit planning constraints and open risks
   - Otherwise:
     - ERROR "Specification is not aligned enough for planning."
   - If `Planning Gate Recommendation` indicates `/sp.clarify` or the unresolved items still materially affect plan structure:
     - ERROR "Specification still has planning-critical gaps. Run {{invoke:clarify}} or refine {{invoke:specify}} before planning."
   - If `Planning Gate Recommendation` indicates `/sp.deep-research`, or the Feasibility / Deep Research Gate says `Needed before plan` or `Blocked`:
     - ERROR "Specification still has unproven feasibility. Run {{invoke:deep-research}} before planning."
   - If `deep-research.md` exists but lacks a `Planning Handoff` section and the feature depends on its research conclusions:
     - ERROR "Deep research evidence is not ready for planning. Re-run {{invoke:deep-research}} to synthesize a Planning Handoff."
   - If `deep-research.md` exists and includes Planning Handoff IDs (`PH-###`), preserve those IDs in plan sections that consume the research. Do not collapse traceable handoff items into unsourced prose.

5. **Assume the specification package is analysis-first**:
   - Treat the canonical workflow token `/sp.specify` as the primary pre-planning requirement-analysis entry point.
   - Tell the user to run `{{invoke:specify}}` when they need to start or repeat that requirement-analysis step manually.
   - Treat the canonical workflow token `/sp.clarify` as the follow-up enhancement path when the spec package needs deeper analysis before planning.
   - Tell the user to run `{{invoke:clarify}}` when that follow-up must be invoked manually.
   - Use capability decomposition from `spec.md` when sequencing design work
   - Use `references.md` when retained sources or reusable examples affect planning choices
   - Use `deep-research.md` when feasibility evidence, disposable demo results, research-agent findings, synthesis decisions, or implementation-chain constraints affect planning choices
   - Treat the `Planning Handoff` section in `deep-research.md` as a direct planning input, not a status note. Preserve its `PH-###` IDs, recommended approach, architecture implications, module boundaries, API/library choices, data flow notes, demo artifacts, validation implications, rejected options, and residual risks.
   - Use the `Evidence Quality Rubric` and `Planning Traceability Index` from `deep-research.md` to distinguish blocking constraints from informative context.
   - Treat `Locked Decisions`, `Claude Discretion`, `Canonical References`, and `Deferred / Future Ideas` in `spec.md` as active planning inputs, not descriptive appendix material
   - If `spec.md` includes `Fidelity Requirements`, treat `Reference Object`, `Required Fidelity`, and `Reference Behavior Inventory` as mandatory planning inputs rather than optional background.
   - Treat `context.md` as the primary implementation-context artifact that captures downstream planning decisions explicitly
   - Treat `workflow-state.md` scenario profile fields as active planning inputs. The plan consumes the existing supported profile contract persisted by upstream routing.
   - Do not perform a second informal task classification pass; `sp-plan` consumes `active_profile`, `required_sections`, `activated_gates`, `task_shaping_rules`, `required_evidence`, and `transition_policy` from `workflow-state.md`.
   - Do not introduce a separate clarification command as the normal next step for routine planning readiness
   - [AGENT] Before plan synthesis begins, split the work only into the supported plan lanes: `research`, `data model`, `contracts`, and `quickstart and validation scenarios`.
   - [AGENT] Before dispatch begins, assess the current agent capability snapshot and apply the shared policy contract: `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)`.
   - Persist the adaptive decision fields exactly: `execution_model: adaptive`, `execution_mode: light | standard | heavy`, `workflow_status: ready | blocked`, `dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked`, `execution_surface: leader-inline | native-subagents | none`, `capability_degraded: false | true`, and `blocked_reason: required when blocked`.
   - Adaptive decision order:
     - If the workload is lightweight safe, use `execution_mode: light`, `dispatch_shape: leader-inline`, and `execution_surface: leader-inline`; no planning lane handoff files are required.
     - If the workload is standard and native subagents are available, dispatch `one-subagent` for exactly one validated isolated planning lane or `parallel-subagents` for two or more isolated planning lanes.
     - If the workload is standard, native subagents are unavailable, and no high-risk trigger is present, continue leader-inline with `capability_degraded: true`.
     - If the workload is heavy or safety-critical and native subagents are unavailable, or if heavy work cannot be packetized safely, record `workflow_status: blocked`, `dispatch_shape: subagent-blocked`, `execution_surface: none`, and a concrete `blocked_reason`; stop before synthesizing planning artifacts.
     - This adaptive blocker preserves scope. It may stop synthesis when execution
       cannot proceed safely, but it must not convert confirmed behavior into a
       smaller MVP, future phase, or agent-invented release slice.
   - Managed-team fallback is not part of adaptive plan/tasks dispatch.
   - Artifact-writing delegated planning lanes must be dispatched as a writable, execution-capable native subagent lane. If the runtime exposes role, sandbox, or permission choices, select a role/sandbox that can write the declared handoff file; a read-only lane is not a valid lane for `planning/handoffs/<lane-id>.json`.
   - Do not dispatch a read-only explorer, reviewer, or diagnostic lane to satisfy a delegated planning lane that must write a handoff. Such lanes may inform the leader only as supplemental evidence, and they do not satisfy `one-subagent` or `parallel-subagents` planning handoff requirements.
   - The delegated lane contract's allowed write scope must include the exact expected handoff path, `planning/handoffs/<lane-id>.json`, and must forbid writes outside that path unless the lane is explicitly assigned a generated artifact.
   - Before dispatching any delegated planning lane, persist a `planning_checkpoint` record to `planning/checkpoints.ndjson` with the lane id, dispatch shape, authoritative inputs, expected handoff path, and current workflow-state summary.
   - Each delegated planning lane must persist the lane's structured handoff to `planning/handoffs/<lane-id>.json` before the leader accepts the lane, waits at a join point, or synthesizes `plan.md`, `research.md`, or `plan-contract.json`.
   - Update `planning/evidence-index.json` after each accepted delegated lane handoff with lane id, handoff path, source artifacts inspected, decisions or constraints contributed, affected plan sections or generated artifacts, blocker status, and integration status.
   - Consume `planning/evidence-index.json` before final synthesis when delegated lanes were used: for every accepted handoff, mark the handoff as `integrated`, assigned to a refinement checkpoint, recorded in `user_confirmed_deferrals` with confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact, or `blocked`, and name the target `plan.md`, `research.md`, `quickstart.md`, `data-model.md`, `contracts/`, or `plan-contract.json` section that consumed it.
   - Do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only delegated lane results. If a delegated lane reports only prose, idle state, or an unwritten handoff, mark `subagent-blocked`, write the blocker to `workflow-state.md`, and stop or re-dispatch with a writable lane and a valid handoff path.
   - When resuming after compaction and delegated lanes were used, re-read `workflow-state.md`, `planning/checkpoints.ndjson`, `planning/evidence-index.json`, and all accepted `planning/handoffs/<lane-id>.json` files before continuing planning synthesis.
   - Required join points:
     - before final constitution and risk re-check
     - before writing the consolidated implementation plan
   - Record the chosen dispatch shape, blocked reason if any, selected lanes, and join points in the planning artifacts you generate.
   - In `plan-contract.json`, include references to accepted `planning/handoffs/<lane-id>.json` files that shaped each major plan decision, research conclusion, generated artifact, risk, guardrail, or escalation.
   - Do not mark planning complete while `planning/evidence-index.json` contains an accepted handoff without an explicit consuming artifact section, refinement checkpoint, `user_confirmed_deferrals` entry carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact, or blocker reason.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.

6. **Execute the plan workflow** using the IMPL_PLAN template:
   - Fill Technical Context (mark unknowns as `NEEDS CLARIFICATION`)
   - Add `Implementation Constitution` using architecture invariants, boundary ownership, forbidden implementation drift, required implementation references, and review focus from repository evidence
   - Add `Global Constraints` when constraints materially affect implementation or review.
   - Add `Task Interface Map` when task-level consumes/produces expectations are already known.
   - Add `Review-Risk Notes` for plan-approved risks, manual checks, UI/reference fidelity risks, or quality tradeoffs that reviewers must not reconstruct from chat memory.
   - Carry implementation-review artifact expectations into the plan when relevant: `implementation-review/task-briefs/`, `implementation-review/review-packages/`, `implementation-review/task-reviews/`, `implementation-review/ledger.json`, and `implementation-review/branch-review.md`.
    - `Implementation Constitution` MUST be added if any one of the following conditions is true:
      - the feature touches an established framework-owned boundary or adapter pattern
      - the touched area is a native bridge, plugin surface, protocol seam, generated API surface, or other contract-heavy boundary
      - generic implementation drift would violate an existing repository pattern
      - the repository already has canonical boundary files or examples that implementers must inspect before changing code safely
    - If none of those conditions is true, the plan MAY omit `Implementation Constitution`.
    - Add `Dispatch Compilation Hints` whenever subagent execution would be unsafe without an explicit boundary owner, packet references, validation gates, or task-level quality floor
   - Fill Constitution Check from the constitution
   - Add a `Scenario Profile Inputs` section using `workflow-state.md` when present, including `active_profile`, `required_sections`, `activated_gates`, `task_shaping_rules`, `required_evidence`, and `transition_policy`.
   - Add a `Profile-Driven Implementation Constraints` section when `workflow-state.md` records profile-specific implementation obligations.
   - If `active_profile` is `Reference-Implementation`, promote fidelity-preservation rules, reference-object constraints, allowed-drift limits, and required evidence into `Implementation Constitution` so implementers preserve the reference instead of treating it as background inspiration.
   - When `Reference Behavior Inventory` exists, copy each preserved or redesigned behavior into `Reference Fidelity Inputs` and ensure the consolidated plan names where that behavior is preserved, redesigned, covered by a refinement checkpoint, covered by a valid blocker, or deferred through a user-confirmed deferral carrying confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact.
   - Add an `Input Risks From Alignment` section using remaining risks from `alignment.md`
   - Add a `Feasibility Evidence From Deep Research` section when `deep-research.md` exists, preserving proven chains, research-agent findings, spike evidence, constraints, rejected options, and residual risks
   - Add a `Planning Handoff From Deep Research` section when `deep-research.md` contains `Planning Handoff`, and translate that handoff into implementation strategy, architecture implications, module boundaries, API/library choices, data flow notes, validation implications, and plan-level risks
   - Add a `Deep Research Traceability Matrix` section when `deep-research.md` contains Planning Handoff IDs:
     - columns: `Plan Decision`, `Handoff ID`, `Capability ID`, `Track ID`, `Evidence / Spike ID`, `Evidence Quality`, `Plan Action`
     - every architecture, module-boundary, API/library, data-flow, validation, or residual-risk decision derived from deep research must cite at least one `PH-###` item
     - mark any `PH-###` item not consumed by the plan as covered by a refinement checkpoint, recorded in `user_confirmed_deferrals` with confirmation source, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact, `not applicable`, or `requires user decision`
   - Copy locked planning decisions from `alignment.md`, `context.md`, `spec.md`, and `deep-research.md` into planning constraints, assumptions, or design notes so they are not silently dropped
   - Add each implementation-shaping `MP-*` item to `plan.md#Must-Preserve Carry-Forward`, `Locked Planning Decisions`, `Implementation Constitution`, or `Alignment Inputs`.
   - Preserve `MP-*` IDs when the plan consumes goals, non-goals, references, decisions, trade-offs, and stop-and-reopen conditions.
   - Copy implementation-chain constraints and synthesis decisions from `deep-research.md` into the implementation plan instead of rediscovering or weakening them
   - Promote framework and boundary rules from "technical background" into explicit implementation constraints rather than leaving them as implied context
   - Evaluate gates (ERROR if violations are unjustified)
   - Phase 0: generate `research.md` and resolve all `NEEDS CLARIFICATION`
   - Phase 1: generate `data-model.md`, `contracts/`, and `quickstart.md`
   - Phase 1: update agent context by running the agent script
   - Before finalizing the consolidated implementation plan, verify that no locked planning decision or implementation constitution rule has been silently omitted from the generated plan artifacts
   - Re-evaluate Constitution Check after design artifacts exist

7. **Stop and report**:
    - write `FEATURE_DIR/plan/plan-contract.json` or `FEATURE_DIR/plan-contract.json` as the machine-readable planning contract
      - Before writing semantic planning fields into `plan-contract.json`, create the fixed JSON envelope when it is missing. If `plan-contract.json` already exists, read, validate, and preserve it, then update semantic planning fields through the same contract shape.

        ```text
        {{specify-subcmd:artifact scaffold --kind plan-contract --out "<project-relative-feature-dir>/plan-contract.json" --vars "{}" --format json}}
        ```

      - `--out` must be project-relative. Prerequisite helpers may emit `FEATURE_DIR` as an absolute path; do not pass absolute `FEATURE_DIR` to `artifact scaffold`. Convert it to a project-relative output path first, then write semantic planning values through the returned JSON Pointer `fill_targets`.
      - Supported output locations are `<project-relative-feature-dir>/plan-contract.json` and `<project-relative-feature-dir>/plan/plan-contract.json`; use the existing location on reruns and scaffold only the missing target.
    - branch
    - plan path
    - alignment status
    - generated artifacts
    - planning evidence paths when delegated lanes were used: `planning/evidence-index.json`, `planning/checkpoints.ndjson`, and accepted `planning/handoffs/<lane-id>.json` files; otherwise report `delegated_planning_lanes: none`
    - execution_model: adaptive
    - execution_mode: light | standard | heavy
    - workflow_status: ready | blocked
    - dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked
    - execution_surface: leader-inline | native-subagents | none
    - capability_degraded: false | true
    - blocked_reason: required when blocked
    - workflow-state path
    - recommended follow-up quality check: `{{invoke:checklist}}` only when an explicit requirements-quality audit is still needed before decomposition
    - cognition follow-up: if artifact-only planning work introduces or sharpens future architecture boundaries, ownership splits, integration surfaces, workflow contracts, or verification routes that the current project cognition runtime does not yet encode, record that as an advisory in `workflow-state.md` or `plan.md`; do not mark project cognition dirty or require a refresh until actual source/runtime changes make the runtime truth out of date.
    - If this workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, follow the shared inline closeout contract:

{{spec-kit-include: ../../command-partials/common/inline-project-cognition-update.md}}
    - before final completion text, write or update `WORKFLOW_STATE_FILE` so it records:
      - `active_command: sp-plan`
      - `phase_mode: design-only`
      - current authoritative files
     - exit criteria for planning completion
     - the next action required before handoff
     - `next_command: /sp.tasks`
- [AGENT] before final completion text, if auto-capture did not preserve a reusable `workflow_gap` or `project_constraint`, use the manual `learning capture` helper surface.
  Required options: `--command`, `--type`, `--summary`, `--evidence`
   - leave one-off runs as `--decision none` with no reusable lesson; store reusable lessons as index/detail entries, and use `{{specify-subcmd:learning promote --target learning ...}}` only after explicit confirmation or proven recurrence
   - only ask for confirmation when a new learning is highest-signal, such as an explicit user default, clear cross-stage reuse, or repeated recurrence that should become shared project memory
   - Use the user's current language for the completion report and any explanatory text, while preserving literal command names, file paths, and fixed status values exactly as written.

8. **Check for extension hooks**: After reporting, check if `.specify/extensions.yml` exists in the project root.
   - If it exists, read it and look for entries under the `hooks.after_plan` key
{{spec-kit-include: ../../command-partials/common/extension-hooks-after-body.md}}

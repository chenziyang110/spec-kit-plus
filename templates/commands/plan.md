---
description: Use when the current specification package is ready for implementation planning and you need design artifacts before task breakdown or coding.
workflow_contract:
  when_to_use: The current spec package is ready for design work, but implementation should not start until explicit planning artifacts exist.
  primary_objective: Produce the planning artifact set that turns specification intent into an implementation-ready architecture and execution approach.
  primary_outputs: '`plan.md`, `research.md`, `quickstart.md`, `plan-contract.json`, and `workflow-state.md` under the active `FEATURE_DIR`; `data-model.md` and `contracts/` when the feature scope demands them; `planning/handoffs/<lane-id>.json`, `planning/evidence-index.json`, and `planning/checkpoints.ndjson` only when delegated planning lanes are used.'
  default_handoff: '/sp.tasks for decomposition; /sp.checklist remains optional for requirements-quality review, not a default handoff.'
handoffs:
  - label: Create Tasks
    agent: sp.tasks
    prompt: Break the plan into tasks
    send: true
  - label: Create Checklist
    agent: sp.checklist
    prompt: Create a checklist for the following domain...
scripts:
  sh: scripts/bash/setup-plan.sh --json
  ps: scripts/powershell/setup-plan.ps1 -Json
agent_scripts:
  sh: scripts/bash/update-agent-context.sh __AGENT__
  ps: scripts/powershell/update-agent-context.ps1 -AgentType __AGENT__
---

{{spec-kit-include: ../command-partials/plan/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

{{spec-kit-include: ../command-partials/common/semantic-work-contract.md}}

{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}

## Pre-Execution Checks

**Check for extension hooks (before planning)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_plan` key
{{spec-kit-include: ../command-partials/common/extension-hooks-body.md}}

**Maintain workflow quality without hook choreography**:
- Confirm project cognition freshness and valid workflow entry before deeper planning work begins.
- Keep `workflow-state.md` current as the durable source of truth for phase, allowed artifact writes, next action, and exit criteria.
- Verify the final `plan.md` and `workflow-state.md` outputs before handoff instead of relying on chat narration.
- Update durable state before compaction-risk transitions, large planning synthesis handoffs, or any stop where resume will depend on more than the visible conversation.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command plan --format json}}` when available so passive learning files exist and the current planning run sees relevant shared project memory.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader planning context.
- Open only learning detail docs linked from planning-relevant index entries, especially repeated workflow gaps or project constraints that would otherwise be rediscovered during planning.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- [AGENT] When planning friction exposes route changes, artifact rewrites, false starts, hidden dependencies, validation gaps, or reusable constraints, make sure `workflow-state.md` captures that durable context.
- [AGENT] Prefer `{{specify-subcmd:learning capture-auto --command plan --feature-dir "$FEATURE_DIR" --format json}}` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints.
- [AGENT] When the durable state does not capture the reusable lesson cleanly, update `.specify/memory/learnings/INDEX.md` and a linked detail document with the command, type, summary, and evidence.
- Treat this as passive shared memory, not as a separate user-visible planning command.

## Workflow Phase Lock

- [AGENT] Create or resume `WORKFLOW_STATE_FILE` before substantial planning analysis.
- Read `templates/workflow-state-template.md`.
- If `WORKFLOW_STATE_FILE` is missing, recreate it from the template and the current spec package instead of continuing from chat memory alone.
- Treat `WORKFLOW_STATE_FILE` as the stage-state source of truth on resume after compaction for the current command, allowed artifact writes, forbidden actions, authoritative files, next action, and exit criteria.
- Set or update the state for this run with at least:
  - `active_command: sp-plan`
  - `phase_mode: design-only`
  - `forbidden_actions: edit source code, edit tests, implement behavior, start execution from plan artifacts`
- Do not implement code, edit source files, edit tests, or treat planning as implicit permission to start execution.
- When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.
- If native hook policy redirects a prompt-entry phase jump, return to `WORKFLOW_STATE_FILE`; repeated or explicit phase jumps are blocked by shared workflow policy.

## Outline

1. **Setup**: Run `{SCRIPT}` from repo root and parse JSON for `FEATURE_SPEC`, `IMPL_PLAN`, `SPECS_DIR`, `BRANCH`, and `FEATURE_DIR`.
   - If `FEATURE_DIR` is not already explicit, prefer `{{specify-subcmd:lane resolve --command plan --ensure-worktree}}` before guessing from branch-only context.
   - When lane resolution returns a materialized lane worktree, continue planning from that isolated worktree context rather than assuming the leader workspace is the only source of truth for this feature lane.
   - Set `WORKFLOW_STATE_FILE` to `FEATURE_DIR/workflow-state.md`.
   - [AGENT] Create or resume `WORKFLOW_STATE_FILE` before substantial planning analysis.
   - Read `templates/workflow-state-template.md`.
   - If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid `next_action`, `exit_criteria`, and `next_command` details instead of relying on chat memory alone.
   - Persist at least these fields for the active pass:
     - `active_command: sp-plan`
     - `phase_mode: design-only`
     - `allowed_artifact_writes: plan.md, research.md, data-model.md, contracts/, quickstart.md, plan-contract.json, planning/handoffs/*.json, planning/evidence-index.json, planning/checkpoints.ndjson, workflow-state.md`
     - `forbidden_actions: edit source code, edit tests, implement behavior, start execution from plan artifacts`
     - `authoritative_files: spec.md, alignment.md, context.md, plan.md, research.md, plan-contract.json, planning/handoffs/*.json, planning/evidence-index.json`
   - When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.
   - If native hook policy redirects a prompt-entry phase jump, return to `WORKFLOW_STATE_FILE`; repeated or explicit phase jumps are blocked by shared workflow policy.

2. **Ensure project cognition runtime exists and record planning advisory state**:
   - Check whether `.specify/project-cognition/status.json` exists.
   - If it exists, use the project cognition freshness helper for the active script variant to assess freshness before trusting the current project cognition baseline.
   - [AGENT] If freshness is `missing`, continue with live repository evidence when workflow policy allows degraded advisory navigation; recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only as follow-up brownfield first-baseline maintenance unless the user explicitly requested cognition repair or planning truly cannot proceed without a usable baseline.
   - [AGENT] If freshness is `stale`, record a planning advisory, continue with minimal live reads from the query result, and do not require `{{invoke:map-update}}` during artifact-only `sp-plan` work.
   - [AGENT] If freshness is `support_drift`, record a planning advisory about support-surface drift and continue only with evidence-backed reads; do not reflexively route to `{{invoke:map-update}}`.
   - [AGENT] If freshness is `partial_refresh`, record a planning advisory that the refresh was incomplete, preserve `recommended_next_action`, and continue only when query results plus minimal live reads are sufficient for implementation planning.
   - [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. For artifact-only `sp-plan` work, record a planning advisory for any overlapping topics, review those topic files and minimal live reads, and continue without requiring `{{invoke:map-scan}}`/`{{invoke:map-build}}`.
   - Check whether `.specify/project-cognition/status.json` exists at the repository root.
   - [AGENT] If the project cognition runtime is missing, continue with live repository evidence when workflow policy allows degraded advisory navigation; recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only as follow-up brownfield first-baseline maintenance unless the user explicitly requested cognition repair or planning truly cannot proceed without a usable baseline.
   - Treat task-relevant coverage as insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
   - [AGENT] If task-relevant coverage is insufficient for the current planning request, record a planning advisory, continue with minimal live reads and targeted planning assumptions, and do not require a project cognition refresh during `sp-plan`.

3. **Load context**:
   - Read `FEATURE_SPEC`
   - Read `FEATURE_DIR/brainstorming/handoff-to-specify.json` when present and treat it as the authoritative pre-plan truth package.
   - If `brainstorming/handoff-to-specify.json` contains `must_preserve`, treat those `MP-*` items as planning obligations, not background notes.
   - If `planning_gate_status` is not `ready`, stop and route back to `{{invoke:specify}}` or to the user conflict decision named by the handoff.
   - If `quality_gate.user_confirmed` or equivalent user-confirmed `quality_gate.status` is missing, stop and route back to `{{invoke:specify}}` or `sp-discussion` according to the recorded blocker.
   - If `handoff_goal` is missing or vague, stop and route back to `sp-discussion` for handoff refresh.
   - If `context_boundary` is incomplete, stop before structural planning.
   - If `target_project_root` is required but missing, stop before structural planning.
   - If hard unknowns or open conflicts remain, stop and report the named blocker.
   - If `target_project_root` differs from `current_project_root`, plan from the target project context. Current project's cognition is not proof of target-project implementation facts.
   - For cross-project implementation, artifact-only planning may proceed only with explicit minimal live reads, target path confirmation, and recorded risk when target cognition is stale or missing.
   - Must not tell the user to run current-project `{{invoke:map-scan}} -> {{invoke:map-build}}` to fix target-project coverage.
   - If any `conflicts` item has `status: open`, stop and ask the user to resolve the conflict before planning.
   - Read `plan-contract.json` when present and treat route, intent, complexity as authoritative planning inputs.
   - Read `FEATURE_DIR/alignment.md`
   - Read `FEATURE_DIR/context.md`
   - Read `FEATURE_DIR/references.md` if present
   - Read `FEATURE_DIR/brainstorming/handoff-to-plan.json` if present; preserve route, intent, complexity, and handoff constraints as planning inputs.
   - Read `FEATURE_DIR/deep-research.md` if present
   - Read `FEATURE_DIR/workflow-state.md` if present. When it exists, treat it as semantically required profile-aware planning context, not optional resume trivia.
   - Read `.specify/memory/constitution.md`
   - Read `.specify/memory/project-rules.md` if present
   - Read `.specify/memory/learnings/INDEX.md` if present
   - Open only linked learning detail docs relevant to planning so repeated workflow gaps, implementation constraints, and user defaults are not rediscovered from scratch
   - [AGENT] Query project cognition with `{{specify-subcmd:project-cognition compass --intent plan --query="$ARGUMENTS" --format json}}`. Read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons, `verification_hints`, `followup_surfaces`, and `before_fix_claim`. Do not treat first-pass reads as the final edit scope. Use `project-cognition expand` only when the packet's coverage state or live evidence requires it. Use the advanced `lexicon -> semantic_intake -> query` flow only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, run `project-cognition query --query-plan "<query_plan_json>"` with `query_plan`, `semantic_intake`, `concept_decisions`, and facet coverage
   - If the topical coverage for the touched area is missing, stale, too broad, or task-relevant coverage is insufficient, record a planning advisory in the feature artifacts, inspect the minimum live files still needed to replace guesswork with evidence, and carry explicit assumptions or follow-up tasks instead of requiring a project cognition refresh during artifact-only planning work.
   - Read `templates/research-template.md`
   - Read `templates/workflow-state-template.md`
   - Load the copied IMPL_PLAN template

## Scenario Profile Inputs

- First-release `sp-plan` supports only these active profiles from `FEATURE_DIR/workflow-state.md`: `Standard Delivery` and `Reference-Implementation`.
- Read `FEATURE_DIR/workflow-state.md` if present and consume its scenario profile contract before planning synthesis.
- Treat `active_profile`, `required_sections`, `activated_gates`, `task_shaping_rules`, `required_evidence`, and `transition_policy` as planning inputs, not status-only metadata.
- Use the existing `active_profile` contract from `workflow-state.md`; do not perform a second informal task classification pass during planning.
- Preserve `transition_policy` as an obligation field that constrains downstream handoff; do not use it as a substitute for a supported `active_profile`.
- If the active profile is `Reference-Implementation`, add `Profile-Driven Implementation Constraints` to the generated plan and promote fidelity-preservation rules, reference-object constraints, and required evidence into `Implementation Constitution`.
- If the active profile is `Standard Delivery`, keep the standard planning artifact contract and only add profile-driven constraints when `workflow-state.md` explicitly records them.
- If `workflow-state.md` presents any other `active_profile` in first release, stop and tell the operator to repair or re-run upstream scenario profile routing state before planning; do not silently reinterpret unsupported profiles as a new planning mode.

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
- If the user did not confirm the deferral, plan the behavior, create a refinement or validation checkpoint that keeps it inside the current feature, or identify a valid hard blocker.
- Runtime capability limits are blockers only under the adaptive execution policy
  for heavy, safety-critical, or unpacketizable work. They are not permission to
  shrink scope or relabel confirmed behavior as a later version.

## Operational Consequence Design

Before `sp-tasks`, convert every triggered `CA-###` consequence obligation into concrete operational design.

- Preserve the upstream Affected Object Map, State-Behavior Matrix, Dependency Impact Table, Recovery And Validation Contract, and Coverage Gaps from `spec.md`, `alignment.md`, `context.md`, `references.md`, and machine-readable handoffs.
- For each implementation-shaping `CA-###` obligation, define the operational state machine, ordering, locking or lease behavior, idempotency, concurrency hazards, recovery path, observability, rollout or migration notes, and verification strategy.
- Name behavior for running-state objects explicitly: drain, cancel, force, wait, retry, resume, ignore late result, or preserve until a later lifecycle event.
- Map every dependency impact to plan sections, design artifacts, contracts, data model notes, quickstart validation, or explicit deferrals with stop-and-reopen conditions.
- Ensure `plan-contract.json` carries the same `CA-###` obligations, operational decisions, unresolved coverage gaps, and stop-and-reopen conditions as the Markdown plan.
- If any `CA-###` obligation cannot be designed safely in `sp-plan`, stop before `sp-tasks` and route back to `{{invoke:specify}}`, `{{invoke:clarify}}`, or `{{invoke:deep-research}}` with the missing decision named.

## Capability Preservation Planning

Before command, route, or contract design is locked, preserve every operation-shaped capability from `spec.md`, `alignment.md`, `context.md`, and `brainstorming/handoff-to-specify.json`.

- Treat new/create/scaffold/authoring/template-creation signals as buildable capability operations when they were preserved or in scope upstream.
- Command-surface minimization must not delete capability. If the plan chooses a small public command surface, perform entry-point remapping: map the capability to a TUI route, core API, public CLI command, private helper invoked by the TUI, or an explicitly user-confirmed deferral.
- For every remapped capability, name the selected entry point, owning module or route, design artifact, quickstart or test proof, and any user confirmation for narrowing.
- If the plan removes or defers an upstream operation-shaped capability because of a command-surface constraint, stop and route back to `{{invoke:specify}}` or `{{invoke:clarify}}` unless the user already confirmed that narrowing.
- Record create/scaffold operation mappings in `plan.md#Capability Preservation Plan` and in `plan-contract.json` so `sp-tasks` cannot convert them into template-only or documentation-only work.
- A static template directory, manual copy docs, or authoring guide is support material; it is not an implementation of a confirmed scaffold operation unless the user-confirmed scope says manual copy is the intended entry point.

{{spec-kit-include: ../command-partials/common/planning-context-loading-gradient.md}}

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
   - Consume `planning/evidence-index.json` before final synthesis when delegated lanes were used: for every accepted handoff, mark the handoff as `integrated`, `deferred`, or `blocked`, and name the target `plan.md`, `research.md`, `quickstart.md`, `data-model.md`, `contracts/`, or `plan-contract.json` section that consumed it.
   - Do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only delegated lane results. If a delegated lane reports only prose, idle state, or an unwritten handoff, mark `subagent-blocked`, write the blocker to `workflow-state.md`, and stop or re-dispatch with a writable lane and a valid handoff path.
   - When resuming after compaction and delegated lanes were used, re-read `workflow-state.md`, `planning/checkpoints.ndjson`, `planning/evidence-index.json`, and all accepted `planning/handoffs/<lane-id>.json` files before continuing planning synthesis.
   - Required join points:
     - before final constitution and risk re-check
     - before writing the consolidated implementation plan
   - Record the chosen dispatch shape, blocked reason if any, selected lanes, and join points in the planning artifacts you generate.
   - In `plan-contract.json`, include references to accepted `planning/handoffs/<lane-id>.json` files that shaped each major plan decision, research conclusion, generated artifact, risk, guardrail, or escalation.
   - Do not mark planning complete while `planning/evidence-index.json` contains an accepted handoff without an explicit consuming artifact section, deferral, or blocker reason.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.

6. **Execute the plan workflow** using the IMPL_PLAN template:
   - Fill Technical Context (mark unknowns as `NEEDS CLARIFICATION`)
   - Add `Implementation Constitution` using architecture invariants, boundary ownership, forbidden implementation drift, required implementation references, and review focus from repository evidence
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
   - When `Reference Behavior Inventory` exists, copy each preserved or redesigned behavior into `Reference Fidelity Inputs` and ensure the consolidated plan names where that behavior is preserved, redesigned, or explicitly deferred.
   - Add an `Input Risks From Alignment` section using remaining risks from `alignment.md`
   - Add a `Feasibility Evidence From Deep Research` section when `deep-research.md` exists, preserving proven chains, research-agent findings, spike evidence, constraints, rejected options, and residual risks
   - Add a `Planning Handoff From Deep Research` section when `deep-research.md` contains `Planning Handoff`, and translate that handoff into implementation strategy, architecture implications, module boundaries, API/library choices, data flow notes, validation implications, and plan-level risks
   - Add a `Deep Research Traceability Matrix` section when `deep-research.md` contains Planning Handoff IDs:
     - columns: `Plan Decision`, `Handoff ID`, `Capability ID`, `Track ID`, `Evidence / Spike ID`, `Evidence Quality`, `Plan Action`
     - every architecture, module-boundary, API/library, data-flow, validation, or residual-risk decision derived from deep research must cite at least one `PH-###` item
     - mark any `PH-###` item not consumed by the plan as `deferred`, `not applicable`, or `requires user decision`
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

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}
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
{{spec-kit-include: ../command-partials/common/extension-hooks-after-body.md}}

## Phases

### Phase 0: Outline & Research

1. Extract unknowns from Technical Context:
   - For each `NEEDS CLARIFICATION` -> research task
   - For each dependency -> best-practices task
   - For each integration -> patterns task
   - For each high-risk architectural choice -> stack/pattern/pitfall task
   - For each external tool, runtime, or service dependency -> availability and fallback task

2. Generate and dispatch research tasks.
   - Prefer official documentation, standards, and primary sources for factual claims.
   - Treat model memory as provisional unless confirmed by a primary source or direct repository evidence.
   - Research must reduce planning ambiguity, not accumulate background reading.

3. Consolidate findings in `research.md` using:
   - Decision
   - Rationale
   - Alternatives considered
   - Source confidence (`verified`, `cited`, or `assumed`) for each consequential claim
   - Standard stack recommendations where the phase depends on specific libraries, tools, or frameworks
   - `Don't hand-roll` guidance for problems that should use established libraries or platform capabilities
   - Common pitfalls, failure modes, and anti-patterns the planner should explicitly avoid
   - Assumptions log for anything still not verified in this session
   - Validation notes describing how the researched choice should be proven during implementation or verification
   - Environment or dependency notes when the phase depends on tools, services, runtimes, or external infrastructure that may not be present

4. Research quality bar:
   - Do not present unverified claims as settled facts.
   - If a claim could materially change plan structure, security posture, compatibility, or verification scope, it must either be verified, explicitly cited, or moved into the assumptions log.
   - Prefer prescriptive recommendations over broad option dumps once the evidence is strong enough to guide planning.
   - The finished `research.md` should answer: "What does the planner need to know to produce a high-quality implementation plan without rediscovering the domain?"
   - Use `templates/research-template.md` as the default structure for `research.md`; remove sections that are not relevant rather than leaving placeholder text behind.

**Output**: `research.md` with all `NEEDS CLARIFICATION` resolved

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

1. **Conditional: `data-model.md`** — Required only when the spec introduces new entities, data structures, state transitions, or persistence concerns. For pure logic changes, bug fixes, or config-only work, skip and note the reason in plan.md.
2. **Conditional: `contracts/`** — Required only when the feature defines new external interfaces, APIs, cross-service contracts, or protocol boundaries. For internal-only changes, skip and note the reason.
3. **`quickstart.md`** — Generate for every feature. Keep it focused on a representative end-to-end validation scenario that proves the confirmed product scope works through the relevant integration boundary.
4. Run `{AGENT_SCRIPT}` to update agent-specific context.

**Output**: `research.md` (required), `quickstart.md` (required), plus `data-model.md` and `contracts/*` when the feature scope demands them. Note skipped conditional artifacts in plan.md.

## Input Risks From Alignment

- [Risk 1 from alignment.md, or "None"]
- [Risk 2 from alignment.md, or omit if none]

## Key Rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications
- Match the user's current language for all user-visible output unless a literal command name, file path, or fixed status value must remain unchanged.

---
description: Use when the current specification package is ready for implementation planning and you need design artifacts before task breakdown or coding.
workflow_contract:
  when_to_use: The current spec package is ready for design work, but implementation should not start until explicit planning artifacts exist.
  primary_objective: Produce the planning artifact set that turns specification intent into an implementation-ready architecture and execution approach.
  primary_outputs: '`plan.md`, `research.md`, `quickstart.md`, and `workflow-state.md` under the active `FEATURE_DIR`, plus `data-model.md` and `contracts/` when the feature scope demands them.'
  default_handoff: '/sp.tasks for decomposition, optionally /sp.checklist for quality checks on the resulting plan package.'
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

{{spec-kit-include: ../command-partials/common/subagent-execution.md}}


## Pre-Execution Checks

**Check for extension hooks (before planning)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_plan` key
{{spec-kit-include: ../command-partials/common/extension-hooks-body.md}}

**Run first-party workflow quality hooks once `FEATURE_DIR` is known**:
- Use `{{specify-subcmd:hook preflight --command plan --feature-dir "$FEATURE_DIR"}}` before deeper planning execution so stale brownfield routing or invalid workflow entry is caught by the shared product guardrail layer.
- After `WORKFLOW_STATE_FILE` is created or resumed, use `{{specify-subcmd:hook validate-state --command plan --feature-dir "$FEATURE_DIR"}}` so the shared validator confirms `workflow-state.md` matches the `sp-plan` contract.
- Before final handoff, use `{{specify-subcmd:hook validate-artifacts --command plan --feature-dir "$FEATURE_DIR"}}` so the minimum plan artifact set is checked by the shared hook surface.
- Before compaction-risk transitions or after large planning artifact synthesis, use `{{specify-subcmd:hook checkpoint --command plan --feature-dir "$FEATURE_DIR"}}` to emit a resume-safe checkpoint payload from `workflow-state.md`.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command plan --format json}}` when available so passive learning files exist, the current planning run sees relevant shared project memory, and repeated candidates, including repeated high-signal candidates, can be auto-promoted into shared learnings at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/project-learnings.md` in that order before broader planning context.
- Review `.planning/learnings/candidates.md` only when it still contains planning-relevant candidate learnings after the passive start step, especially repeated workflow gaps or project constraints that would otherwise be rediscovered during planning.
- [AGENT] When planning friction appears, use the `signal-learning` helper surface with route-change, artifact-rewrite, user-correction, false-start, or hidden-dependency counts.
  Command shape: `{{specify-subcmd:hook signal-learning --command plan --route-changes <n> --artifact-rewrites <n> --user-corrections <n>}}`
- [AGENT] Before final completion or blocked reporting, use the `review-learning` helper surface; use `--decision none` only when no reusable `workflow_gap`, `routing_mistake`, `state_surface_gap`, `decision_debt`, or `project_constraint` exists.
  Command shape: `{{specify-subcmd:hook review-learning --command plan --terminal-status <resolved|blocked> --decision <none|captured|deferred> --rationale "<why>"}}`
- [AGENT] Prefer `{{specify-subcmd:learning capture-auto --command plan --feature-dir "$FEATURE_DIR" --format json}}` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints.
- [AGENT] When the durable state does not capture the reusable lesson cleanly, use the manual `capture-learning` hook surface.
  Required options: `--command`, `--type`, `--summary`, `--evidence`
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
     - `allowed_artifact_writes: plan.md, research.md, data-model.md, contracts/, quickstart.md, workflow-state.md`
     - `forbidden_actions: edit source code, edit tests, implement behavior, start execution from plan artifacts`
     - `authoritative_files: spec.md, alignment.md, context.md, plan.md, research.md`
   - When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.
   - If native hook policy redirects a prompt-entry phase jump, return to `WORKFLOW_STATE_FILE`; repeated or explicit phase jumps are blocked by shared workflow policy.

2. **Ensure repository navigation system exists**:
   - Check whether `.specify/project-map/index/status.json` exists.
   - If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
   - [AGENT] If freshness is `missing` or `stale`, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
   - [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If `must_refresh_topics` is non-empty for the current planning request, run `/sp-map-scan` followed by `/sp-map-build` before continuing. If only `review_topics` are non-empty, review those topic files before trusting the current map for planning.
   - Check whether `PROJECT-HANDBOOK.md` exists at the repository root.
   - Check whether `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/STRUCTURE.md`, `.specify/project-map/root/CONVENTIONS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md` exist.
   - [AGENT] If the navigation system is missing, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
   - Treat task-relevant coverage as insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
   - [AGENT] If task-relevant coverage is insufficient for the current planning request, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.

3. **Load context**:
   - Read `FEATURE_SPEC`
   - Read `FEATURE_DIR/alignment.md`
   - Read `FEATURE_DIR/context.md`
   - Read `FEATURE_DIR/references.md` if present
   - Read `FEATURE_DIR/deep-research.md` if present
   - Read `FEATURE_DIR/workflow-state.md` if present. When it exists, treat it as semantically required profile-aware planning context, not optional resume trivia.
   - Read `.specify/testing/TESTING_CONTRACT.md` if present
   - Read `.specify/testing/TESTING_PLAYBOOK.md` if present
   - Read `.specify/testing/COVERAGE_BASELINE.json` if present
   - Read `.specify/memory/constitution.md`
   - Read `.specify/memory/project-rules.md` if present
   - Read `.specify/memory/project-learnings.md` if present
   - If `.planning/learnings/candidates.md` exists, inspect only the entries relevant to planning so repeated workflow gaps, implementation constraints, and user defaults are not rediscovered from scratch
   - [AGENT] Read `PROJECT-HANDBOOK.md`
   - Read the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`, `.specify/project-map/root/STRUCTURE.md`, `.specify/project-map/root/CONVENTIONS.md`, `.specify/project-map/root/INTEGRATIONS.md`, `.specify/project-map/root/WORKFLOWS.md`, `.specify/project-map/root/TESTING.md`, and `.specify/project-map/root/OPERATIONS.md`.
   - If the topical coverage for the touched area is missing, stale, too broad, or task-relevant coverage is insufficient, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then inspect the minimum live files still needed to replace guesswork with evidence.
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

{{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}

**Project-map hard gate:** you must pass an atlas gate before planning
analysis, architecture synthesis, or implementation-shaping code reads begin.

**This command tier: heavy.** Pass the atlas gate by reading
`PROJECT-HANDBOOK.md`, `atlas.entry`, `atlas.index.status`,
`atlas.index.atlas`, `atlas.index.modules`, `atlas.index.relations`, the
relevant root topic documents, and the relevant module overview documents
before broader planning reads continue. Freshness is enforced as a blocking
gate.

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
   - Treat `context.md` as the primary implementation-context artifact that captures downstream planning decisions explicitly
   - Treat `workflow-state.md` scenario profile fields as active planning inputs. The plan consumes the existing supported profile contract persisted by upstream routing.
   - Do not perform a second informal task classification pass; `sp-plan` consumes `active_profile`, `required_sections`, `activated_gates`, `task_shaping_rules`, `required_evidence`, and `transition_policy` from `workflow-state.md`.
   - Do not introduce a separate clarification command as the normal next step for routine planning readiness
   - [AGENT] Before research or design fan-out begins, assess workload shape and the current agent capability snapshot, then apply the shared policy contract: `choose_subagent_dispatch(command_name="plan", snapshot, workload_shape)`
   - Persist the decision fields exactly: `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, `execution_surface: native-subagents`.
   - Decision order is fixed:
     - One safe validated lane -> `one-subagent` on `native-subagents` when available.
     - Two or more safe isolated lanes -> `parallel-subagents` on `native-subagents` when available.     - No safe lane, overlapping writes, missing contract, or unavailable delegation -> `subagent-blocked` with a recorded reason.
   - If collaboration is justified, keep `plan` lanes limited to:
     - research
     - data model
     - contracts
     - quickstart and validation scenarios
   - Required join points:
     - before final constitution and risk re-check
     - before writing the consolidated implementation plan
   - Record the chosen strategy, reason, any blocked dispatch or escalation decision, selected lanes, and join points in the planning artifacts you generate.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.

6. **Execute the plan workflow** using the IMPL_PLAN template:
   - Fill Technical Context (mark unknowns as `NEEDS CLARIFICATION`)
   - Add `Implementation Constitution` using architecture invariants, boundary ownership, forbidden implementation drift, required implementation references, and review focus from repository evidence
    - Add `Implementation Constitution` whenever one or more of these heuristics is true:
      - the feature touches an established framework-owned boundary or adapter pattern
      - the touched area is a native bridge, plugin surface, protocol seam, generated API surface, or other contract-heavy boundary
      - a generic implementation instinct would likely drift away from the repository's existing pattern
      - the repository already has canonical boundary files or examples that implementers must inspect before changing code safely
    - Add `Dispatch Compilation Hints` whenever subagent execution would be unsafe without an explicit boundary owner, packet references, validation gates, or task-level quality floor
   - Fill Constitution Check from the constitution
   - Add a `Scenario Profile Inputs` section using `workflow-state.md` when present, including `active_profile`, `required_sections`, `activated_gates`, `task_shaping_rules`, `required_evidence`, and `transition_policy`.
   - Add a `Profile-Driven Implementation Constraints` section when `workflow-state.md` records profile-specific implementation obligations.
   - If `active_profile` is `Reference-Implementation`, promote fidelity-preservation rules, reference-object constraints, allowed-drift limits, and required evidence into `Implementation Constitution` so implementers preserve the reference instead of treating it as background inspiration.
   - Add an `Input Risks From Alignment` section using remaining risks from `alignment.md`
   - Add a `Feasibility Evidence From Deep Research` section when `deep-research.md` exists, preserving proven chains, research-agent findings, spike evidence, constraints, rejected options, and residual risks
   - Add a `Planning Handoff From Deep Research` section when `deep-research.md` contains `Planning Handoff`, and translate that handoff into implementation strategy, architecture implications, module boundaries, API/library choices, data flow notes, validation implications, and plan-level risks
   - Add a `Deep Research Traceability Matrix` section when `deep-research.md` contains Planning Handoff IDs:
     - columns: `Plan Decision`, `Handoff ID`, `Capability ID`, `Track ID`, `Evidence / Spike ID`, `Evidence Quality`, `Plan Action`
     - every architecture, module-boundary, API/library, data-flow, validation, or residual-risk decision derived from deep research must cite at least one `PH-###` item
     - mark any `PH-###` item not consumed by the plan as `deferred`, `not applicable`, or `requires user decision`
   - Copy locked planning decisions from `alignment.md`, `context.md`, `spec.md`, and `deep-research.md` into planning constraints, assumptions, or design notes so they are not silently dropped
   - Copy implementation-chain constraints and synthesis decisions from `deep-research.md` into the implementation plan instead of rediscovering or weakening them
   - If `.specify/testing/TESTING_CONTRACT.md` exists, copy the project-level testing rules into the implementation plan instead of treating tests as optional follow-up work. Preserve the stronger brownfield testing inputs carried from `sp-specify`: module priority waves, covered-module policy, `small / medium / large` policy, scenario matrix expectations, local integration seam expectations, allowed testability refactors, coverage goals, CI gate expectations, and command-tier expectations for `fast smoke`, `focused`, and `full`
   - If `.specify/testing/TESTING_PLAYBOOK.md` exists, preserve the canonical test, targeted-test, and coverage commands inside the generated plan artifacts
   - Promote framework and boundary rules from "technical background" into explicit implementation constraints rather than leaving them as implied context
   - Evaluate gates (ERROR if violations are unjustified)
   - Phase 0: generate `research.md` and resolve all `NEEDS CLARIFICATION`
   - Phase 1: generate `data-model.md`, `contracts/`, and `quickstart.md`
   - Phase 1: update agent context by running the agent script
   - Before finalizing the consolidated implementation plan, verify that no locked planning decision or implementation constitution rule has been silently omitted from the generated plan artifacts
   - Re-evaluate Constitution Check after design artifacts exist

7. **Stop and report**:
    - branch
    - plan path
    - alignment status
    - generated artifacts
    - workflow-state path
    - recommended follow-up quality check: `{{invoke:checklist}}` for a requirements/plan package audit before moving on to decomposition
    - if the planning pass introduces or sharpens new architecture boundaries, ownership splits, integration surfaces, workflow contracts, or verification routes that the current handbook/project-map does not yet encode, treat git-baseline freshness in `.specify/project-map/index/status.json` as the truth source; if a full refresh can be completed now, run `/sp-map-scan` followed by `/sp-map-build` and `{{specify-subcmd:hook complete-refresh}}` as the successful-refresh finalizer, otherwise use `{{specify-subcmd:hook mark-dirty --reason "<reason>"}}` as the manual override/fallback before later brownfield implementation proceeds
    - before final completion text, write or update `WORKFLOW_STATE_FILE` so it records:
      - `active_command: sp-plan`
      - `phase_mode: design-only`
      - current authoritative files
     - exit criteria for planning completion
     - the next action required before handoff
     - `next_command: /sp.tasks`
- [AGENT] before final completion text, if auto-capture did not preserve a reusable `workflow_gap` or `project_constraint`, use the manual `learning capture` helper surface.
  Required options: `--command`, `--type`, `--summary`, `--evidence`
   - keep lower-signal items as candidates and use `{{specify-subcmd:learning promote --target learning ...}}` only after explicit confirmation or proven recurrence
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
3. **`quickstart.md`** — Generate for every feature. Keep it focused on the smallest integration scenario that validates the feature works end-to-end.
4. Run `{AGENT_SCRIPT}` to update agent-specific context.

**Output**: `research.md` (required), `quickstart.md` (required), plus `data-model.md` and `contracts/*` when the feature scope demands them. Note skipped conditional artifacts in plan.md.

## Input Risks From Alignment

- [Risk 1 from alignment.md, or "None"]
- [Risk 2 from alignment.md, or omit if none]

## Key Rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications
- Match the user's current language for all user-visible output unless a literal command name, file path, or fixed status value must remain unchanged.

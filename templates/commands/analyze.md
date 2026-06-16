---
description: Use when tasks.md exists and you need a non-destructive cross-artifact consistency and boundary-guardrail analysis before or during execution.
workflow_contract:
  when_to_use: '`tasks.md` is available and you need a read-only analysis pass before, during, or after implementation revalidation.'
  primary_objective: 'Identify inconsistencies, ambiguities, drift, and boundary-guardrail gaps across `spec.md`, `context.md`, `plan.md`, and `tasks.md`.'
  primary_outputs: A structured analysis report plus workflow-state gate updates. This command does not edit `spec.md`, `context.md`, `plan.md`, or `tasks.md`.
  default_handoff: 'Route into /sp.clarify, /sp.deep-research, /sp.plan, /sp.tasks, /sp.debug, or /sp.implement based on the findings; if analysis runs after implementation has started or finished, reopen the highest invalid stage and regenerate downstream artifacts before continuing.'
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

{{spec-kit-include: ../command-partials/analyze/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


## Goal

Identify inconsistencies, duplications, ambiguities, and underspecified items across the core planning artifacts (`spec.md`, `context.md`, `plan.md`, `tasks.md`) before implementation, during execution, or after implementation when revalidation is needed. This command MUST run only after the canonical `/sp.tasks` workflow has successfully produced a complete `tasks.md`.

## Operating Constraints

**READ-ONLY FOR PLANNING ARTIFACTS**: Do **not** modify `spec.md`, `context.md`, `plan.md`, or `tasks.md`. Output a structured analysis report. This command may update `workflow-state.md` to record the cleared or blocked gate result. Offer an optional remediation plan (user must explicitly approve before any follow-up editing commands would be invoked manually).

Analyze must not switch branches, implicitly check out a "correct" feature branch, or mutate git state in order to determine scope. If the active feature cannot be identified safely through explicit `FEATURE_DIR` binding or lane resolution, fail closed and tell the user how to repair routing.

**Closed-loop requirement**: Do not present findings as a dead-end audit. The report MUST tell the user which workflow stage to reopen, which downstream artifacts must be regenerated, and whether implementation may continue immediately or must pause until upstream remediation is complete.
Preserve canonical `/sp.implement` only in workflow-state fields.
When recommending manual implementation resumption to the user, tell them to run `{{invoke:implement}}`.

**Convergence requirement**: Complete the full detection matrix before selecting the single `Recommended Next Command`. Do not stop analysis after finding enough evidence to route backward. The report must include the complete blocker bundle for the current artifact set, grouped by invalid stage, so downstream remediation does not discover same-artifact blockers one cycle at a time.

**Constitution Authority**: The project constitution (`.specify/memory/constitution.md`) is **non-negotiable** within this analysis scope. Constitution conflicts are automatically CRITICAL and require adjustment of the spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring of the principle. If a principle itself needs to change, that must occur in a separate, explicit constitution update outside `/sp.analyze`.

## Workflow Phase Lock

- [AGENT] Create or resume `WORKFLOW_STATE_FILE` before substantial analysis work begins.
- Read `templates/workflow-state-template.md`.
- If `WORKFLOW_STATE_FILE` is missing, recreate it from the template and the current artifact package instead of relying on chat memory alone.
- Treat `WORKFLOW_STATE_FILE` as the gate-state source of truth for whether implementation may proceed.
- Set or update the state for this run with at least:
  - `active_command: sp-analyze`
  - `phase_mode: analysis-only`
  - `forbidden_actions: edit source code, edit tests, edit planning artifacts, start implementation before the gate is cleared`
- When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before continuing.

## Analyze Gate Convergence Contract

### Stable Finding Identity

- Use stable finding IDs that survive revalidation. Category-only IDs such as `BG2` are too coarse, and run-local sequence numbers are not stable by themselves.
- Use a fingerprint-first ID contract:
  - Build a canonical finding fingerprint from category, invalid stage, artifact, requirement or section key when available, normalized summary, and remediation requirement.
  - Before assigning IDs, load the previous `Analyze Gate` ledger from `workflow-state.md` when it exists.
  - Match current findings to previous open or recently cleared findings by fingerprint first, and reuse the prior ID when the fingerprint matches.
  - Allocate a new ID only for a genuinely new fingerprint.
  - For new fingerprints, allocate the next unused category sequence after sorting by category, artifact, section key, and normalized summary.

### Revalidation Attribution

- When revalidating after a blocked analyze gate, any new blocker must include one attribution:
  - `missed_by_previous_analyze`: detectable in the prior artifact set and should have been included in the earlier blocker bundle.
  - `introduced_by_remediation`: remediation changed `tasks.md` or downstream state in a way that introduced the issue.
  - `upstream_artifact_changed`: an authoritative input changed since the prior analyze pass.
  - `detector_scope_changed`: the workflow template or analysis instructions changed the detector scope between runs.
- If there is no evidence for `introduced_by_remediation`, `upstream_artifact_changed`, or `detector_scope_changed`, use `missed_by_previous_analyze`.
- Persist attribution per new blocking finding in the `Analyze Gate` `blocker_bundle`; report-body attribution without durable blocker-row attribution is not sufficient for revalidation.
- No more than one task-layer remediation cycle is expected. If revalidation finds new task-layer blockers that were detectable before remediation, classify them as a previous analyze miss or a tasks self-audit failure. Do not treat repeated task/analyze loops as normal workflow.

## Workflow Quality Requirements

- Confirm project cognition freshness and valid workflow entry before deeper analysis begins.
- Keep `workflow-state.md` current as the durable gate-state source of truth for whether implementation may proceed, which stage must reopen, and what evidence supports the decision.
- Verify the analysis report, cleared or blocked gate result, and any durable artifact outcomes before final reporting instead of relying on chat narration.
- Update durable analysis state before compaction-risk transitions, large findings synthesis, remediation handoffs, or any stop where resume will depend on more than the visible conversation.
- Run `{{specify-subcmd:learning start --command analyze --format json}}` when available so passive learning files exist and the current analysis sees relevant shared project memory.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader analysis context.
- Open only learning detail docs linked from analysis-relevant index entries.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- When analysis friction exposes repeated artifact rewrites, route changes, false starts, hidden dependencies, validation gaps, or reusable constraints, make sure `workflow-state.md` captures that durable context.
- Prefer `{{specify-subcmd:learning capture-auto --command analyze --feature-dir "$FEATURE_DIR" --format json}}` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints.
- When durable state does not capture the reusable lesson cleanly, update `.specify/memory/learnings/INDEX.md` and a linked detail document with the command, type, summary, and evidence.

## Execution Steps

### 1. Initialize Analysis Context

Run `{SCRIPT}` once from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS. Derive absolute paths:

- If `FEATURE_DIR` is not already explicit, prefer `{{specify-subcmd:lane resolve --command analyze --ensure-worktree}}` before guessing from branch-only context.
- When lane resolution returns a materialized lane worktree, continue analysis from that isolated worktree context so downstream gate decisions stay attached to the same lane boundary.

- SPEC = FEATURE_DIR/spec.md
- CONTEXT = FEATURE_DIR/context.md
- PLAN = FEATURE_DIR/plan.md
- TASKS = FEATURE_DIR/tasks.md
- PLANNING_EVIDENCE_INDEX = FEATURE_DIR/planning/evidence-index.json when present
- TASK_GENERATION_EVIDENCE_INDEX = FEATURE_DIR/task-generation/evidence-index.json when present

Abort with an error message if any required file is missing (instruct the user to run missing prerequisite command).
For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

- Set `WORKFLOW_STATE_FILE` to `FEATURE_DIR/workflow-state.md`.
- [AGENT] Create or resume `WORKFLOW_STATE_FILE` before substantial analysis work begins.
- Read `templates/workflow-state-template.md`.
- If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid authoritative file references and gate notes instead of relying on chat memory alone.

### 2. Ensure project cognition runtime exists

- Choose the cognition intent before querying: use `plan` when analyzing planning-only artifacts or upstream spec/plan drift, use `implement` when analyzing task execution, remediation, or code-change blockers, and preserve the originating workflow intent when this command is reviewing another `sp-*` workflow's output.
- Query project cognition with `{{specify-subcmd:project-cognition compass --intent plan --query="$ARGUMENTS" --format json}}` or `{{specify-subcmd:project-cognition compass --intent implement --query="$ARGUMENTS" --format json}}` according to that chosen intent; preserve the advanced `lexicon -> semantic_intake -> query` flow for explicit concept decisions; write `semantic_intake` from the alias catalog, select candidates by facet coverage, write `concept_decisions` with `covered_facets`, `missing_facets`, and `match_sources`, carry `lexicon_generation_id`, then generate a `query_plan` containing `semantic_intake`, `selected_concepts`, `rejected_concepts`, `concept_decisions`, `lexicon_generation_id`, `expanded_queries`, `repository_search_terms`, and justified `paths`, then run `{{specify-subcmd:project-cognition query --intent <chosen-intent> --query-plan "<query_plan_json>" --format json}}`. Agent-owned semantic normalization is mandatory: raw lexicon ranking and `agent_normalization` are only bootstrap signals, not route decisions. If `agent_normalization.required=true`, every raw candidate is `score=0`, or the prompt is localized, mixed-language, CJK, colloquial, or symptom-first, extract embedded project terms and write `semantic_intake` from the alias catalog before selecting or rejecting concepts. If `agent_normalization` is omitted, treat it as `required=false`; CJK or mixed CJK/ASCII input still requires agent normalization even when positive raw lexical matches exist because embedded project tokens do not translate the surrounding user language. The agent still owns translation; `agent_normalization` is advisory guidance, not a route decision. This includes mixed-language or CJK text. (raw lexicon ranking is only a bootstrap; action: write_semantic_intake_from_alias_catalog) Derive project-language search terms from the alias catalog before source search. Do not search only the raw user words; include component names, state names, file names, command names, UI labels, and route names from candidates, aliases, matched_terms, colloquial_matches, returned paths, `normalized_query`, and `expanded_queries`. Use these project-language search terms before broad repository search. For implementation or remediation analysis, the concrete query command is `{{specify-subcmd:project-cognition query --intent implement --query-plan "<query_plan_json>" --format json}}`.
- If readiness is `needs_rebuild`, stop and tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; this is reserved for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid.
- If compass coverage is too weak for the touched area, use live evidence and record whether a follow-up `{{invoke:map-update}}` is useful for external map maintenance.
- Use map-update for ordinary existing-baseline gaps. Use map-scan -> map-build only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid.
- If readiness is `review`, inspect only the returned `minimal_live_reads` before trusting the runtime for analysis.
- Carry selected/rejected concepts, `selection_reason`, `route_pack`, and
  `minimal_live_reads` into the analysis report and `workflow-state.md`
  blocker bundle whenever cognition evidence affects routing or blocker
  severity.
- Treat task-relevant coverage as insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
- If task-relevant coverage is insufficient for the current analysis request, inspect the returned targeted live evidence; refresh through `{{invoke:map-update}}` with changed paths or affected surfaces, and rebuild through `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only for the explicit rebuild conditions above.

### 3. Load Artifacts (Progressive Disclosure)

Load only the minimal necessary context from each artifact:

**From project cognition runtime:**

- Consume the `project-cognition query` bundle.
- Preserve `selected_concepts`, `rejected_concepts`, `selection_reason`,
  `route_pack`, and `minimal_live_reads` as blocker evidence inputs.
- Preserve cognition-backed blocker evidence when classifying whether issues
  belong to `plan`, `clarify`, `deep-research`, or task-layer remediation. The
  analysis report and `workflow-state.md` blocker bundle must keep the selected
  capability, boundary fact, ambiguity, or verification evidence that justified
  the route.
- Inspect only returned `minimal_live_reads` when the bundle does not fully cover ownership, propagation, or verification routes.
- If topical coverage is missing, stale, too broad, or task-relevant coverage is insufficient, use `/sp-map-update` with changed paths or affected surfaces; rebuild through `/sp-map-scan` followed by `/sp-map-build` only for the explicit rebuild conditions above, then inspect the minimum live files still needed to replace guesswork with evidence

**From spec.md:**

- Overview/Context
- Functional Requirements
- Success Criteria (measurable outcomes — e.g., performance, security, availability, user success, business impact)
- User Stories
- Edge Cases (if present)

**From context.md:**

- Locked Decisions
- Claude Discretion
- Canonical References
- Existing Code Insights
- Specific User Signals
- Outstanding Questions

**From plan.md:**

- Architecture/stack choices
- Locked Planning Decisions
- Implementation Constitution
- Alignment Inputs
- Data Model references
- Phases
- Technical constraints

**From tasks.md:**

- Task IDs
- Descriptions
- Phase grouping
- Parallel markers [P]
- Referenced file paths

**From planning evidence when present:**

- Read `planning/evidence-index.json` and accepted `planning/handoffs/*.json`.
- Verify each accepted planning handoff is consumed by `plan.md`, `research.md`, `quickstart.md`, `data-model.md`, `contracts/`, `plan-contract.json`, or is explicitly deferred or blocked.
- Treat an accepted planning handoff with no downstream consumer as a plan-layer blocker, not harmless leftover evidence.

**From task-generation evidence when present:**

- Read `task-generation/evidence-index.json` and accepted `task-generation/handoffs/*.json`.
- Verify each accepted task-generation handoff is consumed by `tasks.md`, `handoff-to-tasks.json`, `task-index.json`, `task-packets/*.json`, or is explicitly deferred, escalated, or blocked.
- Treat an accepted task-generation handoff with no downstream consumer as a task-layer blocker before implementation can proceed.

**From constitution:**

- Load `.specify/memory/constitution.md` for principle validation

### 4. Build Semantic Models

Create internal representations (do not include raw artifacts in output):

- **Requirements inventory**: For each Functional Requirement (FR-###) and Success Criterion (SC-###), record a stable key. Use the explicit FR-/SC- identifier as the primary key when present, and optionally also derive an imperative-phrase slug for readability (e.g., "User can upload file" → `user-can-upload-file`). Include only Success Criteria items that require buildable work (e.g., load-testing infrastructure, security audit tooling), and exclude post-launch outcome metrics and business KPIs (e.g., "Reduce support tickets by 50%").
- **Locked decision inventory**: Collect locked decisions from `spec.md`, `context.md`, and `plan.md`, then track whether each one survives into the task layer
- **Reference behavior inventory**: When `Fidelity Requirements` exist, collect each reference behavior item and track whether it survives into the plan and task layers
- **Boundary-sensitivity inventory**: Record established boundary patterns, framework-owned surfaces, required implementation references, and any signal that this feature should carry explicit implementation guardrails
- **User story/action inventory**: Discrete user actions with acceptance criteria
- **Task coverage mapping**: Map each task to one or more requirements or stories (inference by keyword / explicit reference patterns like IDs or key phrases)
- **Constitution rule set**: Extract principle names and MUST/SHOULD normative statements

### 5. Detection Passes (Token-Efficient Analysis)

Focus on high-signal findings in the report body. Limit the visible findings table to 50 rows for readability, but do not omit blockers from the durable gate result: `Blocker Bundle` and `workflow-state.md` MUST enumerate every blocking finding. Overflow summaries may cover only non-blocking findings.

#### A. Duplication Detection

- Identify near-duplicate requirements
- Mark lower-quality phrasing for consolidation

#### B. Ambiguity Detection

- Flag vague adjectives (fast, scalable, secure, intuitive, robust) lacking measurable criteria
- Flag unresolved placeholders (TODO, TKTK, ???, `<placeholder>`, etc.)

#### C. Underspecification

- Requirements with verbs but missing object or measurable outcome
- User stories missing acceptance criteria alignment
- Tasks referencing files or components not defined in spec/plan

#### D. Constitution Alignment

- Any requirement or plan element conflicting with a MUST principle
- Missing mandated sections or quality gates from constitution

#### E. Coverage Gaps

- Requirements with zero associated tasks
- Tasks with no mapped requirement/story
- Success Criteria requiring buildable work (performance, security, availability) not reflected in tasks
- Preserved or redesigned reference behavior items with zero associated plan handling or task coverage

#### F. Locked Decision Drift

- Locked decisions present in `spec.md` but absent from `context.md`
- Locked decisions present in `context.md` but missing from `plan.md`
- Locked decisions present in `plan.md` but not preserved by `tasks.md`
- Cases where a decision appears to have been silently weakened, deferred, or renamed without acknowledgment

#### G. Inconsistency

- Terminology drift (same concept named differently across files)
- Data entities referenced in plan but absent in spec (or vice versa)
- Task ordering contradictions (e.g., integration tasks before foundational setup tasks without dependency note)
- Conflicting requirements (e.g., one requires Next.js while other specifies Vue)

#### H. Boundary Guardrail Gaps

- Detect cases where `spec.md`, `context.md`, or `tasks.md` clearly imply a boundary-sensitive implementation area, but later workflow artifacts fail to preserve the needed guardrails
- Use this stable issue family so downstream tooling and reviewers can key off one consistent signal set:
  - `BG1`: missing `Implementation Constitution` for a boundary-sensitive feature area
  - `BG2`: `tasks.md` lacks explicit implementation guardrails even though `plan.md` declares a boundary-sensitive constitution rule
  - `BG3`: implementation guidance does not require confirming the owning framework, defining reference files, or forbidden drift before code-writing work begins
  - `DP1`: subagent execution path lacks compiled hard rules, validation gates, or done criteria in its task packet
  - `DP2`: subagent execution path lacks required references or forbidden drift in its task packet
  - `DP3`: subagent completion lacks required validation evidence or rule acknowledgement
- Treat these signals as triggers:
  - established framework-owned boundary or adapter pattern
  - native bridge, plugin surface, protocol seam, generated API surface, or other contract-heavy boundary
  - explicit required implementation references or boundary-defining files
  - implementation guardrail tasks in `tasks.md` with no matching constitution rule in `plan.md`
- Map findings to codes as follows:
  - `BG1` when the plan is missing the constitution layer
  - `BG2` when the task layer fails to preserve that constitution as implementation guardrails
  - `BG3` when execution guidance fails to force pre-dispatch boundary confirmation
- Report when a generic implementation instinct would likely drift away from the repository's established pattern because the plan left the constraint as background context only

#### I. Consequence Preservation Analysis

- Detect every `CA-###` consequence obligation in `spec.md`, `context.md`, `references.md`, `alignment.md`, `plan.md`, `tasks.md`, `plan-contract.json`, `task-index.json`, and task packets when present.
- Verify each consequence obligation keeps its claim, affected objects, lifecycle state behavior, dependency impact, recovery and validation contract, owner workflow, latest resolve phase, status, and stop-and-reopen condition across downstream artifacts.
- Flag any obligation that disappears, is renamed without traceability, loses validation evidence, lacks task or packet coverage, or is treated as resolved without proof.
- Must not drop consequence obligations from the analysis report or blocker bundle. If an upstream artifact omitted one, report the omission and route to the highest invalid workflow stage that can restore it.
- Treat unresolved or unmapped `CA-###` obligations as blockers when implementation would otherwise continue through lifecycle, running-state, destructive-operation, shared-state, or downstream-consumer ambiguity.
- If the consequence model is complete and every stop-and-reopen condition is mapped or resolved, record the gate as cleared for implementation; otherwise keep implementation paused.

### 6. Severity Assignment

Use this heuristic to prioritize findings:

- **CRITICAL**: Violates constitution MUST, missing core spec artifact, or requirement with zero coverage that blocks baseline functionality
- **HIGH**: Duplicate or conflicting requirement, ambiguous security/performance attribute, untestable acceptance criterion, a locked decision silently dropped between artifacts, or a missing `Implementation Constitution` for a clearly boundary-sensitive feature area
- **MEDIUM**: Terminology drift, missing non-functional task coverage, underspecified edge case
- **LOW**: Style/wording improvements, minor redundancy not affecting execution order

### 7. Produce Compact Analysis Report

Output a Markdown report (no file writes) with the following structure:

## Specification Analysis Report

| ID | Signal Code | Category | Severity | Location(s) | Summary | Recommendation |
|----|-------------|----------|----------|-------------|---------|----------------|
| A1-001 | A1 | Duplication | HIGH | spec.md:L120-134 | Two similar requirements ... | Merge phrasing; keep clearer version |
| BG1-001 | BG1 | Boundary Guardrail Gap | HIGH | plan.md, tasks.md | Boundary-sensitive area lacks `Implementation Constitution` in the plan | Re-run `{{invoke:plan}}` to add the constitution, then `{{invoke:tasks}}` if guardrail tasks need regeneration |
| BG2-001 | BG2 | Boundary Guardrail Gap | HIGH | tasks.md | Plan declares a boundary-sensitive constitution rule, but tasks do not preserve it as implementation guardrails | Re-run `{{invoke:tasks}}` or edit `tasks.md` so guardrail tasks exist before setup or feature work |
| BG3-001 | BG3 | Boundary Guardrail Gap | HIGH | implement guidance | Execution guidance does not force boundary confirmation before code-writing work starts | Update implementation guidance so the owning framework, required references, and forbidden drift are confirmed before dispatch |
| DP1-001 | DP1 | Dispatch Packet Gap | HIGH | implement guidance, runtime payload | Delegated execution path is missing compiled hard rules, validation gates, or done criteria | Compile and validate a `WorkerTaskPacket` before dispatch |
| DP2-001 | DP2 | Dispatch Packet Gap | HIGH | plan.md, tasks.md, runtime payload | Delegated execution path is missing required references or forbidden drift | Add packet references/forbidden drift to planning artifacts, then recompile |
| DP3-001 | DP3 | Dispatch Result Gap | HIGH | subagent result, join point | Subagent completion lacks validation evidence or rule acknowledgement | Reject the subagent result and require a packet-compliant rerun |

(Add one row per finding. Each row uses a stable fingerprint-first finding ID, and keeps BG/DP values as signal codes where applicable.)

**Blocker Bundle:**

The `Blocker Bundle` MUST enumerate every blocking finding even when the visible findings table is capped at 50 rows. Do not place blocking findings only in overflow summaries.

| Invalid Stage | Blocking Finding IDs | Required Re-entry | Notes |
|---------------|----------------------|-------------------|-------|
| clarify | [IDs or none] | `{{invoke:clarify}}` | Reopen spec/context truth, then regenerate downstream artifacts |
| deep-research | [IDs or none] | `{{invoke:deep-research}}` | Prove unresolved implementation chain before planning |
| plan | [IDs or none] | `{{invoke:plan}}` | Repair planning truth, then regenerate tasks |
| tasks | [IDs or none] | `{{invoke:tasks}}` | Repair task decomposition and rerun analyze |
| execution-only | [IDs or none] | `{{invoke:implement}}` or `{{invoke:debug}}` | No upstream artifact regeneration required |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|

**Locked Decision Preservation Table:**

| Locked Decision | In Context? | In Plan? | In Tasks? | Notes |
|-----------------|-------------|----------|-----------|-------|

**Reference Behavior Preservation Table:** (if any)

| Behavior ID | In Spec Fidelity? | In Plan? | In Tasks? | Notes |
|-------------|-------------------|----------|-----------|-------|

**Boundary Guardrail Table:** (if any)

| Boundary Signal | Seen In Spec/Context? | Seen In Plan Constitution? | Seen In Tasks Guardrails? | Notes |
|-----------------|-----------------------|----------------------------|---------------------------|-------|

**Constitution Alignment Issues:** (if any)

**Unmapped Tasks:** (if any)

**Metrics:**

- Total Requirements
- Total Tasks
- Coverage % (requirements with >=1 task)
- Ambiguity Count
- Duplication Count
- Critical Issues Count
- Boundary Guardrail Gap Count

### 8. Provide Next Actions

At the end of the report, output exactly one `Recommended Next Command` based on the highest invalid workflow stage.

- If the highest-impact unresolved issue lives in `spec.md` or `context.md`, `Recommended Next Command` MUST be `{{invoke:clarify}}`.
- If the highest-impact unresolved issue is a clear requirement whose implementation chain is still unproven, `Recommended Next Command` MUST be `{{invoke:deep-research}}`.
- If the highest-impact unresolved issue lives in `plan.md`, `Recommended Next Command` MUST be `{{invoke:plan}}`.
- If the highest-impact unresolved issue lives only in `tasks.md`, `Recommended Next Command` MUST be `{{invoke:tasks}}`.
- If no upstream artifact is invalid and the remaining issue is execution-only, `Recommended Next Command` MUST be `{{invoke:implement}}` or `{{invoke:debug}}`, whichever matches the recorded execution problem.
- Do not output multiple alternative next commands for the same analysis result.

### 9. Define Workflow Re-entry

After `Next Actions`, output a short `Recommended Re-entry` block that names:
- the single highest workflow stage that must be reopened
- the minimum downstream regeneration path from that stage

Rules:
- If the highest invalid stage is `clarify`, the re-entry chain MUST be `{{invoke:clarify}} -> {{invoke:plan}} -> {{invoke:tasks}} -> {{invoke:analyze}} -> {{invoke:implement}}`.
- If the highest invalid stage is `deep-research`, the re-entry chain MUST be `{{invoke:deep-research}} -> {{invoke:plan}} -> {{invoke:tasks}} -> {{invoke:analyze}} -> {{invoke:implement}}`.
- If the highest invalid stage is `plan`, the re-entry chain MUST be `{{invoke:plan}} -> {{invoke:tasks}} -> {{invoke:analyze}} -> {{invoke:implement}}`.
- If the highest invalid stage is `tasks`, the re-entry chain MUST be `{{invoke:tasks}} -> {{invoke:analyze}} -> {{invoke:implement}}`.
- If the remaining issue is execution-only, the re-entry chain MUST begin at `{{invoke:implement}}` or `{{invoke:debug}}`.
- Do not output multiple alternative re-entry chains for the same result.

### 9.5 Persist Workflow Gate Result

Before the final completion text, write or update `WORKFLOW_STATE_FILE` so it records the gate outcome:

Always update or preserve the `Analyze Gate` section in `WORKFLOW_STATE_FILE` with:
- `gate_status: cleared | blocked`
- `gate_cycle: [integer]`
- `highest_invalid_stage: clarify | deep-research | plan | tasks | execution-only | none`
- `blocker_bundle: [finding ID | invalid stage | status | attribution | compact summary | remediation requirement]`
- `artifact_fingerprint_basis: [spec.md/context.md/plan.md/tasks.md summaries or hashes when available]`

When revalidation finds a new blocker, record its attribution on that `blocker_bundle` row using `missed_by_previous_analyze`, `introduced_by_remediation`, `upstream_artifact_changed`, or `detector_scope_changed`.

- When no upstream remediation is required, record the analyze gate as cleared and hand off to implementation.
- If no upstream remediation is required:
  - `active_command: sp-analyze`
  - `phase_mode: analysis-only`
  - `status: completed`
  - `next_action: begin implementation from the cleared execution batch`
  - `next_command: /sp.implement`
- If the highest invalid stage is `spec.md` or `context.md`:
  - `next_action: reopen specification alignment and regenerate downstream artifacts`
  - `next_command: /sp.clarify`
- If the constitution itself must change:
  - `next_action: amend project principles first, then reopen the highest affected downstream stage and regenerate downstream artifacts`
  - `next_command: /sp.constitution`
- If the highest invalid stage is `plan.md`:
  - `next_action: reopen planning and regenerate downstream artifacts`
  - `next_command: /sp.plan`
- If the highest invalid stage is only `tasks.md`:
  - `next_action: regenerate task decomposition before implementation resumes`
  - `next_command: /sp.tasks`
- If execution evidence must be repaired without upstream artifact drift:
  - `next_action: resume execution-side recovery with the recorded blocker context`
  - `next_command: /sp.implement` or `/sp.debug` as justified by the report

### 10. Offer Remediation

Ask the user: "Would you like me to draft concrete remediation edits and the exact workflow re-entry path for the top N issues?" (Do NOT apply them automatically.)

## Operating Principles

### Context Efficiency

- **Minimal high-signal tokens**: Focus on actionable findings, not exhaustive documentation
- **Progressive disclosure**: Load artifacts incrementally; don't dump all content into analysis
- **Token-efficient output**: Limit findings table to 50 rows; summarize overflow
- **Deterministic results**: Rerunning without changes should produce consistent IDs and counts

### Analysis Guidelines

- **NEVER modify files** (this is read-only analysis)
- **NEVER hallucinate missing sections** (if absent, report them accurately)
- **Prioritize constitution violations** (these are always CRITICAL)
- **Use examples over exhaustive rules** (cite specific instances, not generic patterns)
- **Report zero issues gracefully** (emit success report with coverage statistics)

If this workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, follow the shared inline closeout contract:

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}

## Invocation Context

{ARGS}

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

## First-Party Workflow Quality Hooks

- Once `FEATURE_DIR` is known, use `{{specify-subcmd:hook preflight --command analyze --feature-dir "$FEATURE_DIR"}}` before deeper analysis so stale brownfield routing or invalid workflow entry is surfaced through the shared product guardrail layer.
- After `WORKFLOW_STATE_FILE` is created or resumed, use `{{specify-subcmd:hook validate-state --command analyze --feature-dir "$FEATURE_DIR"}}` so the shared validator confirms `workflow-state.md` matches the `sp-analyze` contract.
- Before final gate reporting, use `{{specify-subcmd:hook validate-artifacts --command analyze --feature-dir "$FEATURE_DIR"}}` so the required analyze-side artifact set is checked by the shared hook surface.
- Before compaction-risk transitions or after large findings synthesis, use `{{specify-subcmd:hook checkpoint --command analyze --feature-dir "$FEATURE_DIR"}}` to emit a resume-safe checkpoint payload from `workflow-state.md`.
- Run `{{specify-subcmd:learning start --command analyze --format json}}` when available, then use the `signal-learning` helper surface if the analysis exposes repeated artifact rewrites, route changes, false starts, or hidden dependencies.
- Read `.specify/memory/learnings/INDEX.md` before broader analysis context and open only learning detail docs linked from analysis-relevant index entries.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
  Command shape: `{{specify-subcmd:hook signal-learning --command analyze --retry-attempts <n> --hypothesis-changes <n>}}`
- Before final cleared or blocked gate reporting, use the `review-learning` helper surface.
  Command shape: `{{specify-subcmd:hook review-learning --command analyze --terminal-status <resolved|blocked> --decision <none|captured|deferred> --rationale "<why>"}}`
- Prefer `{{specify-subcmd:learning capture-auto --command analyze --feature-dir "$FEATURE_DIR" --format json}}` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints.
- When durable state does not capture the reusable lesson cleanly, use the manual `capture-learning` hook surface.
  Required options: `--command`, `--type`, `--summary`, `--evidence`

## Execution Steps

### 1. Initialize Analysis Context

Run `{SCRIPT}` once from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS. Derive absolute paths:

- If `FEATURE_DIR` is not already explicit, prefer `{{specify-subcmd:lane resolve --command analyze --ensure-worktree}}` before guessing from branch-only context.
- When lane resolution returns a materialized lane worktree, continue analysis from that isolated worktree context so downstream gate decisions stay attached to the same lane boundary.

- SPEC = FEATURE_DIR/spec.md
- CONTEXT = FEATURE_DIR/context.md
- PLAN = FEATURE_DIR/plan.md
- TASKS = FEATURE_DIR/tasks.md

Abort with an error message if any required file is missing (instruct the user to run missing prerequisite command).
For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

- Set `WORKFLOW_STATE_FILE` to `FEATURE_DIR/workflow-state.md`.
- [AGENT] Create or resume `WORKFLOW_STATE_FILE` before substantial analysis work begins.
- Read `templates/workflow-state-template.md`.
- If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid authoritative file references and gate notes instead of relying on chat memory alone.

### 2. Ensure project cognition runtime exists

- Read `.specify/project-cognition/status.json`.
- Read `.specify/project-cognition/slices/change.json`.
- If the project cognition runtime is missing, stop and tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that rebuild before continuing.
- If the graph runtime is stale or too weak for the touched area, use `{{invoke:map-update}}` when the touched area is localized.
- Escalate to `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only when no usable localized baseline remains or a full rebuild is required.
- If the runtime is `possibly_stale`, inspect the reported changed paths, reasons, and slice coverage. If the change slice does not cover ownership, propagation, or verification routes for the current analysis request, use `{{invoke:map-update}}` before trusting the runtime for analysis.
- Treat task-relevant coverage as insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
- If task-relevant coverage is insufficient for the current analysis request, read existing workflow-specific graph artifacts or targeted live evidence; refresh through `{{invoke:map-update}}` when localized, and rebuild through `{{invoke:map-scan}}`, then `{{invoke:map-build}}` before continuing when no usable localized baseline remains or a full rebuild is required.

### 3. Load Artifacts (Progressive Disclosure)

Load only the minimal necessary context from each artifact:

**From project cognition runtime:**

- Read `.specify/project-cognition/status.json`
- Read `.specify/project-cognition/slices/change.json`
- Read workflow-specific graph artifacts only when the change slice does not fully cover ownership, propagation, or verification routes
- If topical coverage is missing, stale, too broad, or task-relevant coverage is insufficient, use `/sp-map-update` when localized; rebuild through `/sp-map-scan` followed by `/sp-map-build` only when no usable localized baseline remains or a full rebuild is required, then inspect the minimum live files still needed to replace guesswork with evidence

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

Focus on high-signal findings. Limit to 50 findings total; aggregate remainder in overflow summary.

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

### 6. Severity Assignment

Use this heuristic to prioritize findings:

- **CRITICAL**: Violates constitution MUST, missing core spec artifact, or requirement with zero coverage that blocks baseline functionality
- **HIGH**: Duplicate or conflicting requirement, ambiguous security/performance attribute, untestable acceptance criterion, a locked decision silently dropped between artifacts, or a missing `Implementation Constitution` for a clearly boundary-sensitive feature area
- **MEDIUM**: Terminology drift, missing non-functional task coverage, underspecified edge case
- **LOW**: Style/wording improvements, minor redundancy not affecting execution order

### 7. Produce Compact Analysis Report

Output a Markdown report (no file writes) with the following structure:

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Duplication | HIGH | spec.md:L120-134 | Two similar requirements ... | Merge phrasing; keep clearer version |
| BG1 | Boundary Guardrail Gap | HIGH | plan.md, tasks.md | Boundary-sensitive area lacks `Implementation Constitution` in the plan | Re-run `{{invoke:plan}}` to add the constitution, then `{{invoke:tasks}}` if guardrail tasks need regeneration |
| BG2 | Boundary Guardrail Gap | HIGH | tasks.md | Plan declares a boundary-sensitive constitution rule, but tasks do not preserve it as implementation guardrails | Re-run `{{invoke:tasks}}` or edit `tasks.md` so guardrail tasks exist before setup or feature work |
| BG3 | Boundary Guardrail Gap | HIGH | implement guidance | Execution guidance does not force boundary confirmation before code-writing work starts | Update implementation guidance so the owning framework, required references, and forbidden drift are confirmed before dispatch |
| DP1 | Dispatch Packet Gap | HIGH | implement guidance, runtime payload | Delegated execution path is missing compiled hard rules, validation gates, or done criteria | Compile and validate a `WorkerTaskPacket` before dispatch |
| DP2 | Dispatch Packet Gap | HIGH | plan.md, tasks.md, runtime payload | Delegated execution path is missing required references or forbidden drift | Add packet references/forbidden drift to planning artifacts, then recompile |
| DP3 | Dispatch Result Gap | HIGH | subagent result, join point | Subagent completion lacks validation evidence or rule acknowledgement | Reject the subagent result and require a packet-compliant rerun |

(Add one row per finding; generate stable IDs prefixed by category initial.)

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

## Invocation Context

{ARGS}

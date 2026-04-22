---
description: Perform a non-destructive cross-artifact consistency and quality analysis across spec.md, context.md, plan.md, and tasks.md after task generation, including boundary guardrail drift.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Identify inconsistencies, duplications, ambiguities, and underspecified items across the core planning artifacts (`spec.md`, `context.md`, `plan.md`, `tasks.md`) before implementation. This command MUST run only after `/sp.tasks` has successfully produced a complete `tasks.md`.

## Operating Constraints

**STRICTLY READ-ONLY**: Do **not** modify any files. Output a structured analysis report. Offer an optional remediation plan (user must explicitly approve before any follow-up editing commands would be invoked manually).

**Constitution Authority**: The project constitution (`.specify/memory/constitution.md`) is **non-negotiable** within this analysis scope. Constitution conflicts are automatically CRITICAL and require adjustment of the spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring of the principle. If a principle itself needs to change, that must occur in a separate, explicit constitution update outside `/sp.analyze`.

## Execution Steps

### 1. Initialize Analysis Context

Run `{SCRIPT}` once from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS. Derive absolute paths:

- SPEC = FEATURE_DIR/spec.md
- CONTEXT = FEATURE_DIR/context.md
- PLAN = FEATURE_DIR/plan.md
- TASKS = FEATURE_DIR/tasks.md

Abort with an error message if any required file is missing (instruct the user to run missing prerequisite command).
For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

### 2. Ensure repository navigation system exists

- Check whether `.specify/project-map/status.json` exists.
- If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
- If freshness is `missing` or `stale`, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts.
- If freshness is `possibly_stale`, inspect the reported changed paths and reasons. If they overlap the current analysis request, touched area, shared surfaces, change-propagation hotspots, verification entry points, or known unknowns, run `/sp-map-codebase` before continuing.
- Check whether `PROJECT-HANDBOOK.md` exists at the repository root.
- Check whether `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md` exist.
- If the navigation system is missing, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts.
- Treat task-relevant coverage as insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
- If task-relevant coverage is insufficient for the current analysis request, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts.

### 3. Load Artifacts (Progressive Disclosure)

Load only the minimal necessary context from each artifact:

**From handbook/project map:**

- Read `PROJECT-HANDBOOK.md`
- Read the smallest relevant combination of `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md`
- If topical coverage is missing, stale, too broad, or task-relevant coverage is insufficient, run `/sp-map-codebase` before continuing, then inspect the minimum live files still needed to replace guesswork with evidence

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
| BG1 | Boundary Guardrail Gap | HIGH | plan.md, tasks.md | Boundary-sensitive area lacks `Implementation Constitution` in the plan | Re-run `/sp.plan` to add the constitution, then `/sp.tasks` if guardrail tasks need regeneration |
| BG2 | Boundary Guardrail Gap | HIGH | tasks.md | Plan declares a boundary-sensitive constitution rule, but tasks do not preserve it as implementation guardrails | Re-run `/sp.tasks` or edit `tasks.md` so guardrail tasks exist before setup or feature work |
| BG3 | Boundary Guardrail Gap | HIGH | implement guidance | Execution guidance does not force boundary confirmation before code-writing work starts | Update implementation guidance so the owning framework, required references, and forbidden drift are confirmed before dispatch |

(Add one row per finding; generate stable IDs prefixed by category initial.)

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|

**Locked Decision Preservation Table:**

| Locked Decision | In Context? | In Plan? | In Tasks? | Notes |
|-----------------|-------------|----------|-----------|-------|

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

At end of report, output a concise Next Actions block:

- If CRITICAL issues exist: Recommend resolving before `/sp.implement`
- If only LOW/MEDIUM: User may proceed, but provide improvement suggestions
- If a `Boundary Guardrail Gap` exists: explicitly recommend `/sp.plan` to add `Implementation Constitution`, then `/sp.tasks` if task guardrails must be regenerated
- If `BG2` exists: explicitly recommend regenerating or editing `tasks.md` before implementation starts
- If `BG3` exists: explicitly recommend updating implementation guidance before `/sp.implement` continues
- Provide explicit command suggestions: e.g., "Run /sp.specify with refinement", "Run /sp.plan to adjust architecture", "Manually edit tasks.md to add coverage for 'performance-metrics'"

### 9. Offer Remediation

Ask the user: "Would you like me to suggest concrete remediation edits for the top N issues?" (Do NOT apply them automatically.)

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

## Context

{ARGS}

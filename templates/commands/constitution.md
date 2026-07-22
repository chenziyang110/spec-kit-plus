---
description: Use when project principles or development rules need to be created, revised, or realigned before further specification or planning work.
workflow_contract:
  when_to_use: The project's governing principles need to be created or updated before downstream workflow work should continue.
  primary_objective: Update `.specify/memory/constitution.md` after understanding the current project context.
  primary_outputs: A finalized constitution plus a report of any dependent templates, shared-memory, docs, or workflow artifacts that may need separate follow-up.
  default_handoff: /sp-specify for new work, or recommend the highest affected downstream stage (/sp-plan, /sp-tasks, or /sp-analyze) when a midstream amendment invalidates active artifacts.
handoffs:
  - label: Build Specification
    agent: sp.specify
    prompt: Implement the feature specification based on the updated constitution. I want to build...
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Objective

Create or update the project constitution as the authoritative rule layer for
downstream specification, planning, and execution work.

## Constitution-Only Write Boundary

This workflow writes only `.specify/memory/constitution.md`.

Use templates, command files, docs, project rules, learning files,
workflow-state files, project cognition artifacts, generated assets, and active
feature artifacts as read-only context. Do not modify them, synchronize them,
or run mutation commands for them unless the user explicitly expands the write
scope in the same request.

If the amended constitution appears to require downstream changes, report those
changes as pending follow-up in the Sync Impact Report. The report is the
handoff mechanism; this command does not apply the follow-up work.

## Context

- Primary inputs: the current constitution, the user's requested principle
  changes, the consume-only Learning CLI intake, and the smallest repository
  context needed to derive missing values.
- Constitution amendments may invalidate downstream planning artifacts, active
  workflow state, or lower-order project memory. Treat those as re-entry
  signals to report, not as permission to edit additional files.
- Versioning and governance metadata are part of the contract, not optional
  decoration.

## Process

- Run `{{specify-subcmd:learning start --command constitution --format json}}`
  and expand only selected matching Learning through `show_argv`.
- Load the current constitution before broader repository context. Do not parse
  Learning storage files directly.
- If the repository already has code and repo-derived evidence is needed, read
  `.specify/project-cognition/status.json` plus the smallest relevant
  query-backed cognition artifact first to assess map freshness as advisory
  navigation before trusting any compatibility/export artifact.
- If cognition is stale or weak for an ordinary existing-baseline touched area,
  continue from live repository evidence and recommend `/sp-map-update` only as
  external/manual map maintenance when the user asks for map maintenance or
  before a separate map-maintenance pass. Use `/sp-map-scan` followed by
  `/sp-map-build` only for first/missing/unusable baseline, schema failure,
  zero active-generation `path_index` rows, `explicit_rebuild_requested`, or
  `baseline_identity_invalid`.
- Load the current constitution and identify unresolved placeholders or
  requested changes.
- Derive the right version bump and updated governance metadata.
- Rewrite only `.specify/memory/constitution.md`.
- If a principle change appears to invalidate active `spec.md`, `plan.md`,
  `tasks.md`, or `workflow-state.md`, report the highest affected downstream
  stage instead of editing those artifacts.

## Output Contract

- Write a finalized constitution with a Sync Impact Report.
- Record dependent templates, guidance, lower-order project memory, workflow
  state, and cognition artifacts as pending follow-up items when they need
  alignment.
- Surface the exact downstream re-entry path (`/sp-specify`, `/sp-plan`,
  `/sp-tasks`, or `/sp-analyze`) when an amendment invalidates active work.
- Surface any follow-up items if a value must remain intentionally deferred.

## Guardrails

- Do not leave unexplained placeholders behind.
- Respect the semantic-versioning rules for constitution changes.
- Do not partially update downstream guidance. Report pending follow-up instead.
- Do not always hand off directly to `/sp-specify`; use the highest affected
  downstream stage when the amendment is midstream.
- Do not leave project rules or learnings that conflict with the amended
  constitution unreported in the Sync Impact Report.

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch
subagents, wait for structured handoffs, integrate results, verify, and keep
all writes within the constitution-only scope defined below.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.


## Outline

You are updating the project constitution at `.specify/memory/constitution.md`.
This file may already contain a fully initialized default constitution, or it
may still contain legacy placeholder tokens in square brackets (for example
`[PROJECT_NAME]`). Your job is to refine the document into a concrete project
constitution based on the user's request and the current project context.

**Write scope**: This command writes only `.specify/memory/constitution.md`.
Do not modify templates, command files, docs, project rules, learning files,
workflow-state files, project cognition artifacts, or active feature artifacts
unless the user explicitly asks for those additional edits in the same request.
When the amended constitution appears to require changes elsewhere, record them
as pending follow-up items in the Sync Impact Report instead of applying them.

**Note**: If `.specify/memory/constitution.md` does not exist yet, it should
have been initialized from `.specify/templates/constitution-template.md`
during project setup. That project-local template may be the default product
constitution or a built-in profile selected during `{{specify-subcmd:init}}`. If it is
missing, copy the template first.

{{spec-kit-include: ../command-partials/common/learning-layer.md}}

When constitution work exposes a reusable signal, record it as a pending
Learning follow-up in the Sync Impact Report. This consume-only command must not
capture or promote lower-order Learning inline.
Report project rules or learnings that conflict with the amended constitution
as pending follow-up work with explicit owners.

## Repository Context and Navigation Freshness

- If repo-derived evidence is needed, read `.specify/project-cognition/status.json` plus the smallest relevant query bundle or graph artifact first to assess map freshness as advisory navigation before trusting any compatibility/export artifact.
- If the navigation system is stale or weak for an existing usable baseline, continue with live repository evidence and recommend `/sp-map-update` only as external/manual map maintenance when the user asks for map maintenance or before a separate map-maintenance pass rather than fabricating repository context. That route is external map maintenance, not constitution closeout ownership. Use `/sp-map-scan` followed by `/sp-map-build` only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- A constitution-only amendment does not own project cognition mutation closeout.
  Do not run `specify-runtime cognition update`, `specify-runtime cognition mark-dirty`, or
  related mutation commands from this workflow unless the user explicitly asked
  for project cognition maintenance. If the amendment may affect cognition
  coverage or compatibility/export output, report that follow-up instead.
- sp-map-update is for manual/external maintenance and follow-up repair, not
  routine cleanup for constitution-only changes.
- If the amendment changes structure, ownership, workflows, testing strategy, integrations, or operator expectations, mark the related project cognition compatibility/export surface for refresh in the Sync Impact Report even if the constitution update itself is complete. Use this exact framing: mark the related project cognition compatibility/export surface for refresh.

## Downstream Re-entry Contract

- Inspect active downstream artifacts and phase locks before finalizing the
  amendment. At minimum, review any active `spec.md`, `plan.md`, `tasks.md`,
  or `workflow-state.md` package that relies on the current constitution.
- If a principle change appears to invalidate active `spec.md`, `plan.md`,
  `tasks.md`, or `workflow-state.md`, record the highest affected downstream
  stage and exact re-entry path in the Sync Impact Report.
- Do not always hand off directly to `/sp-specify`. Midstream amendments may
  require `/sp-plan`, `/sp-tasks`, or `/sp-analyze` when higher-order feature
  artifacts already exist.

## Workflow Phase Lock (When an Active Feature Is Affected)

- If the amendment changes an active feature package, treat the affected
  `FEATURE_DIR/workflow-state.md` as read-only context for determining the
  downstream re-entry path.
- Read `templates/workflow-state-template.md`.
- When an active feature package is affected, do not update or create
  `FEATURE_DIR/workflow-state.md`. Instead, report the recommended state values:
  - `active_command: sp-constitution`
  - `phase_mode: planning-only`
  - a `next_action` that points to the highest affected downstream stage after
    the constitution amendment lands
  - a `next_command` of `/sp-specify`, `/sp-plan`, `/sp-tasks`, or
    `/sp-analyze` as required by the affected artifacts
- Before final handoff from a constitution amendment that affects an active
  feature package, verify the amended `.specify/memory/constitution.md` and
  list any downstream `workflow-state.md` follow-up needed for resume safety.
- Before any compaction-risk transition during a constitution amendment that
  affects an active feature package, keep the downstream re-entry path in the
  Sync Impact Report so it survives session recovery without mutating feature
  artifacts.

Follow this execution flow:

1. Load the existing constitution at `.specify/memory/constitution.md`.
   - Identify every unresolved placeholder token of the form
     `[ALL_CAPS_IDENTIFIER]`, if any remain.
   - Treat existing concrete principles as the current baseline unless the user
     asks to replace them.
   - **IMPORTANT**: The user might require fewer or more principles than the
     ones used in the default constitution. If a number is specified, respect
     that and update the document accordingly.

2. Collect or derive missing and revised values:
   - If user input (conversation) supplies a value, use it.
   - Otherwise infer from existing repo context (README, docs,
     project cognition runtime truth, compatibility/export references when explicitly relevant, prior constitution versions if embedded).
   - For governance dates: `RATIFICATION_DATE` is the original adoption date
     (if unknown ask or mark TODO), `LAST_AMENDED_DATE` is today if changes
     are made, otherwise keep the previous value.
   - `CONSTITUTION_VERSION` must increment according to semantic versioning
     rules:
     - MAJOR: Backward incompatible governance/principle removals or
       redefinitions.
     - MINOR: New principle/section added or materially expanded guidance.
     - PATCH: Clarifications, wording, typo fixes, non-semantic refinements.
   - If the version bump type is ambiguous, propose reasoning before
     finalizing.

3. Draft the updated constitution content:
   - Replace every unresolved placeholder with concrete text. No unexplained
     bracketed tokens should remain.
   - Preserve heading hierarchy. Remove stale instructional comments once they
     no longer add value.
   - Ensure each Principle section has a succinct name, concrete rules, and
     explicit rationale where helpful.
   - Ensure Governance lists amendment procedure, versioning policy, and
     compliance review expectations.

4. Consistency review checklist (read/report only):
   - Read `.specify/templates/plan-template.md` and ensure any
     "Constitution Check" or rules align with updated principles.
   - Read `.specify/templates/spec-template.md` for scope and requirements
     alignment. Report it if the constitution adds or removes mandatory
     sections or constraints that the template does not reflect.
   - Read `.specify/templates/tasks-template.md` and ensure task
     categorization reflects new or removed principle-driven task types
     (for example observability, versioning, or testing discipline).
   - Read each command file in `.specify/templates/commands/*.md` (including
     this one) to verify no outdated references remain when generic guidance is
     required.
   - Use the consume-only Learning CLI intake and selected `show` records to
     report any lower-order guidance that now conflicts with the amended constitution.
- If the amendment changes navigation, structure, ownership, workflow,
  testing, integration, or operations expectations, mark the runtime
  handbooks for refresh and include `.specify/project-cognition/status.json`
  in the propagation review.
   - Read any runtime guidance docs (for example `README.md`,
     `docs/quickstart.md`, or agent-specific guidance files if present). Report
     references to principles that changed instead of updating those files.

5. Produce a Sync Impact Report (prepend as an HTML comment at the top of the
   constitution file after update):
   - Version change: old -> new
   - List of modified principles (old title -> new title if renamed)
   - Added sections
   - Removed sections
   - Templates, docs, shared memory, workflow-state, or project cognition
     surfaces requiring separate follow-up (`pending`) with file paths
   - Downstream re-entry path: `/sp-specify`, `/sp-plan`, `/sp-tasks`, or
     `/sp-analyze`, with the highest affected downstream stage called out
     explicitly
   - Follow-up TODOs if any placeholders are intentionally deferred

6. Validation before final output:
   - No remaining unexplained bracket tokens
   - Version line matches the report
   - Dates use ISO format `YYYY-MM-DD`
   - Principles are declarative, testable, and free of vague language
     (`should` -> replace with MUST/SHOULD rationale where appropriate)

7. Write the completed constitution back to
   `.specify/memory/constitution.md` (overwrite).

   This is the only file this command may write unless the user explicitly
   expanded the write scope in the same request.

8. Output a final summary to the user with:
   - New version and bump rationale
   - The highest affected downstream stage and why that is the correct
     re-entry point
   - Any files flagged for manual follow-up
   - Suggested commit message (for example
     `docs: amend constitution to vX.Y.Z (principle additions + governance update)`)

Formatting and Style Requirements:

- Use Markdown headings exactly as in the template (do not demote or promote
  levels).
- Wrap long rationale lines to keep readability (under 100 chars ideally) but
  do not hard enforce with awkward breaks.
- Keep a single blank line between sections.
- Avoid trailing whitespace.

If the user supplies partial updates (for example only one principle revision),
still perform validation and version decision steps.

If critical info is missing (for example the ratification date is truly
unknown), insert `TODO(<FIELD_NAME>): explanation` and include it in the Sync
Impact Report under deferred items.

Do not create a new template; always operate on the existing
`.specify/memory/constitution.md` file.

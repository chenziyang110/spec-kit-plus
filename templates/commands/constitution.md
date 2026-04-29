---
description: Use when project principles or development rules need to be created, revised, or realigned before further specification or planning work.
workflow_contract:
  when_to_use: The project's governing principles need to be created or updated before downstream workflow work should continue.
  primary_objective: Update `.specify/memory/constitution.md` and propagate any principle changes into dependent templates and guidance.
  primary_outputs: A synchronized constitution plus any required template, shared-memory, or docs updates triggered by the principle change.
  default_handoff: /sp-specify for new work, or reopen the highest affected downstream stage (/sp-plan, /sp-tasks, or /sp-analyze) when a midstream amendment invalidates active artifacts.
handoffs:
  - label: Build Specification
    agent: sp.specify
    prompt: Implement the feature specification based on the updated constitution. I want to build...
---

{{spec-kit-include: ../command-partials/constitution/shell.md}}

## Outline

You are updating the project constitution at `.specify/memory/constitution.md`.
This file may already contain a fully initialized default constitution, or it
may still contain legacy placeholder tokens in square brackets (for example
`[PROJECT_NAME]`). Your job is to refine the document into a concrete project
constitution and propagate any amendments across dependent artifacts.

**Note**: If `.specify/memory/constitution.md` does not exist yet, it should
have been initialized from `.specify/templates/constitution-template.md`
during project setup. That project-local template may be the default product
constitution or a built-in profile selected during `specify init`. If it is
missing, copy the template first.

## Passive Project Learning Layer

- Run `specify learning start --command constitution --format json` when
  available so passive learning files exist before deeper context collection.
- Read `.specify/memory/constitution.md`,
  `.specify/memory/project-rules.md`, and
  `.specify/memory/project-learnings.md` in that order before broader
  repository context.
- Review `.planning/learnings/candidates.md` only when it still contains
  constitution-relevant candidate learnings after the passive start step,
  especially repeated workflow gaps, stable user defaults, or lower-order
  rules that may need promotion or retirement.
- When constitution work exposes repeated decision debt, rule conflict, or
  promotion friction, run `specify hook signal-learning --command constitution ...`
  so the workflow records reusable learning pressure instead of treating it as
  chat-only discussion.
- Before final reporting, run
  `specify hook review-learning --command constitution --terminal-status <resolved|blocked> ...`;
  use `--decision none --rationale "..."` only when no reusable
  `decision_debt`, `workflow_gap`, `user_preference`, or `project_constraint`
  exists.
- Prefer `specify learning capture-auto --command constitution --feature-dir "$FEATURE_DIR" --format json` when `workflow-state.md` already preserves route reasons, false starts, hidden dependencies, or reusable constraints. Fall back to `specify hook capture-learning --command constitution ...` when the durable state does not capture the reusable lesson cleanly.
- Treat project rules or learnings that conflict with the amended constitution
  as mandatory follow-up work: either realign them in this run or flag them
  explicitly in the Sync Impact Report.

## Repository Context and Navigation Freshness

- If repo-derived evidence is needed, read `PROJECT-HANDBOOK.md` as the root
  navigation artifact and use `.specify/project-map/index/status.json` to assess
  freshness before trusting topical project-map files.
- If the navigation system is missing or stale for an existing codebase, run
  `/sp-map-codebase` before continuing or mark the refresh as a blocking
  follow-up rather than fabricating repository context.
- If the amendment changes structure, ownership, workflows, testing strategy, integrations, or operator expectations, mark the related handbook/project-map surface for refresh in the Sync Impact Report even if the constitution update itself is complete. Use this exact framing: mark the related handbook/project-map surface for refresh.

## Downstream Re-entry Contract

- Inspect active downstream artifacts and phase locks before finalizing the
  amendment. At minimum, review any active `spec.md`, `plan.md`, `tasks.md`,
  or `workflow-state.md` package that relies on the current constitution.
- If a principle change invalidates active `spec.md`, `plan.md`, `tasks.md`,
  or `workflow-state.md`, reopen the highest affected downstream stage and
  record the exact re-entry path in the Sync Impact Report.
- Do not always hand off directly to `/sp-specify`. Midstream amendments may
  require `/sp-plan`, `/sp-tasks`, or `/sp-analyze` when higher-order feature
  artifacts already exist.

## Workflow Phase Lock (When an Active Feature Is Affected)

- If the amendment changes an active feature package, treat the affected
  `FEATURE_DIR/workflow-state.md` as the stage-state source of truth for the
  downstream re-entry path.
- Read `templates/workflow-state-template.md`.
- When an active feature package is affected, update or create
  `FEATURE_DIR/workflow-state.md` so it records:
  - `active_command: sp-constitution`
  - `phase_mode: planning-only`
  - a `next_action` that points to the highest affected downstream stage after
    the constitution amendment lands
  - a `next_command` of `/sp-specify`, `/sp-plan`, `/sp-tasks`, or
    `/sp-analyze` as required by the affected artifacts
- When the local CLI is available and an active feature package is affected,
  use `specify hook validate-state --command constitution --feature-dir "$FEATURE_DIR"`
  after updating `workflow-state.md` so the shared validator confirms the
  constitution handoff state is resume-safe.
- Before final handoff from a constitution amendment that affects an active
  feature package, use
  `specify hook validate-artifacts --command constitution --feature-dir "$FEATURE_DIR"`
  so the amended `.specify/memory/constitution.md` and the downstream
  `workflow-state.md` handoff are machine-checked together.
- Before any compaction-risk transition during a constitution amendment that
  affects an active feature package, use
  `specify hook checkpoint --command constitution --feature-dir "$FEATURE_DIR"`
  so the downstream re-entry path survives session recovery.

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
     handbook/project-map evidence, prior constitution versions if embedded).
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

4. Consistency propagation checklist (convert prior checklist into active
   validations):
   - Read `.specify/templates/plan-template.md` and ensure any
     "Constitution Check" or rules align with updated principles.
   - Read `.specify/templates/spec-template.md` for scope and requirements
     alignment. Update it if the constitution adds or removes mandatory
     sections or constraints.
   - Read `.specify/templates/tasks-template.md` and ensure task
     categorization reflects new or removed principle-driven task types
     (for example observability, versioning, or testing discipline).
   - Read each command file in `.specify/templates/commands/*.md` (including
     this one) to verify no outdated references remain when generic guidance is
     required.
   - Read `.specify/memory/project-rules.md` and
     `.specify/memory/project-learnings.md` and resolve or explicitly report
     any lower-order guidance that now conflicts with the amended constitution.
   - If the amendment changes navigation, structure, ownership, workflow,
     testing, integration, or operations expectations, mark
     `PROJECT-HANDBOOK.md` and the affected `.specify/project-map/` topical
     files for refresh and include `.specify/project-map/index/status.json` in the
     propagation review.
   - Read any runtime guidance docs (for example `README.md`,
     `docs/quickstart.md`, or agent-specific guidance files if present). Update
     references to principles that changed.

5. Produce a Sync Impact Report (prepend as an HTML comment at the top of the
   constitution file after update):
   - Version change: old -> new
   - List of modified principles (old title -> new title if renamed)
   - Added sections
   - Removed sections
   - Templates or shared memory requiring updates (`updated` / `pending`) with
     file paths
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

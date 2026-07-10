Trigger: before marking handoff ready or repairing a rejected handoff.

Purpose: preserve handoff assessment, senior maintainer review, request-changes repair, reviewer guide, self-review, and quality gate rules.

Preserved Contract: Migrated from `templates/commands/discussion.md`; this file preserves existing `sp-discussion` behavior and does not define new workflow behavior.

## Handoff Assessment

Handoff assessment is explicit-user-request only. Run it when the user says the discussion is done, asks to hand off, asks to feed the result to `sp-specify`, or asks to continue the next stage.

A discussion may be specification-ready but still not consumer-ready. Until `handoff-to-specify.md` and `handoff-to-specify.json` both exist, self-review has passed, and the user has confirmed the handoff, the next action is `write-unified-handoff`, draft handoff review, or handoff repair inside `sp-discussion`; do not tell the user to run `sp-specify`.

Write or refresh `handoff-assessment.md` with:

- decision status: `ready-for-handoff` or `continue-discussion`
- rationale citing `requirements.md`, `technical-options.md`, `project-context.md`, `open-questions.md`, boundary evidence, scope confirmation, or explicit assumptions
- assessment dimensions: feature coherence, implementation target clarity, current repository role, reference source clarity, planning shape, validation shape, and risk profile
- required next action: `write-unified-handoff` or `continue-discussion`

Assessment outcomes:

- `ready-for-handoff`: the mature discussion describes one coherent handoff boundary with locked context and a bounded unified scope. Write canonical `handoff-to-specify.json` and render `handoff-to-specify.md` from the same payload.
- `continue-discussion`: the discussion is missing clarity, boundary facts, evidence provenance, scope confirmation, or a coherent unified scope. Return to the question loop.

Do not use `split-required`. Do not write separate split planning artifacts. Broad work must be represented inside the single handoff through a capability map, dependencies, deferred scope, planning constraints, and reopen conditions, or stay in discussion until the scope is coherent. Do not turn broad work into a plan-stage execution sequence inside `sp-discussion`.

## Senior Maintainer Review

Run the Senior Consequence Analysis Gate before technical options are finalized and again before marking the discussion `handoff-ready`. Consequence analysis must shape the option set, not merely review a selected option after the fact.

Before any final option selection or `sp-specify` handoff, perform a maintainer-level consequence review of the selected product direction and any competing candidate option that could change lifecycle, running-state, destructive, shared-state, compatibility, or downstream consumer behavior.

- Apply the Senior Consequence Analysis Gate before writing `handoff-to-specify.md`.
- When the gate triggers, preserve the Affected Object Map, State-Behavior Matrix, Dependency Impact Table, Recovery And Validation Contract, Coverage Gaps, and `CA-###` consequence obligation IDs in the discussion artifacts.
- Route consequence findings into discussion artifacts:
  - `requirements.md`: user-visible state rules, scope, non-goals, acceptance signals, and open behavior choices.
  - `technical-options.md`: 2-3 concrete handling strategies and trade-offs shaped by the consequence analysis.
  - `project-context.md`: project cognition facts, returned `minimal_live_reads`, inference notes, and coverage gaps.
  - `open-questions.md`: only decisions materially changing behavior, implementation shape, or validation.
  - `handoff-to-specify.md`: human-readable `CA-###` obligations.
  - `handoff-to-specify.json`: machine-readable mirror of triggered gate status, consequence analysis, `CA-###` obligations, coverage gaps, and stop-and-reopen conditions.
- Markdown and JSON handoffs must agree on triggered gate status, obligation IDs, claims, blocking level, owner, latest resolve phase, status, and stop-and-reopen condition.
- must not mark the discussion `handoff-ready` while triggered consequence obligations are missing from either Markdown or JSON handoff content.
- Must not mark the discussion `handoff-ready` when the gate triggers and no concrete Affected Object Map, State-Behavior Matrix, Dependency Impact Table, or Recovery And Validation Contract exists.

## Handoff Reviewer Guide

Every draft `handoff-to-specify.md` must include a concise `Handoff Reviewer Guide` before the detailed contract sections or immediately after the Quality Gate. The guide is for an experienced reviewer who understands product and engineering trade-offs but does not know this workflow's internal rules.

The guide must tell the reviewer:

- Decision to make: confirm whether this draft accurately captures the intended product direction and is safe to mark `handoff-ready`, or request changes before the next stage.
- Review order: `Handoff Goal`, `Context Boundary`, `Implementation Target`, `Source Evidence`, `Blocking Unknowns`, `Downstream Instructions`, `Must-Preserve Ledger`, and any `CA-###` consequence obligations.
- Approve only if: the goal matches the user's intent, the target project and reference roles are correct, hard unknowns are absent, soft unknowns are safe to resolve later, non-goals/deferred scope are acceptable, and the Must-Preserve and consequence obligations cover the decisions that would cause drift if lost.
- Request changes if: the target or evidence boundary is wrong, a hard decision is hidden as a soft unknown, a non-goal or reopen condition is missing, the handoff asks downstream workflows to prove or enforce facts outside the target project's authority, or Markdown and JSON disagree on protected IDs or quality-gate status.
- What not to over-review: exact implementation filenames, UI copy/layout, or final field names may remain downstream soft unknowns unless the handoff claims them as verified or they are necessary to keep the scope coherent.

After writing the draft pair, ask the user to review it with this guide and reply with either approval to mark `handoff-ready` or the concrete changes needed. If both consumers are eligible, ask the user to confirm the recommended consumer or choose the other eligible consumer. Do not ask for a bare yes/no confirmation without review criteria.

The visible request for review uses the unified frontstage contract. It must cover the decision being requested, recommended consumer and reason, scope the user would approve, explicitly excluded work, self-review and readiness checks, Markdown/JSON paths, and the allowed responses such as approve as handoff-ready or request concrete changes. The agent chooses the heading names and layout.

Do not collapse the review request into a file list, artifact-write log, or approval keyword. The user needs enough context to decide without rereading every artifact.

## Handoff Quality Gate

The handoff quality gate is mandatory. `sp-discussion` must not mark a handoff ready when any of these checks fail:

- missing or vague `handoff_goal`
- Context Boundary Gate still unresolved
- cross-project request lacks `target_project_root`
- target path exists but evidence source is not named
- current repository roles are not an explicit list of role objects
- target project roles are not an explicit list of role objects when a target exists
- role objects lack `role`, `scope`, `evidence_source`, or `notes`
- Markdown or JSON companion is missing
- Markdown and JSON disagree on shared fields
- hard unknowns remain open
- soft unknowns lack owner, latest resolve phase, or stop-and-reopen condition
- Must-Preserve Ledger omits goal, scope, non-goals, key decisions, acceptance signals, path constraints, or blocking questions
- Markdown handoff lacks a `Handoff Reviewer Guide` with approval and change-request criteria for a reviewer who does not know Spec Kit internals
- quality gate lacks self-review status
- user has not reviewed and confirmed the handoff

Before user confirmation, the handoff can exist only as a draft. Do not recommend `sp-specify` until `quality_gate.status` records user confirmation.

`specification-input.md`, `discussion-state.md`, or any other discussion source file is not a fallback handoff. If the handoff pair is missing or stale, keep the discussion in draft or repair state and refresh `handoff-to-specify.md` and `handoff-to-specify.json` together before any downstream consumer is recommended.

## Handoff Request-Changes Repair

If the user requests changes during handoff review, the repair belongs to `sp-discussion`. Refresh `handoff-to-specify.md` and `handoff-to-specify.json` together from the current discussion source files, then run handoff self-review again before asking the user to approve `handoff-ready`. Keep the discussion in draft/user-review state until the refreshed pair passes self-review and the user confirms it.

Every repair record must preserve `blocked_by_handoff_integrity`, `source_handoff`, `source_handoff_json`, field-level validation errors, `review_digest`, and `quality_gate` evidence.

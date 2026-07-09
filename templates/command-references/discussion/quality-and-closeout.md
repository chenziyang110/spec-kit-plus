Trigger: before closeout, ready-summary, or scope-boundary statements.

Purpose: preserve closeout, ready-summary quality checks, no-execution-planning boundary, no alternate product path, and final response rules.

Preserved Contract: Migrated from `templates/commands/discussion.md`; this file preserves existing `sp-discussion` behavior and does not define new workflow behavior.

## Discussion Flow

1. `context-intake`
   - Identify current project root, user goal, current project roles, target project, target root, reference sources, external systems, path hints, and evidence sources.
   - Run the Context Boundary Gate before project-specific technical options, affected-file claims, or handoff drafting.
   - If the gate is unresolved, ask one boundary question at a time.

2. `product-framing`
   - Clarify goal, users, scenario, scope, non-goals, success signals, constraints, and blocked unknowns.
   - Product framing may continue when target paths are missing, but target-specific implementation claims are forbidden.

3. `context-grounding`
   - Enter only after relevant boundaries are locked.
   - Use current project cognition only for current project facts.
   - Complete the Truth Pass before source-grounded recommendations, affected-surface claims, or project-specific implementation options.
   - For an external target, confirm `target_project_root` first. If target cognition is stale or missing, keep target evidence status as pending context and persist it at the next semantic checkpoint instead of treating current project cognition as proof.

4. `question-loop`
   - Use an Adaptive Question Pack: one required primary question, plus up to two optional same-topic follow-ups only when the topic is local and low risk.
   - Apply the Anti-Toothpaste Protocol before asking: show the decision map, recommend a next path, and ask only when user judgment is genuinely required and no safe default exists.
   - Track hard and soft unknowns in active memory during ordinary turns; persist them to `open-questions.md` only when they materially change at a semantic checkpoint or save trigger.

5. `technical-options`
   - Present 2-3 implementation paths only when strategy affects requirements, the Context Boundary Gate is resolved, and the Truth Pass has established the relevant current-project facts or explicit assumptions.
   - Use the unified frontstage contract: include recommendation, evidence, trade-offs, risks, verification expectations, data-safety constraints, stop-and-reopen conditions, or user-confirmed scope-adjustment path, and required evidence when those details affect the decision.

6. `readiness-summary`
   - Use when direction is locked, the user is no longer choosing core scope, and the useful next discussion product is a readiness summary rather than a plan.
   - State the handoff or downstream-readiness bar, current blockers, blocked user decisions, evidence gaps, and planning inputs to preserve before any state fields or artifact paths.
   - Default to the next safe discussion action when no user-owned decision blocks the work. Do not ask the user to say next just to begin evidence lookup, boundary refinement, or another reversible discussion action.
   - Do not create P0/P1/P2 sequences, migration phases, release batches, task packets, or ordered implementation steps. Keep source edits, test fixes, release execution, and package publishing out of `sp-discussion`; route them as recommended downstream execution only when the user explicitly leaves discussion.

7. `ui-interaction-discussion`
   - Enter only after functional discussion is stable and the matured requirement includes UI-facing scope such as screens, components, layout, navigation, visual hierarchy, interaction states, user-facing copy, accessibility, or workflow feedback.
   - Offer the stage as an optional UI and interaction discussion only when no explicit handoff request is active. If an explicit handoff request is active, run `handoff-assessment.md` first and return to this stage only when UI decisions block readiness or the user reopens UI discussion.
   - If the user skips it, treat `ui_discussion_status: skipped` or `deferred` as a semantic checkpoint field and persist it with the next checkpoint refresh, then continue when other handoff gates are satisfied.
   - Act as a senior UI and interaction designer with 15 years of practical project experience. Guide the user through primary screens, user journey, information hierarchy, component responsibilities, key interactions, loading, empty, success, warning, error, disabled, permission, responsive, density, accessibility, keyboard, focus, and copy expectations when relevant.
   - Use natural language first. ASCII sketches are allowed when they clarify rough screen structure, layout grouping, state transitions, or flow relationships for downstream implementers.

8. `handoff-preview`
   - Use when the discussion has reached a semantic checkpoint where the next useful lifecycle step would be handoff assessment, but the user has not explicitly requested handoff, next-stage continuation, or readiness checking.
   - Do not write `handoff-assessment.md` or handoff draft files in this preview stage.
   - Give the assessment preview in the same visible reply: likely verdict, proposed handoff goal, recommended consumer, proposed package scope, excluded scope, readiness checks, blocking checklist if any, default next action, and override path.
   - Do not end with only "next I recommend handoff assessment" or a list of updated discussion artifacts.
   - Do not phrase the default next action as running `sp-specify`; before explicit handoff and user-confirmed readiness, the next action remains handoff assessment or review inside `sp-discussion`.

9. `handoff-assessment`
   - Decide whether one draft handoff package can be produced for review or discussion must continue.
   - If the direction is too broad to express as one coherent handoff, the result is `continue-discussion`.

10. `handoff-draft`
   - Write Markdown and JSON together only after explicit user request and a bounded unified scope.
   - The draft handoff is a contract, not a prose summary, and is not handoff-ready until self-review and user confirmation.
   - After writing and self-reviewing the draft pair, ask for user review with the unified frontstage contract; do not end in `handoff-draft` with a write-status report.

11. `handoff-self-review`
   - Check placeholders, contradictions, missing goal, missing target path, unresolved hard unknowns, weak evidence provenance, Markdown/JSON drift, Must-Preserve coverage, and consequence obligations.

12. `handoff-review`
   - Ask the user to review the handoff.
   - User confirmation is required before `handoff-ready`.
   - Summarize the handoff goal, recommended consumer, scope being approved, excluded scope, review checks, package paths, and the exact approval or change-request response expected. The agent chooses the visible labels.
   - If the user's next message is an unrelated prompt, codebase explanation request, new target root, or new product question, it must not be treated as approval. Classify it as a new turn, preserve the draft in user-review state, and answer or route the new request according to the normal classifier.

13. `handoff-ready`
   - Only after user confirmation, both handoff files exist, Markdown/JSON agreement is checked, and `quality_gate.status` is user-confirmed. Then tell the user how to invoke the integration-appropriate `sp-specify` command with `.specify/discussions/<slug>/handoff-to-specify.md`.

If a discussion is mature enough for specification but lacks `handoff-to-specify.md` or `handoff-to-specify.json`, close the turn with handoff assessment, draft review, or repair guidance inside `sp-discussion`. Do not tell the user their next sentence should be `sp-specify`, and do not send `specification-input.md` to `sp-specify` as a fallback.

## Quality And Closeout

Handoff-ready closeout covers the handoff goal, selected direction, target boundary, Must-Preserve coverage, hard unknown and conflict counts, quality gate state, Markdown/JSON agreement, and exact downstream consumption path.

Do not close with only file paths, status counters, or a next command. Keep ready-summary quality checks internal until the visible reply translates them into decision-level meaning.

`sp-discussion` does not create P0/P1/P2 sequences, migration phases, release batches, task packets, ordered implementation steps, source edits, test fixes, release execution, or package publishing. Those belong downstream.

When the user rejects fallback/dual-stack/old implementation fallback language, preserve the no alternate product path decision unless the user later reopens it.

Trigger: before closeout, ready-summary, or scope-boundary statements.

Purpose: preserve closeout, ready-summary quality checks, no-execution-planning boundary, no alternate product path, and final response rules.

Preserved Contract: Migrated from `templates/commands/discussion.md`; this file preserves existing `sp-discussion` behavior and does not define new workflow behavior.

## Discussion Flow

Use one primary lifecycle phase and keep blockers, evidence confidence, UI status,
consumer eligibility, persistence mode, and confirmation as orthogonal fields:

1. `explore`: clarify the goal, users, scenarios, scope, non-goals, success
   signals, and meaningful unknowns. Ask only when user judgment is required.
2. `ground`: lock the context boundary and complete the Truth Pass before
   project-specific claims. Current project cognition navigates; live evidence
   proves. External targets require their own root and evidence.
3. `decide`: map adjacent decisions, compare only materially distinct options,
   recommend the best direction, and record confirmed or rejected choices.
4. `prepare`: when explicit handoff is requested, decide `ready-for-handoff` or
   `continue-discussion`. If ready, assemble one canonical JSON payload from the
   selected scope.
5. `review`: validate exact schema/source-contract integrity, Must-Preserve and
   consequence coverage, zero hard blockers/conflicts, evidence provenance,
   reviewer guidance, and the stable review digest. Ask the human to approve
   the meaning of that digest, not machine bookkeeping.
6. `ready`: enter only after exact validation, self-review, and user
   confirmation of the current digest. Name the eligible downstream consumer;
   do not invoke it automatically.
7. `consumed`: require downstream evidence binding the consumer artifact to the
   source contract and review digest.
8. `closed`: explicit terminal state for completed or abandoned discussions;
   archive only after a terminal transition.

For UI-facing requirements, `ui_discussion_status` is orthogonal to lifecycle.
After functional direction is stable, offer an optional UI and interaction
discussion only when no explicit handoff request is active. If UI decisions block readiness,
remain in `decide` or `prepare`; do not invent a separate primary stage.

If a discussion is mature enough for specification but lacks ready canonical `handoff-to-specify.json`, close the turn with handoff assessment, draft review, or repair guidance inside `sp-discussion`. Do not tell the user their next sentence should be `sp-specify`, and do not send `specification-input.md` to `sp-specify` as a fallback.

## Quality And Closeout

Handoff-ready closeout covers the handoff goal, selected direction, target boundary, Must-Preserve coverage, hard unknown and conflict counts, quality gate state, source-contract integrity, and exact downstream consumption path.

Do not close with only file paths, status counters, or a next command. Keep ready-summary quality checks internal until the visible reply translates them into decision-level meaning.

`sp-discussion` does not create P0/P1/P2 sequences, migration phases, release batches, task packets, ordered implementation steps, source edits, test fixes, release execution, or package publishing. Those belong downstream.

When the user rejects fallback/dual-stack/old implementation fallback language, preserve the no alternate product path decision unless the user later reopens it.

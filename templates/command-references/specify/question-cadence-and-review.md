Trigger: before asking requirement-shaping questions or routing the user to the next command.

Purpose: preserve user review, next-command selection, and checkpoint wording behavior.

Preserved Contract: user review remains mandatory and only the user review gate decides the canonical next command.

## User Review Gate

- Ask the user to review the written artifact set before planning.
- Present a current-understanding summary as a misunderstanding-correction gate and ask the user to confirm or correct the current understanding before the final handoff decision is locked.
- Summarize what was confirmed, what remains open, what was deferred or dropped, and what risk remains.
- Use the user's current language for the review summary and cover Business Goals, Users & Roles, confirmed product scope, user-confirmed delivery sequence, business rules, Technical Constraints / Assumptions, confirmed decisions, and Outstanding Questions.
- If the user requests artifact edits, stay in `sp-specify`, update the artifacts, and repeat artifact self-review.
- Recommend exactly one next command:
  - `/sp.plan` when the artifact package is `Aligned: ready for plan`.
  - `/sp.clarify` when planning-critical ambiguity remains.
  - `/sp.deep-research` when requirements are clear enough but feasibility, external evidence, or an implementation-chain proof is still needed.
- Do not present multiple next commands as equally valid.
- No alternative next command is valid for the current state.
- report the single valid next path for the current state. Do not emit a second alternative next command. Do not present multiple downstream command options.
- Only the user review gate may decide whether the canonical next command is `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.
- The completion state must preserve the literal `next_command` as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`.
- After the feature package is written, self-reviewed, and `workflow-state.md` records the single next command, mark the source discussion consumed when this run came from `sp-discussion`: run `specify discussion mark-consumed <slug> --feature-dir "$FEATURE_DIR"` where `<slug>` is derived from `.specify/discussions/<slug>/handoff-to-specify.md`. This writes `handoff_consumption_status: consumed`, `consumed_by_feature_dir: $FEATURE_DIR`, `status: completed`, and `next_command: none` in the source `discussion-state.md`, preventing stale `handoff-ready` discussions from blocking future `sp-auto` routing. If the helper command is unavailable, update those same fields manually and note the fallback in the completion report. Do not mark consumed before the artifacts exist and pass self-review.

## Completion Report

Report completion in the user's current language while preserving literal paths, command names, and fixed status values.

Include:
- branch name
- `spec.md` path
- `alignment.md` path
- `context.md` path
- `references.md` path when created
- `workflow-state.md` path
- `checklists/requirements.md` path
- `brainstorming/handoff-to-specify.json` path
- source-file sweep status
- source-signal disposition status
- readiness decision
- single next command
- cognition follow-up for artifact-only advisory state, if relevant

Trigger: when deciding whether to write discussion files or preserve compaction state.

Purpose: preserve frontstage/backstage separation, checkpoint persistence, semantic checkpoints, save triggers, and recovery persistence rules.

Preserved Contract: Migrated from `templates/commands/discussion.md`; this file preserves existing `sp-discussion` behavior and does not define new workflow behavior.

## Semantic Checkpoints

Refresh canonical state and optional structured files only at semantic checkpoints. A semantic checkpoint is a durable meaning change that affects the discussion's future course; it is not every user response, acknowledgement, minor preference, low-risk clarification, answer to a low-risk follow-up, or elapsed turn count.

- user confirms a goal, non-goal, scope boundary, or important product decision that changes the discussion compass, target boundary, recommendation, handoff readiness, blocking unknowns, or downstream contract
- discussion stage changes, such as product framing to technical options
- project evidence materially changes the understanding of the request
- a code fact was proven and must survive compaction
- evidence conflict is found
- truth pass status changes
- the discussion compass becomes stale or a recommendation changes materially
- user-triggered checkpoint/save confirms the current discussion point should become durable, including `checkpoint`, `save checkpoint`, `checkpoint, continue`, or localized equivalents that pair checkpoint with continue
- the user asks for handoff or next-stage continuation
- context compaction risk is high
- an old discussion is resumed and compact state is missing or stale

Checkpoint triggers do not refresh all files. Refresh only the targets whose durable meaning changed:

- discussion-state.md: short current summary, stage, confirmed decisions, open questions, boundary status, latest evidence route, truth pass status, advice confidence, discussion compass, and current question pack.
- requirements.md only when product requirements have changed enough to matter.
- technical-options.md only when options are introduced, revised, selected, or rejected.
- project-context.md only when source-grounding evidence, truth-pass evidence, assumptions, advice confidence, or cognition coverage changes.
- open-questions.md only when blocking or soft unknowns materially change.

## Checkpoint Prompting

Do not persist only because an unsaved turn count changed. Recovery value and semantic change, not a hidden counter, determine whether a checkpoint is useful.

At a natural pause or after several unsaved ordinary turns, the visible reply may end with one short note that names the unsaved turn count and suggests `checkpoint, continue` if the user wants to save progress and keep going. This note is not a receipt, does not expose file paths by default, and must not call write-capable tools.

When the user says `checkpoint, continue` or an equivalent checkpoint-plus-continue phrase, append one compact event to `discussion-log.jsonl`, update canonical `discussion-state.json`, render the short compatibility Markdown, refresh only semantically changed optional artifacts, and continue with the next useful discussion content in the same reply. Do not stop after a save receipt or ask for permission to continue.

## Recovery Flow

When resuming a discussion, use `specify discussion resume <slug> --json` to receive the compact `DiscussionTurnPacket` and post-checkpoint events. Read canonical `discussion-state.json` directly only for recovery or diagnostics. Read `requirements.md`, `technical-options.md`, `project-context.md`, or `open-questions.md` only when the turn packet references them, is stale, is missing, or conflicts with recent events.

## Frontstage / Backstage Separation

Keep frontstage and backstage separate.

- Frontstage is the visible conversation. It should feel like expert collaborative thinking, not like a workflow status terminal.
- Backstage is state accounting backstage. It tracks open questions, stable decisions, Must-Preserve items, evidence, dirty artifacts, flush reasons, and handoff readiness. Backstage tracking is memory-first between save triggers: do not write local files, counters, dirty markers, or receipts merely because the user replied. Do not surface backstage details unless they change the user's decision, the user asks for state, a save or handoff needs review, or recovery is needed.

Use checkpoint persistence: do not persist every turn. Ordinary replies should keep state accounting backstage and continue the visible conversation without a visible save receipt. Surface file paths and state updates only when the user needs review, recovery, verification, state visibility, or a durable lifecycle handoff.

Trigger: before processing a checkpoint prefix, shaping any discussion reply footer, or deciding whether to write discussion files or preserve compaction state.

Purpose: preserve frontstage/backstage separation, checkpoint persistence, semantic checkpoints, save triggers, and recovery persistence rules.

Preserved Contract: Migrated from `templates/commands/discussion.md`; this file preserves existing `sp-discussion` behavior and does not define new workflow behavior.

## Semantic Checkpoints

Original-source snapshots and unit-delivery progress use the specialized
`discussion import-material` / `discussion read-material` owners from
[source-material-consumption.md](source-material-consumption.md). These are
necessary `evidence-handoff` events, not an ordinary per-reply persistence loop.
Checkpoint only semantic interpretation: complete `unit_dispositions` and
`requirements_snapshot.source_requirements` with stable IDs and source refs.
Never author runtime `reading`, delivered receipts, or inspected status.

Refresh canonical state and optional structured files only at semantic checkpoints. A semantic checkpoint is a durable meaning change that affects the discussion's future course; it is not every user response, acknowledgement, minor preference, low-risk clarification, answer to a low-risk follow-up, or elapsed turn count.

- user confirms a goal, non-goal, scope boundary, or important product decision that changes the discussion compass, target boundary, recommendation, handoff readiness, blocking unknowns, or downstream contract
- discussion stage changes, such as product framing to technical options
- project evidence materially changes the understanding of the request
- a code fact was proven and must survive compaction
- evidence conflict is found
- truth pass status changes
- the discussion compass becomes stale or a recommendation changes materially
- user-triggered checkpoint/save confirms the current discussion point should become durable, including an optional leading `checkpoint` prefix before ordinary discussion text, `checkpoint` alone, `save checkpoint`, `checkpoint, continue`, or clear localized save requests
- the user asks for handoff or next-stage continuation
- context compaction risk is high
- an old discussion is resumed and compact state is missing or stale

Checkpoint triggers do not refresh all files. Refresh only the targets whose durable meaning changed:

- discussion-state.md: short current summary, stage, confirmed decisions, open questions, boundary status, latest evidence route, truth pass status, advice confidence, discussion compass, and current question pack.
- requirements.md only when product requirements have changed enough to matter.
- technical-options.md only when options are introduced, revised, selected, or rejected.
- project-context.md only when source-grounding evidence, truth-pass evidence, assumptions, advice confidence, or cognition coverage changes.
- open-questions.md only when blocking or soft unknowns materially change.

The canonical `discussion-state.json` checkpoint is a complete current semantic
snapshot, not merely the visible summary. It carries `requirements_snapshot`,
implementation target, source evidence, every in-scope user-provided
`source_materials` record, unknowns/conflicts, downstream instructions, decision
digest, Must-Preserve obligations, Truth Pass/compass/UI state, and artifact
references. The compact event log stores only the summary, changed fields, and
snapshot digest.

## Checkpoint Prompting

Do not persist only because an unsaved turn count changed. Recovery value and semantic change, not a hidden counter, determine whether a checkpoint is useful.

Show one short reminder in the user's language only on active discussion turns
whose next user message may continue ordinary discussion, including brief
acknowledgements and replies that already performed a save while the discussion
remains active.
For Chinese, use: "需要保存讨论进度时，可在下一条回复前加 `checkpoint`。"
Do not ask the user to choose whether to save, wait for an answer, show an
unsaved-turn count, or turn the footer into a separate confirmation stage.
The prompt does not write files by itself. Its frequency does not change any
semantic, evidence, compaction, handoff, or lifecycle save trigger.

Suppress the reminder during handoff assessment or consumer-route selection,
draft handoff review or exact digest confirmation, handoff confirmation or
mark-ready, and `handoff-ready` closeout or downstream invocation. Those replies
already request one dedicated handoff action and must not append an unrelated
discussion-save prompt.

Treat an explicit optional leading `checkpoint` prefix as a save modifier.
Separate the prefix from the discussion body; no `continue` keyword or extra
confirmation is required. Whitespace or punctuation can separate the prefix
from normal prose. Quoted text, code, or a question about checkpoint is not a
save request; honor an explicit request not to save.

| User message | Save action | Discussion action |
| --- | --- | --- |
| `这个方案的成本怎么算？` | No explicit save request | Answer the cost question normally |
| `checkpoint，这个方案的成本怎么算？` | Save prior pending progress first | Answer the same cost question normally |
| `checkpoint` | Save prior pending progress | Briefly acknowledge the actual result; keep discussion available |
| `这里的 checkpoint 是什么意思？` | No explicit save request | Explain the term normally |

After resolving the current session, save prior pending progress first, then
answer the body normally in the same visible reply. The saved boundary excludes
the new body until that body is processed. For a later write in the same turn,
obtain a fresh resolver hash rather than reusing the pre-checkpoint hash.
Classify the body and apply topic
ownership independently; the prefix is not a topic, consumer choice, handoff
approval, or permission to widen scope. Without the prefix, continue normally
unless another existing save trigger fires. Preserve standalone and legacy
explicit save requests, including `save checkpoint` and `checkpoint, continue`.

For the save, pass the compact semantic delta through the exact rendered command
`{{specify-subcmd:specify-runtime discussion checkpoint <slug> --expected-state-sha256 <state_sha256> --input-json - --format json}}`.
Use the exact rendered project-local runtime launcher at the start of that
command. Never prepend or synthesize a drive letter, rebuild the launcher from
the current directory, or replace it with an absolute path guessed by the
agent. Run it from the project root. On Windows PowerShell, keep the payload in
memory and pipe it to the command's stdin with `--input-json -`; do not place a
PowerShell here-string directly after `--input-json`, and do not create a
temporary authoring file only for transport.

The payload may include `summary`, `lifecycle_phase`/`phase`, `user_goal`,
`context_boundary`, `confirmed_decisions`, `open_questions`,
`current_recommendation`, `requirements_snapshot`, implementation target,
source evidence/materials, unknowns/conflicts, downstream instructions,
decision digest, Must-Preserve obligations, Truth Pass/compass/UI state,
artifact refs, and the other accepted turn_packet fields. Every user-provided
document, screenshot, recording, pasted note, or link that shapes the current
topic uses a stable `MAT-###` material record; restricted content stores only a
safe locator and sanitized summary. Before the
first checkpoint payload in a session, or whenever the field shape is uncertain,
expand the live schema with
`{{specify-subcmd:specify-runtime api schema discussion-checkpoint-input --format json}}`
and obey it exactly instead of guessing object shapes. The runtime persists
accepted fields into `discussion-state.json` / `turn_packet` and appends
`discussion-log.jsonl`; unknown fields are rejected instead of silently
dropped. Never mutate those files directly.

If saving fails, no durable checkpoint exists. Do not dismiss the failure as
harmless, claim it was saved, or cross a semantic, handoff, or lifecycle boundary
that depends on the checkpoint. Retain pending progress in memory and perform
one typed recovery before replying: for a path or executable lookup failure,
retry the exact rendered launcher from the project root without varying path
syntax; for invalid input, inspect returned `show_argv` or the live
`discussion-checkpoint-input` schema and retry the corrected payload; for stale
state, execute the returned slug-bound `next_argv`/resolve action and retry with
its fresh digest. If that contract-correct retry still fails, report the save as
pending with the exact blocker. A standalone `checkpoint` has no discussion body
to continue, so stop there. With a prefixed ordinary body, only safe discussion
that does not depend on the missing durable transition may continue, and the
reply must keep the checkpoint visibly pending. A missing or ambiguous session
still requires the existing identity guard before any durable write.

## Recovery Flow

When resuming, use `specify-runtime discussion resume` for the compact packet. Query canonical state and optional views only through `specify-runtime artifact show`, and only for recovery, a referenced stale field, or a conflict.

## Frontstage / Backstage Separation

Keep frontstage and backstage separate.

- Frontstage is the visible conversation. It should feel like expert collaborative thinking, not like a workflow status terminal.
- Backstage is state accounting backstage. It tracks open questions, stable decisions, Must-Preserve items, evidence, dirty artifacts, flush reasons, and handoff readiness. Backstage tracking is memory-first between save triggers: do not write local files, counters, dirty markers, or receipts merely because the user replied. Do not surface backstage details unless they change the user's decision, the user asks for state, a save or handoff needs review, or recovery is needed.

Use checkpoint persistence: do not persist every turn. Ordinary replies should keep state accounting backstage and continue the visible conversation without a visible save receipt. Surface file paths and state updates only when the user needs review, recovery, verification, state visibility, or a durable lifecycle handoff.

{{spec-kit-include: ../common/user-input.md}}

## Objective

Drive a resumable product and technical discussion that locks context boundaries, matures a rough idea into requirements and implementation options, and produces one reviewed handoff contract before formal specification.

## Context

- Primary inputs: the user's idea, the current discussion session under `.specify/discussions/<slug>/`, passive project memory, boundary evidence, and project cognition only when the discussion reaches source-grounded technical judgment.
- `discussion-state.json` is the canonical typed session state. `discussion-state.md` is a short derived compatibility view, and `discussion-log.jsonl` contains compact semantic events rather than transcript prose.
- `sp-discussion` is upstream of `sp-specify`; it does not create feature branches or write formal feature artifacts.
- The final handoff is an agent-only `handoff-to-specify.json` contract. Human review is presented in the visible reply and bound to the contract's protected revision; no persisted Markdown handoff is produced.

## Human Frontstage and Agent Backstage

- Human frontstage is written from the human's point of view and optimizes for a clear decision, useful reasoning, and a natural next move.
- Agent backstage uses the typed `DiscussionTurnPacket` and canonical discussion state to optimize resume, validation, persistence, and handoff efficiency.
- Do not expose typed state or machine bookkeeping in a normal human reply. Translate backstage facts into the decision-level meaning the user needs.

## Process

- Create or resume the discussion session.
- Run the Context Boundary Gate before project-specific technical options, affected-file claims, implementation-path claims, or handoff generation.
- Use project cognition as advisory navigation only when current-project facts matter; use `--intent discussion`, read returned `minimal_live_reads`, and prove technical claims from live repository files.
- Complete a Truth Pass before source-grounded technical advice, affected-surface claims, implementation-path recommendations, or testing strategy claims tied to existing code; keep `verified_project_facts`, `open_assumptions`, `evidence_checked`, and `advice_confidence` as pending truth-pass state and persist them only at the next semantic checkpoint or save trigger.
- Keep the discussion responsibility boundary strict: confirm goal, boundary, scope, non-goals, constraints, evidence, trade-offs, user-owned decisions, and handoff readiness. Do not split work into P0/P1/P2, migration phases, release batches, sprints, task packets, or ordered implementation steps; those belong to `sp-plan`, `sp-tasks`, or `sp-implement`.
- If the user rejects fallback, backup plans, dual-stack operation, or old-implementation fallback, record that as no parallel old-backend operation, no old-stack cutover fallback, and no alternate product path. Do not turn it into a new discussion question about database snapshots, restore mechanics, rollback scripts, or other data-safety mechanisms; those are downstream planning and implementation safety constraints, not product fallback options.
- Use one high-throughput collaborative brief for all substantive turns: lead with the recommended direction, a plain-language reason, enough concrete detail to be useful, and the next useful move. The agent controls headings, order, and detail level; do not choose among named answer templates or fixed cards.
- Apply frontstage / backstage separation. Frontstage is the visible conversation; backstage is state accounting backstage for open questions, decisions, Must-Preserve items, evidence, dirty artifacts, flush reasons, and handoff readiness. Backstage tracking is memory-first between save triggers; do not write files, counters, dirty markers, or receipts merely because the user replied.
- Apply the frontstage reply gate before substantive replies: do not answer with only a state receipt, status receipt, file paths, status fields, OQ IDs, persistence notes, or updated-artifact lists.
- Use Recommendation-First Decision Progression: when evidence and user intent support a safe default, continue by default, state the recommended choice directly, give the reason, and move to the next useful decision instead of ending on a bare "should we?" question.
- Recommendation-first is not questionless: ask only when user judgment is genuinely required and no safe default exists. The question must include the recommended default and meaningful override options.
- Apply the Next-Step Content Rule: when recommending a default next step, include concrete content for the recommended next step in the same visible reply, such as a first-pass draft, option board, readiness checklist, handoff assessment verdict, evidence plan, or field-by-field responsibility audit table.
- For readiness summary, include the locked direction, why it is not done, blocked decisions, evidence gaps, downstream planning inputs to preserve, safe default discussion action, and override path.
- For pre-handoff readiness, include the likely verdict, proposed handoff goal, recommended consumer, package scope, excluded scope, readiness checks, default next action, and override path, without writing or claiming `handoff-assessment.md`.
- Track lifecycle state at semantic checkpoints, but do not track or expose reply-template selection.
- Maintain a Discussion Compass in active memory during ordinary turns, and persist it to `discussion-state.md` only at semantic checkpoints or save triggers, so long conversations preserve what is being solved, what is confirmed, what changed, what remains undecided, the current recommendation, and the next useful decision.
- Apply the Anti-Toothpaste Protocol: show the broader decision map, recommend a next path, and ask only when user judgment is genuinely required and no safe default exists.
- Classify each user turn before asking a question.
- Run the Question Evidence Gate before asking the user; answer repository-discoverable facts from live evidence.
- Use an Adaptive Question Pack: ask one required primary question, and optionally add up to two same-topic follow-ups only when the topic is local and low risk.
- Fall back to exactly one question for boundary gaps, evidence conflicts, cross-project targets, handoff readiness, destructive or lifecycle consequences, security or data-risk consequences, and major product trade-offs.
- Put a recommended option and short reason on multiple-choice questions.
- Use checkpoint persistence with explicit persistence modes. Default ordinary replies, acknowledgements, low-risk preference answers, and small clarifications to `frontstage-only`: behave like `sp-ask`, keep backstage state in active memory, and do not write local files, counters, dirty markers, receipts, or status summaries even when a discussion package already exists. Use `durable-checkpoint`, `evidence-handoff`, or `lifecycle-transition` only when a semantic checkpoint, user-triggered checkpoint/save, high compaction risk, delegated evidence consumer, handoff, resume repair, or durable lifecycle transition actually requires a compact write. Suggest `checkpoint, continue` only when recovery value justifies it; turn count alone is never a save trigger.
- A user reply is not itself a save trigger. Plain confirmations such as "yes", "ok", "continue", or localized equivalents remain `frontstage-only` unless they approve a named checkpoint, save, handoff, or lifecycle transition.
- Treat `checkpoint`, `save checkpoint`, `checkpoint, continue`, and localized equivalents that pair checkpoint with continue as user-triggered save requests. When the user asks to continue in the same phrase, write one compact JSONL event and refresh canonical typed state first, update only semantically changed optional artifacts, and then continue with useful discussion content in the same visible reply instead of stopping at a save receipt.
- Do not use native hook events as a per-turn persistence loop. Hooks may surface resume or compaction reminders, but `sp-discussion` writes discussion files only after its own save trigger fires.
- Keep ordinary persistence details backstage. Surface file paths and state updates only when the user needs review, recovery, verification, state visibility, or a durable lifecycle handoff.
- Do not ask for continuation, permission to proceed, or agreement with a reversible safe recommendation. Continue by default and include the override path when one exists.
- Refresh `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` only at semantic checkpoints. A semantic checkpoint is a durable meaning change, not every user response, acknowledgement, low-risk clarification, low-risk preference answer, or elapsed turn count.
- If the user asks to transfer functionality into another project, lock `target_project_root` immediately before technicalizing.
- When the user explicitly asks to hand off or continue the next stage, write `handoff-assessment.md` first and decide `ready-for-handoff` or `continue-discussion`.
- Before that explicit lifecycle request, do not answer with only "next I recommend handoff assessment"; provide a pre-handoff readiness preview with concrete assessment content.
- After functional discussion is stable and when no explicit handoff request is active, offer an optional UI and interaction discussion for UI-facing requirements; keep `ui_discussion_status` and confirmed or deferred UI decisions in active memory until the next semantic checkpoint or save trigger; the UI pass is not a mandatory handoff gate.
- If explicit handoff is already requested, run handoff assessment first and return to UI discussion only when UI decisions block readiness or the user reopens UI discussion.
- If the direction is coherent and boundary-locked after explicit handoff request, write exactly one draft agent-only contract: `handoff-to-specify.json`.
- If the direction is too broad to express as one coherent package, continue the discussion instead of writing candidate-specific handoff files.
- Run handoff self-review and require user confirmation before marking `handoff-ready`.
- Until the handoff JSON exists, self-review passes, and `quality_gate.status` records user confirmation, keep the visible next step inside `sp-discussion`: handoff assessment, draft handoff review, or handoff repair. Do not tell the user their next sentence should be `sp-specify`, do not tell them to run or enter `sp-specify`, and do not offer `specification-input.md` as a substitute handoff.
- After writing and self-reviewing a draft contract, ask for user review with the unified frontstage contract: decision requested, recommended route, scope to approve, excluded scope, readiness checks, contract path, and allowed approval/change-request responses. The agent chooses visible labels.
- If handoff review returns `request-changes` or a downstream consumer reports `blocked_by_handoff_integrity`, repair the handoff in `sp-discussion`: update canonical `handoff-to-specify.json`, synchronize protected facts and `source_evidence`, require `version`, `status`, `entry_source: sp-discussion`, `source_contract`, `planning_gate_status`, `coverage_status`, `hard_unknown_count`, `open_conflict_count`, `quality_gate`, `review_digest`, and consumer fields, rerun self-review, then ask the user to approve the current digest. Do not make `sp-specify` or `sp-quick` reconstruct or patch the contract.
- When senior consequence analysis triggers, preserve `CA-###` obligations, affected objects, lifecycle states, dependency impact, recovery/validation needs, coverage gaps, and stop-and-reopen conditions in the unified handoff contract.

## Output Contract

- Maintain the independent discussion state and artifacts under `.specify/discussions/<slug>/`.
- Treat `handoff-ready` as resumable until `sp-specify` consumes it or the user confirms the topic should be dropped; after consumption, mark it with `specify discussion mark-consumed <slug> --feature-dir <feature-dir>` before archiving.
- Provide 2-3 project-grounded technical options only after the relevant boundary is locked.
- Report unresolved questions honestly instead of forcing planning readiness.
- Distinguish verified project facts from open assumptions before presenting technical options.
- Keep the current discussion compass fresh at semantic checkpoints.
- Replies must be frontstage-readable before backstage-complete: start with the recommended direction, plain-language reason, concrete judgment or readiness checklist, default next step, and override path when useful. Do not use mandatory visible headings or fixed card labels.
- Do not end with only a promise to do the next step; produce the safe first-pass content now. If the next step is blocked, state the blocker and provide the smallest useful partial draft, checklist, or evidence plan.
- When direction is locked but the discussion is not handoff-ready, include a readiness summary instead of a state receipt; do not ask the user to say next when a safe default discussion action exists.
- Write one `handoff-to-specify.json` draft contract; it becomes handoff-ready only after self-review and user confirmation of its current digest.
- Do not write separate split planning artifacts or candidate-specific handoff files.
- When explicit handoff is requested, include `handoff_goal`, `context_boundary`, `implementation_target`, `source_evidence`, `blocking_unknowns`, `downstream_instructions`, `quality_gate`, and a Must-Preserve Ledger.
- Request-changes repair is an upstream discussion responsibility: keep the discussion in draft/user-review state, refresh the canonical JSON contract, carry forward soft unknowns with owner/latest resolve phase/stop-and-reopen condition or waive them as non-blocking assumptions, and resubmit for review.
- Do not present draft handoff review as a path receipt or artifact-write log; the visible reply must summarize the decision, recommended route, approved scope, excluded scope, checks, contract path, and allowed review responses.
- When a handoff becomes `handoff-ready`, use a concise visible reply that covers the handoff goal, selected direction, target boundary, Must-Preserve coverage, readiness, contract path, and next consumption path; do not close with only file paths, status counters, or a next command. Keep ready-summary quality checks internal instead of showing them as primary headings.
- Before `handoff-ready`, do not describe the next consumption path as a user-invoked `sp-specify` command. The safe default next action is still `sp-discussion` handoff assessment, review, or repair.
- Do not mark handoff ready if role objects, target path context, evidence provenance, self-review status, user confirmation, or blocking unknown handling is missing.
- Preserve `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` for the downstream fidelity gate.
- For UI-facing work, preserve `ui_discussion_status`; confirmed UI decisions; deferred UI unknowns; and Markdown-carried ASCII sketches with JSON fields `ui_sketches_present`, `ui_sketch_summary`, and `ui_sketch_reference`.

## Guardrails

- Do not edit source code or tests.
- Do not create feature branches or feature directories.
- Do not automatically invoke or route into `sp-specify`.
- Do not make project-specific technical claims before the Context Boundary Gate, staged cognition gate, and Truth Pass are complete.
- Do not use current project cognition to prove another project's implementation facts.

{{spec-kit-include: ../common/read-only-evidence-lanes.md}}

For `sp-discussion`, read-only evidence lanes may support boundary locking, Truth Pass evidence, affected-surface checks, option evidence, or consequence mapping. Use `choose_evidence_lane_dispatch(command_name="discussion", snapshot, workload_shape)` only after the discussion question has a safe read-only evidence lane contract. The leader owns product judgment, recommendation, handoff assessment, and `handoff-ready` status.

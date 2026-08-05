{{spec-kit-include: ../common/user-input.md}}

## Objective

Drive a resumable product and technical discussion that locks context boundaries, matures a rough idea into requirements and implementation options, and produces one reviewed handoff contract before direct Quick delivery or formal specification.

## Context

- Primary inputs: the user's idea, the selected session returned by `specify-runtime discussion resume <slug> --format json`, passive project memory through its CLI, boundary evidence, and project cognition only when the discussion reaches source-grounded technical judgment. Never inspect the session directory directly.
- `discussion-state.json` is the canonical typed session state. `discussion-state.md` is a short derived compatibility view, and `discussion-log.jsonl` contains compact semantic events rather than transcript prose.
- `sp-discussion` is upstream of `sp-quick` direct delivery and `sp-specify` formalization; it does not create implementation or formal feature artifacts.
- The final handoff is an agent-only `handoff-to-specify.json` contract. Human review is presented in the visible reply and bound to the contract's protected revision; no persisted Markdown handoff is produced.
- Do not treat an already-active discussion as a new automatic workflow entry. Topical follow-ups continue the invoked discussion even when the user does not repeat the workflow name.

## Human Frontstage and Agent Backstage

- Human frontstage is written from the human's point of view and optimizes for a clear decision, useful reasoning, and a natural next move.
- Agent backstage uses the typed `DiscussionTurnPacket` and canonical discussion state to optimize resume, validation, persistence, and handoff efficiency.
- Do not expose typed state or machine bookkeeping in a normal human reply. Translate backstage facts into the decision-level meaning the user needs.

## Process

- Create or resume the discussion session.
- Run the Context Boundary Gate before project-specific technical options, affected-file claims, implementation-path claims, or handoff generation.
- Use project cognition as advisory navigation only when current-project facts matter; use `--intent discussion`, read returned `minimal_live_reads`, and prove technical claims from live repository files.
- Complete a Truth Pass before source-grounded technical advice, affected-surface claims, implementation-path recommendations, or testing strategy claims tied to existing code; keep `verified_project_facts`, `open_assumptions`, `evidence_checked`, and `advice_confidence` as pending truth-pass state and persist them only at the next semantic checkpoint or save trigger.
- Keep the discussion responsibility boundary strict: confirm goal, boundary, scope, non-goals, constraints, evidence, trade-offs, user-owned decisions, and handoff readiness. Do not split work into P0/P1/P2, migration phases, release batches, sprints, task packets, or ordered implementation steps; those belong to `sp-quick` task-local planning when Quick is selected, or to `sp-plan`, `sp-tasks`, and `sp-implement` on the formal feature path.
- If the user rejects fallback, backup plans, dual-stack operation, or old-implementation fallback, record that as no parallel old-backend operation, no old-stack cutover fallback, and no alternate product path. Do not turn it into a new discussion question about database snapshots, restore mechanics, rollback scripts, or other data-safety mechanisms; those are downstream planning and implementation safety constraints, not product fallback options.
- Use one high-throughput collaborative brief for all substantive turns: lead with the recommended direction, a plain-language reason, enough concrete detail to be useful, and the next useful move. The agent controls headings, order, and detail level; do not choose among named answer templates or fixed cards.
- Apply frontstage / backstage separation. Frontstage is the visible conversation; backstage is state accounting backstage for open questions, decisions, Must-Preserve items, evidence, dirty artifacts, flush reasons, and handoff readiness. Backstage tracking is memory-first between save triggers; do not write files, counters, dirty markers, or receipts merely because the user replied.
- Apply the frontstage reply gate before substantive replies: do not answer with only a state receipt, status receipt, file paths, status fields, OQ IDs, persistence notes, or updated-artifact lists.
- Use Recommendation-First Decision Progression: when evidence and user intent support a safe default, continue by default, state the recommended choice directly, give the reason, and move to the next useful decision instead of ending on a bare "should we?" question.
- Recommendation-first is not questionless: ask only when user judgment is genuinely required and no safe default exists. The question must include the recommended default and meaningful override options.
- Apply the Next-Step Content Rule: when recommending a default next step, include concrete content for the recommended next step in the same visible reply, such as a first-pass draft, option board, readiness checklist, handoff assessment verdict, evidence plan, or field-by-field responsibility audit table.
- For readiness summary, include the locked direction, why it is not done, blocked decisions, evidence gaps, downstream planning inputs to preserve, safe default discussion action, and override path.
- For pre-handoff readiness, include the likely verdict, proposed handoff goal, both paths and their eligibility, a complexity-informed recommendation among eligible paths, package scope, excluded scope, readiness checks, and one user-owned route choice without creating a separate assessment artifact.
- Present both paths and their eligibility before drafting: `sp-quick` for direct execution with task-local planning and `sp-specify` for the formal specification-first pipeline; explain any blocker on an ineligible path. Base the recommendation on delivery complexity and consequence profile, not raw size alone: recommend Quick for bounded, well-understood work with stable requirements and limited cross-boundary risk; recommend Specify for high-complexity or ambiguous work, interacting capabilities or systems, architecture/data migration/security/compliance/rollout concerns, broad acceptance obligations, or durable traceability needs. Task size alone is not a hard routing ceiling. The user owns the final consumer choice and may choose either eligible path against the recommendation.
- Track lifecycle state at semantic checkpoints, but do not track or expose reply-template selection.
- Maintain a Discussion Compass in active memory during ordinary turns, and submit it to `specify-runtime discussion checkpoint` only at semantic checkpoints or save triggers; that command owns `discussion-state.md` and companion state.
- Apply the Anti-Toothpaste Protocol: show the broader decision map, recommend a next path, and ask only when user judgment is genuinely required and no safe default exists.
- Classify each user turn before asking a question.
- Run the Question Evidence Gate before asking the user; answer repository-discoverable facts from live evidence.
- Use an Adaptive Question Pack: ask one required primary question, and optionally add up to two same-topic follow-ups only when the topic is local and low risk.
- Fall back to exactly one question for boundary gaps, evidence conflicts, cross-project targets, handoff readiness, destructive or lifecycle consequences, security or data-risk consequences, and major product trade-offs.
- Put a recommended option and short reason on multiple-choice questions.
- Use checkpoint persistence with explicit persistence modes. Default ordinary replies, acknowledgements, low-risk preference answers, and small clarifications to `frontstage-only`: behave like `sp-ask`, keep backstage state in active memory, and do not write local files, counters, dirty markers, receipts, or status summaries even when a discussion package already exists. Use `durable-checkpoint`, `evidence-handoff`, or `lifecycle-transition` only when a semantic checkpoint, user-triggered checkpoint/save, high compaction risk, delegated evidence consumer, handoff, resume repair, or durable lifecycle transition actually requires a compact write. Suggest `checkpoint, continue` only when recovery value justifies it; turn count alone is never a save trigger.
- A user reply is not itself a save trigger. A contextual confirmation such as `yes`, `ok`, or `可以` inherits the immediately preceding named decision: it selects the recommended consumer only when the visible request explicitly asked the user to choose between both eligible routes, and it approves readiness only when the visible review named the exact digest and selected consumer; otherwise it remains an ordinary decision confirmation and cannot authorize `sp-quick` or `sp-specify` consumption.
- Treat `checkpoint`, `save checkpoint`, `checkpoint, continue`, and localized equivalents that pair checkpoint with continue as user-triggered save requests. When the user asks to continue in the same phrase, pass one compact semantic event to `specify-runtime discussion checkpoint`; let that CLI append JSONL and refresh canonical typed state, update semantically changed optional views only through their registered artifact owners, and then continue with useful discussion content in the same visible reply instead of stopping at a save receipt.
- A summary-only checkpoint is valid only for an explicit savepoint with no
  semantic change. When meaning changed since the last durable state, submit
  every changed semantic field needed to preserve current truth, especially
  confirmed decisions, the context boundary, the current recommendation, and
  open assumptions. Do not report checkpoint success while leaving newly
  confirmed decisions only in chat memory.
- Do not use native hook events as a per-turn persistence loop. Hooks may surface resume or compaction reminders, but `sp-discussion` writes discussion files only after its own save trigger fires.
- Keep ordinary persistence details backstage. Surface file paths and state updates only when the user needs review, recovery, verification, state visibility, or a durable lifecycle handoff.
- Do not ask for continuation, permission to proceed, or agreement with a reversible safe recommendation. Continue by default and include the override path when one exists.
- Refresh optional discussion views only through their registered artifact owner at semantic checkpoints; this includes `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md`.
- If the user asks to transfer functionality into another project, lock `target_project_root` immediately before technicalizing.
- When the user explicitly asks to hand off or continue the next stage, assess `ready-for-contract`, `continue-discussion`, or `blocked` in memory and persist the result through canonical state or the single JSON contract; do not create a duplicate assessment document.
- Before that explicit lifecycle request, do not answer with only "next I recommend handoff assessment"; provide a pre-handoff readiness preview with concrete assessment content.
- After functional discussion is stable and when no explicit handoff request is active, offer an optional UI and interaction discussion for UI-facing requirements; keep `ui_discussion_status` and confirmed or deferred UI decisions in active memory until the next semantic checkpoint or save trigger; the UI pass is not a mandatory handoff gate.
- If explicit handoff is already requested, run handoff assessment first and return to UI discussion only when UI decisions block readiness or the user reopens UI discussion.
- If the direction is coherent and boundary-locked after explicit handoff request, present both paths with their eligibility and the complexity-informed recommendation among eligible paths, then obtain the user's final consumer choice. Do not call `specify-runtime discussion write-handoff` until the user has selected an eligible consumer; then submit exactly one draft contract with `recommended_consumer` recording that confirmed selection. The runtime owns `handoff-to-specify.json`.
- If the direction is too broad to express as one coherent package, continue the discussion instead of writing candidate-specific handoff files.
- Run `{{specify-subcmd:specify-runtime discussion validate-handoff <slug> --mode draft --json}}` after writing and self-reviewing the draft. Present its exact digest for named user confirmation, then record that approval with `{{specify-subcmd:specify-runtime discussion confirm-handoff <slug> --digest <review-digest> --json}}` before `{{specify-subcmd:specify-runtime discussion mark-ready <slug> --json}}`.
- Until the handoff JSON exists, self-review passes, and `quality_gate.status` records user confirmation of the protected revision and selected consumer, keep the visible next step inside `sp-discussion`: handoff assessment, draft handoff review, or handoff repair. Do not tell the user to run or enter `sp-quick` or `sp-specify`, and do not offer `specification-input.md` as a substitute handoff.
- After writing and self-reviewing a draft contract, ask for user review with the unified frontstage contract: decision requested, selected route, scope to approve, excluded scope, readiness checks, contract path, and allowed approval/change-request responses. The agent chooses visible labels.
- If review requests changes or a consumer reports `blocked_by_handoff_integrity`, resubmit the corrected semantic contract through `specify-runtime discussion write-handoff`; never update canonical `handoff-to-specify.json` directly. Rerun self-review and ask the user to approve its current digest.
- When senior consequence analysis triggers, preserve `CA-###` obligations, affected objects, lifecycle states, dependency impact, recovery/validation needs, coverage gaps, and stop-and-reopen conditions in the unified handoff contract.

## Output Contract

- Let `specify-runtime discussion` and each registered artifact owner maintain the independent discussion state and artifacts under `.specify/discussions/<slug>/`; never mutate that workspace with filesystem operations.
- Treat `handoff-ready` as resumable until its confirmed `sp-quick` or `sp-specify` consumer binds the source contract and review digest, or the user confirms the topic should be dropped; after consumption, mark it with `{{specify-subcmd:specify-runtime discussion mark-consumed <slug> --feature-dir <consumer-workspace>}}` before archiving. The compatibility `--feature-dir` flag accepts a Quick workspace.
- Provide 2-3 project-grounded technical options only after the relevant boundary is locked.
- Report unresolved questions honestly instead of forcing planning readiness.
- Distinguish verified project facts from open assumptions before presenting technical options.
- Keep the current discussion compass fresh at semantic checkpoints.
- Replies must be frontstage-readable before backstage-complete: start with the recommended direction, plain-language reason, concrete judgment or readiness checklist, default next step, and override path when useful. Do not use mandatory visible headings or fixed card labels.
- Do not end with only a promise to do the next step; produce the safe first-pass content now. If the next step is blocked, state the blocker and provide the smallest useful partial draft, checklist, or evidence plan.
- When direction is locked but the discussion is not handoff-ready, include a readiness summary instead of a state receipt; do not ask the user to say next when a safe default discussion action exists.
- Create the single draft through `specify-runtime discussion write-handoff`; `handoff-to-specify.json` becomes handoff-ready only after self-review and digest confirmation.
- Do not write separate split planning artifacts or candidate-specific handoff files.
- When explicit handoff is requested, include `handoff_goal`, `context_boundary`, `implementation_target`, `source_evidence`, `blocking_unknowns`, `downstream_instructions`, `quality_gate`, and a Must-Preserve Ledger.
- Request-changes repair is an upstream discussion responsibility: keep the discussion in draft/user-review state, resubmit the refreshed contract inline through `specify-runtime discussion write-handoff`, carry forward soft unknowns with owner/latest resolve phase/stop-and-reopen condition or waive them as non-blocking assumptions, and resubmit for review.
- Do not present draft handoff review as a path receipt or artifact-write log; the visible reply must summarize the decision, user-selected route, approved scope, excluded scope, checks, contract path, and allowed review responses.
- When a handoff becomes `handoff-ready`, use a concise visible reply that covers the handoff goal, selected direction, target boundary, Must-Preserve coverage, readiness, contract path, and next consumption path; do not close with only file paths, status counters, or a next command. Keep ready-summary quality checks internal instead of showing them as primary headings.
- Before `handoff-ready`, do not describe the next consumption path as a user-invoked `sp-quick` or `sp-specify` command. The safe default next action is still `sp-discussion` handoff assessment, review, or repair.
- Before every final response that names `sp-quick` or `sp-specify`, run `specify-runtime discussion status <slug> --format json` and consume its canonical status and selected `recommended_consumer`; withhold the invocation unless status is exactly `handoff-ready` and the named workflow is the selected consumer.
- Do not mark handoff ready if role objects, target path context, evidence provenance, self-review status, user confirmation, or blocking unknown handling is missing.
- Preserve `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` for the downstream fidelity gate.
- For UI-facing work, preserve `ui_discussion_status`; confirmed UI decisions; deferred UI unknowns; and Markdown-carried ASCII sketches with JSON fields `ui_sketches_present`, `ui_sketch_summary`, and `ui_sketch_reference`.

## Guardrails

- Do not edit source code or tests.
- Do not create feature branches or feature directories.
- Do not automatically invoke or route into either downstream consumer; prepare and expose the confirmed route for a later invocation.
- Do not make project-specific technical claims before the Context Boundary Gate, staged cognition gate, and Truth Pass are complete.
- Do not use current project cognition to prove another project's implementation facts.

{{spec-kit-include: ../common/read-only-evidence-lanes.md}}

For `sp-discussion`, read-only evidence lanes may support boundary locking, Truth Pass evidence, affected-surface checks, option evidence, or consequence mapping. Use `choose_evidence_lane_dispatch(command_name="discussion", snapshot, workload_shape)` only after the discussion question has a safe read-only evidence lane contract. The leader owns product judgment, recommendation, handoff assessment, and `handoff-ready` status.

{{spec-kit-include: ../common/user-input.md}}

## Objective

Drive a resumable product and technical discussion that locks context boundaries, matures a rough idea into requirements and implementation options, and produces one reviewed handoff contract before formal specification.

## Context

- Primary inputs: the user's idea, the current discussion session under `.specify/discussions/<slug>/`, passive project memory, boundary evidence, and project cognition only when the discussion reaches source-grounded technical judgment.
- `discussion-state.md` is the durable session state source of truth.
- `sp-discussion` is upstream of `sp-specify`; it does not create feature branches or write formal feature artifacts.

## Process

- Create or resume the discussion session.
- Run the Context Boundary Gate before project-specific technical options, affected-file claims, implementation-path claims, or handoff generation.
- Use project cognition as advisory navigation only when current-project facts matter; use `--intent discussion`, read returned `minimal_live_reads`, and prove technical claims from live repository files.
- Complete a Truth Pass before source-grounded technical advice, affected-surface claims, implementation-path recommendations, or testing strategy claims tied to existing code; record `verified_project_facts`, `open_assumptions`, `evidence_checked`, and `advice_confidence`.
- Use a high-throughput collaborative brief for substantive turns: lead with the recommended direction, a plain-language reason, enough concrete detail to be useful, and the next useful move.
- Apply frontstage / backstage separation. Frontstage is the visible conversation; backstage is state accounting backstage for open questions, decisions, Must-Preserve items, evidence, dirty artifacts, flush reasons, and handoff readiness.
- Use Recommendation-First Decision Progression: when evidence and user intent support a safe default, continue by default, state the recommended choice directly, give the reason, and move to the next useful decision instead of ending on a bare "should we?" question.
- Recommendation-first is not questionless: ask only when user judgment is genuinely required and no safe default exists. The question must include the recommended default and meaningful override options.
- Track an internal `reply_shape_id` from the Adaptive Reply Contract at semantic checkpoints; treat it as bookkeeping, not mandatory visible headings.
- Maintain a Discussion Compass in `discussion-state.md` so long conversations preserve what is being solved, what is confirmed, what changed, what remains undecided, the current recommendation, and the next useful decision.
- Apply the Anti-Toothpaste Protocol: show the broader decision map, recommend a next path, and ask only when user judgment is genuinely required and no safe default exists.
- Classify each user turn before asking a question.
- Run the Question Evidence Gate before asking the user; answer repository-discoverable facts from live evidence.
- Use an Adaptive Question Pack: ask one required primary question, and optionally add up to two same-topic follow-ups only when the topic is local and low risk.
- Fall back to exactly one question for boundary gaps, evidence conflicts, cross-project targets, handoff readiness, destructive or lifecycle consequences, security or data-risk consequences, and major product trade-offs.
- Put a recommended option and short reason on multiple-choice questions.
- Use checkpoint persistence: do not persist every turn. Ordinary turns do not write local files by default; flush one batched compact event to `discussion-log.md` only at a semantic checkpoint, user-triggered save, five-turn cadence, high compaction risk, or durable lifecycle transition.
- Keep ordinary persistence details backstage. Surface file paths and state updates only when the user needs review, recovery, verification, state visibility, or a durable lifecycle handoff.
- Do not ask for continuation, permission to proceed, or agreement with a reversible safe recommendation. Continue by default and include the override path when one exists.
- Refresh `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` only at semantic checkpoints.
- If the user asks to transfer functionality into another project, lock `target_project_root` immediately before technicalizing.
- When the user explicitly asks to hand off or continue the next stage, write `handoff-assessment.md` first.
- After functional discussion is stable and when no explicit handoff request is active, offer an optional UI and interaction discussion for UI-facing requirements; record `ui_discussion_status` and preserve confirmed or deferred UI decisions; the UI pass is not a mandatory handoff gate.
- If explicit handoff is already requested, run handoff assessment first and return to UI discussion only when UI decisions block readiness or the user reopens UI discussion.
- If the direction is coherent and boundary-locked after explicit handoff request, write exactly one draft handoff package: `handoff-to-specify.md` and `handoff-to-specify.json`.
- If the direction is too broad to express as one coherent package, continue the discussion instead of writing candidate-specific handoff files.
- Run handoff self-review and require user confirmation before marking `handoff-ready`.
- When senior consequence analysis triggers, preserve `CA-###` obligations, affected objects, lifecycle states, dependency impact, recovery/validation needs, coverage gaps, and stop-and-reopen conditions in the unified handoff pair.

## Output Contract

- Maintain the independent discussion state and artifacts under `.specify/discussions/<slug>/`.
- Treat `handoff-ready` as resumable until `sp-specify` consumes it or the user confirms the topic should be dropped; after consumption, mark it with `specify discussion mark-consumed <slug> --feature-dir <feature-dir>` before archiving.
- Provide 2-3 project-grounded technical options only after the relevant boundary is locked.
- Report unresolved questions honestly instead of forcing planning readiness.
- Distinguish verified project facts from open assumptions before presenting technical options.
- Keep the current discussion compass fresh at semantic checkpoints.
- Write `handoff-to-specify.md` and `handoff-to-specify.json` together as a draft pair; both files are mandatory, and the pair becomes handoff-ready only after self-review and user confirmation.
- Do not write separate split planning artifacts or candidate-specific handoff files.
- When explicit handoff is requested, include `handoff_goal`, `context_boundary`, `implementation_target`, `source_evidence`, `blocking_unknowns`, `downstream_instructions`, `quality_gate`, and a Must-Preserve Ledger.
- When a handoff becomes `handoff-ready`, use a concise visible card with `Handoff Ready`, `Locked Direction`, `Carry Forward`, `Readiness`, `Package`, and `Next Step`; do not close with only file paths, status counters, or a next command. Keep the `Ready Summary Quality` check internal instead of showing it as a primary heading.
- Do not mark handoff ready if role objects, target path context, evidence provenance, self-review status, user confirmation, or blocking unknown handling is missing.
- Preserve `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` for the downstream fidelity gate.
- For UI-facing work, preserve `ui_discussion_status`; confirmed UI decisions; deferred UI unknowns; and Markdown-carried ASCII sketches with JSON fields `ui_sketches_present`, `ui_sketch_summary`, and `ui_sketch_reference`.

## Guardrails

- Do not edit source code or tests.
- Do not create feature branches or feature directories.
- Do not automatically invoke or route into `sp-specify`.
- Do not make project-specific technical claims before the Context Boundary Gate, staged cognition gate, and Truth Pass are complete.
- Do not use current project cognition to prove another project's implementation facts.

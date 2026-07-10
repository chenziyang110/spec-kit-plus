Trigger: when explaining how `sp-specify` or `sp-quick` consumes the handoff.

Purpose: preserve downstream consumption, decision digest, selected direction, target boundary, recommended consumer, and quick-task eligibility rules.

Preserved Contract: Migrated from `templates/commands/discussion.md`; this file preserves existing `sp-discussion` behavior and does not define new workflow behavior.

## Downstream Consumption

The handoff contains `consumer_eligibility`, `recommended_consumer`, `planning_constraints`, and `discussion_decision_digest` so downstream workflows preserve the selected direction, target boundary, next consumption path, rejected alternatives, accepted tradeoffs, experience commitments, review criteria, and `must_not_dilute` constraints.

`sp-specify` consumption must preserve the confirmed unified discussion handoff without repair. `sp-quick` eligibility is allowed only when the handoff contract says the work is bounded enough for quick-task execution. Do not flatten the discussion into generic requirements or rediscover decisions that the handoff already locked.

Downstream consumption begins only from the ready Markdown/JSON handoff pair or an unconsumed discussion whose state points to that pair. If the pair is missing, draft-only, stale, or not user-confirmed, the next action is `sp-discussion` repair or review, not `sp-specify` with `specification-input.md` or another source-file fallback.

# Discussion contract

The durable state is a decision model, not a transcript. Preserve the problem,
actors, outcomes, scope boundaries, repository facts, confirmed decisions,
rejected options with reasons, assumptions, open decisions, and current next
question.

Session identity comes from `specify-runtime discussion resolve --intent continue
[--slug <slug>] --format json`. Multiple candidates are a blocker until the
user chooses a slug; do not guess and do not select latest. The resolver's
`state_sha256` is the compare-and-swap input for checkpoint and write-handoff.

Topic ownership is explicit. Classify each turn with `route: continue_current`,
`branch_new`, `link_existing`, or `defer`. Only `route: continue_current` may change
this discussion's owned scope or handoff. Branch/link/defer side topics stay as
references with `target_slug`/`source_digest` when available; do not copy those
decisions into the current requirement contract.

Before a handoff, preserve the locked target root, `verified_project_facts`,
evidence checked, open assumptions, and advice confidence. Carry triggered
consequence obligations with affected objects and stop/reopen conditions. For UI
work, keep every original UI reference, confirmed direction and interaction
decision, and deferred UI unknown with its downstream owner. Run Design
Discovery when UI is involved and persist durable `design_context` (feeling/tone,
dials, density, motion, references, anti-slop lean, `sp_design_required`) into
Design Carry-Forward and handoff `discussion_decision_digest.design_context`—
not chat-only prose.

Use deterministic discussion helpers for lifecycle changes. A handoff is
eligible only when its evidence exists, product boundaries are explicit,
blocking contradictions are resolved or retained, and every material decision
can become a requirement or constraint. Validation success is necessary but
does not replace agent self-review or user confirmation.

At handoff routing, show both consumers with their eligibility, explain any
blocker, and recommend one eligible consumer from delivery complexity and
consequence profile rather than raw size alone. The user makes the final choice.
If no explicit choice exists, ask one route-choice question, remain in
`spx-discussion`, and do not call `discussion write-handoff`. Keep the route
unresolved until that choice is explicit, then store the selected consumer in
`recommended_consumer`; the protected digest reconfirms it with the rest of the
handoff meaning.

If the conversation changes after a handoff draft, invalidate the draft rather
than editing around its protected revision. Closing and archiving are separate
explicit actions; neither proves the handoff was consumed.

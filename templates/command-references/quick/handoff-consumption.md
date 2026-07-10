Trigger: when sp-quick starts from a discussion contract.

Purpose: consume one bounded agent-only requirement contract without reconstructing upstream discussion or repeating confirmed decisions.

Preserved Contract: quick accepts only a ready contract whose scope and consequence model remain bounded; wider work routes to specify or discussion.

## Resolve Discussion Handoff Intake Before Quick-Task Execution

Accept a normal quick request, a discussion slug, or `.specify/discussions/<slug>/handoff-to-specify.json`. When no argument is supplied, select only one unconsumed handoff-ready discussion whose `recommended_consumer` or `consumer_eligibility.sp-quick.status` selects quick.

Set `SOURCE_CONTRACT` and `SOURCE_DISCUSSION_SLUG`. Require one canonical JSON contract; do not require or search for a Markdown companion or a quick-specific handoff.

Before execution require:

- `entry_source: sp-discussion`;
- `handoff_kind: discussion_requirement_contract`;
- `status: handoff-ready`;
- current `review_digest` matching `quality_gate.confirmed_digest`;
- user-confirmed quality gate;
- zero hard unknowns and open conflicts;
- `consumer_eligibility.sp-quick.status: ready`;
- bounded in/out scope;
- no planning constraint, consequence obligation, or reopen condition that requires specification first.

Read the agent requirement contract, task-relevant `must_preserve`, decision digest, planning constraints, and reopen conditions. Read supporting discussion files only through a named evidence reference that is stale, missing, or contradictory.

Seed `STATUS.md` with `source_discussion_slug`, `source_contract`, `review_digest`, bounded scope, locked direction, task-relevant obligations, reopen conditions, and any source refs actually read.

When quick introduces no `semantic_delta`, bind `understanding_confirmed` to the confirmed `review_digest` and do not repeat user confirmation. Present a new Understanding Checkpoint only when quick changes scope, behavior, risk acceptance, target boundary, validation obligations, or another user-owned decision.

If eligibility fails or the consequence model is no longer bounded, stop with the blocker and route to `{{invoke:specify}}` or `{{invoke:discussion}}` as recorded by the contract.

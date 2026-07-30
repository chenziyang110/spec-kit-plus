Trigger: when sp-quick starts from a discussion contract.

Purpose: consume one confirmed agent-only requirement contract without reconstructing upstream discussion or repeating confirmed decisions.

Preserved Contract: quick accepts a ready, confirmed contract selected for direct delivery. Work size, capability count, architecture, migration, acceptance depth, or consequence breadth do not force a route to specify.

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
- `consumer_eligibility.sp-quick.status: ready`, except for the legacy size/breadth-only override defined below;
- confirmed in/out scope and observable success evidence;
- no unresolved product decision, authority boundary, or reopen condition that blocks implementation from starting.

Query the agent requirement contract, task-relevant `must_preserve`, decision digest, planning constraints, and reopen conditions through their CLI owners. Treat only source refs actually queried through `specify-runtime artifact show` as consumed; query supporting discussion files only when a named evidence reference is stale, missing, or contradictory.

Submit `source_discussion_slug`, `source_contract`, `review_digest`, confirmed scope, locked direction, obligations, and reopen conditions through the registered quick/status artifact CLI. Never seed `STATUS.md` with a direct write.

After the confirmed Quick checkpoint is bound into `STATUS.md`, mark the source discussion consumed with `{{specify-subcmd:specify-runtime discussion mark-consumed <slug> --feature-dir <quick-workspace>}}`. The `--feature-dir` option is the compatibility spelling; the runtime accepts the Quick workspace and validates its `STATUS.md` binding to `source_contract` and `review_digest`. Do not mark consumed before that evidence exists.

When quick introduces no `semantic_delta`, bind `understanding_confirmed` to the confirmed `review_digest` and do not repeat user confirmation. Present a new Understanding Checkpoint only when quick changes scope, behavior, risk acceptance, target boundary, validation obligations, or another user-owned decision.

For a legacy contract whose Quick eligibility is blocked only because the work is
large, multi-capability, architectural, migration-heavy, compatibility-heavy,
acceptance-heavy, or has broad consequences, treat that reason as obsolete
routing advice. Do not rewrite the upstream contract; present a fresh Quick
Checkpoint bound to the same `review_digest`, record the user's explicit Quick
choice, and continue after confirmation.

If eligibility fails because the contract is unconfirmed, internally
contradictory, missing its target boundary, has hard unknowns, or requires a
user-owned decision before implementation, stop with that exact blocker and
return to `{{invoke:discussion}}`. Do not route to `{{invoke:specify}}` as an
automatic recovery.

Trigger: when sp-quick starts from a discussion contract.

Purpose: consume one confirmed agent-only requirement contract without reconstructing upstream discussion or repeating confirmed decisions.

Preserved Contract: quick accepts a ready, confirmed contract selected for direct delivery. Work size, capability count, architecture, migration, acceptance depth, or consequence breadth do not force a route to specify.

## Resolve Discussion Handoff Intake Before Quick-Task Execution

Accept a normal quick request, a discussion slug, or `.specify/discussions/<slug>/handoff-to-specify.json`. Resolve discussion intake with `specify-runtime discussion resolve --intent sp-quick [--slug <slug>] --format json`. When no argument is supplied, select only one unconsumed handoff-ready discussion whose `recommended_consumer` or `consumer_eligibility.sp-quick.status` selects quick. If multiple candidates are returned, stop for an explicit slug; never guess, do not select latest, and do not use name, slug, title, topic, or keyword similarity as binding evidence.

Set `SOURCE_CONTRACT` and `SOURCE_DISCUSSION_SLUG`. Require one canonical JSON contract; do not require or search for a Markdown companion or a quick-specific handoff.

Before execution require:

- `entry_source: sp-discussion`;
- `handoff_kind: discussion_requirement_contract`;
- `version: 5` with a current `discussion_snapshot_digest`;
- `status: handoff-ready`;
- current `review_digest` matching `quality_gate.confirmed_digest`;
- resolver-returned `recommended_consumer`, `review_digest`, and `state_sha256` matching the consumed source contract;
- `topic_ownership.owner_slug` matching `SOURCE_DISCUSSION_SLUG`;
- user-confirmed quality gate;
- zero hard unknowns and open conflicts;
- `consumer_eligibility.sp-quick.status: ready`, except for the legacy size/breadth-only override defined below;
- confirmed in/out scope and observable success evidence;
- non-empty actors, scenarios, success criteria, and optimal solution approach in `agent_requirement_contract`;
- every `source_materials` entry inspected with no coverage gaps and referenced by `source_evidence.material_id`;
- no unresolved product decision, authority boundary, or reopen condition that blocks implementation from starting.

Query the agent requirement contract, source-material ledger and evidence links, task-relevant `must_preserve`, decision digest, planning constraints, and reopen conditions through their CLI owners. Treat only source refs actually queried through `specify-runtime artifact show` as consumed; query supporting discussion files only when a named evidence reference is stale, missing, or contradictory.

Submit the resolver's exact `discussion_slug` as `source_discussion_slug`, plus `source_contract`, resolver-returned `review_digest`, resolver-returned `state_sha256`, resolver-returned `recommended_consumer`, confirmed scope, locked direction, obligations, and reopen conditions through the registered quick/status artifact CLI. Never seed `STATUS.md` with a direct write.

After the confirmed Quick checkpoint is bound into `STATUS.md`, verify the five lineage fields `source_discussion_slug`, `source_contract`, `review_digest`, `state_sha256`, and `recommended_consumer`, then mark the source discussion consumed with `{{specify-subcmd:specify-runtime discussion mark-consumed <slug> --feature-dir <quick-workspace>}}`. The `--feature-dir` option is the compatibility spelling; the runtime accepts the Quick workspace and validates its `STATUS.md` binding to all five lineage fields. Do not mark consumed before that binding evidence exists.

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
## Complete source consumption for direct delivery

A Discussion handoff with materials must pass the same ready validator before
Quick inherits it: every original extent accounted for, complete runtime
`reading`/unit delivery, complete `unit_dispositions`, and every
`agent_requirement_contract.source_requirements` record explicitly disposed.
Query the full source ledger through the canonical handoff binding and map all
in-scope REQ IDs into the existing work-item outcomes and acceptance; preserve
negations, conditions, permissions, exceptions, corrections, and source-backed
non-goals/deferrals. Do not shrink source scope because delivery uses Quick.
Undelivered, unmapped, stale, unavailable, or unresolved material is a readiness
blocker even if an old summary, status, or size-based eligibility override says
ready. Legacy materials without runtime reading receipts return to Discussion
for import and rereading, never automatic promotion from a summary. Context-
direct selection cannot bypass these source gates: a material-backed handoff
uses full Quick intake. New original-source material or a changed rule requires
source reconciliation in its owning Discussion before relying on its old
binding. When no semantic delta exists, inherit the already confirmed digest
without another user confirmation; only a real decision change uses the existing
amendment gate. Pure conversation without materials retains normal Quick rules.

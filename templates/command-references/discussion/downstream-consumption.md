Trigger: when explaining how `sp-specify` or `sp-quick` consumes a ready discussion contract.

Purpose: preserve downstream fidelity while preventing duplicate source sweeps and human-oriented handoff material.

Preserved Contract: consumers read canonical JSON, inherit confirmed truth by stable reference, and return integrity defects to `sp-discussion`.

## Downstream Consumption

Complete original source consumption belongs to Discussion. Its handoff carries
runtime `reading`, all `unit_dispositions`, and
`agent_requirement_contract.source_requirements`; the consumer verifies this
coverage through the ready validator before relying on compact downstream
reads. A MAT/evidence link or hash alone does not prove complete interpretation.
Specify maps every REQ in `source_requirement_coverage` to its exact disposition
and real requirement/acceptance pointers, which Plan and Tasks preserve.
Implement packets derive `source_requirement_refs` from assigned acceptance
refs. Quick consumes the same source ledger through its confirmed binding.
No downstream phase silently removes a source rule or reinterprets it as
context to avoid work; genuine truth changes return to the owning phase.

When a consumer needs the original text behind a REQ, use its exact material
and unit IDs with `specify-runtime discussion read-material <slug> --material-id
<MAT-ID> --unit-id <unit-id> --format json`. Already-delivered units return
`replayed: true` without reopening or changing ready/consumed/closed/archived
state. Replay may omit `--expected-state-sha256`; a supplied hash must match
current state. Verify the returned `content_sha256`/unit digest against the
bound source ledger and consume the complete text. Keep the canonical snapshot
ref and slug; do not reimport, silently switch versions, or expand the entire
raw snapshot merely to read one original unit.

Consumers select `.specify/discussions/<slug>/handoff-to-specify.json` through `specify-runtime discussion resolve --intent sp-specify|sp-quick [--slug <slug>] --format json`, then `specify-runtime artifact show`, verify ready/user-confirmed gates and current `review_digest`, and query only required contract fields and evidence refs. With multiple candidates, stop for an explicit slug; never guess and never select latest.

Do not require a Markdown companion. `specification-input.md`, `discussion-state.md`, and other discussion source files are not fallback handoffs. Do not scan discussion logs or checkpoint documents unless a named evidence reference is stale, missing, or contradictory. Consume the handoff's `discussion_snapshot_digest`, `source_materials`, and `source_evidence.material_id` coverage directly; every carried material must be inspected, gap-free, and evidence-linked. Do not rebuild `discussion_decision_digest`, flatten the selected direction, or re-ask confirmed questions when `semantic_delta` is empty.

At the discussion routing gate, present both paths and their eligibility, explain any blocker, and give a complexity-informed recommendation among eligible paths: `sp-quick` for bounded, well-understood direct delivery with task-local planning; `sp-specify` for high-complexity or ambiguous work, interacting capabilities or systems, architecture/data migration/security/compliance/rollout concerns, broad acceptance obligations, or durable specification traceability. Task size alone is not a hard routing ceiling. The user's final choice controls the route, even when it differs from the recommendation. The confirmed contract records that selected consumer: `sp-specify` compiles it into `spec-contract.json`, while `sp-quick` consumes it for direct delivery. After successful consumption, bind downstream evidence to all five lineage values—the resolver's exact slug in `discussion_slug` for the formal feature pointer or `source_discussion_slug` for Quick `STATUS.md`, plus `source_contract`, `review_digest`, `state_sha256`, and `recommended_consumer`—then mark the discussion consumed.

Consumption remains single-owner: `topic_ownership.owner_slug` must equal the resolved slug. Cross-discussion `routed_topics` are pointers only and do not authorize a consumer to pull requirements from another discussion without resolving that discussion separately.

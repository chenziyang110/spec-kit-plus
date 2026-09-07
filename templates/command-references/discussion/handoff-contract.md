Trigger: after an explicit user handoff request and a locked context boundary.

Purpose: write one minimum-sufficient agent requirement contract that preserves product intent, evidence, obligations, and downstream recovery without human-oriented duplication.

Preserved Contract: requirements stay consumer-neutral, while the route is user-selected, schema-validated, and owned by `sp-discussion` until ready.

## Agent-Facing Requirement Contract

Build only the compact semantic routing/review input in memory—consumer choice, self-review timestamp, and other non-state-owned handoff controls—and submit it with `{{specify-subcmd:specify-runtime discussion write-handoff <slug> --expected-state-sha256 <state_sha256> --input-json '<semantic-json>' --json}}`, where `state_sha256` is returned by `discussion resolve`. Prefer `--input-json @payload.json` or `--input-json -` on Windows PowerShell when the draft is large. Expand the live field contract with `{{specify-subcmd:specify-runtime api schema discussion-write-handoff-input --json}}` instead of guessing shapes. Before this call, write a complete semantic checkpoint so `latest_checkpoint.snapshot_sha256` matches the current state; otherwise write-handoff blocks with `missing_semantic_checkpoint` or stale checkpoint evidence. The CLI expands `templates/discussion-handoff-template.json`, supplies stable metadata and blocked defaults, derives state-owned semantics from canonical `discussion-state.json`, copies state `requirements_snapshot` into `agent_requirement_contract`, binds only `discussion_snapshot_digest`, recomputes source material digests, coverage and unknown/conflict counts, computes the review digest, and atomically writes the canonical contract. Never read or reproduce the template, never pass state truth to override the checkpoint, and never create a draft file. The canonical result is `.specify/discussions/<slug>/handoff-to-specify.json`; the filename is compatibility-only, and the payload is one `discussion_requirement_contract` that may select `sp-specify` or `sp-quick`.

Before that write, present both paths and their eligibility, explain any blocker, give a complexity-informed recommendation among eligible paths, and obtain the user's final consumer choice. `recommended_consumer` records that confirmed selection, even when it differs from the recommendation. Do not create a draft with an unresolved route; the digest review reconfirms the selected consumer as protected meaning.

Do not write a Markdown companion, consumer-specific copy, reviewer guide, transcript, or pointer-only substitute. Human review is a visible response generated from the canonical JSON and bound to its `review_digest`.

The contract must contain the minimum sufficient inputs for the next agent:

- target need, in/out/deferred scope, constraints, success criteria, selected design direction, and optimal solution approach;
- `topic_ownership.owner_slug` matching the resolved slug, the current discussion's `owned_scope`, and only reference-level `routed_topics` for `branch_new`, `link_existing`, or `defer` side topics;
- locked context boundary (`status: locked`) and implementation target;
- `current_project_roles` / `target_project_roles` as objects with `role`, `scope`, `evidence_source`, `notes` (not bare string arrays);
- `source_evidence[]` objects with `source_type`, `evidence_status`, `source`, `claim` (not `ref`/`authority`/`status` aliases);
- `source_materials[]` for every user-provided document, screenshot, recording, pasted note, link, or other supplied material, using stable `MAT-###` IDs, `material_type`, `locator`, summary, `inspection_status`, `claims[]`, `coverage_gaps[]`, `sensitivity`, and safe references or sanitized summaries for restricted material;
- `source_evidence[].material_id` links to existing `MAT-###` entries, and every material has at least one evidence link before handoff; uncovered, pending, partial, stale, unavailable, or conflicting material stays visible as a blocker or coverage gap;
- hard and soft unknown handling;
- settled decisions, task-relevant dependencies and planning constraints, deferred scope, and reopen conditions;
- `consumer_eligibility.*.status` must be `ready` or `blocked`; draft/ready validation requires at least one `ready` consumer (`eligible` is rejected);
- decision digest entries only when losing them could change downstream behavior;
- task-relevant `MP-*` and `CA-###` obligations with stable IDs;
- `quality_gate.self_reviewed_at` (write-handoff sets `status: self_reviewed` from that timestamp; notes alone are insufficient);
- coverage/planning gates, protected `review_digest`, and `source_contract`.

Soft unknowns that remain open must be carried forward explicitly with owner or reopen condition; never disguise them as settled facts.

Side topics are not soft unknowns and not downstream scope. If the Topic Ownership Gate classified a turn as `branch_new`, `link_existing`, or `defer`, keep that material out of this handoff's requirement contract except for a routed-topic reference containing the target slug/source digest when available.

Exclude human presentation, duplicated background prose, full discussion history, timestamps not required by confirmation, ordered execution plans, and fields that do not change downstream action, verification, or recovery.

Store the protected digest under `discussion_decision_digest`: `locked_direction`, only relevant `rejected_alternatives`, `accepted_tradeoffs`, `experience_commitments`, `review_criteria_carried_forward`, and `must_not_dilute`. Downstream phases refer to this digest and must not rediscover or flatten it.

## Review Digest

Compute `review_digest` from protected semantic content only. Exclude status transitions, timestamps, confirmation bookkeeping, and integrity fields so approval binds to meaning.

Run `{{specify-subcmd:specify-runtime discussion validate-handoff <slug> --mode draft --json}}`, present a concise human-facing review in the conversation, including material coverage (`MAT-###` IDs covered and uncovered), material inspection gaps, unknowns/conflicts, and require confirmation of the returned digest. Bind approval with `{{specify-subcmd:specify-runtime discussion confirm-handoff <slug> --digest <review-digest> --json}}`. A semantic write invalidates confirmation and requires a new digest; bookkeeping-only confirmation does not change the digest.

Do not ask for a bare yes/no confirmation without review criteria. An unrelated prompt is not approval of the protected digest.

## Must-Preserve Ledger And Consequence Obligations

Preserve only semantic units whose loss can cause product or implementation drift. Each obligation needs `id`, `type`, `claim`, `source`, `downstream_requirement`, `blocking_level`, `owner`, `latest_resolve_phase`, and `status`. Add `stop_and_reopen_condition` when unresolved.

Describe only the target need, constraints, success criteria, design direction, and optimal solution approach; do not describe current execution or implementation progress in the Agent-facing contract.

Do not copy the same obligation body into later phase transitions. Downstream contracts refer to the stable obligation and add only phase-owned resolution or evidence.

## Repair Ownership

If validation, user review, or a downstream consumer rejects the contract, repair canonical JSON in `sp-discussion`, recompute the digest, rerun self-review, and ask for confirmation of the current revision. Consumers must not reconstruct or patch upstream truth.

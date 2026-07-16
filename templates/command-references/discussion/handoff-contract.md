Trigger: after an explicit user handoff request and a locked context boundary.

Purpose: write one minimum-sufficient agent requirement contract that preserves product intent, evidence, obligations, and downstream recovery without human-oriented duplication.

Preserved Contract: the handoff is user-confirmed, consumer-neutral, schema-validated, and owned by `sp-discussion` until ready.

## Agent-Facing Requirement Contract

Write `.specify/discussions/<slug>/handoff-to-specify.json` from `templates/discussion-handoff-template.json`. The filename is compatibility-only; the payload is one `discussion_requirement_contract` that may select `sp-specify` or `sp-quick`.

Do not write a Markdown companion, consumer-specific copy, reviewer guide, transcript, or pointer-only substitute. Human review is a visible response generated from the canonical JSON and bound to its `review_digest`.

The contract must contain the minimum sufficient inputs for the next agent:

- target need, in/out/deferred scope, constraints, success criteria, selected design direction, and optimal solution approach;
- locked context boundary and implementation target;
- evidence refs with authority/status, plus hard and soft unknown handling;
- settled decisions, task-relevant dependencies and planning constraints, deferred scope, and reopen conditions;
- consumer eligibility and recommended consumer;
- decision digest entries only when losing them could change downstream behavior;
- task-relevant `MP-*` and `CA-###` obligations with stable IDs;
- coverage/planning gates, quality gate, protected `review_digest`, and `source_contract`.

Soft unknowns that remain open must be carried forward explicitly with owner or reopen condition; never disguise them as settled facts.

Exclude human presentation, duplicated background prose, full discussion history, timestamps not required by confirmation, ordered execution plans, and fields that do not change downstream action, verification, or recovery.

Store the protected digest under `discussion_decision_digest`: `locked_direction`, only relevant `rejected_alternatives`, `accepted_tradeoffs`, `experience_commitments`, `review_criteria_carried_forward`, and `must_not_dilute`. Downstream phases refer to this digest and must not rediscover or flatten it.

## Review Digest

Compute `review_digest` from protected semantic content only. Exclude status transitions, timestamps, confirmation bookkeeping, and integrity fields so approval binds to meaning.

Self-review the JSON contract, present a concise human-facing review in the conversation, and require confirmation of the current digest. A semantic edit invalidates confirmation and requires a new digest; bookkeeping-only changes do not.

Do not ask for a bare yes/no confirmation without review criteria. An unrelated prompt is not approval of the protected digest.

## Must-Preserve Ledger And Consequence Obligations

Preserve only semantic units whose loss can cause product or implementation drift. Each obligation needs `id`, `claim`, `source`, `downstream_requirement`, `owner`, `latest_resolve_phase`, current status, and `stop_and_reopen_condition` when unresolved.

Describe only the target need, constraints, success criteria, design direction, and optimal solution approach; do not describe current execution or implementation progress in the Agent-facing contract.

Do not copy the same obligation body into later phase transitions. Downstream contracts refer to the stable obligation and add only phase-owned resolution or evidence.

## Repair Ownership

If validation, user review, or a downstream consumer rejects the contract, repair canonical JSON in `sp-discussion`, recompute the digest, rerun self-review, and ask for confirmation of the current revision. Consumers must not reconstruct or patch upstream truth.

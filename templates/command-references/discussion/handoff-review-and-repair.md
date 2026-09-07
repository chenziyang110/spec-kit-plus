Trigger: before marking a discussion contract ready or when review/consumption reports an integrity blocker.

Purpose: validate and repair the canonical agent-only contract without producing duplicate handoff views.

Preserved Contract: ready status requires a coherent boundary, complete coverage, zero hard unknowns/open conflicts, exact digest confirmation, and at least one eligible consumer.

## Handoff Assessment

After an explicit handoff request, classify the discussion as:

- `continue-discussion`: a product decision, target boundary, hard unknown, conflict, or required evidence is still unresolved;
- `ready-for-contract`: one coherent scope is mature enough to write canonical JSON;
- `blocked`: external/user-owned evidence prevents a safe contract.

Do not create the contract before explicit request and boundary lock.
Before `write-handoff`, save the complete current semantic snapshot through
`discussion checkpoint`; handoff creation requires
`latest_checkpoint.snapshot_sha256` to match canonical state. Missing checkpoints
block as `missing_semantic_checkpoint`, and stale checkpoints block instead of
allowing ad hoc handoff input to override state truth.

## Deterministic Draft Review

For supplied materials, first finish
[source-material-consumption.md](source-material-consumption.md): every
original-source extent accounted for, every runtime unit delivered, every unit
explicitly disposed, every atomic REQ source-bound, and every unresolved
interpretation surfaced. Perform semantic reverse review separately from the
runtime's structural validation. Do not approve a context-only unit that hides
a rule, or an exclusion/deferral without its actual decision source.

Use `{{specify-subcmd:specify-runtime discussion validate-handoff <slug> --mode draft --json}}` before asking for approval. Validate schema/version, goal/scope, consumer eligibility, context boundary, implementation target, evidence shape, source material ledger coverage, `MP-*`/`CA-###` coverage, planning/coverage gates, unknown/conflict counts, agent self-review, state snapshot digest, and the protected digest. Draft validation intentionally does not require user confirmation.

Use agent review only for judgment that deterministic validation cannot decide: whether the selected direction matches user intent, whether a soft unknown is genuinely non-blocking, or whether a tradeoff/reopen condition is truthful.

## Human Confirmation

Present the decision, recommended consumer, approved and excluded scope, important protected obligations, material coverage (`MAT-###` IDs covered and uncovered), unresolved non-blocking assumptions, conflicts or coverage gaps, and current digest in the visible reply. The JSON remains agent-only; do not persist a reviewer guide or Markdown rendering.

After the user confirms the current digest, run `{{specify-subcmd:specify-runtime discussion confirm-handoff <slug> --digest <review-digest> --json}}` and then `{{specify-subcmd:specify-runtime discussion mark-ready <slug> --json}}`. A semantic rewrite clears prior confirmation and requires this sequence again.

## Repair

On handoff request-changes repair or `blocked_by_handoff_integrity`, resubmit the repaired contract inline through `specify-runtime discussion write-handoff`, preserve still-valid IDs and evidence refs, consume the returned `review_digest`, rerun validation, and request confirmation again. Return field-level validation errors or a compact blocker with cause, safe retry, and stop condition when repair cannot complete.

Legacy v4 handoffs are not silently accepted as v5. Resume the owning
discussion, checkpoint the complete v3 semantic state (including material
ledger and evidence links), rewrite the handoff through `discussion
write-handoff`, and request approval of the new digest. Do not hand-edit a v4
payload into a v5 shape or reuse its prior confirmation.

The repair belongs to `sp-discussion`; consumers block instead of patching upstream truth.

Trigger: when a discussion contract is supplied, uniquely discoverable, or referenced by existing feature state.

Purpose: validate one agent-only upstream contract, enter compile mode, and avoid repeated source sweeps, decisions, and user review when semantics are unchanged.

Preserved Contract: feature creation begins only from a ready, user-confirmed, planning-eligible contract with a locked target boundary and complete protected obligations.

## Contract Intake

Classify arguments as a normal feature request, `.specify/discussions/<slug>/handoff-to-specify.json`, or a discussion slug. With no arguments and exactly one unconsumed `status: handoff-ready` discussion eligible for `sp-specify`, select it. If multiple unconsumed `handoff-ready` discussions exist, stop and ask for the slug; never guess.

Set `SOURCE_CONTRACT` and `SOURCE_DISCUSSION_SLUG`. Require one canonical JSON contract. Do not require a Markdown companion and do not reconstruct the contract from `specification-input.md`, discussion state, logs, or checkpoint documents.

Before feature creation require:

- `entry_source: sp-discussion` and `handoff_kind: discussion_requirement_contract`;
- canonical status `handoff-ready`;
- `consumer_eligibility.sp-specify.status: ready`;
- complete coverage and ready planning gate;
- user-confirmed quality gate with `confirmed_digest == review_digest`;
- zero hard unknowns and open conflicts;
- locked context boundary and confirmed implementation target;
- valid evidence refs and complete task-relevant `MP-*`/`CA-###` coverage.

Treat these protected refs as the Must-Preserve Ledger. Keep `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` distinct so an integrity or conflict blocker cannot be mistaken for ready planning state.

If validation fails, return `blocked_by_handoff_integrity` with field errors, safe retry in `sp-discussion`, and stop condition. Do not patch upstream truth.

Derive the feature description from `handoff_goal` and implementation target, not the path or slug. If the target root differs from the current project, stop before creating the feature in the wrong repository.

## Compile Mode

A confirmed discussion contract enters compile mode:

1. Read the canonical contract once.
2. Reuse its scope, decisions, tradeoffs, context capsule inputs, evidence refs, consumer boundary, and protected obligations.
   Preserve `discussion_decision_digest` by `decision_digest_ref`, including locked direction, relevant rejected alternatives, accepted tradeoffs, experience commitments, review criteria, and `must_not_dilute`.
3. Produce `spec-contract.json` and compute `semantic_delta` between the confirmed requirement contract and the compiled specification.
4. Read supporting discussion files only through a named evidence reference that is stale, missing, or contradictory.
5. Do not repeat approach comparison, section approval, source-signal extraction, decision-digest construction, or user review when `semantic_delta` is empty.

A non-empty delta must identify the affected ref and change. Ask the user only when the delta changes scope, behavior, target boundary, risk acceptance, deferral, or another user-owned decision. Repository-discoverable facts are resolved from bounded live evidence instead.

## Context Capsule

Write the minimum sufficient context into `spec-contract.json.context_capsule`: boundary ref, selected capability refs, evidence refs, minimal live reads actually needed, validation routes, and precise stale conditions. Do not copy repository prose or full source files into the contract.

Project cognition is advisory navigation. Reuse fresh upstream evidence; run a new bounded intake only when the spec needs a missing facet or the upstream evidence is stale for the requested planning claim.

## Specification Outputs

Write canonical `spec-contract.json` first. Render `spec.md` for project review. Create `alignment.md`, `context.md`, `references.md`, or a requirements diagnostic only when triggered content has independent value; otherwise store stable refs in the contract.

When compatibility requires `brainstorming/handoff-to-specify.json`, generate a pointer-only transition containing `source_contract`, `review_digest`, `semantic_delta`, required refs, blockers, and next action. Do not copy the requirement contract.

After deterministic schema, acceptance-coverage, traceability, contradiction, and scope-preservation checks pass, record the single next route. Mark the source discussion consumed only after canonical spec output exists and passes review.

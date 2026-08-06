Trigger: when a discussion contract is supplied, uniquely discoverable, or referenced by existing feature state.

Purpose: validate one agent-only upstream contract, enter compile mode, and avoid repeated source sweeps, decisions, and user review when semantics are unchanged.

Preserved Contract: feature creation begins only from a ready, user-confirmed, planning-eligible contract with a locked target boundary and complete protected obligations.

## Contract Intake

Classify arguments as a normal feature request, `.specify/discussions/<slug>/handoff-to-specify.json`, or a discussion slug. Use `specify-runtime discussion list --format json` for discovery and `discussion status <slug>` for selection. With no arguments and exactly one unconsumed `status: handoff-ready` discussion eligible for `sp-specify`, select it. If multiple unconsumed `handoff-ready` discussions exist, stop and ask for the slug; never guess.

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

1. Query the canonical contract once through `specify-runtime artifact show`.
2. Reuse its scope, decisions, tradeoffs, context capsule inputs, evidence refs, consumer boundary, and protected obligations.
   Preserve `discussion_decision_digest` by `decision_digest_ref`, including locked direction, relevant rejected alternatives, accepted tradeoffs, experience commitments, review criteria, and `must_not_dilute`.
3. Create `spec-contract.json` with `specify-runtime artifact scaffold --kind spec-contract`, patch its semantic fields through leased `artifact patch` calls, and compute `semantic_delta` between the confirmed requirement contract and the compiled specification.
4. Query supporting discussion artifacts only through their artifact/evidence CLI owner and only for a named evidence reference that is stale, missing, or contradictory.
5. Do not repeat approach comparison, section approval, source-signal extraction, decision-digest construction, or user review when `semantic_delta` is empty.

A non-empty delta must identify the affected ref and change. Ask the user only when the delta changes scope, behavior, target boundary, risk acceptance, deferral, or another user-owned decision. Repository-discoverable facts are resolved from bounded live evidence instead.

## Context Capsule

Patch `/context_capsule` through a leased `specify-runtime artifact patch --json-pointer /context_capsule --value-json '<inline-json>'` with only the minimum context; do not rewrite `spec-contract.json` or copy repository prose.

Project cognition is advisory navigation. Reuse fresh upstream evidence; run a new bounded intake only when the spec needs a missing facet or the upstream evidence is stale for the requested planning claim.

## Specification Outputs

Scaffold canonical `spec-contract.json` first with `specify-runtime artifact scaffold --kind spec-contract` and fill only targeted JSON pointers through fresh leased patches. Render `spec.md` and conditional views through their registered owners only when triggered content has independent value.

When compile mode requires `brainstorming/handoff-to-specify.json`, pass only `semantic_delta`, `required_refs`, `blockers`, and `recovery` to `specify-runtime discussion bind-consumer <slug> --feature-dir <feature-dir> --input-json '<transition-json>'` (inline JSON, `@path`, or `-` for stdin). The runtime validates the ready source contract and binds its digest, status, and next action; do not generate or patch the pointer directly. A create-feature scaffold with `status: pending` and null `discussion_slug` / `source_contract` / `review_digest` is unbound and may receive the first bind; a pointer already bound to a different discussion is rejected.

After deterministic schema, acceptance-coverage, traceability, contradiction, and scope-preservation checks pass, record the single next route. Mark the source discussion consumed only after canonical spec output exists and passes review.

Trigger: when a discussion contract is supplied, uniquely discoverable, or referenced by existing feature state.

Purpose: validate one agent-only upstream contract, enter compile mode, and avoid repeated source sweeps, decisions, and user review when semantics are unchanged.

Preserved Contract: feature creation begins only from a ready, user-confirmed, planning-eligible contract with a locked target boundary and complete protected obligations.

## Contract Intake

Classify arguments as a normal feature request, `.specify/discussions/<slug>/handoff-to-specify.json`, or a discussion slug. Use `specify-runtime discussion resolve --intent sp-specify [--slug <slug>] --format json` for selection. With no arguments and exactly one unconsumed `status: handoff-ready` discussion eligible for `sp-specify`, select it. If multiple unconsumed `handoff-ready` discussions exist, stop and ask for the slug; never guess. Multiple candidates from resolve are ambiguous; do not select latest or infer an unstated slug from a name, title, topic, or keyword similarity.

Respect the upstream Topic Ownership Gate: only `continue_current` material is owned by this discussion handoff. `branch_new`, `link_existing`, and `defer` entries in `topic_ownership.routed_topics` are reference-only and must not be silently compiled into this spec.

Set `SOURCE_CONTRACT` and `SOURCE_DISCUSSION_SLUG`. Require one canonical JSON contract. Do not require a Markdown companion and do not reconstruct the contract from `specification-input.md`, discussion state, logs, or checkpoint documents.

Before feature creation require:

- `entry_source: sp-discussion` and `handoff_kind: discussion_requirement_contract`;
- `version: 5` with a current `discussion_snapshot_digest` bound to the canonical checkpoint;
- canonical status `handoff-ready`;
- `consumer_eligibility.sp-specify.status: ready`;
- complete coverage and ready planning gate;
- user-confirmed quality gate with `confirmed_digest == review_digest`;
- `recommended_consumer: sp-specify` and `topic_ownership.owner_slug` matching `SOURCE_DISCUSSION_SLUG`;
- zero hard unknowns and open conflicts;
- locked context boundary and confirmed implementation target;
- non-empty actors, scenarios, scope, success criteria, and optimal solution approach in `agent_requirement_contract`;
- every `source_materials` entry inspected, gap-free, and linked through `source_evidence.material_id`;
- valid evidence refs and complete task-relevant `MP-*`/`CA-###` coverage.

Treat these protected refs as the Must-Preserve Ledger. Keep `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` distinct so an integrity or conflict blocker cannot be mistaken for ready planning state.

If validation fails, return `blocked_by_handoff_integrity` with field errors, safe retry in `sp-discussion`, and stop condition. Do not patch upstream truth.

Derive the feature description from `handoff_goal` and implementation target, not the path or slug. If the target root differs from the current project, stop before creating the feature in the wrong repository.

## Source intent before compilation

After the feature is created and `FEATURE_DIR` is known, but before compiling
the Spec body or its requirement/acceptance mappings, bind the selected source:

`{{specify-subcmd:specify-runtime discussion bind-consumer <slug> --feature-dir <feature-dir> --review-digest <review_digest> --intake --input-json '<transition-json>' --format json}}`

Use the resolver's current digest and the existing transition input shape:
`semantic_delta: []`, `required_refs: []`, `blockers: []`, `recovery: null`.
The source must already be complete, user-confirmed, currently ready, and
selected for `sp-specify`. Intake creates `brainstorming/handoff-to-specify.json`
with `status: pending` and all five lineage fields: `discussion_slug`,
`source_contract`, `review_digest`, `state_sha256`, `recommended_consumer`.
This declares source intent; it cannot be consumed and does not claim that
the specification is complete. No additional human approval is required.

On resume, a matching pending intake is idempotent. Reuse an already-ready
matching binding without running intake again: intake must not downgrade it.
A different source/digest blocks instead of replacing the binding. The Agent
must not delete this source pointer, clear its fields, or detach
`spec-contract.json.source_contract` / `source_revision` to make validation pass.
Keep the canonical source path and digest while compiling the complete
`source_requirement_coverage`. If intake fails, stop before compilation and
repair the exact binding rather than proceeding as an unbound direct request.

## Compile Mode

A confirmed discussion contract enters compile mode:

1. Query the canonical contract once through `specify-runtime artifact show`.
2. Reuse its scope, decisions, tradeoffs, context capsule inputs, source-material ledger and evidence links, consumer boundary, and protected obligations.
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

After complete Spec compilation and normal self-review, upgrade the existing
pending intake with `specify-runtime discussion bind-consumer <slug>
--feature-dir <feature-dir> --review-digest <review_digest>
--input-json '<transition-json>'` without --intake. Pass only `semantic_delta`,
`required_refs`, `blockers`, and `recovery`; use the resolver's exact digest.
Default binding retains strict compiled-Spec acceptance/source-coverage checks
before recording ready consumption evidence. Do not author or patch the pointer
directly, wait until this point for the first source-intent bind, or bypass the
pending stage's declared source. A different already-bound source is rejected.

After deterministic schema, acceptance-coverage, traceability, contradiction, and scope-preservation checks pass, record the single next route. Mark the source discussion consumed only after canonical spec output exists and passes review.
## Source requirement coverage

For material-backed intake, validate the ready Discussion source before
compilation. Require complete runtime-owned `reading`, full unit delivery,
`unit_dispositions`, and `agent_requirement_contract.source_requirements`.
Old material records without reading receipts must return to Discussion for
import and rereading; never infer full consumption from `inspected`, empty
gaps, a summary, or an old ready flag. Pure conversation with no materials
retains its existing path. This check adds no duplicate human confirmation.

Set `spec-contract.json.source_contract` to the canonical discussion handoff
path and `source_revision` to its exact `review_digest`. Populate
`source_requirement_coverage` with exactly one row per upstream REQ, preserving
`requirement_id` and `disposition`. Every `in_scope` row has non-empty
`requirement_refs` to real values such as
`spec-contract.json#/scope/in/0` or
`spec-contract.json#/capability_operations/0`, and `acceptance_refs` to real
`spec-contract.json#/acceptance_criteria/N` values. Inspect those referenced
values and preserve the source rule's conditions, negations, permissions,
exceptions, and observable acceptance; pointing at generic scope prose is not
semantic coverage. Keep each mapping consistent with `acceptance_coverage`.

For `context`, `deferred`, `out_of_scope`, and `duplicate`, retain the source
ID/disposition with empty `requirement_refs` and `acceptance_refs`; a duplicate
also preserves exact `duplicate_of`, resolving to an existing retained REQ
without cycles. Decision sources, reasons, and reopen conditions remain bound
in the upstream source ledger. An unresolved source rule blocks readiness.
Never remove an upstream REQ to make the coverage count agree. Do not retell or
reextract unchanged original sources: verify complete mappings by stable refs
and return true omissions or interpretation conflicts to their owning phase.

## Project Cognition Advisory Gate

This planning-only command should treat the project cognition runtime as an
advisory navigation index, not a mandatory pre-source gate.

### Advisory Rule

Use project cognition when available to find likely owners, affected paths,
risks, verification routes, and minimal live reads. Do not treat map output as
evidence by itself. Technical claims must be backed by live code, tests,
scripts, configuration, or authoritative docs.

### Required Project Cognition Compass

Default project cognition intake is `project-cognition compass --intent <intent> --query="$ARGUMENTS" --format json`.

Consume the packet in this order:

1. Read top-level `epistemic_contract` first. Require `graph_role=route_candidate_only`, `fact_source_of_truth=live_repository`, `live_verification_required=true`, `graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`.
2. Read top-level `minimal_live_reads` and use those files as the bounded first live evidence route.
3. Then use lane-level `first_pass_paths` for reasons, evidence hints, verification hints, follow-up surfaces, and `before_fix_claim` checks.
4. Read lane-level `claim_refs` only as compact route candidates. `route_confidence` is scoped by `confidence_scope=route_candidate`; inspect each claim's `state`, `freshness`, and `stale` marker, and require live verification before using it as repository truth.
5. Treat `coverage_diagnostics` as confidence and closeout signals, never as route candidates.
6. Treat `expansion_ref` as a normal continuation path. Run `project-cognition expand --id <id> --section claim_evidence --format json` when an active claim needs its bounded `source_path`/`span` evidence; use other sections only when coverage state or live evidence requires more map detail. Advanced `project-cognition query` may also return top-level `claim_signals` with bounded evidence refs.
7. Do not infer final edit scope from `minimal_live_reads`, `first_pass_paths`, `claim_refs`, `claim_signals`, or `claim_evidence`.

Compass applies graph claims only as a bounded rerank after repository-backed route eligibility is established. `match_score` remains the eligibility score; lane `claim_ranking.adjustment` may only move an already-matched candidate by `+1` for fresh `supported`/`verified_in_graph_generation`, `-1` for stale, or `-2` for contradicted. Claims cannot create candidates and cannot replace live verification. When `coverage_diagnostics` contains `stale_claim_signal` or `contradicted_claim_signal`, treat the packet as `usable_with_review`, follow `reconcile_claims_with_minimal_live_reads`, and complete the lane-specific refresh or reconciliation action against the live repository.

For a selected stale or contradicted claim, open only the returned claim-specific bounded live reads. If those reads are decisive, provide only reconciliation intent: workflow, stable `claim_id`, reason, and evidence with repository-relative `source_path`, bounded line `span`, and `supporting` or `contradicting` role, plus optional claim-specific verification. Run `project-cognition claim-reconcile prepare --input <intent.json> --format json`. The runtime owns the contract version, active generation, expected state and revision, UTC observation and expiry, source kind, file hashes, repository snapshot, IDs, and prepared packet path; do not author or edit those integrity fields. Execute the returned `apply_argv` exactly; it invokes `project-cognition claim-reconcile apply --input <prepared_packet_path> --format json`. A generic workflow verification is insufficient. On `result_state=ready`, rerun Compass once and use the new packet only for planning routes; on partial or blocked output, withhold the claim and follow `recommended_next_action`.

The `epistemic_contract` cannot authorize source changes and cannot prove current behavior. Carry `epistemic_contract` into planning state, withhold unverified requirements or implementation facts, and let contradictory live evidence override the route candidate.

Graph claims are indexed assertions. Their lifecycle is `candidate`, `supported`, `verified_in_graph_generation`, `contradicted`, or `stale`; even `verified_in_graph_generation` is only an active graph-generation state, not current repository truth. Graph claims cannot authorize source changes and cannot set workflow `claim_ready=true`; open bounded live evidence and run matching workflow claim-specific verification before any final claim.

Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`. Compass-specific advice is in `compass_state` and `recommended_next_action`.

- `query_ready`: read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons before expanding.
- `review`: inspect the returned `minimal_live_reads` before expanding and carry review notes from `coverage_diagnostics`.
- `needs_rebuild`: reserve `{{invoke:map-scan}} -> {{invoke:map-build}}` for documented brownfield rebuild triggers.
- `blocked`: report the runtime state clearly; continue with live evidence only when this workflow allows degraded advisory navigation.
- `unsupported_runtime`: continue with live evidence and record that compass intake was unavailable.

When `compass_state=needs_semantic_intake`, the agent writes `semantic_intake` from project vocabulary and reruns compass with `--semantic-intake-file`, or uses the advanced `lexicon -> semantic_intake -> query` path when explicit concept decisions are needed.

### Advanced Routing

Advanced routing remains available as `project-cognition lexicon --mode catalog`, agent-authored `semantic_intake` and `concept_decisions`, then `project-cognition query --query-plan`. Use it when the first compass packet is too draft-like, a workflow needs explicit concept decisions, or coverage cannot be resolved from the default packet.

The advanced `lexicon -> semantic_intake -> query` path retrieves the schema v5 `alias_index`-backed alias catalog, helps agents normalize user input into project vocabulary, records `alias_interpretations`, selects task-relevant `selected_concepts`, records unsafe or irrelevant `rejected_concepts`, writes per-concept `concept_decisions`, carries `lexicon_generation_id` and `candidate_universe_version`, and then runs `project-cognition query --query-plan`. The current query contract is `claim_retrieval_contract_version=2` and `candidate_universe_version=2`. Never parse missing or non-current versions as legacy input; rerun lexicon or compass with the current binary and repair the install if needed. Schema v5 is current-only. The current runtime does not migrate schema v4 or older databases and does not archive or replace them. Remove the incompatible project-cognition.db explicitly, then run `sp-map-scan -> sp-map-build` with the current binary. When writing the recommendation in plain text, use: run sp-map-scan -> sp-map-build.

If `project-cognition query` reports query-plan diagnostics, carry forward its `warnings`, `repair_hints`, normalized `query_plan`, structured `errors`, and `expected_shape` instead of reducing them to a raw parser exception.

### Agent-Owned Semantic Normalization

Agent-owned semantic normalization is mandatory for the advanced path. The raw lexicon ranking and `agent_normalization` are only bootstrap signals for retrieving the alias catalog and candidate universe; they are not route decisions. Raw lexicon ranking is only a bootstrap. Treat `agent_normalization.required=true` as a non-intelligent CLI reminder to write `semantic_intake` from the alias catalog (action: write_semantic_intake_from_alias_catalog). If `agent_normalization` is omitted, `omitted => required=false`: treat it as `required=false`; omission does not make raw lexical ranking authoritative. If raw `concept_candidates` are all `score=0`, or the prompt is localized, mixed-language, CJK, colloquial, symptom-first, or mixed-language or CJK text, do not stop at the raw score. CJK or mixed CJK/ASCII input still requires agent normalization even when positive raw lexical matches exist because embedded project tokens do not translate the surrounding user language. Extract embedded project terms such as command names, UI labels, file stems, state names, adapter names, and skill or package identifiers from the user's wording and the alias catalog. The agent still owns translation; `agent_normalization` is advisory guidance, not a route decision. Put those translated terms into `normalized_query`, `alias_interpretations`, `intent_facets`, `expanded_queries`, and `repository_search_terms`, then select or reject concepts by facet coverage.

Use this canonical query-plan skeleton when shaping `<query_plan_json>`. Keep `alias_interpretations` as an array of objects, not strings:

```json
{
  "raw_query": "$ARGUMENTS",
  "candidate_universe_version": 2,
  "semantic_intake": {
    "workflow_intent": "<active workflow intent>",
    "normalized_query": "<project-language interpretation>",
    "intent_facets": ["<facet the selected concept must cover>"],
    "negative_constraints": ["<scope boundary not to treat as route truth>"],
    "alias_interpretations": [
      {"alias": "<user term>", "meaning": "<project term>", "confidence": "medium"}
    ],
    "open_semantic_questions": []
  },
  "selected_concepts": ["<concept id from lexicon payload>"],
  "rejected_concepts": ["<considered concept id>"],
  "concept_decisions": [
    {
      "concept_id": "<concept id>",
      "decision": "selected",
      "selection_reason": "<facet-coverage rationale>",
      "covered_facets": ["<covered facet>"],
      "missing_facets": [],
      "match_sources": ["alias", "semantic_intake"],
      "confidence": "medium",
      "risk": ""
    }
  ],
  "lexicon_generation_id": "<lexicon_generation_id from lexicon payload>",
  "expanded_queries": ["<normalized project-language query>"],
  "repository_search_terms": ["<project-local term to search before raw wording>"],
  "paths": ["<justified path hint>"]
}
```

### Project-Language Search Terms

Before any source search, turn the user's wording into project-language search terms derived from the alias catalog, `semantic_intake`, selected candidates, and returned route metadata. Write these as `repository_search_terms` in the query plan or workflow notes. Include component names, state names, file names, command names, UI labels, and route names when the lexicon or candidate payload exposes them.

Do not search only the raw user words. If the user's phrase has no direct code match, use `normalized_query`, `alias_interpretations`, candidate titles, candidate aliases, `matched_terms`, `colloquial_matches`, returned paths, and `expanded_queries` to form the first search set. Use these project-language search terms before broad repository search; only widen after the translated terms and returned `minimal_live_reads` fail to identify the owner.

### Concept Selection

`concept_candidates` are not a flat keyword list. Treat them as structured project concept candidates with ownership, route, alias, `matched_terms`, `colloquial_matches`, domain, disambiguation, and confidence signals. Select concepts that match the user's intent and the workflow objective, reject concepts that are unrelated or unsafe to assume, and preserve the `selection_reason` and `concept_decisions` so downstream artifacts can understand why the query was bounded that way. Each `concept_decisions` entry should record `covered_facets`, `missing_facets`, `match_sources`, confidence, and risk. Candidate selection must satisfy facet coverage for the active workflow; do not trust top similarity alone, whether the match came from lexical overlap, vector similarity, aliases, paths, or graph-neighbor expansion.

When candidate concepts conflict, are too broad, or remain unknown, follow the returned compass state instead of guessing. Do not bypass `route_pack`, `minimal_live_reads`, or `first_pass_paths` by expanding into broad repository reads merely because a candidate concept looks interesting.

### Fixed Bundle Consumption

Every workflow must consume the readiness and task-local bundle returned by the project cognition compass packet explicitly required by its command contract. Treat the compass packet as the task-local project navigation bundle. Treat raw graph JSON artifacts as obsolete runtime surfaces. Do not replace bundle consumption with broad freeform repository rereads when the runtime already covers the touched area.

### Query Completion

A project-cognition compass intake is not complete when it returns JSON. It is complete only when readiness drives routing, minimal_live_reads constrains inspection, lane-level `first_pass_paths` reasons are considered, and relevant facts are carried into the next workflow artifact or execution state.

Extract and carry forward the selected concepts, rejected concepts, `selection_reason`, `semantic_intake`, `normalized_query`, `intent_facets`, `negative_constraints`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, matched capability or symptom, affected nodes and subgraph, `route_pack`, `minimal_live_reads`, `first_pass_paths`, `coverage_diagnostics`, missing coverage, evidence traces, verification routes, ambiguity, conflicts, and weak coverage.

### Command Tier Depth

Tier determines how deeply the workflow must continue through the returned bundle
and minimal live reads after the minimum gate, not whether it may skip cognition-runtime consumption.

- `trivial`: minimum required artifact set only
- `light`: minimum artifact set plus relevant routing or playbook artifacts
- `heavy`: minimum artifact set plus all relevant collaboration, propagation, and verification artifacts

### Freshness

Treat runtime freshness as map-quality diagnostics:

- `fresh` -> use the returned task-local bundle as an advisory first pass navigation aid
- `missing` -> if cognition freshness is `missing`, continue with live repository evidence when workflow policy allows degraded advisory navigation; recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only as follow-up brownfield first-baseline maintenance unless the user explicitly requested cognition repair or the workflow truly cannot proceed without a usable baseline
- `stale` -> if cognition freshness is `stale`, treat map output as advisory and continue with live repository evidence; recommend `{{invoke:map-update}}` as external/manual maintenance
- `stale` with changed paths missing from `path_index` -> warn and continue with live repository evidence; recommend `{{invoke:map-update}}` first for ordinary existing-baseline gaps.
  Use `{{invoke:map-scan}} -> {{invoke:map-build}}` only for brownfield first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows outside baseline-kind exceptions described below, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`
- `support_drift` -> warn and continue with live repository evidence; recommend resolving or intentionally ignoring support-surface drift
- `partial_refresh` -> warn that refresh data was recorded but readiness did not pass; continue with live repository evidence
- `possibly_stale` -> inspect the returned affected scope when useful, then continue with live repository evidence

Preserve the distinction between the machine freshness field and public state
guidance: `freshness` records map quality, while `recommended_next_action` is a
map-maintenance recommendation.

Entry-time stale or weak cognition is still an advisory navigation concern unless the user explicitly requested map maintenance. That entry routing rule does not waive closeout ownership.

Planning-only artifact writes do not require project cognition refresh. If this planning workflow makes actual source/runtime/template/config/test/generated-asset changes in the current run, follow the shared inline closeout contract:

{{spec-kit-include: inline-project-cognition-update.md}}

### Greenfield Empty Baseline

If `baseline_kind=greenfield_empty`, continue with workflow artifacts and live requirements. Do not recommend map-scan -> map-build solely because the graph has no paths.

### Primary Read Restriction

Do not treat handbook-first or layered project-map files as evidence. If
query-returned coverage is insufficient, inspect live repository surfaces
directly and recommend `sp-map-update` for ordinary existing-baseline gaps,
localized stale cognition refresh, weak localized coverage after a usable
baseline, or external/manual changed-path map maintenance. Use `sp-map-scan -> sp-map-build`
only for brownfield first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation
`path_index` rows outside `greenfield_empty`, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.

The completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs. Project cognition can support route selection but cannot be the sole evidence for completion.

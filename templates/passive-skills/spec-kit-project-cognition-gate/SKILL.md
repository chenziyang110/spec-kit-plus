---
name: spec-kit-project-cognition-gate
description: "Use when changing, reviewing, planning against, or debugging an existing Spec Kit Plus codebase. Consult the agent-planned project cognition query bundle as advisory navigation, then prove technical claims from live evidence."
origin: spec-kit-plus
---

# Spec Kit Project Cognition Gate

This passive skill is the brownfield advisory navigation layer, not a hard workflow gate.

## Complementary Passive Skills

- `spec-kit-workflow-routing` owns route selection into the correct `sp-*` workflow
  before implementation, planning, or debugging proceeds.
- `spec-kit-project-learning` owns the shared memory capture layer after context is
  loaded. Once this gate is satisfied, follow that skill's learning-start and
  learning-capture expectations for the active workflow.

## Advisory Navigation

Before code edits, investigation, planning against existing code, or architectural
judgment in an established Spec Kit Plus repository:

- Default project cognition intake is `project-cognition compass --intent <intent> --query="$ARGUMENTS" --format json`.
  Consume the packet in this order:
  1. Read top-level `epistemic_contract` first. Require `graph_role=route_candidate_only`, `fact_source_of_truth=live_repository`, `live_verification_required=true`, `graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`.
  2. Read top-level `minimal_live_reads` and use those files as the bounded first live evidence route.
  3. Then use lane-level `first_pass_paths` for reasons, evidence hints, verification hints, follow-up surfaces, and `before_fix_claim` checks.
  4. Read lane-level `claim_refs` only as compact route candidates. `route_confidence` is scoped by `confidence_scope=route_candidate`; inspect `state`, `freshness`, and `stale`, and require live verification before using a claim as repository truth.
  5. Treat `coverage_diagnostics` as confidence and closeout signals, never as route candidates.
  6. Treat `expansion_ref` as a normal continuation path. Run `project-cognition expand --id <id> --section claim_evidence --format json` when an active claim needs bounded `source_path`/`span` evidence; advanced `project-cognition query` may also return top-level `claim_signals` with bounded evidence refs.
  7. Do not infer final edit scope from `minimal_live_reads`, `first_pass_paths`, `claim_refs`, `claim_signals`, or `claim_evidence`.
  Compass applies graph claims only as a bounded rerank after repository-backed route eligibility is established. `match_score` remains the eligibility score; lane `claim_ranking.adjustment` may only move an already-matched candidate by `+1` for fresh `supported`/`verified_in_graph_generation`, `-1` for stale, or `-2` for contradicted. Claims cannot create candidates and cannot replace live verification. When `coverage_diagnostics` contains `stale_claim_signal` or `contradicted_claim_signal`, treat the packet as `usable_with_review`, follow `reconcile_claims_with_minimal_live_reads`, and complete the lane-specific refresh or reconciliation action against the live repository.
  For decisive claim-specific evidence, provide only reconciliation intent: workflow, stable `claim_id`, reason, repository-relative `source_path`, bounded line `span`, `supporting` or `contradicting` role, and optional claim-specific verification. Run `project-cognition claim-reconcile prepare --input <intent.json> --format json`; the runtime owns every integrity field and the prepared packet path. Execute the returned `apply_argv` exactly (`project-cognition claim-reconcile apply --input <prepared_packet_path> --format json`). Generic workflow verification is insufficient. On ready, rerun Compass once; on partial or blocked, withhold the claim.
  The `epistemic_contract` cannot authorize source changes and cannot prove current behavior. Carry `epistemic_contract` forward, withhold unverified claims, and let contradictory live evidence override the route candidate.
  Graph claims are indexed assertions. Even `verified_in_graph_generation` is only an active graph-generation state, not current repository truth; graph claims cannot authorize source changes and cannot set workflow `claim_ready=true`. Treat `candidate` and `supported` as navigation hypotheses, and `contradicted` or `stale` as negative-route or historical context until bounded live evidence is checked.
  Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`. Compass-specific advice is in `compass_state` and `recommended_next_action`.
  When `compass_state=needs_semantic_intake`, the agent writes `semantic_intake` from project vocabulary and reruns compass with `--semantic-intake-file`, or uses the advanced `lexicon -> semantic_intake -> query` path when explicit concept decisions are needed.
  Advanced routing remains available as `project-cognition lexicon --mode catalog`, agent-authored `semantic_intake` and `concept_decisions`, then `project-cognition query --query-plan`. Use it when the first compass packet is too draft-like, a workflow needs explicit concept decisions, or coverage cannot be resolved from the default packet.
  The current query contract is `claim_retrieval_contract_version=2` and `candidate_universe_version=2`; carry the latter from lexicon into every explicit query plan. Never parse missing or non-current versions as legacy input; rerun lexicon or compass with the current binary and repair the install if needed.
  The advanced path still requires `normalized_query`, `intent_facets`, `negative_constraints`, `alias_interpretations`, `selected_concepts`, `rejected_concepts`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `expanded_queries`, `repository_search_terms`, and facet coverage; do not trust top similarity alone.
  If the query command reports query-plan diagnostics, preserve its `warnings`, `repair_hints`, normalized `query_plan`, structured `errors`, and `expected_shape` so the workflow can repair the plan instead of ending on a raw parser exception.
  Agent-owned semantic normalization is mandatory for the advanced path. The raw lexicon ranking and `agent_normalization` are only bootstrap signals for retrieving the alias catalog and candidate universe; they are not route decisions. Raw lexicon ranking is only a bootstrap. Treat `agent_normalization.required=true` as a non-intelligent CLI reminder to write `semantic_intake` from the alias catalog (action: write_semantic_intake_from_alias_catalog). If `agent_normalization` is omitted, `omitted => required=false`: treat it as `required=false`; omission does not make raw lexical ranking authoritative. If raw `concept_candidates` are all `score=0`, or the prompt is localized, mixed-language, CJK, colloquial, symptom-first, or mixed-language or CJK text, do not stop at the raw score. CJK or mixed CJK/ASCII input still requires agent normalization even when positive raw lexical matches exist because embedded project tokens do not translate the surrounding user language. Extract embedded project terms such as command names, UI labels, file stems, state names, adapter names, and skill or package identifiers from the user's wording and the alias catalog. The agent still owns translation; `agent_normalization` is advisory guidance, not a route decision. Put those translated terms into `normalized_query`, `alias_interpretations`, `intent_facets`, `expanded_queries`, and `repository_search_terms`, then select or reject concepts by facet coverage.
  Before source search, write project-language search terms derived from the alias catalog, `semantic_intake`, selected candidates, and route metadata. Write them as `repository_search_terms`; include component names, state names, file names, command names, UI labels, and route names when present. Do not search only the raw user words. Use these project-language search terms before broad repository search.
- Treat `concept_candidates` as structured project concept candidates, not a
  flat keyword list. Resolve broad, conflicting, or unknown candidates through
  the returned readiness state; do not widen live repository reads beyond the
  returned `route_pack` and `minimal_live_reads`.
- For `sp-ask`, use `project-cognition compass --intent ask --query="$ARGUMENTS" --format json`
  as the default advisory navigation command. Use
  `project-cognition query --intent ask` only after the agent builds a semantic
  intake or query plan because the compass output or live evidence is ambiguous
  or has incomplete coverage. Stale or localization-sensitive cases are examples
  that still require that ambiguity or incomplete-coverage reason. Live evidence
  is authoritative. The ask route is read-only: do not run tests, run builds,
  execute project CLI commands, write files, create handoffs, or create ask
  state.
- For same-topic `sp-ask` follow-ups in the same chat, reuse the previous target
  project root, evidence set, compass or query packet, semantic intake, and
  proven facts when they still cover the new question; read only delta evidence
  and rerun compass when the topic, target, boundary, or evidence family changes.
- For localized, mixed-language, CJK, colloquial, or project-slang ask queries,
  normalize terms through the alias catalog and write project-language search
  terms before source search. For cross-boundary questions, include the protocol
  view: client fields or callsites, interface URLs or payload/schema names, and
  whether backend/server/runtime code exists in the repository.
- Treat the task-local project cognition compass packet as the task-local
  project navigation bundle. Treat raw graph JSON artifacts as obsolete runtime surfaces;
  use `.specify/project-cognition/project-cognition.db`, the compass packet,
  and bounded live evidence instead.
- Candidate selection must satisfy facet coverage for the active workflow. Each
  `concept_decisions` item should include `covered_facets`, `missing_facets`,
  `match_sources`, confidence, and risk. Do not trust top similarity alone:
  lexical overlap, vector similarity, alias matches, path matches, and graph
  neighbor expansion are signals, not route truth.
- For `sp-discussion`, product framing may begin before the cognition gate. Before
  technical options, affected-surface claims, testing strategy claims tied to
  existing code, implementation-path recommendations, or source-grounded
  recommendations, complete the workflow's Truth Pass with the active
  launcher-backed project cognition query planning flow and bounded live evidence.
  Use `project-cognition compass --intent discussion --query="$ARGUMENTS" --format json` and
  preserve `project-cognition query --intent discussion` as the advanced precision path for discussion grounding. Record
  `verified_project_facts`, `open_assumptions`, `evidence_checked`, and
  `advice_confidence`. Do not use `--intent plan` from `sp-discussion`.
- Project cognition is project-scoped. Current project cognition proves only
  current project facts.
- In `sp-discussion`, if the implementation target is another repository or
  external project, lock `target_project_root` before source-grounded technical
  claims.
- Reference project cognition is supplemental-only and cannot replace target
  evidence.
- If target root is unknown, block technical options and handoff readiness;
  continue only with product framing and explicit unknowns.
- If target root is known but target cognition is stale or missing, use target
  cognition, minimal live reads in the target, user confirmation, or explicit
  assumptions. Do not ask the user to rebuild current-project cognition for
  target files.
- Treat project cognition as advisory navigation and coverage metadata. Use it
  to choose minimal live reads, ownership hints, consumers, state surfaces,
  verification routes, and coverage gaps. Do not treat it as authoritative
  evidence for current behavior; prove project facts from live repository files.
- A project-cognition compass intake is not complete when it returns JSON. It is complete
  only when readiness is interpreted as advisory navigation, `minimal_live_reads`
  constrains inspection, lane-level `first_pass_paths` reasons are considered,
  live evidence proves technical claims, and relevant facts are carried into the
  next workflow artifact or execution state.
- Extract and carry forward `selected_concepts`, `rejected_concepts`,
  `selection_reason`, `semantic_intake`, `normalized_query`, `intent_facets`,
  `negative_constraints`, `concept_decisions`, `covered_facets`,
  `missing_facets`, `match_sources`, `lexicon_generation_id`, the matched
  capability or symptom, affected nodes and subgraph, `route_pack`,
  `minimal_live_reads`, `first_pass_paths`, `coverage_diagnostics`, missing coverage, evidence traces, verification routes,
  ambiguity, conflicts, and weak coverage.
- Treat project cognition under `.specify/project-cognition/` as an advisory navigation surface. Legacy project-map exports are not evidence for current project behavior and `templates/project-map/**` is historical compatibility/export only.
- Consume project rules and reusable Learning through `specify learning start -> list -> show`; do not parse Learning storage as part of cognition intake.

## Cross-Project Reference Directories

- When inspecting or comparing another local directory, check whether that
  directory or its children contain `.specify/` first. A referenced directory may
  be a downstream Spec Kit project even when it is outside the current repo.
- Prefer `project-cognition discover --root <path> --format json` to enumerate nested
  `.specify/` candidates before broad live reads. Treat its `projects` entries as
  project-cognition candidates and its `specify_candidates` entries as the
  broader set of Spec Kit-shaped directories.
- Use another project's cognition only when
  `.specify/project-cognition/status.json` exists,
  `.specify/project-cognition/project-cognition.db` exists,
  `reference_readiness` is `ready`, freshness is `fresh`, and `graph_ready` is
  true.
- For ready references, read only the fresh project cognition artifacts needed
  for the comparison, then use the returned minimal read order before inspecting
  more source files. Treat the reference map as supplemental navigation, not as
  evidence by itself.
- For blocked, stale, or incomplete references, do not treat legacy
  `.specify/project-map/**` outputs as current truth. Fall back to minimal live
  reads and recommend `{{invoke:map-update}}` for localized stale coverage, weak
  reference coverage, external/manual changed-path map maintenance, or ordinary
  existing-baseline gaps after a usable reference baseline.
- For brownfield missing or unusable reference baselines, recommend
  `{{invoke:map-scan}} -> {{invoke:map-build}}`. Recommend scan/build for a
  reference project only for brownfield first/missing/unusable baseline, schema
  failure, zero active-generation `path_index` rows outside `greenfield_empty`,
  `explicit_rebuild_requested`, or `baseline_identity_invalid`.

## Command Surface Discipline

- Treat the live `specify --help` output as the only authoritative CLI command surface.
- Before suggesting or running a `specify <subcommand>` invocation while satisfying this gate, verify that it exists in `specify --help` or `specify <subcommand> --help`.
- Do not invent, paraphrase, or "normalize" unsupported CLI names such as `specify create-feature`.
- Feature creation remains `{{invoke:specify}}` plus the generated create-feature script at `.specify/scripts/bash/create-new-feature.sh` or `.specify/scripts/powershell/create-new-feature.ps1`, not a separate branch-creation command. Default feature workspace names use `YYYY-MM-DD-<slug>`; numeric prefixes are legacy and require the script's explicit numeric option.

## Missing Runtime Launcher Recovery

- If an installed cognition command begins with the all-caps
  `PROJECT_COGNITION_LAUNCHER_UNAVAILABLE` marker, treat the complete marked
  command as non-executable. The suffix only preserves the intended cognition
  subcommand so managed guidance can be rebound after repair.
- Do not probe `specify cognition` or `specify project-cognition`. Run
  `{{specify-subcmd:check}}` for project-pinned diagnostics, then run
  `{{specify-subcmd:integration repair}}` as the deterministic recovery entry.
  Re-open the active installed skill after repair; if the marker remains,
  report cognition unavailable and continue from live repository evidence only
  where the workflow's safety boundary permits degraded advisory navigation.

## Freshness State Guidance

- If the project cognition runtime is missing for a brownfield project, continue with live repository
  evidence and recommend the canonical `sp-map-scan -> sp-map-build` workflow only as
  external baseline maintenance. When giving the user an explicit command to type, write
  `{{invoke:map-scan}} -> {{invoke:map-build}}`.
- If `baseline_kind=greenfield_empty`, continue with workflow artifacts and live requirements. Do not recommend map-scan -> map-build solely because the graph has no paths.
- If the project cognition runtime is stale for a localized touched area, continue
  with live repository evidence and recommend `sp-map-update` first when map
  maintenance is useful. When giving the user an explicit
  command to type, write `{{invoke:map-update}}`.
- If changed paths are missing from project cognition `path_index`, let
  `sp-map-update` classify the gap first. Adoptable paths get provisional
  `path_index` plus `alias_index` coverage, uncertain paths return
  `minimal_live_reads`, and ordinary existing-baseline gaps stay in
  `{{invoke:map-update}}`.
- Treat repository boundary accounting as separate from graph evidence. `.cognitionignore` exclusions and automatic exclusions explain why a path is outside graph-facing coverage; they do not become project cognition evidence.
- For `map-update`, changed-path accounting must explain every candidate path before readiness can be considered useful.
- If the freshness state is `support_drift`, stop and tell the user to resolve
  support-surface drift; do not reflexively route to `sp-map-update`.
- If the freshness state is `partial_refresh`, tell the user the refresh was
  recorded but readiness did not pass; follow the reported
  `recommended_next_action` instead of implying success.
- If `partial_refresh` follows `sp-map-update` and validation shows bounded
  path-led `identity_reconciliation` debt, the next action is a focused
  identity-repair pass inside `sp-map-update`, not an immediate user choice
  between repair and full rebuild. Escalate to `sp-map-scan -> sp-map-build`
  only when validation reports a reserved rebuild condition such as unusable
  baseline, schema failure, zero active-generation path index rows outside
  `greenfield_empty`, missing or invalid `alias_index`,
  `explicit_rebuild_requested`, or `baseline_identity_invalid`.
- If project cognition readiness is `blocked`, report the runtime issue as
  degraded advisory map state. Ordinary discussion may continue with product
  framing or bounded live evidence; recommend a map maintenance workflow only
  when the user asks for map maintenance or handoff needs evidence that live
  reads cannot provide.
- Preserve the distinction between the machine freshness field and public state
  guidance: `freshness` records factual state, while `recommended_next_action`
  tells the operator what to do next.
- Use `map-update` for ordinary existing-baseline gaps. Use `map-scan -> map-build`
  only for brownfield first/missing/unusable baseline, schema failure, schema v1
  or old broad-schema rebuild-required readiness, zero active-generation
  path_index rows outside `greenfield_empty`, missing or invalid `alias_index`,
  `explicit_rebuild_requested`, or `baseline_identity_invalid`.
  Schema v5 is current-only. The runtime does not migrate schema v4 or older
  databases and does not archive or replace them. Remove the incompatible project-cognition.db
  explicitly before `sp-map-scan -> sp-map-build` with the current binary.
  Uncertain closure can be recorded by `sp-map-update` as partial/low-confidence
  facts, known unknowns, and `minimal_live_reads`.
- Entry-time stale or weak cognition is still an advisory navigation concern unless the user explicitly requested map maintenance. A workflow may continue from live evidence when entry guidance allows it. That entry routing rule does not waive closeout ownership.
- Workflow-owned mutation closeout is not an external map-maintenance handoff. If the active workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, or behavior-bearing docs, closeout must run `project-cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --format json` before recording inline project cognition update data.
- When `DELTA_SESSION_ID` exists, pass `--delta-session "$DELTA_SESSION_ID"` to `closeout-plan`. Fill fields listed in `required_agent_fields` from live evidence; optional payload/delta fields such as `known_unknowns` and `boundary` are populated only when evidence supports them. Follow `update_mode=delta_session` by completing `delta_append_draft.argv_prefix` with evidence placeholders, appending the workflow closeout delta event, then running structured `update_argv`. Follow `update_mode=payload_file` by writing the completed `payload_draft`, then running structured `update_argv`. The display-only `update_command` and display-only `delta_append_command` placeholders are not execution strings.
- Use `known_unknowns` only for blockers that make the cognition update unsafe to trust. If the working tree contains unrelated dirty/untracked paths and the workflow uses explicit workflow-owned paths, record that as `confidence_notes` or `boundary.initial_dirty_paths`, not as a blocking `known_unknowns` item.
- Before update recording, resolve `unknown_path_dispositions` by setting `agent_disposition` to `adoptable`, `review_only`, `ignored`, or `blocking_known_unknown`. Verified `adoptable` paths do not become blocking `known_unknowns`. Only `blocking_known_unknown` dispositions become payload or delta known unknowns. `agent_disposition=adoptable` is an agent accounting decision, not proof that runtime indexing already succeeded; after `update_argv` runs, inspect `result_state`, `adopted_paths`, `review_paths`, `minimal_live_reads`, and `partial_refresh_reasons`.
- Clean closeout keys on `result_state`, not `status=ok`, `update_id`, `last_update_id`, or freshness alone; `recorded` is legacy recorded-only partial/blocked output. If `partial_refresh_reasons` includes `missing_passing_verification_result`, repair the payload or delta evidence and rerun `update_argv` before final closeout instead of routing to `sp-map-update`. Never run the `complete-refresh` or `clear-dirty` helper after `result_state=partial_refresh`, `needs_rebuild`, `blocked`, or legacy `recorded`. Use `project-cognition mark-dirty --reason "workflow-closeout-failed" --format json` only when planner/update is unavailable, fails before recording useful update data, cannot safely identify workflow-owned scope, is blocked by runtime state, or verification/workflow completion is not trustworthy.
- `sp-map-update` is for manual/external maintenance and follow-up repair after user edits, interrupted workflows, or explicit operator map-maintenance requests. It is external map maintenance, not routine cleanup for changes this workflow just made. In shared routing summaries, sp-map-update is for manual/external maintenance.
- Do not rely on generic framework instinct, chat memory, or prior sessions when the
  project cognition runtime should be the source of truth.

## Senior Consequence Analysis Relationship

Project cognition is necessary but not sufficient. Use it first to identify ownership, consumers, state surfaces, verification routes, and coverage gaps. Then run the Senior Consequence Analysis Gate when lifecycle, running-state, destructive-operation, shared-state, downstream consumer, compatibility, or multiple-behavior semantics matter.

The gate output must name affected objects, state behavior, dependency impact, recovery and validation, and coverage gaps. Preserve the Affected Object Map, State-Behavior Matrix, Dependency Impact Table, Recovery And Validation Contract, and Coverage Gaps. If project cognition cannot decide product semantics, record the gap and route to the appropriate workflow instead of treating the graph as authoritative.

## Scope Guard

- This gate applies even if the user asks for a direct code change without mentioning
  Spec Kit workflows.
- Stand down only when the task is clearly greenfield and does not depend on any
  existing project structure, conventions, or runtime surface.

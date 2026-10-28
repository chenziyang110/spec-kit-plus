{{spec-kit-include: ../common/user-input.md}}

## Objective

Answer project questions with evidence-backed, read-only project Q&A.

## Context

- Primary inputs: the user's project question, project memory, generated state, docs, templates, live files, and specify-runtime cognition navigation output.
- Project cognition provides advisory navigation. Live evidence is authoritative.
- Read and carry `epistemic_contract`; require `graph_role=route_candidate_only`, `fact_source_of_truth=live_repository`, `live_verification_required=true`, `graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`. It cannot authorize source changes and cannot prove current behavior.
- This workflow answers questions only; it does not create implementation, discussion, debug, or planning state.

## Process

- Classify the user's question.
- Detect whether the question is a same-topic follow-up in the current chat. Reuse the previous evidence set only after the valid-capsule check below; read only delta evidence needed for the new point. Chat continuity alone is not evidence of fresh cognition or unchanged source.
- For non-trivial questions, give the user a one-sentence evidence route before live reads, such as the two or three surfaces you will check. Keep it short and do not turn it into a plan artifact.
- Use project cognition to find the smallest likely evidence set.
- Normalize localized, mixed-language, CJK, colloquial, or project-slang terms into project vocabulary before source search. Use the alias catalog, candidate concepts, returned paths, and live hits to build project-language search terms; do not search only the raw user words.
- Read only the live evidence needed to prove the answer, adding protocol or interface evidence when the question crosses client/server, package/installer/runtime, API, plugin, or integration boundaries.
- Answer directly, then recommend another workflow only when the user needs action.

## Output Contract

- Provide a read-only answer with conclusion, evidence, uncertainty, and next step when useful.
- For complex answers, separate proven facts, inferences, and unknowns. Proven facts must be backed by live evidence; inferences must name the evidence they are derived from and what was not found.
- State when the available evidence cannot prove the answer.
- Keep the response natural and concise for simple questions, with short sections only when complexity requires them.

## Guardrails

- Do not mutate project files, workflow state, generated state, docs, templates, or memory.
- Do not create `.specify/ask/` or any ask handoff.
- Do not run tests, builds, package managers, app servers, or project CLI commands.
- Do not invoke another `sp-*` workflow automatically.

{{spec-kit-include: ../common/read-only-evidence-lanes.md}}

## Evidence-Backed Project Q&A

You answer project questions. The user's question may be rough, partial, bilingual, or based on an incorrect assumption.

Use this command when the user wants to know something about the project before choosing an action workflow.

For `sp-ask`, read-only evidence lanes are optional. Use leader-inline for simple questions, and use `choose_evidence_lane_dispatch(command_name="ask", snapshot, workload_shape)` only when the answer needs independent evidence packets from multiple files, docs, generated state, memory, or specify-runtime cognition routes.

## Read-Only Boundary

This workflow is read-only.

- Do not edit source files, tests, templates, docs, configs, generated state, or memory.
- Do not create `.specify/ask/`.
- Do not write handoff files.
- Do not run tests.
- Do not run builds.
- Do not run package managers.
- Do not launch apps or servers.
- Do not execute project CLI commands.
- Do not invoke another `sp-*` workflow automatically.

Allowed operations are narrow file reads, `rg`, project memory reads, generated-state reads, docs/template reads, and specify-runtime cognition navigation.

## Default Navigation

When no valid unchanged capsule is available, start with:

```text
{{specify-subcmd:specify-runtime cognition compass --intent ask --query="$ARGUMENTS" --format json}}
```

Treat project cognition as advisory navigation. Live evidence is authoritative.

Use `specify-runtime cognition query --intent ask` only after you build a semantic intake or query plan from the user's wording and the project vocabulary because the compass output or live evidence is ambiguous or has incomplete coverage. Stale or localization-sensitive results are examples that still require that ambiguity or incomplete-coverage reason.

```text
{{specify-subcmd:specify-runtime cognition query --intent ask --query-plan "<query_plan_json>" --format json}}
```

Pass the planned object as one structured argv value to `specify-runtime cognition query --intent ask --query-plan '<inline-json>' --format json`. When shell quoting is brittle, use the integration's native argument API; never create a query-plan file.

Use `specify-runtime cognition lexicon --intent ask --mode catalog --format json` only when you need vocabulary candidates before writing the query plan.

For localized, mixed-language, CJK, colloquial, or project-slang questions, agent-owned semantic normalization is mandatory before broad source search. Extract embedded project terms such as command names, UI labels, file stems, state names, adapter names, package names, extension names, and route names. Write `alias_interpretations`, `normalized_query`, `intent_facets`, `expanded_queries`, and `repository_search_terms` from the alias catalog and live hints before deciding what to read.

Same-topic follow-up mode:

- Use when the current user question is a direct continuation of the prior `sp-ask` answer in the same chat.
- Reuse the previous evidence set, target project root, compass or query packet,
  semantic intake, and proven facts only for the exact unchanged task/query,
  intent, target, scope/required facets, constraints, permissions, runtime, and
  relevant live-source/evidence digests. Keep `expansion_ref.id`,
  `query_fingerprint`, `active_generation_id`, `navigation_digest`, and versions.
- Before one unchanged phase pass reuses that capsule, require
  `cognition.expansion.snapshot.v2` from a bounded `api ensure` proof or one
  older-runtime `api list` fallback. Run one actual read-only
  `{{specify-subcmd:specify-runtime cognition expand --id <id> --section <section> --format json}}`
  with its ID and an available section such as `related_paths`. Require the
  inner payload's `status=ok`, usable `readiness=query_ready|review`,
  `expansion_contract_version=2`, matching ID,
  fingerprint, generation, and advisory `epistemic_contract`. A native outer
  exit code 0 alone is not proof. Missing, stale, incompatible, invalid, or
  failed expansion disables reuse; preserve its recovery action.
- Read only delta evidence for new claims, missing surfaces, changed terminology,
  or unresolved uncertainty. Rerun `specify-runtime cognition compass --intent ask`
  for changed task/query, topic, target, scope/facets, constraints, permissions,
  runtime, source/evidence, generation, status, or claim revision, contradictory
  evidence, and required resume/recovery. Preparatory API/artifact/board calls
  alone do not repeat intake or that unchanged Expand check.
- Learning applicability is separate: a graph digest cannot prove the Learning
  index, lesson source evidence, or project rules unchanged. Relevant lesson/rule
  drift or uncertain applicability refreshes the owning read-only Learning intake.
- In catalog precision escalation, require `cognition.catalog.snapshot.v1` and
  execute `catalog_page.next_argv` exactly while required facets remain unbound;
  preserve revision, snapshot proof, and counts. Stop only after all required
  owners, consumers/dependencies, verification routes, and negative constraints
  have valid bindings and live evidence, with ambiguity resolved. The first word
  match is insufficient. The project launcher may replace only the executable.
  Keep unresolved facets/index gaps explicit; stale snapshots restart intake.
  For required claim pages, require `cognition.claim-evidence.page.v1`, preserve
  `total_count`, `returned_count`, `offset`, and `has_more`, and consume `next_argv`
  exactly while needed. Capability IDs are not commands or write authority.

## Question Classifier

Classify the question before answering:

- `fact`: where something is, what exists, what changed, what config is active.
- `how_to`: how a project workflow, tool, script, or integration should be used.
- `why`: why the project behaves or is designed a certain way.
- `difference`: compare two workflows, files, commands, integrations, or states.
- `impact`: what will be affected if a change is made.
- `status`: whether a feature, artifact, release, map, or state is ready.
- `recommendation`: choose the best next step, with evidence.
- `concept`: explain project terminology or architecture.
- `history`: explain prior decisions from project files, templates, docs, generated state, memory, or project cognition.
- `boundary`: decide which workflow should handle the user's actual need.

## Evidence Rules

- Use project cognition to choose likely files; verify claims with live reads.
- Prefer the smallest evidence set that can answer the question.
- Quote or cite file paths when they materially support the answer.
- If the evidence conflicts, say which source wins and why.
- If the answer cannot be proven from available evidence, say that directly.
- If the user's question names a downstream project path, first establish the target project root before making claims about that project.
- For cross-boundary questions, check the relevant protocol view instead of only implementation files: client fields or callsites, interface URLs or payload/schema names, and whether backend/server/runtime code exists in the repository. If one side is absent, label downstream requirements as inferred rather than proven.

## Answer Shape

Answer naturally. Use only as much structure as the question needs.

Default shape:

1. Answer first.
2. Proven from live evidence.
3. Inferred from live evidence, when useful.
4. Unknowns or caveats.
5. Next step only when useful.

For simple questions, one short paragraph is enough. For complex questions, use short sections with human-readable names, not rigid audit labels.

## Routing Guidance

If the answer reveals that the user needs action, recommend one next workflow without invoking it:

- Use `sp-discussion` for product/design/requirement shaping.
- Use `sp-specify` when the user wants a formal specification before implementation.
- Use `sp-quick` for tracked direct implementation of a confirmed outcome, including larger or multi-capability work.
- Use `sp-fast` for minimal low-risk execution.
- Use `sp-debug` for root-cause diagnosis.
- Use `sp-deep-research` for feasibility proof or external evidence.
- Use `sp-explain` for explaining a specific generated artifact or stage output.
- Use `sp-map-update`, `sp-map-scan`, or `sp-map-build` only when specify-runtime cognition freshness or coverage itself is the subject.

Do not ask the user to say "continue" when the answer and recommended next step can be delivered in one response.

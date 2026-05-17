## Project Cognition Gate

This command must treat the project cognition runtime as the mandatory pre-source knowledge base.

### Hard Rule

Do not inspect implementation source, run reproduction or tests, compile a
plan, prepare a fix, or emit technical recommendations until the cognition gate has
passed.

### Required Project Cognition Query

Use the launcher-backed project cognition query planning flow required by this
command's workflow contract to retrieve the task-local project cognition bundle:
run `project-cognition lexicon`, inspect the returned `concept_candidates`,
select the task-relevant `selected_concepts`, record non-selected or unsafe
`rejected_concepts`, and write a `selection_reason` for both inclusion and
exclusion choices. Then construct a `query_plan` containing
`selected_concepts`, `rejected_concepts`, `expanded_queries`, and `paths`, and
run `project-cognition query --query-plan`. Treat raw graph JSON artifacts as obsolete runtime surfaces.

### Concept Selection

`concept_candidates` are not a flat keyword list. Treat them as structured
project concept candidates with ownership, route, alias, `matched_terms`,
`colloquial_matches`, domain, disambiguation, and confidence signals.
Select concepts that match the user's intent and the workflow objective, reject
concepts that are unrelated or unsafe to assume, and preserve the
`selection_reason` so downstream artifacts can understand why the query was
bounded that way.

When candidate concepts conflict, are too broad, or remain unknown, follow the
returned readiness state instead of guessing. Do not bypass `route_pack` or
`minimal_live_reads` by expanding into broad repository reads merely because a
candidate concept looks interesting.

### Fixed Bundle Consumption

Every workflow must consume the readiness and task-local bundle returned by the
project cognition query explicitly required by its command contract.
Do not replace bundle consumption with broad freeform repository rereads when the runtime already covers the touched area.

### Query Completion

A project-cognition query is not complete when it returns JSON. It is complete
only when readiness drives routing, minimal_live_reads constrains inspection,
and relevant facts are carried into the next workflow artifact or execution state.

Extract and carry forward the selected concepts, rejected concepts,
`selection_reason`, matched capability or symptom, affected nodes and subgraph,
`route_pack`, `minimal_live_reads`, missing coverage, evidence traces,
verification routes, ambiguity, conflicts, and weak coverage.

### Command Tier Depth

Tier determines how deeply the workflow must continue through the returned bundle
and minimal live reads after the minimum gate, not whether it may skip cognition-runtime consumption.

- `trivial`: minimum required artifact set only
- `light`: minimum artifact set plus relevant routing or playbook artifacts
- `heavy`: minimum artifact set plus all relevant collaboration, propagation, and verification artifacts

### Freshness

Treat runtime freshness as a gate:

- `missing` -> block and refresh through `sp-map-scan -> sp-map-build`
- `stale` -> block and refresh through `sp-map-update`
- `stale` with changed paths missing from `path_index` -> block and rebuild through `sp-map-scan -> sp-map-build`; repeating `sp-map-update` cannot create absent path coverage
- `support_drift` -> stop and tell the user to resolve support-surface drift; do not reflexively route to `sp-map-update`
- `partial_refresh` -> tell the user the refresh was recorded but readiness did not pass; follow `recommended_next_action`
- `possibly_stale` -> inspect the returned affected scope; if the touched area is not safely covered, route through `sp-map-update`

Preserve the distinction between the machine freshness field and public state
guidance: consume `freshness` as the factual state and use
`recommended_next_action` for the operator-facing next step.

### Primary Read Restriction

Do not treat handbook-first or layered project-map files as the primary runtime read surfaces. If query-returned
coverage is insufficient, refresh the cognition runtime through `sp-map-update`; reserve `sp-map-scan -> sp-map-build` for missing, unusable, schema-incompatible, explicitly rebuilt, or architecture-replaced baselines
instead of forcing a second handbook traversal phase.

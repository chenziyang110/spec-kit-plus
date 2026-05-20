## Project Cognition Advisory Gate

This planning-only command should treat the project cognition runtime as an
advisory navigation index, not a mandatory pre-source gate.

### Advisory Rule

Use project cognition when available to find likely owners, affected paths,
risks, verification routes, and minimal live reads. Do not treat map output as
evidence by itself. Technical claims must be backed by live code, tests,
scripts, configuration, or authoritative docs.

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

Treat runtime freshness as map-quality diagnostics:

- `fresh` -> use the returned task-local bundle as an advisory first pass navigation aid
- `missing` -> if cognition freshness is `missing`, stop and tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that rebuild before continuing
- `stale` -> if cognition freshness is `stale`, treat map output as advisory and continue with live repository evidence; recommend `{{invoke:map-update}}` as follow-up map maintenance
- `stale` with changed paths missing from `path_index` -> warn and continue with live repository evidence; recommend `sp-map-scan -> sp-map-build` only if the user wants map repair
- `support_drift` -> warn and continue with live repository evidence; recommend resolving or intentionally ignoring support-surface drift
- `partial_refresh` -> warn that refresh data was recorded but readiness did not pass; continue with live repository evidence
- `possibly_stale` -> inspect the returned affected scope when useful, then continue with live repository evidence

Preserve the distinction between the machine freshness field and public state
guidance: `freshness` records map quality, while `recommended_next_action` is a
map-maintenance recommendation.

### Primary Read Restriction

Do not treat handbook-first or layered project-map files as evidence. If
query-returned coverage is insufficient, inspect live repository surfaces
directly and recommend `sp-map-update` or `sp-map-scan -> sp-map-build` as
follow-up map maintenance when useful.

The completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs. Project cognition can support route selection but cannot be the sole evidence for completion.

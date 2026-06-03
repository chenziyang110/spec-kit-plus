# Project Cognition Alias Schema Cleanup Design

## Context

Project cognition now uses `.specify/project-cognition/project-cognition.db` as the query-backed graph store for generated brownfield workflows. The current SQLite schema includes many tables, but the implemented `build-from-scan` path primarily imports evidence, nodes, edges, observations, path coverage, and update records.

Two local observations shaped this design:

- In this repository, `.specify/project-cognition/project-cognition.db` exists but has no active generation and no scan package. It is not a valid baseline.
- In `D:\work\JZWinReNewEx`, the project cognition baseline is valid and `validate-build` passes with `evidence=3216`, `path_index=3237`, `nodes=20`, `edges=24`, and `observations=13`. Several tables still remain empty even though the baseline is query-ready.

The empty-table issue should not be handled by keeping broad placeholder schema. The database should represent implemented behavior. At the same time, the alias-first intake flow is a core product requirement and needs durable database support.

## Problem

The current schema mixes three categories:

- Implemented runtime tables that are written and queried today.
- Conceptual future tables with no reliable producer.
- Alias and retrieval surfaces that are product-critical but currently assembled mostly from node titles, paths, and node attrs instead of a first-class table.

This creates two problems:

- Users inspecting the database see many empty tables and reasonably question whether the runtime is incomplete or broken.
- The alias-first flow depends on derived aliases, but the database does not clearly own the alias catalog that agents use to normalize user prompts before querying cognition.

## Goals

- Make the default project cognition schema honest: keep only tables that have an implemented producer and a runtime consumer.
- Preserve and implement a first-class alias catalog that supports the workflow: list aliases first, let the agent normalize user input, then query cognition with a precise query plan.
- Keep `validate-build` focused on query readiness while adding clear evidence that required alias data exists for non-greenfield baselines.
- Make future semantic expansions explicit schema-version upgrades rather than unused tables in schema v1.
- Preserve compatibility with existing query-ready baselines through a rebuild path instead of fragile in-place manual SQL edits.

## Non-Goals

- Do not implement a full static symbol index in this change.
- Do not synthesize full claim, conflict, slice, or FTS systems before there are reliable scan artifacts and runtime consumers.
- Do not change the high-level `lexicon -> agent semantic_intake -> query` workflow contract.
- Do not make map-scan or map-build trust raw chat summaries as graph evidence.

## Recommended Approach

Use a smaller schema v2 with a real alias table.

Keep these tables:

- `metadata`
- `generations`
- `evidence`
- `nodes`
- `node_evidence`
- `edges`
- `edge_evidence`
- `observations`
- `observation_evidence`
- `path_index`
- `alias_index`
- `updates`

Remove these tables from the default schema until there is an implemented producer and runtime consumer:

- `claims`
- `claim_evidence`
- `conflicts`
- `conflict_claims`
- `symbol_index`
- `entrypoint_index`
- `test_index`
- `slice_members`
- `query_examples`
- `claim_fts`
- `observation_fts`
- `alias_fts`

`alias_index` remains because it directly supports the core alias-first prompt normalization flow. Unlike the other currently-empty tables, it should become a required produced table for brownfield full baselines.

## Alias Model

`alias_index` stores user-facing and project-facing names for graph concepts.

Required fields:

- `id`: stable row id.
- `generation_id`: active generation owner.
- `alias`: the user or project phrase.
- `normalized_alias`: lowercase/token-normalized matching value.
- `target_type`: initially `node`.
- `target_id`: graph node id.
- `language`: examples include `en`, `zh`, `code`, or `unknown`.
- `source`: provenance such as `node_title`, `path_material`, `scan_alias`, `observation`, or `update`.
- `confidence`: `verified`, `high`, `medium`, `low`, or `provisional`.
- `evidence_id`: supporting evidence row when available.

The build should derive aliases from:

- Node title and node id.
- Node type.
- `nodes[].attrs.aliases`, `attrs.domain`, `attrs.owner`, `attrs.workflow`, `attrs.route`, `attrs.route_hints`, and `attrs.verification_hints`.
- Path material from `nodes[].paths`, including meaningful filename, directory, and class-like tokens.
- Observation summaries when tied to node evidence.
- Explicit scan-provided alias rows if the scan artifact schema adds them.

The build should not write aliases for excluded paths or `.specify/**` workflow state.

## Data Flow

1. `sp-map-scan` builds the scan package.
   It writes evidence, provisional nodes, edges, observations, coverage, and route vocabulary. It should prefer explicit aliases in node attrs or future `aliases.json` scan artifacts when available.

2. `project-cognition build-from-scan` imports the package.
   It creates the active generation, imports evidence/nodes/edges/observations/path indexes, then builds `alias_index` from graph-backed concept material.

3. `project-cognition lexicon --mode catalog` reads `alias_index`.
   It returns alias catalog entries grouped by concept, plus candidate universe metadata bound to `active_generation_id`.

4. The agent rewrites the user's raw prompt into `semantic_intake`.
   The agent records `normalized_query`, `intent_facets`, `negative_constraints`, `alias_interpretations`, selected concepts, rejected concepts, and `concept_decisions`.

5. `project-cognition query --query-plan` validates and resolves the plan.
   It checks generation agreement, resolves selected concepts to nodes and paths, reports missing coverage, and returns `minimal_live_reads`.

## Readiness Rules

For `brownfield_full` baselines, `validate-build` should require:

- Active generation exists.
- DB metadata and `status.json` agree.
- Nodes exist.
- Evidence rows exist.
- `path_index` has active-generation rows.
- Scan package and DB identity reconciliation pass.
- Sparse path-index gates pass.
- `alias_index` has active-generation rows for at least the produced node universe.

For `greenfield_empty`, zero nodes, zero path indexes, and zero aliases remain valid.

Empty removed tables are no longer relevant because they no longer exist in schema v2.

## Compatibility

Schema v1 databases may contain the old broad table set. The runtime should treat them as compatible enough to inspect but should not keep creating v1 databases.

Recommended compatibility behavior:

- `ExistingDatabaseCompatible` accepts current v1 databases for read/query if required active-generation tables exist.
- `build-from-scan` replaces or rebuilds into schema v2 when it imports a new generation.
- `doctor` or `validate-build` reports schema version and table profile so users can distinguish old broad schema from v2 minimal schema.
- No manual SQL migration is required for downstream projects. Running `sp-map-scan -> sp-map-build` refreshes the graph store.

## CLI And Prompt Surface

`lexicon --mode catalog` should make the alias-first flow obvious:

- Return `alias_catalog` from `alias_index`.
- Include `concept_id`, `title`, `aliases`, `path_hints`, `route_hints`, `verification_hints`, `confidence`, and evidence summary tags.
- Preserve `lexicon_generation_id` and `candidate_universe_version`.
- Continue to include the query-planning contract so agents know which fields to write.

The generated workflow guidance should say that agents must use catalog aliases to normalize user input before broad source search. They should not search only raw user words when project vocabulary exists.

## Error Handling

If a brownfield build has nodes and paths but no aliases, `validate-build` should block with a specific error such as `active_generation_has_no_alias_rows`.

If `alias_index` rows reference missing nodes or evidence, build import should fail before publishing ready metadata.

If a query plan selects a concept from an older lexicon generation, query should return the existing generation-mismatch response and recommend rerunning lexicon.

## Testing

Add focused tests for:

- Schema v2 required table list excludes unused future tables.
- `build-from-scan` writes `alias_index` rows from node titles and node paths.
- `lexicon --mode catalog` reads aliases from `alias_index`.
- Brownfield `validate-build` blocks when aliases are absent.
- Greenfield empty validation does not require aliases.
- Existing v1 databases can still be inspected or routed to rebuild without crashing.
- Generated map-scan/map-build guidance explains that alias rows are required, while removed tables are not part of current readiness.

## Rollout

Implement in one contained project-cognition runtime change set:

- Update schema and required table lists.
- Add alias import/build logic.
- Update validation and lexicon reads.
- Update tests and docs.
- Rebuild downstream baselines through normal `sp-map-scan -> sp-map-build` when desired.

This keeps the database small, truthful, and aligned with the actual alias-first cognition workflow.

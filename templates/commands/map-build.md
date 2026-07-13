---
description: Use when `sp-map-scan` has produced a value-weighted evidence baseline and you need to reconstruct the project cognition SQLite runtime.
workflow_contract:
  when_to_use: A scan baseline exists and the project cognition runtime must be built or rebuilt from that evidence.
  primary_objective: Validate value-weighted scan evidence, reconstruct graph nodes, edges, observations, typed graph claims, path indexes, and alias indexes from high-value evidence into the schema v3 SQLite cognition database, derive claim lifecycle state, assign confidence, and publish queryable task-oriented cognition bundles.
  primary_outputs: '`.specify/project-cognition/status.json`, `.specify/project-cognition/project-cognition.db`, and query/update helper readiness metadata.'
  default_handoff: Return to the blocked brownfield workflow once the query-backed cognition baseline is ready.
---

{{spec-kit-include: ../command-partials/map-build/shell.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying shared semantic contracts.

- [semantic work contract](references/semantic-work-contract.md)

## Mandatory Subagent Execution

All substantive tasks in ordinary `sp-*` workflows default to and must use subagents.

The leader orchestrates: route, split tasks, prepare task contracts, dispatch subagents, wait for structured handoffs, integrate results, verify, and update state.

Before dispatch, every subagent lane needs a task contract with objective, authoritative inputs, allowed read/write scope, forbidden paths, acceptance checks, verification evidence, and structured handoff format.

Use `execution_model: subagent-mandatory`.
Use `dispatch_shape: one-subagent | parallel-subagents`.
Use `execution_surface: native-subagents`.

## Objective

Reconstruct or refresh the query-backed project cognition runtime from a completed value-weighted evidence baseline.

## Passive Project Learning Layer

- [AGENT] Run `{{specify-subcmd:learning start --command map-build --format json}}` when available so passive learning files exist and repeated graph-build blind spots can be promoted at start.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader graph-build context.
- Open only learning detail docs linked from map-build-relevant index entries.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- [AGENT] When graph reconstruction friction exposes route changes, artifact rewrites, validation gaps, false starts, hidden dependencies, or reusable constraints, make sure `map-state.md` captures that durable context.
- [AGENT] When durable state does not capture the reusable lesson cleanly, update `.specify/memory/learnings/INDEX.md` and a linked detail document with the command, type, summary, and evidence.

## Process

- Start with validation, not writing.
- Update `map-state.md` before long-running reconstruction, join-point acceptance, compaction-risk transitions, or any stop where resume will depend on more than the visible conversation.
- Validate scan inputs before execution and compile/validate `MapBuildPacket` inputs before dispatch.
- Validate both `.specify/project-cognition/workbench/repository-universe.json` and `.specify/project-cognition/workbench/scan-targets.json` before graph import. `repository-universe.json` is full path accounting; `scan-targets.json` is the high-value execution target set.
- Treat `P0`/`P1` `scan_decision=scan` rows as graph-build candidates that must be backed by accepted packet evidence before they can publish queryable runtime truth.
- Treat `P2` rows according to their recorded `scan_decision`: scanned or sampled rows can support graph truth when evidence-backed; inventory-only rows remain boundary accounting.
- Treat `P3`, `inventory_only`, and `excluded` rows as boundary accounting only unless explicit accepted scan evidence and a high-value reason promote them. Do not derive graph, path_index, alias_index, route rows, or `minimal_live_reads` from raw inventory-only rows.
- Dispatch only validated packetized build lanes as `one-subagent` or `parallel-subagents`.
- If overlap, missing packet data, missing required references, or unsafe acceptance criteria prevent safe dispatch, record `subagent-blocked` and stop for escalation or recovery.
- Run `{{specify-subcmd:project-cognition validate-scan --format json}}` before graph import.
- Run `{{specify-subcmd:project-cognition build-from-scan --format json}}` after scan and package validation. It adapts the accepted canonical scan package into a versioned proposal and runs the deterministic cognition proposal compiler before any graph-store mutation, then rebuilds the graph store into schema v3 and owns DB import, metadata, status publication, and DB/status agreement.
- Treat `compilation.publication_allowed=false` as a hard pre-publication block. Report the bounded compiler conflicts and stop without creating, archiving, replacing, or publishing a graph store.
- A successful compile means the proposal is structurally safe and deterministic enough to publish as advisory graph material. Compiled nodes, edges, paths, aliases, and graph claims remain route candidates rather than repository facts; even `verified_in_graph_generation` requires bounded live repository evidence before behavioral or workflow final claims.
- If `build-from-scan` returns `status=blocked`, report its `errors`, identity reconciliation details from `identity_reconciliation`, `rejections`, `merge_records`, and `recovery_action` and do not proceed to build validation.
- Run `{{specify-subcmd:project-cognition validate-build --format json}}` after `build-from-scan`.

## Machine-Readable Blocked State

Human workflow prose may say `subagent-blocked`, but persisted machine fields use
`subagent_blocked`.

If a substantive scan/build lane cannot dispatch or complete, write:

- `.specify/project-cognition/status.json` with `baseline_state=blocked` and
  `subagent_blocked` in `stale_reasons` or `dirty_reasons`
- `.specify/project-cognition/workbench/map-state.md` with
  `readiness=blocked`, `blocking_reason=subagent_blocked`, blocked lane ids,
  blocked scope, and recovery condition
- `.specify/project-cognition/workbench/coverage-ledger.json.open_gaps[]` with
  `reason="subagent_blocked"`, `lane_id`, `packet_id`, `blocked_scope`,
  `criticality`, `owner`, `status="blocked"`, and `recovery_condition`

`unknown` blocks, `blocked`, `critical_open_gap`, and `subagent_blocked` block baseline
activation. `low_risk_open_gap` may pass only with owner, reason,
`evidence_expectation`, and `revisit_condition`.

## Hard Boundary

- `sp-map-build` is the command that publishes query-backed cognition truth.
- `sp-map-build` must not fall back to handbook-first runtime output.
- `sp-map-build` owns schema v3 SQLite runtime publication, confidence assignment, typed graph-claim lifecycle derivation, route validation, and alias catalog readiness.
- Existing narratives may inform continuity, but final runtime rows must be backed by scan evidence. Map points, code proves: the alias catalog is route vocabulary, not evidence by itself.

## Required Inputs

Before writing query-backed truth, read:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/evidence/`
- `.specify/project-cognition/provisional/nodes.json`
- `.specify/project-cognition/provisional/edges.json`
- `.specify/project-cognition/provisional/observations.json`
- optional `.specify/project-cognition/provisional/claims.json`
- `.specify/project-cognition/coverage.json`
- `.specify/project-cognition/workbench/repository-universe.json`
- `.specify/project-cognition/workbench/scan-targets.json`
- `.specify/project-cognition/workbench/coverage-ledger.json`
- `.specify/project-cognition/workbench/scan-queue.json`
- `.specify/project-cognition/workbench/handoff-ledger.json`
- `.specify/project-cognition/workbench/scan-packets/`

If those artifacts are missing, stop and route back to `/sp-map-scan`.

## Boundary Acceptance

`sp-map-build` must validate `.specify/project-cognition/workbench/repository-universe.json` and `.specify/project-cognition/workbench/scan-targets.json` before publishing runtime truth.

- Every `included_paths` entry in `repository-universe.json` must have one explicit boundary disposition: `deep_read`, `sampled`, `inventory_only`, `excluded`, or `blocked`.
- For graph-eligible selected paths, every included path is represented in scan coverage or an accepted gap.
- Every `selected_paths` entry in `scan-targets.json` must appear in `coverage.json`, `coverage-ledger.json`, or an accepted non-blocking gap.
- Every `P0` or `P1` row with `scan_decision=scan` must have accepted packet evidence before runtime publication, or the build must return a scan gap report and route back to `sp-map-scan`.
- `P2` rows may be sampled or inventory-only only when `scan-targets.json` records the lower-depth decision and `coverage-ledger.json` preserves the evidence expectation and revisit condition.
- `P3`, `inventory_only`, and `excluded` rows are not missing graph evidence. They are complete only as boundary accounting and must not inflate graph-readiness failure counts.
- Every `excluded_paths` entry must stay only in the boundary artifact or grouped exclusion ledger.
- Excluded paths are represented only by the boundary artifact or grouped accounting ledgers, not by graph-facing coverage rows. Inventory-only paths follow the same boundary-accounting rule unless explicitly promoted.
- Excluded paths must not appear in graph-facing coverage rows, evidence rows, provisional graph rows, DB path indexes, route indexes, alias indexes, or `minimal_live_reads`. Inventory-only paths follow the same rule unless the scan target explicitly promoted them with accepted evidence.
- If repository-universe, scan-targets, coverage, and packet handoffs cannot explain the same selected path universe, return a scan gap report and route back to `sp-map-scan`.
- If scan packet acceptance reports `fail_contract` or `fail_systemic`, route back to `sp-map-scan` with a scan gap report because the repair is not only a local patch.
- `path_index_to_included_ratio` must be computed from graph-eligible paths: selected `P0`/`P1` paths plus evidence-backed selected `P2` paths, minus true exclusions and `accepted_nonblocking_gap_paths`.
- Critical and important graph-eligible paths must remain in the sparse path-index denominator unless they are true repository-universe exclusions or explicitly accepted nonblocking gaps.
- `build-from-scan` must not set `freshness=fresh`, must not set `readiness=query_ready`, and must not set `graph_ready=true` until sparse path-index gates pass.

## Schema V3 Runtime Contract

`project-cognition build-from-scan --format json` archives schema v1 or old broad
schema databases, migrates a structurally compatible schema v2 database
additively without discarding its graph data, and creates schema v3 for new
baselines. Schema v3 keeps the
implemented runtime tables: `metadata`, `generations`, `evidence`, `nodes`,
`node_evidence`, `edges`, `edge_evidence`, `observations`,
`observation_evidence`, `path_index`, `alias_index`, `claims`, `claim_evidence`,
`claim_verifications`, `claim_transitions`, and `updates`.

Conflicts, symbols, entrypoints, tests, slices, query examples, FTS tables, and compatibility `query_examples` are not current readiness requirements.

Graph claims use `graph_claim_type` and a compiler-derived lifecycle state:
`candidate`, `supported`, `verified_in_graph_generation`, `contradicted`, or
`stale`. `claim_evidence` records supporting and contradicting evidence,
`claim_verifications` records bounded verification inputs, and
`claim_transitions` makes lifecycle changes auditable. An Agent-provided
`requested_state` is never authoritative. `verified_in_graph_generation` means
only that the active graph generation contains supporting evidence and a current
passed graph verification; it is not current repository truth and never grants
workflow authorization or final claim readiness.

For brownfield baselines, `alias_index` is required: every active node must have
at least one active-generation alias row, no alias may point at a missing node,
and no alias may reference a missing non-empty evidence id. The schema v3 alias
catalog helps agents normalize user input before query planning; it does not prove behavior
without live repository evidence.

If validation reports schema v1, an old broad schema, or rebuild-required
readiness, route the user to `sp-map-scan -> sp-map-build`; build-from-scan
archives the v1 DB and creates a clean schema v3 database. Compatible schema v2
databases migrate in place.
When writing the recommendation in plain text, use: run sp-map-scan -> sp-map-build.

## Path Index Source Contract

build-from-scan creates DB path_index rows from nodes.json `paths`. It does not read `attrs_json.path`, raw node metadata, `repository-universe.json`, `scan-targets.json`, or `coverage.json` as path-index sources.
coverage.json rows without matching node paths are recorded as rejected coverage with reason `no_node_relation`. Inventory-only and excluded rows do not need path_index rows and must not be inserted into nodes solely to satisfy raw path-count coverage. If `validate-build` reports
`active_generation_has_no_path_index_rows`, route back to `sp-map-scan` to repair
node `paths` in the scan package instead of inserting SQL manually.

## Output Contract

The only canonical runtime outputs for this command are:

- `.specify/project-cognition/status.json`
- `.specify/project-cognition/project-cognition.db`
- query/update helper readiness metadata
- join-point `worker-results` evidence for delegated build lanes until the leader accepts the final query-ready baseline
- `.specify/project-cognition/workbench/worker-results/<packet-id>.json`

Do not publish handbook-first runtime truth from this command. Do not publish raw graph JSON artifacts or slices as runtime truth.

## Guardrails

- Do not rebuild the scan from chat memory.
- Do not guess and continue when required scan inputs are incomplete.
- Do not treat raw scan prose or raw Markdown checklist items alone as accepted build evidence.
- Do not accept packet results without inspected paths, evidence, and confidence.
- Do not accept packet results whose `paths_read` is a boolean, summary flag, or anything other than a non-empty array of concrete paths.
- Do not accept read/deep_read packet results whose `evidence_ids` are missing from the scan evidence package or point only to a different `source_path`.
- Do not accept orphan packet results that do not correspond to a `scan-packets/<lane-id>.md` input packet.
- Do not perform a structural-only refresh and call it success.
- Do not accept manual SQL, sqlite shell scripting, hand-picked node subsets, or leader-memory graph reconstruction as normal build paths.
- Do not locally patch around contract-invalid or systemic scan packet failures.
- If the build lane cannot be safely packetized or delegated, record `subagent-blocked` and stop for escalation or recovery.
- If a delegated lane returns unresolved evidence gaps, preserve the scan gap report and stop for escalation or recovery instead of inventing closure.

## Project Cognition Workbench State Protocol

- Project Map State Protocol remains active during build acceptance.
- Validate Scan Inputs Before Execution.
- Compile And Validate MapBuildPacket Inputs.
- Treat `coverage-ledger.json` as the machine-readable row source.
- `MapBuildPacket` is required for delegated build lanes.
- Raw scan prose or raw Markdown checklist items alone are insufficient.
- raw scan prose or raw Markdown checklist items alone
- Packet evidence intake must reject packet results without paths read.
- Packet evidence intake must require `paths_read` to be a non-empty array of concrete paths, not `true` or another summary flag.
- Packet evidence intake must reject packet results that only summarize without evidence.
- Packet evidence intake must reject non-`pass` packet outcomes until the scan lane is repacked, repaired, or recorded as an explicit unresolved gap.
- derived-only evidence is insufficient for final graph acceptance.
- Structural-only refresh is a failed build.
- The build phase is not a scaffold, migration, or file-moving command.
- Treat scan artifacts as inputs, not evidence, until packet evidence is accepted.
- `.specify/**` inputs are workbench/control artifacts, not graph evidence rows.
- DB publication must not write `.specify/**` into `evidence.source_path`, `path_index.path`, or `alias_index` target material.
- Build intake must reject `.cognitionignore`-excluded paths from scan coverage, evidence rows, provisional nodes, provisional edges, observations, packet results, and `repository-universe.json` included paths.
- DB publication must not write `.cognitionignore`-excluded paths into `evidence.source_path`, `path_index.path`, or `alias_index` target material.
- DB publication must not write raw inventory-only paths into `evidence.source_path`, `nodes.paths`, `path_index.path`, `alias_index`, route rows, or `minimal_live_reads` unless the path was promoted by `scan-targets.json` and backed by accepted evidence.

## Build Duties

`sp-map-build` must:

- begins with validation, not writing
- validate scan completeness for graph reconstruction through the value-weighted target set
- validate that `scan-targets.json` selects high-value graph evidence and keeps low-value inventory-only surfaces out of graph publication
- deduplicate provisional nodes into graph nodes
- convert candidate edges into validated graph edges
- build schema v3 `alias_index` rows from alias-ready node titles, types, paths, and bounded attrs
- compile optional graph claim candidates, validate all node/evidence references, derive lifecycle state, and persist claim evidence, verification, and transition rows atomically with the generation
- assign node, edge, observation, path, and alias confidence
- publish queryable task-oriented bundles for downstream agent work
- produce workflow-operational reachability validation
- produce reverse coverage validation
- project graph truth into retrieval outputs by building evidence-backed route rows
- preserve compatibility `query_examples` only as non-readiness route examples when present
- synthesize `concept_candidates` from graph-backed aliases, ownership,
  capabilities, symptoms, generated surfaces, and verification routes
- publish `route_pack` entries that connect selected concepts to owners,
  consumers, affected paths, verification routes, conflicts, and
  `minimal_live_reads`
- do not rebuild the scan from chat memory
- must not guess and continue when required scan inputs are incomplete
- must reject `.cognitionignore`-excluded paths before graph reconstruction; if scan artifacts contain them, return a scan gap report instead of publishing runtime truth
- must reject raw inventory-only paths before graph reconstruction unless they were promoted by `scan-targets.json` and backed by accepted evidence
- maintain a scan gap report when unresolved critical rows remain in the graph-eligible set

The build must keep graph truth projection explicit: every route row that feeds
`concept_candidates`, `query_examples`, or `route_pack` must be evidence-backed,
traceable to accepted scan evidence, and rejectable when confidence, ownership,
or route semantics are weak.

## Consequence Substrate Synthesis

`sp-map-build` must synthesize consequence-analysis substrate from scan evidence so downstream workflows can query dependency impact without rebuilding the map:

- owner edges for files, modules, commands, APIs, templates, generated assets, state files, and verification entry points
- consumer edges for direct callsites, generated-surface propagation, adjacent workflows, user-facing commands, and automation/runtime entry points
- lifecycle/state edges for active actors, running work, queues, sessions, locks, caches, persisted state, cleanup, retry, rollback, and idempotency behavior
- shared-state and destructive-operation edges where close/delete/archive/rename/migrate actions can affect members, consumers, or in-flight work
- verification-route records for the checks that prove owners, consumers, state transitions, and recovery behavior
- known-unknown, stale-route, confidence, and `minimal_live_reads` records that `sp-map-update` can preserve or narrow incrementally

The resulting query-backed runtime must be able to answer which owners, consumers, state surfaces, generated surfaces, and verification routes are implicated by a changed path or requested behavior.

## Required Graph Semantics

Every accepted schema v3 graph build must make room for:

- nodes
- edges
- observations
- path_index
- alias_index
- updates
- queryable task-local bundles

The alias catalog must be route vocabulary backed by `alias_index` rows. It helps
normalize user input into project vocabulary; it is not evidence by itself.

## Dispatch Guidance

- Use `choose_subagent_dispatch(command_name="map-build", snapshot, workload_shape)` before lane execution.
- Dispatch each build lane from a validated `MapBuildPacket`.
- Recommended build lanes include DB normalization, alias readiness review, route validation, and queryable task-local bundle generation.
- The leader owns final graph consistency and readiness state.

## Completion Rule

Before reporting completion:

- run `{{specify-subcmd:project-cognition validate-scan --format json}}` before graph import
- run `{{specify-subcmd:project-cognition build-from-scan --format json}}`; if it returns `status=blocked`, report its `errors`, identity reconciliation details from `identity_reconciliation`, `rejections`, `merge_records`, and `recovery_action`
- run `{{specify-subcmd:project-cognition validate-build --format json}}` after `build-from-scan`
- report completion only after `validate-build` returns `status=ok` and `readiness=query_ready`
- confirm that `.specify/project-cognition/project-cognition.db` was written and can be queried through `{{specify-subcmd:project-cognition compass --intent implement --query="$ARGUMENTS" --format json}}`. Read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths`, `claim_refs`, `coverage_diagnostics`, and `before_fix_claim`. Treat `route_confidence` only within `confidence_scope=route_candidate`; use top-level advanced-query `claim_signals` or `project-cognition expand --section claim_evidence` for bounded `source_path`/`span` evidence. These signals require live verification and cannot prove current repository truth. Do not infer final edit scope from first-pass reads or graph claims.
- preserve the advanced `lexicon -> semantic_intake -> query` flow for explicit concept decisions or unresolved coverage. In that escalation, write `semantic_intake` from the alias catalog, select candidates by facet coverage, write `concept_decisions` with `covered_facets`, `missing_facets`, and `match_sources`, carry `lexicon_generation_id`, add `repository_search_terms`, and run `{{specify-subcmd:project-cognition query --intent implement --query-plan "<query_plan_json>" --format json}}`. Agent-owned semantic normalization is mandatory: raw lexicon ranking and `agent_normalization` are only bootstrap signals, not route decisions. If `agent_normalization.required=true`, every raw candidate is `score=0`, or the prompt is localized, mixed-language, CJK, colloquial, symptom-first, or mixed-language or CJK text, extract embedded project terms and write `semantic_intake` from the alias catalog before selecting or rejecting concepts. If `agent_normalization` is omitted, treat it as `required=false`; CJK or mixed CJK/ASCII input still requires agent normalization even when positive raw lexical matches exist because embedded project tokens do not translate the surrounding user language. The agent still owns translation; `agent_normalization` is advisory guidance, not a route decision. (raw lexicon ranking is only a bootstrap; action: write_semantic_intake_from_alias_catalog) Derive project-language search terms from the alias catalog before source search. Do not search only the raw user words; include component names, state names, file names, command names, UI labels, and route names from candidates, aliases, matched_terms, colloquial_matches, returned paths, `normalized_query`, and `expanded_queries`. Use these project-language search terms before broad repository search
- if `validate-build` returns `status=blocked`, report the specific DB, schema, active generation, status, or smoke-query error and do not mark the baseline fresh
- confirm that `status.json` reflects a query-ready baseline
- confirm that the runtime remains query-backed and does not advertise raw graph JSON or handbook-first outputs as runtime truth
- report whether follow-on localized maintenance should continue through `map-update` for future touched-area drift
- every `critical` row is covered by active runtime path and route indexes
- every `important` row is reachable through active runtime path and route indexes when graph-eligible
- every `P0`/`P1` row with `scan_decision=scan` is covered by accepted evidence and active runtime path or route indexes
- every `P3`, `inventory_only`, or `excluded` row remains out of graph-facing runtime outputs unless explicitly promoted with accepted evidence
- every scan packet is consumed
- every accepted packet result has paths read and confidence
- every runtime node, edge, observation, path row, and alias row is backed by accepted packet evidence where the row requires evidence
- query bundle and route reachability are validated through runtime query surfaces
- no final report claims success for a structural-only refresh
- `map_state_file` records accepted packet results
- owner, consumer, change propagation, and verification routes remain explicit
- known unknowns or known-unknowns remain visible
- the excluded bucket has a reason and revisit condition
- every critical shared surface can be discovered through runtime query surfaces
- every key verification entry point can be located through runtime query surfaces
- required_reads contain only reference-only or hard-excluded exceptions when runtime compatibility outputs are mentioned

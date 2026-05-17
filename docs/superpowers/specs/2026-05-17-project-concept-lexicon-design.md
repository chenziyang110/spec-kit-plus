# Project Concept Lexicon Design

## Summary

Project Concept Lexicon adds a semantic retrieval layer on top of the
SQLite-backed project cognition runtime. It lets workflow agents translate
colloquial user requests into project-specific concepts before they read source
files, plan changes, dispatch work, or debug behavior.

The layer is a projection of existing project cognition truth, not a second
knowledge graph.

```text
canonical truth:
  nodes / edges / claims / evidence

retrieval signals:
  alias_index / symbol_index / path_index / query_examples / claim_fts / alias_fts

consumer view:
  concept_candidates / selected_concepts / rejected_concepts / route_pack
```

For a request such as "I want to add provider support to agent teams", the
runtime should surface project concepts such as `agent teams runtime`,
`provider`, `backend adapter`, `subagent dispatch`, `team member lifecycle`, and
`sp-teams`. The agent then selects and rejects concepts with reasons, queries
project cognition from those selections, and receives a route pack containing
the relevant code, docs, state surfaces, workflow surfaces, tests, consumers,
and minimum live reads.

## Goals

- Let agents start brownfield work from project concepts instead of broad source
  search.
- Support colloquial user language, project terminology, module names,
  workflow names, feature names, symptoms, tests, and technical aliases.
- Preserve high recall while keeping every returned concept explainable,
  evidence-backed, ranked, and disambiguated.
- Keep project cognition graph truth canonical. Do not create a parallel concept
  graph that can drift from `nodes`, `edges`, `claims`, and `evidence`.
- Make `sp-map-scan`, `sp-map-build`, and `sp-map-update` all maintain concept
  retrieval signals.
- Centralize all `sp-*` consumer behavior in the shared project cognition gate
  partial so the workflow fleet does not copy and drift.
- Return route packs that explain why each suggested file or artifact matters.

## Non-Goals

- Do not replace live reads. The lexicon and query result should reduce and
  prioritize live reads, not eliminate verification.
- Do not make keywords a flat global bag of words. Generic terms such as
  `provider`, `agent`, `test`, or `state` must be domain-scoped and ranked.
- Do not make a new authoritative `concepts` graph at this phase.
- Do not require full `sp-map-scan -> sp-map-build` rebuilds for ordinary
  alias, path, or route-pack drift after a baseline exists.
- Do not make downstream workflows infer ownership or verification routes from
  raw strings when the runtime has graph edges and claims.

## Current Context

The current runtime already has the foundation:

- `project-cognition lexicon` returns terms derived from `nodes.title`,
  `alias_index.alias`, `path_index.path`, and `symbol_index.symbol_name`.
- `project-cognition query` resolves raw query text, agent-expanded queries,
  and path hints through `alias_index`, `claim_fts`, and `path_index`.
- `validate-build` already performs a smoke check that requires some query
  signal through aliases or claim FTS.
- Workflow templates already share a project cognition consumer partial:
  `templates/command-partials/common/context-loading-gradient.md`.
- `templates/command-partials/common/navigation-check.md` is already a shim
  that points consumers at the shared gate.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md` mirrors
  the shared gate for skills-based integrations.

The gap is that the lexicon is still term-oriented. It does not yet expose a
first-class concept candidate view, concept selection contract, rejected
concepts, route packs, or strong scan/build/update duties for colloquial and
project-specific retrieval signals.

## Design Principle

Project Concept Lexicon is an API and indexing projection over the graph:

- A concept candidate is how a workflow agent sees a graph node or node cluster.
- The canonical source remains `nodes`, `edges`, `claims`, and `evidence`.
- Retrieval signals remain in indexed tables such as `alias_index`,
  `symbol_index`, `path_index`, `query_examples`, `claim_fts`, and `alias_fts`.
- Optional future materialization, such as `lexicon_index`, is a cache that can
  be rebuilt from canonical truth and indexes.

This avoids dual truth while still allowing a refined consumer experience.

## Runtime Contract Version

This design changes the public query runtime contract. The implementation must
bump `query_contract_version` from `1` to `2` when concept candidates,
selected/rejected concepts, and route packs become required runtime behavior.

Contract version `2` means:

- `project-cognition lexicon` returns `concept_candidates` in addition to
  compatibility `terms` and `available_terms`.
- `project-cognition query --query-plan` accepts `selected_concepts`,
  `rejected_concepts`, and `selection_reason`.
- query results include `selected_concepts`, `rejected_concepts`, and
  `route_pack`.
- build validation rejects runtimes that publish version `2` metadata without
  these behaviors.

`update_contract_version` may stay at `1` only for an implementation that
records retrieval-signal maintenance as update metadata without changing the
update command payload. If `sp-map-update` gains new public update inputs or
outputs for concept corrections, bump `update_contract_version` in the same
implementation lane and validate it.

Backward compatibility is read-only: generated consumers may tolerate older
version `1` runtimes by routing to `sp-map-update` or `sp-map-scan ->
sp-map-build`, but a version `1` runtime must not pass validation as
concept-lexicon ready.

## Concept Candidate View

`project-cognition lexicon` should return concept candidates, not only raw map
terms. A candidate is a projected view over one or more graph nodes and indexed
signals.

Example shape:

```json
{
  "concept_id": "capability:codex-team-runtime",
  "label": "agent teams runtime",
  "kind": "capability",
  "domain": "agent teams",
  "matched_terms": ["agent teams", "provider", "subagent"],
  "aliases": ["sp-teams", "team runtime", "backend adapter"],
  "colloquial_matches": ["为 agent teams 接入 provider"],
  "target_nodes": ["capability:codex-team-runtime"],
  "related_concepts": ["capability:subagent-dispatch", "module:codex-team"],
  "disambiguation_hint": "Here, provider likely means team runtime backend/provider, not LLM provider.",
  "confidence": "strong",
  "evidence_ids": ["E-team-runtime"]
}
```

Required fields:

- `concept_id`: stable graph-backed identifier. Prefer the primary node ID.
- `label`: human-readable project concept name.
- `kind`: `capability`, `module`, `workflow`, `runtime`, `api`, `state`,
  `test`, `symptom`, `integration`, or `documentation`.
- `domain`: local context that makes generic words precise, such as
  `agent teams`, `project cognition`, `testing`, or `workflow orchestration`.
- `matched_terms`: query terms, aliases, symbols, or path terms that caused the
  candidate to appear.
- `aliases`: project-specific synonyms and technical equivalents.
- `colloquial_matches`: user-facing phrases from `query_examples` or extracted
  docs that match the request.
- `target_nodes`: graph nodes the concept resolves to.
- `related_concepts`: adjacent graph-backed concepts useful for expansion.
- `disambiguation_hint`: explanation for ambiguous or overloaded terms.
- `confidence`: ranked confidence derived from evidence quality and match type.
- `evidence_ids`: evidence backing the candidate and its aliases.

### Query Examples Evidence

`query_examples` are retrieval signals, not standalone evidence. The current
table records expected target metadata but does not include `evidence_id` or
`confidence`. A concept candidate may use `query_examples` for
`colloquial_matches` only when the candidate is also backed by node, alias,
claim, path, symbol, or edge evidence.

The implementation has two acceptable paths:

- extend `query_examples` with `evidence_id` and `confidence`, then validate
  those fields for version `2` runtimes; or
- keep the table shape unchanged and treat query examples as annotations that
  inherit evidence from the resolved target node's aliases, claims, paths,
  symbols, or node evidence.

The first version of this design should prefer the second path unless
implementation discovers that query examples need independent provenance for
correction workflows.

## Query Plan Contract

The agent must select and reject concepts before running the graph query. The
selection is part of the durable query plan and must be carried into downstream
artifacts or workflow state.

Example:

```json
{
  "raw_query": "我想为 agent teams 接入 provider",
  "selected_concepts": [
    "capability:codex-team-runtime",
    "capability:subagent-dispatch"
  ],
  "rejected_concepts": [
    "capability:llm-provider"
  ],
  "selection_reason": "The request targets agent teams runtime provider behavior, not model provider configuration.",
  "expanded_queries": [
    "team runtime provider",
    "backend adapter",
    "subagent dispatch",
    "sp-teams provider"
  ],
  "paths": []
}
```

`project-cognition query --query-plan` must accept:

- `raw_query`
- `selected_concepts`
- `rejected_concepts`
- `selection_reason`
- `expanded_queries`
- `paths`

Rejected concepts are not just comments. They lower or suppress candidates that
would otherwise be pulled in by generic aliases.

Unknown or conflicting concept selections are not ready states:

- If a selected concept does not exist in the active generation, query readiness
  must be `needs_update` when supplied paths suggest new coverage is needed, or
  `review` when the runtime can only offer fallback reads.
- If the same concept appears in both `selected_concepts` and
  `rejected_concepts`, rejection wins for automatic expansion and readiness must
  be `ambiguous` unless a path hint or another selected concept resolves the
  conflict.
- Query results must echo invalid or conflicting concept IDs in
  `missing_coverage` or an equivalent conflict field so the consuming workflow
  can correct the plan instead of silently continuing.

## Route Pack

The query result should return a route pack that tells the workflow where to
look and why.

Required route pack fields:

- `entry_files`: files that define public entry points, commands, adapters, or
  handlers for the selected concepts.
- `owner_files`: files that own behavior or truth for the selected concepts.
- `consumer_files`: callers, downstream workflows, generated surfaces, or
  automation that consume the selected concept.
- `state_surfaces`: databases, JSON state, status files, config, sessions,
  queues, locks, caches, or runtime metadata implicated by the concept.
- `workflow_surfaces`: `sp-*` templates, command partials, passive skills,
  worker prompts, hooks, or scripts implicated by the concept.
- `tests`: tests and verification entry points related to the concept.
- `docs`: source-of-truth docs, design notes, README sections, or handbook
  entries that explain the concept.
- `minimal_live_reads`: the smallest live read set required before trusting the
  route.
- `why_these_reads`: evidence-backed explanation for each important route item.

All route arrays except `minimal_live_reads` and `why_these_reads` use route
item objects with the same schema:

```json
{
  "path": "src/specify_cli/codex_team/",
  "node_id": "capability:codex-team-runtime",
  "claim_id": "claim:codex-team-runtime-owner",
  "relation": "owner",
  "reason": "Owns Codex team runtime state and operations.",
  "evidence_ids": ["E-team-runtime"],
  "confidence": "strong"
}
```

Required route item fields:

- `path`: repository-relative path, normalized with `/`.
- `relation`: route relation such as `entry`, `owner`, `consumer`, `state`,
  `workflow`, `test`, or `documentation`.
- `reason`: concise explanation of why this item is relevant.
- `evidence_ids`: non-empty evidence IDs backing the route.
- `confidence`: `grounded`, `strong`, `partial`, or `weak`.

At least one of `node_id` or `claim_id` is required. Both may be present when a
route item is backed by a graph node and a specific claim.

`minimal_live_reads` stays a string array for compatibility and ergonomic
consumer prompts. Every `minimal_live_reads` path must correspond to at least one
route item unless the path is a low-confidence fallback for `review` or
`partial_refresh`; fallback paths must be explained in `why_these_reads`.

Example:

```json
{
  "route_pack": {
    "entry_files": [
      {
        "path": "src/specify_cli/__init__.py",
        "node_id": "capability:codex-team-runtime",
        "claim_id": "claim:sp-teams-cli-entry",
        "relation": "entry",
        "reason": "CLI entry point exposes sp-teams commands.",
        "evidence_ids": ["E-cli-teams"],
        "confidence": "strong"
      }
    ],
    "owner_files": [
      {
        "path": "src/specify_cli/codex_team/",
        "node_id": "capability:codex-team-runtime",
        "claim_id": "claim:codex-team-runtime-owner",
        "relation": "owner",
        "reason": "Owns Codex team runtime state and operations.",
        "evidence_ids": ["E-team-runtime"],
        "confidence": "strong"
      }
    ],
    "consumer_files": [],
    "state_surfaces": [],
    "workflow_surfaces": [],
    "tests": [],
    "docs": [],
    "minimal_live_reads": [
      "src/specify_cli/codex_team/"
    ],
    "why_these_reads": [
      "Selected concept resolves to codex team runtime owner paths."
    ]
  }
}
```

## `sp-map-scan` Responsibilities

`sp-map-scan` remains evidence-only. It must not publish final cognition truth
or final concept candidates.

It must collect retrieval signals while scanning:

- feature and capability names from docs, tests, commands, code, and templates
- module and package names from directory structure, imports, and ownership
  evidence
- workflow and command names such as `sp-teams`, `sp-map-update`,
  `sp-implement`, and generated command aliases
- colloquial user phrases from docs, examples, support notes, issues,
  generated workflow guidance, and query examples when available
- technical aliases and near-synonyms such as `provider`, `adapter`, `backend`,
  `connector`, `runner`, `worker`, `member`, `teammate`, and `subagent`
- symbol names, class names, functions, CLI options, config keys, error
  messages, state values, and test names
- disambiguation evidence for overloaded terms
- domain ownership evidence that scopes generic words to a project area
- route evidence for owners, consumers, state surfaces, workflow surfaces,
  verification routes, and docs

The scan package should expose these as accepted evidence, provisional nodes,
provisional observations, coverage rows, and workbench notes. It should not
write final lexicon output.

Scan acceptance should block on critical retrieval-signal gaps when a critical
or important surface has no discoverable name, alias, route evidence, or owner.
Non-critical gaps may remain only when they include owner, reason, criticality,
and revisit condition.

## `sp-map-build` Responsibilities

`sp-map-build` publishes the query-backed runtime and owns final normalization.

It must:

- deduplicate provisional concept-like evidence into canonical graph nodes
- write project aliases into `alias_index`
- write colloquial examples into `query_examples`
- populate `alias_fts` and `claim_fts` with high-recall but evidence-backed
  terms
- populate `path_index` and `symbol_index` for routeable source and symbol
  surfaces
- store domain and disambiguation metadata in node or claim `attrs_json`
- synthesize claims and edges for owner, consumer, state, workflow,
  verification, and documentation routes
- preserve confidence, conflicts, stale claims, known unknowns, and evidence IDs
- publish runtime metadata only after build validation passes

Build must not treat raw scan prose as concept truth. Every candidate exposed by
`project-cognition lexicon` must be backed by a graph node, an indexed retrieval
signal, and evidence.

## `sp-map-update` Responsibilities

`sp-map-update` is the normal maintenance path after the first baseline.

The publishing model is patch-in-active-generation for this phase:

- `sp-map-update` mutates or appends records in the current active generation
  for the affected closure.
- It appends an `updates` row describing changed paths, affected nodes, affected
  claims, affected route-pack records, stale retrieval signals, known unknowns,
  and confidence.
- It does not create a new active generation for ordinary incremental updates.
- It must invalidate or replace stale retrieval rows in the same transaction
  that records the update.
- It must update `status.json` refresh metadata only after the transactional DB
  update succeeds.

A new generation is reserved for `sp-map-scan -> sp-map-build` full baselines,
schema-incompatible rebuilds, corruption recovery, explicit rebuilds, or broad
architecture replacement.

It must:

- start from changed paths, changed commit range, or explicit user-supplied
  corrections
- query current project cognition for affected nodes, aliases, claims,
  route-pack entries, and known unknowns
- refresh retrieval signals for affected nodes when names, symbols, docs, tests,
  workflow surfaces, or path ownership changed
- update or invalidate stale aliases, query examples, FTS rows, and route claims
- record low-confidence or partial retrieval facts instead of forcing a rebuild
- preserve `minimal_live_reads` for uncertain concepts and uncovered paths
- return `partial_refresh` when the update was recorded but readiness did not
  pass
- preserve enough update metadata for a later full build to understand which
  retrieval signals were patched, invalidated, or left low-confidence
- escalate to `sp-map-scan -> sp-map-build` only for missing baseline, unusable
  DB/status/schema, explicit rebuild request, or broad architecture replacement

If a user explicitly says that a term means something in this project, such as
"provider here means team runtime provider", `sp-map-update` should treat that
as a first-class correction for the affected area unless repository evidence
contradicts it.

## Consumer Template

The consumer protocol belongs in:

- `templates/command-partials/common/context-loading-gradient.md`
- `templates/command-partials/common/navigation-check.md` as the compatibility
  shim
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md` as the
  skills mirror

The shared gate should define the common flow:

```text
project-cognition lexicon
  -> review concept_candidates
  -> select and reject concepts with reasons
  -> build query_plan
  -> project-cognition query --query-plan
  -> consume route_pack and readiness
  -> carry selected concepts and route facts into workflow state
```

Individual `sp-*` workflows should not copy the full protocol. Each workflow
should only declare:

- intent (`plan`, `implement`, `debug`, `test`, `research`)
- where selected concepts and route facts are carried forward
- workflow-specific readiness routing, if it differs from the shared default

## `sp-*` Consumer Behavior

`sp-specify`, `sp-clarify`, `sp-plan`, and `sp-tasks` use `intent=plan`.

- Carry selected concepts into `context.md`, `alignment.md`,
  `plan-contract.json`, or `tasks.md` as appropriate.
- If readiness is `review`, use returned `minimal_live_reads` before making
  project claims.
- If selected concepts are ambiguous, ask for or record a clarification before
  planning assumes a target.

`sp-implement`, `sp-quick`, and `sp-fast` use `intent=implement`.

- Carry selected concepts and route pack into `implement-tracker.md`,
  `WorkerTaskPacket`, quick status, or fast-task report.
- Use route pack owner and consumer files to bound read and write scope.
- Use returned verification routes to choose tests and closeout checks.
- Refresh project cognition through `sp-map-update` when implementation changes
  concept truth, route ownership, aliases, or verification surfaces.

`sp-debug` uses `intent=debug`.

- Carry selected concepts, rejected concepts, symptom candidates, competing
  truths, route pack, and minimal live reads into debug session state.
- Use rejected concepts to avoid chasing generic aliases in the wrong domain.
- Use route pack tests and state surfaces for root-cause verification.

`sp-analyze` uses the same project cognition gate as the workflow it is
analyzing. For task remediation and blocker analysis it normally uses
`intent=implement`, because it is judging implementation readiness, blockers,
and affected execution scope. If `sp-analyze` is invoked only to inspect
planning artifacts before implementation scope exists, it may use `intent=plan`.
In both cases it carries selected/rejected concepts, route pack, blocker
evidence, and coverage gaps into its blocker bundle.

`sp-test-scan` and `sp-test-build` use `intent=test`.

- Carry selected concepts into testing scope, coverage gaps, and testing build
  plans.
- Use route pack tests, owner files, and state surfaces to decide unit,
  integration, and e2e coverage targets.

`sp-deep-research`, `sp-prd-scan`, and related research flows use
`intent=research`.

- Carry selected concepts into research tracks, evidence IDs, and planning
  handoff.
- Use concept ambiguity to separate external feasibility research from internal
  project behavior.

Other current or future `sp-*` workflows inherit the shared consumer gate by
default. A workflow may opt out only if its command contract proves it does not
consume brownfield project context.

## Ranking and Disambiguation

Ranking should favor:

1. Explicit selected concepts.
2. Exact alias or query example match in the same domain.
3. Path or symbol match tied to a graph node.
4. Claim FTS match with evidence and high-confidence claim.
5. Related concept edge from a selected concept.
6. Generic token overlap.

Generic token-only matches should not produce `ready` by themselves when
multiple plausible domains exist. They should return `ambiguous` or `review`
with disambiguation hints and minimal live reads.

Rejected concepts suppress candidates and route expansion unless an explicit
path or selected concept reintroduces them with stronger evidence.

## Validation

`validate-scan` should check that critical and important surfaces have retrieval
signal evidence:

- name or alias evidence
- path or symbol route evidence
- owner evidence
- confidence or gap metadata

`validate-build` should check:

- runtime metadata publishes `query_contract_version = 2` for concept lexicon
  readiness
- the active generation has aliases or query examples for important concepts
- lexicon smoke query returns at least one concept candidate for a known indexed
  concept
- query accepts `selected_concepts` and `rejected_concepts` in `query_plan`
- query returns a route pack for a known selected concept
- route pack entries satisfy the route item schema and are evidence-backed
- every ordinary `minimal_live_reads` path maps to at least one route item, and
  every fallback read has a `why_these_reads` explanation
- weak coverage returns `review`, `ambiguous`, `needs_update`, or
  `partial_refresh` rather than false `ready`
- optional materialized lexicon caches are consistent with the active
  generation when they exist

Validation should not require a large concept table. It validates the projection
from graph truth and retrieval indexes.

## Migration Strategy

1. Bump the public query runtime contract to `query_contract_version = 2` and
   update runtime metadata publication plus build validation to require version
   `2` for concept-lexicon readiness.
2. Extend the query plan parser and runtime query payload with
   `selected_concepts`, `rejected_concepts`, and `selection_reason`.
3. Extend `project-cognition lexicon` to return `concept_candidates` while
   preserving existing `terms` and `available_terms` for compatibility.
4. Extend `project-cognition query` to resolve selected concepts directly before
   alias and FTS matching.
5. Add route pack output derived from existing path, edge, claim, entrypoint,
   test, and symbol indexes using the route item schema.
6. Implement the patch-in-active-generation update model for affected retrieval
   signals, including update metadata for patched, invalidated, and
   low-confidence concept routes.
7. Update `sp-map-scan`, `sp-map-build`, and `sp-map-update` prompt contracts to
   maintain retrieval signals.
8. Update the shared consumer gate and passive skill mirror.
9. Add validation and integration tests for concept selection, rejected concept
   suppression, route pack output, scan/build guidance, update guidance, and
   generated integration output.

## Risks

- Too many aliases can create noisy matches. Mitigation: domain scoping,
  confidence, disambiguation hints, rejected concepts, and readiness states.
- Sparse projects may not have enough evidence. Mitigation: return `review` and
  `minimal_live_reads`, not false certainty.
- Workflow templates may drift if each command repeats the protocol.
  Mitigation: centralize in `context-loading-gradient.md` and mirror through the
  passive skill.
- Materialized caches can drift if introduced too early. Mitigation: keep caches
  optional and derived from active graph generation.
- Agent concept selection may be wrong. Mitigation: preserve selected/rejected
  concepts and selection reason in artifacts so later workflows can review and
  correct them.

## Acceptance Criteria

- `project-cognition lexicon` returns `concept_candidates` with labels, domains,
  matched terms, aliases, confidence, evidence IDs, and disambiguation hints.
- `project-cognition query --query-plan` accepts selected and rejected concepts.
- Query results include a route pack with evidence-backed read routes and
  `why_these_reads`.
- Runtime metadata and validation require `query_contract_version = 2` for the
  concept lexicon contract.
- Route pack entries follow the route item schema and can be validated against
  evidence-backed node or claim references.
- `sp-map-update` has an explicit patch-in-active-generation model with update
  records for patched, invalidated, partial, and low-confidence retrieval
  signals.
- Query examples either carry direct evidence/confidence or are explicitly
  treated as annotations over already evidence-backed targets.
- `sp-map-scan`, `sp-map-build`, and `sp-map-update` templates describe their
  concept retrieval signal responsibilities.
- `context-loading-gradient.md` defines the shared consumer protocol.
- `spec-kit-project-cognition-gate` mirrors the shared protocol for skills.
- `sp-analyze` and future `sp-*` consumers inherit the shared gate unless their
  command contract proves no brownfield context is consumed.
- At least one test proves colloquial language plus selected concepts can route
  to relevant code without broad source search.
- At least one test proves rejected concepts suppress a plausible but wrong
  domain.
- At least one validation test proves weak concept coverage cannot be reported
  as fully ready.

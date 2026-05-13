# Project Cognition SQLite Graph Store Design

**Date:** 2026-05-13  
**Status:** Draft for review  
**Owner:** Codex

## Summary

This design replaces the current large-JSON project cognition graph runtime with
a SQLite-backed property graph store.

The current `project-cognition` direction is conceptually right: workflows
should use project cognition before broad brownfield source reading. The current
storage and command contracts are not yet strong enough to deliver that promise.
Small reads still require large graph artifacts. Small updates can still trigger
heavy `map-update` flows. Capability and symptom matching can still depend too
much on agent inference instead of indexed graph evidence.

The approved direction is:

- make `.specify/project-cognition/project-cognition.db` the canonical runtime
  truth store
- keep `.specify/project-cognition/status.json` as the lightweight status,
  readiness, and schema-version entrypoint
- remove large JSON graph files from the runtime read/write path
- expose a query API that returns task-local subgraphs instead of raw graph
  artifacts
- make `map-update` a transactional, index-driven incremental updater
- require query results to carry evidence traces, candidate scoring, and
  ambiguity handling

This is a runtime architecture change, not a prompt-only adjustment.

## Problem

The current graph-native runtime has three practical failures.

### 1. Reads are too coarse

Workflow templates and helper contracts still often point agents at:

- `.specify/project-cognition/graph/nodes.json`
- `.specify/project-cognition/graph/edges.json`
- `.specify/project-cognition/graph/claims.json`
- `.specify/project-cognition/graph/conflicts.json`

Those artifacts become increasingly expensive as the project grows. They also
put too much burden on the agent to load broad context and manually filter it.

### 2. Updates are too heavy

`sp-map-update` is intended to be incremental, but the current storage contract
does not give it enough indexed lookup power. A small change can still require:

- reading large graph files
- recomputing broad topic coverage
- rewriting entire graph artifacts
- refreshing more slices than the touched area needs

This makes ordinary maintenance slow and discourages keeping cognition fresh.

### 3. Natural-language lookup is under-specified

For debugging requests such as "login has a bug" or "valid password login
fails", the system needs to map user language to project graph nodes. That
mapping cannot be a hidden model guess. It must be an indexed, evidence-bearing
resolution step that can return multiple candidates or require confirmation.

Without this, two bad outcomes are possible:

- the graph contains the right node but the agent fails to retrieve it
- the agent retrieves the wrong node and presents the result as certain

## Goals

- Make project cognition reads task-local by default.
- Make project cognition updates transactional and affected-scope limited.
- Let workflows query project cognition without knowing graph storage details.
- Give `map-update` direct indexes from changed paths to affected graph nodes.
- Separate graph-provided evidence from semantic guesses.
- Surface ambiguity and missing coverage instead of hiding it.
- Preserve a low-install local runtime by using SQLite from the Python standard
  library.
- Remove old large-JSON graph artifacts from the primary runtime contract.

## Non-Goals

- Do not preserve backwards compatibility with the current JSON graph runtime.
- Do not add Neo4j, Gremlin, or another external graph database dependency.
- Do not make agents read raw graph tables directly.
- Do not make every natural-language match automatic.
- Do not optimize for human-readable graph artifacts as the primary interface.
- Do not keep `nodes.json`, `edges.json`, `claims.json`, or `conflicts.json` as
  canonical truth.

## Approved Direction

Use a SQLite-backed property graph store:

```text
.specify/project-cognition/
  status.json
  project-cognition.db
```

`status.json` remains the lightweight entrypoint. It records:

- schema version
- baseline state
- freshness state
- readiness state
- baseline commit and branch
- last update id
- graph store path
- query/update compatibility version

`project-cognition.db` becomes the canonical truth store for:

- evidence
- observations
- nodes
- edges
- claims
- conflicts
- aliases
- path and symbol indexes
- slice membership
- update events
- query examples and recall checks

Large JSON graph files are removed from the runtime path. Optional exports can
exist later, but they are not part of correctness, freshness, or workflow
consumption.

## Usage Model

Workflows do not read graph artifacts.

They ask the cognition runtime for a task-local bundle:

```text
specify cognition query --intent debug --query "valid password login fails"
```

or, when paths are already known:

```text
specify cognition query --intent implement --paths src/auth/login.ts tests/auth/login.test.ts
```

The response contains:

- readiness
- matched capability candidates
- matched symptom candidates
- evidence traces for each match
- relevant entrypoints
- implementation nodes
- state surfaces
- claims
- conflicts
- verification routes
- minimal live read set
- missing coverage
- recommended next action

Example shape:

```json
{
  "readiness": "ready",
  "intent": "debug",
  "query": "valid password login fails",
  "capability_candidates": [
    {
      "node_id": "capability:auth.login",
      "label": "User login",
      "score": 0.93,
      "matched_by": [
        "alias:login",
        "entrypoint:POST /api/login",
        "claim:AuthService implements user login"
      ]
    }
  ],
  "symptom_candidates": [
    {
      "symptom_id": "symptom:valid_credentials_rejected",
      "score": 0.86,
      "matched_by": [
        "alias:valid password rejected",
        "test:accepts valid password",
        "risk:password hash mismatch"
      ]
    }
  ],
  "subgraph": {
    "entrypoints": ["entrypoint:api.login"],
    "implementation_nodes": ["symbol:AuthService.login", "symbol:PasswordVerifier.verify"],
    "state_surfaces": ["state:users.password_hash", "state:session_store"],
    "verification_nodes": ["verification:auth-login-unit"]
  },
  "minimal_live_reads": [
    "src/api/auth/login.ts",
    "src/auth/AuthService.ts",
    "src/auth/PasswordVerifier.ts",
    "tests/auth/login.test.ts"
  ],
  "verification_routes": ["npm test -- auth-login"],
  "missing_coverage": []
}
```

The agent then reads only the returned bundle and the minimum live files needed
to replace stale or weak claims with current evidence.

## Why Reads Become Effective

The current model asks agents to read graph files and filter them in context.
That is an expensive full-scan pattern.

The new model asks SQLite indexes to locate the relevant subgraph:

```text
query text or paths
-> resolver candidates
-> path/alias/symbol/entrypoint/test indexes
-> affected nodes
-> bounded edge traversal
-> claims, conflicts, verification routes
-> task-local bundle
```

The read complexity moves from "load the whole graph and filter" to "index
lookup plus the size of the relevant result set".

For a login bug, the runtime should not scan every node. It should resolve:

```text
login/authentication capability
-> login entrypoints
-> auth service symbols
-> password verification symbols
-> user/session state surfaces
-> login tests
```

The result is small because the graph store has direct indexes for each access
path.

## Query Resolver

Natural-language lookup is a first-class runtime component.

The resolver accepts:

- raw query text
- intent
- optional changed paths
- optional command context
- optional user-supplied capability or symptom hints

It performs multi-route candidate retrieval:

- exact alias lookup
- normalized alias lookup
- path index lookup
- symbol index lookup
- entrypoint index lookup
- test index lookup
- claim text lookup
- optional semantic candidate lookup when indexed evidence is weak

Every candidate must carry a `matched_by` trace.

Candidate confidence is derived from:

- match route strength
- number of independent evidence routes
- graph confidence of backing claims
- freshness of backing evidence
- conflict state
- distance from requested intent
- gap between first and second candidate

The resolver must not silently collapse ambiguous candidates. If candidate
scores are close or evidence is weak, the query response returns:

```json
{
  "readiness": "ambiguous",
  "recommended_next_action": "ask_user_to_select_candidate"
}
```

If indexed lookup fails but live search finds relevant files, the response
returns:

```json
{
  "readiness": "needs_update",
  "recommended_next_action": "run_map_update",
  "missing_coverage": ["graph has no capability coverage for login"],
  "fallback_live_hits": ["src/auth/login.ts", "tests/auth/login.test.ts"]
}
```

Semantic guesses are allowed only as low-confidence candidates. They must not be
reported as graph-backed truth unless at least one indexed or evidence-backed
route supports them.

## SQLite Data Model

The initial canonical schema should include the following tables.

### Metadata

```text
metadata(key primary key, value_json, updated_at)
```

Stores schema version, baseline metadata, and runtime options that belong in the
database rather than `status.json`.

### Evidence

```text
evidence(
  id primary key,
  source_kind,
  source_path,
  commit_sha,
  span,
  extractor,
  content_hash,
  captured_at,
  attrs_json
)
```

Indexes:

```text
evidence(source_path)
evidence(source_path, content_hash)
evidence(commit_sha)
```

### Observations

```text
observations(
  id primary key,
  observation_type,
  summary,
  attrs_json,
  created_at,
  updated_at
)
```

Join table:

```text
observation_evidence(observation_id, evidence_id)
```

### Nodes

```text
nodes(
  id primary key,
  type,
  title,
  confidence,
  attrs_json,
  created_at,
  updated_at
)
```

Indexes:

```text
nodes(type)
nodes(confidence)
```

### Edges

```text
edges(
  id primary key,
  type,
  source_id,
  target_id,
  confidence,
  attrs_json,
  created_at,
  updated_at
)
```

Indexes:

```text
edges(source_id)
edges(target_id)
edges(type)
edges(source_id, type)
edges(target_id, type)
```

### Claims

```text
claims(
  id primary key,
  subject_ref,
  predicate,
  object_ref,
  object_value,
  truth_layer,
  confidence,
  status,
  last_validated_at,
  attrs_json
)
```

Indexes:

```text
claims(subject_ref)
claims(predicate)
claims(truth_layer)
claims(status)
```

### Claim Evidence

```text
claim_evidence(claim_id, evidence_id)
```

### Conflicts

```text
conflicts(
  id primary key,
  subject_ref,
  conflict_type,
  impact_scope,
  agent_behavior_rule,
  resolution_status,
  attrs_json,
  updated_at
)
```

Join table:

```text
conflict_claims(conflict_id, claim_id)
```

Indexes:

```text
conflicts(subject_ref)
conflicts(resolution_status)
```

### Path Index

```text
path_index(
  path,
  node_id,
  relation,
  confidence,
  updated_at
)
```

This is the primary bridge from changed files to affected graph nodes.

Indexes:

```text
path_index(path)
path_index(node_id)
```

### Symbol Index

```text
symbol_index(
  symbol_name,
  normalized_symbol,
  node_id,
  path,
  relation,
  confidence
)
```

Indexes:

```text
symbol_index(normalized_symbol)
symbol_index(path)
symbol_index(node_id)
```

### Alias Index

```text
alias_index(
  alias,
  normalized_alias,
  target_type,
  target_id,
  language,
  source,
  confidence,
  evidence_id
)
```

Targets may include:

- capability nodes
- symptom nodes
- entrypoint nodes
- state nodes
- verification nodes

Indexes:

```text
alias_index(normalized_alias)
alias_index(target_id)
alias_index(target_type, normalized_alias)
```

### Entrypoint Index

```text
entrypoint_index(
  entrypoint_key,
  entrypoint_type,
  node_id,
  capability_id,
  path,
  confidence
)
```

Examples:

- HTTP route
- CLI command
- UI route
- event handler
- worker entrypoint

### Test Index

```text
test_index(
  test_path,
  test_name,
  node_id,
  capability_id,
  verification_node_id,
  confidence
)
```

### Slice Membership

```text
slice_members(
  slice_id,
  object_type,
  object_id,
  rank,
  reason,
  updated_at
)
```

Indexes:

```text
slice_members(slice_id)
slice_members(object_id)
```

### Query Examples

```text
query_examples(
  id primary key,
  query_text,
  intent,
  expected_target_type,
  expected_target_id,
  language,
  source,
  created_at
)
```

These examples support recall regression tests for important capabilities and
symptoms.

### Update Events

```text
updates(
  id primary key,
  trigger,
  changed_paths_json,
  affected_nodes_json,
  affected_claims_json,
  affected_slices_json,
  result_state,
  completed_at,
  attrs_json
)
```

## Map Command Contracts

The three existing command names remain, but their contracts change.

### `map-scan`

`map-scan` becomes the evidence and index staging command.

Responsibilities:

- enumerate project-relevant source, tests, scripts, configs, docs, templates,
  and workflow files
- extract evidence records
- extract provisional observations
- discover files, symbols, routes, commands, tests, state surfaces, and config
  surfaces
- build staging path, symbol, entrypoint, test, and alias candidates
- record coverage gaps
- avoid publishing final graph truth

Primary output:

- staged records in `project-cognition.db`
- status metadata showing scan completed but graph not yet published

### `map-build`

`map-build` becomes the graph compiler.

Responsibilities:

- read staged evidence and observations
- deduplicate nodes
- create typed edges
- synthesize claims
- create conflicts
- compute confidence
- build alias, path, symbol, entrypoint, test, and slice indexes
- seed query examples for high-value capabilities
- run query recall checks
- publish runtime readiness in `status.json`

Primary output:

- canonical `project-cognition.db`
- ready `status.json`

### `map-update`

`map-update` becomes a transactional incremental updater.

Responsibilities:

- accept changed paths, commit range, or user supplement
- resolve affected nodes through `path_index`
- refresh evidence only for changed paths
- invalidate claims whose backing evidence changed
- recompute affected nodes, edges, claims, conflicts, aliases, and slices
- append an update event
- rerun readiness checks
- commit or roll back as one transaction

Primary output:

- updated `project-cognition.db`
- updated `status.json`
- update event row

`map-update` must not read or rewrite full graph exports because full graph
exports are no longer canonical.

## Transactional Update Algorithm

For changed paths:

```text
BEGIN IMMEDIATE
  normalize changed paths
  affected_nodes = SELECT node_id FROM path_index WHERE path IN changed_paths
  if affected_nodes is empty:
    run bounded fallback live discovery for changed paths
    create provisional affected nodes or return needs_rebuild

  affected_closure = bounded traversal from affected_nodes
  refresh evidence for changed paths
  compare content hashes
  upsert changed evidence
  update path_index for changed paths
  upsert affected file/symbol/entrypoint/test/state nodes
  upsert or delete affected edges
  invalidate claims backed only by changed stale evidence
  recompute claims for affected subjects
  update conflicts for affected subjects
  update aliases whose sources changed
  recompute affected slice_members
  insert update event
  update status metadata
COMMIT
```

If any step cannot safely bound affected scope, the transaction rolls back and
the command returns:

```text
readiness = needs_rebuild
recommended_next_action = run_map_scan_build
```

## Why Updates Become Effective

The update path becomes effective because it has direct indexes for the two
questions that currently force broad work:

1. Which graph objects does this changed file affect?
2. Which slices and claims depend on those graph objects?

`path_index`, `edges`, `claims`, and `slice_members` answer those questions
without scanning a full JSON graph.

Writes become row-level upserts inside one transaction. A small login file
change updates the login-related rows and slices, not the entire project
cognition graph.

## Debug Example: Login Bug

User request:

```text
login has a bug: valid password login fails
```

Workflow call:

```text
specify cognition query --intent debug --query "login valid password login fails"
```

Resolver steps:

1. Normalize query terms.
2. Lookup aliases for `login`, `valid password`, and `login fails`.
3. Retrieve capability candidates from `alias_index` and `entrypoint_index`.
4. Retrieve symptom candidates from `alias_index`, `test_index`, and risk
   claims.
5. Score candidates with evidence routes and freshness.
6. Expand the winning or user-selected candidate through typed edges.
7. Return implementation, state, claim, conflict, and verification subgraph.

Possible high-confidence result:

```text
capability:auth.login
symptom:valid_credentials_rejected
entrypoint:POST /api/login
implementation:symbol:AuthService.login
implementation:symbol:PasswordVerifier.verify
state:users.password_hash
state:session_store
verification:auth-login-unit
```

If `capability:auth.login` and `capability:admin.sso_login` both score close,
the response is ambiguous and asks the user to choose. It must not silently pick
one.

If indexed lookup fails but live fallback finds `src/auth/login.ts`, the
response reports missing graph coverage and routes to `map-update`.

## Readiness States

Query and update commands should use a shared readiness vocabulary:

- `ready`: graph query is sufficiently grounded for the requested task
- `review`: graph query is usable but requires targeted live verification
- `ambiguous`: multiple candidates require user or workflow selection
- `needs_update`: graph coverage exists but is stale or incomplete for the
  requested task
- `needs_rebuild`: baseline or indexes are not reliable enough for incremental
  repair
- `blocked`: runtime is corrupt, missing, or incompatible

Readiness is separate from recommended action.

Recommended actions:

- `retry_current_workflow`
- `perform_minimal_live_reads`
- `ask_user_to_select_candidate`
- `run_map_update`
- `run_map_scan_build`
- `repair_or_rebuild_database`

## Accuracy Protections

### Evidence Traces

Every returned candidate must include why it matched. Examples:

- `alias:login`
- `entrypoint:POST /api/login`
- `symbol:AuthService.login`
- `test:accepts valid password`
- `claim:AuthService implements user login`
- `semantic_guess`

Only graph-backed traces can raise confidence above weak.

### Ambiguity Handling

The resolver must return `ambiguous` when:

- top candidates are too close
- candidates come from different capabilities with similar names
- there is no strong evidence route
- conflicts affect candidate ownership

### Missing Coverage Detection

The resolver must return `needs_update` when:

- live fallback finds relevant files not connected to any capability
- a capability has no verification route
- a capability has no entrypoint or implementation edge
- a changed path is missing from `path_index`

### Query Recall Tests

`map-build` should seed or preserve query examples for high-value capabilities.
Regression checks should verify examples resolve to expected targets.

Examples:

```text
login bug -> capability:auth.login
valid password rejected -> symptom:valid_credentials_rejected
session lost after login -> symptom:session_not_persisted
```

Failed recall checks should degrade readiness instead of letting the graph
pretend to be complete.

## Failure and Escalation Boundaries

Use `map-update` when:

- changed paths map to known nodes
- missing coverage is localized
- affected closure is bounded
- indexes are valid
- schema version is compatible

Use `map-scan` followed by `map-build` when:

- database schema is incompatible
- indexes are missing or corrupt
- path-to-node mapping fails for broad project areas
- a repository restructure invalidates too much path coverage
- recall checks fail across multiple core capabilities
- affected closure cannot be bounded safely

The system must explain the exact reason for escalation.

## CLI and Runtime Surface

Add or formalize the following helper commands:

```text
specify cognition status [--format json]
specify cognition query --intent <intent> [--query <text>] [--paths <paths...>] [--format json]
specify cognition update --changed-paths <paths...> [--reason <reason>] [--format json]
specify cognition rebuild
specify cognition doctor
```

`sp-map-scan`, `sp-map-build`, and `sp-map-update` remain workflow-level
commands. The `cognition` CLI group is the lower-level runtime API they use.

## Testing Surface

Regression coverage should include:

- schema creation and migration from empty runtime
- `map-scan` stages evidence and indexes without publishing ready truth
- `map-build` creates graph nodes, edges, indexes, slices, and query examples
- `cognition query` returns a task-local bundle without raw graph artifacts
- login query resolves by aliases, entrypoints, symbols, and tests
- ambiguous login query returns multiple candidates
- query with missing coverage returns `needs_update`
- `map-update` changes only affected rows for a small path change
- `map-update` rolls back on failed bounded update
- update events record affected paths, nodes, claims, and slices
- query recall checks degrade readiness when examples fail
- workflow templates no longer require direct reads of raw graph JSON files

## Rollout Strategy

Because backwards compatibility is not required, the rollout can be a direct
runtime replacement:

1. Add SQLite schema and repository/query/update APIs.
2. Change `map-scan` to stage evidence and indexes in the database.
3. Change `map-build` to compile the database graph and mark status ready.
4. Change `map-update` to use path-indexed transactional updates.
5. Change workflow templates to use `cognition query` instead of raw graph
   reads.
6. Remove raw graph JSON artifacts from required runtime paths and tests.
7. Add query recall and localized update regression coverage.

## Acceptance Criteria

- Workflows no longer require reading `graph/nodes.json`, `graph/edges.json`,
  `graph/claims.json`, or `graph/conflicts.json`.
- `project-cognition.db` is the canonical graph truth store.
- `status.json` points to the active graph store and records readiness.
- `cognition query` returns task-local bundles with evidence traces.
- Natural-language capability and symptom matching returns candidates with
  `matched_by` evidence.
- Ambiguous query results are surfaced as ambiguous, not silently resolved.
- Missing graph coverage is surfaced as `needs_update`.
- Small changed-path updates do not read or rewrite full graph artifacts.
- `map-update` uses transactions and rolls back incomplete updates.
- Query recall tests protect high-value capability lookup.
- `map-scan`, `map-build`, and `map-update` have distinct responsibilities and
  no longer share a heavy all-graph read/write path.

## Decision

Proceed with a SQLite canonical project cognition graph store, a query resolver
that returns evidence-backed task-local bundles, and a transactional
`map-update` path driven by path, symbol, alias, entrypoint, test, edge, claim,
and slice indexes.

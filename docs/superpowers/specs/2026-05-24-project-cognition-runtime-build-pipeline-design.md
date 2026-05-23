# Project Cognition Runtime Build Pipeline Design

**Date:** 2026-05-24  
**Status:** Draft for user review  
**Owner:** Codex

## Summary

The Go `project-cognition` runtime has become the canonical runtime direction,
but the current implementation does not yet own the full `map-scan ->
map-build -> SQLite` construction path. It validates scan and build artifacts,
publishes runtime metadata, and exposes shallow query/update helpers, but it
does not provide an official importer that turns scan artifacts into a complete
SQLite generation.

That missing importer is the root cause of the observed failure where scan
produced substantial evidence but build persisted only a hand-picked subset.
Agents had to write SQL manually because the product did not expose a supported
record-insertion surface.

This design keeps the Go runtime direction and closes that product gap. The
runtime must provide a transactional build pipeline, stronger build validation,
and a staged path for update/query/lexicon behavior to use the graph store
rather than prompt-only reconstruction.

## Context

This design builds on these approved directions:

- `2026-05-13-project-cognition-sqlite-graph-store-design.md`: SQLite is the
  canonical project cognition truth store.
- `2026-05-21-map-update-first-maintenance-design.md`: after a usable baseline
  exists, ordinary maintenance should go through `map-update`, not full
  scan/build.
- `2026-05-22-project-cognition-go-runtime-design.md`: the standalone Go
  executable is the only project cognition runtime.

The recent failure exposed an implementation gap between those designs and the
current runtime surface:

- `validate-scan` correctly catches scan schema problems such as BOM-polluted
  JSON and missing `path` or `rows` fields.
- `validate-build` requires a Go-format status/runtime but does not prove that
  all scan artifacts were imported into SQLite.
- `store` has schema and metadata methods but no public graph writer APIs for
  evidence, nodes, edges, claims, conflicts, or indexes.
- `sp-map-build` promises graph construction, but the runtime does not provide
  a graph construction command.
- `map-update`, `lexicon`, and `query` are present as commands, but their
  current behavior is shallower than the workflow contracts describe.

## Problem

The current runtime has a responsibility gap: scan artifacts are machine-readable
and SQLite schema exists, but there is no supported bridge between them.

That creates four practical failures.

### 1. Agents can silently drop scan results during build

When the runtime exposes no importer, agents fall back to ad hoc SQL or manual
selection. The build can then persist only a fraction of the scan package while
still looking structurally valid to later commands.

The observed example was:

- scan read hundreds of files
- scan produced evidence, provisional nodes, provisional edges, and observations
- build inserted only a subset of nodes and edges
- build validation did not fail on that loss

### 2. Runtime format checks happen too late and too separately

`publish-runtime-metadata`, `validate-build`, and `complete-refresh` expect the
Go runtime format. If a workflow or manual workaround writes a legacy-shaped
status file, runtime commands fail with `unsupported_legacy_runtime`. That error
is correct for a hard switch, but the normal build command should be the thing
that creates the Go-format runtime, not a later command that discovers the
format mismatch.

### 3. Prompt contracts exceed runtime behavior

`map-build` promises a graph with evidence, nodes, edges, claims, conflicts,
indexes, concept candidates, and route packs. The runtime schema supports much
of this shape, but the implementation does not own enough write APIs or import
rules to make the contract enforceable.

The same pattern appears in `map-update`, `lexicon`, and `query`: command names
exist, but their behavior does not yet match the graph-native operating model.

### 4. Validation checks structure more than fidelity

`validate-build` checks that required files and tables exist and that critical
tables are non-empty. It does not compare the DB against the scan package. A DB
with 35 imported nodes can pass even when the scan package contained 103.

## Goals

- Make the Go runtime own the official scan-artifact-to-SQLite build path.
- Eliminate normal workflow dependence on manual SQL, sqlite shell scripting, or
  ad hoc Bun/TypeScript import helpers.
- Ensure build validation fails when scan artifacts are silently lost.
- Make runtime metadata and status publication part of one explicit publish
  protocol, with SQLite changes transactional and `status.json` written
  atomically.
- Keep `unsupported_legacy_runtime` as a valid hard-switch guard, but provide a
  clear recovery path through the official build command.
- Add store-level writer APIs that match the schema instead of forcing callers
  to write raw SQL.
- Stage follow-up runtime work so `map-update`, `lexicon`, and `query` become
  graph-backed without turning the first implementation into a broad rewrite.
- Update templates, docs, tests, and generated workflow guidance together.

## Non-Goals

- Do not restore the Python-era project cognition runtime.
- Do not add a second canonical runtime format.
- Do not make downstream agents write raw SQLite as the normal path.
- Do not require perfect semantic claims/conflicts synthesis in the first
  importer version.
- Do not make `map-build` reread the whole repository to compensate for weak
  scan artifacts.
- Do not hide scan gaps by importing incomplete data as if it were complete.

## Approved Direction

Use a runtime-first, phased completion plan.

Phase 1 fixes the baseline construction failure:

```text
sp-map-scan artifacts
        |
        v
project-cognition build-from-scan --format json
        |
        v
.specify/project-cognition/project-cognition.db
.specify/project-cognition/status.json
        |
        v
project-cognition validate-build --format json
```

Phase 2 makes `map-update` use the same graph writer layer for incremental
maintenance.

Phase 3 makes `lexicon` and `query` read graph-backed indexes and return honest
route packs, ambiguity, evidence traces, and missing-coverage signals.

## Runtime Command Contract

Add a new build command:

```text
project-cognition build-from-scan --format json
```

Allowed aliases:

```text
project-cognition import-scan --format json
project-cognition rebuild-from-scan --format json
```

The canonical command in generated workflows should be `build-from-scan`.
Aliases may exist for operator convenience, but templates should not teach
multiple names.

The command reads the current project's scan package from:

```text
.specify/project-cognition/
  evidence/
  provisional/nodes.json
  provisional/edges.json
  provisional/observations.json
  coverage.json
  status.json                  # optional scan-stage state input; not a Go runtime prerequisite
  workbench/map-scan.md
  workbench/coverage-ledger.md
  workbench/coverage-ledger.json
  workbench/scan-packets/
  workbench/map-state.md
  workbench/repository-universe.json
  workbench/capability-ledger.json
  workbench/control-ledger.json
```

The command must:

- run shared scan artifact validation without requiring a pre-existing Go-format
  runtime status
- create or replace the active graph generation transactionally
- import every valid evidence record, provisional node, provisional edge,
  observation, and coverage/path relation
- write required graph indexes, especially `path_index`
- publish runtime metadata
- write Go-format `status.json`
- return machine-readable counts and warnings

The command must not require a pre-existing Go-format `status.json`. It is the
entrypoint that creates a Go-format baseline from validated scan artifacts. If a
scan-stage `status.json` exists, `build-from-scan` may parse it as generic JSON
for provenance and blocking metadata, but it must not call `ReadStatus` before
the new Go-format baseline has been published.

## Store Writer APIs

The Go `store` package should expose domain writer methods instead of making CLI
commands construct SQL directly. The exact Go names can change during
implementation, but the boundary should cover:

- create graph generation
- import evidence rows
- import observations
- import nodes
- import edges
- import claims and conflicts when provided
- import path index rows
- import symbol, alias, entrypoint, test, slice, and query example rows when
  available
- record rejected or skipped scan rows with explicit reasons
- publish runtime metadata

All write APIs used by `build-from-scan` must run inside a single transaction.
If any required import step fails, the previous active generation remains usable
and the partial generation is not published as active.

## Publish Protocol

SQLite changes can be transactional; `status.json` cannot participate in that
SQLite transaction. `build-from-scan` therefore needs a two-phase publish
protocol with explicit recovery semantics.

The publish order should be:

1. Open the DB transaction.
2. Insert the new generation with `state='building'`.
3. Import evidence, observations, nodes, edges, indexes, metadata, rejections,
   and merge records.
4. Run internal structural and identity reconciliation checks inside the
   transaction.
5. Change the new generation to `state='active'` and mark the previous active
   generation superseded inside the same DB transaction.
6. Commit the DB transaction.
7. Write the new Go-format status to a temporary file in the runtime directory.
8. Atomically replace `status.json` with the temporary file.
9. Re-read status and DB metadata to verify they agree on active generation,
   graph store path, runtime format, and schema.

If any step before the DB commit fails, the DB transaction rolls back and the
previous active generation remains published.

If the DB commit succeeds but the status write or atomic replace fails,
`build-from-scan` must report `status=blocked`, leave the DB active generation
intact, and include a recovery action that rewrites `status.json` from DB
metadata. A follow-up command may be added for that recovery path, but the first
implementation can make rerunning `build-from-scan` perform the repair after
revalidating the same scan package.

If the final DB/status agreement check fails, `build-from-scan` must report
`status=blocked` and identify whether DB metadata or `status.json` is stale. It
must not report the baseline as query-ready until the agreement check passes.

All baseline-reading commands must enforce the same DB/status agreement gate
before returning graph data or mutating the runtime. If `status.json` and the DB
active generation disagree, commands such as `query`, `lexicon`, `update`,
`validate-build`, `complete-refresh`, `read`, and `discover` must return
`status=blocked` with a recovery action instead of continuing against either
side of the split-brain state.

## Import Fidelity Rules

`build-from-scan` must preserve the scan package unless a row is invalid and
explicitly rejected.

Minimum row fidelity requirements:

- every scan evidence row becomes a DB evidence row or a rejected row with a
  machine-readable reason
- every provisional node becomes a DB node or a rejected row with a
  machine-readable reason
- every provisional edge becomes a DB edge or a rejected row with a
  machine-readable reason
- every covered repository path that has project relevance becomes a
  `path_index` row or a rejected row with a machine-readable reason
- observations are retained in the existing `observations` table
- rejected rows are recorded in active generation metadata under a structured
  `rejections` key for the first phase

Fidelity is identity-based, not count-only. The importer and validator must
reconcile expected row identities against DB row identities:

- evidence identity: evidence id when present, plus source path and content hash
- node identity: provisional node id
- edge identity: provisional edge id, source id, target id, and edge type
- observation identity: observation id
- coverage identity: normalized repository path

If the importer intentionally merges duplicate scan rows, it must record a
structured merge record that maps each source identity to the surviving DB
identity. A row may be absent from the DB only when it has a rejection record or
a merge record. Count equality alone is never sufficient.

The first importer does not need to invent high-confidence semantic claims that
the scan package did not support. It may seed minimal claims, conflicts, aliases,
and query examples only when the scan artifacts provide enough evidence.

## Build Validation

`validate-build` must become a fidelity gate, not only a structural gate.

It should continue checking:

- DB exists
- required tables and columns exist
- schema metadata exists
- active generation exists
- status is Go-format
- key graph tables are non-empty

It must also compare scan artifacts to DB import identity sets:

- evidence ids, source paths, and content hashes
- provisional node ids
- provisional edge ids, source ids, target ids, and edge types
- observation ids
- normalized coverage paths
- rejected row identities by category and reason
- merge source identities and surviving DB identities

Validation should fail when valid scan rows are missing from the DB without an
explicit rejection or merge record. It should also fail when DB rows claim scan
origin identities that do not exist in the scan package.

JSON output should include enough detail for prompts and tests:

```json
{
  "status": "blocked",
  "scan_artifact_counts": {
    "evidence": 203,
    "nodes": 103,
    "edges": 92,
    "observations": 18
  },
  "db_counts": {
    "evidence": 203,
    "nodes": 103,
    "edges": 92,
    "observations": 18
  },
  "identity_reconciliation": {
    "evidence": "ok",
    "nodes": "ok",
    "edges": "ok",
    "observations": "ok",
    "coverage_paths": "ok"
  },
  "rejections": []
}
```

The numbers above are illustrative. Tests should use fixtures rather than these
exact values. The key acceptance rule is identity reconciliation, with counts as
summary diagnostics.

## Legacy Runtime Handling

The Go hard switch remains in force. Runtime commands should still reject
legacy status/runtime formats when they are expected to read an existing active
baseline.

`build-from-scan` is different: it creates a new Go-format runtime baseline.
Its behavior should be:

- If no runtime exists, create one.
- If a valid Go-format runtime exists, create a new generation and publish it
  only after successful validation.
- If a legacy runtime exists and a validated scan package exists, replace it
  only through the explicit build command path and report that replacement in
  JSON output.
- If a legacy runtime exists but scan validation fails, leave the legacy files in
  place and report the scan errors.

This keeps the hard switch honest while giving `sp-map-build` a supported
recovery path.

## Workflow Template Changes

`templates/commands/map-build.md` and its shell partial should stop asking the
agent to construct SQLite directly.

The generated workflow should:

1. run `project-cognition validate-scan --format json`
2. inspect scan validation output and stop on errors
3. run `project-cognition build-from-scan --format json`
4. run `project-cognition validate-build --format json`
5. rely on `build-from-scan` to mark the baseline complete after validation has
   succeeded internally

The prompt should explicitly say that manual SQL, hand-picked node subsets, and
leader-memory graph reconstruction are not acceptable normal build paths.

`publish-runtime-metadata` may remain as an operator command, but normal
`map-build` should not depend on agents calling it as a separate fragile step if
`build-from-scan` already published metadata transactionally.

`complete-refresh` may remain available for non-build maintenance flows, but a
successful baseline build should not require a separate completion command that
can fail after the DB was already published.

## Scan Validation Hardening

The scan-side problems were schema compliance problems, not graph design
problems. Keep them in `validate-scan`, but improve diagnostics:

- detect UTF-8 BOM at the start of JSON files and report a direct "JSON contains
  UTF-8 BOM" error
- keep requiring `coverage.json.rows[].path`
- keep requiring top-level `coverage-ledger.json.rows`
- keep rejecting `.specify/**` as scan coverage/evidence
- report the exact file and JSON path for missing required fields

Workflow guidance should tell agents to use runtime or write-file tools that
produce UTF-8 without BOM for machine JSON on Windows.

Scan validation should be factored into two layers:

- artifact validation: required directories/files, JSON shape, BOM detection,
  coverage rows, coverage ledger rows, open gap blocking, `.specify/**`
  exclusion, and scan packet presence
- runtime status validation: checks that an existing `status.json` is readable
  and acceptable for commands that are reading an already-published runtime

`project-cognition validate-scan` may continue to require scan-stage
`status.json` for the current workflow gate. `build-from-scan` must call the
artifact validation layer directly so first baseline construction is not blocked
by the absence of a Go-format runtime status. This split keeps scan acceptance
strict while allowing the build command to create the first Go-format status.

## Map Update Follow-Up

After Phase 1, `map-update` should be moved onto the same writer layer.

The update command should:

- derive changed paths from explicit flags or git state
- read existing `path_index` and affected graph nodes
- create update records
- add or revise evidence rows for touched paths
- adopt new path coverage when live reads prove the relationship
- record low-confidence, known-unknown, or minimal-live-read state instead of
  recommending scan/build for ordinary gaps
- update status metadata without invalidating the active generation unless the
  baseline is structurally unusable

This preserves the `map-update-first` policy: missing or weak coverage becomes
incremental maintenance work, not a reason to rebuild the entire baseline.

## Lexicon and Query Follow-Up

After the baseline importer is reliable, `lexicon` and `query` should stop
being shallow path helpers.

`lexicon` should use:

- `alias_index`
- `query_examples`
- node labels and tags
- path and symbol indexes
- evidence-backed concepts from the active generation

`query` should use:

- selected lexicon candidates
- `path_index`
- node and edge traversal
- evidence rows
- claims and conflicts when available
- confidence and ambiguity metadata

Query output should distinguish:

- graph evidence
- live-read requirements
- ambiguous candidate matches
- missing coverage
- stale or partial update state

The runtime should not present inferred graph routes as certain when the DB only
supports a weak match.

## Error Handling

All machine-facing commands must produce JSON errors with stable fields:

- `status`
- `errors`
- `warnings`
- `recommended_next_action`
- `status_path`
- `graph_store_path`
- relevant count or validation detail fields

`build-from-scan` must be transactional. If it fails, it should leave the
previous active generation intact and report whether any temporary generation
was rolled back.

Validation errors should be specific enough that an agent can fix the artifact
without guessing. Examples:

- `coverage.rows[12].path is required`
- `coverage-ledger.json.rows is required`
- `evidence/runtime-summary.json contains UTF-8 BOM`
- `db missing 68 imported nodes from provisional/nodes.json`

## Testing Strategy

Add Go tests for:

- successful full import from fixture scan artifacts
- identity reconciliation for evidence, nodes, edges, observations, and paths
- validation failure when DB rows are missing, substituted, or falsely claim
  scan-origin identities
- transaction rollback on malformed input
- legacy status replacement through `build-from-scan`
- legacy status rejection through ordinary read/query commands
- BOM-specific scan validation diagnostics
- store writer APIs without using raw SQL from CLI tests

Add repository-level tests for:

- generated `sp-map-build` guidance calls `build-from-scan`
- generated guidance no longer teaches manual SQL as normal flow
- `validate-build` output includes scan-vs-DB identity reconciliation details
- templates, passive skills, docs, and shell partials stay aligned

Add a regression fixture that models the observed failure shape:

- scan artifacts contain many more nodes/edges than an intentionally truncated
  DB
- `validate-build` must fail and report the mismatch
- scan artifacts and DB contain the same number of rows but different node,
  edge, evidence, or coverage identities
- `validate-build` must fail the substituted-row case too

## Implementation Surface

Expected implementation areas:

- `tools/project-cognition/internal/store/**`
- `tools/project-cognition/internal/cli/**`
- `tools/project-cognition/internal/validation/**`
- `tools/project-cognition/internal/runtime/**`
- `tools/project-cognition/internal/update/**`
- `tools/project-cognition/internal/query/**`
- `templates/commands/map-build.md`
- `templates/command-partials/map-build/shell.md`
- `templates/commands/map-update.md`
- passive skill mirrors under `templates/passive-skills/**`
- worker prompts that mention map scan/build/update artifacts
- `README.md`
- `PROJECT-HANDBOOK.md`
- release/runtime docs if command names or installer behavior change
- Go tests under `tools/project-cognition`
- Python/template alignment tests under `tests/**`

Use the workflow change surface index in `AGENTS.md` before implementation so
the change does not land as a template-only or runtime-only fix.

## Acceptance Criteria

- A validated scan package can be imported into SQLite without manual SQL.
- The build command writes Go-format status and metadata.
- `validate-build` fails when DB row identities do not match scan artifact row
  identities, even if counts match.
- `sp-map-build` guidance routes through the official runtime command.
- Existing Go-format baselines are updated by creating a new generation, not by
  partial in-place mutation.
- Legacy-format runtimes have a clear build recovery path but remain rejected by
  ordinary read/query/update commands.
- Tests cover the exact class of data-loss failure that motivated this design.

## Implementation Defaults

- Use the existing `observations` table for scan observations.
- Store rejected scan rows in `generations.attrs_json.rejections` for the first
  phase instead of adding a new schema table.
- Make `build-from-scan` publish metadata, write Go-format status, validate the
  imported generation, and mark the baseline complete in one command.
- Keep the first `build-from-scan` JSON schema small: `status`, `errors`,
  `warnings`, `scan_artifact_counts`, `db_counts`,
  `identity_reconciliation`, `rejections`, `merge_records`,
  `recovery_action`, `status_path`, `graph_store_path`, and
  `active_generation_id`. `identity_reconciliation`, `merge_records`, and
  `recovery_action` must be present in blocked or diagnostic outputs; they may
  be compact success summaries in the `ok` case.

These defaults can be revised during implementation only if code evidence shows
they create unnecessary complexity or conflict with existing runtime invariants.
The core requirement remains unchanged: the runtime owns complete, validated
import from scan artifacts to SQLite.

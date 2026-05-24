# Project Cognition Coverage Boundary Design

Date: 2026-05-24

## Context

`sp-map-scan`, `sp-map-build`, and `sp-map-update` rely on subagents to inspect
large repositories and publish project cognition evidence. In large projects,
subagents may receive broad lane prompts such as "scan the Python area" while the
actual file set is too large for one context window. When the lane is not
path-bounded and auditable, a subagent can optimize for "important-looking"
files and silently omit lower-salience files. The resulting map appears useful
but misses repository surfaces.

The system needs to make coverage a contract, not an agent attitude.

## Goal

Make project cognition maintenance produce auditable path coverage across full
baseline scans, graph builds, and incremental updates without requiring users to
manually maintain `.cognitionignore` before the workflow is useful.

## Non-Goals

- Do not require users to approve every scan directory before normal work.
- Do not make `.cognitionignore` the primary user interface.
- Do not turn `sp-map-update` into a full repository scan.
- Do not let `sp-map-build` compensate for missing scan evidence by guessing.

## Recommended Approach

Use automatic scan boundary planning with low-interruption user review.

1. The leader establishes the candidate universe from Git-tracked paths and
   explicit user-supplied paths.
2. The workflow applies built-in low-risk exclusions and `.cognitionignore`
   rules.
3. The leader classifies every candidate path into a required disposition.
4. Only high-impact ambiguous boundaries require user confirmation.
5. The workflow persists the final boundary in
   `.specify/project-cognition/workbench/repository-universe.json` and every
   subagent packet must account for assigned paths.
6. Validation fails when included paths are not explained by coverage rows,
   accepted gaps, or exclusions.

`.cognitionignore` remains supported as an advanced and persisted override, but
correct baseline behavior must not depend on the user knowing that file exists.

## Boundary Model

The project cognition boundary has these inputs:

- Git-tracked files, from `git ls-files`, as the default baseline universe.
- Git diffs, commit ranges, or explicit changed paths for incremental update
  candidates.
- Built-in ignore heuristics for common non-source outputs and caches.
- `.cognitionignore` and `.specify/project-cognition/.cognitionignore` as
  project-specific overrides.
- User answers for ambiguous high-impact paths.

Every candidate path receives exactly one disposition. Disposition is a coverage
handling decision, separate from criticality and scan depth priority:

- `deep_read`: content must be read and evidence extracted.
- `sampled`: representative examples are read and the sampling reason is
  recorded.
- `inventory_only`: path, ownership, and role are recorded without a full content
  read.
- `excluded`: path is intentionally outside project cognition scope.
- `blocked`: path should be handled but cannot be safely processed now.

"Not deep-read" is not the same as "not recorded." Inventory-only and sampled
paths still need explicit coverage rows. Excluded paths need explicit boundary
accounting in `repository-universe.json` or a grouped exclusion ledger, but must
not appear in graph-facing `coverage.json` rows, project evidence, or runtime
indexes.

Criticality remains a separate classification used after disposition:

- `critical`
- `important`
- `low_risk`

The workflow may derive criticality from ownership, entrypoint status,
downstream consumers, state/lifecycle role, generated-surface propagation,
verification reachability, security sensitivity, and recent Git evolution.

## User Review Policy

The workflow should not routinely ask users to edit ignore files or approve
large directory lists. It should continue automatically when the boundary planner
can classify paths confidently.

Ask the user only when a boundary decision is both ambiguous and likely to affect
map quality, for example:

- A generated-looking directory is imported by source code.
- An archived or legacy directory still has runtime entry points.
- A large documentation tree may contain the only business or workflow truth.
- A vendored-looking directory contains local patches or source ownership.

The question should be narrow and actionable, such as choosing one disposition
for one ambiguous path group. The accepted answer should be persisted to the
project cognition policy surface or converted into a suggested
`.cognitionignore` rule so the same question does not recur.

## Scan Contract

`sp-map-scan` owns the full boundary and packetization contract.

Before dispatching subagents, the leader must write or stage the canonical
boundary artifact:

- `.specify/project-cognition/workbench/repository-universe.json`

The schema should evolve from a loose inventory into a versioned boundary
contract. It must include:

- `schema_version`
- `candidate_universe`
- `included_paths`
- `excluded_paths`
- `ambiguous_paths`
- `dispositions`
- `classification_reasons`
- `decision_source` for each decision, such as git, built-in heuristic,
  `.cognitionignore`, or user decision
- optional grouped exclusion summaries for large generated, cache, fixture,
  archive, or vendor trees

Each `MapScanPacket` must include a bounded `assigned_paths` list. Subagents may
not silently narrow this list. For every assigned path, the handoff must return
one of:

- evidence and `paths_read`
- `sampled` with reason and representative paths
- `inventory_only` with reason
- `excluded` with the rule or decision source
- `blocked` with blocker and recovery condition

If a subagent cannot fit the assigned set in context, it must return an overflow
or blocked result. The leader then splits and redispatches the lane or records a
blocking coverage gap.

## Build Contract

`sp-map-build` must treat scan artifacts as the only accepted scan package. It
must not decide that unscanned files are unimportant.

Before publishing query-backed runtime truth, build validation must confirm:

- every included path is represented in scan coverage or an accepted gap
- every critical and important coverage row has supporting evidence
- excluded paths are represented only by the boundary artifact or grouped
  exclusion ledger, not by graph-facing coverage rows
- every scan packet has been consumed
- every accepted packet result reports paths read or a non-read disposition
- no `.cognitionignore`-excluded path enters graph evidence or runtime route
  indexes

If these checks fail, `sp-map-build` returns a scan gap report and routes back to
`sp-map-scan` rather than synthesizing graph truth.

## Update Contract

`sp-map-update` starts from changed paths, not the full repository.

The update candidate set comes from:

- current Git diff
- staged diff
- supplied commit range
- explicit user paths or corrections

After applying built-in exclusions and cognition ignore rules, the leader queries
the current project cognition runtime for each remaining changed path and expands
only through known affected closure: owners, consumers, generated surfaces,
state/lifecycle edges, conflicts, known unknowns, and verification routes.

Every changed path must be accounted for as:

- updated
- provisionally adopted
- ignored with reason
- partial with `minimal_live_reads`
- blocked with recovery condition
- requiring full rebuild for a reserved rebuild reason

Uncertain closure should become `partial_refresh`, low-confidence claims,
conflicts, known unknowns, and `minimal_live_reads`. It should not silently skip
paths and should not escalate to scan/build unless the baseline is missing,
unusable, schema-invalid, has zero active-generation `path_index` rows, the user
explicitly requested rebuild, or baseline identity is invalid.

## Validation

The project cognition runtime should grow machine checks that compare boundary,
packet, coverage, and result artifacts.

At minimum, `validate-scan` should fail when:

- a Git-tracked candidate path has no disposition in
  `repository-universe.json`
- a scan packet omits assigned path accounting
- a subagent handoff summarizes work without path-level evidence or disposition
- `coverage.json` and `coverage-ledger.json` disagree on represented paths
- excluded paths appear in `coverage.json`, graph-facing coverage rows, project
  evidence, provisional graph rows, runtime indexes, or `minimal_live_reads`
- blocked or unknown critical gaps remain unresolved
- ignored paths leak into evidence, provisional nodes, provisional edges,
  observations, route indexes, or `minimal_live_reads`

`validate-build` should fail when the accepted scan package cannot support graph
publication without inventing coverage.

`map-update` validation should fail or report partial readiness when changed
paths are not accounted for by update records, ignored-path reports,
`minimal_live_reads`, or explicit rebuild conditions.

## Persistence

The workflow should persist boundary decisions in generated project state so
later runs are stable:

- the canonical boundary artifact at
  `.specify/project-cognition/workbench/repository-universe.json`
- coverage rows in `.specify/project-cognition/coverage.json`
- ledger rows in `.specify/project-cognition/workbench/coverage-ledger.json`
- grouped exclusion rows in the boundary artifact or a dedicated exclusion
  ledger that does not feed graph-facing coverage
- optional project policy for repeated user decisions
- optional generated `.cognitionignore` suggestions for durable exclusions

The system should distinguish user decisions from automatic heuristics so future
tools can explain or revise them.

## Open Risks

- Built-in heuristics can still misclassify unusual repositories, so ambiguous
  high-impact groups must stay visible.
- Very large tracked source trees may need multiple scan waves and overflow
  handling.
- Some Git-untracked files can be operationally important. The default should be
  Git-tracked coverage, but user-supplied paths and explicit workflow hints must
  allow untracked paths to enter the boundary.
- Persisted decisions need a clear revision path when the repository changes.

## Acceptance Criteria

- `sp-map-scan` can describe the exact candidate universe before dispatch.
- Subagent packets include explicit assigned paths and cannot pass by summary
  alone.
- Every candidate path ends in a disposition or open gap.
- `sp-map-build` refuses to publish graph truth from incomplete scan coverage.
- `sp-map-update` accounts for each changed path without broad full-scan
  escalation.
- Users are asked only about ambiguous, high-impact boundaries, and those answers
  are persisted.

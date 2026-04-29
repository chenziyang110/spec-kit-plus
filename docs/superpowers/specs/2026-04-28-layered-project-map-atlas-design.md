# Layered Project-Map Atlas Design

**Date:** 2026-04-28
**Status:** Proposed
**Owner:** Codex

## Summary

This design evolves the current handbook plus flat topical `project-map` into a
layered atlas that can scale to repositories with multiple subprojects and
modules without collapsing technical truth into one global document set.

The approved direction is:

- keep `PROJECT-HANDBOOK.md` as the stable root entrypoint
- add a machine-readable index layer under `.specify/project-map/index/`
- split technical truth into root-level topical documents and module-level
  document sets
- allow deeper per-module documentation without requiring global full refreshes
- make agent read order, stale detection, and refresh behavior explicit so the
  atlas is both human-readable and machine-routable

This is not a token-saving design. The objective is to preserve or increase
technical detail while separating it into maintainable layers.

## Problem Statement

The current atlas shape is:

- one root `PROJECT-HANDBOOK.md`
- one global `.specify/project-map/` topical set
- one global `status.json`

That is sufficient for medium repositories but starts to fail when a repository
contains multiple subprojects, module roots, or independently evolving
subsystems.

The failure modes are:

1. The global topical files become too broad and accumulate details for many
   unrelated modules.
2. Agents can tell that documentation exists, but cannot reliably determine
   which subset of it owns the touched area.
3. Refreshes are all-or-nothing even when only one module changed.
4. Cross-module and module-local truth are mixed together, which makes updates
   noisy and stale-state reasoning imprecise.
5. Deep technical detail has no structured place to live except the global
   topical files, so detail either bloats the root map or is omitted.

The result is not lack of documentation. The result is insufficient structure.

## Goals

- Preserve `PROJECT-HANDBOOK.md` as the first-read entrypoint.
- Add a machine-readable atlas index that can route agents into the correct
  module or root layer before broad code reads.
- Support repositories with multiple subprojects, packages, services, or
  module families.
- Keep cross-module truth in root-level documents instead of duplicating it in
  every module.
- Let module-level docs hold complete technical truth for that module, not just
  a lightweight summary.
- Support partial refresh by module, with explicit root-document fallout.
- Represent stale state at both the global and module levels.
- Surface `deep` module content as first-class but separately stale-able.

## Non-Goals

- Do not replace `PROJECT-HANDBOOK.md` with a purely machine-owned index file.
- Do not reduce documentation depth in the name of smaller context windows.
- Do not create free-form per-module documentation trees without a contract.
- Do not require deep module content to be regenerated on every atlas refresh.
- Do not eliminate the existing root topical concerns such as architecture,
  workflows, integrations, testing, and operations.

## Approved Layer Model

The layered atlas has four content surfaces and one status surface.

### 1. Root Entry Surface

`PROJECT-HANDBOOK.md` remains the stable root navigation artifact at the
repository root.

Purpose:

- orientation for humans and agents
- first routing step into the atlas
- summary of shared surfaces, risky coordination points, and topic routing
- high-level change impact guide and verification entry points

This file stays index-first. It is not the place to hide module internals.

### 2. Machine Index Surface

`.specify/project-map/index/`

This is the machine-readable routing layer. It exists so agents can discover
modules, choose the next documentation reads, and determine whether atlas
coverage is fresh enough before making architectural or implementation
judgments.

Canonical files:

- `.specify/project-map/index/atlas-config.json`
- `.specify/project-map/index/atlas-index.json`
- `.specify/project-map/index/modules.json`
- `.specify/project-map/index/relations.json`
- `.specify/project-map/index/status.json`

### 3. Root Topical Surface

`.specify/project-map/root/`

This layer stores global topical documents whose truth is not owned by any
single module.

Canonical files:

- `ARCHITECTURE.md`
- `STRUCTURE.md`
- `CONVENTIONS.md`
- `INTEGRATIONS.md`
- `WORKFLOWS.md`
- `TESTING.md`
- `OPERATIONS.md`

These files cover shared contracts, cross-module seams, root-level workflow
rules, shared testing strategy, and platform/runtime invariants.

### 4. Module Surface

`.specify/project-map/modules/<module-id>/`

Each module receives its own documentation set. Module docs are not summaries.
They are the module-local truth-owning atlas layer.

Canonical module files:

- `OVERVIEW.md`
- `ARCHITECTURE.md`
- `STRUCTURE.md`
- `WORKFLOWS.md`
- `TESTING.md`

Each module may also include:

```text
deep/
  capabilities/
  workflows/
  integrations/
  runtime/
  references/
```

The `deep/` tree is controlled, not free-form.

### 5. Status Surface

`.specify/project-map/index/status.json`

This is the single freshness and staleness status source. It replaces the idea
that one global `fresh/stale` bit is enough.

## Module Discovery Model

Module discovery uses automatic top-level detection with explicit human
overrides.

The approved model is:

- auto-detect top-level module candidates from repository layout
- allow manual merge, split, rename, or tagging through `atlas-config.json`
- default module identifiers derive from path
- stable overrides are allowed when path-derived IDs are not sufficient

### Stable Module Fields

The module registry should distinguish stable ownership roots from pattern-based
coverage.

Approved fields:

- `module_id`
- `display_name`
- `root_paths`
- `include_globs`
- `exclude_globs`
- `tags`
- `owner_topics`
- `doc_paths`

`root_paths` are stable owned roots such as:

- `src/specify_cli/integrations`
- `src/specify_cli/codex_team`

`include_globs` may extend coverage for non-owned but relevant paths such as:

- `tests/codex_team/**`
- `templates/project-map/**`

`exclude_globs` remove noise such as generated fixtures, snapshots, or broad
directories that should not affect module freshness.

This is stricter than using globs directly in `root_paths`, because ownership
and coverage are not the same concept.

## Machine Index Contracts

### `atlas-index.json`

`atlas-index.json` is the entry summary, not the decision source.

It should remain intentionally small and contain only routing summary fields
such as:

- `version`
- `generated_at`
- `modules_count`
- `last_full_refresh_commit`
- `global_freshness`
- `primary_root_docs`
- `module_registry_path`
- `relations_path`
- `status_path`

Agents may use this file to know what to load next. They must not treat it as
the full truth source for module ownership or freshness.

### `modules.json`

`modules.json` is the canonical module registry.

For each module it should record:

- stable identity
- owned roots
- extended coverage patterns
- excluded patterns
- tags
- the paths to that module's docs
- which root topics most often interact with the module

### `relations.json`

`relations.json` records cross-module and root-to-module relationships.

Examples:

- dependency direction
- command or workflow call chains
- shared runtime surfaces
- root-owned cross-cutting contracts
- upstream/downstream testing relationships

This file exists so an agent can start from the primary module and then expand
into adjacent modules only when the atlas says the relationship matters.

### `status.json`

`status.json` is the canonical freshness source.

It should have two levels:

- `global`
- `modules`

Proposed shape:

```json
{
  "global": {
    "freshness": "fresh",
    "last_full_refresh_commit": "abc123",
    "stale_reasons": [],
    "affected_root_docs": []
  },
  "modules": {
    "codex-team": {
      "freshness": "fresh",
      "deep_status": "fresh",
      "last_refresh_commit": "abc123",
      "coverage_fingerprint": "sha256:...",
      "stale_reasons": [],
      "affected_docs": []
    }
  }
}
```

### Freshness Semantics

Freshness should not be based primarily on timestamps.

The approved model is:

- compare module `last_refresh_commit`
- compare module coverage against current repository state
- use a module `coverage_fingerprint`
- preserve explicit dirty reasons and affected docs

`coverage_fingerprint` should be derived only from the module-declared coverage
set, not by recursively hashing the entire repository.

### Deep Staleness

`deep/` content is not a mandatory full-refresh target.

The approved behavior is:

- root and core module docs may refresh automatically
- `deep/` docs may be marked `deep_stale`
- the agent must be told that deep details may be outdated
- deep docs refresh on demand, manually or semi-automatically

This prevents the atlas from lying about freshness while avoiding expensive and
noisy automatic rewrites of deep detail.

## Module Documentation Contract

Each module gets a complete local documentation contract:

- `OVERVIEW.md` for identity, ownership, key entrypoints, and routing
- `ARCHITECTURE.md` for internal boundaries, truth ownership, and change
  propagation
- `STRUCTURE.md` for file placement, owned directories, and extension points
- `WORKFLOWS.md` for module-specific flows, state transitions, and handoffs
- `TESTING.md` for module verification routes and regression-sensitive areas

### `deep/` Controlled Categories

The approved `deep/` categories are:

- `capabilities/`
- `workflows/`
- `integrations/`
- `runtime/`
- `references/`

Each deep file should use a minimum template with:

- `Scope`
- `Why This Exists`
- `Truth Lives`
- `Inputs / Outputs`
- `Update Triggers`
- `Minimum Verification`
- `Confidence`

This allows deep content to expand without collapsing into arbitrary folder
sprawl.

## Agent Read Contract

The agent read contract must be explicit and machine-supported.

### High-Risk Brownfield Work

For `specify`, `plan`, `debug`, and `implement` on an existing repository:

1. Read `atlas-index.json`
2. Read `status.json`
3. Read `PROJECT-HANDBOOK.md`
4. Resolve the primary module from `modules.json`
5. Read `modules/<module-id>/OVERVIEW.md`
6. Read the smallest relevant set of that module's core docs
7. Expand into related modules only if `relations.json` says the touched area
   crosses module boundaries

### Fast/Quick Work

`fast` and `quick` may take a lighter route:

1. read `PROJECT-HANDBOOK.md`
2. inspect the index and status only enough to determine whether the touched
   area is local
3. load the primary module docs if the work is not obviously root-local

The gate remains strict enough to prevent blind local edits, but not so broad
that quick tasks need the full atlas on every turn.

### Missing or Weak Coverage

If module docs or related root docs are:

- missing
- stale
- too broad
- or insufficient for the touched area

the agent must route through `sp-map-codebase` and request a partial or full
refresh before proceeding.

## Refresh Model

The default refresh should be partial, not global.

### Partial Refresh

Default behavior:

- refresh the primary touched module
- refresh any directly affected module docs named by `relations.json`
- refresh affected root docs
- update index metadata and status

### Full Refresh

Full refresh is required when:

- module discovery rules changed
- large directory ownership moved
- shared top-level structure changed
- cross-module relations changed broadly
- the status model itself changed

### Deep Refresh

Deep docs are not automatically rewritten during every partial refresh.

Instead:

- mark the module `deep_stale`
- record which deep categories are affected
- let the agent decide whether the current task requires deep refresh

## Root vs Module Truth Split

The atlas must keep shared truth at the root layer and local truth at the
module layer.

### Root Layer Owns

- cross-module dependency graph
- shared workflow contracts
- repository-wide conventions
- runtime and operations invariants
- global testing strategy
- integration boundaries that span modules

### Module Layer Owns

- module-local architecture
- module-local file placement
- module-local workflow details
- module-local verification paths
- module-local deep technical references

This split avoids both duplication and under-specification.

## Validation Model

The rollout should be validated in phases.

The approved sequence is:

1. define index contracts
2. implement the new status model
3. pilot one real module through partial refresh -> status update -> agent read
   path
4. only then widen templates, `map-codebase`, passive gates, and docs

The single-module pilot is a design requirement, not an optional optimization.

## Alternatives Considered

### Option A: Keep one global topical set only

Pros:

- minimal implementation churn

Cons:

- does not solve module-local truth routing
- keeps global docs on a path toward bloat

Decision:

- rejected

### Option B: Put all docs beside source directories

Pros:

- strong locality

Cons:

- weak root navigation
- inconsistent structure across modules
- harder machine routing

Decision:

- rejected

### Option C: Root entrypoint plus index plus root/module split with controlled `deep/`

Pros:

- scalable
- machine-routable
- preserves detail
- supports partial refresh

Cons:

- larger implementation surface
- status model and templates both need migration

Decision:

- approved

## Risks and Mitigations

### Risk: Status model becomes too complex

Mitigation:

- keep `atlas-index.json` intentionally minimal
- keep `modules.json`, `relations.json`, and `status.json` responsibilities
  separate

### Risk: Deep docs drift silently

Mitigation:

- explicit `deep_stale`
- per-category update triggers
- no false "fresh" status for modules with stale deep content

### Risk: Agent still reads the wrong docs

Mitigation:

- make read order contractual
- route through `modules.json` plus `relations.json`
- update passive gate language to require module-targeted reads

### Risk: Partial refresh produces incoherent global state

Mitigation:

- every partial refresh also updates root fallout and index metadata
- pilot the closed loop on one real module before broad rollout

## Approved Direction

The approved design is:

- preserve `PROJECT-HANDBOOK.md` as the root entrypoint
- add a machine index under `.specify/project-map/index/`
- move root topical docs under `.specify/project-map/root/`
- add `.specify/project-map/modules/<module-id>/` as the module truth layer
- allow controlled `deep/` expansion inside each module
- track freshness at both global and module scope
- represent deep staleness explicitly instead of pretending it is always fresh
- make agents read root -> module -> related-module docs in a defined order
- ship the migration through a real single-module pilot before full rollout

This turns the atlas from a flat topical map into a layered documentation
system with enough structure to support large repositories without reducing
technical depth.

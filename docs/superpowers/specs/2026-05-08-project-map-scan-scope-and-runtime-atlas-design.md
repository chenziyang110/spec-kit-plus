# Project-Map Scan Scope and Runtime Atlas Design

**Date:** 2026-05-08
**Status:** Approved
**Owner:** Codex

## Summary

This design tightens the `sp-map-scan -> sp-map-build` atlas refresh flow in
three ways:

1. `sp-map-scan` becomes `diff-first`, even when the current project-map
   freshness state is `fresh`.
2. scan scope is restricted to `live surfaces` that can change atlas truth,
   while atlas outputs and workflow workbench artifacts become
   `reference-only`.
3. `sp-map-build` must fail closed when its evidence comes only from derived
   atlas artifacts instead of live repository paths.

The design also clarifies that Mermaid lifecycle and flow diagrams are
required atlas outputs, but they must be rendered into human-consumed deep
workflow pages instead of living primarily inside machine-readable indexes.

## Problem

Downstream use exposed three product failures:

1. `sp-map-scan` can treat an already-present atlas as if it were sufficient
   proof that no new scan is needed.
2. generated atlas artifacts under `.specify/project-map/` can be scanned back
   into the next atlas refresh as if they were source-of-truth repository
   surfaces.
3. capability flow diagrams may exist in `index/capabilities.json` or broad
   root pages, yet still be effectively absent from the pages humans and
   brownfield `sp-*` workflows actually use.

The result is wasted scan budget, false-positive refresh success, and poor
runtime usability of the atlas.

## Goals

- Make `sp-map-scan` perform a git-baseline diff before deciding scan scope,
  even when freshness is `fresh`.
- Restrict scan ledger and packet generation to live repository surfaces.
- Treat atlas outputs, worker results, and scan/build state artifacts as
  readable reference inputs, not as scan targets.
- Separate the runtime atlas consumed by ordinary `sp-*` workflows from the
  scan/build workbench artifacts used only during atlas refresh.
- Keep Mermaid lifecycle and flow diagrams mandatory, but render them into the
  deep workflow pages that brownfield workflows actually consume.
- Make `sp-map-build` reject scan packages or worker results that are grounded
  only in derived artifacts.

## Non-Goals

- Do not remove git-baseline freshness tracking.
- Do not make `sp-map-scan` re-scan the whole repository whenever git metadata
  is unavailable.
- Do not remove machine-readable capability or symptom indexes.
- Do not treat every path under `.specify/` as disposable or non-authoritative.
  Some `.specify` paths remain source-of-truth inputs.

## Key Terms

### Live Surface

A repository path whose contents can change atlas truth directly, such as:

- `src/**`
- `templates/**`
- `scripts/**`
- `tests/**`
- `.github/workflows/**`
- top-level product configs and docs that define runtime or workflow behavior

### Reference-Only Surface

A path that may be read to recover baseline, routing, or prior evidence, but
must not become a scan target, coverage row, packet scope, or build-success
evidence source.

Examples:

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/**`
- `.specify/project-map/scan-packets/**`
- `.specify/project-map/worker-results/**`
- `.specify/project-map/map-state.md`
- `.specify/project-map/index/status.json`
- other generated refresh exports or workflow state artifacts

### Hard-Excluded Surface

A path that is neither scanned nor used as atlas evidence except when a
separate task explicitly makes it relevant.

Examples:

- `.git/`
- virtual environments
- tool caches
- build outputs
- temporary logs
- vendor or dependency caches

## Approved Scope Model

### 1. `sp-map-scan` is Diff-First

Entering `sp-map-scan` with freshness `fresh` no longer permits an immediate
"already complete" conclusion.

The workflow must:

1. recover the current map baseline from project-map status and atlas inputs
2. compute `last_mapped_commit..HEAD` changed files when git baseline data is
   available
3. classify each changed path as `hard_excluded`, `reference_only`, or
   `live_surface`
4. generate scan ledger rows and packets only from live surfaces plus any
   explicitly focused live-surface expansion

`fresh` means "the previous refresh completed against a known baseline." It
does not mean "skip diff analysis."

### 2. `sp-map-scan` Uses a Three-Stage Filter

For each candidate path:

1. remove `hard_excluded`
2. downgrade atlas outputs and workflow workbench artifacts to
   `reference_only`
3. keep only `live_surface` paths for coverage-ledger and scan-packet output

`reference_only` paths may still be read during baseline recovery, but they
must not re-enter the next scan as if they were source-of-truth product
surfaces.

### 3. Focus Never Upgrades Derived Artifacts

If `$ARGUMENTS` or user focus points to a reference-only file such as
`PROJECT-HANDBOOK.md` or a project-map JSON index, the workflow must trace that
request back to the smallest matching live surface.

If no live source-of-truth path can be found, the workflow must block or
report a scope gap instead of scanning the derived artifact directly.

### 4. Fallback When Git Baseline Is Missing

If git is unavailable or `last_mapped_commit` is missing:

- do not fall back to a whole-repository scan
- if focus exists, scan only focused live surfaces
- otherwise scan a constrained set of source-of-truth live roots
- mark the run as a constrained fallback in scan metadata

This preserves correctness without widening back to "scan everything."

## `.specify` Classification Rules

The product must stop treating `.specify` as a single category.

### Keep as Source-of-Truth Inputs

These may remain live or authoritative inputs depending on task:

- `.specify/memory/**`
- `.specify/templates/**`
- other project-local override or rules surfaces that define future generated
  behavior

### Treat as Reference-Only Atlas or Workflow Outputs

These are not scan targets for the next atlas refresh:

- `.specify/project-map/**`
- `.specify/prd-runs/**` run outputs
- `.specify/testing/worker-results/**`
- generated workflow state, packet, export, and worker-result trees that exist
  only to record prior execution

The classification rule is: do not scan unnecessary artifacts, and do not
collapse `.specify` into one blanket exclusion.

## Runtime Atlas vs Refresh Workbench

The product should treat `.specify/project-map` as two distinct surfaces.

### Runtime Atlas

These are the files ordinary brownfield `sp-*` workflows should consume:

- `.specify/project-map/index/status.json`
- `.specify/project-map/QUICK-NAV.md`
- `.specify/project-map/index/atlas-index.json`
- `.specify/project-map/index/capabilities.json`
- `.specify/project-map/index/symptoms.json`
- `.specify/project-map/root/*.md`
- `.specify/project-map/modules/*/deep/workflows/*.md`

### Refresh Workbench

These exist to support `sp-map-scan` and `sp-map-build`, not routine
specification or implementation flows:

- `.specify/project-map/map-scan.md`
- `.specify/project-map/coverage-ledger.*`
- `.specify/project-map/repository-universe.json`
- `.specify/project-map/capability-ledger.json`
- `.specify/project-map/control-ledger.json`
- `.specify/project-map/scan-packets/*`
- `.specify/project-map/worker-results/*`
- `.specify/project-map/map-state.md`

This separation reduces confusion for both humans and agents and makes it
clear which artifacts should never be scanned back into the next atlas build.

## Mermaid Output Rules

The requirement to produce Mermaid diagrams remains valid:

- each mapped capability must produce a lifecycle Mermaid
- each mapped capability must produce a flow Mermaid

However, the primary human-consumed home for these diagrams must be:

- `.specify/project-map/modules/<module-id>/deep/workflows/<capability-id>.md`

`index/capabilities.json` may continue to retain structured Mermaid fields, but
it should not be the only or primary location where the diagrams exist.

`sp-map-build` should be considered incomplete if the capability diagrams exist
only in machine-readable indexes and are absent from the deep workflow pages
that runtime `sp-*` flows use.

## `sp-map-build` Fail-Closed Rules

`sp-map-build` must refuse success when:

- packet `required_reads` contain only reference-only or hard-excluded paths
- worker results report `paths_read` that are only atlas outputs, worker
  results, packet files, or other derived state artifacts
- the build can only confirm atlas content by re-reading prior atlas artifacts
  rather than live repository truth
- Mermaid diagram data exists only in indexes and was not rendered into the
  deep workflow documentation pages

This is an extension of the existing "structural-only refresh is a failed
build" rule. The build must now also reject `derived-only` evidence.

## Product Surfaces To Change

### Prompt and Contract Surfaces

- `templates/commands/map-scan.md`
- `templates/command-partials/map-scan/**`
- `templates/commands/map-build.md`
- related generated integration renderings and tests

### Shared Runtime Logic

- project-map scope selection helper surface
- project-map freshness/runtime helpers that currently treat `fresh` as
  sufficient without a new diff-first scope decision

### Documentation

- README guidance for atlas refresh
- handbook guidance for project-map runtime consumption
- project-map template docs where runtime atlas vs refresh workbench separation
  is explained

### Tests

- template guidance tests for diff-first scan semantics
- tests for live/reference/excluded scope classification
- tests that derived-only worker evidence blocks build success
- tests that capability Mermaid output is rendered into deep workflow pages

## Acceptance Criteria

The design is complete when all of the following are true:

1. Running `sp-map-scan` with freshness `fresh` still performs git diff-based
   scope selection before deciding whether a new scan is necessary.
2. Project-map atlas outputs and refresh workbench artifacts no longer enter
   the scan ledger as ordinary repository surfaces.
3. `.specify` classification is granular enough to preserve source-of-truth
   memory/templates surfaces while excluding unnecessary derived artifacts.
4. `sp-map-build` fails when its accepted evidence comes only from derived
   atlas artifacts.
5. Capability lifecycle and flow Mermaid diagrams are visible in deep workflow
   Markdown pages, not just in JSON indexes or broad root summaries.
6. Ordinary `sp-*` workflows have a clear, smaller runtime atlas surface to
   consume.

## Risks and Mitigations

- **Risk:** overly aggressive exclusion can hide a real source-of-truth file.
  Mitigation: keep `.specify` classification granular and test explicit
  allowlists for memory/templates surfaces.
- **Risk:** diff-only thinking can miss required neighboring truth surfaces.
  Mitigation: allow controlled live-surface expansion around changed paths and
  user focus.
- **Risk:** downstream projects may already have indexes with Mermaid content
  but no deep-page render.
  Mitigation: make `map-build` normalize and render diagram content into deep
  workflow pages during refresh.

## Implementation Sequence

1. Add shared scope-classification logic for `hard_excluded`,
   `reference_only`, and `live_surface`.
2. Update `sp-map-scan` contract and helpers to use diff-first scope
   narrowing.
3. Update `sp-map-build` readiness rules to reject derived-only evidence.
4. Render capability Mermaid content into deep workflow pages as a required
   build step.
5. Update tests and docs to reflect runtime atlas vs refresh workbench
   separation.

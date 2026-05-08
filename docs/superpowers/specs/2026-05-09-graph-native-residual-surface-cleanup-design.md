# Graph-Native Residual Surface Cleanup

**Date:** 2026-05-09
**Status:** Proposed
**Owner:** Codex

## Summary

This design completes the next cleanup phase after
`graph-native downstream workflow adoption`.

The target is not another foundation rewrite.
The target is contract closure across the remaining upstream workflow,
compatibility, scaffolding, and test surfaces that still teach or consume
handbook-first brownfield semantics.

`project cognition` remains the only default brownfield runtime truth path.
`PROJECT-HANDBOOK.md`, `DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`, and
`.specify/project-map/**` may continue to exist, but only as
`compatibility`, `export`, or `reference-only` surfaces unless the active
workflow is explicitly generating or maintaining those artifacts.

This round intentionally includes `sp-specify`, `sp-plan`, and `sp-tasks`.
Leaving those three surfaces handbook-gated would preserve the most visible
runtime contradiction in the product.

## Problem

The prior adoption round established graph-native downstream behavior, but a
repo-wide residue scan still shows three classes of drift:

1. upstream command templates and partials still treat
   `BUILD-HANDBOOK.md` or the handbook/project-map set as the default runtime
   gate, default scout artifact, or top-level context source
2. compatibility infrastructure and team scaffolding still describe
   handbook/project-map outputs in a way that blurs the difference between
   compatibility production and runtime truth
3. tests, fixtures, and lock assertions still encode old runtime-handbook
   contracts, which makes it easy to reintroduce handbook-first semantics

The result is partial convergence:

- downstream runtime behavior says cognition-first
- some managed guidance says cognition-first
- but several high-visibility upstream and infrastructure surfaces still say
  handbook-first or atlas-first

That mismatch is the product problem this design addresses.

## Goals

- Make graph-native cognition the only default brownfield runtime truth path
  across upstream and downstream workflow surfaces.
- Remove `BUILD-HANDBOOK.md`, `PROJECT-HANDBOOK.md`, and the
  handbook/project-map set from default runtime gates, default read order,
  default scout artifacts, and default context-bundle top entries for ordinary
  workflow execution.
- Preserve compatibility/export surfaces where they still serve migration,
  reader, or export purposes, but label them explicitly as
  `compatibility-only`, `export-only`, or `reference-only`.
- Keep the scripts and templates that maintain compatibility/export surfaces,
  while redefining them as compatibility-layer infrastructure rather than
  brownfield runtime truth.
- Realign tests and convergence locks so the default truth path is enforced
  and future handbook-first regressions are caught early.

## Non-Goals

- Do not remove every handbook or project-map artifact from the product.
- Do not rename all `project-map` user-facing command surfaces in this round.
- Do not redesign the cognition runtime foundation itself.
- Do not do a repo-wide text rewrite that ignores behavioral and contract
  consequences.
- Do not start implementation work from this design document.

## Scope

### Workflow Contract Scope

The primary migration set is:

- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/clarify.md`
- `templates/commands/deep-research.md`
- `templates/commands/constitution.md`
- the related command partials that still describe handbook/project-map
  surfaces as default runtime context

### Compatibility Infrastructure Scope

The normalization set includes:

- `scripts/bash/project-map-freshness.sh`
- `scripts/powershell/project-map-freshness.ps1`
- `templates/project-map/**`
- integration scaffolding and team guidance that still bundle
  `PROJECT-HANDBOOK.md` or `.specify/project-map/**` as default brownfield
  context

### Contract Lock Scope

The lock realignment set includes:

- tests that still encode runtime-handbook semantics
- packet/context fixtures that still use handbook-first bundles
- CLI and integration assertions that still describe handbook/project-map
  coverage as the default runtime entry
- allowlist and convergence coverage that should distinguish intentional
  compatibility from accidental drift

## Key Product Decision

This cleanup should be a `full residual migration`, not a partial wording pass.

Three alternative paths were considered:

1. full migration of upstream workflow surfaces, compatibility infrastructure,
   and tests
2. partial migration that keeps `sp-specify`, `sp-plan`, and `sp-tasks` on a
   special `BUILD-HANDBOOK` gate
3. wording-first cleanup with minimal contract and test movement

The product should choose option 1.

Option 2 keeps the most important contradiction in place.
Option 3 creates false convergence and weak regression protection.
Only full residual migration closes the remaining contract gap without leaving
the main specification and planning entrypoints on legacy truth semantics.

## Classification Rules

This round should use a hard three-way classification for every residue hit.

### `migrate-now`

A surface belongs here when it does any of the following for ordinary workflow
execution:

- treats handbook or project-map artifacts as the default runtime truth source
- requires `BUILD-HANDBOOK.md` or `PROJECT-HANDBOOK.md` as the default gate
- uses handbook/project-map artifacts as the default scout artifact
- places handbook/project-map artifacts at the top of the default context
  bundle
- tells the user to refresh handbook/project-map truth before continuing

These hits must be removed or rewritten in this round.

### `compatibility/export`

A surface belongs here when its purpose is to:

- provide a reader-facing export
- preserve migration continuity
- expose compatibility navigation for users or tooling
- act as a reference surface when a user explicitly asks for the legacy/export
  artifact

These hits may remain, but their wording must explicitly mark the surface as
`compatibility-only`, `export-only`, or `reference-only`.
They must not imply that ordinary workflow execution should start there.

### `infrastructure-itself`

A surface belongs here when its job is to generate, refresh, validate, or
package compatibility/export outputs.

Examples:

- `project-map-freshness` scripts
- `templates/project-map/**`
- integration scaffolding that orchestrates compatibility artifact generation

These surfaces are allowed to manipulate `PROJECT-HANDBOOK.md` and
`.specify/project-map/**` directly because those are their outputs.
However, their outward explanations must still avoid describing those outputs as
the default brownfield runtime truth path.

## Architecture Of The Cleanup

This work should be delivered as three bounded work packages rather than a
repo-wide wording sweep.

### Work Package A: Workflow Contract Migration

This package rewrites the remaining upstream workflow contracts so they match
the graph-native runtime.

Required changes:

- replace `BUILD-HANDBOOK.md` and handbook/project-map heavy-gate language in
  `specify`, `plan`, and `tasks`
- align `clarify`, `deep-research`, and `constitution` with the same
  cognition-first gate
- update related partials so their `Primary inputs`, read order, and scout
  rules begin with `.specify/project-cognition/status.json` plus the
  workflow-appropriate graph and slice surfaces
- keep `map-scan`, `map-build`, and `map-update` as workflow names where
  needed, but change their surrounding wording from
  `refresh handbook/project-map truth` to
  `refresh cognition baseline and synchronize compatibility/export outputs`

The target contract is:

- ordinary brownfield workflow entry starts at cognition status and required
  slices
- graph artifacts are read when the workflow contract requires deeper context
- legacy handbook/project-map artifacts are read only when the workflow is
  explicitly handling a compatibility/export request or compatibility-layer
  maintenance task

### Work Package B: Compatibility Infrastructure Normalization

This package keeps compatibility/export infrastructure intact while correcting
its product semantics.

Required changes:

- keep `project-map-freshness` scripts functional for compatibility asset
  lifecycle tracking
- adjust error messages, help text, and status framing so they describe
  compatibility/export outputs rather than ordinary runtime truth
- review `templates/project-map/**` for wording that still implies map outputs
  are the normal first-read path
- correct team scaffolding and integration instructions that still bundle
  `PROJECT-HANDBOOK.md` or `.specify/project-map/**` as the default brownfield
  execution context

This package does not delete compatibility infrastructure.
It narrows its meaning:

- compatibility artifacts can still be created, refreshed, exported, and
  referenced
- infrastructure that maintains them remains legitimate
- but none of that infrastructure should teach those artifacts as the default
  cognition path for ordinary workflow execution

### Work Package C: Contract Lock Realignment

This package changes the tests and anti-regression locks so the cleanup stays
closed after the implementation lands.

Required changes:

- rewrite tests that still assert runtime-handbook-first semantics
- update packet/context fixtures that still present handbook-first bundles as
  normative
- align CLI and integration descriptions with cognition-first routing
- add a stricter allowlist/convergence lock that permits only intentional
  `compatibility/export` and `infrastructure-itself` residue hits

The target assertion model is:

- ordinary workflows must default to graph-native cognition
- compatibility/export assets may still exist and be generated
- infrastructure that maintains compatibility assets is allowed to mention and
  touch them
- `migrate-now` residue must trend to zero and stay there

## Detailed Behavioral Contract

After this cleanup:

- `sp-specify`, `sp-plan`, and `sp-tasks` no longer describe
  `BUILD-HANDBOOK.md` as the default heavy gate
- no ordinary workflow should describe handbook/project-map coverage as the
  source of truth when graph-native cognition coverage exists
- compatibility/export artifacts remain available when explicitly requested or
  when a maintenance workflow is producing them
- compatibility/export maintenance helpers may require those outputs to exist,
  because those helpers operate on that layer itself
- user messaging should distinguish
  `refresh cognition baseline` from
  `refresh compatibility/export outputs`

## Completion Definition

This round is complete when all of the following are true:

- upstream workflow surfaces no longer treat `BUILD-HANDBOOK.md`,
  `PROJECT-HANDBOOK.md`, or the handbook/project-map set as the default
  brownfield runtime truth path
- graph-native cognition is the only default gate described in command
  wording, read order, scout behavior, and refresh routing
- compatibility/export surfaces still exist where intended, but are labeled as
  non-default surfaces
- infrastructure-itself surfaces still work, but describe themselves as
  compatibility-layer production and validation tools
- tests and fixtures lock the new contract instead of the old handbook-first
  contract

Completion is not defined as `fewer grep hits`.
Completion is defined as `closed semantics with explicit exceptions`.

## Validation Strategy

Validation should happen in layers.

### 1. Residue Re-Scan

Run the repo-wide residue scan again and classify every remaining hit.

Success criteria:

- `migrate-now` hits are zero
- remaining hits fall only into `compatibility/export` or
  `infrastructure-itself`
- any remaining intentional hits are documented by a tight allowlist rather
  than by informal reasoning

### 2. Template And Contract Tests

Run the workflow-template and contract coverage that protects:

- command template wording
- cognition gate enforcement
- project-map compatibility semantics
- integration rendering
- packet/context assembly
- team scaffolding and worker bootstrap wording

### 3. Convergence Lock

Add or strengthen a focused regression lock that prevents:

- `specify`, `plan`, or `tasks` from reintroducing `BUILD-HANDBOOK` heavy gates
- handbook-first default read order from returning in upstream commands
- handbook/project-map truth wording from reappearing outside the intentional
  compatibility allowlist

### 4. Targeted Stability Suite

Extend the targeted convergence suite so this residual cleanup becomes part of
the stable anti-regression surface rather than a one-off local patch.

## Risks And Mitigations

### Risk: Compatibility And Runtime Truth Get Blurred Again

Mitigation:

- use the three-way residue classification explicitly in code review and tests
- keep allowlist ownership narrow and auditable

### Risk: Infrastructure Cleanup Accidentally Breaks Compatibility Exports

Mitigation:

- do not delete compatibility infrastructure in this round
- keep infrastructure tests that prove compatibility outputs can still be
  generated and tracked

### Risk: Search-And-Replace Produces Superficial Consistency

Mitigation:

- review workflow read order, gate semantics, packet fixtures, and integration
  descriptions, not just strings
- require convergence locks that express behavioral intent

## Out-Of-Scope Follow-On Work

Possible later work, but not part of this design:

- shrinking or removing compatibility/export layers after the migration window
- renaming external `project-map` command surfaces if product policy changes
- broader documentation simplification after the residual cleanup is stable

## Recommended Implementation Order

1. update workflow templates and partials
2. normalize compatibility infrastructure wording
3. realign tests and fixtures
4. add the stricter allowlist/convergence lock
5. rerun residue scan and targeted verification until only intentional residue
   remains

## Decision

Proceed with `graph-native residual surface cleanup` as a full residual
migration program.

Do not preserve `sp-specify`, `sp-plan`, or `sp-tasks` as handbook-gated
exceptions.
Do not treat compatibility infrastructure as evidence that handbook/project-map
artifacts are still ordinary runtime truth.

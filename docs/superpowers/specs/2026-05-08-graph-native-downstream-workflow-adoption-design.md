# Graph-Native Downstream Workflow Adoption

**Date:** 2026-05-08
**Status:** Proposed
**Owner:** Codex

## Summary

This design turns the already-landed project cognition runtime foundation into
the default downstream brownfield truth surface across the product.

The target is not more foundation work.
The target is product-surface convergence.

`project cognition` becomes the only default brownfield runtime truth surface
for downstream workflows.
`DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`, and
`.specify/project-map/**` may remain for one release as explicit compatibility
or export surfaces, but they stop defining default gating, read order,
packet/context assembly, or generated guidance.

This is a downstream consumer adoption program, not a repo-wide rename.
The external `project-map` command surface can remain for one release as a
compatibility shell while its runtime meaning becomes cognition-first.

## Problem

The cognition runtime foundation is stable, but the wider product surface still
teaches and consumes older brownfield truth models.

Current drift appears in four layers:

1. shared workflow templates and command partials still require handbook-first
   or project-map-first reads in many downstream workflows
2. runtime helpers and gating surfaces still emit old atlas semantics in some
   packet, preflight, hook, and explanation paths
3. generated guidance and broad docs still teach
   `DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`, or
   `.specify/project-map/**` as the default runtime truth surfaces
4. tests and integration assertions still encode the old contract in places,
   which makes accidental regression easy even after local template updates

The result is false convergence:

- the foundation says cognition-first
- parts of the runtime already use cognition-first
- but broad downstream workflow behavior still acts handbook-first

That gap is the product problem this design addresses.

## Goals

- Make `.specify/project-cognition/status.json` the only default brownfield
  runtime freshness and truth gate for downstream workflows.
- Make workflow-specific cognition slices the default touched-area context
  surfaces for downstream workflows.
- Remove `DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`, and
  `.specify/project-map/**` from default downstream gating, read order,
  packet/context assembly, and generated workflow guidance.
- Keep one release of explicit compatibility surfaces where needed, but mark
  them as compatibility-only rather than default truth.
- Sweep docs, passive skills, managed guidance, runtime helpers, and broad
  tests so only intentional compatibility remains.

## Non-Goals

- Do not do a full external rename from `project-map` to `project-cognition`
  in the same round.
- Do not make `sp-specify`, `sp-plan`, or `sp-tasks` the main migration
  theater for this work.
- Do not remove every old brownfield artifact immediately if a compatibility
  export still serves one-release migration needs.
- Do not restart foundation design for the cognition runtime itself.
- Do not treat broad search-and-replace as sufficient proof of convergence.

## Scope

### Primary Workflow Scope

This design directly targets downstream brownfield consumer workflows:

- `sp-fast`
- `sp-quick`
- `sp-implement`
- `sp-debug`
- `sp-analyze`
- `sp-explain`
- `sp-test-scan`
- `sp-test-build`

### Secondary Scope

The following surfaces are in scope because they shape the downstream
consumption contract:

- shared command partials
- passive skills
- managed guidance blocks
- hook wording and guardrail messages
- runtime packet/context helpers
- docs and quickstart guidance
- relevant integration wording
- broad tests that lock consumer behavior

### Out Of Primary Scope

`sp-specify`, `sp-plan`, and `sp-tasks` should receive only consistency repairs
required to prevent contradictory product guidance.
They are not the primary migration target for this plan.

## Key Product Decision

The product should adopt a `one-release soft compatibility` rollout.

That means:

- downstream runtime behavior and default guidance switch to cognition-first now
- handbook and project-map legacy surfaces may remain temporarily as explicit
  compatibility or export layers
- compatibility layers must not remain silent defaults
- the next cleanup round may remove or further shrink those compatibility
  layers after downstream consumers have converged

This is intentionally not a hard delete cutover, because the current product
still has broad old-surface teaching and tests that need controlled migration.

## Architecture Of The Adoption Program

This work should be executed as a consumer-chain cutover, not as a text-only
documentation rewrite.

### Layer 1: Shared Runtime Gate

`templates/command-partials/common/context-loading-gradient.md` becomes the
single authoritative brownfield pre-source gate.

Its contract should be treated as the shared runtime truth:

- read `.specify/project-cognition/status.json`
- read the workflow-required cognition slices
- read graph artifacts only when the active workflow requires deeper context
- treat freshness as a gate, not a hint

Target freshness behavior:

- `missing` -> block and route through `sp-map-scan -> sp-map-build`
- `stale` -> block and route through `sp-map-update`
- `possibly_stale` -> inspect touched-area coverage and route through
  `sp-map-update` when coverage is not trustworthy

`templates/command-partials/common/navigation-check.md` may remain only as a
compatibility shim while migration is in progress.
It must not continue to define the primary brownfield contract.

### Layer 2: Runtime Propagation Helpers

Runtime helpers must stop merely acknowledging cognition and instead consume it
as the default runtime truth surface.

Representative surfaces include:

- `src/specify_cli/execution/packet_compiler.py`
- `src/specify_cli/hooks/preflight.py`
- hook messages and block reasons under `src/specify_cli/hooks/**`
- explanation routing and artifact resolution paths
- debug session intake and investigation routing
- result and context helpers that still name handbook-first paths

The contract change is:

- default context bundles start from `status.json` and workflow-appropriate
  slices
- block messages describe cognition refresh actions first
- resume logic uses cognition freshness and touched-area overlap instead of
  handbook trust as the default mental model
- helper wording treats handbook and project-map artifacts as compatibility or
  explicit fallback surfaces only

### Layer 3: Workflow Consumer Contracts

Downstream workflow templates should declare required cognition artifacts
instead of required handbook files.

Default workflow mapping:

- `fast`, `quick`, `implement`, `analyze`, `test-scan`, `test-build`
  consume `.specify/project-cognition/status.json` plus
  `.specify/project-cognition/slices/change.json` by default, with graph or
  testing artifacts added only when needed
- `debug` consumes `.specify/project-cognition/status.json` plus
  `.specify/project-cognition/slices/debug.json` by default, with graph
  claims/conflicts added when investigation depth requires them
- `explain` defaults to explaining cognition runtime truth when the user asks
  about brownfield runtime understanding or touched-area state; legacy handbook
  or project-map exports are explained only when the user explicitly asks for
  them

### Layer 4: Docs And Compatibility Shell

Once runtime and workflow consumers are cut over, broad docs and generated
guidance must converge on the new default.

Primary surfaces include:

- `README.md`
- `PROJECT-HANDBOOK.md`
- `docs/quickstart.md`
- managed AGENTS guidance
- passive skills
- integration wording that still teaches handbook-first reads

The requirement is not "remove every old name."
The requirement is "teach the new default path and label compatibility as
compatibility."

## Migrate-Now vs Intentional-Compat

This plan should explicitly classify legacy surfaces instead of leaving them in
an ambiguous state.

### Migrate Now

The following surfaces should stop behaving as default runtime truth surfaces
in this round:

- workflow templates that require `BUILD-HANDBOOK.md` or `DEBUG-HANDBOOK.md`
  as the first mandatory read
- shared partials or hook wording that teach handbook/project-map-first gating
- runtime helper paths that assemble packet context around handbook-first reads
- broad docs that teach `.specify/project-map/**` or handbook-first atlas
  traversal as the standard brownfield workflow entry
- tests that still enforce handbook-first downstream behavior by default

### Intentional Compatibility

The following surfaces may remain for one release, but only as explicit
compatibility layers:

- `project-map` command naming and selected CLI wording
- `DEBUG-HANDBOOK.md`
- `BUILD-HANDBOOK.md`
- `.specify/project-map/**` artifacts that are still useful as
  export/reference/continuity surfaces

Compatibility surfaces must obey two rules:

1. they are labeled as compatibility, export, or reference-only surfaces
2. no downstream workflow may require them as the default runtime truth path

## Completion Criteria

`graph-native downstream workflow adoption` should be considered complete only
when all of the following are true.

### 1. Shared Runtime Contract Is Unified

- `context-loading-gradient.md` is the only authoritative brownfield pre-source
  gate
- `navigation-check.md` is either downgraded to a compatibility shim or removed
  from primary workflow routing

### 2. Downstream Workflows Default To Cognition Runtime

The downstream workflow family no longer treats:

- `DEBUG-HANDBOOK.md`
- `BUILD-HANDBOOK.md`
- `.specify/project-map/**`

as the default runtime truth surfaces for gating, read order, or main workflow
context.

### 3. Runtime Helpers Have Actually Changed Route

Preflight, packet/context assembly, explanation routing, debug intake, and hook
wording are cognition-first in behavior, not just in aspirational wording.

### 4. Broad Docs And Tests Contain Only Intentional Compatibility

`README.md`, `PROJECT-HANDBOOK.md`, `docs/quickstart.md`, managed guidance,
passive skills, and broad test suites no longer contain accidental
handbook-first or project-map-first teaching.

### 5. Compatibility Inventory Exists

The migration leaves an explicit record of which remaining old surfaces are
intentional compatibility and which were required to migrate immediately.

## Implementation Phases

The implementation plan should be written in phases shaped by product
convergence, not by file buckets.

### Phase 1: Shared Gate Cutover

Objectives:

- finalize shared freshness semantics around cognition runtime
- make the cognition gate the only brownfield hard gate
- downgrade old navigation gate language to compatibility-only status

Primary outputs:

- shared partial convergence
- aligned block/recovery wording
- unambiguous freshness rules

### Phase 2: Runtime Helper Propagation

Objectives:

- move packet compilation, preflight, hook messages, and runtime artifact
  resolution onto cognition-first defaults
- ensure downstream runtime helpers consume slices/status rather than
  handbook-first surfaces

Primary outputs:

- context bundles that start from cognition runtime
- cognition-first resume and gating messages
- helper behavior aligned with the new contract

### Phase 3: Workflow Contract Migration

Objectives:

- update the targeted downstream workflows so their required reads and
  instructions explicitly name cognition runtime artifacts
- remove default handbook-first instructions from those workflows

Primary outputs:

- downstream workflow templates that declare slice/status reads
- updated partial usage across the targeted workflow family

### Phase 4: Guidance And Compatibility Sweep

Objectives:

- converge passive skills, docs, managed guidance, and integration wording on
  the new default
- keep only clearly labeled compatibility surfaces

Primary outputs:

- cognition-first generated guidance
- compatibility shell documentation that does not masquerade as default truth

### Phase 5: Convergence Verification

Objectives:

- run a repo-wide migrate-now vs intentional-compat sweep
- update or add tests that prove only explicit compatibility remains
- verify the product no longer drifts back to handbook-first downstream
  behavior

Primary outputs:

- convergence-proof test coverage
- explicit compatibility inventory
- repo-wide drift scan evidence

## Verification Strategy For The Plan

The implementation plan derived from this design should verify convergence at
three levels:

1. targeted unit or contract tests for runtime helpers and packet/context logic
2. template and generated-guidance tests for downstream workflow contracts
3. repo-wide search assertions that distinguish `intentional-compat` from
   accidental legacy drift

The plan should treat broad search as a verification aid, not as the only
proof of correctness.

## Risks

### Risk 1: Narrative-Only Convergence

Docs may be updated while runtime helpers still consume handbook-first
surfaces.

Mitigation:

- change shared gate and runtime helpers before broad doc sweep

### Risk 2: Runtime-Only Convergence

Helpers may become cognition-first while workflow templates and passive skills
still teach the old model.

Mitigation:

- keep workflow contract migration and guidance sweep in the same adoption
  program

### Risk 3: Compatibility Surfaces Reassert Default Status

Legacy surface retention can silently become default retention if wording is
not explicit.

Mitigation:

- require all retained legacy surfaces to be labeled compatibility-only
- add tests that fail when old surfaces are required as defaults

### Risk 4: Scope Creep Back Into Foundation Work

The migration can expand into redesigning cognition internals or unrelated
workflow families.

Mitigation:

- keep the scope on downstream consumer adoption
- limit `specify`, `plan`, and `tasks` to contradiction repair only

## Recommendation

Adopt the `consumer-surface adoption program` approach.

Do not run this as:

- a docs-first rewrite
- a narrow runtime-only cutover
- a repo-wide rename campaign

Run it as a phased downstream consumer migration that:

1. unifies the shared cognition gate
2. propagates runtime helper behavior
3. migrates downstream workflow contracts
4. sweeps generated guidance and docs
5. proves convergence with explicit compatibility accounting

That is the smallest plan that makes the foundation become real product
default behavior instead of remaining a partial substrate underneath older
brownfield contracts.

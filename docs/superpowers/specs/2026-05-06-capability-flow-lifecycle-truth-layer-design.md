# Capability Flow and Lifecycle Truth Layer Design

**Date:** 2026-05-06
**Status:** Approved
**Owner:** Codex

## Summary

This design extends the layered project-map atlas with a new truth layer for
capability flow, lifecycle, failure analysis, and change impact reasoning.

The current atlas is strong at architecture, structure, conventions,
integrations, testing, and operations routing. It is weaker at one specific
brownfield need: answering "where can this capability fail, which gates shape
its execution, and what adjacent branches must be considered before changing
it?" quickly enough for debugging and requirement work.

The approved direction is:

- keep the current layered atlas model
- add a product-level `capability flow + lifecycle truth layer` to generated
  projects
- make that layer a first-class brownfield truth surface, not an optional note
- support two primary entry modes: `By Capability` and `By Symptom`
- require `sp-map-scan` to prove full managed-scope coverage before
  `sp-map-build` may render the atlas
- make `sp-map-build` fail closed when any file, entrypoint, branch, or
  control node is not fully classified and mapped
- require `sp-debug`, `sp-analyze`, `sp-implement`, `sp-plan`, and
  `sp-tasks` to actively consume this layer when the task touches existing
  repository capabilities
- update generated `AGENTS.md` and `CLAUDE.md` guidance so agents read
  `symptom -> capability deep workflow -> module workflows -> root workflows`
  before broad code search when a matching atlas route exists

This design is intentionally not a "best effort" atlas expansion. The product
contract is that atlas completeness must be proven within the managed
repository universe before the atlas is allowed to claim completeness.

## Problem

The current atlas answers:

- which module owns the touched area
- which root topic explains architecture, operations, or testing
- which shared surfaces are risky
- whether the atlas baseline is fresh enough to trust

It does not yet answer, as a first-class truth surface:

- what the end-to-end lifecycle of a specific capability is
- what the main success and failure branches of that capability are
- which guards, filters, interceptors, middleware, hooks, feature flags, or
  permission gates alter the execution path
- where a capability should be inspected first when a user reports a symptom
- which neighboring branches and downstream surfaces must be reviewed when a
  new requirement changes the capability

That gap forces agents back into broad code search too early. In practice,
repositories need a brownfield atlas layer that is optimized for:

- debugging from a reported symptom
- extending an existing capability without missing adjacent branches
- reasoning about lifecycle transitions and failure points before code changes

The failure mode is not "missing documentation" in the generic sense. The
failure mode is lack of a truth-owning capability-flow surface with hard
coverage guarantees.

## Goals

- Add a first-class capability flow and lifecycle truth layer to the atlas.
- Represent that truth layer at root, module, and capability depth.
- Make `By Capability` and `By Symptom` first-class routing surfaces.
- Treat lifecycle diagrams and flow diagrams as mandatory atlas outputs for
  mapped capabilities, not optional illustrations.
- Require full managed-scope coverage at file, entrypoint, branch, and
  control-node levels before atlas build success.
- Support fast brownfield diagnosis by routing directly from symptom to
  capability and then to precise code/test/logging surfaces.
- Support safe brownfield change design by surfacing adjacent branches,
  lifecycle transitions, and downstream impact.
- Keep machine-readable proof artifacts separate from human-readable atlas
  documents while making them cross-reference each other.
- Preserve compatibility with the existing layered atlas architecture instead
  of inventing a second parallel documentation system.

## Non-Goals

- Do not replace the layered atlas model introduced by the existing project-map
  design.
- Do not treat partial capability coverage as acceptable for a "complete"
  atlas build.
- Do not make `sp-map-build` a second scanner that guesses missing truth from
  prose.
- Do not rely on manual documentation upkeep as the primary maintenance model.
- Do not promise that runtime behavior that is outside the declared managed
  repository universe can be proven by this system.
- Do not require runtime tracing in v1 in order to construct the truth layer.
  Runtime trace validation is an enhancement lane, not the initial contract.

## Managed Repository Universe

Completeness claims must be made against an explicit managed universe, not
against an undefined idea of "the repo."

The approved rule is:

- every file under managed scope must either be covered or explicitly excluded
- exclusions must be declared through atlas configuration or generated proof
  artifacts, not silently skipped by scanners
- vendor, generated, fixture, cache, or irrelevant support surfaces may be
  excluded only when the exclusion is explicit, machine-readable, and auditable
- any file kind that the scanner cannot classify must block completeness
  instead of being ignored

This is how "scan everything" becomes a verifiable contract:

- the system first defines the universe
- the system then proves coverage for that universe
- the atlas may only claim completeness for the declared universe

## Approved Truth-Layer Model

The capability truth layer extends the existing atlas. It does not replace the
handbook, root topical docs, or module docs.

### 1. Handbook and Quick Navigation

`PROJECT-HANDBOOK.md` remains the stable root entrypoint, but it must gain
explicit routing for:

- `By Capability`
- `By Symptom`
- `By Change Impact`

`.specify/project-map/QUICK-NAV.md` must gain parallel routing sections that
allow readers and agents to start from either:

- a known capability identifier such as `remote-terminal.create`
- a symptom such as `remote-terminal-create-failed`

These routes must point to the smallest truth-owning atlas page first.

### 2. Root Workflow Truth

`.specify/project-map/root/WORKFLOWS.md` becomes the system-level capability
truth page. It must contain machine-backed Mermaid views for:

- `system lifecycle`: repository-wide lifecycle transitions for the highest
  value entities, sessions, resources, or long-lived workflow objects
- `capability flow map`: major cross-module capability routes, including key
  control points that redirect or fail execution

This page remains global and cross-module. It should not absorb deep
capability-local detail that belongs in module or deep workflow pages.

### 3. Module Workflow Truth

`.specify/project-map/modules/<module-id>/WORKFLOWS.md` becomes the module-level
truth page. Each module must have two required diagram families:

- `module lifecycle`
- `module flow map`

The page must also route to module-owned capability deep workflow pages.

### 4. Capability Deep Workflow Pages

`.specify/project-map/modules/<module-id>/deep/workflows/<capability-id>.md`
becomes the primary brownfield debugging and change-impact page.

Each page must contain:

- one Mermaid lifecycle diagram
- one Mermaid flow diagram
- capability scope and owning module
- declared entrypoints
- preconditions and guards
- failure branches
- control nodes such as filters, interceptors, middleware, hooks, and feature
  gates
- "where to inspect" guidance: related files, logging surfaces, tests, and
  runtime boundaries
- change-impact guidance: adjacent branches and downstream surfaces that must
  be reviewed when this capability changes
- evidence links back to machine-readable proof artifacts

This page is the first-read target when a symptom or known capability can be
matched.

### 5. Mermaid as the Human Truth Format

The approved diagram format is Mermaid embedded directly in Markdown.

Reasons:

- generated projects already treat Markdown as the atlas surface
- Mermaid is readable in version control and in raw text
- agents can inspect and update Mermaid without requiring binary assets
- Mermaid can coexist with nearby diagnostic and verification prose

No secondary binary diagram format is required in v1.

## Capability and Symptom Routing

The atlas must gain explicit machine-readable routing for capability and
symptom lookup.

Approved new index surfaces:

- `.specify/project-map/index/capabilities.json`
- `.specify/project-map/index/symptoms.json`

`capabilities.json` should map:

- `capability_id`
- display name
- owning module
- deep workflow page
- entrypoints
- control-node summary
- related symptoms

`symptoms.json` should map:

- `symptom_id`
- likely capability candidates
- recommended first-read atlas page
- likely failure branches or control nodes
- related tests or evidence surfaces when known

`index/modules.json` should also record module-owned capability identifiers.
`index/relations.json` should record cross-module capability dependencies and
change-impact expansion routes.

## Completeness Proof Model

The capability truth layer is only trustworthy if completeness is proven
mechanically before rendering.

### Proof Objects

The approved proof model introduces four object families:

- `files`: all managed-scope files
- `entrypoints`: observable entry surfaces such as CLI commands, HTTP routes,
  UI actions, queue consumers, scheduled jobs, webhooks, and event handlers
- `flow nodes`: capability steps such as handlers, services, providers,
  publishers, consumers, state transitions, and external calls
- `control nodes`: branches and execution shapers such as middleware, guards,
  filters, interceptors, hooks, permission checks, feature flags, retries, or
  error mappers

### Required Proof Artifacts

The existing `coverage-ledger.json` remains necessary but is no longer
sufficient on its own.

Approved artifacts:

- `.specify/project-map/repository-universe.json`
- `.specify/project-map/coverage-ledger.json`
- `.specify/project-map/capability-ledger.json`
- `.specify/project-map/control-ledger.json`
- `.specify/project-map/scan-packets/*.md`
- `.specify/project-map/worker-results/*.json`

Suggested responsibilities:

- `repository-universe.json`: every managed-scope file and explicit exclusion
- `coverage-ledger.json`: file-level coverage, ownership, atlas targets, and
  packet/evidence linkage
- `capability-ledger.json`: capability definitions, entrypoints, major flow
  nodes, ownership, and atlas targets
- `control-ledger.json`: failure branches, guards, hooks, filters,
  interceptors, and other control nodes

### Four-Layer Proof Chain

The atlas build is considered complete only when all of these chains close:

1. `File Proof`
   Every managed-scope file must have a row that classifies its kind, ownership,
   atlas targets, and evidence status.

2. `Entrypoint Proof`
   Every detected entrypoint must map to a capability identifier and an atlas
   target.

3. `Branch/Control Proof`
   Every capability must enumerate success path, failure branches, and
   execution-shaping control nodes that alter behavior.

4. `Reverse Coverage Proof`
   Every root/module/deep atlas page must be able to point back to the proof
   objects that justify its content.

### Fail-Closed Rules

`sp-map-build` must fail when any of the following are true:

- a managed-scope file is unknown, unowned, or unmapped
- a file kind is unsupported and no explicit exclusion exists
- an entrypoint has no capability mapping
- a capability has no lifecycle diagram target or no flow diagram target
- a detected failure branch or control node is not assigned to an atlas target
- a required capability or symptom index route is missing
- root, module, and deep workflow routes do not link coherently
- an atlas diagram or section cannot be traced back to proof artifacts

This is the central policy choice of the design. The product must not emit a
"complete" atlas from incomplete proof data.

## `sp-map-scan` Pipeline

`sp-map-scan` becomes the proof compiler front half.

Approved pass structure:

1. `Universe pass`
   Enumerate every managed-scope file and write `repository-universe.json`.

2. `Surface detector pass`
   Run stack-aware detectors that discover entrypoints and control points across
   source, configs, templates, scripts, and tests.

3. `Flow extraction pass`
   Build candidate capability paths from entrypoints through handlers, services,
   providers, state transitions, and external boundaries.

4. `Capability clustering pass`
   Group related entrypoints and flow nodes into stable capability identifiers.

5. `Branch/control proof pass`
   Enumerate success paths, failure branches, guards, filters, interceptors,
   hooks, and related control nodes for each capability.

6. `Atlas target assignment pass`
   Assign every file, capability, branch, and control node to root, module, and
   deep atlas targets.

7. `Proof summary pass`
   Emit the ledgers and packets required by `sp-map-build`.

The approved rule is that `sp-map-scan` must not silently downgrade unknowns.
Unknowns remain blocking proof gaps.

## `sp-map-build` Pipeline

`sp-map-build` becomes the renderer and validator back half.

Approved build rules:

- it must read proof artifacts first and refuse to continue when proof does not
  close
- it must not perform a second broad repository scan to "fill in" truth
- it may organize, summarize, and render ledger-backed information only
- it must write root/module/deep workflow truth surfaces and updated index
  routes

Approved outputs include:

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/QUICK-NAV.md`
- `.specify/project-map/root/WORKFLOWS.md`
- `.specify/project-map/modules/<module-id>/WORKFLOWS.md`
- `.specify/project-map/modules/<module-id>/deep/workflows/<capability-id>.md`
- `.specify/project-map/index/capabilities.json`
- `.specify/project-map/index/symptoms.json`

## Workflow Consumption Rules

This truth layer only matters if workflows actively consume it.

### Strong Consumers

These workflows must actively load capability truth when working against an
existing repository capability:

- `sp-debug`
- `sp-analyze`
- `sp-implement`
- `sp-plan`
- `sp-tasks`

Approved read order:

1. symptom route when the user reports a concrete symptom
2. capability route when the touched capability is known
3. module workflow truth when no direct capability page exists
4. root workflow truth when the issue is cross-module or still ambiguous
5. live code only after atlas truth is insufficient, stale, or explicitly
   incomplete

### Representative Workflow Requirements

- `sp-debug` must read the matching symptom or capability deep workflow page
  before broad code search when a route exists.
- `sp-analyze` must read capability flow and change-impact sections when the
  analysis concerns an existing feature or failure mode.
- `sp-implement` must read capability lifecycle, flow, and change-impact
  sections before editing an existing capability.
- `sp-plan` must use relevant capability truth as brownfield evidence when
  planning around an existing implementation.
- `sp-tasks` must preserve adjacent branch and control-node coverage in task
  decomposition when a capability page exists.

## Generated Prompt and Guidance Surfaces

The capability truth layer must also be reflected in generated prompt guidance.

Required surfaces:

- generated `AGENTS.md`
- generated `CLAUDE.md`
- shared atlas-routing passive skills such as
  `spec-kit-project-map-gate` and `spec-kit-workflow-routing`
- common command partials that describe handbook/project-map read order

Approved guidance principle:

When a task extends, debugs, or refactors an existing capability, the agent
must attempt:

`symptom -> capability deep workflow -> module workflows -> root workflows`

before broad live code search, unless freshness or proof state says the truth
layer is missing or stale.

## Files and Product Surfaces Likely Affected

This is a cross-surface product change, not a template-only tweak.

Likely affected surfaces:

- `templates/project-map/**`
- `templates/project-handbook-template.md`
- `templates/commands/map-scan.md`
- `templates/commands/map-build.md`
- `templates/commands/{debug,analyze,implement,plan,tasks,specify}.md`
- `templates/command-partials/common/**`
- `templates/passive-skills/spec-kit-project-map-gate/`
- `templates/passive-skills/spec-kit-workflow-routing/`
- `templates/passive-skills/subagent-driven-development/`
- `src/specify_cli/project_map_status.py`
- `src/specify_cli/hooks/artifact_validation.py`
- project-map freshness helpers and route-aware scripts
- generated asset integration propagation tests
- `README.md` and `PROJECT-HANDBOOK.md`

## Verification Strategy

The new truth layer requires stronger contract testing.

Minimum validation families:

- template contract tests for handbook, quick-nav, module workflow, deep
  workflow, and map-scan/map-build wording
- artifact-validation tests for new ledger and index requirements
- status and routing tests for capability and symptom lookups
- integration propagation tests to ensure generated assets across supported
  agents inherit the new rules
- reverse coverage tests to ensure rendered atlas pages reference valid proof
  objects

## Rollout

### v1

Deliver the fail-closed product shell:

- atlas structure changes
- new ledger and index contracts
- updated `sp-map-scan` and `sp-map-build` workflow contracts
- strong consumer workflow guidance
- prompt-surface routing updates
- test coverage that prevents incomplete atlas builds from passing

### v1.1

Expand detector coverage for common repository surfaces and improve capability
clustering quality while preserving the same fail-closed rules.

### v2

Add optional runtime-trace-backed validation and stronger reverse proof for
projects that can supply executable evidence.

## Acceptance Criteria

- Generated projects gain a first-class capability flow and lifecycle truth
  layer within the existing atlas.
- `PROJECT-HANDBOOK.md` and `QUICK-NAV.md` support capability and symptom
  routing as first-class entry modes.
- Root and module workflow pages include required lifecycle and flow diagram
  families.
- Capability deep workflow pages become mandatory outputs for mapped
  capabilities.
- `sp-map-scan` emits machine-readable proof artifacts that cover managed-scope
  files, entrypoints, branches, and control nodes.
- `sp-map-build` fails when proof does not close.
- `sp-debug`, `sp-analyze`, `sp-implement`, `sp-plan`, and `sp-tasks` gain
  explicit truth-layer consumption rules.
- Generated prompt surfaces route agents through symptom and capability truth
  before broad code search when atlas state is trustworthy.
